@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ====================================================================
echo   TECNO KL5 (Spark 30C) Firmware Reassembly Utility
echo ====================================================================
echo.
echo Free disk space notice:
echo Ensure you have at least 15 GB of free disk space on this drive
echo while parts and joined images coexist.
echo.

if not exist manifest.txt (
  echo [ERROR] manifest.txt not found in current folder: %CD%
  echo Please make sure all release files were downloaded into this directory.
  pause
  exit /b 1
)

if not exist SHA256SUMS.txt (
  echo [ERROR] SHA256SUMS.txt not found in current folder: %CD%
  echo Please make sure all release files were downloaded into this directory.
  pause
  exit /b 1
)

set "ERRORS_FOUND=0"

rem Read manifest line by line
rem Format: TARGET_PARTITION|JOINED_FILE|EXPECTED_SHA256|PARTS_LIST (plus-separated, e.g. p1+p2 or single file)
for /f "usebackq tokens=1,2,3,4 delims=|" %%A in ("manifest.txt") do (
  set "LINE_TARGET=%%A"
  set "JOINED_FILE=%%B"
  set "EXPECTED_SHA=%%C"
  set "PARTS_LIST=%%D"
  
  if not "!JOINED_FILE!"=="" (
    echo --------------------------------------------------------------------
    echo Processing: !JOINED_FILE! ^(Target: !LINE_TARGET!^)
    
    set "NEEDS_JOIN=1"
    if exist "!JOINED_FILE!" (
      echo   Checking existing file !JOINED_FILE!...
      call :VerifyHash "!JOINED_FILE!" "!EXPECTED_SHA!"
      if !ERRORLEVEL! EQU 0 (
        echo   [OK] !JOINED_FILE! already exists and SHA256 matches. Skipping reassembly.
        set "NEEDS_JOIN=0"
      ) else (
        echo   [INFO] Existing !JOINED_FILE! hash did not match. Re-joining from parts...
        del /f /q "!JOINED_FILE!" 2>nul
        set "NEEDS_JOIN=1"
      )
    )
    
    if "!NEEDS_JOIN!"=="1" (
      rem Verify all required parts exist before copying
      set "MISSING_PARTS=0"
      for %%P in (!PARTS_LIST:+^= !) do (
        if not exist "%%P" (
          echo   [ERROR] Missing part file: %%P
          set "MISSING_PARTS=1"
          set "ERRORS_FOUND=1"
        )
      )
      
      if !MISSING_PARTS! NEQ 0 (
        echo   [ABORT] Cannot reassemble !JOINED_FILE! due to missing part files.
        echo   Please verify your download from GitHub Releases.
        pause
        exit /b 1
      )
      
      rem Check if multi-part or single file
      if not "!PARTS_LIST!"=="!JOINED_FILE!" (
        echo   Joining parts: !PARTS_LIST! -^> !JOINED_FILE!
        copy /b !PARTS_LIST! "!JOINED_FILE!" >nul
        if !ERRORLEVEL! NEQ 0 (
          echo   [ERROR] copy /b command failed for !JOINED_FILE!
          set "ERRORS_FOUND=1"
          pause
          exit /b 1
        )
      )
      
      echo   Verifying SHA256 hash for !JOINED_FILE!...
      call :VerifyHash "!JOINED_FILE!" "!EXPECTED_SHA!"
      if !ERRORLEVEL! NEQ 0 (
        echo   [ERROR] SHA256 checksum mismatch for !JOINED_FILE!
        echo   Expected: !EXPECTED_SHA!
        echo   The downloaded parts may be corrupted. Please re-download.
        set "ERRORS_FOUND=1"
        pause
        exit /b 1
      ) else (
        echo   [OK] Verified SHA256 checksum: !JOINED_FILE!
      )
    )
  )
)

echo.
echo ====================================================================
if !ERRORS_FOUND! NEQ 0 (
  echo [FAILURE] One or more errors occurred during reassembly.
  echo Review the output above and re-download missing/corrupted files.
  pause
  exit /b 1
)

echo [SUCCESS] All files reassembled and cryptographically verified!
echo ====================================================================
echo.

set "DEL_ANSWER=N"
set /p DEL_ANSWER="Would you like to delete the downloaded .part* files to save disk space? (Y/N) [N]: "
if /i "!DEL_ANSWER!"=="Y" (
  echo Deleting part files...
  del /f /q *.part* 2>nul
  echo Done.
)

echo.
echo You can now proceed to run the flash script.
pause
exit /b 0

:VerifyHash
set "TARGET_FILE=%~1"
set "TARGET_EXPECTED=%~2"
set "COMPUTED_HASH="

for /f "tokens=* skip=1" %%H in ('certutil -hashfile "%TARGET_FILE%" SHA256 2^>nul') do (
  if not defined COMPUTED_HASH (
    set "COMPUTED_HASH=%%H"
    set "COMPUTED_HASH=!COMPUTED_HASH: =!"
  )
)

if /i "!COMPUTED_HASH!"=="!TARGET_EXPECTED!" (
  exit /b 0
) else (
  exit /b 1
)
