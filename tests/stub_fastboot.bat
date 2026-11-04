@echo off
setlocal EnableDelayedExpansion

if not defined FASTBOOT_LOG (
  set "FASTBOOT_LOG=%TEMP%astboot_commands.log"
)

echo %* >> "%FASTBOOT_LOG%"

if defined FASTBOOT_FAIL_ON (
  echo %* | findstr /i "%FASTBOOT_FAIL_ON%" >nul
  if !ERRORLEVEL! EQU 0 (
    echo FAILED (remote: simulated failure for %FASTBOOT_FAIL_ON%) >&2
    exit /b 1
  )
)

if "%1"=="devices" (
  echo KL5_SERIAL_TEST    fastboot
  exit /b 0
)

if "%1"=="getvar" (
  if "%2"=="product" (
    echo product: TECNO-KL5
    exit /b 0
  )
  if "%2"=="unlocked" (
    echo unlocked: yes
    exit /b 0
  )
  if "%2"=="current-slot" (
    echo current-slot: b
    exit /b 0
  )
  if "%2"=="is-userspace" (
    if exist "%TEMP%astboot_is_userspace.flag" (
      echo is-userspace: yes
    ) else (
      echo is-userspace: no
    )
    exit /b 0
  )
  echo %2 | findstr /i "partition-size:" >nul
  if !ERRORLEVEL! EQU 0 (
    echo %2: 0x2000000
    exit /b 0
  )
  echo %2: OKAY
  exit /b 0
)

if "%1"=="reboot" (
  if "%2"=="fastboot" (
    echo Rebooting into fastbootd...
    echo 1 > "%TEMP%astboot_is_userspace.flag"
    exit /b 0
  )
  if "%2"=="bootloader" (
    echo Rebooting into bootloader...
    del /f /q "%TEMP%astboot_is_userspace.flag" 2>nul
    exit /b 0
  )
  echo Rebooting device...
  exit /b 0
)

if "%1"=="flash" (
  echo [STUB] Successfully flashed: %*
  exit /b 0
)

if "%1"=="delete-logical-partition" (
  echo [STUB] Deleted logical partition %2
  exit /b 0
)

if "%1"=="create-logical-partition" (
  echo [STUB] Created logical partition %2
  exit /b 0
)

if "%1"=="resize-logical-partition" (
  echo [STUB] Resized logical partition %2
  exit /b 0
)

if "%1"=="--set-active=b" (
  echo [STUB] Setting active slot to b
  exit /b 0
)

if "%1"=="-w" (
  echo [STUB] Erasing userdata and cache
  exit /b 0
)

exit /b 0
