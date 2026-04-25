#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PerfSense Inference Service
FastAPI microservice that serves the trained XGBoost model.

Endpoints:
  POST /predict          — predict from pre-extracted feature dict
  POST /predict/diff     — extract features from raw git diff + predict
  GET  /health           — liveness check
  GET  /model/info       — model metadata and feature list

Usage:
  python -X utf8 06_inference_service.py
  # or via uvicorn:
  uvicorn 06_inference_service:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import sys
import re
import json
import logging
from datetime import datetime
from typing import Optional

import joblib
import numpy as np
import pandas as pd
import shap
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
MODELS_DIR   = os.path.join(PROJECT_ROOT, "data", "models")

FEATURE_COLS = [
    "files_changed", "files_in_components", "lines_added", "lines_deleted",
    "net_lines", "large_commit", "package_json_changed", "complexity_delta",
    "useEffect_added", "useState_added", "useCallback_added", "useMemo_added",
    "useContext_added", "useReducer_added", "memo_added", "lazy_added",
    "inline_arrow_functions", "console_log_added", "import_count_delta",
    "nested_components",
    "deployment_frequency", "bundle_size_delta",
    "component_count_delta", "hook_density", "optimization_ratio",
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("perfsense")

# ─────────────────────────────────────────────────────────────
# MODEL LOADING
# ─────────────────────────────────────────────────────────────

def load_artifacts():
    model  = joblib.load(os.path.join(MODELS_DIR, "xgboost_model.pkl"))
    scaler = joblib.load(os.path.join(MODELS_DIR, "scaler.pkl"))
    with open(os.path.join(MODELS_DIR, "evaluation_report.json"), encoding="utf-8") as f:
        report = json.load(f)
    explainer = shap.TreeExplainer(model)
    return model, scaler, explainer, report

logger.info("Loading model artifacts...")
MODEL, SCALER, EXPLAINER, EVAL_REPORT = load_artifacts()
logger.info("Model loaded successfully.")

# ─────────────────────────────────────────────────────────────
# DIFF FEATURE EXTRACTION (mirrors 03_extract_features.py)
# ─────────────────────────────────────────────────────────────

def _count(lines, pattern, flags=0):
    rx = re.compile(pattern, flags)
    return sum(len(rx.findall(l)) for l in lines)

def extract_features_from_diff(diff_text: str) -> dict:
    """Parse a unified git diff and return the 25 model features."""
    added, removed, files = [], [], []
    for line in diff_text.split("\n"):
        if line.startswith("diff --git"):
            m = re.search(r" b/(.+)$", line)
            if m:
                files.append(m.group(1))
        elif line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            removed.append(line[1:])

    # F1-F8
    v_f1  = len(files)
    v_f2  = sum(1 for f in files if re.search(r"[/\\]components?[/\\]", f, re.I))
    v_f3  = len(added)
    v_f4  = len(removed)
    v_f5  = v_f3 - v_f4
    v_f6  = 1 if v_f3 > 200 else 0
    v_f7  = 1 if any("package.json" in f for f in files) else 0
    cf_pat = r"\b(if|else\s+if|switch|case|\?|for|while|catch)\b"
    v_f8  = _count(added, cf_pat) - _count(removed, cf_pat)

    # F9-F20
    v_f9  = _count(added, r"\buseEffect\s*\(")
    v_f10 = _count(added, r"\buseState\s*\(")
    v_f11 = _count(added, r"\buseCallback\s*\(")
    v_f12 = _count(added, r"\buseMemo\s*\(")
    v_f13 = _count(added, r"\buseContext\s*\(")
    v_f14 = _count(added, r"\buseReducer\s*\(")
    v_f15 = _count(added, r"React\.memo\s*\(|=\s*memo\s*\(")
    v_f16 = _count(added, r"React\.lazy\s*\(|=\s*lazy\s*\(")
    v_f17 = _count(added, r"on[A-Z]\w*\s*=\s*\{(?:async\s+)?(?:\([^)]*\)|[a-zA-Z_]\w*)\s*=>")
    v_f18 = _count(added, r"\bconsole\.(log|warn|error|debug)\s*\(")
    v_f19 = _count(added, r"^\s*import\s+") - _count(removed, r"^\s*import\s+")
    v_f20 = _count(added, r"^\s{2,}(?:export\s+)?(?:const\s+[A-Z]\w+\s*=|function\s+[A-Z]\w*\s*\()")

    # F24-F28 (no historical context available from raw diff)
    v_f24 = 0       # deployment_frequency unknown without repo history
    v_f25 = round(min(v_f19 * 2.0, 50.0), 2) if v_f7 and v_f19 > 0 else 0.0
    comp_pat = r"^\s*(?:export\s+)?(?:default\s+)?(?:const\s+[A-Z]\w+\s*=|function\s+[A-Z]\w*\s*\()"
    v_f26 = _count(added, comp_pat) - _count(removed, comp_pat)
    hooks = v_f9 + v_f10 + v_f11 + v_f12 + v_f13 + v_f14
    v_f27 = round(hooks / max(1, abs(v_f26) + 1), 4)
    v_f28 = round((v_f15 + v_f16 + v_f11 + v_f12) / max(1, v_f9 + v_f10), 4)

    return {
        "files_changed": v_f1, "files_in_components": v_f2,
        "lines_added": v_f3, "lines_deleted": v_f4, "net_lines": v_f5,
        "large_commit": v_f6, "package_json_changed": v_f7, "complexity_delta": v_f8,
        "useEffect_added": v_f9, "useState_added": v_f10,
        "useCallback_added": v_f11, "useMemo_added": v_f12,
        "useContext_added": v_f13, "useReducer_added": v_f14,
        "memo_added": v_f15, "lazy_added": v_f16,
        "inline_arrow_functions": v_f17, "console_log_added": v_f18,
        "import_count_delta": v_f19, "nested_components": v_f20,
        "deployment_frequency": v_f24, "bundle_size_delta": v_f25,
        "component_count_delta": v_f26, "hook_density": v_f27,
        "optimization_ratio": v_f28,
    }

# ─────────────────────────────────────────────────────────────
# PREDICTION LOGIC
# ─────────────────────────────────────────────────────────────

def run_prediction(features: dict) -> dict:
    """Scale features, predict, compute SHAP explanation."""
    row = pd.DataFrame([{col: features.get(col, 0) for col in FEATURE_COLS}])
    X_scaled = SCALER.transform(row)

    prob  = float(MODEL.predict_proba(X_scaled)[0][1])
    label = int(MODEL.predict(X_scaled)[0])

    # SHAP explanation (top 5 contributors)
    shap_vals = EXPLAINER.shap_values(X_scaled)[0]
    shap_pairs = sorted(
        zip(FEATURE_COLS, shap_vals.tolist()),
        key=lambda x: abs(x[1]), reverse=True
    )
    top_shap = [{"feature": f, "shap_value": round(v, 4)} for f, v in shap_pairs[:5]]

    risk_level = "high" if prob >= 0.6 else "medium" if prob >= 0.35 else "low"

    return {
        "is_regression": label,
        "regression_probability": round(prob, 4),
        "risk_level": risk_level,
        "shap_top5": top_shap,
        "features_used": {col: features.get(col, 0) for col in FEATURE_COLS},
    }

# ─────────────────────────────────────────────────────────────
# PYDANTIC SCHEMAS
# ─────────────────────────────────────────────────────────────

class FeatureInput(BaseModel):
    files_changed:          int   = Field(0, ge=0)
    files_in_components:    int   = Field(0, ge=0)
    lines_added:            int   = Field(0, ge=0)
    lines_deleted:          int   = Field(0, ge=0)
    net_lines:              int   = 0
    large_commit:           int   = Field(0, ge=0, le=1)
    package_json_changed:   int   = Field(0, ge=0, le=1)
    complexity_delta:       int   = 0
    useEffect_added:        int   = Field(0, ge=0)
    useState_added:         int   = Field(0, ge=0)
    useCallback_added:      int   = Field(0, ge=0)
    useMemo_added:          int   = Field(0, ge=0)
    useContext_added:       int   = Field(0, ge=0)
    useReducer_added:       int   = Field(0, ge=0)
    memo_added:             int   = Field(0, ge=0)
    lazy_added:             int   = Field(0, ge=0)
    inline_arrow_functions: int   = Field(0, ge=0)
    console_log_added:      int   = Field(0, ge=0)
    import_count_delta:     int   = 0
    nested_components:      int   = Field(0, ge=0)
    deployment_frequency:   int   = Field(0, ge=0)
    bundle_size_delta:      float = Field(0.0, ge=0.0)
    component_count_delta:  int   = 0
    hook_density:           float = Field(0.0, ge=0.0)
    optimization_ratio:     float = Field(0.0, ge=0.0)

class DiffInput(BaseModel):
    diff: str = Field(..., description="Raw unified git diff (output of `git show --no-color`)")
    commit_hash: Optional[str] = None
    repo:        Optional[str] = None

class PredictionResponse(BaseModel):
    is_regression:           int
    regression_probability:  float
    risk_level:              str
    shap_top5:               list
    features_used:           dict
    commit_hash:             Optional[str] = None
    repo:                    Optional[str] = None
    predicted_at:            str

# ─────────────────────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="PerfSense Inference API",
    description="ML-based performance regression predictor for React applications",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "model": "xgboost", "timestamp": datetime.utcnow().isoformat()}


