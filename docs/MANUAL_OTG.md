# Manual OTG control — no always-on work

Stock Type-C/USB role management (including rt-pd-manager) must be understood before writing sysfs. Applying a generic `OTG_CTL` or host role is not sufficient evidence that USB enumeration will work.

The audit records stock USB init, HAL/VINTF, props, fstab/ueventd and SELinux text. The designer searches for a **single exact stock property with paired on/off init triggers** that write OTG/role nodes. If proven, the experimental KernelSU module packages only `system/bin/kl5-otg` and stock evidence. It has no `service.sh`, boot script, daemon or polling loop and changes nothing at boot.

```sh
su -c 'kl5-otg status'
su -c 'kl5-otg on'
# Plug in the mouse, then test enumeration and current draw.
su -c 'kl5-otg off'
```

A property readback only means the request was set; it does not prove the vendor HAL/kernel switched role. If discovery is missing/ambiguous, no guessed control is installed. KernelSU system overlays require a compatible mount implementation; if the command is not mounted, the bundled script can be invoked from the module's own `system/bin` path. Do not weaken SELinux or replace the stock USB HAL to make it appear functional.

Uninstall the optional module to remove the helper. Do not leave forced host mode active while charging; verify stock role/charging recovery after switching off. All hardware results remain unverified until physical-device tests pass.
