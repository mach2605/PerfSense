#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PerfSense — Lighthouse CI Runner
Runs Lighthouse on N commits from a chosen repository.
Produces real ground-truth performance scores for a subset of commits.

Usage:
  python -X utf8 lighthouse_commits.py
"""

import os, sys, json, subprocess, time, shutil
from datetime import datetime

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

REPO_NAME    = "excalidraw"
REPO_PATH    = os.path.join(PROJECT_ROOT, "data", "repos", REPO_NAME)
BUILD_DIR    = os.path.join(REPO_PATH, "excalidraw-app", "build")
OUTPUT_FILE  = os.path.join(PROJECT_ROOT, "data", "lighthouse", "lighthouse_scores.json")
LH_RAW_DIR   = os.path.join(PROJECT_ROOT, "data", "lighthouse", "raw")

PORT         = 9900
N_COMMITS    = 10
REGRESSION_THRESHOLD = 0.20   # >20% drop in score = regression

# Commits to test — picked from recent non-merge JS/TS commits
# Mix of feature, fix, and chore commits for variety
COMMITS = [
    {"hash": "d9e8a33a", "subject": "feat: implement overlap box selection"},
    {"hash": "4a5c9e99", "subject": "fix: font picker font names not quoted"},
    {"hash": "c09e170b", "subject": "feat: deselect on esc"},
    {"hash": "1c292e49", "subject": "fix(math): validate second point in isLineSegment"},
    {"hash": "d6f0f34f", "subject": "fix: Rotated rounded arrow center point"},
    {"hash": "75789f62", "subject": "fix: Other endpoint not updated on midpoint snap"},
    {"hash": "987173b5", "subject": "fix: Arrow point index Out-of-Bounds"},
    {"hash": "81ab857a", "subject": "feat: various text related improvements"},
    {"hash": "e8b4620a", "subject": "feat: put caret at pointer coords on text click"},
    {"hash": "2b0e4c96", "subject": "fix: remove leftover debug code path"},
]

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
os.makedirs(LH_RAW_DIR, exist_ok=True)


def run(cmd, cwd=None, timeout=300):
    r = subprocess.run(
        cmd, shell=True, capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        cwd=cwd, timeout=timeout
    )
    return r.returncode, r.stdout, r.stderr


def kill_port(port):
    """Kill whatever process is on the given port (Windows-safe)."""
    try:
        # Windows: find PID using netstat, kill it
        rc, out, _ = run(
            f'netstat -ano | findstr ":{port} "',
            timeout=8
        )
        for line in out.splitlines():
            parts = line.split()
            if parts and parts[-1].isdigit():
                pid = parts[-1]
                run(f"taskkill /PID {pid} /F", timeout=5)
    except Exception:
        pass
    time.sleep(1)


def build_commit(hash_val):
    """Checkout, install (if needed), build. Returns True on success."""
    print(f"  Checking out {hash_val[:8]}...")
    rc, _, err = run(f"git checkout {hash_val}", cwd=REPO_PATH)
    if rc != 0:
        print(f"  [ERR] checkout failed: {err[:200]}")
        return False

    # Only re-install if package.json changed vs previous (heuristic: always install)
    print(f"  Installing dependencies...")
    rc, _, err = run("yarn install --frozen-lockfile --silent", cwd=REPO_PATH, timeout=300)
    if rc != 0:
        # Try without frozen lockfile if it fails
        rc, _, err = run("yarn install --silent", cwd=REPO_PATH, timeout=300)
    if rc != 0:
        print(f"  [ERR] install failed: {err[:200]}")
        return False

    print(f"  Building...")
    rc, _, err = run(
        "yarn --cwd ./excalidraw-app build",
        cwd=REPO_PATH, timeout=300
    )
    if rc != 0:
        print(f"  [ERR] build failed: {err[:300]}")
        return False

    if not os.path.isdir(BUILD_DIR):
        print(f"  [ERR] build dir not found: {BUILD_DIR}")
        return False

    return True


def run_lighthouse(hash_val):
    """Serve build and run Lighthouse. Returns score dict or None."""
    kill_port(PORT)

    raw_out = os.path.join(LH_RAW_DIR, f"{hash_val[:8]}.json")

    # Start server in background
    server_proc = subprocess.Popen(
        f"http-server \"{BUILD_DIR}\" -p {PORT} -s",
        shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(3)

    print(f"  Running Lighthouse on http://localhost:{PORT}...")
    rc, stdout, stderr = run(
        f'npx lighthouse http://localhost:{PORT} '
        f'--output=json --output-path="{raw_out}" '
        f'--chrome-flags="--headless --no-sandbox --disable-gpu" '
        f'--only-categories=performance --quiet',
        timeout=120
    )

    server_proc.terminate()
    server_proc.wait(timeout=5)
    kill_port(PORT)

    if rc != 0 or not os.path.exists(raw_out):
        print(f"  [ERR] Lighthouse failed (rc={rc}): {stderr[:200]}")
        return None

    with open(raw_out, encoding="utf-8") as f:
        lh = json.load(f)

    a = lh["audits"]
    score = lh["categories"]["performance"]["score"]

    return {
        "performance_score":    round(score * 100, 1),
        "lcp_ms":               a["largest-contentful-paint"]["numericValue"],
        "tbt_ms":               a["total-blocking-time"]["numericValue"],
        "cls":                  a["cumulative-layout-shift"]["numericValue"],
        "fcp_ms":               a["first-contentful-paint"]["numericValue"],
        "tti_ms":               a["interactive"]["numericValue"],
        "speed_index_ms":       a["speed-index"]["numericValue"],
    }


def label_with_lighthouse(scores):
    """
    Label each commit:
      - Compare perf score to previous commit
      - >20% relative drop = regression
    First commit: no regression by definition.
    """
    labeled = []
    for i, entry in enumerate(scores):
        if i == 0 or entry.get("lh") is None:
            entry["lh_regression"] = 0
            entry["score_delta_pct"] = 0.0
        else:
            prev_score = scores[i-1].get("lh", {}).get("performance_score")
            curr_score = entry.get("lh", {}).get("performance_score")
            if prev_score and curr_score and prev_score > 0:
                delta_pct = (curr_score - prev_score) / prev_score
                entry["score_delta_pct"] = round(delta_pct * 100, 2)
                entry["lh_regression"] = 1 if delta_pct < -REGRESSION_THRESHOLD else 0
            else:
                entry["score_delta_pct"] = 0.0
                entry["lh_regression"] = 0
        labeled.append(entry)
    return labeled


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print(f"PerfSense — Lighthouse CI Runner ({REPO_NAME})")
    print(f"Running {N_COMMITS} commits")
    print("=" * 60)

    results = []

    for i, commit in enumerate(COMMITS[:N_COMMITS]):
        h = commit["hash"]
        print(f"\n[{i+1}/{N_COMMITS}] {h[:8]}  {commit['subject'][:55]}")
        print("-" * 60)

        entry = {
            "hash":    h,
            "repo":    REPO_NAME,
            "subject": commit["subject"],
            "lh":      None,
            "build_ok": False,
        }

        build_ok = build_commit(h)
        entry["build_ok"] = build_ok

        if build_ok:
            lh_scores = run_lighthouse(h)
            entry["lh"] = lh_scores
            if lh_scores:
                print(f"  Score: {lh_scores['performance_score']}  "
                      f"LCP: {lh_scores['lcp_ms']/1000:.1f}s  "
                      f"TBT: {lh_scores['tbt_ms']:.0f}ms  "
                      f"CLS: {lh_scores['cls']:.3f}")
            else:
                print(f"  [WARN] Lighthouse failed for this commit")
        else:
            print(f"  [SKIP] Build failed, skipping Lighthouse")

        results.append(entry)

    # Restore repo to latest
    run("git checkout main", cwd=REPO_PATH)

    # Label
    results = label_with_lighthouse(results)

    # Summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    print(f"{'Hash':<10} {'Score':>6} {'Delta%':>8} {'Regression':>11}  Subject")
    print("-" * 70)
    for r in results:
        score  = r["lh"]["performance_score"] if r["lh"] else "FAIL"
        delta  = f"{r.get('score_delta_pct', 0):+.1f}%" if r["lh"] else "—"
        reg    = "YES ⚠" if r.get("lh_regression") else "no"
        subj   = r["subject"][:45]
        print(f"{r['hash'][:8]:<10} {str(score):>6} {delta:>8} {reg:>11}  {subj}")

    regressions = sum(1 for r in results if r.get("lh_regression"))
    successes   = sum(1 for r in results if r.get("lh"))
    print(f"\nBuilt & scored: {successes}/{N_COMMITS}")
    print(f"Regressions   : {regressions}/{successes} "
          f"({100*regressions/max(1,successes):.0f}%)")

    # Save
    output = {
        "repo":                REPO_NAME,
        "n_commits":           N_COMMITS,
        "regression_threshold": REGRESSION_THRESHOLD,
        "scored_at":           datetime.utcnow().isoformat(),
        "commits":             results,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\n[OK] Results saved → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
