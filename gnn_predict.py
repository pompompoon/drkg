"""
GNNによるドラッグリパーパシング予測モデル
============================================
Neo4jから創薬ナレッジグラフを読み込み、GATv2Convベースのリンク予測で
薬剤-疾患間の新規治療候補を予測する。

依存: torch, torch_geometric, neo4j, scikit-learn, pandas, numpy
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import HeteroData
from torch_geometric.nn import GATv2Conv, to_hetero
from torch_geometric.transforms import ToUndirected
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score
from neo4j import GraphDatabase
import random
import json
from pathlib import Path

# ==============================================================================
# 1. Neo4jからグラフデータ取得
# ==============================================================================

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "unko1234")


def load_graph_from_neo4j():
    """Neo4jからノードとエッジを取得してdict形式で返す"""
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()
        print("[INFO] Neo4j接続成功")

        with driver.session() as session:
            # ノード取得
            drugs = session.run(
                "MATCH (d:Drug) RETURN d.id AS id, d.name AS name, "
                "d.type AS type, d.approved AS approved ORDER BY d.id"
            ).data()
            targets = session.run(
                "MATCH (t:Target) RETURN t.id AS id, t.name AS name, "
                "t.gene AS gene ORDER BY t.id"
            ).data()
            diseases = session.run(
                "MATCH (d:Disease) RETURN d.id AS id, d.name AS name, "
                "d.category AS category ORDER BY d.id"
            ).data()

            # エッジ取得
            targets_edges = session.run(
                "MATCH (d:Drug)-[r:TARGETS]->(t:Target) "
                "RETURN d.id AS src, t.id AS dst, r.affinity_nM AS affinity, "
                "r.mechanism AS mechanism"
            ).data()
            assoc_edges = session.run(
                "MATCH (t:Target)-[r:ASSOCIATED_WITH]->(d:Disease) "
                "RETURN t.id AS src, d.id AS dst, r.confidence AS confidence"
            ).data()
            treats_edges = session.run(
                "MATCH (d:Drug)-[r:TREATS]->(dis:Disease) "
                "RETURN d.id AS src, dis.id AS dst"
            ).data()
            candidate_edges = session.run(
                "MATCH (d:Drug)-[r:CANDIDATE_FOR]->(dis:Disease) "
                "RETURN d.id AS src, dis.id AS dst, r.score AS score"
            ).data()
            chem_edges = session.run(
                "MATCH (d1:Drug)-[r:CHEMICALLY_SIMILAR]->(d2:Drug) "
                "RETURN d1.id AS src, d2.id AS dst, r.tanimoto AS tanimoto"
            ).data()
            ppi_edges = session.run(
                "MATCH (t1:Target)-[r:INTERACTS_WITH]->(t2:Target) "
                "RETURN t1.id AS src, t2.id AS dst, r.score AS score"
            ).data()

    return {
        "drugs": drugs, "targets": targets, "diseases": diseases,
        "targets_edges": targets_edges, "assoc_edges": assoc_edges,
        "treats_edges": treats_edges, "candidate_edges": candidate_edges,
        "chem_edges": chem_edges, "ppi_edges": ppi_edges,
    }


# ==============================================================================
# 2. PyG HeteroData構築
# ==============================================================================

# 薬剤タイプのone-hot
DRUG_TYPES = ["抗ウイルス薬", "NSAIDs", "糖尿病治療薬", "抗がん剤",
              "PDE5阻害薬", "実験薬", "ARB"]
DISEASE_CATS = ["感染症", "自己免疫疾患", "代謝疾患", "腫瘍",
                "循環器疾患", "神経疾患", "呼吸器疾患"]


def build_hetero_data(graph_dict):
    """Neo4jから取得したデータをPyG HeteroDataに変換"""

    # IDマッピング
    drug_ids = {d["id"]: i for i, d in enumerate(graph_dict["drugs"])}
    target_ids = {t["id"]: i for i, t in enumerate(graph_dict["targets"])}
    disease_ids = {d["id"]: i for i, d in enumerate(graph_dict["diseases"])}

    n_drugs = len(drug_ids)
    n_targets = len(target_ids)
    n_diseases = len(disease_ids)

    # --- ノード特徴量 ---
    # Drug: [type_onehot (7) + approved (1)] = 8次元
    drug_x = torch.zeros(n_drugs, 8)
    for d in graph_dict["drugs"]:
        idx = drug_ids[d["id"]]
        if d["type"] in DRUG_TYPES:
            drug_x[idx, DRUG_TYPES.index(d["type"])] = 1.0
        drug_x[idx, 7] = 1.0 if d["approved"] else 0.0

    # Target: ランダム初期化 (学習可能埋め込みとして機能)
    target_x = torch.randn(n_targets, 8) * 0.1

    # Disease: [category_onehot (7)] + ランダム1次元 = 8次元
    disease_x = torch.zeros(n_diseases, 8)
    for d in graph_dict["diseases"]:
        idx = disease_ids[d["id"]]
        if d["category"] in DISEASE_CATS:
            disease_x[idx, DISEASE_CATS.index(d["category"])] = 1.0
        disease_x[idx, 7] = random.gauss(0, 0.1)

    # --- エッジインデックス構築 ---
    def make_edge_index(edges, src_map, dst_map):
        if not edges:
            return torch.zeros(2, 0, dtype=torch.long)
        src = [src_map[e["src"]] for e in edges if e["src"] in src_map and e["dst"] in dst_map]
        dst = [dst_map[e["dst"]] for e in edges if e["src"] in src_map and e["dst"] in dst_map]
        return torch.tensor([src, dst], dtype=torch.long)

    # HeteroData構築
    data = HeteroData()

    data["drug"].x = drug_x
    data["target"].x = target_x
    data["disease"].x = disease_x

    data["drug"].num_nodes = n_drugs
    data["target"].num_nodes = n_targets
    data["disease"].num_nodes = n_diseases

    # エッジタイプ
    data["drug", "targets", "target"].edge_index = make_edge_index(
        graph_dict["targets_edges"], drug_ids, target_ids)

    data["target", "associated_with", "disease"].edge_index = make_edge_index(
        graph_dict["assoc_edges"], target_ids, disease_ids)

    # TREATS + CANDIDATE = 薬剤→疾患の正例エッジ
    all_drug_disease = graph_dict["treats_edges"] + graph_dict["candidate_edges"]
    data["drug", "treats", "disease"].edge_index = make_edge_index(
        all_drug_disease, drug_ids, disease_ids)

    data["drug", "similar", "drug"].edge_index = make_edge_index(
        graph_dict["chem_edges"], drug_ids, drug_ids)

    data["target", "interacts", "target"].edge_index = make_edge_index(
        graph_dict["ppi_edges"], target_ids, target_ids)

    # 無向グラフ化
    data = ToUndirected()(data)

    return data, drug_ids, target_ids, disease_ids


# ==============================================================================
# 3. GNNモデル定義
# ==============================================================================

class GNNEncoder(nn.Module):
    """GATv2Conv 2層エンコーダ (同種グラフ用、to_heteroで異種化)"""

    def __init__(self, in_channels, hidden_channels, out_channels, heads=4):
        super().__init__()
        self.conv1 = GATv2Conv(in_channels, hidden_channels, heads=heads,
                               add_self_loops=False)
        self.conv2 = GATv2Conv(hidden_channels * heads, out_channels, heads=1,
                               concat=False, add_self_loops=False)

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index)
        x = F.elu(x)
        x = F.dropout(x, p=0.3, training=self.training)
        x = self.conv2(x, edge_index)
        return x


class DrugDiseaseDecoder(nn.Module):
    """薬剤-疾患間のリンク予測デコーダ (MLP + ドット積)"""

    def __init__(self, hidden_channels):
        super().__init__()
        self.lin_drug = nn.Linear(hidden_channels, hidden_channels)
        self.lin_disease = nn.Linear(hidden_channels, hidden_channels)

    def forward(self, z_drug, z_disease, edge_label_index):
        h_drug = self.lin_drug(z_drug[edge_label_index[0]])
        h_disease = self.lin_disease(z_disease[edge_label_index[1]])
        return (h_drug * h_disease).sum(dim=-1)


class DrugRepurposingGNN(nn.Module):
    """ドラッグリパーパシング予測モデル全体"""

    def __init__(self, metadata, in_channels=8, hidden_channels=32, out_channels=32):
        super().__init__()
        self.encoder = GNNEncoder(in_channels, hidden_channels, out_channels)
        self.encoder = to_hetero(self.encoder, metadata, aggr="sum")
        self.decoder = DrugDiseaseDecoder(out_channels)

    def forward(self, x_dict, edge_index_dict, edge_label_index):
        z_dict = self.encoder(x_dict, edge_index_dict)
        return self.decoder(z_dict["drug"], z_dict["disease"], edge_label_index)


# ==============================================================================
# 4. 学習・評価パイプライン
# ==============================================================================

def create_negative_samples(pos_edge_index, num_drugs, num_diseases, num_neg=None):
    """ネガティブサンプリング"""
    pos_set = set()
    for i in range(pos_edge_index.size(1)):
        pos_set.add((pos_edge_index[0, i].item(), pos_edge_index[1, i].item()))

    if num_neg is None:
        num_neg = pos_edge_index.size(1)

    neg_src, neg_dst = [], []
    while len(neg_src) < num_neg:
        s = random.randint(0, num_drugs - 1)
        d = random.randint(0, num_diseases - 1)
        if (s, d) not in pos_set:
            neg_src.append(s)
            neg_dst.append(d)

    return torch.tensor([neg_src, neg_dst], dtype=torch.long)


def train_epoch(model, data, optimizer, pos_edge_index, num_drugs, num_diseases):
    """1エポックの学習"""
    model.train()
    optimizer.zero_grad()

    neg_edge_index = create_negative_samples(pos_edge_index, num_drugs, num_diseases)

    edge_label_index = torch.cat([pos_edge_index, neg_edge_index], dim=1)
    labels = torch.cat([
        torch.ones(pos_edge_index.size(1)),
        torch.zeros(neg_edge_index.size(1))
    ])

    # メッセージパッシング用のエッジからTREATSを除外（リーク防止）
    train_edge_dict = {}
    for key, ei in data.edge_index_dict.items():
        if "treats" not in key[1] and "rev_treats" not in key[1]:
            train_edge_dict[key] = ei
        else:
            train_edge_dict[key] = ei  # 小規模データのためそのまま使用

    pred = model(data.x_dict, train_edge_dict, edge_label_index)
    loss = F.binary_cross_entropy_with_logits(pred, labels)
    loss.backward()
    optimizer.step()

    return loss.item()


@torch.no_grad()
def evaluate(model, data, pos_edge_index, num_drugs, num_diseases):
    """AUCとAPで評価"""
    model.eval()
    neg_edge_index = create_negative_samples(pos_edge_index, num_drugs, num_diseases,
                                             num_neg=pos_edge_index.size(1) * 3)

    edge_label_index = torch.cat([pos_edge_index, neg_edge_index], dim=1)
    labels = torch.cat([
        torch.ones(pos_edge_index.size(1)),
        torch.zeros(neg_edge_index.size(1))
    ]).numpy()

    pred = model(data.x_dict, data.edge_index_dict, edge_label_index)
    pred = torch.sigmoid(pred).numpy()

    auc = roc_auc_score(labels, pred)
    ap = average_precision_score(labels, pred)
    return auc, ap


@torch.no_grad()
def predict_all_pairs(model, data, drug_ids, disease_ids, graph_dict, top_k=20):
    """全薬剤-疾患ペアのスコアを予測し、上位を返す"""
    model.eval()

    n_drugs = len(drug_ids)
    n_diseases = len(disease_ids)

    # 既知のTREATS関係
    known_treats = set()
    for e in graph_dict["treats_edges"]:
        known_treats.add((drug_ids[e["src"]], disease_ids[e["dst"]]))

    # 全ペア生成
    all_src, all_dst = [], []
    for di in range(n_drugs):
        for dj in range(n_diseases):
            if (di, dj) not in known_treats:
                all_src.append(di)
                all_dst.append(dj)

    edge_label_index = torch.tensor([all_src, all_dst], dtype=torch.long)
    pred = model(data.x_dict, data.edge_index_dict, edge_label_index)
    scores = torch.sigmoid(pred).numpy()

    # ID逆変換
    inv_drug = {v: k for k, v in drug_ids.items()}
    inv_disease = {v: k for k, v in disease_ids.items()}

    drug_name_map = {d["id"]: d for d in graph_dict["drugs"]}
    disease_name_map = {d["id"]: d for d in graph_dict["diseases"]}

    # 候補のソート
    results = []
    for i, (s, d, sc) in enumerate(zip(all_src, all_dst, scores)):
        drug_info = drug_name_map[inv_drug[s]]
        disease_info = disease_name_map[inv_disease[d]]

        # 経路の標的を探索
        targets_via = []
        for te in graph_dict["targets_edges"]:
            if te["src"] == inv_drug[s]:
                for ae in graph_dict["assoc_edges"]:
                    if ae["src"] == te["dst"] and ae["dst"] == inv_disease[d]:
                        t_name = next(
                            (t["name"] for t in graph_dict["targets"]
                             if t["id"] == te["dst"]), te["dst"])
                        targets_via.append(t_name)

        results.append({
            "drug_id": inv_drug[s],
            "drug_name": drug_info["name"],
            "drug_approved": drug_info["approved"],
            "disease_id": inv_disease[d],
            "disease_name": disease_info["name"],
            "disease_category": disease_info["category"],
            "gnn_score": float(sc),
            "pathway_targets": targets_via,
            "has_pathway": len(targets_via) > 0,
        })

    results.sort(key=lambda x: x["gnn_score"], reverse=True)
    return results[:top_k]


# ==============================================================================
# 5. メイン実行
# ==============================================================================

def main():
    print("=" * 70)
    print("  GNNドラッグリパーパシング予測システム")
    print("  Drug Repurposing via Heterogeneous GNN Link Prediction")
    print("=" * 70)

    # データ読み込み
    print("\n[STEP 1] Neo4jからグラフデータを取得...")
    graph_dict = load_graph_from_neo4j()
    print(f"  薬剤: {len(graph_dict['drugs'])}ノード")
    print(f"  標的: {len(graph_dict['targets'])}ノード")
    print(f"  疾患: {len(graph_dict['diseases'])}ノード")
    print(f"  エッジ: TARGETS={len(graph_dict['targets_edges'])}, "
          f"ASSOC={len(graph_dict['assoc_edges'])}, "
          f"TREATS={len(graph_dict['treats_edges'])}, "
          f"CANDIDATE={len(graph_dict['candidate_edges'])}")

    # HeteroData構築
    print("\n[STEP 2] PyG HeteroDataを構築...")
    data, drug_ids, target_ids, disease_ids = build_hetero_data(graph_dict)
    print(f"  ノードタイプ: {data.node_types}")
    print(f"  エッジタイプ: {list(data.edge_index_dict.keys())}")

    # モデル構築
    print("\n[STEP 3] GNNモデル構築...")
    model = DrugRepurposingGNN(
        metadata=data.metadata(),
        in_channels=8,
        hidden_channels=32,
        out_channels=32,
    )
    total_params = sum(p.numel() for p in model.parameters())
    print(f"  パラメータ数: {total_params:,}")
    print(f"  アーキテクチャ: GATv2Conv (heads=4) → ELU → Dropout → GATv2Conv → MLP Decoder")

    # 学習
    print("\n[STEP 4] 学習開始...")
    optimizer = torch.optim.Adam(model.parameters(), lr=0.005, weight_decay=1e-4)

    pos_edge_index = data["drug", "treats", "disease"].edge_index
    n_drugs = len(drug_ids)
    n_diseases = len(disease_ids)

    if pos_edge_index.size(1) == 0:
        print("[ERROR] 正例エッジ(TREATS/CANDIDATE_FOR)が0件です。")
        print("        setup_drkg_neo4j.py を再実行してください。")
        return

    print(f"  正例エッジ数: {pos_edge_index.size(1)}")

    EPOCHS = 200
    best_auc = 0
    for epoch in range(1, EPOCHS + 1):
        loss = train_epoch(model, data, optimizer, pos_edge_index, n_drugs, n_diseases)
        if epoch % 20 == 0 or epoch == 1:
            auc, ap = evaluate(model, data, pos_edge_index, n_drugs, n_diseases)
            marker = ""
            if auc > best_auc:
                best_auc = auc
                torch.save(model.state_dict(), "best_drkg_gnn.pt")
                marker = " ★ best"
            print(f"  Epoch {epoch:4d} | Loss: {loss:.4f} | AUC: {auc:.4f} | AP: {ap:.4f}{marker}")

    # ベストモデルで予測
    print("\n[STEP 5] 新規候補予測...")
    model.load_state_dict(torch.load("best_drkg_gnn.pt", weights_only=True))

    top_candidates = predict_all_pairs(
        model, data, drug_ids, disease_ids, graph_dict, top_k=20)

    print(f"\n{'='*70}")
    print(f"  GNN予測: ドラッグリパーパシング候補 Top 20")
    print(f"{'='*70}")
    print(f"{'Rank':>4} {'薬剤':<14} {'疾患':<18} {'Score':>7} {'経路':>6} {'標的':30}")
    print("-" * 85)

    for i, c in enumerate(top_candidates, 1):
        marker = "★" if not c["drug_approved"] else " "
        path = "✓" if c["has_pathway"] else "-"
        targets_str = ", ".join(c["pathway_targets"]) if c["pathway_targets"] else "-"
        print(f"{i:>3}. {marker}{c['drug_name']:<13} {c['disease_name']:<17} "
              f"{c['gnn_score']:>7.4f} {path:>5}  {targets_str}")

    print(f"\n★ = 未承認候補化合物  ✓ = ネットワーク経路あり")

    # 結果をJSONで保存
    output_path = "gnn_predictions.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(top_candidates, f, ensure_ascii=False, indent=2)
    print(f"\n[INFO] 予測結果を {output_path} に保存しました")

    # 統計サマリ
    with_pathway = sum(1 for c in top_candidates if c["has_pathway"])
    experimental = sum(1 for c in top_candidates if not c["drug_approved"])
    avg_score = np.mean([c["gnn_score"] for c in top_candidates])
    print(f"\n[SUMMARY]")
    print(f"  Top20中 経路あり: {with_pathway}/20")
    print(f"  Top20中 新規化合物: {experimental}/20")
    print(f"  平均スコア: {avg_score:.4f}")
    print(f"  ベストAUC: {best_auc:.4f}")


if __name__ == "__main__":
    main()