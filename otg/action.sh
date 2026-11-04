#!/system/bin/sh
# KernelSU Action script: Toggles OTG on/off
TRAN_BATTERY_DIR="/sys/devices/platform/odm/odm:tran_battery"

current_val=0
if [ -f "$TRAN_BATTERY_DIR/OTG_CTL" ]; then
    current_val=$(cat "$TRAN_BATTERY_DIR/OTG_CTL" 2>/dev/null)
fi

if [ "$current_val" = "1" ]; then
    /system/bin/otg off
else
    /system/bin/otg on
fi
