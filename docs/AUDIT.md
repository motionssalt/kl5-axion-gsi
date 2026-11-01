# KL5 stock versus GSI audit

Static evidence only. Missing vendor files inside a GSI are NOT automatically gaps: the stock vendor stays on the device.

Stock partitions: product, system, system_ext, tr_product, vendor

Base partitions: system

## Coverage

| Area | Stock files | Base files |
|---|---:|---:|
| vintf | 57 | 23 |
| init | 289 | 105 |
| props | 14 | 3 |
| media | 157 | 57 |
| camera | 192 | 39 |
| fingerprint | 23 | 23 |
| usb_otg | 55 | 19 |
| audio | 600 | 500 |
| sensors | 74 | 24 |
| gnss | 58 | 19 |
| nfc | 7 | 9 |
| bluetooth | 60 | 20 |
| wifi | 69 | 15 |
| telephony_ims | 214 | 75 |
| display | 118 | 176 |
| power_thermal_charging | 183 | 48 |
| vibrator_lights | 53 | 34 |
| overlays | 47 | 483 |
| permissions_sysconfig | 130 | 130 |
| selinux | 53 | 78 |
| hardware_apps | 5 | 13 |

## Ranked candidates

Video/camera, fingerprint and USB/OTG are first. Full details and exact stock paths/hashes are in audit.json and per-partition Release archives. Every candidate still needs proof of framework, linker, property, VINTF or SELinux mismatch. No speculative binary/manifest transplant is performed.

## ELF dependency candidates

android.hardware.gnss-V1-ndk_platform.so, android.hardware.light-V1-ndk_platform.so, android.hardware.power-V2-ndk_platform.so, android.hardware.vibrator-V2-ndk_platform.so, android.system.keystore2-V1-ndk_platform.so, libadb_pairing_connection.so, libadb_pairing_server.so, libandroidicu.so, libicu.so, libnativehelper.so, libnativeloader.so, libneuralnetworks.so, libstatspull.so, libstatssocket.so, libtouch_ll_imp.so

## Limitations

- Binary SELinux policy rules are not decompiled; contexts/CIL only when present.
- VINTF XML inventory is not checkvintf proof.
- Framework overlay resources decoded only when aapt succeeds.
- Differences do not justify overriding stock vendor configs or base performance settings.
