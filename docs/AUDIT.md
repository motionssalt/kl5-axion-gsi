# Audit status: pending actual input extraction

This file is replaced only after real stock/base evidence is inventoried. No device-specific findings are claimed yet. Per-partition inventories/config evidence are checkpointed in audit Releases. The machine report `audit.json` is generated from those actual fragments.

Coverage includes VINTF HAL declarations, init/ueventd/fstab, props/API/VNDK, media/codec/camera, fingerprint, USB/Type-C/OTG, audio, sensors, GNSS, NFC, Bluetooth, WiFi, RIL/IMS, display, power/thermal/charging, vibrator/lights, overlays, permissions/sysconfig, SELinux contexts/CIL, hardware apps and ELF DT_NEEDED candidates. Coverage counts, extraction errors and omissions are explicit. Binary SELinux rules are not reconstructed by this implementation.
