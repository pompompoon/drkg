# DRKG Explorer — GNNによるドラッグリパーパシング予測システム

Drug Repurposing Knowledge Graph（創薬ナレッジグラフ）をNeo4j上に構築し、  
GATv2Conv ベースの異種グラフニューラルネットワーク（GNN）で薬剤-疾患間のリンク予測を行うシステムです。

---

## 全体アーキテクチャ

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│   Neo4j     │────▶│ PyG          │────▶│ GATv2Conv       │────▶│ 予測結果     │
│ グラフDB    │     │ HeteroData   │     │ Link Prediction │     │ JSON / UI    │
└─────────────┘     └──────────────┘     └─────────────────┘     └──────────────┘
  setup_drkg_          gnn_predict.py         gnn_predict.py        drkg_explorer
  neo4j.py                                                           .jsx
```

## ナレッジグラフ構造

画像の論文（DRKG / TransE）に基づき、3種のノードと6種のエッジで構成されます。

### ノード

| ノードタイプ | 数 | 特徴量 | 説明 |
|---|---|---|---|
| **Drug（薬剤）** | 10 | タイプone-hot(7) + 承認フラグ(1) = 8次元 | 承認薬7種 + 候補化合物3種 |
| **Target（標的）** | 10 | 学習可能埋め込み 8次元 | タンパク質・受容体（COX-2, ACE2, mTOR等） |
| **Disease（疾患）** | 10 | カテゴリone-hot(7) + noise(1) = 8次元 | COVID-19, 乳がん, アルツハイマー等 |

### エッジ

| エッジタイプ | 方向 | 属性 | 意味 |
|---|---|---|---|
| `TARGETS` | Drug → Target | affinity_nM, mechanism | 薬剤が標的に結合 |
| `ASSOCIATED_WITH` | Target → Disease | confidence, pathway | 標的が疾患に関与 |
| `TREATS` | Drug → Disease | phase, year | 既知の治療関係（正例） |
| `CANDIDATE_FOR` | Drug → Disease | score, basis | リパーパシング候補（予測対象） |
| `CHEMICALLY_SIMILAR` | Drug ↔ Drug | tanimoto | 化学的類似性 |
| `INTERACTS_WITH` | Target ↔ Target | interaction_type | タンパク質間相互作用 |

```
Drug ──TARGETS──▶ Target ──ASSOCIATED_WITH──▶ Disease
 │                  │                            ▲
 │ SIMILAR          │ INTERACTS                  │
 ▼                  ▼                            │
Drug              Target          Drug ──TREATS──┘
                                  Drug ──CANDIDATE_FOR──▶ Disease
```

## GNNモデル詳細

### エンコーダ: Heterogeneous GATv2Conv

```
入力特徴 (8次元)
    │
    ▼
GATv2Conv Layer 1 (heads=4, hidden=32)
    │  → 出力: 32×4 = 128次元
    ▼
ELU + Dropout(0.3)
    │
    ▼
GATv2Conv Layer 2 (heads=1, out=32)
    │  → 出力: 32次元（ノード埋め込み）
    ▼
ノード埋め込み z_dict
```

- `to_hetero()` により、各エッジタイプごとに独立した重みを持つ異種グラフGNNに自動変換
- GATv2Conv はアテンション機構により、重要な隣接ノードの情報を選択的に集約

### デコーダ: MLP + Dot Product

```
z_drug[i]  ──▶ Linear(32→32) ──▶ h_drug
                                      │
                                      ▼
                                  dot product ──▶ スコア ──▶ sigmoid ──▶ 予測確率
                                      ▲
z_disease[j] ──▶ Linear(32→32) ──▶ h_disease
```

### 学習

| 項目 | 設定 |
|---|---|
| 損失関数 | Binary Cross-Entropy with Logits |
| オプティマイザ | Adam (lr=0.005, weight_decay=1e-4) |
| ネガティブサンプリング | 正例と同数のランダムペア |
| エポック数 | 200 |
| 評価指標 | AUC-ROC, Average Precision |

### 予測の仕組み

1. 既知の `TREATS` エッジを正例、ランダムな薬剤-疾患ペアを負例として学習
2. 学習後、`TREATS` に含まれない全ペアのスコアを計算
3. スコア上位の薬剤-疾患ペアが**新規リパーパシング候補**
4. `Drug → Target → Disease` の2ホップ経路が存在する候補は根拠が強い

## ファイル構成

```
drkg-explorer/
├── setup_drkg_neo4j.py    # Neo4jにサンプルデータを投入
├── gnn_predict.py         # GNN学習・予測メインスクリプト
├── drkg_explorer.jsx      # React可視化アプリ
├── gnn_predictions.json   # GNN予測結果（自動生成）
├── best_drkg_gnn.pt       # ベストモデル重み（自動生成）
└── README.md              # 本ファイル
```

## セットアップ・実行手順

### 1. 前提条件

```bash
# Neo4j Desktop または Community Editionが起動済みであること
# Python 3.9+, Anaconda推奨

