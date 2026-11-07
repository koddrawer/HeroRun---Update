# Build HeroRunLive.exe (Windows) bằng PyInstaller, rồi gom thành thư mục release\HeroRunLive
#   python tools/build_exe.py
import os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
EXCL = ['app', 'torch', 'torchaudio', 'torchvision', 'transformers', 'gradio', 'librosa', 'numba', 'llvmlite',
        'matplotlib', 'lmdeploy', 'IPython', 'pandas', 'sklearn', 'scipy', 'pytest', 'tensorflow']
args = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', '--windowed',
        '--name', 'HeroRunLive', '--distpath', 'dist', '--workpath', 'build']
if os.path.exists('assets/icon.ico'): args += ['--icon', 'assets/icon.ico']
for m in EXCL: args += ['--exclude-module', m]
for p in ['TikTokLive', 'TikTokLiveProto', 'pygame', 'sea_g2p', 'onnxruntime', 'soundfile', 'pyvirtualcam',
          'kaldi_native_fbank', 'tokenizers', 'soxr']:
    args += ['--collect-all', p]
for p in ['vieneu', 'vieneu_utils', 'betterproto2', 'EulerApiSdk']:
    args += ['--collect-submodules', p, '--collect-data', p]
args += ['--hidden-import', 'exe_deps', 'launcher.py']
print(' '.join(args)); subprocess.check_call(args)

out = os.path.join('release', 'HeroRunLive')
shutil.rmtree('release', ignore_errors=True)
shutil.copytree(os.path.join('dist', 'HeroRunLive'), out)
for d in ['app', 'assets', 'music']:
    shutil.copytree(d, os.path.join(out, d), ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
for f in ['version.json', 'README.md']:
    shutil.copy(f, out)
print('Xong:', out)
