import { useState, useEffect, useCallback } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, CartesianGrid, Legend,
} from "recharts";
import "./App.css";
import {
  analyzeCommitDiff, fetchModelInfo, fetchMetrics, checkHealth,
  type Prediction, type ModelInfo, type MetricsRecord,
} from "./api";

// ─────────────────────────────────────────────
// Sample diffs for quick testing
// ─────────────────────────────────────────────
const SAMPLE_HIGH = `diff --git a/src/components/Dashboard.tsx b/src/components/Dashboard.tsx
index abc..def 100644
--- a/src/components/Dashboard.tsx
+++ b/src/components/Dashboard.tsx
@@ -1,5 +1,60 @@
+import React, { useEffect, useState } from 'react';
+import { fetchData } from '../api/data';
+import { Chart } from './Chart';
+import { Table } from './Table';
+import { Filter } from './Filter';
+import { Sidebar } from './Sidebar';
+import lodash from 'lodash';
+
+const Dashboard = () => {
+  const [data, setData] = useState([]);
+  const [filter, setFilter] = useState('');
+  const [loading, setLoading] = useState(false);
+  const [error, setError] = useState(null);
+  const [page, setPage] = useState(0);
+  useEffect(() => {
+    setLoading(true);
+    fetchData(filter).then(setData).catch(setError);
+    console.log('fetching data', filter);
+    console.log('page', page);
+  });
+  const Inner = () => <div>{data.map(d => <span key={d.id}>{d.name}</span>)}</div>;
+  return (
+    <div>
+      <Filter onChange={(v) => setFilter(v)} />
+      <Inner />
+      {data.map(d => <Chart key={d.id} data={d} onSelect={(id) => setPage(id)} />)}
+    </div>
+  );
+};`;

const SAMPLE_LOW = `diff --git a/src/utils/format.ts b/src/utils/format.ts
index abc..def 100644
--- a/src/utils/format.ts
+++ b/src/utils/format.ts
@@ -1,3 +1,8 @@
+export function formatDate(ts: number): string {
+  return new Date(ts).toLocaleDateString();
+}
+
+export function formatMs(ms: number): string {
+  return ms < 1000 ? \`\${ms}ms\` : \`\${(ms/1000).toFixed(2)}s\`;
+}`;

// ─────────────────────────────────────────────
// Sub-pages
// ─────────────────────────────────────────────

