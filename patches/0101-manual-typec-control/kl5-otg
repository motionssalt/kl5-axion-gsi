#!/system/bin/sh
# EXPERIMENTAL: manual Type-C port-type control, not a hardware compatibility fix.
# No boot service, daemon, persistent property, OTG_CTL guess or SELinux changes.
# Source ABI: https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-typec
set -u
PORT=/sys/class/typec/port0
STATE=/data/adb/kl5-otg-manual
active_value() {
    value=$(cat "$1" 2>/dev/null) || return 1
    case "$value" in
        *'['*']'*) printf '%s\n' "$value" | sed -n 's/.*\[\([^]]*\)\].*/\1/p' ;;
        source|sink|dual|host|device) printf '%s\n' "$value" ;;
        *) return 1 ;;
    esac
}
status() {
    for name in port_type power_role data_role; do
        printf '%s: ' "$name"
        cat "$PORT/$name" 2>/dev/null || printf 'unavailable\n'
    done
    printf 'USB devices (excluding root hubs):\n'
    for item in /sys/bus/usb/devices/*; do
        [ -f "$item/idVendor" ] && [ -f "$item/idProduct" ] || continue
        case "${item##*/}" in usb*) continue ;; esac
        printf '%s ' "${item##*/}"; cat "$item/idVendor" "$item/idProduct" | tr '\n' ' '; printf '\n'
    done
    printf 'Role readback is NOT proof of mouse enumeration or VBUS current.\n'
}
case "${1:-}" in
    status) status; exit 0 ;;
    on|off|restore) ACTION=$1 ;;
    *) echo 'usage: kl5-otg on|off|restore|status'; exit 2 ;;
esac
[ "$(id -u)" = 0 ] || { echo 'Root required'; exit 1; }
DEVICE=$(getprop ro.product.vendor.device)
BOARD=$(getprop ro.board.platform)
case "$DEVICE" in *KL5*) ;; *) echo 'Refusing non-KL5 vendor identity'; exit 1 ;; esac
[ "$BOARD" = mt6768 ] || { echo 'Refusing unexpected board platform'; exit 1; }
[ -e "$PORT/port_type" ] && [ -w "$PORT/port_type" ] || { echo 'Stock port_type ABI missing or not writable; inspect USB HAL/SELinux, no bypass attempted'; exit 1; }
umask 077
mkdir -p "$STATE" || exit 1
[ ! -L "$STATE" ] || { echo 'Unsafe state directory'; exit 1; }
chmod 700 "$STATE" || exit 1
mkdir "$STATE/lock" 2>/dev/null || { echo 'Another command is running or an interrupted lock exists; no write attempted'; exit 1; }
trap 'rmdir "$STATE/lock" 2>/dev/null || true' EXIT HUP INT TERM
ORIGINAL=$(active_value "$PORT/port_type") || { echo 'Cannot determine current port type'; exit 1; }
case "$ORIGINAL" in source|sink|dual) ;; *) echo 'Unexpected current port type'; exit 1 ;; esac
if [ "$ACTION" = on ]; then
    # Never force source into a connected charger or other USB power source.
    [ ! -e /sys/class/typec/port0-partner ] || { echo 'Disconnect USB/charger before enabling forced host mode'; exit 1; }
    for online in /sys/class/power_supply/usb/online /sys/class/power_supply/ac/online /sys/class/power_supply/charger/online; do
        [ ! -r "$online" ] || [ "$(cat "$online")" != 1 ] || { echo 'External power detected; refusing forced source mode'; exit 1; }
    done
    TARGET=source
elif [ "$ACTION" = off ]; then
    TARGET=sink
else
    [ -f "$STATE/original-port-type" ] && [ ! -L "$STATE/original-port-type" ] || { echo 'No original state saved'; exit 1; }
    TARGET=$(cat "$STATE/original-port-type")
    case "$TARGET" in source|sink|dual) ;; *) echo 'Invalid saved state'; exit 1 ;; esac
fi
if [ "$ACTION" != restore ] && [ ! -e "$STATE/original-port-type" ]; then
    printf '%s\n' "$ORIGINAL" > "$STATE/original-port-type" || exit 1
fi
# Kernel Type-C class defines source as source-only DFP (host), sink as UFP.
# Synchronous ABI request; never loop/retry or repeatedly fight the vendor HAL.
if ! printf '%s\n' "$TARGET" > "$PORT/port_type"; then
    echo 'Kernel or SELinux rejected the port-type request; no policy changes attempted'
    exit 1
fi
OBSERVED=$(active_value "$PORT/port_type") || OBSERVED=unknown
if [ "$OBSERVED" != "$TARGET" ]; then
    printf '%s\n' "$ORIGINAL" > "$PORT/port_type" 2>/dev/null || true
    echo 'Requested type did not stick; previous type restoration attempted. Vendor HAL may override it'
    exit 1
fi
[ "$ACTION" != restore ] || rm -f "$STATE/original-port-type"
printf 'Port type readback: %s. Hardware operation remains UNVERIFIED.\n' "$OBSERVED"
[ "$ACTION" != on ] || echo 'Now connect the OTG device, then run status. If no enumeration, collect USB HAL/kernel logs; do not force roles repeatedly'
[ "$ACTION" != off ] || echo 'Host forcing disabled (sink-only). Use restore to return to the pre-test port type; reboot also removes runtime forcing'
status
