"""
創薬ナレッジグラフ (Drug Repurposing Knowledge Graph) - Neo4j セットアップスクリプト
薬剤・標的(タンパク質)・疾患ノードとエッジを作成し、TransEスタイルのスコアリングを実行
"""

from neo4j import GraphDatabase
import random
import math

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "unko1234")

# ====== サンプルデータ定義 ======

DRUGS = [
    {"id": "D001", "name": "レムデシビル",    "formula": "C27H35N6O8P", "type": "抗ウイルス薬",   "approved": True},
    {"id": "D002", "name": "イブプロフェン",  "formula": "C13H18O2",    "type": "NSAIDs",         "approved": True},
    {"id": "D003", "name": "メトホルミン",    "formula": "C4H11N5",     "type": "糖尿病治療薬",   "approved": True},
    {"id": "D004", "name": "ドキソルビシン",  "formula": "C27H29NO11",  "type": "抗がん剤",       "approved": True},
    {"id": "D005", "name": "アスピリン",      "formula": "C9H8O4",      "type": "NSAIDs",         "approved": True},
    {"id": "D006", "name": "シルデナフィル",  "formula": "C22H30N6O4S", "type": "PDE5阻害薬",     "approved": True},
    {"id": "D007", "name": "候補化合物A",     "formula": "C18H22N4O3",  "type": "実験薬",         "approved": False},
    {"id": "D008", "name": "候補化合物B",     "formula": "C21H26N2O5",  "type": "実験薬",         "approved": False},
    {"id": "D009", "name": "候補化合物C",     "formula": "C15H19N3O4",  "type": "実験薬",         "approved": False},
    {"id": "D010", "name": "バルサルタン",    "formula": "C24H29N5O3",  "type": "ARB",            "approved": True},
]

TARGETS = [
    {"id": "T001", "name": "RdRp",      "full_name": "RNA依存性RNAポリメラーゼ",     "gene": "RDRP"},
    {"id": "T002", "name": "COX-2",     "full_name": "シクロオキシゲナーゼ2",         "gene": "PTGS2"},
    {"id": "T003", "name": "AMPK",      "full_name": "AMP活性化プロテインキナーゼ",   "gene": "PRKAA1"},
    {"id": "T004", "name": "TOP2A",     "full_name": "トポイソメラーゼIIα",           "gene": "TOP2A"},
    {"id": "T005", "name": "COX-1",     "full_name": "シクロオキシゲナーゼ1",         "gene": "PTGS1"},
    {"id": "T006", "name": "PDE5",      "full_name": "ホスホジエステラーゼ5",         "gene": "PDE5A"},
    {"id": "T007", "name": "ACE2",      "full_name": "アンジオテンシン変換酵素2",     "gene": "ACE2"},
    {"id": "T008", "name": "mTOR",      "full_name": "哺乳類ラパマイシン標的タンパク質","gene": "MTOR"},
    {"id": "T009", "name": "EGFR",      "full_name": "上皮成長因子受容体",            "gene": "EGFR"},
    {"id": "T010", "name": "AT1R",      "full_name": "アンジオテンシンII受容体タイプ1","gene": "AGTR1"},
]

DISEASES = [
    {"id": "DIS001", "name": "COVID-19",       "category": "感染症",     "icd10": "U07.1"},
    {"id": "DIS002", "name": "関節リウマチ",   "category": "自己免疫疾患","icd10": "M06.9"},
    {"id": "DIS003", "name": "2型糖尿病",      "category": "代謝疾患",   "icd10": "E11"},
    {"id": "DIS004", "name": "乳がん",         "category": "腫瘍",       "icd10": "C50"},
    {"id": "DIS005", "name": "心不全",         "category": "循環器疾患", "icd10": "I50"},
    {"id": "DIS006", "name": "肺動脈性肺高血圧症","category": "循環器疾患","icd10": "I27.0"},
    {"id": "DIS007", "name": "アルツハイマー病","category": "神経疾患",   "icd10": "G30"},
    {"id": "DIS008", "name": "高血圧",         "category": "循環器疾患", "icd10": "I10"},
    {"id": "DIS009", "name": "大腸がん",       "category": "腫瘍",       "icd10": "C18"},
    {"id": "DIS010", "name": "ARDS",           "category": "呼吸器疾患", "icd10": "J80"},
]

