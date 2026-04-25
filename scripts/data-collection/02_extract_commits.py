#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract commit history from cloned repositories"""

import os
import subprocess
import json
from datetime import datetime
import sys

# Fix Windows console encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
REPOS_DIR = os.path.join(PROJECT_ROOT, "data", "repos")

REPOS = [
    "joplin", "excalidraw", "react-admin", "strapi",
    "grafana", "ant-design-pro", "metabase", "discourse"
]

def extract_commits_from_repo(repo_name, max_commits=120):
    """Extract commit information from a repository"""
    repo_path = os.path.join(REPOS_DIR, repo_name)

    if not os.path.exists(repo_path):
        print(f"  [SKIP] Repository {repo_name} not found at {repo_path}")
        return []

    print(f"\n[{repo_name}] Extracting commits...")

    # Git command to get commit info
    # Format: hash|author|email|date|subject
    cmd = [
        "git", "log",
        "--pretty=format:%H|%an|%ae|%ad|%s",
        "--date=iso",
        f"-n{max_commits}",
        "--no-merges",
        "--",
        "*.tsx", "*.ts", "*.jsx", "*.js"
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            cwd=repo_path
        )

        commits = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue

            parts = line.split('|', 4)
            if len(parts) != 5:
                continue

            hash_val, author, email, date, subject = parts

            commits.append({
                "hash": hash_val,
                "repo": repo_name,
                "author": author,
                "email": email,
                "date": date,
                "subject": subject
            })

        print(f"  [OK] Extracted {len(commits)} commits")
        return commits

    except Exception as e:
        print(f"  [ERR] {e}")
        return []

def main():
    print("="*60)
    print("Commit Extraction")
    print("="*60)
    
    all_commits = []
    
    for repo in REPOS:
        commits = extract_commits_from_repo(repo)
        all_commits.extend(commits)
    
    print(f"\n✓ Total commits extracted: {len(all_commits)}")
    
    # Save to JSON
    output_file = os.path.join(PROJECT_ROOT, "data", "raw-commits", "all_commits.json")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, "w") as f:
        json.dump(all_commits, f, indent=2)
    
    print(f"✓ Saved to {output_file}")
    
    # Show statistics
    print("\nPer-repository breakdown:")
    repo_counts = {}
    for commit in all_commits:
        repo = commit['repo']
        repo_counts[repo] = repo_counts.get(repo, 0) + 1
    
    for repo, count in sorted(repo_counts.items()):
        print(f"  {repo}: {count} commits")

if __name__ == "__main__":
    main()