# KL5 OTG MODULE: BUILD PROMPT

## STEP 0: CREDENTIALS (read first)
```
GITHUB_PAT = [CONFIGURED_IN_ACTIONS_SECRET]
STOCK_ROM_REPO = motionssalt/kl5-axion-gsi
```

## 1. ROLE AND AUTONOMY
Goal: deliver a Magisk/KernelSU module (flashable zip) that makes USB OTG actually work on Victor's phone, running the Axion 2.9 GSI, based on how his STOCK ROM wires OTG. The finished zip must be published as a GitHub Release asset so he can download and flash it immediately.

## 2. PROJECT BACKGROUND
- Device: TECNO KL5 (Spark 30c), MediaTek MT6768 (Helio G81), board name TECNO-KL5, A/B, tdgsi_arm64_ab, Type-C port managed through rt-pd-manager.
- ROM: Axion 2.9 GSI (Android 16, API 36), rooted with KernelSU.
- Stock ROM kernel and vendor partition are still present on device.

## 3. EVIDENCE FROM THE PHONE (2026-11-04)
- /sys/class/usb_role/mt_usb-role-switch/role is writable. Host sticks with cable plugged in.
- Even in host, no USB device enumerates.
- VBUS (5V out) is never turned on. Regulator usb-otg-vbus is disabled, num_users=0.
- Transsion-specific nodes: /sys/devices/platform/odm/odm:tran_battery/OTG_CTL (reads 1), /sys/devices/platform/odm/odm:tran_otg/otg_debug.
