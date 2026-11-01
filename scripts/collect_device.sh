#!/system/bin/sh
# Run on the KL5 as root; collect locally only, NEVER upload private logs automatically.
set -u
OUT=${1:-/sdcard/Download/kl5-diagnostics}
case "$OUT" in /*) ;; *) echo 'Use an absolute output directory'; exit 2 ;; esac
[ "$(id -u)" = 0 ] || { echo 'Run through su as root'; exit 1; }
mkdir -p "$OUT" || exit 1
getprop > "$OUT/getprop.txt" 2>&1
getenforce > "$OUT/selinux-mode.txt" 2>&1
cat /proc/mounts > "$OUT/mount-topology.txt" 2>&1
ls -la /apex > "$OUT/apex-activation.txt" 2>&1
{
  for prop in ro.product.vendor.device ro.board.platform ro.hardware.fingerprint init.svc.vendor.fps_hal init.svc.vendor.focaltech.fps_hal sys.usb.config persist.sys.usb.config ro.vndk.version persist.sys.vndk ro.vendor.build.version.sdk ro.product.first_api_level ro.board.first_api_level debug.stagefright.c2inputsurface debug.stagefright.ccodec; do
    printf '%s=' "$prop"; getprop "$prop"
  done
  printf 'USB gadget UDC: '; cat /config/usb_gadget/g1/UDC 2>&1
  for name in port_type power_role data_role; do
    printf '%s: ' "$name"; cat "/sys/class/typec/port0/$name" 2>&1
  done
  printf 'Stock OTG gate (read only): '; cat /sys/devices/platform/odm/odm:tran_battery/OTG_CTL 2>&1
} > "$OUT/priority-integration-state.txt" 2>&1
lshal > "$OUT/lshal.txt" 2>&1
dmesg > "$OUT/dmesg.txt" 2>&1
logcat -b all -d -v threadtime > "$OUT/logcat.txt" 2>&1
for service in media.codec media.camera fingerprint biometric usb audio sensorservice location wifi bluetooth_manager telephony.registry display thermalservice battery; do
  dumpsys "$service" > "$OUT/dumpsys-$service.txt" 2>&1
done
printf 'Saved locally: %s\nContains potentially private identifiers. Inspect/redact before sharing.\n' "$OUT"
