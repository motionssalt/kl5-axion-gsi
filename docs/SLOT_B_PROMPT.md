# KL5 STOCK + GSI → SLOT B FLASH PACKAGES: BUILD PROMPT

## STEP 0: CREDENTIALS (read first)
```
GITHUB_PAT = <SECRET_GITHUB_PAT>
```
- Use the PAT to clone/push the repo, run GitHub Actions and publish Releases in `motionssalt/kl5-axion-gsi`.
- Never commit the PAT or write it into `BUILD_STATE.json` (secret NAMES only).
- If it is still a placeholder, do everything that does not need it first. Nothing in this task deploys to Cloudflare, so no Cloudflare credentials are needed.

---

## 1. ROLE AND AUTONOMY
You are the builder, with full autonomy. You have no memory of earlier sessions; everything you need is in this file and in the repo's `BUILD_STATE.json`.

**Do not stop to ask Victor anything** (clarification, confirmation, choices) unless the work genuinely cannot continue. When something is ambiguous, pick the most sensible default, proceed, and record it in `BUILD_STATE.json` `decisions`. If truly blocked: do all other possible work first, record the blocker, and ask in one short message at the end.

**Goal:** give Victor two ready-to-use Windows packages, each published as a GitHub Release:
1. **Stock package:** the stock TECNO KL5 firmware, converted so it flashes to **slot B**, with a `.bat` that reassembles the downloaded parts and a `.bat` that flashes everything to the `_b` partitions.
2. **GSI package:** the Axion 2.9 GSI prepared the same way, with its own `.bat` to flash it to slot B on top of the stock one.

**There is no emulator and none may be used.** The phone is the only real test device and you cannot touch it. So everything must be built from hard evidence in the firmware, validated as far as possible in CI (including on a Windows runner), and fail-safe: any error must stop the scripts before they do more damage.

## 2. PROJECT BACKGROUND
- Victor (brand MOTIONSALT, Nigeria). Device: **TECNO KL5** (Spark 30c), MediaTek **MT6768** (Helio G81), board `TECNO-KL5`, A/B device with dynamic partitions (`super`). Bootloader unlocked, rooted (KernelSU).
- He wants to restore the **stock ROM** (clean baseline: many things stopped working about two weeks ago, e.g. OTG, camera, video, and he wants to rule out damage) and then reflash the Axion 2.9 GSI.
- The stock firmware is in his repo **`motionssalt/kl5-axion-gsi`** (a little over 6GB, mirrored as parts in its Releases). It contains the **slot A** layout: in the stock `super.img`, partitions are named `*_a` (the `_b` ones are empty/zero-sized).
- **The phone runs from slot B.** `fastboot set_active a` was tried before and the bootloader went back to B (slot A was probably not bootable, e.g. failed verification, so it fell back). **Do not rely on switching to A.** Everything must be flashed to the `_b` partitions.
- The method that worked before, by hand: extract the stock `super.img` and flash each file manually to the `_b` partitions. It works but is tedious. This task automates exactly that.
- GSI to use afterwards: `https://github.com/Doze-off/axion_aosp/releases/download/2026-10-17/Axion-2.9-GSI_treble_arm64-ab-GAPPS-20261017.img.xz` (Android 16, arm64 A/B, with GApps).
- Victor flashes from a **Windows PC using CMD** with **platform-tools** (`fastboot`). He will download the Release parts into the same folder as the platform-tools files and run the `.bat` files from there. He does not use PowerShell, WSL or any extra tools (no 7-Zip, no Python).
- A separate builder session may be working in the same repo on an OTG module (folder `otg/`, queue item `O1`). **Do not touch `otg/`, `evidence/otg/`, any existing workflow, file or Release.**

## 3. FASTBOOT FACTS THE SCRIPTS MUST RESPECT
- **Bootloader fastboot** can flash *physical* partitions (e.g. `boot_b`, `vendor_boot_b`, `dtbo_b`, `vbmeta_b`, and the whole `super`).
- **fastbootd** (`fastboot reboot fastboot`) is required for *logical* partitions inside super (`system_b`, `vendor_b`, `product_b`, `system_ext_b`, `odm_b`, etc.). It can also flash physical ones.
- Therefore the flash script runs in stages: physical partitions in the bootloader → `fastboot reboot fastboot` → logical partitions in fastbootd → final reboot.
- `fastboot getvar is-userspace` tells which mode the device is in; `fastboot getvar current-slot`, `slot-count`, `unlocked` and `partition-size:<name>` / `partition-type:<name>` are available to check preconditions.
- `vbmeta` must be flashed with `--disable-verity --disable-verification` so the unlocked/rooted phone does not fail verification.
- Logical partitions may need resizing to fit an image: `fastboot resize-logical-partition <name> <size>` (fastbootd) and, for a GSI that bundles `product`/`system_ext`, `fastboot delete-logical-partition <name>` may be needed to free space. Decide from the real super metadata (`lpdump`) of the stock `super.img`.

## 4. TASK QUEUE
S1: Stock package for slot B
S2: GSI package for slot B
S3: Final tidy-up
