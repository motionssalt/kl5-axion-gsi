========================================================================
  TECNO KL5 (SPARK 30C / HELIO G81) AXION 2.9 GSI (SLOT B) PACKAGE
========================================================================

Author / Brand: MOTIONSALT (Nigeria)
Device: TECNO KL5 (Spark 30C) - MediaTek MT6768 (Helio G81)
Target: Axion 2.9 GSI (Android 16, Treble arm64-ab with GAPPS) -^> Slot B
Baseline Required: Flash stock-b-v1 package first to establish clean drivers
Release Tag: gsi-b-v1

------------------------------------------------------------------------
1. QUICK START INSTRUCTIONS
------------------------------------------------------------------------
1. Download ALL files from this release into your platform-tools folder.
2. Run '1_reassemble.bat' to join split parts and verify SHA-256 hashes.
3. Put phone into fastboot mode (Volume Down + Power).
4. Run '3_flash_gsi_b.bat':
   - Flashes vbmeta_b with AVB disabled.
   - Reboots into fastbootd.
   - Clears OEM product_b and system_ext_b partitions to prevent conflicts.
   - Flashes Axion 2.9 GSI system.img to system_b.
   - Prompts to wipe userdata (mandatory when switching from stock to GSI).
   - Sets slot B active and reboots phone into Axion Android 16.

------------------------------------------------------------------------
2. WHY ARE PRODUCT_B AND SYSTEM_EXT_B CLEARED?
------------------------------------------------------------------------
Axion GSI is a standalone Android 16 AOSP system that bundles its own
product and system_ext components inside /system. Leaving the stock Tecno
HiOS overlays in product_b and system_ext_b causes zygote crashes on boot.
Clearing them ensures a clean, stable boot while keeping stock vendor_b
for MT6768 camera, display, and modem hardware support.
