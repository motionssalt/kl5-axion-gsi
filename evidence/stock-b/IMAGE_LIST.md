# TECNO KL5 (Spark 30C / MT6768) Stock Firmware Image List & Partition Target Analysis

## 1. Firmware Source & Provenance
- **Firmware Archive:** `Tecno_Spark_30C_KL5_MT6768_OP_V1085_240811`
- **Scatter File:** `Tecno_Spark_30C_KL5_MT6768_OP_V1085_240811/Firmware/MT6768_Android_scatter.txt`
- **Super Image:** `Tecno_Spark_30C_KL5_MT6768_OP_V1085_240811/Firmware/super.img` (Sparse 5.46 GB, Raw 8.59 GB)
- **Source Checksum (ZIP):** `9aa24d0518815a16b2d3c532825379b99595fdb701918c0dbeae738fa877b257`
- **Stock Layout:** Device uses MediaTek A/B partitioning scheme with dynamic partitions (`super`). Stock firmware populates slot A (`*_a` partitions inside `super.img`). Slot B partitions exist with 0 extents in metadata.

---

## 2. Boot & Ramdisk Analysis: Does `init_boot.img` Exist?

### Evidence from MT6768 Scatter File:
```text
SYS33
  partition_name: init_boot_a
  file_name: NONE
  is_download: false
  type: NORMAL_ROM
  partition_size: 0x800000

SYS47
  partition_name: init_boot_b
  file_name: NONE
  is_download: false
  type: NORMAL_ROM
  partition_size: 0x800000
```
- **Finding:** The scatter file reserves partition definitions for `init_boot_a` and `init_boot_b`, but assigns `file_name: NONE` and `is_download: false`.
- **Archive Contents:** No file named `init_boot.img` exists anywhere inside the stock firmware archive.

### Evidence from `boot.img` Header:
```text
Magic: ANDROID! (Android Boot Header v4)
Header Version: 4
Kernel Size: 19,586,404 bytes (~18.68 MB)
Ramdisk Size: 1,380,092 bytes (~1.32 MB)
OS Version: Android 14
```
- **Ramdisk Location:** The GKI ramdisk is **embedded directly in `boot.img`**, NOT in a separate `init_boot.img`.
- **Implication for Rooting:** To root with Magisk or KernelSU, the user must patch **`boot.img`** (never `init_boot.img`), and flash the patched image to **`boot_b`** in fastboot bootloader mode:
  ```cmd
  fastboot flash boot_b magisk_patched_boot.img
  ```
- **Remnant Cleanup:** Because Victor previously switched between KernelSU and Magisk and remnants persisted, the stock flash script unconditionally reflashes clean stock images to:
  - `boot_b` (clean stock kernel + ramdisk)
  - `vendor_boot_b` (clean stock vendor ramdisk + dtb)
  - `dtbo_b` (clean stock device tree overlay)

---

## 3. Physical Partitions (Flashed in Bootloader Fastboot)

These partitions exist as physical A/B blocks on the eMMC storage and are flashed during Stage 1 in standard bootloader `fastboot`:

| Target Partition | Source Image | Size (Bytes) | Role & Flash Justification |
| :--- | :--- | :--- | :--- |
| `boot_b` | `boot.img` | 33,554,432 | Linux GKI Kernel 5.10 + boot ramdisk. Essential for boot and cleanly removing KernelSU remnants. |
| `vendor_boot_b` | `vendor_boot.img` | 67,108,864 | Vendor ramdisk, fstab, and boot device tree blob. |
| `dtbo_b` | `dtbo.img` | 8,388,608 | Device Tree Blob Overlay for MT6768 board peripheral configuration. |
| `vbmeta_b` | `vbmeta.img` | 12,288 | Android Verified Boot root metadata. **Must flash with `--disable-verity --disable-verification`** to ensure bootloader does not reject unlocked/modified images. |
| `vbmeta_system_b` | `vbmeta_system.img` | 4,096 | AVB chained metadata descriptor for system partitions. |
| `vbmeta_vendor_b` | `vbmeta_vendor.img` | 4,096 | AVB chained metadata descriptor for vendor partitions. |
| `md1img_b` | `md1img.img` | 51,863,360 | MediaTek LTE/GSM Cellular Baseband Modem firmware. |
| `spmfw_b` | `spmfw.img` | 49,360 | System Power Management firmware for MT6768 power sequencing. |
| `scp_b` | `scp.img` | 580,832 | System Control Processor (low-power sensor hub/audio coprocessor). |
| `sspm_b` | `sspm.img` | 504,992 | System Security Processor (ARM TrustZone secure hardware enclave). |
| `gz_b` | `gz.img` | 1,267,248 | MediaTek GenieZone secure hypervisor/OS image. |
| `lk_b` | `lk.img` | 1,850,832 | Little Kernel second-stage bootloader (handles display init, fastboot, and A/B slot selection). |
| `logo_b` | `logo.bin` | 1,520,784 | Early boot logo bitmap displayed before kernel init. |
| `tee_b` | `tee.img` | 908,128 | Trusted Execution Environment OS (Trusty TEE). |
| `tkv_b` | `tkv.img` | 528,576 | MediaTek Trusted Key Vendor partition. |

