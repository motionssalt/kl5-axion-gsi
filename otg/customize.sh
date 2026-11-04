#!/system/bin/sh
ui_print "****************************************"
ui_print "   TECNO KL5 USB OTG Enabler (v1.0)     "
ui_print "       Author: Victor Jumbo             "
ui_print "       Brand : MOTIONSALT               "
ui_print "****************************************"
ui_print "- Installing /system/bin/otg binary..."

set_perm $MODPATH/system/bin/otg 0 0 0755
set_perm $MODPATH/action.sh 0 0 0755

ui_print "- Checking device compatibility..."
DEVICE_NAME=$(getprop ro.product.device)
BOARD_NAME=$(getprop ro.product.board)
ui_print "  Detected device: $DEVICE_NAME ($BOARD_NAME)"

ui_print "- Module successfully installed!"
ui_print ""
ui_print "Usage via Termux or root shell:"
ui_print "  su -c otg on     -> Turn on USB Host & VBUS 5V"
ui_print "  su -c otg off    -> Turn off USB Host"
ui_print "  su -c otg status -> Check detected USB devices"
ui_print "  su -c otg debug  -> Save log to /sdcard/Download/otg-debug.txt"
ui_print "****************************************"
