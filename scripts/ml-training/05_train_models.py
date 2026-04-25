#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PerfSense ML Training Pipeline

Models trained:
  1. Logistic Regression  — baseline
  2. Random Forest        — comparison
  3. XGBoost              — primary model

Dataset split (chronological, no data leakage):
  Train : 70 %  (earliest commits)
  Val   : 10 %  (hyperparameter tuning)
  Test  : 20 %  (final held-out evaluation)

Class imbalance handled via SMOTE on training set only.

Outputs (data/models/):
  logistic_regression.pkl
  random_forest.pkl
  xgboost_model.pkl
  scaler.pkl
  evaluation_report.json
  feature_importance.csv
  results/  — confusion matrix + ROC curve PNGs
"""

import os, sys, json, warnings
import numpy  as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import joblib

from sklearn.preprocessing    import StandardScaler
from sklearn.linear_model     import LogisticRegression
from sklearn.ensemble         import RandomForestClassifier
from sklearn.metrics          import (accuracy_score, precision_score,
                                      recall_score, f1_score,
                                      roc_auc_score, confusion_matrix,
                                      ConfusionMatrixDisplay, RocCurveDisplay)
from sklearn.model_selection  import StratifiedKFold, cross_val_score
from imblearn.over_sampling   import SMOTE
import xgboost as xgb
import shap

warnings.filterwarnings("ignore")

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
DATA_FILE    = os.path.join(PROJECT_ROOT, "data", "features", "features_labeled.csv")
MODELS_DIR   = os.path.join(PROJECT_ROOT, "data", "models")
RESULTS_DIR  = os.path.join(MODELS_DIR, "results")

os.makedirs(MODELS_DIR,  exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────
# FEATURE COLUMNS
# F21-F23 excluded: sentinel values (-1 / 0), no real Lighthouse scores yet
# regression_score excluded: derived from labels (would leak)
# ─────────────────────────────────────────────────────────────
FEATURE_COLS = [
    # Static Code Metrics
    "files_changed", "files_in_components", "lines_added", "lines_deleted",
    "net_lines", "large_commit", "package_json_changed", "complexity_delta",
    # React-Specific Patterns
    "useEffect_added", "useState_added", "useCallback_added", "useMemo_added",
    "useContext_added", "useReducer_added", "memo_added", "lazy_added",
    "inline_arrow_functions", "console_log_added", "import_count_delta",
    "nested_components",
    # Historical Context (computable without Lighthouse)
    "deployment_frequency", "bundle_size_delta",
    "component_count_delta", "hook_density", "optimization_ratio",
]
LABEL_COL = "is_regression"


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def evaluate(name, model, X, y, threshold=0.5):
    """Return dict of evaluation metrics."""
    proba = model.predict_proba(X)[:, 1]
    pred  = (proba >= threshold).astype(int)
    return {
        "model":     name,
        "accuracy":  round(accuracy_score(y, pred),          4),
        "precision": round(precision_score(y, pred,          zero_division=0), 4),
        "recall":    round(recall_score(y, pred,             zero_division=0), 4),
        "f1":        round(f1_score(y, pred,                 zero_division=0), 4),
        "roc_auc":   round(roc_auc_score(y, proba),          4),
        "support_pos": int(y.sum()),
        "support_neg": int((y == 0).sum()),
    }


def plot_confusion(name, model, X, y, out_dir, threshold=0.5):
    proba = model.predict_proba(X)[:, 1]
    pred  = (proba >= threshold).astype(int)
    cm    = confusion_matrix(y, pred)
    disp  = ConfusionMatrixDisplay(cm, display_labels=["No Regression", "Regression"])
    fig, ax = plt.subplots(figsize=(5, 4))
    disp.plot(ax=ax, colorbar=False, cmap="Blues")
    ax.set_title(f"{name} — Confusion Matrix (test set)")
    fname = os.path.join(out_dir, f"cm_{name.lower().replace(' ', '_')}.png")
    fig.savefig(fname, bbox_inches="tight", dpi=120)
    plt.close(fig)
    return fname


def plot_roc(models_probas, y, out_dir):
    """Overlay ROC curves for all models."""
    fig, ax = plt.subplots(figsize=(6, 5))
    for name, proba in models_probas:
        RocCurveDisplay.from_predictions(y, proba, name=name, ax=ax)
    ax.set_title("ROC Curves — Test Set")
    ax.plot([0,1],[0,1], "k--", linewidth=0.8)
    fname = os.path.join(out_dir, "roc_curves.png")
    fig.savefig(fname, bbox_inches="tight", dpi=120)
    plt.close(fig)
    return fname


def plot_feature_importance(feature_names, importances, out_dir):
    idx  = np.argsort(importances)[-20:]           # top 20
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh([feature_names[i] for i in idx],
            [importances[i]   for i in idx], color="steelblue")
    ax.set_xlabel("Importance")
    ax.set_title("XGBoost Feature Importance (top 20)")
    fname = os.path.join(out_dir, "feature_importance_xgb.png")
    fig.savefig(fname, bbox_inches="tight", dpi=120)
    plt.close(fig)
    return fname


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("PerfSense — ML Training Pipeline")
    print("=" * 60)

    # ── Load data ────────────────────────────────────────────
    df = pd.read_csv(DATA_FILE, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)   # chronological order

    print(f"Dataset  : {len(df)} commits  |  "
          f"Regressions: {df[LABEL_COL].sum()} ({100*df[LABEL_COL].mean():.1f} %)\n")

    X = df[FEATURE_COLS].values
    y = df[LABEL_COL].values

    # ── Chronological split ──────────────────────────────────
    n        = len(df)
    n_train  = int(n * 0.70)
    n_val    = int(n * 0.10)

    X_train, y_train = X[:n_train],          y[:n_train]
    X_val,   y_val   = X[n_train:n_train+n_val], y[n_train:n_train+n_val]
    X_test,  y_test  = X[n_train+n_val:],    y[n_train+n_val:]

    print(f"Train : {len(X_train):>4} commits  "
          f"({100*y_train.mean():.1f} % regression)")
    print(f"Val   : {len(X_val):>4} commits  "
          f"({100*y_val.mean():.1f} % regression)")
    print(f"Test  : {len(X_test):>4} commits  "
          f"({100*y_test.mean():.1f} % regression)\n")

    # ── Scale features ───────────────────────────────────────
    scaler  = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train)
    X_val_sc   = scaler.transform(X_val)
    X_test_sc  = scaler.transform(X_test)
    joblib.dump(scaler, os.path.join(MODELS_DIR, "scaler.pkl"))

    # ── SMOTE on training set only ───────────────────────────
    sm = SMOTE(random_state=42, k_neighbors=min(5, y_train.sum() - 1))
    X_train_res, y_train_res = sm.fit_resample(X_train_sc, y_train)
    print(f"After SMOTE — train: {len(X_train_res)} "
          f"({100*y_train_res.mean():.1f} % regression)\n")

    # ═══════════════════════════════════════════════════════
    # MODEL 1: Logistic Regression (baseline)
    # ═══════════════════════════════════════════════════════
    print("─" * 40)
    print("Training: Logistic Regression (baseline)")
    lr = LogisticRegression(max_iter=1000, class_weight="balanced",
                            C=0.1, random_state=42)
    lr.fit(X_train_res, y_train_res)
    joblib.dump(lr, os.path.join(MODELS_DIR, "logistic_regression.pkl"))

    lr_val  = evaluate("Logistic Regression", lr, X_val_sc,  y_val)
    lr_test = evaluate("Logistic Regression", lr, X_test_sc, y_test)
    print(f"  Val  → acc={lr_val['accuracy']}  prec={lr_val['precision']}  "
          f"rec={lr_val['recall']}  f1={lr_val['f1']}  auc={lr_val['roc_auc']}")
    print(f"  Test → acc={lr_test['accuracy']}  prec={lr_test['precision']}  "
          f"rec={lr_test['recall']}  f1={lr_test['f1']}  auc={lr_test['roc_auc']}")

    # ═══════════════════════════════════════════════════════
    # MODEL 2: Random Forest
    # ═══════════════════════════════════════════════════════
    print("\n─" * 2 + "─" * 38)
    print("Training: Random Forest")
    rf = RandomForestClassifier(n_estimators=200, max_depth=8,
                                class_weight="balanced", random_state=42,
                                n_jobs=-1)
    rf.fit(X_train_res, y_train_res)
    joblib.dump(rf, os.path.join(MODELS_DIR, "random_forest.pkl"))

    rf_val  = evaluate("Random Forest", rf, X_val_sc,  y_val)
    rf_test = evaluate("Random Forest", rf, X_test_sc, y_test)
    print(f"  Val  → acc={rf_val['accuracy']}  prec={rf_val['precision']}  "
          f"rec={rf_val['recall']}  f1={rf_val['f1']}  auc={rf_val['roc_auc']}")
    print(f"  Test → acc={rf_test['accuracy']}  prec={rf_test['precision']}  "
          f"rec={rf_test['recall']}  f1={rf_test['f1']}  auc={rf_test['roc_auc']}")

    # ═══════════════════════════════════════════════════════
    # MODEL 3: XGBoost (primary) — tuned on val set
    # ═══════════════════════════════════════════════════════
    print("\n─" * 2 + "─" * 38)
    print("Training: XGBoost (primary model)")

    pos_weight = int((y_train == 0).sum() / max(1, y_train.sum()))

    # Grid search over key hyperparameters using val F1
    best_f1, best_params, best_xgb = 0, {}, None
    grid = [
        {"n_estimators": n, "max_depth": d, "learning_rate": lr_,
         "subsample": ss, "colsample_bytree": cs}
        for n  in [200, 400]
        for d  in [4, 6]
        for lr_ in [0.05, 0.1]
        for ss in [0.8]
        for cs in [0.8]
    ]

    print(f"  Grid search over {len(grid)} configs...")
    for params in grid:
        model = xgb.XGBClassifier(
            **params,
            scale_pos_weight=pos_weight,
            use_label_encoder=False,
            eval_metric="logloss",
            random_state=42,
            verbosity=0,
        )
        model.fit(X_train_res, y_train_res,
                  eval_set=[(X_val_sc, y_val)],
                  verbose=False)
        metrics = evaluate("XGBoost", model, X_val_sc, y_val)
        if metrics["f1"] > best_f1:
            best_f1, best_params, best_xgb = metrics["f1"], params, model

    print(f"  Best val F1: {best_f1}  params: {best_params}")
    joblib.dump(best_xgb, os.path.join(MODELS_DIR, "xgboost_model.pkl"))

    xgb_val  = evaluate("XGBoost", best_xgb, X_val_sc,  y_val)
    xgb_test = evaluate("XGBoost", best_xgb, X_test_sc, y_test)
    print(f"  Val  → acc={xgb_val['accuracy']}  prec={xgb_val['precision']}  "
          f"rec={xgb_val['recall']}  f1={xgb_val['f1']}  auc={xgb_val['roc_auc']}")
    print(f"  Test → acc={xgb_test['accuracy']}  prec={xgb_test['precision']}  "
          f"rec={xgb_test['recall']}  f1={xgb_test['f1']}  auc={xgb_test['roc_auc']}")

    # ═══════════════════════════════════════════════════════
    # CROSS-REPO VALIDATION (leave-one-repo-out)
    # ═══════════════════════════════════════════════════════
    print("\n─" * 2 + "─" * 38)
    print("Cross-repo validation (leave-one-repo-out):")
    repos      = sorted(df["repo"].unique())
    cross_repo = []

    for held_out in repos:
        mask_train = df["repo"] != held_out
        mask_test  = df["repo"] == held_out

        Xtr = scaler.transform(df.loc[mask_train, FEATURE_COLS].values)
        ytr = df.loc[mask_train, LABEL_COL].values
        Xte = scaler.transform(df.loc[mask_test,  FEATURE_COLS].values)
        yte = df.loc[mask_test,  LABEL_COL].values

        if yte.sum() == 0:
            cross_repo.append({"repo": held_out, "note": "no regressions in test"})
            print(f"  {held_out:<20}  [skip — no regressions in held-out set]")
            continue

        sm2 = SMOTE(random_state=42, k_neighbors=min(5, ytr.sum() - 1))
        Xtr_res, ytr_res = sm2.fit_resample(Xtr, ytr)

        xgb_cv = xgb.XGBClassifier(
            **best_params,
            scale_pos_weight=int((ytr==0).sum()/max(1,ytr.sum())),
            use_label_encoder=False,
            eval_metric="logloss",
            random_state=42,
            verbosity=0,
        )
        xgb_cv.fit(Xtr_res, ytr_res)
        m = evaluate(f"XGB-no-{held_out}", xgb_cv, Xte, yte)
        cross_repo.append({
            "repo": held_out,
            "accuracy":  m["accuracy"],
            "precision": m["precision"],
            "recall":    m["recall"],
            "f1":        m["f1"],
            "roc_auc":   m["roc_auc"],
        })
        print(f"  {held_out:<20}  "
              f"acc={m['accuracy']}  prec={m['precision']}  "
              f"rec={m['recall']}  f1={m['f1']}  auc={m['roc_auc']}")

    # ═══════════════════════════════════════════════════════
    # FEATURE IMPORTANCE — XGBoost + SHAP
    # ═══════════════════════════════════════════════════════
    print("\n─" * 2 + "─" * 38)
    print("Feature importance (XGBoost gain):")
    importances = best_xgb.feature_importances_
    fi_pairs = sorted(zip(FEATURE_COLS, importances),
                      key=lambda x: -x[1])
    for feat, imp in fi_pairs[:10]:
        print(f"  {feat:<30}  {imp:.4f}")

    fi_df = pd.DataFrame({"feature": FEATURE_COLS, "importance": importances})
    fi_df = fi_df.sort_values("importance", ascending=False)
    fi_df.to_csv(os.path.join(MODELS_DIR, "feature_importance.csv"), index=False)

    plot_feature_importance(FEATURE_COLS, importances, RESULTS_DIR)

    # SHAP summary
    print("\nComputing SHAP values...")
    explainer   = shap.TreeExplainer(best_xgb)
    shap_values = explainer.shap_values(X_test_sc)
    shap_mean   = np.abs(shap_values).mean(axis=0)
    shap_pairs  = sorted(zip(FEATURE_COLS, shap_mean), key=lambda x: -x[1])
    print("Top 10 SHAP features:")
    for feat, val in shap_pairs[:10]:
        print(f"  {feat:<30}  {val:.4f}")

    # SHAP bar plot
    fig, ax = plt.subplots(figsize=(8, 6))
    top_n    = 15
    top_feat = [p[0] for p in shap_pairs[:top_n]][::-1]
    top_vals = [p[1] for p in shap_pairs[:top_n]][::-1]
    ax.barh(top_feat, top_vals, color="coral")
    ax.set_xlabel("Mean |SHAP value|")
    ax.set_title("SHAP Feature Importance (test set, top 15)")
    fig.savefig(os.path.join(RESULTS_DIR, "shap_importance.png"),
                bbox_inches="tight", dpi=120)
    plt.close(fig)

    # ═══════════════════════════════════════════════════════
    # PLOTS — Confusion matrices + ROC
    # ═══════════════════════════════════════════════════════
    plot_confusion("Logistic Regression", lr,       X_test_sc, y_test, RESULTS_DIR)
    plot_confusion("Random Forest",       rf,       X_test_sc, y_test, RESULTS_DIR)
    plot_confusion("XGBoost",             best_xgb, X_test_sc, y_test, RESULTS_DIR)

    plot_roc([
        ("Logistic Regression", lr.predict_proba(X_test_sc)[:, 1]),
        ("Random Forest",       rf.predict_proba(X_test_sc)[:, 1]),
        ("XGBoost",             best_xgb.predict_proba(X_test_sc)[:, 1]),
    ], y_test, RESULTS_DIR)

    # ═══════════════════════════════════════════════════════
    # SAVE EVALUATION REPORT
    # ═══════════════════════════════════════════════════════
    report = {
        "dataset": {
            "total_commits":       len(df),
            "regression_count":    int(df[LABEL_COL].sum()),
            "regression_rate":     round(df[LABEL_COL].mean(), 4),
            "feature_count":       len(FEATURE_COLS),
            "features_used":       FEATURE_COLS,
        },
        "split": {
            "train": len(X_train), "val": len(X_val), "test": len(X_test),
            "train_regression_rate": round(float(y_train.mean()), 4),
            "test_regression_rate":  round(float(y_test.mean()),  4),
        },
        "best_xgb_params":    best_params,
        "validation_metrics": {
            "logistic_regression": lr_val,
            "random_forest":       rf_val,
            "xgboost":             xgb_val,
        },
        "test_metrics": {
            "logistic_regression": lr_test,
            "random_forest":       rf_test,
            "xgboost":             xgb_test,
        },
        "cross_repo_validation": cross_repo,
        "feature_importance_top10": [
            {"feature": f, "importance": round(float(i), 6)}
            for f, i in fi_pairs[:10]
        ],
        "shap_top10": [
            {"feature": f, "mean_shap": round(float(v), 6)}
            for f, v in shap_pairs[:10]
        ],
    }

    report_path = os.path.join(MODELS_DIR, "evaluation_report.json")
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    # ─── Final summary ───────────────────────────────────────
    print("\n" + "=" * 60)
    print("FINAL TEST SET RESULTS")
    print("=" * 60)
    header = f"{'Model':<25} {'Acc':>6} {'Prec':>6} {'Rec':>6} {'F1':>6} {'AUC':>6}"
    print(header)
    print("-" * len(header))
    for m in [lr_test, rf_test, xgb_test]:
        print(f"  {m['model']:<23} {m['accuracy']:>6} {m['precision']:>6} "
              f"{m['recall']:>6} {m['f1']:>6} {m['roc_auc']:>6}")

    targets_met = (
        xgb_test["accuracy"]  >= 0.75 and
        xgb_test["precision"] >= 0.70 and
        xgb_test["recall"]    >= 0.60
    )
    print(f"\nDissertation targets (acc>0.75, prec>0.70, rec>0.60): "
          f"{'MET' if targets_met else 'NOT MET'}")

    print(f"\n[OK] Models saved to  {MODELS_DIR}")
    print(f"[OK] Plots saved to   {RESULTS_DIR}")
    print(f"[OK] Report saved to  {report_path}")


if __name__ == "__main__":
    main()