@app.get("/model/info")
def model_info():
    xgb_metrics = EVAL_REPORT.get("test_metrics", {}).get("xgboost", {})
    return {
        "model":         "XGBoost",
        "features":      FEATURE_COLS,
        "feature_count": len(FEATURE_COLS),
        "test_f1":       xgb_metrics.get("f1"),
        "test_auc":      xgb_metrics.get("roc_auc"),
        "test_accuracy": xgb_metrics.get("accuracy"),
        "best_params":   EVAL_REPORT.get("best_xgb_params"),
    }


@app.post("/predict", response_model=PredictionResponse)
def predict(body: FeatureInput):
    try:
        result = run_prediction(body.dict())
    except Exception as e:
        logger.error(f"/predict error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    result["predicted_at"] = datetime.utcnow().isoformat()
    return result


@app.post("/predict/diff", response_model=PredictionResponse)
def predict_from_diff(body: DiffInput):
    if not body.diff.strip():
        raise HTTPException(status_code=400, detail="diff field is empty")
    try:
        features = extract_features_from_diff(body.diff)
        result   = run_prediction(features)
    except Exception as e:
        logger.error(f"/predict/diff error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    result["commit_hash"] = body.commit_hash
    result["repo"]        = body.repo
    result["predicted_at"] = datetime.utcnow().isoformat()
    return result


# ─────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("06_inference_service:app", host="0.0.0.0", port=8000, reload=False)