function AnalyzePage() {
  const [diff, setDiff]       = useState("");
  const [repo, setRepo]       = useState("");
  const [hash, setHash]       = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult]   = useState<Prediction | null>(null);
  const [error, setError]     = useState<string | null>(null);

  const run = useCallback(async () => {
    if (!diff.trim()) return;
    setLoading(true); setError(null); setResult(null);
    try {
      const r = await analyzeCommitDiff(diff, repo || undefined, hash || undefined);
      setResult(r);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [diff, repo, hash]);

  const maxShap = result ? Math.max(...result.shap_top5.map(s => Math.abs(s.shap_value))) : 1;

  return (
    <>
      <div className="page-header">
        <h2>Commit Analyzer</h2>
        <p>Paste a git diff to predict regression probability</p>
      </div>

      <div className="card">
        <div className="card-title">Commit Details (optional)</div>
        <div className="input-row">
          <input type="text" placeholder="Repository name  e.g. my-app" value={repo} onChange={e => setRepo(e.target.value)} />
          <input type="text" placeholder="Commit hash  e.g. abc1234" value={hash} onChange={e => setHash(e.target.value)} />
        </div>
        <div className="card-title">Git Diff</div>
        <textarea rows={12} placeholder="Paste git diff here (output of `git show --no-color HEAD`)" value={diff} onChange={e => setDiff(e.target.value)} />
        <div style={{ display: "flex", gap: 10, marginTop: 14 }}>
          <button className="btn btn-primary" onClick={run} disabled={loading || !diff.trim()}>
            {loading ? <><span className="spinner" /> Analyzing…</> : "Analyze Commit"}
          </button>
          <button className="btn btn-ghost" onClick={() => { setDiff(SAMPLE_HIGH); setRepo("demo-app"); setHash("a1b2c3d"); }}>
            Load High-Risk Sample
          </button>
          <button className="btn btn-ghost" onClick={() => { setDiff(SAMPLE_LOW); setRepo("demo-app"); setHash("e4f5g6h"); }}>
            Load Low-Risk Sample
          </button>
        </div>
        {error && <div className="error-box">Error: {error}</div>}
      </div>

      {result && (
        <>
          {/* Risk summary */}
          <div className="card">
            <div className="card-title">Prediction Result</div>
            <div style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: 16 }}>
              <span className={`risk-badge risk-${result.risk_level}`}>
                {result.risk_level === "high" ? "🔴" : result.risk_level === "medium" ? "🟡" : "🟢"}
                &nbsp;{result.risk_level.toUpperCase()} RISK
              </span>
              <span style={{ color: "#9ca3af", fontSize: 13 }}>
                {result.is_regression === 1 ? "⚠ Regression predicted" : "✓ No regression predicted"}
              </span>
              {result.commit_hash && <span style={{ fontSize: 12, color: "#4b5563", fontFamily: "monospace" }}>{result.commit_hash}</span>}
            </div>
            <div className="prob-bar-wrap">
              <div style={{ fontSize: 13, color: "#9ca3af", marginBottom: 6 }}>
                Regression Probability: <b style={{ color: "#f1f5f9" }}>{(result.regression_probability * 100).toFixed(1)}%</b>
              </div>
              <div className="prob-bar-track">
                <div
                  className={`prob-bar-fill prob-bar-${result.risk_level}`}
                  style={{ width: `${result.regression_probability * 100}%` }}
                />
              </div>
              <div className="prob-label"><span>0%</span><span>50%</span><span>100%</span></div>
            </div>
          </div>

          {/* SHAP explanation */}
          <div className="card">
            <div className="card-title">Why? — Top Contributing Features (SHAP)</div>
            <div style={{ fontSize: 12, color: "#4b5563", marginBottom: 14 }}>
              Red = pushes toward regression &nbsp;|&nbsp; Green = reduces regression risk
            </div>
            {result.shap_top5.map(s => {
              const pct = Math.abs(s.shap_value) / maxShap * 48;
              return (
                <div className="shap-row" key={s.feature}>
                  <div className="shap-name">{s.feature}</div>
                  <div className="shap-track">
                    <div style={{ position: "absolute", top: 0, bottom: 0, left: "50%", width: 1, background: "#3d4265" }} />
                    {s.shap_value >= 0
                      ? <div className="shap-bar shap-pos" style={{ width: `${pct}%` }} />
                      : <div className="shap-bar shap-neg" style={{ width: `${pct}%` }} />}
                  </div>
                  <div className="shap-val">{s.shap_value > 0 ? "+" : ""}{s.shap_value.toFixed(3)}</div>
                </div>
              );
            })}
          </div>

          {/* Feature values used */}
          <div className="card">
            <div className="card-title">Extracted Features</div>
            <div className="chip-grid">
              {Object.entries(result.features_used).filter(([, v]) => v !== 0).map(([k, v]) => (
                <span className="chip" key={k}>{k}: <b>{v}</b></span>
              ))}
              {Object.values(result.features_used).every(v => v === 0) && (
                <span style={{ color: "#4b5563", fontSize: 13 }}>All features are zero for this diff.</span>
              )}
            </div>
          </div>
        </>
      )}
    </>
  );
}

