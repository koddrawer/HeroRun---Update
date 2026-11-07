# Hero Run Live — điểm khởi chạy
#   python launcher.py          -> bảng điều khiển (tự mở cửa sổ game)
#   python launcher.py --game   -> chỉ cửa sổ game 9:16
import os, sys, importlib, traceback

ROOT = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
os.chdir(ROOT)


def smoke():
    """kiểm tra bản build: python launcher.py --smoke  (ghi kết quả ra smoke.txt)"""
    os.environ['SDL_VIDEODRIVER'] = 'dummy'; os.environ['SDL_AUDIODRIVER'] = 'dummy'
    out = []
    for mod in ['app.panel', 'vieneu', 'vieneu.v3turbo', 'TikTokLive', 'pyvirtualcam', 'soundfile', 'onnxruntime', 'sea_g2p']:
        try:
            importlib.import_module(mod); out.append(f'OK   import {mod}')
        except Exception as e:
            out.append(f'FAIL import {mod}: {e!r}')
    try:
        G = importlib.import_module('app.game')
        g = G.Game(); g.cfg['tts_enabled'] = False; g.cfg['auto_update'] = False
        for i in range(240):
            if i % 40 == 0: g.test('guest')
            if i == 60: g.test('gift', 1)
            if i == 120: g.test('like', 100)
            g.frame(1 / 60)
        out.append(f'OK   game {len(g.a.img)} sprites, music={g.music.current!r}')
    except Exception:
        out.append('FAIL game ' + traceback.format_exc())
    open(os.path.join(ROOT, 'smoke.txt'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    os._exit(0 if not any(x.startswith('FAIL') for x in out) else 1)


def main():
    if '--smoke' in sys.argv:
        smoke(); return
    if '--game' in sys.argv:
        importlib.import_module('app.game').main()
        return
    if getattr(sys, 'frozen', False):
        cmd = [sys.executable, '--game']
    else:
        cmd = [sys.executable, os.path.join(ROOT, 'launcher.py'), '--game']
    importlib.import_module('app.panel').Panel(cmd).run()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        with open(os.path.join(ROOT, 'error.log'), 'a', encoding='utf-8') as f:
            f.write(traceback.format_exc() + '\n')
        raise
