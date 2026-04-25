#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PerfSense Commit Labeling Script

Labels each commit as regression (1) or no-regression (0) using a
multi-signal heuristic proxy — a practical alternative to running
Lighthouse CI on 960 historical commits (~48 hrs compute).

Academic justification (dissertation Section 5.6 / challenges):
  Running Lighthouse on historical commits requires checkout → install →
  build → serve → audit for every commit, which is infeasible at scale.
  This heuristic uses the 28 extracted code features to approximate the
  same signal, consistent with the "bundle size + code pattern" fallback
  described in the risk mitigation plan.

Scoring logic:
  Each commit receives a risk score from weighted signals.
  Score ≥ THRESHOLD → is_regression = 1.
  Threshold is auto-tuned to produce a ~10-15 % regression rate,
  matching the expected class distribution from the dissertation.

Outputs:
  data/features/features_labeled.csv   — full feature set + label
  data/labeled-commits/label_report.json — statistics and signal breakdown
"""

import os
import sys
import json
import csv
import pandas as pd
from collections import defaultdict

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
INPUT_FILE   = os.path.join(PROJECT_ROOT, "data", "features", "features.csv")
OUTPUT_FILE  = os.path.join(PROJECT_ROOT, "data", "features", "features_labeled.csv")
REPORT_FILE  = os.path.join(PROJECT_ROOT, "data", "labeled-commits", "label_report.json")

# Target regression rate (10–15 %)
TARGET_RATE_LOW  = 0.10
TARGET_RATE_HIGH = 0.15


# ─────────────────────────────────────────────────────────────
# SIGNAL DEFINITIONS
# Each entry: (column, condition_fn, weight, description)
# ─────────────────────────────────────────────────────────────

def build_signals(row):
    """
    Returns list of (signal_name, triggered: bool, weight, description).
    Positive weight → increases regression risk.
    Negative weight → decreases regression risk (protective).
    """
    signals = []

    # ── Positive signals (risk factors) ──────────────────────

    signals.append((
        "large_commit",
        row["large_commit"] == 1,
        3,
        "lines_added > 200 — large changes are higher regression risk"
    ))

    signals.append((
        "heavy_dep_added",
        row["package_json_changed"] == 1 and row["import_count_delta"] > 2,
        3,
        "package.json changed + >2 new imports — likely heavy dependency added"
    ))

    signals.append((
        "effect_without_optimization",
        row["useEffect_added"] > 0
        and row["useCallback_added"] == 0
        and row["useMemo_added"] == 0
        and row["memo_added"] == 0,
        2,
        "useEffect added without any memoization — common re-render cause"
    ))

    signals.append((
        "high_complexity_increase",
        row["complexity_delta"] > 5,
        2,
        "complexity_delta > 5 — significant increase in cyclomatic complexity"
    ))

    signals.append((
        "many_inline_arrows",
        row["inline_arrow_functions"] > 3,
        2,
        "inline_arrow_functions > 3 — breaks memoization for child components"
    ))

    signals.append((
        "many_component_files",
        row["files_in_components"] > 4,
        2,
        "files_in_components > 4 — wide component tree changes"
    ))

    signals.append((
        "nested_components",
        row["nested_components"] > 0,
        2,
        "nested_components > 0 — components defined inside components cause remount"
    ))

    signals.append((
        "debug_code_left",
        row["console_log_added"] > 1,
        1,
        "console_log_added > 1 — debug statements suggest rushed/incomplete work"
    ))

    signals.append((
        "moderate_complexity_increase",
        2 < row["complexity_delta"] <= 5,
        1,
        "complexity_delta 2-5 — moderate complexity increase"
    ))

    signals.append((
        "many_new_state_hooks",
        row["useState_added"] > 2,
        1,
        "useState_added > 2 — many new state variables increase re-render triggers"
    ))

    signals.append((
        "many_new_effects",
        row["useEffect_added"] > 2,
        1,
        "useEffect_added > 2 — many new side effects"
    ))

    # ── Protective signals (risk reducers) ───────────────────

    signals.append((
        "memoization_applied",
        row["memo_added"] > 0,
        -3,
        "memo_added > 0 — React.memo applied, optimization-aware change"
    ))

    signals.append((
        "callback_or_memo_hooks",
        row["useCallback_added"] > 0 or row["useMemo_added"] > 0,
        -2,
        "useCallback/useMemo added — developer is applying optimization"
    ))

    signals.append((
        "code_splitting_added",
        row["lazy_added"] > 0,
        -2,
        "lazy_added > 0 — React.lazy code splitting reduces bundle"
    ))

    signals.append((
        "net_code_removal",
        row["net_lines"] < -50,
        -1,
        "net_lines < -50 — significant code removal / cleanup commit"
    ))

    signals.append((
        "high_optimization_ratio",
        row["optimization_ratio"] > 1.5,
        -1,
        "optimization_ratio > 1.5 — optimizations outweigh hook additions"
    ))

    return signals


def score_commit(row):
    """Compute total risk score and list of triggered signal names."""
    signals = build_signals(row)
    total   = 0
    fired   = []
    for name, triggered, weight, desc in signals:
        if triggered:
            total += weight
            fired.append({"signal": name, "weight": weight, "desc": desc})
    return total, fired


# ─────────────────────────────────────────────────────────────
# AUTO-TUNE THRESHOLD
# ─────────────────────────────────────────────────────────────

def find_threshold(scores, target_low=TARGET_RATE_LOW, target_high=TARGET_RATE_HIGH):
    """
    Find the lowest integer threshold such that the regression rate
    falls within [target_low, target_high].
    Tries thresholds from high to low, picks first that satisfies range.
    Falls back to target ~12.5 % if no exact match.
    """
    n = len(scores)
    best_thresh = 4          # default
    best_diff   = float("inf")

    for thresh in range(1, 15):
        rate = sum(1 for s in scores if s >= thresh) / n
        if target_low <= rate <= target_high:
            return thresh
        diff = abs(rate - (target_low + target_high) / 2)
        if diff < best_diff:
            best_diff   = diff
            best_thresh = thresh

    return best_thresh


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("PerfSense — Commit Labeling (Heuristic Proxy)")
    print("=" * 60)

    df = pd.read_csv(INPUT_FILE)
    print(f"Loaded {len(df)} commits from {INPUT_FILE}\n")

    # Score every commit
    all_scores  = []
    all_signals = []

    for _, row in df.iterrows():
        score, fired = score_commit(row)
        all_scores.append(score)
        all_signals.append(fired)

    # Auto-tune threshold
    threshold = find_threshold(all_scores)
    labels    = [1 if s >= threshold else 0 for s in all_scores]

    regression_n = sum(labels)
    rate         = regression_n / len(labels)
    print(f"Threshold  : {threshold}")
    print(f"Regressions: {regression_n} / {len(labels)}  ({100*rate:.1f} %)")
    print(f"No-regress : {len(labels) - regression_n} / {len(labels)}\n")

    # Attach to dataframe
    df["regression_score"]  = all_scores
    df["is_regression"]     = labels

    # Per-repo breakdown
    print("Per-repo regression rate:")
    for repo in sorted(df["repo"].unique()):
        sub  = df[df["repo"] == repo]
        n    = len(sub)
        reg  = sub["is_regression"].sum()
        print(f"  {repo:<20}  {reg:>3}/{n}  ({100*reg/n:.1f} %)")

    # Signal frequency analysis
    signal_freq = defaultdict(lambda: {"count": 0, "regression_contrib": 0})
    for fired, label in zip(all_signals, labels):
        for s in fired:
            signal_freq[s["signal"]]["count"] += 1
            if label == 1:
                signal_freq[s["signal"]]["regression_contrib"] += 1

    print("\nSignal frequencies (in regression commits):")
    for sig, stats in sorted(signal_freq.items(),
                              key=lambda x: -x[1]["regression_contrib"]):
        print(f"  {sig:<35}  total={stats['count']:>4}  "
              f"in-regression={stats['regression_contrib']:>4}")

    # Save labeled CSV
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\n[OK] Labeled CSV → {OUTPUT_FILE}")

    # Save report
    os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
    report = {
        "total_commits":      len(df),
        "threshold":          threshold,
        "regression_count":   int(regression_n),
        "no_regression_count":int(len(labels) - regression_n),
        "regression_rate":    round(rate, 4),
        "target_range":       [TARGET_RATE_LOW, TARGET_RATE_HIGH],
        "per_repo": {
            repo: {
                "total":      int(len(df[df["repo"] == repo])),
                "regression": int(df[df["repo"] == repo]["is_regression"].sum()),
                "rate":       round(df[df["repo"] == repo]["is_regression"].mean(), 4)
            }
            for repo in sorted(df["repo"].unique())
        },
        "signal_frequencies": {
            k: {"count": v["count"], "regression_contrib": v["regression_contrib"]}
            for k, v in signal_freq.items()
        },
        "score_distribution": {
            str(s): int(all_scores.count(s))
            for s in sorted(set(all_scores))
        }
    }

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"[OK] Label report  → {REPORT_FILE}")


if __name__ == "__main__":
    main()
