# HERO RUN LIVE — game side-scroller 8-bit cho TikTok LIVE (cửa sổ 9:16)
import os, sys, math, random, time, queue
import pygame

from . import config as C
from .assets import Assets, Avatars
from .fx import Text, FX, pixel_heart, pixel_coin, chain
from .ipc import Server
from .tiktok_client import TikTokThread
from . import voice as V
from .music import Music
from .vcam import VirtualCam

W, H = 720, 1280
GROUND_Y = 905
HERO_X = 200
WORLD_TOP = 150

FAKE_NAMES = ['Bé Na', 'Anh Tú', 'Minh Khang', 'Linh Chi', 'Hoàng Long', 'Thu Trang', 'Đức Anh', 'Mai Phương',
              'Gia Bảo', 'Ngọc Hân', 'Quốc Huy', 'Bảo Ngọc', 'Tuấn Kiệt', 'Hồng Nhung', 'Văn Hùng', 'Khánh Vy']


def set_dpi_aware():
    """Windows: tắt co giãn DPI để cửa sổ đúng kích thước pixel (LIVE Studio capture chuẩn)"""
    if sys.platform != 'win32': return
    try:
        import ctypes
        try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception: ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def clamp(v, a, b): return a if v < a else b if v > b else v


def ease_out_back(t):
    c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


# =====================================================================
class Camera:
    def __init__(self):
        self.z = 1.0; self.fx = W / 2; self.fy = H / 2
        self.reqs = []
        self.shake = 0.0
        self.now = 0.0

    def request(self, focus, zoom, dur=None):
        r = {'focus': focus, 'zoom': zoom, 'until': (self.now + dur) if dur else None, 'done': False}
        self.reqs.append(r)
        return r

    def update(self, dt):
        self.now += dt
        now = self.now
        self.reqs = [r for r in self.reqs if not r['done'] and (r['until'] is None or now < r['until'])]
        if self.reqs:
            r = self.reqs[-1]
            tz = r['zoom']; tfx, tfy = r['focus']()
        else:
            tz, tfx, tfy = 1.0, W / 2, H / 2
        k = min(1, dt * 6)
        self.z += (tz - self.z) * k
        self.fx += (tfx - self.fx) * k
        self.fy += (tfy - self.fy) * k
        self.shake = max(0, self.shake - dt * 30)

    def apply(self, world, out):
        sx = random.uniform(-self.shake, self.shake); sy = random.uniform(-self.shake, self.shake)
        if self.z < 1.01:
            out.blit(world, (sx, sy))
            return
        w, h = W / self.z, H / self.z
        x = clamp(self.fx - w / 2 + sx, 0, W - w)
        y = clamp(self.fy - h / 2 + sy, 0, H - h)
        sub = world.subsurface(pygame.Rect(int(x), int(y), int(w), int(h)))
        pygame.transform.scale(sub, (W, H), out)