conda create -n drkg python=3.10
conda activate drkg
```

### 2. 依存パッケージ

```bash
# PyTorch (CUDA or CPU)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
# または CPU版: pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# PyTorch Geometric
pip install torch_geometric

# その他
pip install neo4j scikit-learn pandas numpy
```

### 3. Neo4jにデータ投入

```bash
python setup_drkg_neo4j.py
```

出力例:
```
Neo4j接続成功！
既存データを削除しました
制約を作成しました
ノード作成完了: 薬剤10, 標的10, 疾患10
エッジ作成完了: 48本
===== グラフ統計 =====
  Drug: 10ノード
  Target: 10ノード
  Disease: 10ノード
  ...
```

### 4. GNN学習・予測

```bash
python gnn_predict.py
```

出力例:
```
[STEP 4] 学習開始...
  Epoch    1 | Loss: 0.7124 | AUC: 0.5312 | AP: 0.4205
  Epoch   20 | Loss: 0.4523 | AUC: 0.7845 | AP: 0.6932
  Epoch  200 | Loss: 0.1234 | AUC: 0.9512 | AP: 0.9201 ★ best

[STEP 5] 新規候補予測...
======================================================================
  GNN予測: ドラッグリパーパシング候補 Top 20
======================================================================
Rank 薬剤           疾患               Score  経路  標的
  1. ★候補化合物A   COVID-19           0.9234     ✓  RdRp, ACE2
  2.  バルサルタン   心不全             0.8901     ✓  AT1R
  ...
```

### 5. 可視化

`drkg_explorer.jsx` をClaude Artifactまたは React環境で表示。  
ネットワークグラフと候補一覧の2ビューを切り替え可能。

## 技術的ポイント

### なぜGATv2Convか

- **GATv2** は static attention の制約を解消した dynamic attention 機構を持つ
- 薬剤-標的間の結合親和性の重要度を自動的に学習できる
- `to_hetero()` により、エッジタイプごとの独立したアテンション重みを獲得

### TransEとの関係

画像の論文で紹介されている **TransE** はエンティティ埋め込みを `h + r ≈ t` の関係で学習する手法です。  
本システムでは、より表現力の高いGNNベースの手法を採用していますが、基本的な考え方は共通です:

| | TransE | 本システム (GNN) |
|---|---|---|
| 埋め込み学習 | 翻訳ベース (h+r≈t) | メッセージパッシング + アテンション |
| 関係の表現 | 関係ベクトル r | エッジタイプ別GATv2重み |
| マルチホップ | 直接はできない | グラフ構造で自然に捕捉 |
| 帰納的推論 | 不可（transductive） | ノード特徴量があれば可能 |

### Drug → Target → Disease 経路の意義

GNNスコアが高く、かつ `Drug → Target → Disease` の2ホップ経路が存在する候補は:

1. **ネットワーク構造的根拠**がある（GNNスコア）
2. **生物学的根拠**がある（薬剤が標的に結合 → 標的が疾患に関与）
3. 実験的検証の優先順位付けに活用できる

## 拡張のアイデア

- **TransE/DistMult/RotatE 埋め込みとの組み合わせ**: 初期ノード特徴量にKGE埋め込みを使用
- **GNNExplainer**: 予測根拠の可視化（どのエッジが予測に寄与したか）
- **副作用ノードの追加**: Drug → SideEffect エッジで安全性も考慮
- **臨床試験データの統合**: ClinicalTrials.gov からのフェーズ情報
- **大規模DRKG**: Amazon DRKG (97K+ ノード, 5.8M+ エッジ) への拡張

## ライセンス

研究・学習目的。サンプルデータは架空です。
