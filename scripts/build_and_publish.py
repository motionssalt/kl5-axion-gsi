#!/usr/bin/env python3
"""
Full automation script to build and publish:
1. stock-b-v1 (TECNO KL5 Stock Firmware converted for Slot B)
2. gsi-b-v1 (Axion 2.9 GSI prepared for Slot B)
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import requests

REPO = "motionssalt/kl5-axion-gsi"
STOCK_ZIP_SHA256 = "9aa24d0518815a16b2d3c532825379b99595fdb701918c0dbeae738fa877b257"
AXION_GSI_URL = "https://github.com/Doze-off/axion_aosp/releases/download/2026-10-17/Axion-2.9-GSI_treble_arm64-ab-GAPPS-20261017.img.xz"
LPUNPACK_URL = "https://raw.githubusercontent.com/unix3dgforce/lpunpack/c59b8f3b069c5a8aa438a049fa4a091177172434/lpunpack.py"

PHYSICAL_IMAGES = [
    "boot.img", "vendor_boot.img", "dtbo.img", "vbmeta.img",
    "vbmeta_system.img", "vbmeta_vendor.img", "md1img.img", "spmfw.img",
    "scp.img", "sspm.img", "gz.img", "lk.img", "logo.bin", "tee.img", "tkv.img"
]

LOGICAL_PARTITIONS = [
    "product_a", "system_a", "system_ext_a", "vendor_a",
    "tr_product_a", "tr_mi_a", "tr_theme_a", "tr_preload_a",
    "tr_region_a", "tr_company_a", "tr_carrier_a"
]

def run(cmd, cwd=None, check=True):
    print(f"[*] Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    res = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), check=check)
    return res

def compute_sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(16 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()

def github_create_or_update_release(token, tag, name, body, assets_dir):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    # Check if release exists
    url = f"https://api.github.com/repos/{REPO}/releases/tags/{tag}"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        rel = r.json()
        print(f"[*] Release {tag} already exists (ID {rel['id']}). Deleting old assets...")
        for asset in rel.get("assets", []):
            del_url = f"https://api.github.com/repos/{REPO}/releases/assets/{asset['id']}"
            requests.delete(del_url, headers=headers)
        # Update release metadata
        up_url = f"https://api.github.com/repos/{REPO}/releases/{rel['id']}"
        requests.patch(up_url, headers=headers, json={"name": name, "body": body})
        rel_id = rel["id"]
    else:
        print(f"[*] Creating new release: {tag}...")
        create_url = f"https://api.github.com/repos/{REPO}/releases"
        payload = {
            "tag_name": tag,
            "target_commitish": "main",
            "name": name,
            "body": body,
            "draft": False,
            "prerelease": False
        }
        res = requests.post(create_url, headers=headers, json=payload)
        if res.status_code not in (200, 201):
            raise RuntimeError(f"Failed to create release {tag}: {res.status_code} {res.text}")
        rel_id = res.json()["id"]

    # Upload assets
    upload_base = f"https://uploads.github.com/repos/{REPO}/releases/{rel_id}/assets"
    for fname in sorted(os.listdir(assets_dir)):
        fpath = os.path.join(assets_dir, fname)
        if not os.path.isfile(fpath):
            continue
        print(f"[*] Uploading asset {fname} ({os.path.getsize(fpath)} bytes)...")
        with open(fpath, "rb") as f:
            up_headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/octet-stream"
            }
            up_url = f"{upload_base}?name={fname}"
            # Retry up to 3 times on transient network error
            for attempt in range(3):
                up_res = requests.post(up_url, headers=up_headers, data=f)
                if up_res.status_code in (200, 201):
                    print(f"  [OK] Uploaded {fname}")
                    break
                else:
                    print(f"  [WARN] Attempt {attempt+1} failed: {up_res.status_code} {up_res.text}")
                    time.sleep(3)
                    f.seek(0)
            else:
                raise RuntimeError(f"Failed to upload asset {fname} after 3 attempts.")

def build_stock(work_dir, token, repo_root):
    print("\n====================================================================")
    print(" STEP 1: BUILDING STOCK PACKAGE FOR SLOT B")
    print("====================================================================")
    stock_dir = os.path.join(work_dir, "stock_build")
    os.makedirs(stock_dir, exist_ok=True)
    
    # 1. Download stock mirror parts
    print("[*] Downloading 4 stock parts from stock-mirror release...")
    part_urls = [
        f"https://github.com/{REPO}/releases/download/stock-mirror/stock-part-0001",
        f"https://github.com/{REPO}/releases/download/stock-mirror/stock-part-0002",
        f"https://github.com/{REPO}/releases/download/stock-mirror/stock-part-0003",
        f"https://github.com/{REPO}/releases/download/stock-mirror/stock-part-0004"
    ]
    part_files = []
    for i, u in enumerate(part_urls, 1):
        dst = os.path.join(stock_dir, f"stock.part{i:03d}")
        part_files.append(dst)
        if not os.path.exists(dst):
            print(f"  Downloading part {i}/4...")
            run(["curl", "-sL", u, "-o", dst])
    
    # 2. Join parts into stock.zip
    stock_zip = os.path.join(stock_dir, "stock.zip")
    if not os.path.exists(stock_zip):
        print("[*] Joining stock.zip from parts...")
        with open(stock_zip, "wb") as out_f:
            for pf in part_files:
                with open(pf, "rb") as in_f:
                    shutil.copyfileobj(in_f, out_f)
        # Delete parts to free space
        for pf in part_files:
            os.remove(pf)
    
    # 3. Verify SHA256
    print("[*] Verifying stock.zip SHA256...")
    actual_sha = compute_sha256(stock_zip)
    if actual_sha != STOCK_ZIP_SHA256:
        raise ValueError(f"stock.zip SHA256 mismatch! Got {actual_sha}, expected {STOCK_ZIP_SHA256}")
    print(f"  [OK] SHA256 verified: {actual_sha}")
    
    # 4. Extract firmware images
    extract_dir = os.path.join(stock_dir, "extracted")
    os.makedirs(extract_dir, exist_ok=True)
    print("[*] Unzipping firmware images from stock.zip...")
    run(["unzip", "-q", stock_zip, "Tecno_Spark_30C_KL5_MT6768_OP_V1085_240811/Firmware/*", "-d", extract_dir])
    os.remove(stock_zip) # free 6.5 GB
    
    firmware_dir = os.path.join(extract_dir, "Tecno_Spark_30C_KL5_MT6768_OP_V1085_240811", "Firmware")
    pkg_dir = os.path.join(stock_dir, "pkg")
    os.makedirs(pkg_dir, exist_ok=True)
    
    # 5. Copy physical images
    print("[*] Staging physical partition images...")
    for img in PHYSICAL_IMAGES:
        src = os.path.join(firmware_dir, img)
        if os.path.exists(src):
            dst = os.path.join(pkg_dir, img)
            shutil.copy2(src, dst)
            print(f"  Staged physical: {img} ({os.path.getsize(dst)} bytes)")
        else:
            print(f"  [NOTICE] Physical image {img} not present in stock archive.")
            
    # 6. Process super.img
    super_img = os.path.join(firmware_dir, "super.img")
    super_raw = os.path.join(stock_dir, "super.raw.img")
    print("[*] Converting sparse super.img to raw...")
    run(["simg2img", super_img, super_raw])
    os.remove(super_img) # free 5.4 GB
    
    # Download lpunpack.py
    lpunpack_py = os.path.join(stock_dir, "lpunpack.py")
    if not os.path.exists(lpunpack_py):
        run(["curl", "-sL", LPUNPACK_URL, "-o", lpunpack_py])
        
    logical_dir = os.path.join(stock_dir, "logical")
    os.makedirs(logical_dir, exist_ok=True)
    print("[*] Extracting populated _a logical partitions with lpunpack...")
    partitions_arg = ",".join(LOGICAL_PARTITIONS)
    run(["python3", lpunpack_py, "-p", partitions_arg, super_raw, logical_dir])
    os.remove(super_raw) # free 8.5 GB
    
    # 7. Convert logical partitions to sparse images
    print("[*] Converting logical partitions to fastboot sparse images...")
    large_logicals = ["product_a.img", "system_a.img", "system_ext_a.img", "vendor_a.img"]
    for l_img in large_logicals:
        raw_path = os.path.join(logical_dir, l_img)
        target_name = l_img.replace("_a.img", ".img")
        out_sparse = os.path.join(pkg_dir, target_name)
        print(f"  Converting {l_img} ({os.path.getsize(raw_path)} bytes) -> sparse {target_name}...")
        run(["img2simg", raw_path, out_sparse])
        os.remove(raw_path)
        
    # Copy smaller logical partitions (tr_*)
    for fname in os.listdir(logical_dir):
        if fname.endswith(".img"):
            raw_path = os.path.join(logical_dir, fname)
            target_name = fname.replace("_a.img", ".img")
            out_path = os.path.join(pkg_dir, target_name)
            shutil.copy2(raw_path, out_path)
            print(f"  Staged OEM logical: {target_name} ({os.path.getsize(out_path)} bytes)")
            
    shutil.rmtree(logical_dir, ignore_errors=True)
    shutil.rmtree(extract_dir, ignore_errors=True)
    
    # 8. Run prepare_package.py to split files > 1900MB and build manifest & checksums
    dist_stock = os.path.join(stock_dir, "dist_stock")
    prepare_py = os.path.join(repo_root, "scripts", "prepare_package.py")
    print("[*] Packaging stock assets (splitting files > 1,900 MB, generating manifest and hashes)...")
    run(["python3", prepare_py, "--pkg-dir", pkg_dir, "--out-dir", dist_stock, "--mode", "stock"])
    
    # Copy batch scripts, README.txt, and SUPER_LAYOUT.md into release package
    shutil.copy2(os.path.join(repo_root, "stock-b", "1_reassemble.bat"), os.path.join(dist_stock, "1_reassemble.bat"))
    shutil.copy2(os.path.join(repo_root, "stock-b", "2_flash_stock_b.bat"), os.path.join(dist_stock, "2_flash_stock_b.bat"))
    shutil.copy2(os.path.join(repo_root, "stock-b", "README.txt"), os.path.join(dist_stock, "README.txt"))
    shutil.copy2(os.path.join(repo_root, "evidence", "stock-b", "SUPER_LAYOUT.md"), os.path.join(dist_stock, "SUPER_LAYOUT.md"))
    
    # 9. Publish release stock-b-v1
    body = (
        "## TECNO KL5 (Spark 30C / MT6768) Stock Firmware - Slot B Flash Package\n\n"
        "This release contains the complete stock ROM converted and prepared specifically for **Slot B**.\n\n"
        "### Instructions:\n"
        "1. Download all assets into your Android platform-tools folder.\n"
        "2. Run `1_reassemble.bat` to rejoin parts and verify SHA-256 hashes.\n"
        "3. Connect your phone in fastboot mode.\n"
        "4. Run `2_flash_stock_b.bat` to flash all physical partitions (bootloader) and logical partitions (fastbootd) into `_b`.\n\n"
        "### Rooting with Magisk:\n"
        "The GKI ramdisk is embedded inside `boot.img` (there is no `init_boot.img`). "
        "Patch `boot.img` with Magisk and flash to `boot_b` (`fastboot flash boot_b magisk_patched.img`).\n"
    )
    github_create_or_update_release(token, "stock-b-v1", "TECNO KL5 Stock Firmware (Slot B)", body, dist_stock)
    print("\n[SUCCESS] stock-b-v1 published successfully!")

def build_gsi(work_dir, token, repo_root):
    print("\n====================================================================")
    print(" STEP 2: BUILDING AXION 2.9 GSI PACKAGE FOR SLOT B")
    print("====================================================================")
    gsi_dir = os.path.join(work_dir, "gsi_build")
    os.makedirs(gsi_dir, exist_ok=True)
    
    # 1. Download Axion 2.9 GSI .img.xz
    gsi_xz = os.path.join(gsi_dir, "Axion-2.9-GSI.img.xz")
    if not os.path.exists(gsi_xz):
        print("[*] Downloading Axion 2.9 GSI image...")
        run(["curl", "-sL", AXION_GSI_URL, "-o", gsi_xz])
        
    # 2. Decompress
    gsi_img = os.path.join(gsi_dir, "system.raw.img")
    print("[*] Decompressing GSI xz archive...")
    run(["xz", "-dc", gsi_xz], cwd=gsi_dir)
    # xz decompresses to system.raw.img via pipe or unxz
    run(f"unxz -k -c {gsi_xz} > {gsi_img}", shell=True)
    os.remove(gsi_xz) # free space
    
    pkg_dir = os.path.join(gsi_dir, "pkg")
    os.makedirs(pkg_dir, exist_ok=True)
    
    # 3. Convert GSI raw image to sparse system.img
    sparse_gsi = os.path.join(pkg_dir, "system.img")
    print(f"[*] Converting GSI raw image ({os.path.getsize(gsi_img)} bytes) to sparse format...")
    run(["img2simg", gsi_img, sparse_gsi])
    os.remove(gsi_img)
    
    # 4. Include clean stock vbmeta.img from stock-b package
    stock_vbmeta = os.path.join(work_dir, "stock_build", "pkg", "vbmeta.img")
    if not os.path.exists(stock_vbmeta):
        # Fetch from repo or release
        stock_vbmeta = os.path.join(repo_root, "stock-b", "vbmeta.img")
        if not os.path.exists(stock_vbmeta):
            run(["curl", "-sL", f"https://github.com/{REPO}/releases/download/stock-b-v1/vbmeta.img", "-o", os.path.join(pkg_dir, "vbmeta.img")])
    if os.path.exists(stock_vbmeta):
        shutil.copy2(stock_vbmeta, os.path.join(pkg_dir, "vbmeta.img"))
        
    # 5. Run prepare_package.py
    dist_gsi = os.path.join(gsi_dir, "dist_gsi")
    prepare_py = os.path.join(repo_root, "scripts", "prepare_package.py")
    print("[*] Packaging GSI assets...")
    run(["python3", prepare_py, "--pkg-dir", pkg_dir, "--out-dir", dist_gsi, "--mode", "gsi"])
    
    # Copy batch scripts and README.txt into release package
    shutil.copy2(os.path.join(repo_root, "gsi-b", "1_reassemble.bat"), os.path.join(dist_gsi, "1_reassemble.bat"))
    shutil.copy2(os.path.join(repo_root, "gsi-b", "3_flash_gsi_b.bat"), os.path.join(dist_gsi, "3_flash_gsi_b.bat"))
    shutil.copy2(os.path.join(repo_root, "gsi-b", "README.txt"), os.path.join(dist_gsi, "README.txt"))
    
    # 6. Publish release gsi-b-v1
    body = (
        "## TECNO KL5 (Spark 30C / MT6768) Axion 2.9 GSI - Slot B Flash Package\n\n"
        "This release contains the Axion 2.9 GSI (Android 16, Treble arm64-ab with GAPPS) prepared for **Slot B**.\n\n"
        "### Instructions:\n"
        "1. Ensure you have flashed the `stock-b-v1` package first to establish clean stock drivers in `vendor_b`.\n"
        "2. Download all files from this release into your platform-tools folder.\n"
        "3. Run `1_reassemble.bat` to join split parts and verify hashes.\n"
        "4. Put device in fastboot mode and run `3_flash_gsi_b.bat`.\n"
        "   - vbmeta_b will be flashed with AVB disabled.\n"
        "   - device reboots to fastbootd.\n"
        "   - conflicting OEM product_b / system_ext_b partitions are cleared.\n"
        "   - Axion GSI is flashed to system_b.\n"
        "   - prompt will wipe userdata (mandatory when switching from stock).\n"
        "   - slot B activated and phone reboots into Axion 2.9.\n"
    )
    github_create_or_update_release(token, "gsi-b-v1", "TECNO KL5 Axion 2.9 GSI (Slot B)", body, dist_gsi)
    print("\n[SUCCESS] gsi-b-v1 published successfully!")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", required=True, help="GitHub Personal Access Token")
    parser.add_argument("--work-dir", default="/tmp/build_work")
    parser.add_argument("--step", choices=["all", "stock", "gsi"], default="all")
    args = parser.parse_args()
    
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    os.makedirs(args.work_dir, exist_ok=True)
    
    if args.step in ("all", "stock"):
        build_stock(args.work_dir, args.token, repo_root)
    if args.step in ("all", "gsi"):
        build_gsi(args.work_dir, args.token, repo_root)
        
    print("\n====================================================================")
    print(" ALL BUILD AND RELEASE OPERATIONS COMPLETED SUCCESSFULLY!")
    print("====================================================================")

if __name__ == '__main__':
    main()