# エッジ: (from_id, to_id, rel_type, properties)
EDGES = [
    # 薬剤 → 標的 (TARGETS_関係)
    ("D001", "T001", "TARGETS",  {"mechanism": "阻害", "affinity_nM": 77,   "evidence": "臨床"}),
    ("D002", "T002", "TARGETS",  {"mechanism": "阻害", "affinity_nM": 300,  "evidence": "臨床"}),
    ("D002", "T005", "TARGETS",  {"mechanism": "阻害", "affinity_nM": 1500, "evidence": "臨床"}),
    ("D003", "T003", "TARGETS",  {"mechanism": "活性化","affinity_nM": 5000, "evidence": "臨床"}),
    ("D004", "T004", "TARGETS",  {"mechanism": "阻害", "affinity_nM": 50,   "evidence": "臨床"}),
    ("D005", "T002", "TARGETS",  {"mechanism": "阻害", "affinity_nM": 4500, "evidence": "臨床"}),
    ("D005", "T005", "TARGETS",  {"mechanism": "阻害", "affinity_nM": 1200, "evidence": "臨床"}),
    ("D006", "T006", "TARGETS",  {"mechanism": "阻害", "affinity_nM": 3.5,  "evidence": "臨床"}),
    ("D007", "T001", "TARGETS",  {"mechanism": "阻害", "affinity_nM": 120,  "evidence": "in_vitro"}),
    ("D007", "T007", "TARGETS",  {"mechanism": "阻害", "affinity_nM": 450,  "evidence": "in_vitro"}),
    ("D008", "T004", "TARGETS",  {"mechanism": "阻害", "affinity_nM": 85,   "evidence": "in_vitro"}),
    ("D008", "T009", "TARGETS",  {"mechanism": "阻害", "affinity_nM": 200,  "evidence": "in_vitro"}),
    ("D009", "T003", "TARGETS",  {"mechanism": "活性化","affinity_nM": 3200, "evidence": "in_silico"}),
    ("D009", "T008", "TARGETS",  {"mechanism": "阻害", "affinity_nM": 780,  "evidence": "in_silico"}),
    ("D010", "T010", "TARGETS",  {"mechanism": "阻害", "affinity_nM": 2.4,  "evidence": "臨床"}),
    # 標的 → 疾患 (ASSOCIATED_WITH)
    ("T001", "DIS001", "ASSOCIATED_WITH", {"pathway": "ウイルス複製",     "confidence": 0.95}),
    ("T002", "DIS002", "ASSOCIATED_WITH", {"pathway": "炎症カスケード",   "confidence": 0.90}),
    ("T003", "DIS003", "ASSOCIATED_WITH", {"pathway": "糖代謝",          "confidence": 0.88}),
    ("T004", "DIS004", "ASSOCIATED_WITH", {"pathway": "DNA複製",         "confidence": 0.92}),
    ("T004", "DIS009", "ASSOCIATED_WITH", {"pathway": "DNA複製",         "confidence": 0.85}),
    ("T005", "DIS005", "ASSOCIATED_WITH", {"pathway": "血小板凝集",      "confidence": 0.70}),
    ("T006", "DIS006", "ASSOCIATED_WITH", {"pathway": "cGMP経路",        "confidence": 0.87}),
    ("T007", "DIS001", "ASSOCIATED_WITH", {"pathway": "ウイルス侵入",    "confidence": 0.98}),
    ("T007", "DIS010", "ASSOCIATED_WITH", {"pathway": "肺保護",          "confidence": 0.75}),
    ("T008", "DIS004", "ASSOCIATED_WITH", {"pathway": "細胞増殖",        "confidence": 0.80}),
    ("T008", "DIS007", "ASSOCIATED_WITH", {"pathway": "オートファジー",   "confidence": 0.65}),
    ("T009", "DIS004", "ASSOCIATED_WITH", {"pathway": "細胞増殖シグナル", "confidence": 0.93}),
    ("T009", "DIS009", "ASSOCIATED_WITH", {"pathway": "細胞増殖シグナル", "confidence": 0.88}),
    ("T010", "DIS008", "ASSOCIATED_WITH", {"pathway": "RAS系",           "confidence": 0.94}),
    ("T010", "DIS005", "ASSOCIATED_WITH", {"pathway": "心臓リモデリング", "confidence": 0.82}),
    # 薬剤 → 疾患 (TREATS / CANDIDATE_FOR)
    ("D001", "DIS001", "TREATS",        {"phase": "承認済", "year": 2020}),
    ("D002", "DIS002", "TREATS",        {"phase": "承認済", "year": 1984}),
    ("D003", "DIS003", "TREATS",        {"phase": "承認済", "year": 1995}),
    ("D004", "DIS004", "TREATS",        {"phase": "承認済", "year": 1974}),
    ("D005", "DIS005", "TREATS",        {"phase": "承認済", "year": 1950}),
    ("D006", "DIS006", "TREATS",        {"phase": "承認済", "year": 2005}),
    ("D010", "DIS008", "TREATS",        {"phase": "承認済", "year": 1996}),
    # ドラッグリパーパシング候補
    ("D003", "DIS004", "CANDIDATE_FOR", {"score": 0.72, "basis": "AMPK-mTOR経路"}),
    ("D005", "DIS009", "CANDIDATE_FOR", {"score": 0.68, "basis": "COX-2炎症抑制"}),
    ("D006", "DIS005", "CANDIDATE_FOR", {"score": 0.61, "basis": "cGMP心保護"}),
    ("D007", "DIS001", "CANDIDATE_FOR", {"score": 0.83, "basis": "RdRp+ACE2二重阻害"}),
    ("D008", "DIS009", "CANDIDATE_FOR", {"score": 0.77, "basis": "TOP2A+EGFR二重阻害"}),
    ("D009", "DIS007", "CANDIDATE_FOR", {"score": 0.59, "basis": "mTORオートファジー誘導"}),
    ("D009", "DIS003", "CANDIDATE_FOR", {"score": 0.74, "basis": "AMPK活性化"}),
    ("D010", "DIS005", "CANDIDATE_FOR", {"score": 0.80, "basis": "AT1R心臓リモデリング抑制"}),
    # 化学的類似性
    ("D002", "D005", "CHEMICALLY_SIMILAR", {"tanimoto": 0.45}),
    ("D004", "D008", "CHEMICALLY_SIMILAR", {"tanimoto": 0.62}),
    ("D001", "D007", "CHEMICALLY_SIMILAR", {"tanimoto": 0.38}),
    ("D003", "D009", "CHEMICALLY_SIMILAR", {"tanimoto": 0.41}),
    # タンパク質間相互作用
    ("T002", "T005", "INTERACTS_WITH", {"interaction_type": "共発現", "score": 0.91}),
    ("T003", "T008", "INTERACTS_WITH", {"interaction_type": "シグナル伝達", "score": 0.85}),
    ("T007", "T010", "INTERACTS_WITH", {"interaction_type": "RAS系クロストーク", "score": 0.72}),
    ("T004", "T009", "INTERACTS_WITH", {"interaction_type": "細胞増殖経路", "score": 0.78}),
]


