# Axion 2.9 GSI Fitting Analysis for TECNO KL5 Slot B

## 1. GSI Identification & Image Attributes
- **GSI Name:** Axion 2.9 GSI Treble arm64-ab with Google Apps
- **Upstream URL:** `https://github.com/Doze-off/axion_aosp/releases/download/2026-10-17/Axion-2.9-GSI_treble_arm64-ab-GAPPS-20261017.img.xz`
- **Compressed Size (.xz):** 1,292,048,564 bytes (~1.20 GiB)
- **Architecture:** `arm64` A/B Treble compatible
- **Target OS:** Android 16 (AOSP) with embedded GApps
- **Packaging:** Bundles the complete system root (`/system`), including core apps, priv-apps, and GApps services.

---

## 2. Super Partition Space Budget Analysis
From `SUPER_LAYOUT.md`:
- `main_b` Maximum Size: **8,587,837,440 bytes (~8.00 GiB)**
- Stock `vendor_b` Size: **722,919,424 bytes (~689.4 MiB)** (Must be retained for hardware HALs, camera, audio, and sensors)
- Decompressed Axion GSI `system.img` typical raw size: **~3,300,000,000 bytes (~3.07 GiB)** (sparse format ~2.2 GiB).

### Scenario 1: Retaining Stock `product_b` and `system_ext_b`
- `vendor_b`: ~0.72 GiB
- GSI `system_b`: ~3.30 GiB
- Stock `product_b`: 1.78 GiB
- Stock `system_ext_b`: 2.09 GiB
- Total Required: $0.72 + 3.30 + 1.78 + 2.09 = 7.89 \text{ GiB} \le 8.00 \text{ GiB}$
- **Architectural Conflict:** While the raw sector count technically fits under the 8.00 GiB ceiling by ~110 MiB, retaining stock `product_b` (Tecno HiOS overlays and system apps) and `system_ext_b` causes severe framework mismatch against Android 16 AOSP/Axion GSI! Stock Tecno proprietary framework jars in `system_ext` clash with Android 16 runtime classes, inducing bootloops (`SIGSEGV` in `zygote64` / `system_server`).

### Scenario 2: Deleting or Zeroing `product_b` and `system_ext_b` (Standard Treble Flow)
- GSI bundles its required product and system_ext functionality directly within `/system`.
- In `fastbootd`, deleting `product_b` and `system_ext_b`:
  ```cmd
  fastboot delete-logical-partition product_b
  fastboot delete-logical-partition system_ext_b
  ```
- Frees **3,876,937,728 bytes (~3.61 GiB)** in `main_b`!
- Available budget in `main_b` for GSI:
  $$8,587,837,440 - 722,919,424 = 7,864,918,016 \text{ bytes} \approx 7.32 \text{ GiB}$$
- Axion GSI `system_b` easily expands to 3.3 GiB with **>4 GiB remaining margin**!
- If the device bootloader requires `product_b` and `system_ext_b` partition nodes to exist in metadata, they are created with size 0:
  ```cmd
  fastboot create-logical-partition product_b 0
  fastboot create-logical-partition system_ext_b 0
  ```

---

## 3. Flash Protocol for `3_flash_gsi_b.bat`
1. **Pre-checks:** Fastboot communication, bootloader unlocked, battery > 30%.
2. **AVB Handling:** Flash stock `vbmeta_b` with `--disable-verity --disable-verification` to disable Android Verified Boot checks on the modified system image:
   ```cmd
   fastboot flash --disable-verity --disable-verification vbmeta_b vbmeta.img
   ```
3. **Switch to fastbootd:**
   ```cmd
   fastboot reboot fastboot
   ```
4. **Logical Partition Management:**
   - Delete conflicting OEM partitions:
     ```cmd
     fastboot delete-logical-partition product_b
     fastboot delete-logical-partition system_ext_b
     ```
   - Recreate empty nodes (optional safe fallback):
     ```cmd
     fastboot create-logical-partition product_b 0
     fastboot create-logical-partition system_ext_b 0
     ```
   - Flash Axion 2.9 GSI to `system_b`:
     ```cmd
     fastboot flash system_b system.img
     ```
5. **Wipe Userdata:** Prompt user to confirm `fastboot -w` (strictly mandatory when switching between stock OEM ROM and AOSP GSI due to incompatible `/data` encryption and app databases).
6. **Slot & Reboot:**
   ```cmd
   fastboot --set-active=b
   fastboot reboot
   ```
