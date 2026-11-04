#!/system/bin/sh
# Safe late-start service script
# Wait until system boot is completed
while [ "$(getprop sys.boot_completed)" != "1" ]; do
    sleep 2
done

# Ensure permissions on binaries if overlaid
chmod 0755 /system/bin/otg 2>/dev/null || true

# Safe initial state: Do NOT force host mode at boot
# Host mode should be activated on demand via `otg on` or action button.
exit 0
