# Re-applicable evidence-gated patches

Each numbered directory has a `patch.json`, payload files, a description of what/why, and exact stock paths/hashes as evidence. `approved: false` means proposed only and is skipped. No permissive SELinux, blanket VINTF HAL injection, copied vendor HAL executable, proprietary framework transplant or performance property is automatically approved.

An operation supports a regular file in `/system/` only, and records `target`, `source`, `sha256`, `expected_before` (null for absence), `uid`, `gid`, `mode`, and `selinux`. Parent directories must already exist. Symlink traversal and path escape are rejected. All operations are planned before writes. One conflict stops publication and is recorded in the report. Re-application reports identical files as skipped.

The deterministic designer currently only approves an exact empty codec XML include explicitly referenced by an absolute path in stock vendor/odm XML and missing in base. Real codec components, fingerprint HAL binding, SELinux rules and framework overlays stay proposed until a safe system-side mismatch is established. This intentionally avoids pretending inventory differences fix hardware.

The optional manual OTG helper is generated separately only if stock init contains one unambiguous paired on/off OTG property trigger. It is never smuggled into the GSI and has no boot service.
