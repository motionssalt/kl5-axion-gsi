# Rejoin, integrity and cautious flashing

**Do not flash a status/audit Release or an unverified candidate.** A final build must identify the exact base SHA, patch results, emulator evidence and hardware limitations. Back up data and the matching stock boot/vendor_boot/vbmeta recovery path. An unlocked bootloader and working recovery/fastbootd path are prerequisites. Never relock with modified images.

Download every image part, `build-manifest.json` and `asset_tool.py` from the same build. Termux verification and rejoin need only Python:

```sh
python asset_tool.py verify build-manifest.json
python asset_tool.py join build-manifest.json --output system.img.xz
xz -dk system.img.xz
```

The join tool validates each part and the complete compressed image before renaming the output. Ensure the phone has space for both compressed and raw copies; delete intermediates only after verification.

A phone cannot run Termux commands while that **same phone** is in fastbootd. The following commands require a second USB-capable fastboot host (which can be another Android phone with suitable USB permissions), or an already-working device recovery that can flash a system image. This repository does not pretend GitHub Actions can remotely flash a disconnected KL5.

```sh
adb reboot fastboot
fastboot getvar is-userspace
fastboot getvar current-slot
fastboot getvar unlocked
fastboot getvar partition-size:system
# Verify fastbootd, active-slot handling and image/partition size before writing.
fastboot flash system system.img
fastboot reboot
```

On dynamic A/B devices, fastbootd usually exposes logical `system`; do not invent a slot suffix or delete logical partitions to force a size fit. If the advertised partition name differs or the image will not fit, stop flashing and use the device's verified stock recovery procedure. No partition resizing/deletion or automatic data wipe is performed by this project.

## AVB and KernelSU

A patched system image cannot retain the original valid AVB digest/signature. The patcher removes an appended obsolete AVB footer when present; it does not possess OEM signing keys. AVB handling is **device/build-specific** and emulator boot does not validate KL5 vbmeta behavior. Preserve the known-working GSI/KernelSU AVB setup if already configured.

Only when the matching stock build and device recovery procedure explicitly require it, a fastboot host can use:

```sh
fastboot --disable-verity --disable-verification flash vbmeta vbmeta.img
```

That is conditional guidance, not a universal instruction. Never flash an empty vbmeta, another model's image, or unknown vbmeta_system/vbmeta_vendor chains. Never overwrite boot/vendor_boot just to install this system image: KernelSU lives with the user's kernel setup and this pipeline does not modify it. Incorrect AVB/slot/partition handling can brick or erase data.

Emulator success proves boot/UI only. Test codecs/camera, fingerprint, OTG and all other hardware using DEVICE_TEST_CHECKLIST.md after flashing.
