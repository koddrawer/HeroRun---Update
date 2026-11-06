import os, json, threading, urllib.request, io, hashlib, colorsys
import pygame
from .config import ASSETS

SPR = os.path.join(ASSETS, 'sprites')


class Assets:
    def __init__(self):
        self.meta = json.load(open(os.path.join(SPR, 'meta.json'), encoding='utf-8'))
        self.img = {}
        for f in os.listdir(SPR):
            if f.endswith('.png'):
                self.img[f[:-4]] = pygame.image.load(os.path.join(SPR, f)).convert_alpha()
        self._scaled = {}
        self._flip = {}
        self.fonts = {}
        self.sounds = {}
        self.sfx_vol = 0.7
        self.mus_vol = 0.35
        self._load_sounds()

    # ---------- ảnh ----------
    def get(self, name, scale=1.0, flip=False):
        key = (name, round(scale, 3), flip)
        s = self._scaled.get(key)
        if s is None:
            s = self.img[name]
            if scale != 1.0:
                s = pygame.transform.smoothscale_by(s, scale) if scale < 1 else pygame.transform.scale_by(s, scale)
            if flip:
                s = pygame.transform.flip(s, True, False)
            self._scaled[key] = s
        return s

    # ---------- chữ ----------
    def font(self, size, kind='pixel'):
        key = (size, kind)
        f = self.fonts.get(key)
        if f is None:
            path = os.path.join(ASSETS, 'fonts', kind + '.ttf')
            f = pygame.font.Font(path, size)
            self.fonts[key] = f
        return f

    # ---------- âm thanh ----------
    def _load_sounds(self):
        d = os.path.join(ASSETS, 'sfx')
        if not pygame.mixer.get_init(): return
        for f in os.listdir(d):
            if f.endswith('.wav') and f != 'bgm.wav':
                try:
                    self.sounds[f[:-4]] = pygame.mixer.Sound(os.path.join(d, f))
                except Exception:
                    pass

    def play(self, name, vol=1.0):
        s = self.sounds.get(name)
        if s and pygame.mixer.get_init():
            s.set_volume(max(0, min(1, self.sfx_vol * vol)))
            s.play()

    def music(self, vol):
        self.mus_vol = vol
        if not pygame.mixer.get_init(): return
        try:
            if not pygame.mixer.music.get_busy():
                pygame.mixer.music.load(os.path.join(ASSETS, 'sfx', 'bgm.wav'))
                pygame.mixer.music.play(-1)
            pygame.mixer.music.set_volume(vol)
        except Exception:
            pass


# ---------------- Avatar ----------------
def _color_for(uid):
    h = int(hashlib.md5(uid.encode('utf-8')).hexdigest()[:6], 16) / 0xFFFFFF
    r, g, b = colorsys.hsv_to_rgb(h, 0.55, 0.85)
    return int(r * 255), int(g * 255), int(b * 255)


class Avatars:
    SIZE = 128

    def __init__(self, assets):
        self.a = assets
        self.raw = {}       # uid -> (bytes, (w,h)) từ luồng tải
        self.surf = {}      # uid -> Surface tròn
        self.pending = set()
        self.lock = threading.Lock()
        self.cache = {}

    def request(self, uid, url, name):
        if uid in self.surf or uid in self.pending: return
        self.surf[uid] = self._placeholder(uid, name)
        if not url: return
        self.pending.add(uid)
        threading.Thread(target=self._fetch, args=(uid, url), daemon=True).start()

    def _fetch(self, uid, url):
        try:
            from PIL import Image, ImageDraw
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            data = urllib.request.urlopen(req, timeout=8).read()
            im = Image.open(io.BytesIO(data)).convert('RGBA').resize((self.SIZE, self.SIZE), Image.LANCZOS)
            mask = Image.new('L', im.size, 0)
            ImageDraw.Draw(mask).ellipse([0, 0, self.SIZE - 1, self.SIZE - 1], fill=255)
            im.putalpha(mask)
            with self.lock:
                self.raw[uid] = im.tobytes()
        except Exception:
            pass
        self.pending.discard(uid)

    def _placeholder(self, uid, name):
        s = pygame.Surface((self.SIZE, self.SIZE), pygame.SRCALPHA)
        c = _color_for(uid)
        pygame.draw.circle(s, c, (64, 64), 64)
        pygame.draw.circle(s, (255, 255, 255), (64, 64), 64, 6)
        ch = (name or '?').strip()[:1].upper() or '?'
        try:
            t = self.a.font(90, 'bold').render(ch, True, (255, 255, 255))
            s.blit(t, t.get_rect(center=(64, 70)))
        except Exception:
            pass
        return s

    def pump(self):
        with self.lock:
            items = list(self.raw.items()); self.raw.clear()
        for uid, b in items:
            self.surf[uid] = pygame.image.frombytes(b, (self.SIZE, self.SIZE), 'RGBA').convert_alpha()
            for k in [k for k in self.cache if k[0] == uid]:
                del self.cache[k]

    def get(self, uid, diameter):
        d = max(4, int(diameter))
        key = (uid, d)
        s = self.cache.get(key)
        if s is None:
            base = self.surf.get(uid)
            if base is None: return None
            s = pygame.transform.smoothscale(base, (d, d))
            self.cache[key] = s
            if len(self.cache) > 600:
                for k in list(self.cache)[:200]: del self.cache[k]
        return s
