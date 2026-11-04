@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "FLASHED_LIST="
set "FAILED_CMD="
set "STAGE=Initialization"

echo ====================================================================
echo   TECNO KL5 (Spark 30C) Axion 2.9 GSI Slot B Flasher
echo ====================================================================
echo.
echo Device: TECNO KL5 (MT6768)
echo Target: Axion 2.9 GSI (Android 16, Treble arm64-ab GAPPS) -^> Slot B
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

echo [PRE-CHECK 1/3] Checking device connection...
fastboot getvar product 2>&1 | findstr /i "product" >nul
if %ERRORLEVEL% NEQ 0 (
  echo [ERROR] No fastboot device detected!
  echo Connect phone via USB in fastboot mode (Volume Down + Power).
  pause
  exit /b 1
)

echo [PRE-CHECK 2/3] Checking bootloader unlocked state...
fastboot getvar unlocked 2>&1 | findstr /i "unlocked: yes" >nul
if %ERRORLEVEL% NEQ 0 (
  echo [WARNING] Bootloader does not report unlocked: yes.
  echo Flashing GSIs requires an unlocked bootloader.
  echo.
) else (
  echo   [OK] Bootloader is UNLOCKED.
)

echo [PRE-CHECK 3/3] Checking image files...
if not exist system.img (
  echo [ERROR] system.img not found!
  echo Please run 1_reassemble.bat first to reassemble the GSI image.
  pause
  exit /b 1
)
if not exist vbmeta.img (
  echo [ERROR] vbmeta.img not found!
  pause
  exit /b 1
)
echo   [OK] system.img and vbmeta.img present.

echo.
echo ====================================================================
echo  NOTICE: Flashing Axion GSI will install Android 16 to slot B.
echo  Stock vendor_b is preserved for hardware drivers and HALs.
echo  product_b and system_ext_b will be cleared to prevent OEM app conflicts.
echo ====================================================================
echo.
set "CONFIRM="
set /p CONFIRM="Type YES (in capital letters) to continue: "
if not "%CONFIRM%"=="YES" (
  echo Cancelled by user.
  pause
  exit /b 0
)

echo.
echo ====================================================================
echo  STAGE 1: FLASHING VBMETA TO SLOT B (AVB DISABLED)
echo ====================================================================
set "STAGE=Stage 1 (AVB Disable)"

echo [*] Flashing vbmeta_b with AVB disabled...
set "FAILED_CMD=fastboot flash --disable-verity --disable-verification vbmeta_b vbmeta.img"
fastboot flash --disable-verity --disable-verification vbmeta_b vbmeta.img
if %ERRORLEVEL% NEQ 0 goto :fail_flash
set "FLASHED_LIST=!FLASHED_LIST! vbmeta_b"

echo.
echo ====================================================================
echo  TRANSITIONING TO FASTBOOTD (USERSPACE)
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
  echo   [OK] Connected to fastbootd!
  goto :fastbootd_ready
)
if %WAIT_COUNT% GEQ 20 (
  echo [ERROR] Timed out waiting for fastbootd mode.
  goto :fail_flash
)
echo   Waiting for fastbootd... (!WAIT_COUNT!/20)
goto :wait_fastbootd

:fastbootd_ready
echo.
echo ====================================================================
echo  STAGE 2: PREPARING DYNAMIC PARTITIONS ^& FLASHING GSI TO SYSTEM_B
echo ====================================================================
set "STAGE=Stage 2 (GSI Logical Flash)"

echo [*] Deleting conflicting OEM logical partitions (product_b, system_ext_b)...
fastboot delete-logical-partition product_b >nul 2>&1
fastboot delete-logical-partition system_ext_b >nul 2>&1

echo [*] Re-creating empty placeholder nodes...
fastboot create-logical-partition product_b 0 >nul 2>&1
fastboot create-logical-partition system_ext_b 0 >nul 2>&1

echo [*] Flashing Axion 2.9 GSI to system_b...
set "FAILED_CMD=fastboot flash system_b system.img"
fastboot flash system_b system.img
if %ERRORLEVEL% NEQ 0 goto :fail_flash
set "FLASHED_LIST=!FLASHED_LIST! system_b"

echo.
echo ====================================================================
echo  STAGE 3: USERDATA WIPE ^& SLOT ACTIVATION
echo ====================================================================
set "STAGE=Stage 3 (Finalization)"

echo.
echo WARNING: When installing a new GSI over stock, formatting userdata
echo (fastboot -w) is required to prevent encryption and database bootloops.
set "WIPE_ANSWER=Y"
set /p WIPE_ANSWER="Wipe user data (factory reset)? (Y/N) [Y]: "
if /i not "%WIPE_ANSWER%"=="N" (
  echo [*] Wiping userdata: fastboot -w...
  set "FAILED_CMD=fastboot -w"
  fastboot -w
  if %ERRORLEVEL% NEQ 0 goto :fail_flash
) else (
  echo [*] Skipping data wipe.
)

echo [*] Setting active slot to B...
set "FAILED_CMD=fastboot --set-active=b"
fastboot --set-active=b
if %ERRORLEVEL% NEQ 0 goto :fail_flash

echo.
echo ====================================================================
echo  [SUCCESS] AXION 2.9 GSI FLASH TO SLOT B COMPLETE!
echo ====================================================================
echo.
set "REBOOT_NOW=Y"
set /p REBOOT_NOW="Reboot system now? (Y/N) [Y]: "
if /i not "%REBOOT_NOW%"=="N" (
  echo [*] Rebooting device into Axion GSI...
  fastboot reboot
)
echo Done. You may close this window.
pause
exit /b 0

:fail_flash
echo.
echo ====================================================================
echo  [FATAL ERROR] GSI FLASH TERMINATED
echo ====================================================================
echo.
echo Stage: %STAGE%
echo Failed command:
echo   %FAILED_CMD%
echo.
echo Flashed partitions:
echo   %FLASHED_LIST%
echo.
echo RECOVERY:
echo   1. Check USB connection and driver in Device Manager.
echo   2. You can safely rerun this script or reflash the stock package
echo      to slot B using 2_flash_stock_b.bat.
echo   3. Slot A was not touched and remains intact.
echo ====================================================================
pause
exit /b 1