---

## 4. Logical Partitions (Flashed in fastbootd)

These partitions reside inside dynamic partition container `super` and require Android userspace fastboot (`fastbootd` via `fastboot reboot fastboot`):

| Target Partition | Extracted Source Image | Size (Bytes) | Role & Flash Justification |
| :--- | :--- | :--- | :--- |
| `system_b` | `system.img` (from `system_a`) | 888,471,552 | Stock Android OS framework, core daemons, and system binaries. |
| `vendor_b` | `vendor.img` (from `vendor_a`) | 722,919,424 | MediaTek MT6768 hardware drivers, HALs, camera/audio/modem services. |
| `product_b` | `product.img` (from `product_a`) | 1,783,443,456 | Tecno HiOS system apps, Google Mobile Services (GMS), and product configurations. |
| `system_ext_b` | `system_ext.img` (from `system_ext_a`) | 2,093,494,272 | Extended system apps, carrier services, and vendor framework extensions. |
| `tr_product_b` | `tr_product.img` (from `tr_product_a`) | 348,160 | Transsion OEM carrier/product customizations. |
| `tr_mi_b` | `tr_mi.img` (from `tr_mi_a`) | 7,737,344 | Transsion OEM system animations and audio assets. |
| `tr_theme_b` | `tr_theme.img` (from `tr_theme_a`) | 348,160 | Transsion OEM theme engine assets. |
| `tr_preload_b` | `tr_preload.img` (from `tr_preload_a`) | 348,160 | Transsion preloaded application configurations. |
| `tr_region_b` | `tr_region.img` (from `tr_region_a`) | 348,160 | Transsion regional carrier/region parameters. |
| `tr_company_b` | `tr_company.img` (from `tr_company_a`) | 348,160 | Transsion corporate metadata and branding. |
| `tr_carrier_b` | `tr_carrier.img` (from `tr_carrier_a`) | 348,160 | Transsion carrier network configurations. |

---

## 5. FORBIDDEN PARTITIONS (NEVER TOUCHED)

The flash scripts explicitly **exclude** all of the following partitions. Under no circumstances will any script erase, format, or write to these:

| Partition Name | Why it is FORBIDDEN |
| :--- | :--- |
| `preloader` / `preloader_raw` | Boot ROM initial loader. Corrupting preloader can permanently brick the device into an unresponsive state requiring BROM hardware testpoint shorting. |
| `nvram` | Non-Volatile RAM containing factory calibration, IMEI 1 & 2, WiFi/Bluetooth MAC addresses. Overwriting causes NULL IMEI and lost cellular capability. |
| `nvdata` / `nvcfg` | Active runtime NVRAM database and configuration. Required for baseband operation. |
| `proinfo` | Device hardware serial number, board revisions, and factory production information. |
| `protect1` / `protect2` | Critical telephony security and SIM lock credentials. |
| `persist` | Factory sensors calibration (accelerometer, gyroscope, light sensor) and FRP token. |
| `seccfg` | Security configuration flag (controls unlocked bootloader state). |
| `frp` | Google Factory Reset Protection data block. |
| `metadata` | File-Based Encryption (FBE) encryption key table. Overwriting causes unrecoverable data loss and cryptographic bootloops. |
| `expdb` | Hardware exception and crash log database. |
| `para` / `misc` | Bootloader command parameter blocks and recovery control arguments. |
| `userdata` | User partition (only wiped via standard `fastboot -w` upon explicit user confirmation). |
