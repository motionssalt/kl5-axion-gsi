@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "FLASHED_LIST="
set "FAILED_CMD="
set "STAGE=Initialization"

echo ====================================================================
echo   TECNO KL5 (Spark 30C) Stock Firmware Slot B Flasher
echo ====================================================================
echo.
echo Device: TECNO KL5 (Helio G81 / MT6768)
echo Target Slot: B (slot A is completely untouched)
echo.

rem Check fastboot binary
where fastboot >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
  if exist fastboot.exe (
    set "PATH=%~dp0;%PATH%"
  ) else (
    echo [ERROR] fastboot command was not found!
    echo Please make sure this script is running inside your platform-tools folder
    echo or that fastboot.exe is added to your Windows PATH.
    pause
    exit /b 1
  )
)

echo [PRE-CHECK 1/4] Checking device connection...
fastboot getvar product 2>&1 | findstr /i "product" >nul
if %ERRORLEVEL% NEQ 0 (
  echo [ERROR] No fastboot device detected!
  echo 1. Connect phone via USB cable.
  echo 2. Boot to fastboot mode (Hold Volume Down + Power).
  echo 3. Check Device Manager to ensure MediaTek/Android Fastboot drivers are installed.
  pause
  exit /b 1
)

echo [PRE-CHECK 2/4] Checking bootloader unlocked state...
fastboot getvar unlocked 2>&1 | findstr /i "unlocked: yes" >nul
if %ERRORLEVEL% NEQ 0 (
  echo [WARNING] Device does not report unlocked: yes!
  echo If the bootloader is locked, fastboot flashing will fail.
  echo Proceed only if you have already unlocked the bootloader.
  echo.
) else (
  echo   [OK] Bootloader is UNLOCKED.
)

echo [PRE-CHECK 3/4] Checking required image files...
if not exist manifest.txt (
  echo [ERROR] manifest.txt is missing. Please re-run 1_reassemble.bat first.
  pause
  exit /b 1
)

set "MISSING_IMG=0"
for /f "usebackq tokens=1,2 delims=|" %%A in ("manifest.txt") do (
  if not exist "%%B" (
    echo   [ERROR] Missing joined image file: %%B
    set "MISSING_IMG=1"
  )
)
if %MISSING_IMG% NEQ 0 (
  echo.
  echo [ERROR] Some image files are missing.
  echo Please run 1_reassemble.bat to reassemble all parts before flashing.
  pause
  exit /b 1
)
echo   [OK] All image files are present.

echo [PRE-CHECK 4/4] Mode check...
fastboot getvar is-userspace 2>&1 | findstr /i "is-userspace: yes" >nul
if %ERRORLEVEL% EQU 0 (
  echo   Device is currently in fastbootd (userspace).
  echo   Rebooting to bootloader fastboot for Stage 1 physical flashing...
  fastboot reboot bootloader
  timeout /t 5 >nul
) else (
  echo   [OK] Device is in bootloader fastboot mode.
)

echo.
echo ====================================================================
echo  CAUTION: THIS OPERATION WILL FLASH THE STOCK ROM TO SLOT B.
echo  Forbidden partitions (preloader, nvram, nvdata, persist, etc.)
echo  will NEVER be touched to protect IMEI and calibration data.
echo ====================================================================
echo.
set "CONFIRM="
set /p CONFIRM="Type YES (in capital letters) to start flashing: "
if not "%CONFIRM%"=="YES" (
  echo Flashing cancelled by user.
  pause
  exit /b 0
)

echo.
echo ====================================================================
echo  STAGE 1: FLASHING PHYSICAL PARTITIONS IN BOOTLOADER FASTBOOT
echo ====================================================================
set "STAGE=Stage 1 (Bootloader Physical Flash)"

rem Flash vbmeta with disable flags first
echo.
echo [*] Flashing vbmeta_b (with AVB disabled)...
set "FAILED_CMD=fastboot flash --disable-verity --disable-verification vbmeta_b vbmeta.img"
fastboot flash --disable-verity --disable-verification vbmeta_b vbmeta.img
if %ERRORLEVEL% NEQ 0 goto :fail_flash
set "FLASHED_LIST=!FLASHED_LIST! vbmeta_b"

rem Flash boot, vendor_boot, dtbo
call :FlashPhysical boot_b boot.img
if %ERRORLEVEL% NEQ 0 goto :fail_flash

call :FlashPhysical vendor_boot_b vendor_boot.img
if %ERRORLEVEL% NEQ 0 goto :fail_flash

