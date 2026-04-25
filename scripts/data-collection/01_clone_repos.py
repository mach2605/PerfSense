#!/usr/bin/env python3
"""Clone target repositories for analysis"""

import os
import subprocess
import json
from datetime import datetime

# Repository configuration
REPOS = {
    "joplin": "https://github.com/laurent22/joplin.git",
    "excalidraw": "https://github.com/excalidraw/excalidraw.git",
    "react-admin": "https://github.com/marmelab/react-admin.git",
    "strapi": "https://github.com/strapi/strapi.git",
    "grafana": "https://github.com/grafana/grafana.git",
    "ant-design-pro": "https://github.com/ant-design/ant-design-pro.git",
    "metabase": "https://github.com/metabase/metabase.git",
    "discourse": "https://github.com/discourse/discourse.git"
}

def clone_repository(name, url, depth=1000):
    """Clone a repository with limited depth"""
    target_dir = f"../../data/repos/{name}"
    
    if os.path.exists(target_dir):
        print(f"⏭️  {name} already exists, skipping...")
        return True
    
    print(f"📥 Cloning {name}...")
    
    try:
        # Clone with depth limit to save time/space
        cmd = [
            "git", "clone",
            "--depth", str(depth),
            url,
            target_dir
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        if result.returncode == 0:
            print(f"✓ {name} cloned successfully")
            return True
        else:
            print(f"✗ Failed to clone {name}: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"✗ {name} clone timed out")
        return False
    except Exception as e:
        print(f"✗ Error cloning {name}: {e}")
        return False

def main():
    print("="*60)
    print("PerfSense Repository Cloning")
    print("="*60)
    
    os.makedirs("../../data/repos", exist_ok=True)
    
    results = {}
    start_time = datetime.now()
    
    for name, url in REPOS.items():
        success = clone_repository(name, url)
        results[name] = success
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    successful = sum(1 for v in results.values() if v)
    print(f"Successful: {successful}/{len(REPOS)}")
    print(f"Duration: {duration:.1f} seconds")
    
    print("\nResults:")
    for name, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {name}")
    
    # Save results
    with open("../../data/clone_results.json", "w") as f:
        json.dump({
            "timestamp": start_time.isoformat(),
            "duration_seconds": duration,
            "results": results
        }, f, indent=2)
    
    print(f"\n✓ Results saved to data/clone_results.json")

if __name__ == "__main__":
    main()