# =====================================================================
class Hero:
    def __init__(self, g):
        self.g = g
        self.reset()

    def reset(self):
        self.x = HERO_X; self.y = GROUND_Y
        self.state = 'run'; self.t = 0; self.act_t = 0; self.dur = 0.8
        self.jump_h = 110; self.yoff = 0
        self.hurt = 0
        self.power_t = 0; self.power_kind = 'damage'; self.power_uid = None
        self.shoot_cd = 0; self.aim = None

    @property
    def frames(self): return self.g.a.meta['hero']['frames']

    def busy(self): return self.state in ('jump', 'slide')

    def airborne(self):
        return self.state == 'jump' and 0.12 < self.act_t / self.dur < 0.86

    def low(self):
        return self.state == 'slide' and 0.12 < self.act_t / self.dur < 0.86

    def start_jump(self, width, rel):
        self.state = 'jump'; self.act_t = 0
        self.dur = clamp((width + 80) / max(60, rel) + 0.3, 0.75, 1.4)
        self.jump_h = clamp(60 + width * 0.35, 90, 150)
        self.g.a.play('jump', 0.8)
        self.g.chatter(V.HERO_JUMP)

    def start_slide(self, width, rel):
        self.state = 'slide'; self.act_t = 0
        self.dur = clamp((width + 80) / max(60, rel) + 0.3, 0.75, 1.5)
        self.g.a.play('slide', 0.8)
        self.g.chatter(V.HERO_SLIDE)

    def hitbox(self):
        if self.low():
            return pygame.Rect(self.x - 36, self.y - 70, 72, 70)
        return pygame.Rect(self.x - 26, self.y - 128 + self.yoff, 52, 124)

    def chest(self):
        r = self.hitbox(); return r.centerx, r.centery

    def stumble(self):
        """vấp chướng ngại (không mất máu, chỉ hiệu ứng)"""
        g = self.g
        self.hurt = 0.35
        g.cam.shake = max(g.cam.shake, 5)
        g.a.play('hurt', 0.7)
        g.fx.float_text('ÁI DA!', self.x, self.y - 190, (255, 200, 120), 34)
        g.chatter(V.HERO_HURT, 0.5)

    def muzzle(self, aim):
        mx, my = self.g.a.meta['hero']['muzzle_shoot45' if aim == 'up' else 'muzzle_shoot']
        return self.x + mx, self.y + self.yoff + my

    def laser_col(self):
        return BUFF_COL[self.power_kind] if self.power_t > 0 else (60, 210, 255)

    def update(self, dt):
        g = self.g
        self.t += dt
        self.hurt = max(0, self.hurt - dt)
        self.power_t = max(0, self.power_t - dt)
        self.yoff = 0
        if self.state in ('jump', 'slide'):
            self.act_t += dt
            p = self.act_t / self.dur
            if self.state == 'jump':
                u = clamp((p - 0.1) / 0.78, 0, 1)
                self.yoff = -self.jump_h * 4 * u * (1 - u)
                if p >= 1:
                    self.state = 'run'; g.fx.dust(self.x, GROUND_Y, 6)
            else:
                if self.low() and int(self.t * 30) % 2 == 0: g.fx.dust(self.x - 30, GROUND_Y, 2)
                if p >= 1: self.state = 'run'
        # ngắm: ưu tiên vẽ avatar donate, sau đó bắn pet hết giờ
        self.shoot_cd -= dt
        self.aim = None
        art = g.art_cur
        if art is not None and art.firing():
            self.aim = 'up'
            return
        tg = g.pet_target()
        if tg is not None:
            self.aim = 'up' if tg.fly else 'fwd'
            if self.shoot_cd <= 0:
                self.shoot_cd = g.cfg['fire_interval']
                self.fire(tg)

    def anim_frame(self):
        fr = self.frames
        if self.state == 'jump':
            p = clamp(self.act_t / self.dur, 0, 0.999)
            if p < 0.12: i = int(p / 0.12 * 2)
            elif p < 0.86: i = 2 + int((p - 0.12) / 0.74 * 4)
            else: i = 6 + int((p - 0.86) / 0.14 * 2)
            return fr['jump'][clamp(i, 0, 7)]
        if self.state == 'slide':
            p = clamp(self.act_t / self.dur, 0, 0.999)
            if p < 0.12: i = int(p / 0.12 * 2)
            elif p < 0.86: i = 2 + int(self.act_t * 12) % 4
            else: i = 6 + int((p - 0.86) / 0.14 * 2)
            return fr['slide'][clamp(i, 0, 7)]
        row = {'up': 'shoot45', 'fwd': 'shoot'}.get(self.aim, 'run')
        i = int(self.t * 13) % 8
        if row != 'run' and i < 2: i += 2   # luôn khung đang bắn
        return fr[row][i]

    def fire(self, tg):
        g = self.g
        sx, sy = self.muzzle(self.aim or 'fwd')
        tx, ty = tg.center()
        dx, dy = tx - sx, ty - sy
        d = math.hypot(dx, dy) or 1
        spd = 1000
        g.bullets.append(Bullet(sx, sy, dx / d * spd, dy / d * spd, tg, self.laser_col()))
        g.a.play('shoot', 0.35)

    def draw(self, s):
        g = self.g
        f = self.anim_frame()
        img = g.a.get(f['img'])
        x, y = self.x - f['ax'], self.y + self.yoff - f['ay']
        if self.hurt > 0:
            img = img.copy(); img.fill((255, 80, 80, 0), special_flags=pygame.BLEND_RGBA_ADD)
        elif self.power_t > 0 and int(self.t * 8) % 2 == 0:
            c = BUFF_COL[self.power_kind]
            img = img.copy(); img.fill((c[0] // 4, c[1] // 4, c[2] // 4, 0), special_flags=pygame.BLEND_RGBA_ADD)
        # bóng
        sh = pygame.Surface((70, 12), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 70), sh.get_rect())
        s.blit(sh, (self.x - 35, GROUND_Y - 6))
        if self.power_t > 0:
            c = BUFF_COL[self.power_kind]
            rad = 74
            surf = pygame.Surface((rad * 2 + 8, rad * 2 + 8), pygame.SRCALPHA)
            a = int(60 + 30 * math.sin(self.t * 6))
            pygame.draw.circle(surf, (*c, a // 2), (rad + 4, rad + 4), rad)
            pygame.draw.circle(surf, (*c, a + 80), (rad + 4, rad + 4), rad, 3)
            s.blit(surf, (self.x - rad - 4, self.y + self.yoff - 70 - rad - 4))
            if random.random() < 0.3:
                g.fx.sparkle(self.x, self.y + self.yoff - 70, [c, (255, 255, 255)], 1, 60)
        s.blit(img, (x, y))


# =====================================================================
class Bullet:
    def __init__(self, x, y, vx, vy, target, col):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.target = target; self.col = col
        self.dead = False

    def update(self, dt):
        self.x += self.vx * dt; self.y += self.vy * dt
        if self.x > W + 40 or self.x < -40 or self.y < 0 or self.y > H: self.dead = True

    def draw(self, s):
        d = math.hypot(self.vx, self.vy) or 1
        ux, uy = self.vx / d, self.vy / d
        L = 36
        x0, y0 = self.x - ux * L, self.y - uy * L
        pygame.draw.line(s, self.col, (x0, y0), (self.x, self.y), 8)
        pygame.draw.line(s, (240, 255, 255), (x0 + ux * 8, y0 + uy * 8), (self.x, self.y), 3)


# =====================================================================
class Trap:
    ROLL = {'spike_log': 90, 'boulder': 120}

    def __init__(self, g, tdef, x):
        self.g = g; self.d = tdef
        self.img = g.a.get(tdef['img'])
        self.w, self.h = self.img.get_size()
        self.x = x + self.w / 2      # tâm
        self.action = tdef['action']; self.hang = tdef['hang']
        self.vx = self.ROLL.get(tdef['id'], 0)
        self.t = random.uniform(0, 5)
        self.triggered = False; self.resolved = False; self.fail = False
        if self.hang == 1:
            self.bottom = GROUND_Y - 98
        elif self.hang == 2:
            self.bottom = GROUND_Y - 118 + self.h / 2
        else:
            sink = {'lava': 26, 'lava2': 26, 'spike_block': 34, 'spike_updown': 10, 'saw': 18, 'thorns': 12}
            self.bottom = GROUND_Y + sink.get(tdef['id'], 6)

    def update(self, dt, scroll):
        self.t += dt
        self.x -= (scroll + self.vx) * dt
        return self.x > -self.w

    def draw(self, s):
        img = self.img
        tid = self.d['id']
        bottom = self.bottom
        cx = self.x
        if tid == 'crusher':
            bottom += (math.sin(self.t * 3) * 0.5 + 0.5) * -20
        if tid == 'boulder':
            img = pygame.transform.rotate(img, (self.t * 260) % 360)
            s.blit(img, img.get_rect(center=(cx, bottom - self.h / 2)))
            return
        if tid == 'spike_log':
            bottom += -abs(math.sin(self.t * 8)) * 4
        top = bottom - self.h
        if self.hang:
            # xích treo từ trần
            if top > WORLD_TOP:
                if tid in ('swing',):
                    chain(s, cx - self.w * 0.33, WORLD_TOP, top + 8); chain(s, cx + self.w * 0.33, WORLD_TOP, top + 8)
                elif tid in ('flame', 'arrows'):
                    bx = cx + self.w / 2 - 28
                    pygame.draw.rect(s, (40, 36, 46), (bx - 12, WORLD_TOP, 24, top - WORLD_TOP + 6))
                    pygame.draw.rect(s, (90, 86, 100), (bx - 8, WORLD_TOP, 16, top - WORLD_TOP + 6))
                else:
                    chain(s, cx, WORLD_TOP, top + 8)
        if tid == 'axe':
            ang = math.sin(self.t * 3.2) * 16
            r = pygame.transform.rotate(img, ang)
            # xoay quanh đỉnh
            piv = pygame.math.Vector2(0, self.h / 2).rotate(-ang)
            s.blit(r, r.get_rect(center=(cx + piv.x, top + piv.y)))
            return
        if tid == 'flame':
            k = 0.9 + 0.1 * math.sin(self.t * 30)
            s.blit(img, img.get_rect(midbottom=(cx, bottom)))
            return
        s.blit(img, img.get_rect(midbottom=(cx, bottom)))


# =====================================================================
class Guest:
    def __init__(self, g, user, gdef):
        self.g = g
        self.uid = user['uid']; self.name = user['name']
        self.d = gdef
        self.fly = bool(gdef['fly'])
        self.sc = g.cfg['guest_scale']
        self.img = g.a.get(gdef['img'], self.sc)
        self.w, self.h = self.img.get_size()
        self.x = random.uniform(HERO_X + 120, W - 70) if self.fly else random.uniform(70, W - 70)
        self.y = random.uniform(260, 640) if self.fly else GROUND_Y + 6
        self.tx, self.ty = self.x, self.y
        self.t = random.uniform(0, 6)
        self.active = self.born = time.time()
        self.state = 'in'; self.st = 0
        self.dir = random.choice([-1, 1])
        self.speed = random.uniform(40, 75)
        self.doomed = False; self.doom_t = 0
        self.palette = self._palette()

    def _palette(self):
        """màu để nổ thành hạt pixel"""
        cols = []
        w, h = self.img.get_size()
        for _ in range(40):
            c = self.img.get_at((random.randrange(w), random.randrange(h)))
            if c.a > 200: cols.append((c.r, c.g, c.b))
        return cols or [(255, 255, 255)]

    def touch(self): self.active = time.time()

    def doom(self):
        """hết giờ: bay ra trước mặt Hero để bị bắn"""
        if not self.doomed:
            self.doomed = True; self.doom_t = 0
            self.speed = 230

    def ready(self):
        return self.doomed and self.state == 'live' and HERO_X + 110 < self.x < W - 30

    def center(self):
        cy = self.draw_y()
        return (self.x, cy) if self.fly else (self.x, cy - self.h * 0.5)

    def update(self, dt):
        self.t += dt; self.st += dt
        if self.state == 'in' and self.st > 0.45: self.state = 'live'
        if self.state == 'out':
            if self.st > 0.3: self.state = 'gone'
            return
        if self.doomed:
            self.doom_t += dt
            if self.doom_t > 7: self.g.pop_guest(self); return
            if self.fly:
                self.tx = max(self.tx, HERO_X + 220); self.ty = clamp(self.ty, 300, 620)
            else:
                self.tx = max(self.x, HERO_X + 200)
                self.dir = 1
        if self.fly:
            if math.hypot(self.tx - self.x, self.ty - self.y) < 8:
                lo = HERO_X + 220 if self.doomed else 70
                self.tx = random.uniform(lo, W - 70); self.ty = random.uniform(250, 650)
            dx, dy = self.tx - self.x, self.ty - self.y
            d = math.hypot(dx, dy) or 1
            self.x += dx / d * self.speed * dt; self.y += dy / d * self.speed * dt
            if abs(dx) > 2: self.dir = 1 if dx > 0 else -1
        else:
            if self.doomed and self.x >= self.tx:
                return
            self.x += self.dir * self.speed * dt
            if self.x < 60: self.dir = 1
            if self.x > W - 60: self.dir = -1
            if not self.doomed and random.random() < dt * 0.15: self.dir *= -1

    def leave(self):
        """biến mất nhẹ (xoá thủ công)"""
        if self.state != 'out':
            self.state = 'out'; self.st = 0
            self.g.fx.burst(self.x, self.draw_y(), [(255, 255, 255), (200, 200, 255)], 12, 160, 0.5, 5, 0)

    def pop(self):
        """bị bắn: nổ tan thành hạt pixel"""
        if self.state == 'out': return
        g = self.g
        cx, cy = self.center()
        g.fx.burst(cx, cy, self.palette, 46, 380, 0.9, 9, 500)
        g.fx.burst(cx, cy, [(255, 255, 255), (255, 240, 150)], 14, 240, 0.4, 5, 0)
        g.fx.float_text('BÙM!', cx, cy - 50, (255, 230, 120), 40, 0.9)
        g.a.play('explode', 0.55)
        self.state = 'out'; self.st = 0

    def draw_y(self):
        if self.fly: return self.y + math.sin(self.t * 2.6) * 10
        return self.y - abs(math.sin(self.t * 7)) * 12

    def draw(self, s):
        g = self.g
        k = 1.0
        if self.state == 'in': k = ease_out_back(clamp(self.st / 0.45, 0, 1))
        elif self.state == 'out': k = 1 - clamp(self.st / 0.3, 0, 1)
        if k <= 0.02: return
        cy = self.draw_y()
        img = self.img
        flip = not self.fly and self.dir < 0
        if flip:
            img = g.a.get(self.d['img'], self.sc, True)
        hole = self.d['hole']
        if self.fly:
            pos = (self.x - self.w / 2, cy - self.h / 2)
        else:
            pos = (self.x - self.w / 2, cy - self.h)
        hx = (self.w - hole[0] * self.sc) if flip else hole[0] * self.sc
        hy = hole[1] * self.sc; hr = hole[2] * self.sc
        if k < 0.999:
            img = pygame.transform.smoothscale_by(img, k)
            ox = (self.w - img.get_width()) / 2; oy = (self.h - img.get_height()) / 2
            pos = (pos[0] + ox, pos[1] + oy); hx = hx * k; hy = hy * k; hr *= k
        av = g.av.get(self.uid, hr * 2 + 6)
        if av is not None:
            s.blit(av, av.get_rect(center=(pos[0] + hx, pos[1] + hy)))
        if self.doomed and int(self.t * 10) % 2 == 0:
            img = img.copy(); img.fill((90, 30, 30, 0), special_flags=pygame.BLEND_RGBA_ADD)
        s.blit(img, pos)
        if k > 0.6:
            t = g.text.render(self.name, 22, (255, 255, 255), maxw=150)
            s.blit(t, t.get_rect(midtop=(self.x, pos[1] + img.get_height() - 4)))
            if not self.doomed and self.state == 'live':
                left = g.cfg['guest_life'] - (time.time() - self.born)
                if left <= 10:
                    tt = g.text.render(str(max(0, int(left + 0.99))), 26, (255, 120, 120))
                    s.blit(tt, tt.get_rect(midbottom=(self.x, pos[1] + 6)))


# =====================================================================
BUFF_COL = {'damage': (255, 120, 60), 'heal': (120, 255, 120), 'armor': (120, 190, 255)}
BUFF_TXT = {'damage': '+SỨC MẠNH', 'heal': '+NĂNG LƯỢNG', 'armor': '+KHIÊN SÁNG'}


class SkyArt:
    """Donate: Hero bắn tia sáng lên trời, ghép thành avatar 8-bit của người tặng (càng nhiều xu càng to)."""

    def __init__(self, g, user, coins):
        self.g = g; self.user = user; self.coins = coins
        cfg = g.cfg
        cmax = max(2, cfg['art_coins_max'])
        self.k = clamp(math.log(max(1, coins)) / math.log(cmax), 0, 1)
        k = self.k
        self.px = cfg['art_min_px'] + (cfg['art_max_px'] - cfg['art_min_px']) * k
        gmin = max(6, int(cfg.get('art_grid_min', 24)))
        gmax = max(gmin, int(cfg.get('art_grid_max', 72)))
        self.n = int(round(gmin + (gmax - gmin) * k))
        self.cell = self.px / self.n
        self.cx = clamp(W * 0.57, self.px / 2 + 14, W - self.px / 2 - 14)
        lo, hi = 190 + self.px / 2, GROUND_Y - 250 - self.px / 2
        self.cy = (lo + hi) / 2 if lo > hi else clamp(470, lo, hi)
        self.state = 'wait'; self.t = 0
        self.speed = clamp(float(cfg.get('art_speed', 1.0)), 0.1, 10)
        self.build = (1.1 + 2.2 * k) / self.speed
        self.show = cfg['art_show_time'] + 3 * k
        self.cells = []; self.lit = {}; self.shots = []; self.launched = 0
        self.snd_t = 0; self.surf = None; self.done = False
        g.av.request(user['uid'], user.get('avatar'), user['name'])

    def firing(self):
        return self.state == 'build' and self.launched < len(self.cells)

    def center(self): return self.cx, self.cy

    def _prepare(self):
        g = self.g
        base = g.av.surf.get(self.user['uid'])
        n = self.n
        small = pygame.transform.smoothscale(base, (n, n))
        cells = []
        for iy in range(n):
            for ix in range(n):
                c = small.get_at((ix, iy))
                if c.a < 150: continue
                q = lambda v: min(255, int(round(v / 40.0)) * 40 + 15)   # bảng màu 8-bit
                cells.append((ix, iy, (q(c.r), q(c.g), q(c.b))))
        random.shuffle(cells)
        self.canvas = pygame.Surface((int(self.px) + 2, int(self.px) + 2), pygame.SRCALPHA)
        cells.sort(key=lambda c: -(c[1] + random.uniform(-2.5, 2.5)))  # vẽ từ dưới lên
        self.cells = cells
        name = V.clean_name(self.user['name'])
        g.say('hero', random.choice(V.DONATE_THANKS).format(name=name, n=self.coins), 4, 12)
        g.banner(f"{self.user['name']} tặng {self.coins} xu!", (255, 222, 90))
        g.a.play('beam', 0.5)

    def _render(self):
        s = pygame.Surface((int(self.px) + 2, int(self.px) + 2), pygame.SRCALPHA)
        for ix, iy, col in self.cells:
            self._cell(s, ix, iy, col, 0, 0)
        self.surf = s

    def _cell(self, s, ix, iy, col, ox, oy, grow=0):
        c = self.cell
        x = ox + ix * c - grow; y = oy + iy * c - grow
        sz = math.ceil(c) + grow * 2
        pygame.draw.rect(s, col, (int(x), int(y), sz, sz))
        if c >= 8:
            dk = (col[0] * 3 // 4, col[1] * 3 // 4, col[2] * 3 // 4)
            pygame.draw.rect(s, dk, (int(x), int(y), sz, sz), 1)

    def recent(self):
        """các ô vừa sáng (< 0.12s) để vẽ hiệu ứng loé"""
        t = self.t
        old = [k for k, t0 in self.lit.items() if t - t0 >= 0.12]
        for k in old: del self.lit[k]
        return list(self.lit.items())

    def cell_pos(self, ix, iy):
        x0 = self.cx - self.px / 2; y0 = self.cy - self.px / 2
        return x0 + (ix + 0.5) * self.cell, y0 + (iy + 0.5) * self.cell

    def update(self, dt):
        g = self.g
        self.t += dt
        if self.state == 'wait':
            if self.user['uid'] not in g.av.pending or self.t > 3:
                self._prepare(); self.state = 'build'; self.t = 0
            return
        if self.state == 'build':
            total = len(self.cells)
            want = total if self.build <= 0 else int(total * clamp(self.t / self.build, 0, 1))
            sx, sy = g.hero.muzzle('up')
            while self.launched < want:
                ix, iy, col = self.cells[self.launched]
                tx, ty = self.cell_pos(ix, iy)
                dur = clamp(math.hypot(tx - sx, ty - sy) / (1500 * max(0.5, self.speed)), 0.08, 0.6)
                self.shots.append([sx, sy, tx, ty, self.t, dur, col, self.launched])
                self.launched += 1
            keep = []
            for sh in self.shots:
                if self.t - sh[4] >= sh[5]:
                    self.lit[sh[7]] = self.t
                    ix, iy, col = self.cells[sh[7]]
                    self._cell(self.canvas, ix, iy, col, 0, 0)
                    if random.random() < 0.06: g.fx.sparkle(sh[2], sh[3], [sh[6], (255, 255, 255)], 2, 6)
                else:
                    keep.append(sh)
            self.shots = keep
            self.snd_t -= dt
            if self.shots and self.snd_t <= 0:
                self.snd_t = 0.07; g.a.play('shoot', 0.15)
            if self.launched >= total and not self.shots:
                self.surf = self.canvas
                self.state = 'show'; self.t = 0
                g.cam.shake = 4 + 6 * self.k
                g.a.play('revive', 0.7)
                g.flash = 0.12 + 0.1 * self.k
                for _ in range(int(4 + 8 * self.k)):
                    g.fx.sparkle(self.cx + random.uniform(-self.px / 2, self.px / 2),
                                 self.cy + random.uniform(-self.px / 2, self.px / 2),
                                 [(255, 255, 255), (255, 230, 120)], 3, 12)
            return
        if self.state == 'show':
            show = self.show * (0.5 if len(g.art_q) >= 2 else 1.0)
            if random.random() < dt * 4:
                g.fx.sparkle(self.cx + random.uniform(-self.px / 2, self.px / 2),
                             self.cy + random.uniform(-self.px / 2, self.px / 2), [(255, 255, 255)], 1, 4)
            if self.t >= show:
                self.state = 'fade'; self.t = 0
                step = max(1, len(self.cells) // 320)
                for ix, iy, col in self.cells[::step]:
                    x, y = self.cell_pos(ix, iy)
                    g.fx.burst(x, y, [col], 1, 120, 1.0, max(4, int(self.cell * 1.6)), 520)
                g.a.play('explode', 0.35)
            return
        if self.state == 'fade':
            if self.t > 0.5: self.done = True

    def draw(self, s):
        g = self.g
        if self.state == 'wait': return
        x0 = self.cx - self.px / 2; y0 = self.cy - self.px / 2
        if self.state in ('show', 'fade'):
            a = 255 if self.state == 'show' else int(255 * clamp(1 - self.t / 0.5, 0, 1))
            if self.state == 'show':
                halo = pygame.Surface((int(self.px) + 60, int(self.px) + 60), pygame.SRCALPHA)
                r = halo.get_width() // 2
                al = int(40 + 25 * math.sin(self.t * 4))
                pygame.draw.circle(halo, (255, 230, 140, al), (r, r), r)
                s.blit(halo, (x0 - 30, y0 - 30))
            img = self.surf
            if a < 255: img = img.copy(); img.set_alpha(a)
            bob = math.sin(self.t * 2) * 4 if self.state == 'show' else 0
            s.blit(img, (x0, y0 + bob))
        else:
            s.blit(self.canvas, (x0, y0))
            for idx, t0 in self.recent():
                ix, iy, col = self.cells[idx]
                age = self.t - t0
                self._cell(s, ix, iy, (255, 255, 255) if age < 0.06 else col, x0, y0, 1 if self.cell < 8 else 2)
            for sx, sy, tx, ty, st, dur, col, idx in self.shots:
                u = clamp((self.t - st) / dur, 0, 1)
                x = sx + (tx - sx) * u; y = sy + (ty - sy) * u
                dx, dy = tx - sx, ty - sy; d = math.hypot(dx, dy) or 1
                tail = 16
                pygame.draw.line(s, col, (x - dx / d * tail, y - dy / d * tail), (x, y), 4)
                pygame.draw.line(s, (255, 255, 255), (x - dx / d * 6, y - dy / d * 6), (x, y), 2)
        # tên + số xu
        if self.state != 'fade' or self.t < 0.3:
            size = int(30 + 18 * self.k)
            ny = y0 + self.px + 10
            tr = g.text.draw(s, self.user['name'], (self.cx, ny), size, (255, 255, 255), anchor='midtop', maxw=W - 40)
            ct = g.text.render(f'{self.coins} xu', size - 6, (255, 222, 90))
            wtot = g.coin_img.get_width() + 8 + ct.get_width()
            xx = self.cx - wtot / 2; yy = tr.bottom + 2
            s.blit(g.coin_img, (xx, yy + (ct.get_height() - g.coin_img.get_height()) / 2))
            s.blit(ct, (xx + g.coin_img.get_width() + 8, yy))


class BuffShow:
    DUR = 2.2

    def __init__(self, g, user, btype):
        self.g = g; self.user = user; self.b = btype
        self.t = 0
        self.sx, self.sy = HERO_X + 120, GROUND_Y - 330
        self.x, self.y = self.sx, self.sy
        self.k = 0
        self.done = False
        self.cam = g.cam.request(lambda: (self.x, self.y + 60), g.cfg['zoom_scale'], g.cfg['zoom_like_time'])
        g.a.play('buff')
        g.say('hero', random.choice(V.HERO_BUFF[btype]).format(name=V.clean_name(user['name'])), 3, 10)

    def update(self, dt):
        g = self.g
        self.t += dt
        t = self.t
        if t < 0.35:
            self.k = ease_out_back(t / 0.35)
        elif t < 1.45:
            self.k = 1; self.y = self.sy + math.sin(t * 4) * 6
            if random.random() < dt * 14:
                g.fx.sparkle(self.x, self.y, [BUFF_COL[self.b], (255, 255, 255)], 2, 80)
        elif t < 2.05:
            u = (t - 1.45) / 0.6
            u2 = u * u
            hx, hy = g.hero.chest()
            self.x = self.sx + (hx - self.sx) * u2
            self.y = self.sy + (hy - self.sy) * u2
            self.k = 1 - 0.85 * u
            if random.random() < 0.7:
                g.fx.sparkle(self.x, self.y, [BUFF_COL[self.b], (255, 255, 255)], 2, 20)
        else:
            g.apply_buff(self.b, self.user)
            self.done = True

    def draw(self, s):
        g = self.g
        meta = g.a.meta['buffs'][self.b]['big']
        k = max(0.05, self.k)
        img = g.a.get(meta['img'], round(k, 2))
        hx, hy, hr = [v * round(k, 2) for v in meta['hole']]
        r = img.get_rect(center=(self.x, self.y))
        av = g.av.get(self.user['uid'], hr * 2 + 8)
        if av is not None:
            s.blit(av, av.get_rect(center=(r.x + hx, r.y + hy)))
        s.blit(img, r)
        if self.t < 1.45 and k > 0.5:
            g.text.draw(s, self.user['name'], (self.x, r.bottom + 4), 30, (255, 255, 255), anchor='midtop', maxw=300)
            g.text.draw(s, BUFF_TXT[self.b], (self.x, r.top - 4), 34, BUFF_COL[self.b], anchor='midbottom')


# =====================================================================
class Game:
    def __init__(self):
        self.logs = []
        self.ipc = None
        self.cfg = C.load()
        set_dpi_aware()
        os.environ.setdefault('SDL_VIDEO_CENTERED', '1')
        if self.cfg.get('window_x', -1) >= 0:
            os.environ['SDL_VIDEO_WINDOW_POS'] = f"{self.cfg['window_x']},{self.cfg['window_y']}"
        pygame.mixer.pre_init(44100, -16, 2, 1024)
        pygame.init()
        try:
            pygame.mixer.init(44100, -16, 2, 1024)
        except Exception:
            pass
        self.window = None
        self.open_window(self.cfg['window_size'])
        pygame.display.set_caption('Hero Run Live — 9:16')
        self.a = Assets()
        self.a.sfx_vol = self.cfg['sfx_volume']
        self.av = Avatars(self.a)
        self.text = Text(self.a)
        self.fx = FX(self.text)
        self.cam = Camera()
        self.world = pygame.Surface((W, H)).convert()
        self.screen = pygame.Surface((W, H)).convert()
        self.inbox = queue.Queue()
        self.ipc = Server(self.inbox)
        self.tt = TikTokThread(self.inbox, self.log)
        self.voice = V.Voice(self)
        self.clock = pygame.time.Clock()
        self.heart_img = pixel_heart(32)
        self.heart_small = pixel_heart(22)
        self.coin_img = pixel_coin(30)
        self.coin_big = pixel_coin(46)
        self.bg = self.a.get('background')
        self.bg_flip = pygame.transform.flip(self.bg, True, False)
        self.land = self.a.get('land')
        self.grass_y = self.a.meta['land_grass_y']
        self.reset()
        self.music = Music(self)
        self.vcam = VirtualCam(self)
        if self.cfg.get('auto_connect') and self.cfg.get('username'):
            self.tt.connect(self.cfg['username'], self.cfg.get('sign_api_key', ''))
        self.status_t = 0
        self.fps_v = 0
        self.prewarm_voice()
        self.say('narrator', V.GUIDE_LINES[0], 2, 30)

    @staticmethod
    def parse_size(s):
        try:
            w, h = [int(v) for v in str(s).lower().split('x')]
            return w, h
        except Exception:
            return W, H

    def log(self, msg):
        line = time.strftime('%H:%M:%S ') + str(msg)
        self.logs.append(line)
        try:
            if self.ipc: self.ipc.send({'type': 'log', 'msg': line})
        except Exception:
            pass

    # ------------------------------------------------------------
    def reset(self):
        self.hero = Hero(self)
        self.bullets = []; self.traps = []
        self.art_q = []; self.art_cur = None
        self.guests = {}; self.guest_leaving = []; self.guest_wait = []; self.guest_seen = set()
        self.guest_spawn_cd = 0
        self.buff_q = []; self.buff_cur = None
        self.likes = {}; self.likes_given = {}
        self.like_t = {}; self.like_names = {}; self.top_disp = {}; self.top_nudged = {}
        self.stats = {'popped': 0, 'likes': 0, 'coins': 0, 'gifts': 0}
        self.dist = 0.0; self.scroll_x = 0.0; self.scroll = 0.0
        self.trap_timer = 3.0
        self.banners = []; self.hearts = []
        self.flash = 0; self.revive_fx = 0
        self.cycle_i = 0
        self.guide_t = 30; self.guide_i = 0
        self.mids = []; self.clouds = []
        x = -50
        while x < W + 400:
            x = self.add_mid(x)
        for _ in range(6):
            self.clouds.append(self.new_cloud(random.uniform(-100, W)))

    def add_mid(self, x):
        name = random.choice(self.a.meta['mids'])
        img = self.a.get(name)
        self.mids.append([name, x])
        return x + img.get_width() + random.uniform(-30, 120)

    def new_cloud(self, x):
        name = random.choice(self.a.meta['clouds'])
        sc = random.uniform(0.55, 1.25)
        return [name, x, random.uniform(170, 560), sc, random.uniform(0.6, 1.4)]

    def banner(self, text, col=(255, 255, 255)):
        self.banners.append([text, col, 2.6])
        if len(self.banners) > 4: self.banners = self.banners[-4:]
        self.log(text)

    # ------------------------------------------------------------
    def say(self, role, text, prio=1, ttl=10, key=None, cooldown=0):
        self.voice.say(role, text, prio, ttl, key, cooldown)

    def chatter(self, lines, chance=0.35):
        if self.cfg.get('tts_hero_chatter') and random.random() < chance:
            self.say('hero', random.choice(lines), 1, 2.5, 'chat', 6)

    def guide_lines(self):
        c = self.cfg
        return [l.format(likes=c['likes_per_buff'], life=c['guest_life']) for l in V.GUIDE_LINES]

    def prewarm_voice(self):
        if not self.cfg.get('tts_enabled'): return
        fixed = [('narrator', l) for l in self.guide_lines()]
        if self.cfg.get('obstacles_enabled'):
            for lst in (V.HERO_JUMP, V.HERO_SLIDE, V.HERO_HURT):
                fixed += [('hero', l) for l in lst]
        for role, l in fixed:
            self.voice.say(role, l, -1, 1e9, gen_only=True)

    # ------------------------------------------------------------
    def user_from(self, ev):
        return {'uid': ev.get('uid') or ev.get('name') or 'anon', 'name': ev.get('name') or 'Ẩn danh',
                'avatar': ev.get('avatar')}

    def ensure_guest(self, u, reason='join'):
        """xếp người xem vào hàng chờ thành pet (spawn dần trong update)"""
        self.av.request(u['uid'], u.get('avatar'), u['name'])
        uid = u['uid']
        gst = self.guests.get(uid)
        if gst:
            gst.touch(); return gst
        # đã từng xuất hiện rồi thì chỉ quay lại khi VÀO PHÒNG lại (tránh hiện/mất liên tục vì tim, bình luận)
        if reason != 'join' and uid in self.guest_seen: return None
        if any(w[0]['uid'] == uid for w in self.guest_wait): return None
        self.guest_wait.append((u, time.time()))
        if len(self.guest_wait) > 20: self.guest_wait.pop(0)
        return None

    def retire_guest(self, gst):
        gst.leave()
        self.guests.pop(gst.uid, None)
        self.guest_leaving.append(gst)

    def pop_guest(self, gst):
        """pet bị bắn tan"""
        gst.pop()
        if self.guests.get(gst.uid) is gst:
            self.guests.pop(gst.uid, None)
            self.guest_leaving.append(gst)
            self.stats['popped'] += 1
            if random.random() < 0.5:
                self.say('hero', random.choice(V.PET_POP).format(name=V.clean_name(gst.name)), 0, 3, 'pop', 9)

    def pet_target(self):
        """pet hết giờ đã bay ra trước mặt Hero"""
        ready = [x for x in self.guests.values() if x.ready()]
        return min(ready, key=lambda x: x.born) if ready else None

    def live_guests(self):
        return [x for x in self.guests.values() if not x.doomed]

    def update_guests(self, dt):
        cfg = self.cfg
        now = time.time()
        for gst in list(self.guests.values()):
            if not gst.doomed and now - gst.born > cfg['guest_life']: gst.doom()
        # người mới: con xuất hiện lâu nhất bị bắn (khi đã hiện đủ guest_min_show giây)
        self.guest_wait = [w for w in self.guest_wait if now - w[1] < 30]
        self.guest_spawn_cd -= dt
        if self.guest_wait and self.guest_spawn_cd <= 0:
            ok = True
            live = self.live_guests()
            if len(live) >= max(1, cfg['guest_max']):
                old = min(live, key=lambda x: x.born)
                if now - old.born >= cfg.get('guest_min_show', 8): old.doom()
                else: ok = False
            if ok:
                u, _ = self.guest_wait.pop(0)
                if u['uid'] not in self.guests:
                    gst = Guest(self, u, random.choice(self.a.meta['guests']))
                    self.guests[u['uid']] = gst
                    self.guest_seen.add(u['uid'])
                    self.a.play('join', 0.5)
                    if cfg.get('tts_greet'):
                        self.say('narrator', random.choice(V.GREET).format(name=V.clean_name(u['name'])), 0, 8, 'greet', 7)
                    self.guest_spawn_cd = 0.3
        for gst in list(self.guests.values()) + self.guest_leaving:
            gst.update(dt)
        self.guest_leaving = [x for x in self.guest_leaving if x.state != 'gone']

    def handle_tt(self, ev):
        t = ev.get('type')
        u = self.user_from(ev)
        cfg = self.cfg
        if t == 'join':
            if cfg['guest_on_join']: self.ensure_guest(u, 'join')
        elif t in ('comment', 'follow', 'share'):
            if cfg['guest_on_comment'] or t != 'comment': self.ensure_guest(u, t)
            if t == 'follow': self.banner(f"{u['name']} đã follow!", (180, 230, 255))
        elif t == 'like':
            n = max(1, int(ev.get('count', 1)))
            if cfg['guest_on_like']: self.ensure_guest(u, 'like')
            else: self.av.request(u['uid'], u.get('avatar'), u['name'])
            self.stats['likes'] += n
            if cfg['show_hearts']:
                for _ in range(min(n, 4)):
                    self.hearts.append([random.uniform(W - 150, W - 40), H - 230, random.uniform(-160, -110),
                                        random.uniform(0, 6), 1.6, random.choice([self.heart_img, self.heart_small])])
            self.likes[u['uid']] = self.likes.get(u['uid'], 0) + n
            self.like_t[u['uid']] = time.time(); self.like_names[u['uid']] = u['name']
            self.nudge_top(u)
            th = max(1, cfg['likes_per_buff'])
            given = self.likes_given.get(u['uid'], 0)
            while self.likes[u['uid']] // th > given:
                given += 1
                if len(self.buff_q) < 30: self.buff_q.append((u, self.pick_buff()))
            self.likes_given[u['uid']] = given
        elif t == 'gift':
            self.av.request(u['uid'], u.get('avatar'), u['name'])
            g = self.guests.get(u['uid'])
            if g: g.touch()
            unit = int(ev.get('unit', 1)); cnt = max(1, int(ev.get('count', 1)))
            tot = max(1, unit * cnt)
            self.stats['coins'] += tot; self.stats['gifts'] += 1
            self.a.play('coin')
            if self.art_q and self.art_q[-1][0]['uid'] == u['uid']:
                self.art_q[-1][1] += tot                     # gộp quà liên tiếp của cùng người
            elif len(self.art_q) < cfg.get('art_queue_max', 20):
                self.art_q.append([u, tot])

    def pick_buff(self):
        types = ['damage', 'heal', 'armor']
        if self.cfg.get('buff_mode') == 'cycle':
            self.cycle_i += 1; return types[self.cycle_i % 3]
        return random.choice(types)

    def apply_buff(self, b, user):
        """100 tim: Hero được tiếp sức (hào quang + tia laser đổi màu)"""
        h = self.hero
        h.power_t = self.cfg.get('power_time', 8); h.power_kind = b; h.power_uid = user['uid']
        cx, cy = h.chest()
        self.fx.float_text(BUFF_TXT[b], cx, cy - 90, BUFF_COL[b], 40)
        self.a.play({'damage': 'buff', 'heal': 'heal', 'armor': 'armor'}[b])
        self.fx.sparkle(cx, cy, [BUFF_COL[b], (255, 255, 255)], 24, 70)

    # ------------------------------------------------------------
    def handle_panel(self, msg):
        cmd = msg.get('cmd')
        if cmd == 'config':
            old = self.cfg
            self.cfg = dict(old); self.cfg.update(msg.get('data', {}))
            self.a.sfx_vol = self.cfg['sfx_volume']
            ns = self.parse_size(self.cfg['window_size'])
            if self.cfg['window_size'] != old.get('window_size'):
                self.open_window(self.cfg['window_size'])
            self.log('Đã áp dụng cài đặt')
        elif cmd == 'connect':
            self.cfg['username'] = msg.get('username', self.cfg['username'])
            self.tt.connect(self.cfg['username'], msg.get('sign_api_key', self.cfg.get('sign_api_key', '')))
        elif cmd == 'disconnect':
            self.tt.disconnect()
        elif cmd == 'test':
            self.test(msg.get('kind'), msg.get('value', 1))
        elif cmd == 'reset':
            self.reset(); self.log('Đã chơi lại từ đầu')
        elif cmd == 'music_next':
            self.music.next()
        elif cmd == 'music_prev':
            self.music.prev()
        elif cmd == 'music_pause':
            self.music.toggle_pause()
        elif cmd == 'music_volume':
            self.cfg['music_volume'] = clamp(float(msg.get('value', 0.35)), 0, 1)
        elif cmd == 'music_reload':
            self.music.refresh(force=True)
        elif cmd == 'clear_guests':
            for gst in list(self.guests.values()): self.retire_guest(gst)
            self.guest_wait.clear()
        elif cmd == 'quit':
            self.running = False

    def fake_user(self):
        n = random.choice(FAKE_NAMES)
        return {'uid': 'test_' + n, 'name': n, 'avatar': None}

    def test(self, kind, value=1):
        u = self.fake_user()
        if kind == 'guest':
            u['uid'] += str(random.randint(0, 9999)); self.handle_tt(dict(type='join', **u))
        elif kind == 'like':
            self.handle_tt(dict(type='like', count=int(value), **u))
        elif kind == 'buff':
            self.buff_q.append((u, value if value in BUFF_COL else self.pick_buff()))
        elif kind == 'gift':
            self.handle_tt(dict(type='gift', unit=int(value), count=1, gift='Test', **u))
        elif kind == 'trap':
            self.spawn_trap(force=True)
        elif kind == 'expire':
            live = self.live_guests()
            if live: min(live, key=lambda x: x.born).doom()
        elif kind == 'voice':
            samples = {'narrator': self.guide_lines()[0],
                       'hero': V.DONATE_THANKS[0].format(name=V.clean_name(u['name']), n=10)}
            self.say(value if value in samples else 'narrator', samples.get(value, samples['narrator']), 5, 30)

    # ------------------------------------------------------------
    def spawn_trap(self, force=False):
        if self.traps and self.traps[-1].x > W - 160 and not force: return
        td = random.choice(self.a.meta['traps'])
        self.traps.append(Trap(self, td, W + 60))

    def update(self, dt):
        cfg = self.cfg
        h = self.hero
        # tốc độ cuộn
        target = cfg['scroll_speed']
        self.scroll += (target - self.scroll) * min(1, dt * 3)
        sc = self.scroll
        self.scroll_x += sc * dt
        self.dist += sc * dt / 40
        # nền
        for m in self.mids: m[1] -= sc * 0.55 * dt
        self.mids = [m for m in self.mids if m[1] + self.a.get(m[0]).get_width() > -50]
        last = self.mids[-1]
        end = last[1] + self.a.get(last[0]).get_width()
        if end < W + 300: self.add_mid(end + random.uniform(-30, 120))
        for c in self.clouds: c[1] -= (sc * 0.12 + 10) * c[4] * dt
        self.clouds = [c for c in self.clouds if c[1] > -400]
        while len(self.clouds) < 6: self.clouds.append(self.new_cloud(W + random.uniform(20, 300)))
        # chướng ngại (tuỳ chọn)
        if cfg.get('obstacles_enabled') and self.art_cur is None:
            self.trap_timer -= dt
            if self.trap_timer <= 0:
                self.spawn_trap()
                self.trap_timer = cfg['obstacle_interval'] * random.uniform(0.75, 1.3)
        # AI né chướng ngại
        self.trap_ai()
        h.update(dt)
        for t in self.traps: t.update(dt, sc)
        self.traps = [t for t in self.traps if t.x > -t.w]
        for b in self.bullets:
            b.update(dt)
            tg = b.target
            if tg is not None and self.guests.get(tg.uid) is tg and tg.state != 'out':
                cx, cy = tg.center()
                if math.hypot(b.x - cx, b.y - cy) < 34 * tg.sc + 12:
                    b.dead = True
                    self.pop_guest(tg)
        self.bullets = [b for b in self.bullets if not b.dead]
        # khách
        now = time.time()
        self.update_guests(dt)
        # buff tim
        if self.buff_cur is None and self.buff_q:
            u, b = self.buff_q.pop(0)
            self.buff_cur = BuffShow(self, u, b)
        if self.buff_cur:
            self.buff_cur.update(dt)
            if self.buff_cur.done: self.buff_cur = None
        # avatar donate trên trời
        if self.art_cur is None and self.art_q:
            u, coins = self.art_q.pop(0)
            self.art_cur = SkyArt(self, u, coins)
        if self.art_cur:
            self.art_cur.update(dt)
            if self.art_cur.done: self.art_cur = None
        self.fx.update(dt, sc)
        self.cam.update(dt)
        for b in self.banners: b[2] -= dt
        self.banners = [b for b in self.banners if b[2] > 0]
        for ht in self.hearts:
            ht[1] += ht[2] * dt; ht[3] += dt; ht[4] -= dt
        self.hearts = [x for x in self.hearts if x[4] > 0][-50:]
        self.flash = max(0, self.flash - dt)
        self.revive_fx = max(0, self.revive_fx - dt)
        iv = cfg.get('tts_guide_interval', 45)
        if iv:
            self.guide_t -= dt
            if self.guide_t <= 0:
                self.guide_t = iv
                gl = self.guide_lines()
                self.guide_i = (self.guide_i + 1) % len(gl)
                self.say('narrator', gl[self.guide_i], 1, 20)

    def trap_ai(self):
        h = self.hero; cfg = self.cfg
        for t in self.traps:
            rel = self.scroll + t.vx
            d = t.x - h.x
            if not t.triggered and d > 0:
                dur_est = clamp((t.w + 80) / max(60, rel) + 0.3, 0.75, 1.5)
                if d <= rel * dur_est * 0.5 + 6:
                    t.triggered = True
                    if random.random() * 100 < cfg['dodge_fail_pct']:
                        t.fail = True
                    elif not h.busy():
                        if t.action == 'jump': h.start_jump(t.w, rel)
                        else: h.start_slide(t.w, rel)
            if not t.resolved and d <= 0:
                t.resolved = True
                safe = (t.action == 'jump' and h.airborne()) or (t.action == 'slide' and h.low())
                if not safe:
                    h.stumble()

    # ------------------------------------------------------------
    def draw_world(self, s):
        # trời / nền xa
        bw = self.bg.get_width()
        off = (self.scroll_x * 0.05) % (bw * 2)
        x = -off
        i = 0
        while x < W:
            s.blit(self.bg if i % 2 == 0 else self.bg_flip, (x, 0))
            x += bw; i += 1
        for name, cx, cy, scl, sp in self.clouds:
            s.blit(self.a.get(name, round(scl, 2)), (cx, cy))
        # cảnh trung
        for name, mx in self.mids:
            img = self.a.get(name)
            s.blit(img, (mx, GROUND_Y + 16 - img.get_height()))
        # đất
        lw = self.land.get_width()
        ly = GROUND_Y - self.grass_y
        x = -(self.scroll_x % lw)
        while x < W:
            s.blit(self.land, (x, ly)); x += lw
        lb = ly + self.land.get_height()
        if lb < H: s.fill((46, 38, 57), (0, lb, W, H - lb))
        # khách bay + chạy
        gl = list(self.guests.values()) + self.guest_leaving
        for gst in gl:
            if gst.fly: gst.draw(s)
        for gst in gl:
            if not gst.fly: gst.draw(s)
        for t in self.traps: t.draw(s)
        if self.art_cur: self.art_cur.draw(s)
        self.hero.draw(s)
        for b in self.bullets: b.draw(s)
        self.fx.draw(s)
        if self.buff_cur: self.buff_cur.draw(s)

    # ------------------------------------------------------------
    def panel_box(self, s, rect, alpha=170):
        r = pygame.Rect(rect)
        box = pygame.Surface(r.size, pygame.SRCALPHA)
        box.fill((18, 14, 32, alpha))
        s.blit(box, r)
        pygame.draw.rect(s, (255, 214, 120), r, 3)
        pygame.draw.rect(s, (90, 60, 30), r.inflate(-6, -6), 2)

    def draw_hud(self, s):
        cfg = self.cfg; h = self.hero
        if cfg['show_hud']:
            self.panel_box(s, (8, 8, W - 16, 104))
            self.text.draw(s, cfg['title'], (24, 12), 40, (255, 222, 90), anchor='topleft')
            st = self.stats
            x = 24; y = 78
            r = self.text.draw(s, f"{int(self.dist)} m", (x, y), 30, (200, 230, 255), anchor='midleft', ow=2); x = r.right + 22
            pet = self.a.get('pet_slime_angel', 0.24); s.blit(pet, pet.get_rect(midleft=(x, y))); x += pet.get_width() + 4
            r = self.text.draw(s, f"{len(self.live_guests())}/{cfg['guest_max']}", (x, y), 30, (255, 255, 255), anchor='midleft', ow=2); x = r.right + 22
            s.blit(self.heart_small, self.heart_small.get_rect(midleft=(x, y))); x += self.heart_small.get_width() + 6
            r = self.text.draw(s, f"{st['likes']}", (x, y), 30, (255, 170, 190), anchor='midleft', ow=2); x = r.right + 22
            s.blit(self.coin_img, self.coin_img.get_rect(midleft=(x, y))); x += self.coin_img.get_width() + 6
            self.text.draw(s, f"{st['coins']}", (x, y), 30, (255, 222, 90), anchor='midleft', ow=2)
            # đang được tiếp sức
            if h.power_t > 0:
                b = h.power_kind
                m = self.a.meta['buffs'][b]['small'][3]
                img = self.a.get(m['img'], 0.78)
                r = img.get_rect(center=(W - 60, 52))
                if h.power_uid and m['hole']:
                    hx, hy, hr = [v * 0.78 for v in m['hole']]
                    av = self.av.get(h.power_uid, hr * 2 + 4)
                    if av: s.blit(av, av.get_rect(center=(r.x + hx, r.y + hy)))
                s.blit(img, r)
                self.text.draw(s, f"{int(h.power_t + 0.99)}s", (W - 60, 98), 22, BUFF_COL[b], ow=2)
            elif self.art_q:
                self.text.draw(s, f"Chờ vẽ: {len(self.art_q)}", (W - 24, 30), 24, (255, 222, 90), anchor='midright', ow=2)
        # banner
        y = 140
        for text, col, life in self.banners[-3:]:
            k = min(1, life / 0.4)
            r = self.text.render(text, 34, col)
            if k < 1: r = r.copy(); r.set_alpha(int(255 * k))
            bg = pygame.Surface((r.get_width() + 30, r.get_height() + 6), pygame.SRCALPHA)
            bg.fill((0, 0, 0, int(120 * k)))
            s.blit(bg, bg.get_rect(center=(W // 2, y)))
            s.blit(r, r.get_rect(center=(W // 2, y)))
            y += 46
        # tim bay
        for x, yy, vy, ph, life, img in self.hearts:
            im = img
            if life < 0.5: im = img.copy(); im.set_alpha(int(255 * life / 0.5))
            s.blit(im, (x + math.sin(ph * 4) * 14, yy))
        big_art = self.art_cur is not None and self.art_cur.state != 'wait' and self.art_cur.px > 280
        if cfg.get('show_top3', True) and not big_art: self.draw_top3(s)
        if cfg['show_guide']: self.draw_guide(s)
        if cfg.get('show_subtitle', True): self.draw_subtitle(s)
        if self.flash > 0:
            f = pygame.Surface((W, H), pygame.SRCALPHA); f.fill((255, 255, 255, int(200 * self.flash / 0.25)))
            s.blit(f, (0, 0))

    # ---------------- TOP 3 sắp đủ tim ----------------
    def top3(self):
        th = max(1, self.cfg['likes_per_buff'])
        now = time.time(); win = self.cfg.get('top3_window', 300)
        rows = []
        for uid, n in self.likes.items():
            p = n % th
            if p <= 0 or now - self.like_t.get(uid, 0) > win: continue
            rows.append((p, self.like_t.get(uid, 0), uid))
        rows.sort(key=lambda r: (-r[0], -r[1]))
        return [(uid, p) for p, _, uid in rows[:3]]

    def nudge_top(self, u):
        """người dẫn nhắc khi ai đó đã qua 80% mà chưa đủ"""
        if not self.cfg.get('tts_top_nudge', True): return
        th = max(1, self.cfg['likes_per_buff'])
        uid = u['uid']; p = self.likes[uid] % th
        cyc = self.likes[uid] // th
        if p >= th * 0.8 and self.top_nudged.get(uid) != cyc:
            self.top_nudged[uid] = cyc
            self.say('narrator', f"{V.clean_name(u['name'])} chỉ còn {th - p} tim nữa là tiếp sức cho Hero rồi!", 1, 6, 'nudge', 15)

    def draw_top3(self, s):
        top = self.top3()
        th = max(1, self.cfg['likes_per_buff'])
        x0, y0, w = W - 288, 262, 280
        h = 44 + max(1, len(top)) * 58
        self.panel_box(s, (x0, y0, w, h), 165)
        s.blit(self.heart_small, (x0 + 12, y0 + 10))
        self.text.draw(s, f'SẮP ĐỦ {th} TIM', (x0 + 46, y0 + 22), 28, (255, 140, 170), anchor='midleft', ow=2)
        if not top:
            k = 0.6 + 0.4 * abs(math.sin(time.time() * 2.5))
            col = (255, int(160 + 60 * k), int(190 + 40 * k))
            self.text.draw(s, 'Thả tim để lên bảng!', (x0 + w / 2, y0 + 70), 26, col, ow=2)
        medal = [(255, 214, 70), (210, 220, 235), (230, 150, 80)]
        for i, (uid, p) in enumerate(top):
            cy = y0 + 64 + i * 58
            d = self.top_disp.get(uid, p)
            d += (p - d) * 0.15
            self.top_disp[uid] = d
            pygame.draw.circle(s, medal[i], (x0 + 22, cy), 14)
            pygame.draw.circle(s, (40, 25, 10), (x0 + 22, cy), 14, 2)
            self.text.draw(s, str(i + 1), (x0 + 22, cy), 24, (40, 25, 10), ow=0)
            av = self.av.get(uid, 42)
            if av:
                s.blit(av, av.get_rect(center=(x0 + 64, cy)))
                pygame.draw.circle(s, medal[i], (x0 + 64, cy), 22, 2)
            name = self.like_names.get(uid, '?')
            self.text.draw(s, name, (x0 + 94, cy - 12), 24, (255, 255, 255), anchor='midleft', ow=2, maxw=176)
            bx, by, bw = x0 + 94, cy + 6, 170
            pygame.draw.rect(s, (20, 10, 20), (bx - 2, by - 2, bw + 4, 16))
            pygame.draw.rect(s, (90, 30, 50), (bx, by, bw, 12))
            k = clamp(d / th, 0, 1)
            col = (255, 90, 130) if k < 0.8 else ((255, 220, 90) if int(time.time() * 6) % 2 else (255, 130, 160))
            pygame.draw.rect(s, col, (bx, by, bw * k, 12))
            pygame.draw.rect(s, (255, 200, 215), (bx, by, bw * k, 3))
            self.text.draw(s, f'{p}/{th}', (bx + bw / 2, by + 6), 18, (255, 255, 255), ow=2)
        if len(self.top_disp) > 200:
            keep = {u for u, _ in top}
            self.top_disp = {u: v for u, v in self.top_disp.items() if u in keep}

    def draw_subtitle(self, s):
        sub = self.voice.subtitle()
        if not sub: return
        role, text = sub
        col = {'narrator': (255, 236, 150), 'hero': (170, 240, 255), 'robot': (255, 170, 90), 'knight': (255, 220, 90)}[role]
        tag = {'narrator': '', 'hero': 'HERO: ', 'robot': 'ROBOT: ', 'knight': 'HIỆP SĨ: '}[role]
        # chia dòng
        f = self.a.font(30)
        words = (tag + text).split(); lines = []; cur = ''
        for w in words:
            t = (cur + ' ' + w).strip()
            if f.size(t)[0] > W - 70 and cur: lines.append(cur); cur = w
            else: cur = t
        if cur: lines.append(cur)
        lines = lines[-3:]
        y = (1100 if self.cfg['show_guide'] else H - 20) - len(lines) * 32 - 10
        box = pygame.Surface((W - 30, len(lines) * 32 + 14), pygame.SRCALPHA); box.fill((0, 0, 0, 150))
        s.blit(box, (15, y))
        for i, l in enumerate(lines):
            self.text.draw(s, l, (W // 2, y + 8 + i * 32), 30, col, anchor='midtop', ow=2)

    def draw_guide(self, s):
        cfg = self.cfg
        y0 = 1112
        self.panel_box(s, (8, y0, W - 16, 160), 185)
        items = [
            ('guest', 'Vào xem', 'thành PET dễ thương'),
            ('heart', f"{cfg['likes_per_buff']} tim", 'TIẾP SỨC cho Hero'),
            ('coin', 'Tặng quà', 'bắn AVATAR lên trời'),
            ('big', 'Càng nhiều xu', 'avatar càng TO'),
        ]
        for i, (ic, a, b) in enumerate(items):
            cx = 24 + (i % 2) * 346; cy = y0 + 14 + (i // 2) * 72
            if ic == 'guest':
                img = self.a.get('pet_slime_angel', 0.38)
            elif ic == 'heart':
                img = self.heart_img
            elif ic == 'coin':
                img = self.coin_big
            else:
                img = self.sample_icon()
            s.blit(img, img.get_rect(center=(cx + 32, cy + 30)))
            self.text.draw(s, a, (cx + 74, cy + 16), 32, (255, 222, 90), anchor='midleft', ow=2)
            self.text.draw(s, b, (cx + 74, cy + 44), 28, (255, 255, 255), anchor='midleft', ow=2)

    def sample_icon(self):
        """icon avatar 8-bit nhỏ -> to cho bảng hướng dẫn"""
        if getattr(self, '_sample_icon', None) is None:
            s = pygame.Surface((62, 58), pygame.SRCALPHA)
            face = ["..XXXX..", ".XXXXXX.", "XX.XX.XX", "XXXXXXXX", "XX.XX.XX", "XXX..XXX", ".XXXXXX.", "..XXXX.."]
            for k, (cell, ox, oy) in enumerate([(3, 0, 34), (4, 22, 26), (5, 6, 0)]):
                col = [(120, 200, 255), (255, 170, 90), (255, 222, 90)][k]
                for yy, row in enumerate(face):
                    for xx, ch in enumerate(row):
                        if ch == 'X':
                            pygame.draw.rect(s, col, (ox + xx * cell, oy + yy * cell, cell, cell))
            self._sample_icon = s
        return self._sample_icon

    # ------------------------------------------------------------
    def send_status(self):
        self.ipc.send({'type': 'status', 'tiktok': self.tt.status, 'fps': round(self.fps_v),
                       'guests': len(self.live_guests()), 'popped': self.stats['popped'], 'dist': int(self.dist),
                       'likes': self.stats['likes'], 'coins': self.stats['coins'], 'gifts': self.stats['gifts'],
                       'buff_q': len(self.buff_q), 'art_q': len(self.art_q) + (1 if self.art_cur else 0),
                       'voice': self.voice.state, 'music': self.music.status(), 'window': '%dx%d' % tuple(self.win_size), 'vcam': self.vcam.state, 'version': C.version()})

    def keys(self, e):
        k = e.key
        if k == pygame.K_g: self.test('guest')
        elif k == pygame.K_h: self.test('like', self.cfg['likes_per_buff'])
        elif k == pygame.K_j: self.test('like', random.randint(10, 35))
        elif k == pygame.K_n: self.music.next()
        elif k == pygame.K_1: self.test('gift', 1)
        elif k == pygame.K_2: self.test('gift', 10)
        elif k == pygame.K_3: self.test('gift', 100)
        elif k == pygame.K_4: self.test('gift', 1000)
        elif k == pygame.K_e: self.test('expire')
        elif k == pygame.K_t: self.test('trap')
        elif k == pygame.K_F5: self.reset()

    def frame(self, dt):
        self.av.pump()
        while True:
            try:
                src, msg = self.inbox.get_nowait()
            except queue.Empty:
                break
            try:
                if src == 'tt': self.handle_tt(msg)
                else: self.handle_panel(msg)
            except Exception as ex:
                self.log(f'Lỗi xử lý sự kiện: {ex}')
        self.update(dt)
        self.music.update(self.cfg['music_volume'])
        self.voice.pump(self.cfg['music_volume'])
        self.draw_world(self.world)
        self.cam.apply(self.world, self.screen)
        self.draw_hud(self.screen)
        self.vcam.update(self.screen)

    def open_window(self, size_str):
        """mở cửa sổ 9:16 vừa màn hình (không vượt quá vùng làm việc -> tránh lỗi capture)"""
        want = (W, H) if str(size_str) == 'fit' else self.parse_size(size_str)
        try:
            dw, dh = pygame.display.get_desktop_sizes()[0]
        except Exception:
            dw, dh = 1920, 1080
        max_h = dh - 90          # chừa thanh tiêu đề + taskbar
        max_w = dw - 20
        w, h = want
        if str(size_str) == 'fit' or h > max_h or w > max_w:
            k = min(max_h / H, max_w / W)
            if str(size_str) != 'fit' and (h > max_h or w > max_w):
                self.log(f'Màn hình {dw}x{dh} nhỏ hơn {w}x{h} → cửa sổ chỉ thu về vừa màn hình. '
                         f'Muốn xuất đúng {w}x{h}: bật "Camera ảo" ở tab Hiển thị.')
            h = int(H * k) // 2 * 2; w = int(h * 9 / 16) // 2 * 2
        self.win_size = (w, h)
        self.window = pygame.display.set_mode(self.win_size, pygame.RESIZABLE)
        self.log(f'Cửa sổ game {w}x{h}')

    def present(self):
        win = pygame.display.get_surface()
        ww, wh = win.get_size()
        if (ww, wh) == (W, H):
            win.blit(self.screen, (0, 0))
        else:
            k = min(ww / W, wh / H)
            sw, sh = max(1, int(W * k)), max(1, int(H * k))
            ox, oy = (ww - sw) // 2, (wh - sh) // 2
            if (ox or oy): win.fill((0, 0, 0))
            if (sw, sh) == (W, H):
                win.blit(self.screen, (ox, oy))
            else:
                win.blit(pygame.transform.smoothscale(self.screen, (sw, sh)), (ox, oy))
        pygame.display.flip()

    def run(self):
        self.running = True
        self.log(f'Hero Run Live v{C.version()} đã chạy')
        while self.running:
            dt = min(0.05, self.clock.tick(self.cfg['fps']) / 1000)
            self.fps_v = self.clock.get_fps()
            for e in pygame.event.get():
                if e.type == pygame.QUIT: self.running = False
                elif e.type == pygame.VIDEORESIZE: self.win_size = (e.w, e.h)
                elif e.type == pygame.KEYDOWN: self.keys(e)
            self.frame(dt)
            self.present()
            self.status_t -= dt
            if self.status_t <= 0:
                self.status_t = 1.0
                self.send_status()
        self.tt.disconnect()
        self.vcam.stop()
        pygame.quit()


def main():
    Game().run()


if __name__ == '__main__':
    main()
