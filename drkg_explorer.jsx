import { useState, useEffect, useRef, useCallback } from "react";

const DRUGS = [
  { id: "D001", name: "レムデシビル", type: "抗ウイルス薬", approved: true, formula: "C27H35N6O8P" },
  { id: "D002", name: "イブプロフェン", type: "NSAIDs", approved: true, formula: "C13H18O2" },
  { id: "D003", name: "メトホルミン", type: "糖尿病治療薬", approved: true, formula: "C4H11N5" },
  { id: "D004", name: "ドキソルビシン", type: "抗がん剤", approved: true, formula: "C27H29NO11" },
  { id: "D005", name: "アスピリン", type: "NSAIDs", approved: true, formula: "C9H8O4" },
  { id: "D006", name: "シルデナフィル", type: "PDE5阻害薬", approved: true, formula: "C22H30N6O4S" },
  { id: "D007", name: "候補化合物A", type: "実験薬", approved: false, formula: "C18H22N4O3" },
  { id: "D008", name: "候補化合物B", type: "実験薬", approved: false, formula: "C21H26N2O5" },
  { id: "D009", name: "候補化合物C", type: "実験薬", approved: false, formula: "C15H19N3O4" },
  { id: "D010", name: "バルサルタン", type: "ARB", approved: true, formula: "C24H29N5O3" },
];

const TARGETS = [
  { id: "T001", name: "RdRp", gene: "RDRP" },
  { id: "T002", name: "COX-2", gene: "PTGS2" },
  { id: "T003", name: "AMPK", gene: "PRKAA1" },
  { id: "T004", name: "TOP2A", gene: "TOP2A" },
  { id: "T005", name: "COX-1", gene: "PTGS1" },
  { id: "T006", name: "PDE5", gene: "PDE5A" },
  { id: "T007", name: "ACE2", gene: "ACE2" },
  { id: "T008", name: "mTOR", gene: "MTOR" },
  { id: "T009", name: "EGFR", gene: "EGFR" },
  { id: "T010", name: "AT1R", gene: "AGTR1" },
];

const DISEASES = [
  { id: "DIS001", name: "COVID-19", category: "感染症" },
  { id: "DIS002", name: "関節リウマチ", category: "自己免疫疾患" },
  { id: "DIS003", name: "2型糖尿病", category: "代謝疾患" },
  { id: "DIS004", name: "乳がん", category: "腫瘍" },
  { id: "DIS005", name: "心不全", category: "循環器疾患" },
  { id: "DIS006", name: "肺動脈性肺高血圧症", category: "循環器疾患" },
  { id: "DIS007", name: "アルツハイマー病", category: "神経疾患" },
  { id: "DIS008", name: "高血圧", category: "循環器疾患" },
  { id: "DIS009", name: "大腸がん", category: "腫瘍" },
  { id: "DIS010", name: "ARDS", category: "呼吸器疾患" },
];

