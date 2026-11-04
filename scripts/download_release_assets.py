#!/usr/bin/env python3
"""
Downloads all assets for a given GitHub release tag.
"""
import argparse
import os
import sys
import time
import urllib.request
import json

REPO = "motionssalt/kl5-axion-gsi"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    parser.add_argument("--dest", required=True)
    parser.add_argument("--token", default=os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN", ""))
    args = parser.parse_args()

    os.makedirs(args.dest, exist_ok=True)
    url = f"https://api.github.com/repos/{REPO}/releases/tags/{args.tag}"
    req = urllib.request.Request(url)
    if args.token:
        req.add_header("Authorization", f"Bearer {args.token}")
    req.add_header("Accept", "application/vnd.github+json")
    
    with urllib.request.urlopen(req) as resp:
        rel = json.loads(resp.read().decode('utf-8'))
    
    assets = rel.get("assets", [])
    print(f"Downloading {len(assets)} assets for release {args.tag} into {args.dest}...")
    for a in assets:
        name = a["name"]
        dl_url = a["browser_download_url"]
        dst_path = os.path.join(args.dest, name)
        print(f"  Downloading {name} ({a['size']} bytes)...")
        # retry loop
        for attempt in range(3):
            try:
                urllib.request.urlretrieve(dl_url, dst_path)
                break
            except Exception as e:
                print(f"  [WARN] Attempt {attempt+1} failed: {e}")
                time.sleep(2)
        else:
            raise RuntimeError(f"Failed to download asset {name}")

    print(f"[SUCCESS] Downloaded all assets for {args.tag} to {args.dest}")

if __name__ == '__main__':
    main()
