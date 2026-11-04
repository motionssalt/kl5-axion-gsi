# TECNO KL5 (Spark 30C / MT6768) Slot B Flash Packages Documentation

## 1. Executive Summary & Purpose
This document details the architecture, design decisions, evidence base, and validation protocol for the **TECNO KL5 (Spark 30C)** slot B flash packages:
1. **`stock-b-v1`**: The complete stock TECNO KL5 firmware converted to flash directly to **slot B**, providing a clean factory hardware baseline.
2. **`gsi-b-v1`**: The Axion 2.9 GSI (Android 16, Treble arm64-ab with GAPPS) prepared to flash onto slot B on top of the clean stock drivers.

Target User: **Victor (MOTIONSALT, Nigeria)**.  
Flashing Environment: **Windows PC using CMD with Android SDK Platform-Tools (`fastboot`)**.  
Device State: **Bootloader unlocked, running from slot B**.

---

## 2. Hard Evidence & Architecture

### 2.1 The Slot B Strategy
- Victor's device hardware runs from **Slot B**.
- Previous attempts to run `fastboot set_active a` caused the bootloader to revert to slot B (likely because slot A failed AVB verification or was unbootable).
- Consequently, all flash operations strictly target `_b` partitions. Slot A is left untouched as an immutable recovery fallback.

### 2.2 Boot Header & Ramdisk Evidence (`init_boot` Myth Debunked)
- **Scatter File Analysis (`MT6768_Android_scatter.txt`):**
  `init_boot_a` and `init_boot_b` entries have `file_name: NONE` and `is_download: false`.
  There is NO `init_boot.img` in the stock firmware.
- **Boot Image Analysis (`boot.img`):**
  Header is Android Boot v4 with GKI Linux Kernel 5.10.
  Kernel size: 19,586,404 bytes (~18.68 MB).
  Ramdisk size: 1,380,092 bytes (~1.32 MB).
- **Magisk Rooting Procedure:**
  To root with Magisk, patch **`boot.img`** (never `init_boot.img`), and flash to `boot_b`:
  ```cmd
  fastboot flash boot_b magisk_patched_boot.img
  ```
  Overwriting `boot_b` and `vendor_boot_b` with this clean stock package purges all leftover KernelSU remnants.

### 2.3 Super Dynamic Partition Structure
- Container: `super` (Total size: 8,589,934,592 bytes / 8.00 GiB).
- Dynamic Groups:
  `main_a`: 8,587,837,440 bytes (~7.998 GiB)
  `main_b`: 8,587,837,440 bytes (~7.998 GiB)
- Stock Extracted Logical Partitions:
  `product_b` (1.78 GB), `system_b` (888 MB), `system_ext_b` (2.09 GB), `vendor_b` (722 MB), and OEM `tr_*_b` partitions (~10 MB).
  Total stock logical footprint: ~5.12 GiB, well within the 8.00 GiB ceiling.
- Axion GSI Fitting:
  Axion GSI bundles all product/system_ext code in `/system`.
  The script deletes `product_b` and `system_ext_b` to eliminate OEM overlay crashes and free 3.87 GB of space.
  Axion GSI `system.img` expands into `system_b` with over 4 GiB of remaining headroom.

---

## 3. Package Structure & Windows CMD Compatibility

### 3.1 Strict Windows CMD Standards
- Pure **ASCII** text encoding (no Unicode box-drawing or special characters that render as garbage in default Windows CMD codepages).
- **CRLF** (`\r\n`) line endings.
- No Byte Order Mark (BOM).
- Built with `%~dp0` and `setlocal EnableDelayedExpansion`.
- Standalone: Zero dependencies on PowerShell, WSL, Python, 7-Zip, or external runtimes. Uses native Windows `copy /b` and `certutil -hashfile`.

### 3.2 Part Splitting
- Files exceeding 1,900 MB (such as `system.img` or `super.img`) are split into plain byte parts (`.part001`, `.part002`, etc.) to comply with GitHub Release asset limits (2 GiB max).
- Reassembled with standard binary concatenate:
  ```cmd
  copy /b file.part001 + file.part002 file.img
  ```
- Checked against `SHA256SUMS.txt` using `certutil`.

---

## 4. Flash Scripts Execution Sequence

### 4.1 Stock Package (`2_flash_stock_b.bat`)
1. **Pre-checks:** Tests `fastboot.exe`, verifies USB device detection, confirms bootloader is unlocked, checks image existence against `manifest.txt`.
2. **User Confirmation:** Prompts for uppercase typed `YES`.
3. **Stage 1 (Bootloader Physical):**
   - `vbmeta_b` flashed with `--disable-verity --disable-verification`.
   - `boot_b`, `vendor_boot_b`, `dtbo_b`, `vbmeta_system_b`, `vbmeta_vendor_b`.
   - MTK firmware: `md1img_b`, `spmfw_b`, `scp_b`, `sspm_b`, `gz_b`, `lk_b`, `logo_b`, `tee_b`, `tkv_b`.
   - Every physical partition checked with `fastboot getvar partition-size:<name>_b`.
4. **Transition:** Calls `fastboot reboot fastboot` and polls `is-userspace` until `fastbootd` responds.
5. **Stage 2 (fastbootd Logical):**
   - Flashes `product_b`, `system_b`, `system_ext_b`, `vendor_b`, `tr_product_b`, `tr_mi_b`, `tr_theme_b`, `tr_preload_b`, `tr_region_b`, `tr_company_b`, `tr_carrier_b`.
6. **Finalization:**
   - Prompts for optional userdata wipe (`fastboot -w`).
   - Sets active slot: `fastboot --set-active=b`.
   - Reboots into stock system: `fastboot reboot`.

### 4.2 Axion GSI Package (`3_flash_gsi_b.bat`)
1. Pre-checks and typed confirmation.
2. Flashes `vbmeta_b` with `--disable-verity --disable-verification`.
3. Reboots to `fastbootd`.
4. Clears conflicting OEM logical partitions:
   `fastboot delete-logical-partition product_b`
   `fastboot delete-logical-partition system_ext_b`
5. Flashes Axion 2.9 GSI to `system_b`:
   `fastboot flash system_b system.img`
6. Formats userdata (`fastboot -w`) to initialize Android 16 encryption table.
7. Sets active slot to B and reboots.

---

## 5. Forbidden Partitions Guard (Safety Constitution)
To eliminate any risk of baseband failure or permanent hardware bricking, the following partitions are strictly forbidden from being written or formatted:
`preloader`, `nvram`, `nvdata`, `nvcfg`, `proinfo`, `protect1`, `protect2`, `persist`, `seccfg`, `frp`, `metadata`, `expdb`, `para`, `misc`, and `userdata` (except via prompted `fastboot -w`).

---

## 6. GitHub Actions Workflows & Validation
- **`stockb-build-and-release.yml`**: Builds packages, splits large images, generates manifests, and publishes releases `stock-b-v1` and `gsi-b-v1`.
- **`stockb-verify-windows.yml`**: Runs on `windows-latest` to validate:
  1. Part reassembly and cryptographic SHA256 integrity.
  2. Deliberate 1-byte corruption rejection.
  3. Execution against `stub_fastboot.bat`:
     - Stage transition sequence.
     - AVB disable flags enforcement.
     - Strictly slot B targets (`_b`).
     - Absolute absence of forbidden partitions.
     - Immediate execution halt upon simulated command failure.
     - Proper conditional execution of `fastboot -w`.
