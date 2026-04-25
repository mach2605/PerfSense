#!/usr/bin/env python3
"""Retry failed repository clones with adjusted settings"""

import os
import subprocess
import json
from datetime import datetime

# Only the failed repos
FAILED_REPOS = {
    "grafana": "https://github.com/grafana/grafana.git",
    "metabase": "https://github.com/metabase/metabase.git"
}

def clone_repository(name, url, depth=500):  # Reduced depth
    """Clone a repository with limited depth"""
    target_dir = f"../../data/repos/{name}"
    
    if os.path.exists(target_dir):
        print(f"⏭️  {name} already exists, skipping...")
        return True
    
    print(f"📥 Cloning {name} (depth={depth})...")
    
    try:
        cmd = [
            "git", "clone",
            "--depth", str(depth),
            "--single-branch",  # Only main branch
            url,
            target_dir
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=900  # 15 minute timeout (increased)
        )
        
        if result.returncode == 0:
            print(f"✓ {name} cloned successfully")
            return True
        else:
            print(f"✗ Failed to clone {name}: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"✗ {name} clone timed out after 15 minutes")
        return False
    except Exception as e:
        print(f"✗ Error cloning {name}: {e}")
        return False

def main():
    print("="*60)
    print("Retry Failed Repositories")
    print("="*60)
    
    results = {}
    
    for name, url in FAILED_REPOS.items():
        success = clone_repository(name, url, depth=500)
        results[name] = success
    
    print("\n" + "="*60)
    print("RETRY RESULTS")
    print("="*60)
    for name, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {name}")

if __name__ == "__main__":
    main()