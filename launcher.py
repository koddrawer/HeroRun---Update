# Hero Run Live — điểm khởi chạy
#   python launcher.py          -> bảng điều khiển (tự mở cửa sổ game)
#   python launcher.py --game   -> chỉ cửa sổ game 9:16
import os, sys, importlib, traceback

ROOT = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
os.chdir(ROOT)


def main():
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