const EDGES = [
  { src: "D001", dst: "T001", rel: "TARGETS", affinity: 77 },
  { src: "D002", dst: "T002", rel: "TARGETS", affinity: 300 },
  { src: "D002", dst: "T005", rel: "TARGETS", affinity: 1500 },
  { src: "D003", dst: "T003", rel: "TARGETS", affinity: 5000 },
  { src: "D004", dst: "T004", rel: "TARGETS", affinity: 50 },
  { src: "D005", dst: "T002", rel: "TARGETS", affinity: 4500 },
  { src: "D005", dst: "T005", rel: "TARGETS", affinity: 1200 },
  { src: "D006", dst: "T006", rel: "TARGETS", affinity: 3.5 },
  { src: "D007", dst: "T001", rel: "TARGETS", affinity: 120 },
  { src: "D007", dst: "T007", rel: "TARGETS", affinity: 450 },
  { src: "D008", dst: "T004", rel: "TARGETS", affinity: 85 },
  { src: "D008", dst: "T009", rel: "TARGETS", affinity: 200 },
  { src: "D009", dst: "T003", rel: "TARGETS", affinity: 3200 },
  { src: "D009", dst: "T008", rel: "TARGETS", affinity: 780 },
  { src: "D010", dst: "T010", rel: "TARGETS", affinity: 2.4 },
  { src: "T001", dst: "DIS001", rel: "ASSOC", confidence: 0.95 },
  { src: "T002", dst: "DIS002", rel: "ASSOC", confidence: 0.90 },
  { src: "T003", dst: "DIS003", rel: "ASSOC", confidence: 0.88 },
  { src: "T004", dst: "DIS004", rel: "ASSOC", confidence: 0.92 },
  { src: "T004", dst: "DIS009", rel: "ASSOC", confidence: 0.85 },
  { src: "T005", dst: "DIS005", rel: "ASSOC", confidence: 0.70 },
  { src: "T006", dst: "DIS006", rel: "ASSOC", confidence: 0.87 },
  { src: "T007", dst: "DIS001", rel: "ASSOC", confidence: 0.98 },
  { src: "T007", dst: "DIS010", rel: "ASSOC", confidence: 0.75 },
  { src: "T008", dst: "DIS004", rel: "ASSOC", confidence: 0.80 },
  { src: "T008", dst: "DIS007", rel: "ASSOC", confidence: 0.65 },
  { src: "T009", dst: "DIS004", rel: "ASSOC", confidence: 0.93 },
  { src: "T009", dst: "DIS009", rel: "ASSOC", confidence: 0.88 },
  { src: "T010", dst: "DIS008", rel: "ASSOC", confidence: 0.94 },
  { src: "T010", dst: "DIS005", rel: "ASSOC", confidence: 0.82 },
  { src: "D001", dst: "DIS001", rel: "TREATS" },
  { src: "D002", dst: "DIS002", rel: "TREATS" },
  { src: "D003", dst: "DIS003", rel: "TREATS" },
  { src: "D004", dst: "DIS004", rel: "TREATS" },
  { src: "D005", dst: "DIS005", rel: "TREATS" },
  { src: "D006", dst: "DIS006", rel: "TREATS" },
  { src: "D010", dst: "DIS008", rel: "TREATS" },
  { src: "D007", dst: "DIS001", rel: "CANDIDATE", score: 0.83 },
  { src: "D008", dst: "DIS009", rel: "CANDIDATE", score: 0.77 },
  { src: "D009", dst: "DIS007", rel: "CANDIDATE", score: 0.59 },
  { src: "D009", dst: "DIS003", rel: "CANDIDATE", score: 0.74 },
  { src: "D003", dst: "DIS004", rel: "CANDIDATE", score: 0.72 },
  { src: "D005", dst: "DIS009", rel: "CANDIDATE", score: 0.68 },
  { src: "D006", dst: "DIS005", rel: "CANDIDATE", score: 0.61 },
  { src: "D010", dst: "DIS005", rel: "CANDIDATE", score: 0.80 },
];

const allNodes = [
  ...DRUGS.map(d => ({ ...d, nodeType: "drug" })),
  ...TARGETS.map(t => ({ ...t, nodeType: "target" })),
  ...DISEASES.map(d => ({ ...d, nodeType: "disease" })),
];

const nodeMap = {};
allNodes.forEach(n => { nodeMap[n.id] = n; });

const COLORS = {
  drug: { fill: "#0ea5e9", stroke: "#0284c7", text: "#f0f9ff", bg: "rgba(14,165,233,0.08)" },
  drugExp: { fill: "#f59e0b", stroke: "#d97706", text: "#fffbeb" },
  target: { fill: "#8b5cf6", stroke: "#7c3aed", text: "#f5f3ff", bg: "rgba(139,92,246,0.08)" },
  disease: { fill: "#ef4444", stroke: "#dc2626", text: "#fef2f2", bg: "rgba(239,68,68,0.08)" },
  candidate: "#f59e0b",
  treats: "#22c55e",
  targets: "#8b5cf6",
  assoc: "#64748b",
};