// ─────────────────────────────────────────────
function MetricsPage() {
  const [data, setData]     = useState<MetricsRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const r = await fetchMetrics();
      setData(r.records);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); const t = setInterval(load, 10000); return () => clearInterval(t); }, [load]);

  // Aggregate vitals across sessions for chart
  const vitalNames = ["LCP", "FID", "CLS", "FCP", "TTFB"] as const;
  const latestVitals: Record<string, { value: number; rating: string }> = {};
  if (data.length > 0) {
    data[0].webVitals.forEach(v => { latestVitals[v.name] = { value: v.value, rating: v.rating }; });
  }

  const sessionChartData = data.slice(0, 10).reverse().map((r, i) => {
    const obj: Record<string, number | string> = { session: `S${i + 1}` };
    r.webVitals.forEach(v => { obj[v.name] = v.value; });
    return obj;
  });

  const renderChartData = data.length > 0
    ? data[0].componentRenders
        .sort((a, b) => b.totalRenderTime - a.totalRenderTime)
        .slice(0, 8)
        .map(r => ({ name: r.componentName, totalMs: Math.round(r.totalRenderTime * 10) / 10, renders: r.renderCount }))
    : [];

  if (loading) return <div className="empty"><div className="spinner" style={{ width: 28, height: 28, margin: "auto" }} /></div>;

  return (
    <>
      <div className="page-header">
        <h2>Live Metrics</h2>
        <p>Core Web Vitals and component render data from the monitoring SDK</p>
      </div>

      {error && <div className="error-box">Could not reach backend: {error}</div>}

      {data.length === 0 ? (
        <div className="card">
          <div className="empty">
            <div className="empty-icon">📡</div>
            No metrics received yet.<br />
            Add <code style={{ color: "#7c6af7" }}>PerfSense.init(&#123; endpoint: "http://localhost:3001" &#125;)</code> to your React app.
          </div>
        </div>
      ) : (
        <>
          {/* Latest vitals */}
          <div className="card">
            <div className="card-title">Latest Session — Core Web Vitals</div>
            <div className="vitals-row">
              {vitalNames.map(name => {
                const v = latestVitals[name];
                if (!v) return null;
                const cls = `vital-${v.rating === "good" ? "good" : v.rating === "needs-improvement" ? "needs" : "poor"}`;
                const unit = name === "CLS" ? "" : "ms";
                return (
                  <div className="vital-pill" key={name}>
                    <div className="vital-name">{name}</div>
                    <div className={`vital-value ${cls}`}>{name === "CLS" ? v.value.toFixed(3) : Math.round(v.value)}</div>
                    <div className="vital-unit">{unit} · {v.rating}</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Component render times */}
          {renderChartData.length > 0 && (
            <div className="card">
              <div className="card-title">Component Render Times (ms) — Latest Session</div>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={renderChartData} margin={{ left: -10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2d3148" />
                  <XAxis dataKey="name" tick={{ fill: "#6b7280", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: "#1a1d27", border: "1px solid #2d3148", borderRadius: 8 }} />
                  <Bar dataKey="totalMs" fill="#7c6af7" radius={[4, 4, 0, 0]} name="Total ms" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* LCP / FCP trend */}
          {sessionChartData.length > 1 && (
            <div className="card">
              <div className="card-title">LCP & FCP Trend Across Sessions</div>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={sessionChartData} margin={{ left: -10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2d3148" />
                  <XAxis dataKey="session" tick={{ fill: "#6b7280", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: "#1a1d27", border: "1px solid #2d3148", borderRadius: 8 }} />
                  <Legend wrapperStyle={{ fontSize: 12, color: "#9ca3af" }} />
                  <Line type="monotone" dataKey="LCP" stroke="#7c6af7" dot={false} strokeWidth={2} />
                  <Line type="monotone" dataKey="FCP" stroke="#22c55e" dot={false} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Sessions table */}
          <div className="card">
            <div className="card-title">Recent Sessions ({data.length})</div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Session</th>
                    <th>URL</th>
                    <th>LCP</th>
                    <th>CLS</th>
                    <th>FID</th>
                    <th>Components</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map(r => {
                    const lcp = r.webVitals.find(v => v.name === "LCP");
                    const cls = r.webVitals.find(v => v.name === "CLS");
                    const fid = r.webVitals.find(v => v.name === "FID");
                    return (
                      <tr key={r.id}>
                        <td style={{ fontFamily: "monospace", fontSize: 11, color: "#4b5563" }}>{new Date(r.received).toLocaleTimeString()}</td>
                        <td style={{ fontFamily: "monospace", fontSize: 11 }}>{r.sessionId.slice(0, 14)}</td>
                        <td style={{ maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontSize: 12, color: "#6b7280" }}>{r.url}</td>
                        <td>{lcp ? `${Math.round(lcp.value)}ms` : "—"}</td>
                        <td>{cls ? cls.value.toFixed(3) : "—"}</td>
                        <td>{fid ? `${Math.round(fid.value)}ms` : "—"}</td>
                        <td>{r.componentRenders.length}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </>
  );
}

// ─────────────────────────────────────────────
function ModelPage() {
  const [info, setInfo]   = useState<ModelInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchModelInfo()
      .then(setInfo)
      .catch(e => setError(e.message));
  }, []);

  return (
    <>
      <div className="page-header">
        <h2>Model Info</h2>
        <p>XGBoost model trained on 960 commits from 8 open-source React repositories</p>
      </div>

      {error && <div className="error-box">{error}</div>}

      {info && (
        <>
          <div className="card">
            <div className="card-title">Test Set Performance</div>
            <div className="grid-4">
              <div className="stat-tile">
                <div className="stat-value" style={{ color: "#7c6af7" }}>{info.test_f1 != null ? (info.test_f1 * 100).toFixed(1) + "%" : "—"}</div>
                <div className="stat-label">F1 Score</div>
                <div className="stat-sub">Primary metric</div>
              </div>
              <div className="stat-tile">
                <div className="stat-value" style={{ color: "#22c55e" }}>{info.test_auc != null ? (info.test_auc * 100).toFixed(1) + "%" : "—"}</div>
                <div className="stat-label">AUC-ROC</div>
              </div>
              <div className="stat-tile">
                <div className="stat-value">{info.test_accuracy != null ? (info.test_accuracy * 100).toFixed(1) + "%" : "—"}</div>
                <div className="stat-label">Accuracy</div>
              </div>
              <div className="stat-tile">
                <div className="stat-value">{info.feature_count}</div>
                <div className="stat-label">Features</div>
                <div className="stat-sub">25 used in model</div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-title">Training Configuration</div>
            <div className="grid-2">
              <div>
                <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 10 }}>Dataset</div>
                <div className="chip-grid">
                  <span className="chip">Commits: <b>960</b></span>
                  <span className="chip">Repos: <b>8</b></span>
                  <span className="chip">Regression rate: <b>14.7%</b></span>
                  <span className="chip">Split: <b>70/10/20</b></span>
                  <span className="chip">SMOTE: <b>train only</b></span>
                </div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 10 }}>Best XGBoost Params</div>
                <div className="chip-grid">
                  {info.best_params && Object.entries(info.best_params).map(([k, v]) => (
                    <span className="chip" key={k}>{k}: <b>{String(v)}</b></span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-title">Feature List ({info.features.length})</div>
            <div className="chip-grid">
              {info.features.map(f => <span className="chip" key={f}>{f}</span>)}
            </div>
          </div>

          <div className="card">
            <div className="card-title">Cross-Repository Validation</div>
            <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 14 }}>
              Leave-one-repo-out F1 scores — confirms generalization across unseen codebases
            </div>
            <div className="grid-4">
              {[
                ["ant-design-pro", 1.000], ["discourse", 1.000],
                ["excalidraw", 0.946],     ["grafana", 0.923],
                ["joplin", 0.833],         ["metabase", 0.898],
                ["react-admin", 0.923],    ["strapi", 0.972],
              ].map(([repo, f1]) => (
                <div className="stat-tile" key={String(repo)}>
                  <div className="stat-value" style={{ fontSize: 22, color: Number(f1) >= 0.95 ? "#4ade80" : Number(f1) >= 0.90 ? "#fbbf24" : "#f87171" }}>
                    {(Number(f1) * 100).toFixed(1)}%
                  </div>
                  <div className="stat-label" style={{ fontSize: 11 }}>{repo}</div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </>
  );
}

// ─────────────────────────────────────────────
// Root App
// ─────────────────────────────────────────────
type Page = "analyze" | "metrics" | "model";

export default function App() {
  const [page, setPage]       = useState<Page>("analyze");
  const [health, setHealth]   = useState<{ backend: string; inference: string }>({ backend: "checking", inference: "checking" });

  useEffect(() => {
    checkHealth()
      .then(h => setHealth({ backend: h.status, inference: h.inference }))
      .catch(() => setHealth({ backend: "err", inference: "err" }));
  }, []);

  const navItems: { id: Page; icon: string; label: string }[] = [
    { id: "analyze", icon: "🔍", label: "Commit Analyzer" },
    { id: "metrics", icon: "📊", label: "Live Metrics" },
    { id: "model",   icon: "🤖", label: "Model Info" },
  ];

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1>PerfSense</h1>
          <span>React Regression Predictor</span>
        </div>
        <nav>
          {navItems.map(n => (
            <div key={n.id} className={`nav-item ${page === n.id ? "active" : ""}`} onClick={() => setPage(n.id)}>
              <span className="nav-icon">{n.icon}</span>
              {n.label}
            </div>
          ))}
        </nav>
        <div className="status-bar">
          <div>
            <span className={`status-dot ${health.backend === "ok" ? "ok" : health.backend === "checking" ? "warn" : "err"}`} />
            Backend API
          </div>
          <div>
            <span className={`status-dot ${health.inference === "ok" ? "ok" : health.inference === "checking" ? "warn" : "err"}`} />
            Inference Service
          </div>
        </div>
      </aside>

      <main className="main">
        {page === "analyze" && <AnalyzePage />}
        {page === "metrics" && <MetricsPage />}
        {page === "model"   && <ModelPage />}
      </main>
    </div>
  );
}