def setup_database(driver):
    """データベースをクリアし、制約・インデックスを作成"""
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        print("既存データを削除しました")

        for label, prop in [("Drug", "id"), ("Target", "id"), ("Disease", "id")]:
            try:
                session.run(f"CREATE CONSTRAINT FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE")
            except Exception:
                pass
        print("制約を作成しました")


def create_nodes(driver):
    """ノードを作成"""
    with driver.session() as session:
        for d in DRUGS:
            session.run(
                "CREATE (n:Drug {id: $id, name: $name, formula: $formula, type: $type, approved: $approved})",
                **d
            )
        for t in TARGETS:
            session.run(
                "CREATE (n:Target {id: $id, name: $name, full_name: $full_name, gene: $gene})",
                **t
            )
        for dis in DISEASES:
            session.run(
                "CREATE (n:Disease {id: $id, name: $name, category: $category, icd10: $icd10})",
                **dis
            )
    print(f"ノード作成完了: 薬剤{len(DRUGS)}, 標的{len(TARGETS)}, 疾患{len(DISEASES)}")


def create_edges(driver):
    """エッジを作成"""
    with driver.session() as session:
        for src, dst, rel, props in EDGES:
            # ノードラベル推定
            src_label = "Drug" if src.startswith("D") else ("Target" if src.startswith("T") else "Disease")
            dst_label = "Drug" if dst.startswith("D") else ("Target" if dst.startswith("T") else "Disease")

            props_str = ", ".join(f"{k}: ${k}" for k in props)
            query = (
                f"MATCH (a:{src_label} {{id: $src}}), (b:{dst_label} {{id: $dst}}) "
                f"CREATE (a)-[:{rel} {{{props_str}}}]->(b)"
            )
            session.run(query, src=src, dst=dst, **props)

    print(f"エッジ作成完了: {len(EDGES)}本")


