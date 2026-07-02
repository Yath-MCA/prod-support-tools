@echo off
REM Change to parent directory (project root) where main.py is located
cd /d "%~dp0.."

python main.py
pause
