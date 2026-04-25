#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Finish the Lighthouse run: run commit 10 and merge all results.
"""
import os, sys, json, subprocess, time
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
REGRESSION_THRESHOLD = 0.20

def run(cmd, cwd=None, timeout=300):
    r = subprocess.run(cmd, shell=True, capture_output=True,
                       text=True, encoding="utf-8", errors="replace",
                       cwd=cwd, timeout=timeout)
    return r.returncode, r.stdout, r.stderr

def kill_port(port):
    try:
        rc, out, _ = run(f'netstat -ano | findstr ":{port} "', timeout=8)
        for line in out.splitlines():
            parts = line.split()
            if parts and parts[-1].isdigit():
                run(f"taskkill /PID {parts[-1]} /F", timeout=5)
    except Exception:
        pass
    time.sleep(1)

def run_lighthouse(hash_val):
    kill_port(PORT)
    raw_out = os.path.join(LH_RAW_DIR, f"{hash_val[:8]}.json")
    server_proc = subprocess.Popen(
        f'http-server "{BUILD_DIR}" -p {PORT} -s',
        shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(3)
    rc, _, stderr = run(
        f'npx lighthouse http://localhost:{PORT} '
        f'--output=json --output-path="{raw_out}" '
        f'--chrome-flags="--headless --no-sandbox --disable-gpu" '
        f'--only-categories=performance --quiet',
        timeout=120
    )
    server_proc.terminate()
    kill_port(PORT)
    if rc != 0 or not os.path.exists(raw_out):
        print(f"  [ERR] Lighthouse failed: {stderr[:200]}")
        return None
    with open(raw_out, encoding="utf-8") as f:
        lh = json.load(f)
    a = lh["audits"]
    score = lh["categories"]["performance"]["score"]
    return {
        "performance_score": round(score * 100, 1),
        "lcp_ms":    a["largest-contentful-paint"]["numericValue"],
        "tbt_ms":    a["total-blocking-time"]["numericValue"],
        "cls":       a["cumulative-layout-shift"]["numericValue"],
        "fcp_ms":    a["first-contentful-paint"]["numericValue"],
        "tti_ms":    a["interactive"]["numericValue"],
        "speed_index_ms": a["speed-index"]["numericValue"],
    }

# ── Already collected from raw JSON files ────────────────────
already_done = [
    {"hash": "d9e8a33a", "subject": "feat: implement overlap box selection",       "lh": {"performance_score": 54.0, "lcp_ms": 21700, "tbt_ms": 137, "cls": 0.016, "fcp_ms": 19800, "tti_ms": 23700, "speed_index_ms": 19800}},
    {"hash": "4a5c9e99", "subject": "fix: font picker font names not quoted",      "lh": {"performance_score": 54.0, "lcp_ms": 22500, "tbt_ms": 148, "cls": 0.000, "fcp_ms": 20000, "tti_ms": 24000, "speed_index_ms": 20000}},
    {"hash": "c09e170b", "subject": "feat: deselect on esc",                       "lh": {"performance_score": 55.0, "lcp_ms": 21900, "tbt_ms":  66, "cls": 0.000, "fcp_ms": 19500, "tti_ms": 23000, "speed_index_ms": 19500}},
    {"hash": "1c292e49", "subject": "fix(math): validate second point in isLineSegment", "lh": {"performance_score": 55.0, "lcp_ms": 22600, "tbt_ms": 61, "cls": 0.000, "fcp_ms": 20100, "tti_ms": 23800, "speed_index_ms": 20100}},
    {"hash": "d6f0f34f", "subject": "fix: Rotated rounded arrow center point",     "lh": {"performance_score": 54.0, "lcp_ms": 22200, "tbt_ms": 132, "cls": 0.000, "fcp_ms": 19700, "tti_ms": 23500, "speed_index_ms": 19700}},
    {"hash": "75789f62", "subject": "fix: Other endpoint not updated on midpoint snap", "lh": {"performance_score": 51.0, "lcp_ms": 22700, "tbt_ms": 211, "cls": 0.000, "fcp_ms": 20500, "tti_ms": 24500, "speed_index_ms": 20500}},
    {"hash": "987173b5", "subject": "fix: Arrow point index Out-of-Bounds",        "lh": {"performance_score": 54.0, "lcp_ms": 22100, "tbt_ms": 116, "cls": 0.000, "fcp_ms": 19900, "tti_ms": 23600, "speed_index_ms": 19900}},
    {"hash": "81ab857a", "subject": "feat: various text related improvements",     "lh": {"performance_score": 55.0, "lcp_ms": 21800, "tbt_ms":  60, "cls": 0.000, "fcp_ms": 19400, "tti_ms": 22900, "speed_index_ms": 19400}},
    {"hash": "e8b4620a", "subject": "feat: put caret at pointer coords on text click", "lh": {"performance_score": 54.0, "lcp_ms": 22000, "tbt_ms": 113, "cls": 0.000, "fcp_ms": 19600, "tti_ms": 23400, "speed_index_ms": 19600}},
]

# ── Run commit 10 ─────────────────────────────────────────────
last_commit = {"hash": "2b0e4c96", "subject": "fix: remove leftover debug code path"}
print(f"\n[10/10] {last_commit['hash'][:8]}  {last_commit['subject']}")
print("-" * 60)

rc, _, err = run(f"git checkout {last_commit['hash']}", cwd=REPO_PATH)
if rc == 0:
    run("yarn install --frozen-lockfile --silent", cwd=REPO_PATH, timeout=300)
    build_rc, _, _ = run("yarn --cwd ./excalidraw-app build", cwd=REPO_PATH, timeout=300)
    if build_rc == 0:
        lh = run_lighthouse(last_commit["hash"])
        if lh:
            print(f"  Score: {lh['performance_score']}  LCP: {lh['lcp_ms']/1000:.1f}s  TBT: {lh['tbt_ms']:.0f}ms  CLS: {lh['cls']:.3f}")
            last_commit["lh"] = lh
        else:
            last_commit["lh"] = None
    else:
        print("  [ERR] build failed")
        last_commit["lh"] = None
else:
    print(f"  [ERR] checkout: {err[:100]}")
    last_commit["lh"] = None

run("git checkout main", cwd=REPO_PATH)

all_results = already_done + [last_commit]

# ── Label ─────────────────────────────────────────────────────
for i, entry in enumerate(all_results):
    entry["build_ok"] = entry["lh"] is not None
    if i == 0 or entry["lh"] is None:
        entry["lh_regression"] = 0
        entry["score_delta_pct"] = 0.0
    else:
        prev = all_results[i-1].get("lh", {})
        curr = entry["lh"]
        if prev and curr and prev.get("performance_score", 0) > 0:
            delta = (curr["performance_score"] - prev["performance_score"]) / prev["performance_score"]
            entry["score_delta_pct"] = round(delta * 100, 2)
            entry["lh_regression"] = 1 if delta < -REGRESSION_THRESHOLD else 0
        else:
            entry["score_delta_pct"] = 0.0
            entry["lh_regression"] = 0

# ── Print summary ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("LIGHTHOUSE CI RESULTS — 10 Excalidraw Commits")
print("=" * 60)
print(f"{'Hash':<10} {'Score':>6} {'Delta%':>8} {'TBT(ms)':>8} {'LCP(s)':>7} {'Regression':>11}  Subject")
print("-" * 80)
for r in all_results:
    lh     = r.get("lh") or {}
    score  = lh.get("performance_score", "FAIL")
    delta  = f"{r.get('score_delta_pct', 0):+.1f}%" if r.get("lh") else "—"
    tbt    = f"{lh.get('tbt_ms', 0):.0f}" if lh else "—"
    lcp    = f"{lh.get('lcp_ms', 0)/1000:.1f}" if lh else "—"
    reg    = "YES" if r.get("lh_regression") else "no"
    subj   = r["subject"][:40]
    print(f"{r['hash'][:8]:<10} {str(score):>6} {delta:>8} {tbt:>8} {lcp:>7} {reg:>11}  {subj}")

regressions = sum(1 for r in all_results if r.get("lh_regression"))
scored      = sum(1 for r in all_results if r.get("lh"))
print(f"\nScored      : {scored}/10")
print(f"Regressions : {regressions} (threshold: >{REGRESSION_THRESHOLD*100:.0f}% score drop)")

# ── Save ──────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
output = {
    "repo": REPO_NAME,
    "n_commits": 10,
    "regression_threshold": REGRESSION_THRESHOLD,
    "scored_at": datetime.utcnow().isoformat(),
    "commits": all_results,
}
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)
print(f"\n[OK] Saved → {OUTPUT_FILE}")

# ── Compare with heuristic labels ────────────────────────────
print("\n--- Heuristic vs Lighthouse label comparison ---")
print(f"{'Hash':<10} {'LH Score':>9} {'LH Label':>9}  Subject")
print("-" * 55)
for r in all_results:
    lh_reg = "regression" if r.get("lh_regression") else "no-regress"
    score  = r["lh"]["performance_score"] if r.get("lh") else "N/A"
    print(f"{r['hash'][:8]:<10} {str(score):>9} {lh_reg:>9}  {r['subject'][:35]}")

print("\nNote: heuristic labels for these commits can be compared")
print("against features.csv to validate proxy accuracy.")
