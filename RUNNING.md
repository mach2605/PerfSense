# PerfSense — Running the Full System

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.11+ | python.org |
| Node.js | 18+ | nodejs.org |
| yarn | any | `npm install -g yarn` |

### Python packages
```bash
pip install fastapi uvicorn[standard] xgboost scikit-learn shap imbalanced-learn pandas numpy joblib
```

### Node packages (run once)
```bash
cd backend && npm install
cd ../dashboard && npm install
```

---

## One-Time Setup: Build the ML Pipeline

Run these scripts **in order** the first time. After that, the trained models persist in `data/models/` and you don't need to re-run them.

```bash
# 1. Extract commits from cloned repos (requires repos in data/repos/)
python -X utf8 scripts/data-collection/02_extract_commits.py

# 2. Extract 28 features from each commit's git diff
python -X utf8 scripts/feature-extraction/03_extract_features.py

# 3. Label commits using heuristic proxy (no Lighthouse needed)
python -X utf8 scripts/feature-extraction/04_label_commits.py

# 4. Train Logistic Regression, Random Forest, XGBoost models
python -X utf8 scripts/ml-training/05_train_models.py
```

Outputs after this step:
- `data/features/features_labeled.csv` — 960 labeled commits
- `data/models/xgboost_model.pkl` — primary model
- `data/models/scaler.pkl` — fitted StandardScaler
- `data/models/evaluation_report.json` — full metrics

---

## Running the System (3 terminals)

Open **three separate terminals** from the project root.

### Terminal 1 — ML Inference Service (FastAPI, port 8000)
```bash
python -X utf8 scripts/inference/06_inference_service.py
```
Expected output:
```
INFO  Loading model artifacts...
INFO  Model loaded successfully.
INFO  Uvicorn running on http://0.0.0.0:8000
```

### Terminal 2 — Backend API (Node/Express, port 3001)
```bash
node backend/src/app.js
```
Expected output:
```
PerfSense API running on http://localhost:3001
Inference service: http://localhost:8000
```

### Terminal 3 — Dashboard (React/Vite, port 5173)
```bash
cd dashboard
npm run dev
```
Then open **http://localhost:5173** in your browser.

---

## Verify Everything is Working

```bash
# Health check (should show both services "ok")
curl http://localhost:3001/api/health

# Expected:
# {"status":"ok","service":"perfsense-backend","inference":"ok",...}
```

---

## API Quick Reference

### Predict from a git diff
```bash
curl -X POST http://localhost:3001/api/analyze/diff \
  -H "Content-Type: application/json" \
  -d '{
    "diff": "diff --git a/src/App.tsx ...\n+useEffect(() => {...",
    "repo": "my-app",
    "commit_hash": "abc1234"
  }'
```

### Predict from pre-extracted features
```bash
curl -X POST http://localhost:3001/api/analyze/features \
  -H "Content-Type: application/json" \
  -d '{
    "features": {
      "lines_added": 350,
      "large_commit": 1,
      "useEffect_added": 3,
      "useCallback_added": 0,
      "memo_added": 0,
      "complexity_delta": 8,
      "inline_arrow_functions": 5,
      "package_json_changed": 1,
      "import_count_delta": 4,
      "nested_components": 2,
      "files_changed": 8,
      "files_in_components": 5,
      "lines_deleted": 20,
      "net_lines": 330,
      "useState_added": 4,
      "useMemo_added": 0,
      "useContext_added": 1,
      "useReducer_added": 0,
      "lazy_added": 0,
      "console_log_added": 3,
      "deployment_frequency": 8,
      "bundle_size_delta": 8.0,
      "component_count_delta": 2,
      "hook_density": 2.5,
      "optimization_ratio": 0.0
    }
  }'
```

### Get stored SDK metrics
```bash
curl http://localhost:3001/api/metrics
```

### Model metadata
```bash
curl http://localhost:3001/api/analyze/model-info
```

---

## Monitoring SDK Usage

Install in any React app:
```bash
npm install /path/to/perfsense-dissertation/sdk
# or link locally:
cd sdk && npm run build
cd your-react-app && npm install ../perfsense-dissertation/sdk
```

Initialise in your app root:
```tsx
// src/main.tsx or src/index.tsx
import PerfSense from "@perfsense/sdk";

PerfSense.init({
  endpoint: "http://localhost:3001",
  sampleRate: 1.0,
  debug: true,         // logs to console in dev
  flushInterval: 30000 // send metrics every 30s
});
```

Track component render times:
```tsx
import { usePerfSenseTracker } from "@perfsense/sdk";

function MyExpensiveComponent() {
  usePerfSenseTracker("MyExpensiveComponent");
  return <div>...</div>;
}
```

Or use the Profiler wrapper:
```tsx
import { PerfSenseProfiler } from "@perfsense/sdk";

<PerfSenseProfiler id="UserList">
  <UserList />
</PerfSenseProfiler>
```

---

## Project Structure

```
perfsense-dissertation/
  data/
    repos/              8 cloned React repositories
    raw-commits/        all_commits.json (960 commits)
    features/           features.csv, features_labeled.csv
    labeled-commits/    label_report.json
    models/             xgboost_model.pkl, scaler.pkl, evaluation_report.json
    models/results/     confusion matrices, ROC curves, SHAP plots
    lighthouse/         lighthouse_scores.json (10-commit validation)
  scripts/
    data-collection/    01_clone_repos.py, 02_extract_commits.py
    feature-extraction/ 03_extract_features.py, 04_label_commits.py
    ml-training/        05_train_models.py
    inference/          06_inference_service.py
  backend/
    src/app.js          Express entry point (port 3001)
    src/routes/
      analyze.js        /api/analyze/diff, /api/analyze/features
      metrics.js        /api/metrics
      health.js         /api/health
  sdk/
    src/                TypeScript source (vitals, transport, hooks, sdk)
    dist/               Compiled JS + type declarations
  dashboard/
    src/App.tsx         React dashboard (Analyze / Live Metrics / Model Info)
  docs/
    reports/            MS2024TM93208_updated.docx (mid-semester report)
```

---

## ML Results Summary

| Model | F1 | AUC | Accuracy |
|---|---|---|---|
| Logistic Regression | 0.881 | 0.973 | 96.4% |
| Random Forest | 0.903 | 0.986 | 96.9% |
| **XGBoost (primary)** | **0.918** | **0.988** | **97.4%** |

Dissertation targets (acc>75%, prec>70%, rec>60%): **all exceeded**.

Top SHAP features: `lines_added`, `large_commit`, `complexity_delta`, `useEffect_added`, `nested_components`
