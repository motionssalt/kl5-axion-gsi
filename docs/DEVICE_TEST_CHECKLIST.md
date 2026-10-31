# Physical KL5 test checklist

**Emulator evidence proves only boot/UI. All MediaTek hardware remains unverified until these tests pass on the phone.** Keep a working stock restore path. Run tests on an unpatched base too when comparing behavior. Do not publish IMEI, phone numbers, account names, WiFi details or unredacted personal logs.

## Baseline and evidence

From an adb-capable host:

```sh
adb shell getprop ro.product.device
adb shell getprop ro.board.platform
adb shell getprop ro.build.version.sdk
adb shell getprop ro.vndk.version
adb shell getprop ro.vendor.build.version.sdk
adb shell getprop ro.treble.enabled
adb shell getprop sys.boot_completed
adb shell getenforce
adb shell lshal > kl5-lshal.txt
adb shell dumpsys -l > kl5-services.txt
adb shell su -c 'dmesg' > kl5-dmesg.txt
adb logcat -b all -d -v threadtime > kl5-logcat.txt
```

For phone-only Termux, `su -c 'getprop'`, `su -c 'dmesg'`, and `su -c 'logcat -b all -d -v threadtime'` provide local equivalents. Root access changes log availability; permission-denied output is not proof no fault exists. `scripts/collect_device.sh` gathers a local bundle without uploading anything.

## 1 — Video and camera (highest priority)

Play known-good local H.264 and HEVC samples at 720p, 1080p and the highest stock-supported resolution; record codec/profile/frame rate and whether hardware acceleration is actually used. Test 1080p camera video recording, playback, audio sync, front/rear switching and a 1080p video-editor export. Success at 720p alone is a failure for the reported issue.

```sh
adb shell dumpsys media.codec > media-codec.txt
adb shell dumpsys media.camera > media-camera.txt
adb shell dumpsys media.extractor > media-extractor.txt
adb shell 'ls -l /vendor/etc/media* /odm/etc/media* /system/etc/media*' > media-config-paths.txt
adb logcat -b all -d -v threadtime | grep -Ei 'codec2|c2\.|OMX|ACodec|MediaCodec|Mtk|camera|avc: denied|linker' > media-failure.txt
```

Do not force a software decoder as a claimed hardware fix. Collect logs immediately after reproducing playback/record/export failures.

## 2 — Fingerprint

Remove/re-enrol a test finger through Settings only if a fallback PIN is known. Test screen-on enrolment, unlock after lock, reboot/PIN-first behavior and repeated touches. Do not erase biometric/vendor data as a workaround.

```sh
adb shell dumpsys fingerprint > fingerprint.txt
adb shell dumpsys biometric > biometric.txt
adb logcat -b all -d -v threadtime | grep -Ei 'fingerprint|biometric|goodix|fpc|hwservicemanager|servicemanager|avc: denied' > fingerprint-failure.txt
```

Sensor listed in Settings is not a pass; actual touch detection and successful enrolment are required.

## 3 — Manual OTG on/off

With the optional evidence-derived helper only: request `kl5-otg on`, connect a known-good low-power mouse through the known-good adapter, and verify pointer movement **and** kernel USB enumeration. Switch off, disconnect and confirm charging/data behavior recovers. No automatic/background switch is installed.

```sh
adb shell dumpsys usb > usb.txt
adb shell su -c 'find /sys/class/typec /sys/class/usb_role -maxdepth 3 -type f 2>/dev/null' > usb-role-paths.txt
adb shell su -c 'dmesg | grep -Ei "usb|xhci|type.?c|rt.pd|otg|vbus"' > usb-kernel.txt
adb logcat -b all -d -v threadtime | grep -Ei 'UsbPort|UsbDevice|UsbHost|typec|otg|avc: denied' > usb-failure.txt
```

Property readback or OTG_CTL alone is not a pass. Do not short pins, force unknown charger registers or disable SELinux.

## 4 — Full regression coverage

Test speakers, earpiece, microphone, wired/Bluetooth audio, voice calls, SMS, mobile data, VoLTE/IMS registration where supported, dual-SIM behavior, WiFi/hotspot, Bluetooth pairing, GNSS fix, NFC if physically present, proximity/ambient-light/rotation sensors, screen brightness/refresh/colors, vibrator/lights, charging/USB data, thermal safety and suspend/wake. Compare features to stock, not marketing assumptions. Collect `dumpsys audio`, `dumpsys sensorservice`, `dumpsys location`, `dumpsys wifi`, `dumpsys bluetooth_manager`, `dumpsys telephony.registry`, `dumpsys display`, `dumpsys thermalservice`, `dumpsys battery` and the corresponding logcat/dmesg around each fault.

Passing static checks or emulator boot does not validate any of these physical functions.