function forceLayout(nodes, edges, w, h) {
  const pos = {};
  const typeGroups = { drug: [], target: [], disease: [] };
  nodes.forEach(n => typeGroups[n.nodeType]?.push(n.id));

  // Initial placement in columns
  const col = { drug: w * 0.15, target: w * 0.5, disease: w * 0.85 };
  Object.entries(typeGroups).forEach(([type, ids]) => {
    ids.forEach((id, i) => {
      const y = (h * 0.1) + (i / Math.max(ids.length - 1, 1)) * (h * 0.8);
      pos[id] = { x: col[type] + (Math.random() - 0.5) * 40, y: y + (Math.random() - 0.5) * 20 };
    });
  });

  // Simple force simulation
  for (let iter = 0; iter < 80; iter++) {
    const forces = {};
    nodes.forEach(n => { forces[n.id] = { x: 0, y: 0 }; });

    // Repulsion
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i].id, b = nodes[j].id;
        let dx = pos[a].x - pos[b].x, dy = pos[a].y - pos[b].y;
        const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
        const f = 2000 / (dist * dist);
        forces[a].x += (dx / dist) * f;
        forces[a].y += (dy / dist) * f;
        forces[b].x -= (dx / dist) * f;
        forces[b].y -= (dy / dist) * f;
      }
    }

    // Attraction along edges
    edges.forEach(e => {
      if (!pos[e.src] || !pos[e.dst]) return;
      let dx = pos[e.dst].x - pos[e.src].x, dy = pos[e.dst].y - pos[e.src].y;
      const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
      const f = (dist - 120) * 0.01;
      forces[e.src].x += (dx / dist) * f;
      forces[e.src].y += (dy / dist) * f;
      forces[e.dst].x -= (dx / dist) * f;
      forces[e.dst].y -= (dy / dist) * f;
    });

    // Column gravity
    nodes.forEach(n => {
      const cx = col[n.nodeType];
      forces[n.id].x += (cx - pos[n.id].x) * 0.05;
      forces[n.id].y += (h / 2 - pos[n.id].y) * 0.002;
    });

    const dt = Math.max(0.3, 1 - iter / 80);
    nodes.forEach(n => {
      pos[n.id].x += forces[n.id].x * dt;
      pos[n.id].y += forces[n.id].y * dt;
      pos[n.id].x = Math.max(60, Math.min(w - 60, pos[n.id].x));
      pos[n.id].y = Math.max(30, Math.min(h - 30, pos[n.id].y));
    });
  }
  return pos;
}

function computeCandidates() {
  const candidates = EDGES.filter(e => e.rel === "CANDIDATE").map(e => {
    const drug = nodeMap[e.src];
    const disease = nodeMap[e.dst];
    const pathTargets = EDGES.filter(x => x.rel === "TARGETS" && x.src === e.src)
      .map(x => nodeMap[x.dst]?.name).filter(Boolean);
    return { drug: drug.name, drugId: e.src, disease: disease.name, diseaseId: e.dst, score: e.score, approved: drug.approved, targets: pathTargets };
  }).sort((a, b) => b.score - a.score);
  return candidates;
}

