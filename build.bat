@echo off
rem Build dist\LibrePhoneCam.exe locally. CI does the same thing on every tag,
rem so this is only needed to test packaging changes.
setlocal
cd /d "%~dp0"

set "VENV=.venv"
set "PY=%VENV%\Scripts\python.exe"

set "BOOTSTRAP=python"
where py >nul 2>&1 && set "BOOTSTRAP=py -3"

if not exist "%PY%" (
  echo   Creating the virtual environment...
  %BOOTSTRAP% -m venv "%VENV%" || goto :fail
)

echo   Installing build dependencies...
"%PY%" -m pip install -r build-tools\requirements.txt --quiet || goto :fail

echo   Building...
"%PY%" -m PyInstaller build-tools\LibrePhoneCam.spec --noconfirm || goto :fail

echo.
echo   Done: dist\LibrePhoneCam.exe
echo.
pause
goto :eof

:fail
echo.
echo   Build failed. The message above should say why.
echo.
pause
exit /b 1
