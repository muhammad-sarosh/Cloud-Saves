@echo off
setlocal enableextensions

:: Change if your venv has a different name
set "ENV_NAME=windows_env"

:: Script dir (folder containing this .bat)
set "SCRIPT_DIR=%~dp0"
:: Project root is two levels up when script is Autostart\Windows\
pushd "%SCRIPT_DIR%..\.." || (
  echo [ERROR] Failed to change directory to project root
  exit /b 1
)
set "PROJECT_DIR=%CD%\"
popd

:: Activate virtual environment
if exist "%PROJECT_DIR%%ENV_NAME%\Scripts\activate.bat" (
  call "%PROJECT_DIR%%ENV_NAME%\Scripts\activate.bat"
) else (
  echo [ERROR] Virtual environment "%ENV_NAME%" not found in: %PROJECT_DIR%
  echo Create it or edit ENV_NAME in this file.
  pause
  exit /b 1
)

:: Prefer venv's pythonw.exe; fall back to system pythonw.exe if needed
set "PYW=%PROJECT_DIR%%ENV_NAME%\Scripts\pythonw.exe"
if not exist "%PYW%" set "PYW=pythonw.exe"

:: start "" detaches so the window can close immediately
start "" "%PYW%" "%PROJECT_DIR%auto.py"