export default function App() {
  const svgRef = useRef(null);
  const [positions, setPositions] = useState({});
  const [selected, setSelected] = useState(null);
  const [hoveredEdge, setHoveredEdge] = useState(null);
  const [view, setView] = useState("graph"); // graph | candidates
  const [filterType, setFilterType] = useState("all");
  const [filterDisease, setFilterDisease] = useState("all");
  const W = 900, H = 560;

  useEffect(() => {
    setPositions(forceLayout(allNodes, EDGES, W, H));
  }, []);

  const candidates = computeCandidates();

  const filteredCandidates = candidates.filter(c => {
    if (filterDisease !== "all" && c.diseaseId !== filterDisease) return false;
    return true;
  });

  const getNodeColor = (n) => {
    if (n.nodeType === "drug" && !n.approved) return COLORS.drugExp;
    return COLORS[n.nodeType];
  };

  const getNodeRadius = (n) => {
    if (n.nodeType === "target") return 18;
    return 22;
  };

  const isConnected = (nodeId) => {
    if (!selected) return true;
    if (nodeId === selected) return true;
    return EDGES.some(e => (e.src === selected && e.dst === nodeId) || (e.dst === selected && e.src === nodeId));
  };

  const isEdgeHighlighted = (e) => {
    if (!selected) return true;
    return e.src === selected || e.dst === selected;
  };

  const edgeColor = (e) => {
    if (e.rel === "CANDIDATE") return COLORS.candidate;
    if (e.rel === "TREATS") return COLORS.treats;
    if (e.rel === "TARGETS") return COLORS.targets;
    return COLORS.assoc;
  };

  const selectedNode = selected ? nodeMap[selected] : null;
  const connectedEdges = selected ? EDGES.filter(e => e.src === selected || e.dst === selected) : [];

  return (
    <div style={{ fontFamily: "'Noto Sans JP', 'Segoe UI', sans-serif", background: "#0c0f1a", color: "#e2e8f0", minHeight: "100vh", padding: 0 }}>
      <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet" />

      {/* Header */}
      <div style={{ background: "linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)", borderBottom: "1px solid rgba(139,92,246,0.3)", padding: "16px 24px", display: "flex", alignItems: "center", gap: 16 }}>
        <div style={{ width: 36, height: 36, borderRadius: 8, background: "linear-gradient(135deg, #8b5cf6, #06b6d4)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>⚗</div>
        <div>
          <h1 style={{ margin: 0, fontSize: 18, fontWeight: 700, letterSpacing: 1 }}>DRKG Explorer</h1>
          <p style={{ margin: 0, fontSize: 11, color: "#94a3b8", letterSpacing: 0.5 }}>Drug Repurposing Knowledge Graph</p>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 4 }}>
          {["graph", "candidates"].map(v => (
            <button key={v} onClick={() => setView(v)} style={{
              padding: "6px 16px", borderRadius: 6, border: "1px solid", fontSize: 12, fontWeight: 600, cursor: "pointer", transition: "all 0.2s",
              background: view === v ? "rgba(139,92,246,0.2)" : "transparent",
              borderColor: view === v ? "#8b5cf6" : "#334155",
              color: view === v ? "#c4b5fd" : "#94a3b8",
            }}>
              {v === "graph" ? "ネットワーク" : "候補一覧"}
            </button>
          ))}
        </div>
      </div>

      {view === "graph" ? (
        <div style={{ display: "flex", height: "calc(100vh - 73px)" }}>
          {/* Graph */}
          <div style={{ flex: 1, position: "relative" }}>
            <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "100%", display: "block" }}>
              <defs>
                <marker id="arrow-candidate" viewBox="0 0 10 7" refX="10" refY="3.5" markerWidth="8" markerHeight="6" orient="auto"><path d={`M 0 0 L 10 3.5 L 0 7 z`} fill={COLORS.candidate} opacity={0.6} /></marker>
                <marker id="arrow-treats" viewBox="0 0 10 7" refX="10" refY="3.5" markerWidth="8" markerHeight="6" orient="auto"><path d={`M 0 0 L 10 3.5 L 0 7 z`} fill={COLORS.treats} opacity={0.6} /></marker>
                <filter id="glow"><feGaussianBlur stdDeviation="3" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
              </defs>

              {/* Column labels */}
              <text x={W * 0.15} y={20} textAnchor="middle" fill="#64748b" fontSize={11} fontWeight={600}>薬剤 (Drug)</text>
              <text x={W * 0.5} y={20} textAnchor="middle" fill="#64748b" fontSize={11} fontWeight={600}>標的 (Target)</text>
              <text x={W * 0.85} y={20} textAnchor="middle" fill="#64748b" fontSize={11} fontWeight={600}>疾患 (Disease)</text>

              {/* Edges */}
              {EDGES.map((e, i) => {
                const p1 = positions[e.src], p2 = positions[e.dst];
                if (!p1 || !p2) return null;
                const hi = isEdgeHighlighted(e);
                const isDashed = e.rel === "CANDIDATE";
                const r1 = getNodeRadius(nodeMap[e.src]);
                const r2 = getNodeRadius(nodeMap[e.dst]);
                const dx = p2.x - p1.x, dy = p2.y - p1.y;
                const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                const x1 = p1.x + (dx / dist) * r1, y1 = p1.y + (dy / dist) * r1;
                const x2 = p2.x - (dx / dist) * r2, y2 = p2.y - (dy / dist) * r2;
                const marker = (e.rel === "CANDIDATE" || e.rel === "TREATS") ? `url(#arrow-${e.rel.toLowerCase()})` : undefined;
                return (
                  <line key={i} x1={x1} y1={y1} x2={x2} y2={y2}
                    stroke={edgeColor(e)} strokeWidth={isDashed ? 1.5 : 1}
                    strokeDasharray={isDashed ? "5,4" : undefined}
                    opacity={hi ? (isDashed ? 0.7 : 0.35) : 0.06}
                    markerEnd={marker}
                    style={{ transition: "opacity 0.3s" }}
                  />
                );
              })}

              {/* Nodes */}
              {allNodes.map(n => {
                const p = positions[n.id];
                if (!p) return null;
                const c = getNodeColor(n);
                const r = getNodeRadius(n);
                const conn = isConnected(n.id);
                const isSel = selected === n.id;
                return (
                  <g key={n.id} onClick={() => setSelected(isSel ? null : n.id)}
                    style={{ cursor: "pointer", transition: "opacity 0.3s" }}
                    opacity={conn ? 1 : 0.15}>
                    {isSel && <circle cx={p.x} cy={p.y} r={r + 5} fill="none" stroke={c.fill} strokeWidth={2} opacity={0.5} filter="url(#glow)" />}
                    <circle cx={p.x} cy={p.y} r={r} fill={c.fill} stroke={c.stroke} strokeWidth={isSel ? 2.5 : 1.5} />
                    <text x={p.x} y={p.y + 1} textAnchor="middle" dominantBaseline="central" fill={c.text} fontSize={n.nodeType === "target" ? 8 : 7} fontWeight={600}>
                      {n.name.length > 7 ? n.name.slice(0, 6) + "…" : n.name}
                    </text>
                    {n.nodeType === "drug" && !n.approved && (
                      <text x={p.x} y={p.y - r - 4} textAnchor="middle" fill="#fbbf24" fontSize={8}>★</text>
                    )}
                  </g>
                );
              })}
            </svg>

            {/* Legend */}
            <div style={{ position: "absolute", bottom: 12, left: 12, display: "flex", gap: 12, fontSize: 10, color: "#94a3b8" }}>
              {[
                { color: COLORS.drug.fill, label: "承認薬" },
                { color: COLORS.drugExp.fill, label: "候補化合物 ★" },
                { color: COLORS.target.fill, label: "標的" },
                { color: COLORS.disease.fill, label: "疾患" },
              ].map(l => (
                <span key={l.label} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: l.color, display: "inline-block" }} />
                  {l.label}
                </span>
              ))}
              <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <span style={{ width: 16, borderTop: "2px dashed #f59e0b", display: "inline-block" }} />
                候補関係
              </span>
              <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <span style={{ width: 16, borderTop: "2px solid #22c55e", display: "inline-block" }} />
                治療関係
              </span>
            </div>
          </div>

          {/* Detail Panel */}
          <div style={{ width: 280, background: "#111827", borderLeft: "1px solid #1e293b", padding: 16, overflowY: "auto", fontSize: 12 }}>
            {selectedNode ? (
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                  <div style={{ width: 10, height: 10, borderRadius: "50%", background: getNodeColor(selectedNode).fill }} />
                  <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700 }}>{selectedNode.name}</h3>
                </div>
                <div style={{ background: "#1e293b", borderRadius: 8, padding: 10, marginBottom: 12 }}>
                  {selectedNode.nodeType === "drug" && <>
                    <div style={{ color: "#94a3b8", marginBottom: 4 }}>タイプ: <span style={{ color: "#e2e8f0" }}>{selectedNode.type}</span></div>
                    <div style={{ color: "#94a3b8", marginBottom: 4 }}>化学式: <span style={{ color: "#e2e8f0", fontFamily: "JetBrains Mono" }}>{selectedNode.formula}</span></div>
                    <div style={{ color: "#94a3b8" }}>状態: <span style={{ color: selectedNode.approved ? "#22c55e" : "#f59e0b" }}>{selectedNode.approved ? "承認済" : "未承認"}</span></div>
                  </>}
                  {selectedNode.nodeType === "target" && <>
                    <div style={{ color: "#94a3b8", marginBottom: 4 }}>遺伝子: <span style={{ color: "#e2e8f0", fontFamily: "JetBrains Mono" }}>{selectedNode.gene}</span></div>
                    <div style={{ color: "#94a3b8" }}>正式名: <span style={{ color: "#e2e8f0" }}>{selectedNode.full_name || selectedNode.name}</span></div>
                  </>}
                  {selectedNode.nodeType === "disease" && <>
                    <div style={{ color: "#94a3b8" }}>分類: <span style={{ color: "#e2e8f0" }}>{selectedNode.category}</span></div>
                  </>}
                </div>
                <h4 style={{ fontSize: 12, color: "#94a3b8", marginBottom: 6 }}>接続エッジ ({connectedEdges.length})</h4>
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  {connectedEdges.map((e, i) => {
                    const other = e.src === selected ? nodeMap[e.dst] : nodeMap[e.src];
                    return (
                      <div key={i} style={{ background: "#0f172a", borderRadius: 6, padding: "6px 8px", display: "flex", justifyContent: "space-between", alignItems: "center" }}
                        onClick={() => setSelected(other.id)}>
                        <div>
                          <span style={{ color: edgeColor(e), fontSize: 10, fontWeight: 600 }}>{e.rel}</span>
                          <span style={{ color: "#cbd5e1", marginLeft: 6 }}>{other.name}</span>
                        </div>
                        {e.score && <span style={{ color: "#fbbf24", fontFamily: "JetBrains Mono", fontSize: 11 }}>{e.score.toFixed(2)}</span>}
                        {e.affinity && <span style={{ color: "#a78bfa", fontFamily: "JetBrains Mono", fontSize: 10 }}>{e.affinity}nM</span>}
                        {e.confidence && <span style={{ color: "#64748b", fontFamily: "JetBrains Mono", fontSize: 10 }}>{(e.confidence * 100).toFixed(0)}%</span>}
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div style={{ color: "#64748b", textAlign: "center", marginTop: 60 }}>
                <div style={{ fontSize: 32, marginBottom: 8 }}>⚗</div>
                <p>ノードをクリックして<br />詳細を表示</p>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Candidates Table View */
        <div style={{ padding: 24, maxWidth: 900, margin: "0 auto" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
            <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>ドラッグリパーパシング候補</h2>
            <select value={filterDisease} onChange={e => setFilterDisease(e.target.value)}
              style={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 6, color: "#e2e8f0", padding: "4px 8px", fontSize: 12 }}>
              <option value="all">全疾患</option>
              {DISEASES.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {filteredCandidates.map((c, i) => (
              <div key={i} style={{
                background: "linear-gradient(135deg, #111827, #1e1b4b20)",
                border: "1px solid #1e293b", borderRadius: 10, padding: 16,
                display: "flex", alignItems: "center", gap: 16,
              }}>
                <div style={{
                  width: 40, height: 40, borderRadius: 8,
                  background: `linear-gradient(135deg, ${c.approved ? "#0ea5e920" : "#f59e0b20"}, transparent)`,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  border: `1px solid ${c.approved ? "#0ea5e940" : "#f59e0b40"}`,
                  fontSize: 11, fontWeight: 700, color: c.approved ? "#38bdf8" : "#fbbf24",
                }}>
                  #{i + 1}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 700, fontSize: 14 }}>{c.drug}</span>
                    <span style={{ color: "#64748b" }}>→</span>
                    <span style={{ color: "#f87171", fontWeight: 600, fontSize: 14 }}>{c.disease}</span>
                    {!c.approved && <span style={{ background: "#f59e0b20", color: "#fbbf24", padding: "1px 6px", borderRadius: 4, fontSize: 9, fontWeight: 600 }}>新規</span>}
                  </div>
                  <div style={{ color: "#94a3b8", fontSize: 11 }}>
                    経路標的: {c.targets.join(", ")}
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{
                    fontSize: 20, fontWeight: 700, fontFamily: "JetBrains Mono",
                    color: c.score >= 0.8 ? "#22c55e" : c.score >= 0.65 ? "#eab308" : "#ef4444",
                  }}>
                    {c.score.toFixed(2)}
                  </div>
                  <div style={{ fontSize: 9, color: "#64748b" }}>network score</div>
                </div>
                <div style={{ width: 60, height: 6, background: "#1e293b", borderRadius: 3, overflow: "hidden" }}>
                  <div style={{
                    width: `${c.score * 100}%`, height: "100%", borderRadius: 3,
                    background: c.score >= 0.8 ? "#22c55e" : c.score >= 0.65 ? "#eab308" : "#ef4444",
                  }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
