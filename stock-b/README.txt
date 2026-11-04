========================================================================
  TECNO KL5 (SPARK 30C / HELIO G81) STOCK FIRMWARE (SLOT B) PACKAGE
========================================================================

Author / Brand: MOTIONSALT (Nigeria)
Device: TECNO KL5 (Spark 30C) - MediaTek MT6768 (Helio G81)
Target Slot: SLOT B ONLY (Slot A is never touched)
Release Tag: stock-b-v1

------------------------------------------------------------------------
1. QUICK START INSTRUCTIONS
------------------------------------------------------------------------
1. Download ALL files from this GitHub Release (including all .part* files,
   .bat scripts, manifest.txt, SHA256SUMS.txt, and README.txt) into the
   SAME folder where your fastboot.exe (Android SDK Platform-Tools) is.
   
2. Ensure your phone has at least 50% battery.

3. Step 1: Double-click '1_reassemble.bat'
   - This joins split byte parts using Windows CMD 'copy /b'.
   - It verifies every file's SHA-256 hash against SHA256SUMS.txt.
   - It will prompt you if you want to delete the .part files after
     successful verification to free disk space.

4. Step 2: Connect phone in FASTBOOT MODE:
   - Power off phone completely.
   - Press and hold Volume Down + Power until FASTBOOT appears on screen.
   - Connect USB cable to PC.

5. Step 3: Double-click '2_flash_stock_b.bat'
   - Pre-checks verify device connection and unlocked status.
   - Stage 1 flashes physical partitions in bootloader fastboot (with vbmeta
     AVB verification disabled).
   - Phone automatically reboots into FASTBOOTD (userspace mode).
   - Stage 2 flashes logical partitions inside the super container.
   - Prompt will ask if you want to wipe user data (recommended if returning
     from a GSI back to stock).
   - Script sets active slot to B and offers to reboot into the phone.

------------------------------------------------------------------------
2. DISK SPACE REQUIREMENT
------------------------------------------------------------------------
- Keep at least 15 GB of free disk space on your Windows drive while
  the downloaded parts and joined images coexist.
- Once '1_reassemble.bat' finishes and passes hash checks, you can safely
  delete the .part* files.

------------------------------------------------------------------------
3. PARTITIONS FLASHED AND FORBIDDEN SAFETY BOUNDARY
------------------------------------------------------------------------
Flashed to Slot B:
- Physical (Bootloader): boot_b, vendor_boot_b, dtbo_b, vbmeta_b,
  vbmeta_system_b, vbmeta_vendor_b, md1img_b, spmfw_b, scp_b, sspm_b,
  gz_b, lk_b, logo_b, tee_b, tkv_b.
- Logical (fastbootd): product_b, system_b, system_ext_b, vendor_b,
  tr_product_b, tr_mi_b, tr_theme_b, tr_preload_b, tr_region_b,
  tr_company_b, tr_carrier_b.

FORBIDDEN PARTITIONS (NEVER TOUCHED):
To guarantee that IMEI, baseband, WiFi MAC, serial number, and security
calibration are never damaged or wiped, the script will NEVER touch:
- preloader / preloader_raw (prevents hardware BROM brick)
- nvram, nvdata, nvcfg (protects IMEI and cellular baseband calibration)
- proinfo (protects factory serial numbers)
- protect1, protect2, persist (protects SIM locks & sensor calibrations)
- seccfg, frp, metadata, expdb, para, misc, userdata (except fastboot -w prompt).

------------------------------------------------------------------------
4. ROOTING WITH MAGISK AFTERWARDS (IMPORTANT ROOT NOTE)
------------------------------------------------------------------------
- DOES THIS FIRMWARE HAVE init_boot.img?
  NO. Analysis of the official MT6768 scatter file confirms init_boot has
  file_name: NONE and is_download: false.
- WHERE IS THE RAMDISK?
  The boot ramdisk (1.38 MB) is embedded directly inside 'boot.img'
  (Android Boot Header version 4, GKI Linux Kernel 5.10).
- HOW TO ROOT WITH MAGISK:
  1. Copy the clean 'boot.img' from this folder to your phone.
  2. Install Magisk App (v26+ or v27+).
  3. Select 'Install' -> 'Select and Patch a File' -> choose boot.img.
  4. Transfer the patched boot image back to your PC platform-tools folder.
  5. Put phone in bootloader fastboot mode and flash ONLY to slot B:
     fastboot flash boot_b magisk_patched_boot.img
     fastboot reboot
  * NEVER flash a patched boot image to slot A.
  * Overwriting boot_b, vendor_boot_b, and dtbo_b with this stock package
    completely wipes out any residual KernelSU / old root remnants.

------------------------------------------------------------------------
5. MANUAL RECOVERY REMINDER
------------------------------------------------------------------------
If any command is interrupted or fails:
1. Do not unplug the phone. Check USB cable and driver.
2. Rerun 2_flash_stock_b.bat. It safely overwrites slot B.
3. If fastbootd has an issue, you can manually run:
   fastboot reboot fastboot
   fastboot flash system_b system.img
   fastboot flash vendor_b vendor.img
   fastboot flash product_b product.img
   fastboot flash system_ext_b system_ext.img
   fastboot --set-active=b
   fastboot reboot
4. Slot A is completely untouched and acts as a safe hardware baseline.
