@echo off
cd /d "%~dp0"
where python >nul 2>nul || (echo Can cai Python 3.11+ tu python.org (tick "Add to PATH") & pause & exit /b)
echo Dang kiem tra thu vien...
python -m pip install -q -r requirements.txt
start "" pythonw launcher.py
