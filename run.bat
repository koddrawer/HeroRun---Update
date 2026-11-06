@echo off
cd /d "%~dp0"
where python >nul 2>nul || (echo Can cai Python 3.11+ tu python.org (tick "Add to PATH") & pause & exit /b)
if not exist ".deps_ok" (
  python -m pip install -r requirements.txt && echo ok> .deps_ok
)
start "" pythonw launcher.py