def compute_repurposing_scores(driver):
    """ネットワーク構造ベースのドラッグリパーパシングスコアを計算"""
    print("\n===== ドラッグリパーパシング候補スコア =====\n")

    with driver.session() as session:
        # 薬剤→標的→疾患の2ホップパスで候補を探索
        result = session.run("""
            MATCH (d:Drug)-[t:TARGETS]->(target:Target)-[a:ASSOCIATED_WITH]->(dis:Disease)
            WHERE NOT EXISTS { MATCH (d)-[:TREATS]->(dis) }
            WITH d, dis,
                 collect(DISTINCT target.name) AS targets,
                 avg(a.confidence) AS avg_confidence,
                 min(t.affinity_nM) AS best_affinity,
                 count(DISTINCT target) AS path_count
            RETURN d.name AS drug, d.approved AS approved,
                   dis.name AS disease, dis.category AS category,
                   targets, avg_confidence, best_affinity, path_count,
                   (avg_confidence * path_count / (1 + log(best_affinity + 1))) AS network_score
            ORDER BY network_score DESC
            LIMIT 15
        """)

        print(f"{'薬剤':<16} {'疾患':<20} {'経路標的':30} {'スコア':>8}")
        print("-" * 80)
        for r in result:
            marker = "★" if not r["approved"] else "  "
            targets_str = ", ".join(r["targets"])
            print(f"{marker}{r['drug']:<14} {r['disease']:<18} {targets_str:28} {r['network_score']:>8.4f}")

    print("\n★ = 未承認候補化合物")


def print_graph_stats(driver):
    """グラフ統計を表示"""
    with driver.session() as session:
        stats = session.run("""
            MATCH (n) WITH labels(n)[0] AS label, count(*) AS cnt
            RETURN label, cnt ORDER BY label
        """).data()
        rels = session.run("""
            MATCH ()-[r]->() WITH type(r) AS rel, count(*) AS cnt
            RETURN rel, cnt ORDER BY cnt DESC
        """).data()

    print("\n===== グラフ統計 =====")
    for s in stats:
        print(f"  {s['label']}: {s['cnt']}ノード")
    for r in rels:
        print(f"  {r['rel']}: {r['cnt']}エッジ")


if __name__ == "__main__":
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()
        print("Neo4j接続成功！\n")

        setup_database(driver)
        create_nodes(driver)
        create_edges(driver)
        print_graph_stats(driver)
        compute_repurposing_scores(driver)

        print("\nセットアップ完了！")
