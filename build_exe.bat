@echo off
REM Build HeroRunLive.exe -> thu muc release\HeroRunLive (copy ca thu muc nay di la chay)
cd /d "%~dp0"
python -m pip install -r requirements.txt pyinstaller
python tools\build_exe.py
pause
