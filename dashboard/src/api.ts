const BASE = "http://localhost:3001";

export interface ShapEntry { feature: string; shap_value: number; }

export interface Prediction {
  request_id?: string;
  is_regression: number;
  regression_probability: number;
  risk_level: "low" | "medium" | "high";
  shap_top5: ShapEntry[];
  features_used: Record<string, number>;
  commit_hash?: string;
  repo?: string;
  predicted_at: string;
}

export interface ModelInfo {
  model: string;
  feature_count: number;
  features: string[];
  test_f1: number;
  test_auc: number;
  test_accuracy: number;
  best_params: Record<string, unknown>;
}

export interface VitalRecord {
  name: string;
  value: number;
  rating: "good" | "needs-improvement" | "poor";
}

export interface MetricsRecord {
  id: string;
  sessionId: string;
  url: string;
  received: string;
  webVitals: VitalRecord[];
  componentRenders: { componentName: string; renderCount: number; totalRenderTime: number; lastRenderTime: number }[];
}

export interface MetricsResponse { count: number; records: MetricsRecord[]; }

export async function analyzeCommitDiff(diff: string, repo?: string, hash?: string): Promise<Prediction> {
  const r = await fetch(`${BASE}/api/analyze/diff`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ diff, repo, commit_hash: hash }),
  });
  if (!r.ok) throw new Error(`API error ${r.status}`);
  return r.json();
}

export async function fetchModelInfo(): Promise<ModelInfo> {
  const r = await fetch(`${BASE}/api/analyze/model-info`);
  if (!r.ok) throw new Error(`API error ${r.status}`);
  return r.json();
}

export async function fetchMetrics(): Promise<MetricsResponse> {
  const r = await fetch(`${BASE}/api/metrics`);
  if (!r.ok) throw new Error(`API error ${r.status}`);
  return r.json();
}

export async function checkHealth(): Promise<{ status: string; inference: string }> {
  const r = await fetch(`${BASE}/api/health`);
  if (!r.ok) throw new Error(`API error ${r.status}`);
  return r.json();
}
