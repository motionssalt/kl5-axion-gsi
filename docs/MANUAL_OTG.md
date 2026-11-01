# Manual Type-C control — experimental, hardware unverified

This is an inert root helper, not a fix for the reported mouse-enumeration problem. It is installed only as `/system/bin/kl5-otg` in a candidate image or as an optional KernelSU module. It performs **no boot work, polling, background service, property tuning, SELinux changes, or vendor partition edits**.

## Evidence and exact behavior

The audited stock `vendor/etc/init/android.hardware.usb@1.2-service-mediatekv2.rc` exposes `/sys/class/typec/port0/{power_role,data_role,port_type}`. Linux documents `port_type=source` as source-only DFP (host), `sink` as sink-only UFP (device), and `dual` as dual-role. This helper uses that standard ABI rather than guessing the meaning of Transsion's `OTG_CTL` or a persistent vendor property.

- Stock evidence and SHA-256 are bundled with the module and numbered patch.
- Linux ABI: https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-typec
- Android 16 USB HAL role-manager reference: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-16.0.0_r1/services/usb/java/com/android/server/usb/UsbPortManager.java

## Phone-only commands

Disconnect the charger and USB devices first. Run through Termux with KernelSU root:

```sh
su -c 'kl5-otg status'
su -c 'kl5-otg on'
# Connect the OTG device only AFTER the explicit on command succeeds.
su -c 'kl5-otg status'
# Disconnect the OTG device when finished.
su -c 'kl5-otg off'
# Optional: return to the exact saved pre-test port type.
su -c 'kl5-otg restore'
```

`on` requests source-only mode. It refuses an unexpected vendor device/platform, an attached Type-C partner, detected external power, unknown node values, missing/non-writable nodes, or concurrent invocations. `off` requests sink-only mode (host forcing disabled, no auto-detection). `restore` explicitly restores the saved pre-test type, which can re-enable stock dual-role behavior if it was originally `dual`. Reboot removes the transient kernel forcing; no script reapplies it at startup.

A role readback is **not** proof of VBUS power, mouse enumeration, charging safety or USB HAL compatibility. The kernel or vendor HAL may reject or override the request. On mismatched readback, the helper attempts to restore the immediately previous type and fails instead of reporting success. It does not repeatedly fight the HAL. Never repeatedly force a port attached to a charger or another power source.

If a helper process was interrupted, a lock may remain at `/data/adb/kl5-otg-manual/lock`. Confirm no helper is running before removing that empty lock with root `rmdir`. Do not blindly delete its saved-state directory.

## Optional KernelSU module

Release: https://github.com/motionssalt/kl5-axion-gsi/releases/tag/experimental-otg

The module sets executable permissions during installation but has no service or boot script. KernelSU system overlay support depends on the installed mount/metamodule implementation. Without a mounted command, invoke the bundled helper directly:

```sh
su -c 'sh /data/adb/modules/kl5_otg_manual/system/bin/kl5-otg status'
```

For the separately downloaded standalone script, use `su -c 'sh /your/download/path/kl5-otg.sh status'`, replacing the path with its actual location. No flashing is needed to test this optional helper.

Restore the previous port type before uninstalling. Uninstalling a module does not itself undo a runtime sysfs write; reboot also resets it. This helper can still fail to detect a mouse, just like the earlier app. Collect the USB HAL, SELinux and kernel logs in DEVICE_TEST_CHECKLIST.md rather than assuming host readback fixed enumeration.

## Validation scope

Automated tests use fake sysfs files to verify command guards, parsing, saved-state restoration and the absence of boot/polling/policy-bypass behavior. These are **not physical-device or emulator hardware tests**. The emulator proves boot/UI only and cannot validate MediaTek OTG, camera, fingerprint or hardware video codecs.
