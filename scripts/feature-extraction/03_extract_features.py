#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PerfSense Feature Extraction Pipeline
Extracts 28 performance-relevant features from each commit's git diff.

Feature groups:
  F1-F8   : Static Code Metrics
  F9-F20  : React-Specific Pattern Features
  F21-F28 : Historical Context Features
"""

import os
import sys
import json
import re
import subprocess
import csv
from datetime import datetime, timedelta
from collections import defaultdict

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
REPOS_DIR    = os.path.join(PROJECT_ROOT, "data", "repos")
COMMITS_FILE = os.path.join(PROJECT_ROOT, "data", "raw-commits", "all_commits.json")
OUTPUT_FILE  = os.path.join(PROJECT_ROOT, "data", "features", "features.csv")

# ─────────────────────────────────────────────────────────────
# GIT HELPERS
# ─────────────────────────────────────────────────────────────

def get_diff(repo_path, commit_hash, timeout=20):
    """Return the unified diff for a commit (JS/TS files only)."""
    try:
        r = subprocess.run(
            ["git", "show", "--no-color", commit_hash,
             "--", "*.ts", "*.tsx", "*.js", "*.jsx"],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=timeout, cwd=repo_path
        )
        return r.stdout
    except Exception:
        return ""


def parse_diff(diff_text):
    """
    Split diff text into:
      added_lines  – lines beginning with '+' (content only)
      removed_lines– lines beginning with '-' (content only)
      changed_files– list of file paths touched
    """
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
    return added, removed, files


# ─────────────────────────────────────────────────────────────
# PATTERN COUNTING HELPERS
# ─────────────────────────────────────────────────────────────

def count(lines, pattern, flags=0):
    """Count total regex matches across all lines."""
    rx = re.compile(pattern, flags)
    return sum(len(rx.findall(l)) for l in lines)


# ─────────────────────────────────────────────────────────────
# F1–F8 : STATIC CODE METRICS
# ─────────────────────────────────────────────────────────────

def f1_files_changed(files):
    return len(files)

def f2_files_in_components(files):
    return sum(1 for f in files if re.search(r"[/\\]components?[/\\]", f, re.I))

def f3_lines_added(added):
    return len(added)

def f4_lines_deleted(removed):
    return len(removed)

def f5_net_lines(added, removed):
    return len(added) - len(removed)

def f6_large_commit(added):
    return 1 if len(added) > 200 else 0

def f7_package_json_changed(files):
    return 1 if any("package.json" in f for f in files) else 0

def f8_complexity_delta(added, removed):
    """Approximate cyclomatic complexity via control-flow keywords."""
    pat = r"\b(if|else\s+if|switch|case|\?|for|while|catch)\b"
    return count(added, pat) - count(removed, pat)


# ─────────────────────────────────────────────────────────────
# F9–F20 : REACT-SPECIFIC PATTERN FEATURES
# ─────────────────────────────────────────────────────────────

def f9_useEffect_added(added):
    return count(added, r"\buseEffect\s*\(")

def f10_useState_added(added):
    return count(added, r"\buseState\s*\(")

def f11_useCallback_added(added):
    return count(added, r"\buseCallback\s*\(")

def f12_useMemo_added(added):
    return count(added, r"\buseMemo\s*\(")

def f13_useContext_added(added):
    return count(added, r"\buseContext\s*\(")

def f14_useReducer_added(added):
    return count(added, r"\buseReducer\s*\(")

def f15_memo_added(added):
    # Match React.memo( or assignment = memo(
    return count(added, r"React\.memo\s*\(|=\s*memo\s*\(")

def f16_lazy_added(added):
    return count(added, r"React\.lazy\s*\(|=\s*lazy\s*\(")

def f17_inline_arrow_functions(added):
    """JSX event handler props with inline arrow functions."""
    return count(added, r"on[A-Z]\w*\s*=\s*\{(?:async\s+)?(?:\([^)]*\)|[a-zA-Z_]\w*)\s*=>")

def f18_console_log_added(added):
    return count(added, r"\bconsole\.(log|warn|error|debug)\s*\(")

def f19_import_count_delta(added, removed):
    pat = r"^\s*import\s+"
    return count(added, pat) - count(removed, pat)

def f20_nested_components(added):
    """
    Heuristic: capitalized component-looking definitions with leading
    indentation (≥2 spaces) suggest they are nested inside a parent.
    """
    return count(
        added,
        r"^\s{2,}(?:export\s+)?(?:const\s+[A-Z]\w+\s*=|function\s+[A-Z]\w*\s*\()"
    )


# ─────────────────────────────────────────────────────────────
# F21–F28 : HISTORICAL CONTEXT FEATURES
# ─────────────────────────────────────────────────────────────

def f24_deployment_frequency(commit_dt, repo_dates):
    """Commits in the same repo in the 7 days preceding this commit."""
    cutoff = commit_dt - timedelta(days=7)
    return sum(1 for d in repo_dates if cutoff <= d < commit_dt)

def f25_bundle_size_delta(f7, f19):
    """
    Proxy for bundle size change (real value requires builds).
    Positive import delta on a package.json-touching commit hints
    at heavier dependencies being added.
    """
    if f7 and f19 > 0:
        return round(min(f19 * 2.0, 50.0), 2)   # cap at 50 % proxy
    return 0.0

def f26_component_count_delta(added, removed):
    """Net change in PascalCase component definitions."""
    pat = r"^\s*(?:export\s+)?(?:default\s+)?(?:const\s+[A-Z]\w+\s*=|function\s+[A-Z]\w*\s*\()"
    return count(added, pat) - count(removed, pat)

def f27_hook_density(added, comp_delta):
    """Total hook usages added / max(1, |component delta| + 1)."""
    hooks = sum([
        count(added, r"\buseEffect\s*\("),
        count(added, r"\buseState\s*\("),
        count(added, r"\buseCallback\s*\("),
        count(added, r"\buseMemo\s*\("),
        count(added, r"\buseContext\s*\("),
        count(added, r"\buseReducer\s*\("),
    ])
    return round(hooks / max(1, abs(comp_delta) + 1), 4)

def f28_optimization_ratio(f11, f12, f15, f16, f9, f10):
    """(optimizing hooks added) / max(1, state/effect hooks added)."""
    return round((f15 + f16 + f11 + f12) / max(1, f9 + f10), 4)


# ─────────────────────────────────────────────────────────────
# MAIN EXTRACTION
# ─────────────────────────────────────────────────────────────

def extract_features(commit, repo_path, repo_dates):
    diff              = get_diff(repo_path, commit["hash"])
    added, removed, files = parse_diff(diff)

    # ── Static Code Metrics ──────────────────────────────────
    v_f1  = f1_files_changed(files)
    v_f2  = f2_files_in_components(files)
    v_f3  = f3_lines_added(added)
    v_f4  = f4_lines_deleted(removed)
    v_f5  = f5_net_lines(added, removed)
    v_f6  = f6_large_commit(added)
    v_f7  = f7_package_json_changed(files)
    v_f8  = f8_complexity_delta(added, removed)

    # ── React-Specific Patterns ──────────────────────────────
    v_f9  = f9_useEffect_added(added)
    v_f10 = f10_useState_added(added)
    v_f11 = f11_useCallback_added(added)
    v_f12 = f12_useMemo_added(added)
    v_f13 = f13_useContext_added(added)
    v_f14 = f14_useReducer_added(added)
    v_f15 = f15_memo_added(added)
    v_f16 = f16_lazy_added(added)
    v_f17 = f17_inline_arrow_functions(added)
    v_f18 = f18_console_log_added(added)
    v_f19 = f19_import_count_delta(added, removed)
    v_f20 = f20_nested_components(added)

    # ── Historical Context ───────────────────────────────────
    try:
        commit_dt = datetime.fromisoformat(commit["date"][:19])
    except Exception:
        commit_dt = datetime.now()

    # F21-F23 require Lighthouse scores → sentinel -1 (filled by labeling script)
    v_f21 = -1      # previous_commit_performance
    v_f22 = 0.0     # performance_trend_7d
    v_f23 = -1      # time_since_last_regression

    v_f24 = f24_deployment_frequency(commit_dt, repo_dates)
    v_f25 = f25_bundle_size_delta(v_f7, v_f19)
    v_f26 = f26_component_count_delta(added, removed)
    v_f27 = f27_hook_density(added, v_f26)
    v_f28 = f28_optimization_ratio(v_f11, v_f12, v_f15, v_f16, v_f9, v_f10)

    return {
        # Metadata (not features, kept for joining/labeling)
        "hash":    commit["hash"],
        "repo":    commit["repo"],
        "date":    commit["date"],
        "author":  commit["author"],
        "subject": commit["subject"][:120],
        # F1–F8 Static Code Metrics
        "files_changed":        v_f1,
        "files_in_components":  v_f2,
        "lines_added":          v_f3,
        "lines_deleted":        v_f4,
        "net_lines":            v_f5,
        "large_commit":         v_f6,
        "package_json_changed": v_f7,
        "complexity_delta":     v_f8,
        # F9–F20 React-Specific Patterns
        "useEffect_added":         v_f9,
        "useState_added":          v_f10,
        "useCallback_added":       v_f11,
        "useMemo_added":           v_f12,
        "useContext_added":        v_f13,
        "useReducer_added":        v_f14,
        "memo_added":              v_f15,
        "lazy_added":              v_f16,
        "inline_arrow_functions":  v_f17,
        "console_log_added":       v_f18,
        "import_count_delta":      v_f19,
        "nested_components":       v_f20,
        # F21–F28 Historical Context
        "previous_commit_performance": v_f21,
        "performance_trend_7d":        v_f22,
        "time_since_last_regression":  v_f23,
        "deployment_frequency":        v_f24,
        "bundle_size_delta":           v_f25,
        "component_count_delta":       v_f26,
        "hook_density":                v_f27,
        "optimization_ratio":          v_f28,
        # Label placeholder — filled by labeling script
        "is_regression": -1,
    }


def print_stats(results):
    """Print summary statistics for key features."""
    cols = [
        "files_changed", "lines_added", "lines_deleted",
        "useEffect_added", "useState_added", "useCallback_added",
        "inline_arrow_functions", "console_log_added", "import_count_delta",
    ]
    print("\nFeature statistics (nonzero | mean | max):")
    for col in cols:
        vals = [r[col] for r in results]
        nonzero = sum(1 for v in vals if v != 0)
        mean    = sum(vals) / len(vals) if vals else 0
        mx      = max(vals) if vals else 0
        print(f"  {col:<30} nonzero={nonzero:>4}  mean={mean:>7.2f}  max={mx}")


def main():
    print("=" * 60)
    print("PerfSense — Feature Extraction Pipeline")
    print("=" * 60)

    with open(COMMITS_FILE, encoding="utf-8") as f:
        commits = json.load(f)
    print(f"Loaded {len(commits)} commits\n")

    # Pre-build per-repo datetime lists for F24
    repo_dates = defaultdict(list)
    for c in commits:
        try:
            repo_dates[c["repo"]].append(datetime.fromisoformat(c["date"][:19]))
        except Exception:
            pass

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    results = []
    errors  = 0

    for i, commit in enumerate(commits):
        repo_path = os.path.join(REPOS_DIR, commit["repo"])

        if (i + 1) % 100 == 0 or i == 0:
            print(f"  [{i+1:>4}/{len(commits)}] repo={commit['repo']:<16} errors={errors}")

        try:
            row = extract_features(commit, repo_path, repo_dates[commit["repo"]])
            results.append(row)
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  [ERR] {commit['repo']}/{commit['hash'][:8]}: {e}")

    # Write CSV
    fieldnames = list(results[0].keys())
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n[OK] Extracted {len(results)}/{len(commits)} commits  ({errors} errors)")
    print(f"[OK] Saved → {OUTPUT_FILE}")

    print_stats(results)

    # Per-repo breakdown
    print("\nPer-repo commit counts:")
    repo_counts = defaultdict(int)
    for r in results:
        repo_counts[r["repo"]] += 1
    for repo, n in sorted(repo_counts.items()):
        print(f"  {repo:<20} {n}")


if __name__ == "__main__":
    main()
