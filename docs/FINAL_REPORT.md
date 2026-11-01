# KL5 execution checkpoint — 2026-11-01

**The resumable GitHub Actions pipeline is deployed and running. No final patched GSI, successful emulator boot, hardware fix or sandboxed Play installation is claimed. Do not flash intermediate assets.**

## Delivered and verified

- Existing public repository resumed; credentials are encrypted repository secrets, not committed values. Telegram session delivery succeeded; workflow notifications continue independently.
- Complete stock archive mirrored: 6,512,327,514 bytes, four Release parts, each at most 1,900,000,000 bytes, plus SHA-256 manifest. Later stages use GitHub Releases, not Google Drive.
- Base mirrored and checksummed: 1,313,731,068-byte compressed GSI. Raw image is ext4. Corrected read-only audit verifies Android 16/API 36/SDK-full 36.1, with zero base inventory errors.
- Corrected canonical stock vendor, product, system_ext and system inventories published, each with zero inventory errors. The optional Open/super image is no longer mistaken for the scatter-adjacent firmware super.
- Root-only 0600 configuration reads fixed without changing source modes. Numbered evidence-gated patch engine, checksum/rejoin utilities, flashing guide and physical-device checklist are in the repository.
- Official Android Build v4 discovery works. Build 14981173 independently verifies Android 16/API 36.1 ARM64; matched x86 host and ARM64 guest runtime mirroring is automated. API 37 latest build was deliberately rejected. No client key or temporary signed URL is written to the repository.
- Telegram screenshot/photo and key-file/document delivery, durable delivery receipts/backfill, bounded retries, concurrent-state journal preservation and daily/manual upstream update workflows are implemented.
- 33 local regression tests passed, Python compilation passed, and shell syntax checks passed. GitHub safety checks for commit 1d524fe passed; newer checks run automatically.

## Still open

The stock/base gap summary encountered a symlink-without-sha256 exception. Its code and regression test are fixed and pushed; the queued run must regenerate the report. No safe, evidence-backed image compatibility patch is currently approved, so an unchanged input is not republished as a patched ROM. Video/recording, fingerprint and OTG remain unverified and unfixed. Stock OTG init grants node permissions but does not provide a paired property toggle; no guessed always-on workaround is shipped.

Matching emulator runtime acquisition and real AxionOS guest boot/UI testing remain pending. The currently active older workflow may still hit its old ARM-host configuration; a queued newer workflow uses the explicit x86-host/ARM64-QEMU path and reuses Release checkpoints. Default AOSP guest boot is never accepted as AxionOS boot.

Sandboxed Google Play stays absent: no safe Android 16 framework-layer port or installation proof exists. It must not delay delivery of a future genuine compatibility build.

**Any eventual emulator result proves boot and UI only. MediaTek codecs, camera, fingerprint, USB OTG and other physical features require testing on the actual KL5.**

## Delivery links

Repository: https://github.com/motionssalt/kl5-axion-gsi

Stock mirror: https://github.com/motionssalt/kl5-axion-gsi/releases/tag/stock-mirror

Base input: https://github.com/motionssalt/kl5-axion-gsi/releases/tag/inputs-c3fff91f5761

Canonical stock audit: https://github.com/motionssalt/kl5-axion-gsi/releases/tag/audit-stock-9aa24d051881-v2

Corrected base audit: https://github.com/motionssalt/kl5-axion-gsi/releases/tag/audit-base-2ad2e18b7046-v2

Queued corrected workflow: https://github.com/motionssalt/kl5-axion-gsi/actions/runs/41255933320

Live report: https://github.com/motionssalt/kl5-axion-gsi/releases/tag/pipeline-status

The workflows continue after this session. BUILD_STATE.json records decisions, checkpoints, blockers and next actions. Credentials shared in the task conversation should be rotated; replacements belong only in the existing repository secrets.
