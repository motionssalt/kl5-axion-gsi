#!/usr/bin/env python3
"""
Splits files > 1,900 MB into byte-parts, creates manifest.txt and SHA256SUMS.txt.
"""
import argparse
import hashlib
import os
import shutil
import sys

PART_LIMIT = 1900000000 # 1,900 MB limit per GitHub release asset

def compute_sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(16 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pkg-dir', required=True, help='Directory with images to package')
    parser.add_argument('--out-dir', required=True, help='Directory for final release assets')
    parser.add_argument('--mode', choices=['stock', 'gsi'], required=True)
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    
    # Target partition mapping for stock images
    target_map = {
        'vbmeta.img': 'vbmeta_b',
        'boot.img': 'boot_b',
        'vendor_boot.img': 'vendor_boot_b',
        'dtbo.img': 'dtbo_b',
        'vbmeta_system.img': 'vbmeta_system_b',
        'vbmeta_vendor.img': 'vbmeta_vendor_b',
        'md1img.img': 'md1img_b',
        'spmfw.img': 'spmfw_b',
        'scp.img': 'scp_b',
        'sspm.img': 'sspm_b',
        'gz.img': 'gz_b',
        'lk.img': 'lk_b',
        'logo.bin': 'logo_b',
        'tee.img': 'tee_b',
        'tkv.img': 'tkv_b',
        'product.img': 'product_b',
        'system.img': 'system_b',
        'system_ext.img': 'system_ext_b',
        'vendor.img': 'vendor_b',
        'tr_product.img': 'tr_product_b',
        'tr_mi.img': 'tr_mi_b',
        'tr_theme.img': 'tr_theme_b',
        'tr_preload.img': 'tr_preload_b',
        'tr_region.img': 'tr_region_b',
        'tr_company.img': 'tr_company_b',
        'tr_carrier.img': 'tr_carrier_b'
    }

    manifest_lines = []
    checksum_lines = []

    files = sorted(os.listdir(args.pkg_dir))
    print(f"Processing {len(files)} files from {args.pkg_dir} in {args.mode} mode...")

    for fname in files:
        fpath = os.path.join(args.pkg_dir, fname)
        if not os.path.isfile(fpath):
            continue
        
        size = os.path.getsize(fpath)
        sha = compute_sha256(fpath)
        checksum_lines.append(f"{sha}  {fname}")
        
        target = target_map.get(fname, fname.split('.')[0] + '_b')
        if args.mode == 'gsi' and fname == 'system.img':
            target = 'system_b'

        if size > PART_LIMIT:
            print(f"File {fname} is {size} bytes (> 1,900 MB). Splitting into parts...")
            part_names = []
            part_num = 1
            with open(fpath, 'rb') as src:
                while True:
                    chunk = src.read(PART_LIMIT)
                    if not chunk:
                        break
                    part_name = f"{fname}.part{part_num:03d}"
                    part_path = os.path.join(args.out_dir, part_name)
                    with open(part_path, 'wb') as dst:
                        dst.write(chunk)
                    part_sha = compute_sha256(part_path)
                    checksum_lines.append(f"{part_sha}  {part_name}")
                    part_names.append(part_name)
                    part_num += 1
            parts_str = "+".join(part_names)
            manifest_lines.append(f"{target}|{fname}|{sha}|{parts_str}")
        else:
            print(f"File {fname} is {size} bytes (<= 1,900 MB). Copying directly...")
            out_file = os.path.join(args.out_dir, fname)
            shutil.copy2(fpath, out_file)
            manifest_lines.append(f"{target}|{fname}|{sha}|{fname}")

    # Write manifest.txt and SHA256SUMS.txt
    manifest_path = os.path.join(args.out_dir, 'manifest.txt')
    with open(manifest_path, 'w', newline='\r\n') as f:
        f.write('\r\n'.join(manifest_lines) + '\r\n')

    checksum_path = os.path.join(args.out_dir, 'SHA256SUMS.txt')
    with open(checksum_path, 'w', newline='\r\n') as f:
        f.write('\r\n'.join(checksum_lines) + '\r\n')

    print(f"Packaging complete. Assets ready in {args.out_dir}")

if __name__ == '__main__':
    main()
