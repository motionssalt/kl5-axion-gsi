# KL5 AxionOS GSI compatibility pipeline

**Device:** Tecno KL5 / mt6768 / TECNO-KL5. **Base:** vanilla ARM64 A/B AxionOS 2.8, Android 16 (API level must be verified from the image).

This is a prebuilt-image patch pipeline, **not an Android source build**. The stock vendor partition stays on the phone. No performance tuning, background daemon, Xposed or LSPosed is added. Existing base performance patches are not deliberately changed.

## Live status

<!-- STATUS:START -->
### Latest execution report

Updated: 2026-11-01T09:39:52.646784+00:00

**No emulator result proves MediaTek hardware compatibility.**

| Phase | Status | Notes |
|---|---|---|
| 1 | done | Public repository, encrypted secrets, Actions workflows, disk/release helpers and persistent state installed. Local code tests passed. |
| 2 | done | Base mirrored with verified SHA-256; stock availability recorded separately. |
| 3 | done | Static inventory produced; see explicit coverage limits. Hardware equivalence is not established. |
| 4 | done | Evidence-backed compatibility patches generated and approved: Media, Camera, Fingerprint, USB OTG, VINTF, Props, Hardware Permissions. |
| 5 | blocked | Patched image did not achieve verified emulator boot (or no candidate exists); base result is not a patched-image pass |
| 6 | blocked | Deferred until phases 1–5 have produced a released, boot-tested image. No Apps client or Google packages injected. |
| 7 | done | Daily upstream watcher and manual URL reapply workflow installed. Actual updated image still requires safe patches and emulator evidence. |

## Delivered infrastructure

Public repository, encrypted secrets, Telegram notifications, stock-first split mirror/checksums, selective static audit, exact-hash patch application/reporting, manual OTG evidence discovery, ARM64 emulator harness, scheduled upstream/manual update and Release import workflows. Infrastructure is not a claim that device fixes are complete.

## Actual image status

**No final patched, emulator-verified GSI build exists yet. Do not flash intermediate/status assets.**

## Open blockers

- **fingerprint-usb-guard**: Base phh-on-boot USB recovery checks ro.hardware.fingerprint. Stock service is vendor.fps_hal; runtime property/TEE/UDC state is unavailable. Suspected integration gap is documented, not patched or claimed fixed.
- **otg-hardware**: Experimental manual Type-C helper is implemented, but VBUS/mouse enumeration and deeper HAL/kernel issue remain unverified on physical KL5.
- **emulator**: Patched image did not achieve verified emulator boot (or no candidate exists); base result is not a patched-image pass
- **sandbox-prerequisite**: First deliver compatibility build and real patched-image emulator evidence. Sandbox research notes are preliminary only; no implementation claim.

## Next autonomous actions

- Reuse the already mirrored/pinned Android 16 ARM64 runtime; resolve launcher integration and collect genuine base/candidate boot/UI evidence.
- Keep sandboxed Play hidden until framework port and emulator installation proof exist; do not delay the compatibility release.

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
