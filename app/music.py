# Nhạc nền: nhạc dựng sẵn + thư mục music\ của bạn; chọn 1 bài cố định hoặc phát cả danh sách
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


def user_folder(cfg):
    f = (cfg.get('music_folder') or '').strip()
    if not f: return USER_DIR
    return f if os.path.isabs(f) else os.path.join(ROOT, f)


def all_tracks(cfg):
    """[(key, tên hiển thị, đường dẫn)] — key: 'builtin/x.ogg' | 'folder/y.mp3' | 'classic'"""
    out = [('builtin/' + os.path.basename(p), '★ ' + os.path.splitext(os.path.basename(p))[0], p)
           for p in list_dir(BUILTIN_DIR)]
    out += [('folder/' + os.path.basename(p), '♪ ' + os.path.splitext(os.path.basename(p))[0], p)
            for p in list_dir(user_folder(cfg))]
    out.append(('classic', '★ nhạc cũ của game', CLASSIC))
    return out


class Music:
    """music_source: all | builtin | folder | classic | off  (auto = thư mục của bạn nếu có, không thì dựng sẵn)
       music_track: '' = phát cả danh sách, hoặc key 1 bài (lặp lại bài đó)"""

    def __init__(self, game):
        self.g = game
        self.playlist = []; self.idx = -1
        self.current = ''
        self.sig = None
        self.vol = 0.35
        self.paused = False
        os.makedirs(USER_DIR, exist_ok=True)

    def build(self):
        cfg = self.g.cfg
        src = cfg.get('music_source', 'all')
        if src == 'off': return []
        tracks = all_tracks(cfg)
        key = (cfg.get('music_track') or '').strip()
        if key:
            for k, _, p in tracks:
                if k == key and os.path.exists(p): return [p]
        if src == 'classic': return [CLASSIC]
        builtin = [p for k, _, p in tracks if k.startswith('builtin/')]
        user = [p for k, _, p in tracks if k.startswith('folder/')]
        if src == 'folder': return user
        if src == 'builtin': return builtin
        if src == 'auto': return user or builtin or [CLASSIC]
        return builtin + user or [CLASSIC]

    def refresh(self, force=False):
        cfg = self.g.cfg
        sig = (cfg.get('music_source'), user_folder(cfg), cfg.get('music_shuffle'), cfg.get('music_track'))
        if sig == self.sig and not force: return
        self.sig = sig
        self.playlist = self.build()
        if cfg.get('music_shuffle', True) and len(self.playlist) > 1: random.shuffle(self.playlist)
        self.idx = -1; self.paused = False
        try: pygame.mixer.music.stop()
        except Exception: pass
        self.current = ''
        if not self.playlist:
            self.g.log('Nhạc nền: tắt / chưa có bài nào')
        else:
            self.g.log(f'Nhạc nền: {len(self.playlist)} bài')
        self.next()

    def _play(self, i):
        p = self.playlist[i]
        pygame.mixer.music.load(p)
        pygame.mixer.music.play(-1 if len(self.playlist) == 1 else 0)
        pygame.mixer.music.set_volume(self.vol)
        self.idx = i; self.paused = False
        self.current = os.path.splitext(os.path.basename(p))[0]

    def next(self, step=1):
        if not pygame.mixer.get_init() or not self.playlist: return
        n = len(self.playlist)
        for k in range(1, n + 1):
            i = (self.idx + step * k) % n
            try:
                self._play(i); return
            except Exception as e:
                self.g.log(f'Không phát được {os.path.basename(self.playlist[i])}: {e}')
        self.current = ''
        if self.playlist != [CLASSIC]:
            self.g.log('Chuyển sang nhạc nền dự phòng (wav)')
            self.playlist = [CLASSIC]; self.idx = -1
            self.next()
        else:
            self.playlist = []

    def prev(self):
        self.next(-1)

    def toggle_pause(self):
        if not pygame.mixer.get_init(): return
        if self.paused:
            pygame.mixer.music.unpause(); self.paused = False
        else:
            pygame.mixer.music.pause(); self.paused = True

    def status(self):
        if not self.current: return '—'
        return ('⏸ ' if self.paused else '') + self.current

    def update(self, vol):
        self.vol = vol
        if not pygame.mixer.get_init(): return
        self.refresh()
        if self.playlist and not self.paused and not pygame.mixer.music.get_busy():
            self.next()
