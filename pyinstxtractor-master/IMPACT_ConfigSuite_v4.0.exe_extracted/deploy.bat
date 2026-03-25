@ECHO ON
cd /d "%~dp0"
Powershell.exe -executionpolicy bypass -File "auto_upload.ps1" -client "%~1" -filePath "%~2"