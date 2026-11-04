# TECNO KL5 USB OTG Enabler

**Target:** TECNO KL5 (Spark 30c) on Axion 2.9 GSI (Android 16, MT6768 / Helio G81)  
**Root Method:** KernelSU or Magisk  
**Author:** Victor Jumbo (MOTIONSALT)  

## Why This Module Is Needed
On stock ROM, USB OTG functions out of the box because the stock MediaTek HIDL USB HAL triggers Transsion's proprietary `tran_otg` and `sgm41516d` charger boost drivers.
On Axion 2.9 GSI (Android 16), the Android system server expects an AIDL USB HAL (`android.hardware.usb.IUsb`), which does not exist on the Android 14 vendor partition. Consequently, the phone switches data roles but **never activates VBUS 5V power**, preventing USB drives, mice, and keyboards from powering on.

Furthermore, Transsion's kernel driver `store_OTG_CTL` is strictly **edge-triggered**: writing `1` when the cached state is already `1` is a complete no-op. This module applies the exact `0 -> 1` edge trigger with safe delay, enables the Type-C DFP host/source roles, sets MediaTek USB controller to host, and turns on 5V VBUS.

## Usage
Open Termux or any terminal emulator and run:

```bash
# Turn on OTG and supply 5V to connected devices
su -c otg on

# Check real-time status and see attached USB devices
su -c otg status

# Turn off OTG when finished
su -c otg off

# If anything goes wrong, generate a comprehensive diagnostic report:
su -c otg debug
# Log is written to /sdcard/Download/otg-debug.txt
```

## KernelSU Action Button
In the KernelSU Manager app, navigate to the **Modules** tab. This module includes an **Action** button that allows you to toggle OTG host mode on and off with a single tap without opening a terminal.
