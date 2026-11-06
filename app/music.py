# Nhạc nền: phát danh sách bài (thư mục music\ của bạn hoặc nhạc dựng sẵn), tự chuyển bài
import os, random
import pygame
from .config import ROOT, ASSETS

EXTS = ('.mp3', '.ogg', '.wav', '.flac', '.opus', '.mod', '.xm')
USER_DIR = os.path.join(ROOT, 'music')
BUILTIN_DIR = os.path.join(ASSETS, 'music')
CLASSIC = os.path.join(ASSETS, 'sfx', 'bgm.wav')


def list_dir(d):
    try:
        return sorted(os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(EXTS))
    except OSError:
        return []


class Music:
    """music_source: auto (thư mục của bạn nếu có bài, không thì nhạc dựng sẵn) | folder | builtin | classic | off"""

    def __init__(self, game):
        self.g = game
        self.playlist = []; self.idx = -1
        self.current = ''
        self.sig = None
        self.vol = 0.35
        os.makedirs(USER_DIR, exist_ok=True)

    def folder(self):
        f = (self.g.cfg.get('music_folder') or '').strip()
        if not f: return USER_DIR
        return f if os.path.isabs(f) else os.path.join(ROOT, f)

    def build(self):
        src = self.g.cfg.get('music_source', 'auto')
        if src == 'off': return []
        if src == 'classic': return [CLASSIC]
        user = list_dir(self.folder())
        if src == 'folder': return user
        if src == 'builtin': return list_dir(BUILTIN_DIR)
        return user or list_dir(BUILTIN_DIR) or [CLASSIC]

    def refresh(self, force=False):
        cfg = self.g.cfg
        sig = (cfg.get('music_source'), self.folder(), cfg.get('music_shuffle'))
        if sig == self.sig and not force: return
        self.sig = sig
        self.playlist = self.build()
        if cfg.get('music_shuffle', True): random.shuffle(self.playlist)
        self.idx = -1
        try: pygame.mixer.music.stop()
        except Exception: pass
        self.current = ''
        if not self.playlist:
            self.g.log('Nhạc nền: tắt / thư mục chưa có bài nào')
        else:
            self.g.log(f'Nhạc nền: {len(self.playlist)} bài')
        self.next()

    def next(self):
        if not pygame.mixer.get_init() or not self.playlist: return
        for _ in range(len(self.playlist)):
            self.idx = (self.idx + 1) % len(self.playlist)
            p = self.playlist[self.idx]
            try:
                pygame.mixer.music.load(p)
                loop = -1 if len(self.playlist) == 1 else 0
                pygame.mixer.music.play(loop)
                pygame.mixer.music.set_volume(self.vol)
                self.current = os.path.splitext(os.path.basename(p))[0]
                return
            except Exception as e:
                self.g.log(f'Không phát được {os.path.basename(p)}: {e}')
        self.current = ''

    def update(self, vol):
        self.vol = vol
        if not pygame.mixer.get_init(): return
        self.refresh()
        if self.playlist and not pygame.mixer.music.get_busy():
            self.next()
