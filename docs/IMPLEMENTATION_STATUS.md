# Implementation boundaries

The repository is executable automation, not proof of completed hardware fixes. Read the latest state/report before treating any artifact as flashable.

| Area | Implemented | Safety boundary / open work |
|---|---|---|
| Credentials | encrypted Actions secrets, private notification transport | exposed conversation credentials should eventually be rotated |
| Mirror | gdown/confirm/curl fallback, part/full SHA-256, per-part checkpoints | partial Drive downloads are not durable unless complete chunks can be saved; quota retries are bounded per run |
| Containers | ZIP range access; direct partition images; pinned selective lpunpack for super | RAR, 7z, proprietary encrypted packages and payload.bin are blocked, not claimed supported |
| Filesystems | streaming Android sparse decode; read-only ext4/EROFS audit | requires loop-mount support; unknown formats fail closed |
| Audit | categorized config/ELF/APK inventory, stock/base candidates | no checkvintf binary proof; no binary SELinux policy synthesis; differences are not runtime diagnosis |
| Patch design | evidence-gated numbered plans, safe empty-include case | no speculative media/fingerprint/OTG fix or missing library transplant |
| Patch application | exact-hash preconditions, no symlink edits, ext4 metadata; EROFS LZ4 when original compressor is provable | EROFS algorithm/layout features need validation; no arbitrary new directories or unsigned framework surgery |
| OTG | optional stock-init property helper, explicit on/off/status, no daemon | only generated for one exact paired stock trigger; not USB enumeration proof |
| ARM64 emulator | matched host/image configuration, real ADB boot property/screenshots/logs, base/candidate isolation | official Android 16/API 36.1 build 14981173 identified through corrected Build v4 API; bootstrap mirrors matching host/images and SHA-256 pins in Actions; boot remains unverified until real evidence exists |
| Sandboxed Play | strict post-release prerequisite gate, version-pin collection, install option hidden | binary framework port not implemented; APK-only install is explicitly rejected |
| Updates | scheduled upstream scan and manual URL, conflict reporting, cached resumable stages | source/base changes invalidate stage fingerprints; hardware still needs retesting |

The stock mirror starts before base downloads. State-write races discovered during provisioning are handled by bounded Git fetch/rebase/push retries. All disk-heavy jobs purge unused toolchains first. Long stages checkpoint per Release asset or partition; failures/near-limit runs can self-dispatch bounded continuations, while the schedule remains a later-run safety net.

No unchanged image is labeled patched, no blank placeholder PNG is a screenshot, no emulator result is a MediaTek result, and no ordinary Play/microG installation is described as GrapheneOS-style sandboxed Play.

## Continuation corrections

Root-owned 0600 configs are now inventoried by a read-only privileged subprocess without modifying source modes. The scatter-adjacent main `Firmware/super.img` is selected instead of the optional `Open/super.img`. Corrected audits use v2 Release namespaces so incomplete old evidence cannot be mistaken for complete canonical stock coverage. Telegram screenshot/log delivery has durable receipt-based retry. Blocked stages retry after six-hour backoff.
