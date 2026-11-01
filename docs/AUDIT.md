# KL5 stock versus GSI audit

Static evidence only. Missing vendor files inside a GSI are NOT automatically gaps: the stock vendor stays on the device.

Stock partitions: none

Base partitions: system

## Coverage

| Area | Stock files | Base files |
|---|---:|---:|
| vintf | 0 | 23 |
| init | 0 | 103 |
| props | 0 | 0 |
| media | 0 | 57 |
| camera | 0 | 37 |
| fingerprint | 0 | 20 |
| usb_otg | 0 | 17 |
| audio | 0 | 498 |
| sensors | 0 | 23 |
| gnss | 0 | 19 |
| nfc | 0 | 9 |
| bluetooth | 0 | 19 |
| wifi | 0 | 14 |
| telephony_ims | 0 | 74 |
| display | 0 | 176 |
| power_thermal_charging | 0 | 46 |
| vibrator_lights | 0 | 32 |
| overlays | 0 | 483 |
| permissions_sysconfig | 0 | 130 |
| selinux | 0 | 78 |
| hardware_apps | 0 | 13 |

## Ranked candidates

Video/camera, fingerprint and USB/OTG are first. Full details and exact stock paths/hashes are in audit.json and per-partition Release archives. Every candidate still needs proof of framework, linker, property, VINTF or SELinux mismatch. No speculative binary/manifest transplant is performed.

## ELF dependency candidates



## Limitations

- Binary SELinux policy rules are not decompiled; contexts/CIL only when present.
- VINTF XML inventory is not checkvintf proof.
- Framework overlay resources decoded only when aapt succeeds.
- Differences do not justify overriding stock vendor configs or base performance settings.
