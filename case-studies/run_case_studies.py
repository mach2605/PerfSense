#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PerfSense — Case Study Runner

Generates unified diffs from before/after files for each case study,
sends them through the live inference pipeline, and records results.

Requires:
  - Inference service running on port 8000
  - Backend API running on port 3001

Usage:
  python -X utf8 run_case_studies.py
"""

import os, sys, json, difflib, urllib.request, urllib.error
from datetime import datetime

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
BACKEND_URL  = "http://localhost:3001"
RESULTS_FILE = os.path.join(SCRIPT_DIR, "results.json")

CASE_STUDIES = [
    {
        "id":          "CS1",
        "name":        "Task Manager",
        "description": "Removes React.memo/useCallback/useMemo; adds 4 unguarded useEffects, 2 nested components, 8+ inline arrow functions",
        "before":      os.path.join(SCRIPT_DIR, "cs1-task-manager", "before.tsx"),
        "after":       os.path.join(SCRIPT_DIR, "cs1-task-manager", "after.tsx"),
        "filepath":    "src/components/TaskManager.tsx",
        "repo":        "task-manager-app",
        "commit_hash": "cs1-regression",
        "expected":    "high",
        "anti_patterns": [
            "useEffect without dependency array (runs every render)",
            "Nested component definitions (TaskItem, TaskBadge inside parent)",
            "Removed React.memo, useCallback, useMemo",
            "8+ inline arrow functions in JSX event handlers",
            "4 console.log debug statements",
        ],
    },
    {
        "id":          "CS2",
        "name":        "Product Catalog",
        "description": "Adds 5 heavy dependencies (lodash, moment, numeral, chart.js, xlsx); 200+ lines; 5 unguarded useEffects; 2 nested components",
        "before":      os.path.join(SCRIPT_DIR, "cs2-product-catalog", "before.tsx"),
        "after":       os.path.join(SCRIPT_DIR, "cs2-product-catalog", "after.tsx"),
        "filepath":    "src/components/ProductCatalog.tsx",
        "repo":        "ecommerce-app",
        "commit_hash": "cs2-regression",
        "expected":    "high",
        "anti_patterns": [
            "5 heavy dependencies imported (lodash, moment, numeral, chart.js, xlsx)",
            "Large commit: 200+ lines added",
            "5 unguarded useEffects (no dependency arrays)",
            "Nested ProductCard and StatsBar components",
            "10+ useState hooks (should use useReducer)",
            "Inline arrow functions for all event handlers",
            "5 console.log debug statements",
        ],
    },
    {
        "id":          "CS3",
        "name":        "Analytics Widget",
        "description": "High complexity delta via inline loops/conditionals; 11 useState hooks; 3 unguarded useEffects; 2 nested components; removed all memoization",
        "before":      os.path.join(SCRIPT_DIR, "cs3-analytics-widget", "before.tsx"),
        "after":       os.path.join(SCRIPT_DIR, "cs3-analytics-widget", "after.tsx"),
        "filepath":    "src/components/AnalyticsWidget.tsx",
        "repo":        "analytics-dashboard",
        "commit_hash": "cs3-regression",
        "expected":    "high",
        "anti_patterns": [
            "High complexity delta: for loops, if/else chains, inline calculations",
            "11 useState hooks (no consolidation with useReducer)",
            "3 unguarded useEffects (run on every render)",
            "Nested ChartBar and StatsRow components",
            "Removed all useMemo, useCallback, React.memo",
            "Inline calculations not memoized (total, average, trend on every render)",
            "6 console.log debug statements",
        ],
    },
]


def make_diff(before_path: str, after_path: str, filepath: str) -> str:
    """Generate a unified diff between before and after files."""
    with open(before_path, encoding="utf-8") as f:
        before_lines = f.readlines()
    with open(after_path, encoding="utf-8") as f:
        after_lines = f.readlines()

    diff = list(difflib.unified_diff(
        before_lines, after_lines,
        fromfile=f"a/{filepath}",
        tofile=f"b/{filepath}",
        lineterm="",
    ))

    # Prepend git-style header
    header = f"diff --git a/{filepath} b/{filepath}\nindex before..after 100644\n"
    return header + "\n".join(diff)


def call_api(diff: str, repo: str, commit_hash: str) -> dict:
    """POST diff to backend /api/analyze/diff."""
    payload = json.dumps({
        "diff":        diff,
        "repo":        repo,
        "commit_hash": commit_hash,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BACKEND_URL}/api/analyze/diff",
        data=payload, method="POST",
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read())


def check_services() -> bool:
    """Verify both services are reachable."""
    try:
        r = urllib.request.urlopen(f"{BACKEND_URL}/api/health", timeout=5)
        h = json.loads(r.read())
        if h.get("status") != "ok" or h.get("inference") != "ok":
            print(f"[ERR] Services not healthy: {h}")
            return False
        return True
    except Exception as e:
        print(f"[ERR] Cannot reach backend: {e}")
        print("      Start services first:")
        print("        Terminal 1: python -X utf8 scripts/inference/06_inference_service.py")
        print("        Terminal 2: node backend/src/app.js")
        return False


def run_case_study(cs: dict) -> dict:
    """Generate diff, call API, return result entry."""
    print(f"\n{'='*60}")
    print(f"{cs['id']}: {cs['name']}")
    print(f"{'='*60}")
    print(f"Description: {cs['description']}\n")

    # Generate diff
    diff = make_diff(cs["before"], cs["after"], cs["filepath"])
    added   = sum(1 for l in diff.split("\n") if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff.split("\n") if l.startswith("-") and not l.startswith("---"))
    print(f"Diff stats: +{added} lines  -{removed} lines")

    # Call API
    print("Calling prediction API...")
    result = call_api(diff, cs["repo"], cs["commit_hash"])

    prob     = result["regression_probability"]
    risk     = result["risk_level"]
    is_reg   = result["is_regression"]
    expected = cs["expected"]
    correct  = (risk == expected) or (is_reg == 1 and expected == "high")

    print(f"\nResult:")
    print(f"  Prediction      : {'REGRESSION' if is_reg else 'NO REGRESSION'}")
    print(f"  Risk level      : {risk.upper()}")
    print(f"  Probability     : {prob*100:.1f}%")
    print(f"  Expected        : {expected.upper()}")
    print(f"  Correct?        : {'YES' if correct else 'NO'}")

    print(f"\nTop SHAP contributors:")
    for s in result.get("shap_top5", []):
        direction = "→ regression" if s["shap_value"] > 0 else "→ safer"
        print(f"  {s['feature']:<30}  {s['shap_value']:+.4f}  {direction}")

    print(f"\nKey extracted features:")
    feats = result.get("features_used", {})
    key_feats = ["lines_added", "large_commit", "useEffect_added", "useState_added",
                 "useCallback_added", "memo_added", "nested_components",
                 "inline_arrow_functions", "console_log_added", "import_count_delta",
                 "package_json_changed", "complexity_delta", "optimization_ratio"]
    for f in key_feats:
        v = feats.get(f, 0)
        if v != 0:
            print(f"  {f:<30}  {v}")

    print(f"\nAnti-patterns introduced:")
    for ap in cs["anti_patterns"]:
        print(f"  • {ap}")

    return {
        "case_study_id":          cs["id"],
        "case_study_name":        cs["name"],
        "repo":                   cs["repo"],
        "commit_hash":            cs["commit_hash"],
        "diff_lines_added":       added,
        "diff_lines_removed":     removed,
        "is_regression":          is_reg,
        "regression_probability": round(prob, 4),
        "risk_level":             risk,
        "expected_risk":          expected,
        "prediction_correct":     correct,
        "shap_top5":              result.get("shap_top5", []),
        "key_features":           {f: feats.get(f, 0) for f in key_feats},
        "anti_patterns":          cs["anti_patterns"],
        "request_id":             result.get("request_id"),
        "predicted_at":           result.get("predicted_at"),
    }


def print_summary(results: list):
    print(f"\n{'='*60}")
    print("CASE STUDY SUMMARY")
    print(f"{'='*60}")
    print(f"{'ID':<5} {'Name':<22} {'Prob':>6} {'Risk':<8} {'Expected':<9} {'Correct':>8}")
    print("-" * 60)
    for r in results:
        correct_str = "YES" if r["prediction_correct"] else "NO"
        print(f"{r['case_study_id']:<5} {r['case_study_name']:<22} "
              f"{r['regression_probability']*100:>5.1f}%  "
              f"{r['risk_level']:<8} {r['expected_risk']:<9} {correct_str:>8}")

    correct_count = sum(1 for r in results if r["prediction_correct"])
    print(f"\nAccuracy: {correct_count}/{len(results)} case studies correctly predicted")

    all_high = all(r["risk_level"] == "high" for r in results)
    avg_prob = sum(r["regression_probability"] for r in results) / len(results)
    print(f"All predicted high risk: {'YES' if all_high else 'NO'}")
    print(f"Average probability: {avg_prob*100:.1f}%")


def main():
    print("=" * 60)
    print("PerfSense — Case Study Validation")
    print(f"Running {len(CASE_STUDIES)} case studies")
    print("=" * 60)

    if not check_services():
        sys.exit(1)
    print("Services OK — both backend and inference reachable\n")

    results = []
    for cs in CASE_STUDIES:
        try:
            result = run_case_study(cs)
            results.append(result)
        except Exception as e:
            print(f"\n[ERR] {cs['id']} failed: {e}")
            results.append({"case_study_id": cs["id"], "error": str(e)})

    print_summary(results)

    output = {
        "run_at":       datetime.utcnow().isoformat(),
        "backend":      BACKEND_URL,
        "case_studies": results,
    }
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\n[OK] Results saved → {RESULTS_FILE}")


if __name__ == "__main__":
    main()
