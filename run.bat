@echo off
setlocal
cd /d "%~dp0"
title LibrePhoneCam

rem The QR code is drawn with block-drawing characters; a legacy console code
rem page turns them into mojibake.
chcp 65001 >nul

set "VENV=.venv"
set "PY=%VENV%\Scripts\python.exe"

rem The py launcher is the reliable way to find Python on Windows; fall back to
rem whatever is on PATH.
set "BOOTSTRAP=python"
where py >nul 2>&1 && set "BOOTSTRAP=py -3"

if not exist "%PY%" (
  echo   Creating the virtual environment ^(one time only^)...
  %BOOTSTRAP% -m venv "%VENV%"
  if errorlevel 1 goto :nopython
)

rem Cheaper and more honest than a timestamp stamp file: ask Python whether the
rem imports actually resolve.
"%PY%" -c "import aiohttp, cryptography, qrcode, colorama" >nul 2>&1
if errorlevel 1 (
  echo   Installing dependencies ^(one time only^)...
  "%PY%" -m pip install --upgrade pip --quiet
  "%PY%" -m pip install -r requirements.txt --quiet
  if errorlevel 1 goto :fail
)

rem No arguments: open the desktop app. Any argument means the caller wants
rem the command line (ports, --ip, and so on).
if "%~1"=="" (
  "%VENV%\Scripts\pythonw.exe" -m librephonecam.gui
  goto :eof
)

"%PY%" -m librephonecam %*
if errorlevel 1 goto :fail
goto :eof

:nopython
echo.
echo   Python was not found.
echo   Install it from https://python.org/downloads and tick
echo   "Add python.exe to PATH" during setup, then run this file again.
echo.
pause
exit /b 1

:fail
echo.
echo   Something went wrong. The message above should say what.
echo.
pause
exit /b 1
