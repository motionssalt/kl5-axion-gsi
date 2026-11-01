# KL5 AxionOS GSI compatibility pipeline

**Device:** Tecno KL5 / mt6768 / TECNO-KL5. **Base:** vanilla ARM64 A/B AxionOS 2.8, Android 16 (API level must be verified from the image).

This is a prebuilt-image patch pipeline, **not an Android source build**. The stock vendor partition stays on the phone. No performance tuning, background daemon, Xposed or LSPosed is added. Existing base performance patches are not deliberately changed.

## Live status

<!-- STATUS:START -->
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

<!-- STATUS:END -->

[Actions](https://github.com/motionssalt/kl5-axion-gsi/actions) · [Releases](https://github.com/motionssalt/kl5-axion-gsi/releases) · [Persistent build state](BUILD_STATE.json)

## Phone-only operation

All heavy work runs in GitHub Actions. Open **Actions → KL5 compatibility pipeline → Run workflow**; empty inputs use the pinned original. A new upstream vanilla `.img.xz` URL can be supplied. The updater also checks upstream daily. A six-hour schedule retries incomplete input mirroring; stages with unchanged inputs/code are cached to avoid repeated expensive work.

Stock input mirroring is attempted first. Assets are at most 1,900,000,000 bytes, below GitHub's 2 GiB limit. `stock-manifest.json` and each part contain/check SHA-256 integrity. After a complete mirror, stock extraction uses bounded Release range requests, not Google Drive. ZIP archives containing direct partition images or `super.img` are selectively inspected; unsupported containers produce explicit blockers rather than a full-unpack surprise.

If Drive quota blocks the download, use the already prepared [Release import](NEEDS_STOCK_UPLOAD.md). **No user intervention is required merely to let independent GSI analysis continue.**

## Delivery and verification policy

`stock-mirror`, `inputs-*`, `audit-*`, `candidate-*`, and `pipeline-status` are intermediate prereleases. Only an actual modified image with real patched-image emulator evidence can become a `build-<date>-<run>` release. A green workflow means orchestration completed; **it does not mean every Android phase passed**. Blockers are state data, not fabricated successes.

Emulator verification proves **boot and UI only**. MediaTek video encode/decode, camera, fingerprint, OTG, RIL/IMS and other physical hardware remain unverified until tested on the KL5. Missing stock files inside the GSI are not automatically defects, since vendor/odm remain present on the phone.

See [audit coverage](docs/AUDIT.md), [implementation limits](docs/IMPLEMENTATION_STATUS.md), [patch format](patches/README.md), [manual OTG design](docs/MANUAL_OTG.md), [device tests](docs/DEVICE_TEST_CHECKLIST.md), [flashing/rejoin guide](docs/FLASHING.md) and [sandboxed Play status](docs/SANDBOXED_PLAY.md).

Credentials are repository secrets only. Never put a PAT, Telegram token, cookies or chat ID into source, Release notes, collected public logs or BUILD_STATE.json. Logs from the physical phone can contain private identifiers; inspect them before publishing.

## Reapply locally or in Actions

`bash scripts/apply_patches.sh input.img.xz --output patched.img.xz --report patch-report.json`

This Linux/root operation is intended for Actions, not for editing a mounted phone system. Approved patches require exact before/after SHA-256, stock evidence and explicit ownership/mode/SELinux metadata. Proposed patches are skipped, changed upstream files are conflicts, and an unchanged image is never republished as a patched build. Workflow manual input provides the phone-friendly path.

## Security

The credentials provided during provisioning were not committed. Because credentials appeared in the task conversation, rotation is prudent after provisioning; replacements belong in **Settings → Secrets and variables → Actions**, under `PIPELINE_PAT`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`. Replacing `PIPELINE_PAT` must preserve repo contents/workflow dispatch permissions. Keep the account/repository public for standard free runners; no paid services are provisioned.
