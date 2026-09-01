@echo off
chcp 65001 >nul
cd /d "%~dp0"
"C:\Users\peng\AppData\Local\Programs\Python\Python311\python.exe" due.py %*
echo.
pause