call :FlashPhysical dtbo_b dtbo.img
if %ERRORLEVEL% NEQ 0 goto :fail_flash

rem Flash vbmeta chained partitions if present
if exist vbmeta_system.img (
  call :FlashPhysical vbmeta_system_b vbmeta_system.img
  if %ERRORLEVEL% NEQ 0 goto :fail_flash
)

if exist vbmeta_vendor.img (
  call :FlashPhysical vbmeta_vendor_b vbmeta_vendor.img
  if %ERRORLEVEL% NEQ 0 goto :fail_flash
)

rem Flash MediaTek firmware physical A/B partitions
call :FlashPhysical md1img_b md1img.img
if %ERRORLEVEL% NEQ 0 goto :fail_flash

call :FlashPhysical spmfw_b spmfw.img
if %ERRORLEVEL% NEQ 0 goto :fail_flash

call :FlashPhysical scp_b scp.img
if %ERRORLEVEL% NEQ 0 goto :fail_flash

call :FlashPhysical sspm_b sspm.img
if %ERRORLEVEL% NEQ 0 goto :fail_flash

call :FlashPhysical gz_b gz.img
if %ERRORLEVEL% NEQ 0 goto :fail_flash

call :FlashPhysical lk_b lk.img
if %ERRORLEVEL% NEQ 0 goto :fail_flash

call :FlashPhysical logo_b logo.bin
if %ERRORLEVEL% NEQ 0 goto :fail_flash

call :FlashPhysical tee_b tee.img
if %ERRORLEVEL% NEQ 0 goto :fail_flash

call :FlashPhysical tkv_b tkv.img
if %ERRORLEVEL% NEQ 0 goto :fail_flash

echo.
echo ====================================================================
echo  TRANSITIONING TO FASTBOOTD (USERSPACE) FOR LOGICAL PARTITIONS
echo ====================================================================
set "STAGE=Rebooting to fastbootd"
echo [*] Sending: fastboot reboot fastboot...
set "FAILED_CMD=fastboot reboot fastboot"
fastboot reboot fastboot
if %ERRORLEVEL% NEQ 0 goto :fail_flash

echo [*] Waiting for fastbootd to become ready...
set "WAIT_COUNT=0"
:wait_fastbootd
timeout /t 3 >nul
set /a WAIT_COUNT+=1
fastboot getvar is-userspace 2>&1 | findstr /i "is-userspace: yes" >nul
if %ERRORLEVEL% EQU 0 (
  echo   [OK] Connected to fastbootd (userspace fastboot)!
  goto :fastbootd_ready
)
if %WAIT_COUNT% GEQ 20 (
  echo [ERROR] Timed out waiting for fastbootd mode.
  echo Please check the phone screen: if it shows fastbootd menu, ensure USB is connected.
  goto :fail_flash
)
echo   Waiting for fastbootd... (!WAIT_COUNT!/20)
goto :wait_fastbootd

:fastbootd_ready
echo.
echo ====================================================================
echo  STAGE 2: FLASHING LOGICAL PARTITIONS IN FASTBOOTD
echo ====================================================================
set "STAGE=Stage 2 (fastbootd Logical Flash)"

call :FlashLogical product_b product.img
if %ERRORLEVEL% NEQ 0 goto :fail_flash

call :FlashLogical system_b system.img
if %ERRORLEVEL% NEQ 0 goto :fail_flash

call :FlashLogical system_ext_b system_ext.img
if %ERRORLEVEL% NEQ 0 goto :fail_flash

call :FlashLogical vendor_b vendor.img
if %ERRORLEVEL% NEQ 0 goto :fail_flash

if exist tr_product.img (
  call :FlashLogical tr_product_b tr_product.img
  if %ERRORLEVEL% NEQ 0 goto :fail_flash
)

if exist tr_mi.img (
  call :FlashLogical tr_mi_b tr_mi.img
  if %ERRORLEVEL% NEQ 0 goto :fail_flash
)

if exist tr_theme.img (
  call :FlashLogical tr_theme_b tr_theme.img
  if %ERRORLEVEL% NEQ 0 goto :fail_flash
)

if exist tr_preload.img (
  call :FlashLogical tr_preload_b tr_preload.img
  if %ERRORLEVEL% NEQ 0 goto :fail_flash
)

if exist tr_region.img (
  call :FlashLogical tr_region_b tr_region.img
  if %ERRORLEVEL% NEQ 0 goto :fail_flash
)

