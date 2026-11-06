import random, math
import pygame


class Text:
    """Render chữ có viền, có cache."""

    def __init__(self, assets):
        self.a = assets
        self.cache = {}

    def clean(self, text, font):
        try:
            m = font.metrics(text)
            if m and all(x is not None for x in m): return text
            return ''.join(ch for ch, mm in zip(text, m) if mm is not None)
        except Exception:
            return text

    def render(self, text, size, color=(255, 255, 255), outline=(20, 16, 30), ow=3, kind='pixel', maxw=0):
        key = (text, size, color, outline, ow, kind, maxw)
        s = self.cache.get(key)
        if s is not None: return s
        f = self.a.font(size, kind)
        t = self.clean(str(text), f) or ' '
        if maxw:
            while len(t) > 3 and f.size(t)[0] > maxw:
                t = t[:-2] + '…' if not t.endswith('…') else t[:-2] + '…'
                t = self.clean(t, f) or t
        base = f.render(t, False, color)
        if ow:
            o = f.render(t, False, outline)
            s = pygame.Surface((base.get_width() + ow * 2, base.get_height() + ow * 2), pygame.SRCALPHA)
            for dx in range(-ow, ow + 1, max(1, ow)):
                for dy in range(-ow, ow + 1, max(1, ow)):
                    if dx or dy: s.blit(o, (dx + ow, dy + ow))
            s.blit(base, (ow, ow))
        else:
            s = base
        if len(self.cache) > 800: self.cache.clear()
        self.cache[key] = s
        return s

    def draw(self, surf, text, pos, size, color=(255, 255, 255), anchor='center', **kw):
        s = self.render(text, size, color, **kw)
        r = s.get_rect(**{anchor: pos})
        surf.blit(s, r)
        return r


class Particle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'life', 'max', 'col', 'size', 'g', 'shape')

    def __init__(self, x, y, vx, vy, life, col, size, g=600, shape='sq'):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max = life
        self.col, self.size, self.g, self.shape = col, size, g, shape


class FX:
    def __init__(self, text):
        self.p = []
        self.texts = []
        self.text = text

    def burst(self, x, y, cols, n=16, spd=260, life=0.6, size=6, g=700):
        for _ in range(n):
            a = random.uniform(0, math.tau); s = random.uniform(0.3, 1) * spd
            self.p.append(Particle(x, y, math.cos(a) * s, math.sin(a) * s - spd * 0.3, life * random.uniform(0.6, 1.2),
                                   random.choice(cols), random.randint(max(2, size - 3), size + 2), g))

    def sparkle(self, x, y, cols, n=10, r=40):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            self.p.append(Particle(x + math.cos(a) * r * random.random(), y + math.sin(a) * r * random.random(),
                                   random.uniform(-40, 40), random.uniform(-120, -30), random.uniform(0.4, 0.9),
                                   random.choice(cols), random.randint(3, 6), 0, 'star'))

    def dust(self, x, y, n=4):
        for _ in range(n):
            self.p.append(Particle(x + random.uniform(-10, 10), y, random.uniform(-160, -60), random.uniform(-60, -10),
                                   random.uniform(0.3, 0.5), random.choice([(222, 205, 170), (190, 170, 140)]),
                                   random.randint(4, 8), 80))

    def float_text(self, txt, x, y, col=(255, 240, 120), size=40, life=1.2):
        self.texts.append([txt, x, y, col, size, life, life])

    def update(self, dt, scroll):
        for q in self.p:
            q.vy += q.g * dt
            q.x += (q.vx - scroll) * dt
            q.y += q.vy * dt
            q.life -= dt
        self.p = [q for q in self.p if q.life > 0]
        if len(self.p) > 900: self.p = self.p[-900:]
        for t in self.texts:
            t[2] -= 60 * dt
            t[5] -= dt
        self.texts = [t for t in self.texts if t[5] > 0]

    def draw(self, s):
        for q in self.p:
            k = q.life / q.max
            sz = max(1, int(q.size * (0.4 + 0.6 * k)))
            if q.shape == 'star':
                c = q.col
                pygame.draw.rect(s, c, (q.x - sz, q.y - 1, sz * 2 + 1, 3))
                pygame.draw.rect(s, c, (q.x - 1, q.y - sz, 3, sz * 2 + 1))
            else:
                pygame.draw.rect(s, q.col, (int(q.x), int(q.y), sz, sz))
        for txt, x, y, col, size, life, mx in self.texts:
            r = self.text.render(txt, size, col)
            k = life / mx
            if k < 0.3:
                r = r.copy(); r.set_alpha(int(255 * k / 0.3))
            s.blit(r, r.get_rect(center=(int(x), int(y))))


HEART = ["01100110", "11111111", "11111111", "11111111", "01111110", "00111100", "00011000"]


def pixel_heart(size, col=(255, 70, 110), outline=(90, 10, 40)):
    px = max(1, size // 8)
    s = pygame.Surface((px * 10, px * 9), pygame.SRCALPHA)
    for y, row in enumerate(HEART):
        for x, c in enumerate(row):
            if c == '1':
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    pygame.draw.rect(s, outline, ((x + 1 + dx) * px, (y + 1 + dy) * px, px, px))
    for y, row in enumerate(HEART):
        for x, c in enumerate(row):
            if c == '1':
                pygame.draw.rect(s, col, ((x + 1) * px, (y + 1) * px, px, px))
    pygame.draw.rect(s, (255, 200, 220), (2 * px, 2 * px, px, px))
    return s


def pixel_coin(size):
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    r = size // 2
    pygame.draw.circle(s, (120, 70, 10), (r, r), r)
    pygame.draw.circle(s, (255, 196, 40), (r, r), r - max(2, size // 10))
    pygame.draw.circle(s, (255, 236, 140), (r, r), r - max(4, size // 4), max(2, size // 12))
    pygame.draw.rect(s, (255, 250, 210), (r - size // 8, size // 5, max(2, size // 8), max(3, size // 4)))
    return s


def chain(s, x, y0, y1, col=(70, 70, 82), hl=(150, 150, 165)):
    """xích pixel thẳng đứng"""
    y = y0
    i = 0
    while y < y1:
        h = 14
        if i % 2 == 0:
            pygame.draw.rect(s, (25, 22, 30), (x - 6, y, 12, h), 0, 3)
            pygame.draw.rect(s, col, (x - 4, y + 2, 8, h - 4), 2, 2)
            pygame.draw.line(s, hl, (x - 3, y + 3), (x - 3, y + h - 4))
        else:
            pygame.draw.rect(s, (25, 22, 30), (x - 2, y - 2, 4, h + 4))
            pygame.draw.rect(s, col, (x - 1, y, 2, h))
        y += h - 3; i += 1
