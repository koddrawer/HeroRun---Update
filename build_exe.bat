@echo off
REM Dong goi thanh HeroRunLive.exe (code trong app\ van nam ngoai exe de cap nhat nong)
cd /d "%~dp0"
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --noconfirm --onedir --windowed --name HeroRunLive --exclude-module app ^
  --collect-all TikTokLive --collect-all TikTokLiveProto --collect-all pygame --collect-all vieneu --collect-all vieneu_utils --collect-all sea_g2p --collect-all onnxruntime --collect-all soundfile ^
  --hidden-import PIL.Image --hidden-import PIL.ImageDraw --hidden-import tkinter --hidden-import tkinter.ttk ^
  --hidden-import tkinter.messagebox --hidden-import queue --hidden-import colorsys --hidden-import hashlib ^
  launcher.py
xcopy /e /i /y dist\HeroRunLive\* .\ >nul
echo Xong: HeroRunLive.exe + thu muc _internal (de cung thu muc voi app\ va assets\)
pause
