# Additional GSI runtime integration findings

## Verified static evidence

The supplemental Actions audit completed successfully and published unmodified base shell scripts plus APEX-container inventories:
https://github.com/motionssalt/kl5-axion-gsi/releases/tag/audit-base-support-2ad2e18b7046

It found `system/system_ext/apex/com.android.vndk.v31.apex`. Therefore, **a missing VNDK 31 container is not established**. Runtime activation, exported namespaces and individual symbol resolution remain unverified. Copying another VNDK package or arbitrary stock libraries is not justified by this finding.

The original `system/bin/phh-on-boot.sh` contains a USB-gadget recovery guard that checks `ro.hardware.fingerprint` before cycling `sys.usb.config`. Its own comments warn that a USB config cycle can invalidate a fingerprint HAL TEE session. The stock init evidence identifies `vendor.fps_hal` and the GSI recovery branch attempts to restart that service. No `ro.hardware.fingerprint=` assignment was found in the selectively extracted stock property files; that does **not** prove the runtime property is unset because boot properties/init/native services can supply it.

This is a **specific integration hypothesis, not a confirmed fingerprint cause**. No patch to that startup script is approved: runtime property/service/UDC state and physical fingerprint logs are missing, and changing this base recovery behavior without them could affect USB recovery. The new manual-only helper does not modify it. `scripts/collect_device.sh` now collects the relevant runtime properties, init service states, UDC binding, Type-C roles, mount topology and active APEX list without writing to them.

The base also includes a Transsion property handler for `persist.sys.phh.transsion.usbotg` which searches for `tran_battery/OTG_CTL`. This means an OTG_CTL write is **already part of existing GSI integration**, not a newly discovered complete solution. It supports the decision not to claim that repeating the user's earlier host/gate app operation fixes enumeration. The experimental helper instead requests the stock HAL-exposed standard Type-C `port_type` ABI, with explicit on/off/restore and no auto-detection.

## Performance behavior preserved

`debug.stagefright.c2inputsurface=-1` is retained. The inspected AOSP commit describes application-side encoder input-surface creation reducing per-frame IPC:
https://android.googlesource.com/platform/frameworks/av/+/1858832%5E%21/

No codec rank, software codec limit, scheduler, governor, thermal configuration, base boot service or background performance behavior was changed.

## Verification boundary

All of the above is static evidence. The active Actions build/test run is:
https://github.com/motionssalt/kl5-axion-gsi/actions/runs/41257412968

No completed patched-image emulator boot or screenshot is available at this session checkpoint. A future successful emulator run proves boot/UI only, not MediaTek video encode/decode, camera, fingerprint, Type-C/OTG or charging.
