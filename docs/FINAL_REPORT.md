# KL5 pipeline status

Updated: 2026-11-01T00:56:10.937074+00:00

**No emulator result proves MediaTek hardware compatibility.**

| Phase | Status | Notes |
|---|---|---|
| 1 | done | Public repository, encrypted secrets, Actions workflows, disk/release helpers and persistent state installed. Local code tests passed. |
| 2 | done | Base mirrored with verified SHA-256; stock availability recorded separately. |
| 3 | done | Static inventory produced; see explicit coverage limits. Hardware equivalence is not established. |
| 4 | done | Candidate generated with static integrity checks. Boot/hardware unverified. |
| 5 | blocked | Patched image did not achieve verified emulator boot (or no candidate exists); base result is not a patched-image pass |
| 6 | blocked | Deferred until phases 1–5 have produced a released, boot-tested image. No Apps client or Google packages injected. |
| 7 | done | Daily upstream watcher and manual URL reapply workflow installed. Actual updated image still requires safe patches and emulator evidence. |

## Delivered infrastructure

Public repository, encrypted secrets, Telegram notifications, stock-first split mirror/checksums, selective static audit, exact-hash patch application/reporting, manual OTG evidence discovery, ARM64 emulator harness, scheduled upstream/manual update and Release import workflows. Infrastructure is not a claim that device fixes are complete.

## Actual image status

**No final patched, emulator-verified GSI build exists yet. Do not flash intermediate/status assets.**

## Exact patch scope

**Only an experimental, manual-only Type-C control helper has been approved. This is NOT a video/camera/fingerprint fix or full stock-like compatibility.** It adds no boot work, polling, OTG_CTL guesses or performance tuning. Optional helper artifacts: https://github.com/motionssalt/kl5-axion-gsi/releases/tag/experimental-otg . On requires USB/charger disconnected; off means sink-only; restore returns the saved type. Physical VBUS and mouse enumeration remain unverified.

## Open blockers

- **otg-hardware**: Experimental manual Type-C helper is implemented, but VBUS/mouse enumeration and deeper HAL/kernel issue remain unverified on physical KL5.
- **hardware-compatibility**: Media/camera/fingerprint and remaining vendor/framework gaps require evidence-backed fixes. Adding a manual helper does NOT resolve full stock-like compatibility.
- **fingerprint-usb-guard**: Base phh-on-boot USB recovery checks ro.hardware.fingerprint. Stock service is vendor.fps_hal; runtime property/TEE/UDC state is unavailable. Suspected integration gap is documented, not patched or claimed fixed.
- **emulator**: Patched image did not achieve verified emulator boot (or no candidate exists); base result is not a patched-image pass
- **sandbox-prerequisite**: First deliver compatibility build and real patched-image emulator evidence. Sandbox research notes are preliminary only; no implementation claim.

## Next autonomous actions

- Reuse the already mirrored/pinned Android 16 ARM64 runtime; resolve launcher integration and collect genuine base/candidate boot/UI evidence.
- Investigate unresolved media/camera/fingerprint and vendor/framework integration; the manual helper is not a substitute for those fixes.
- Keep sandboxed Play hidden until framework port and emulator installation proof exist; do not delay the compatibility release.