if exist tr_company.img (
  call :FlashLogical tr_company_b tr_company.img
  if %ERRORLEVEL% NEQ 0 goto :fail_flash
)

if exist tr_carrier.img (
  call :FlashLogical tr_carrier_b tr_carrier.img
  if %ERRORLEVEL% NEQ 0 goto :fail_flash
)

echo.
echo ====================================================================
echo  STAGE 3: FINALIZATION
echo ====================================================================
set "STAGE=Stage 3 (Finalization)"

echo.
echo Notice: If you are returning from a GSI (like Axion) back to stock,
echo formatting user data is STRONGLY recommended to prevent bootloops.
set "WIPE_ANSWER=N"
set /p WIPE_ANSWER="Wipe user data (factory reset)? (Y/N) [N]: "
if /i "!WIPE_ANSWER!"=="Y" (
  echo [*] Formatting user data: fastboot -w...
  set "FAILED_CMD=fastboot -w"
  fastboot -w
  if %ERRORLEVEL% NEQ 0 goto :fail_flash
) else (
  echo [*] Skipping data wipe. Existing user data preserved.
)

echo [*] Setting active slot to B...
set "FAILED_CMD=fastboot --set-active=b"
fastboot --set-active=b
if %ERRORLEVEL% NEQ 0 goto :fail_flash

echo.
echo ====================================================================
echo  [SUCCESS] TECNO KL5 STOCK FIRMWARE FLASH TO SLOT B COMPLETE!
echo ====================================================================
echo.
echo Flashed partitions:
echo %FLASHED_LIST%
echo.
set "REBOOT_NOW=Y"
set /p REBOOT_NOW="Reboot system now? (Y/N) [Y]: "
if /i not "%REBOOT_NOW%"=="N" (
  echo [*] Rebooting phone...
  fastboot reboot
)
echo Done. You may close this window.
pause
exit /b 0

rem ====================================================================
rem Subroutine: Flash Physical Partition
rem ====================================================================
:FlashPhysical
set "P_NAME=%~1"
set "P_FILE=%~2"

if not exist "%P_FILE%" (
  echo [SKIP] %P_FILE% not found. Skipping %P_NAME%.
  exit /b 0
)

rem Check if partition exists on phone
fastboot getvar partition-size:%P_NAME% 2>&1 | findstr /i "FAILED" >nul
if %ERRORLEVEL% EQU 0 (
  echo [SKIP] Partition %P_NAME% does not exist on this device. Skipping.
  exit /b 0
)

echo [*] Flashing physical partition %P_NAME% with %P_FILE%...
set "FAILED_CMD=fastboot flash %P_NAME% %P_FILE%"
fastboot flash %P_NAME% %P_FILE%
if %ERRORLEVEL% NEQ 0 exit /b 1

set "FLASHED_LIST=!FLASHED_LIST! %P_NAME%"
exit /b 0

rem ====================================================================
rem Subroutine: Flash Logical Partition (fastbootd)
rem ====================================================================
:FlashLogical
set "L_NAME=%~1"
set "L_FILE=%~2"

if not exist "%L_FILE%" (
  echo [SKIP] %L_FILE% not found. Skipping %L_NAME%.
  exit /b 0
)

echo [*] Flashing logical partition %L_NAME% with %L_FILE%...
set "FAILED_CMD=fastboot flash %L_NAME% %L_FILE%"
fastboot flash %L_NAME% %L_FILE%
if %ERRORLEVEL% NEQ 0 exit /b 1

set "FLASHED_LIST=!FLASHED_LIST! %L_NAME%"
exit /b 0

rem ====================================================================
rem Error Recovery Handler
rem ====================================================================
:fail_flash
echo.
echo ====================================================================
echo  [FATAL ERROR] FLASHING PROCESS TERMINATED
echo ====================================================================
echo.
echo The script halted at stage: %STAGE%
echo Failed command:
echo   %FAILED_CMD%
echo.
echo Partitions successfully flashed so far:
if "%FLASHED_LIST%"=="" (
  echo   (None)
) else (
  echo   %FLASHED_LIST%
)
echo.
echo RECOVERY HINT:
echo   1. Do NOT panic or disconnect the device abruptly.
echo   2. Check USB cable connection and driver state in Device Manager.
echo   3. Rerun this script. It will safely overwrite or continue slot B.
echo   4. If it keeps failing, flash the stock images manually to the _b
echo      partitions as before.
echo   5. Slot A was not touched and remains intact.
echo ====================================================================
pause
exit /b 1
