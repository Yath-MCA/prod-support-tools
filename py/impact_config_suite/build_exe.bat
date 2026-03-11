@echo off
setlocal

set "TARGET=%~1"
if "%TARGET%"=="" set "TARGET=common"
set "LEGACY=%~2"

set "LEGACY_ARG="
if /I "%LEGACY%"=="legacy" set "LEGACY_ARG=-LegacyRefs"

powershell -ExecutionPolicy Bypass -File "%~dp0build_exe.ps1" -Target "%TARGET%" -Clean %LEGACY_ARG%
if errorlevel 1 (
  echo Build failed.
  exit /b 1
)

echo Build finished successfully.
exit /b 0
