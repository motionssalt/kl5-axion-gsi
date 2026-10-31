#!/system/bin/sh
# Run on the KL5 as root; collect locally only, NEVER upload private logs automatically.
set -u
OUT=${1:-/sdcard/Download/kl5-diagnostics}
case "$OUT" in /*) ;; *) echo 'Use an absolute output directory'; exit 2 ;; esac
[ "$(id -u)" = 0 ] || { echo 'Run through su as root'; exit 1; }
mkdir -p "$OUT" || exit 1
getprop > "$OUT/getprop.txt" 2>&1
getenforce > "$OUT/selinux-mode.txt" 2>&1
lshal > "$OUT/lshal.txt" 2>&1
dmesg > "$OUT/dmesg.txt" 2>&1
logcat -b all -d -v threadtime > "$OUT/logcat.txt" 2>&1
for service in media.codec media.camera fingerprint biometric usb audio sensorservice location wifi bluetooth_manager telephony.registry display thermalservice battery; do
  dumpsys "$service" > "$OUT/dumpsys-$service.txt" 2>&1
done
printf 'Saved locally: %s\nContains potentially private identifiers. Inspect/redact before sharing.\n' "$OUT"
