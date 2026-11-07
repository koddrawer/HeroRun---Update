# Windows: nạp sẵn các DLL của pygame (libpng, libjpeg, ogg...) theo đường dẫn đầy đủ.
# SDL_image / SDL_mixer nạp chúng "động" lúc chạy; trong bản .exe (PyInstaller) thư mục pygame
# không nằm trong đường tìm DLL nên báo "Failed loading libpng16-16.dll".
import os, sys


def _preload_pygame_dlls():
    if sys.platform != 'win32':
        return
    try:
        import ctypes, importlib.util
        dirs = []
        spec = importlib.util.find_spec('pygame')
        if spec and spec.submodule_search_locations:
            dirs += list(spec.submodule_search_locations)
        base = getattr(sys, '_MEIPASS', None)
        if base:
            dirs += [os.path.join(base, 'pygame'), base]
        exe_dir = os.path.dirname(sys.executable)
        dirs += [os.path.join(exe_dir, '_internal', 'pygame'), os.path.join(exe_dir, 'pygame')]
        seen = set()
        for d in dirs:
            d = os.path.abspath(d)
            if d in seen or not os.path.isdir(d):
                continue
            seen.add(d)
            try:
                os.add_dll_directory(d)
            except Exception:
                pass
            os.environ['PATH'] = d + os.pathsep + os.environ.get('PATH', '')
            # nạp thư viện phụ trước, SDL sau
            names = sorted((f for f in os.listdir(d) if f.lower().endswith('.dll')),
                           key=lambda f: (f.lower().startswith('sdl2'), f.lower()))
            for f in names:
                try:
                    ctypes.WinDLL(os.path.join(d, f))
                except OSError:
                    pass
    except Exception:
        pass


_preload_pygame_dlls()
