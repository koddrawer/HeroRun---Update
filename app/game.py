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
        cfg = self.g.cfg
        self.x = HERO_X; self.y = GROUND_Y
        self.state = 'run'; self.t = 0; self.act_t = 0; self.dur = 0.8
        self.jump_h = 110; self.yoff = 0
        self.hp = cfg['hero_max_hp']; self.shield = 0
        self.dmg_lv = 0; self.dmg_time = 0
        self.invuln = 0; self.hurt = 0
        self.shoot_cd = 0; self.target = None
        self.vx = self.vy = self.rot = 0
        self.dead_t = 0
        self.last_buff = {'damage': None, 'heal': None, 'armor': None}

    @property
    def frames(self): return self.g.a.meta['hero']['frames']

    def busy(self): return self.state in ('jump', 'slide', 'dead', 'respawn')

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

    def damage_mult(self):
        return 1 + self.dmg_lv * self.g.cfg['buff_damage_pct'] / 100.0

    def take(self, dmg, kind='hit'):
        if self.invuln > 0 or self.state in ('dead', 'respawn'): return
        dmg = int(round(dmg))
        if self.shield > 0:
            ab = min(self.shield, dmg); self.shield -= ab; dmg -= ab
            if ab: self.g.fx.float_text(f'-{ab}', self.x + 30, self.y - 150, (120, 200, 255), 30)
        if dmg > 0:
            self.hp -= dmg
            self.g.fx.float_text(f'-{dmg}', self.x, self.y - 150, (255, 90, 90), 38)
        self.hurt = 0.35; self.invuln = 0.45
        self.g.cam.shake = max(self.g.cam.shake, 6)
        self.g.a.play('hurt', 0.8)
        self.g.fx.burst(self.x, self.y - 70, [(255, 80, 80), (255, 200, 200)], 10, 200, 0.4, 5)
        if self.hp <= 0:
            self.die()
        else:
            g = self.g
            if self.hp < g.cfg['hero_max_hp'] * 0.3:
                g.say('hero', random.choice(V.HERO_LOW), 2, 6, 'low', 35)
            else:
                g.chatter(V.HERO_HURT, 0.5)

    def die(self):
        self.hp = 0
        self.state = 'dead'; self.dead_t = 0
        self.vx, self.vy, self.rot = -90, -650, 0
        self.g.stats['deaths'] += 1
        self.g.a.play('die')
        self.g.banner('HERO GỤC NGÃ!', (255, 110, 110))
        self.g.say('hero', random.choice(V.HERO_DIE), 3, 4)
        self.g.cam.shake = 12

    def respawn(self):
        g = self.g
        self.state = 'respawn'; self.x = -90; self.y = GROUND_Y; self.yoff = 0; self.rot = 0
        self.hp = g.cfg['hero_max_hp']; self.invuln = 3.5
        for m in g.monsters:
            if m.state == 'alive': m.knock(g, kill=False)
        g.mproj.clear()
        g.traps = [t for t in g.traps if t.x > HERO_X + 420]
        g.a.play('revive')
        g.banner('HỒI SINH! CHẠY TIẾP NÀO!', (140, 255, 160))
        g.say('hero', random.choice(V.HERO_REVIVE), 3, 5)
        g.revive_fx = 1.4

    def update(self, dt):
        g = self.g
        self.t += dt
        self.invuln = max(0, self.invuln - dt); self.hurt = max(0, self.hurt - dt)
        if self.dmg_lv:
            self.dmg_time -= dt
            if self.dmg_time <= 0: self.dmg_lv = 0
        self.yoff = 0
        if self.state == 'dead':
            self.dead_t += dt
            self.vy += 1600 * dt
            self.x += self.vx * dt; self.y += self.vy * dt; self.rot += 420 * dt
            if self.y > GROUND_Y + 40: self.y = GROUND_Y + 40; self.vy = 0; self.vx = 0
            if self.dead_t > g.cfg['respawn_time']:
                self.respawn()
            return
        if self.state == 'respawn':
            self.x += 300 * dt
            if int(self.t * 20) % 3 == 0: g.fx.dust(self.x - 20, GROUND_Y)
            if self.x >= HERO_X:
                self.x = HERO_X; self.state = 'run'
            return
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
        # ngắm bắn
        self.shoot_cd -= dt
        self.target = None
        if self.state == 'run':
            best = None
            for m in g.monsters:
                if m.state != 'alive' or m.x > W - 10 or m.x < self.x + 40: continue
                d = m.x - self.x
                if d < 640 and (best is None or d < best[0]): best = (d, m)
            if best:
                self.target = best[1]
                if self.shoot_cd <= 0:
                    self.shoot_cd = g.cfg['fire_interval']
                    self.fire(self.target)

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
        if self.state == 'dead':
            return fr['jump'][3]
        row = 'run'
        if self.target is not None:
            row = 'shoot45' if self.target.fly else 'shoot'
        i = int(self.t * 13) % 8
        if row != 'run' and i < 2: i += 2   # luôn khung đang bắn
        return fr[row][i]

    def fire(self, m):
        g = self.g
        fly = m.fly
        key = 'muzzle_shoot45' if fly else 'muzzle_shoot'
        mx, my = g.a.meta['hero'][key]
        sx, sy = self.x + mx, self.y + my
        tx, ty = m.center()
        dx, dy = tx - sx, ty - sy
        if not fly and dx > 0:
            dy = clamp(dy, -0.25 * dx, 0.25 * dx)
        d = math.hypot(dx, dy) or 1
        spd = 950
        dmg = g.cfg['hero_damage'] * self.damage_mult()
        g.bullets.append(Bullet(sx, sy, dx / d * spd, dy / d * spd, dmg, self.dmg_lv))
        g.a.play('shoot', 0.35)

    def draw(self, s):
        g = self.g
        if self.invuln > 0 and self.state != 'respawn' and int(self.invuln * 20) % 2 == 0 and self.state != 'dead':
            return
        f = self.anim_frame()
        img = g.a.get(f['img'])
        x, y = self.x - f['ax'], self.y + self.yoff - f['ay']
        if self.state == 'dead':
            r = pygame.transform.rotate(img, self.rot)
            s.blit(r, r.get_rect(center=(self.x, self.y - 70)))
            return
        if self.hurt > 0:
            img = img.copy(); img.fill((255, 80, 80, 0), special_flags=pygame.BLEND_RGBA_ADD)
        elif self.dmg_lv > 0 and int(self.t * 8) % 2 == 0:
            img = img.copy(); img.fill((70, 20, 0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        # bóng
        sh = pygame.Surface((70, 12), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 70), sh.get_rect())
        s.blit(sh, (self.x - 35, GROUND_Y - 6))
        s.blit(img, (x, y))
        if self.shield > 0:
            k = self.shield / max(1, g.cfg['armor_max'])
            rad = 78
            surf = pygame.Surface((rad * 2 + 8, rad * 2 + 8), pygame.SRCALPHA)
            a = int(50 + 60 * k + 20 * math.sin(self.t * 6))
            pygame.draw.circle(surf, (110, 190, 255, a // 3), (rad + 4, rad + 4), rad)
            pygame.draw.circle(surf, (170, 225, 255, a + 40), (rad + 4, rad + 4), rad, 3)
            s.blit(surf, (self.x - rad - 4, self.y + self.yoff - 70 - rad - 4))


# =====================================================================
class Bullet:
    def __init__(self, x, y, vx, vy, dmg, lv):
        self.x, self.y, self.vx, self.vy, self.dmg, self.lv = x, y, vx, vy, dmg, lv
        self.dead = False

    def update(self, dt):
        self.x += self.vx * dt; self.y += self.vy * dt
        if self.x > W + 40 or self.y < 0 or self.y > H: self.dead = True

    def draw(self, s):
        d = math.hypot(self.vx, self.vy) or 1
        ux, uy = self.vx / d, self.vy / d
        L = 34 + self.lv * 6
        x0, y0 = self.x - ux * L, self.y - uy * L
        if self.lv:
            pygame.draw.line(s, (255, 140, 40), (x0, y0), (self.x, self.y), 12)
        pygame.draw.line(s, (40, 200, 255), (x0, y0), (self.x, self.y), 8)
        pygame.draw.line(s, (230, 255, 255), (x0 + ux * 8, y0 + uy * 8), (self.x, self.y), 3)


# =====================================================================
class Monster:
    def __init__(self, g, mdef, x, level):
        self.g = g; self.d = mdef
        self.fly = mdef['fly']
        self.img = g.a.get(mdef['img'], 1.0, flip=True)
        self.w, self.h = self.img.get_size()
        self.x = x
        self.base_y = GROUND_Y - random.randint(230, 330) if self.fly else GROUND_Y + 4
        self.y = self.base_y
        cfg = g.cfg
        self.maxhp = cfg['monster_hp'] * (1 + (level - 1) * cfg['difficulty_per_level'] / 100) * (0.8 if self.fly else 1)
        self.hp = self.maxhp
        self.speed = random.uniform(70, 120)
        self.hold_x = random.uniform(420, 610)
        self.hold_t = 0
        self.fire_cd = random.uniform(0.6, 1.6)
        self.state = 'alive'
        self.t = random.uniform(0, 6)
        self.flash = 0
        self.vx = self.vy = self.rot = 0
        self.touched = False

    def rect(self):
        if self.fly:
            return pygame.Rect(self.x - self.w * 0.38, self.y - self.h * 0.4, self.w * 0.76, self.h * 0.8)
        return pygame.Rect(self.x - self.w * 0.4, self.y - self.h * 0.92, self.w * 0.8, self.h * 0.9)

    def center(self):
        return self.rect().center

    def knock(self, g, kill=True):
        self.state = 'knock'
        self.vx = random.uniform(500, 900); self.vy = random.uniform(-950, -650)
        self.rot = 0
        g.fx.burst(self.x, self.center()[1], [(255, 255, 255), (255, 220, 80), (255, 120, 40)], 14, 320, 0.5, 6)
        if kill:
            g.stats['kills'] += 1
            g.kill_milestone()

    def update(self, dt):
        g = self.g
        self.t += dt; self.flash = max(0, self.flash - dt)
        if self.state == 'knock':
            self.vy += 1500 * dt
            self.x += self.vx * dt; self.y += self.vy * dt; self.rot += 900 * dt
            if self.y > H + 200 or self.x > W + 300: self.state = 'gone'
            return
        if self.state == 'die':
            self.state = 'gone'; return
        # di chuyển
        if self.x > self.hold_x:
            self.x -= self.speed * 1.6 * dt
        else:
            self.hold_t += dt
            if self.hold_t > 6.5:      # lâu quá thì lao vào
                self.hold_x = -200; self.speed = 260
            self.x += math.sin(self.t * 1.7) * 14 * dt
        if self.fly:
            self.y = self.base_y + math.sin(self.t * 3.2) * 18
        else:
            self.y = self.base_y - abs(math.sin(self.t * 9)) * 8
        # bắn
        if self.x < W - 30 and g.hero.state not in ('dead', 'respawn'):
            self.fire_cd -= dt
            if self.fire_cd <= 0:
                self.fire_cd = g.cfg['monster_fire_interval'] * random.uniform(0.75, 1.3)
                g.mproj.append(MonProj(g, self))
        # va chạm thân
        if not self.touched and self.rect().colliderect(g.hero.hitbox()) and g.hero.state not in ('dead', 'respawn'):
            self.touched = True
            g.hero.take(g.cfg['monster_damage'] * 1.6)
            self.explode()
        if self.x < -150: self.state = 'gone'

    def hit(self, dmg):
        self.hp -= dmg; self.flash = 0.1
        if self.hp <= 0:
            self.g.stats['kills'] += 1
            self.g.kill_milestone()
            self.explode()

    def explode(self):
        g = self.g
        cx, cy = self.center()
        g.fx.burst(cx, cy, [(255, 240, 120), (255, 150, 40), (255, 80, 40), (255, 255, 255)], 22, 360, 0.6, 7)
        g.a.play('explode', 0.6)
        self.state = 'die'

    def draw(self, s):
        if self.state == 'knock':
            r = pygame.transform.rotate(self.img, self.rot)
            s.blit(r, r.get_rect(center=(self.x, self.y - self.h / 2)))
            return
        img = self.img
        if self.flash > 0:
            img = img.copy(); img.fill((180, 180, 180, 0), special_flags=pygame.BLEND_RGBA_ADD)
        if self.fly:
            s.blit(img, img.get_rect(center=(self.x, self.y)))
        else:
            sh = pygame.Surface((int(self.w * 0.8), 10), pygame.SRCALPHA)
            pygame.draw.ellipse(sh, (0, 0, 0, 60), sh.get_rect()); s.blit(sh, (self.x - self.w * 0.4, GROUND_Y - 4))
            s.blit(img, img.get_rect(midbottom=(self.x, self.y)))
        # thanh máu
        if self.hp < self.maxhp:
            r = self.rect()
            bw = 56; x = self.x - bw / 2; y = r.top - 14
            pygame.draw.rect(s, (20, 10, 20), (x - 2, y - 2, bw + 4, 9))
            pygame.draw.rect(s, (230, 60, 60), (x, y, bw * max(0, self.hp) / self.maxhp, 5))


class MonProj:
    def __init__(self, g, m):
        self.g = g
        names = m.d['proj']
        self.travel = [g.a.get(n, 0.9, True) for n in (names[:-1] if len(names) > 1 else names)]
        self.impact = g.a.get(names[-1], 1.0, True)
        cx, cy = m.center()
        self.x, self.y = cx - m.w * 0.35, cy
        tx, ty = g.hero.chest()
        tx += random.uniform(-10, 10)
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy) or 1
        spd = 330
        self.vx, self.vy = dx / d * spd, dy / d * spd
        self.t = 0; self.state = 'fly'; self.it = 0

    def update(self, dt):
        g = self.g
        self.t += dt
        if self.state == 'fly':
            self.x += self.vx * dt; self.y += self.vy * dt
            if g.hero.hitbox().collidepoint(self.x, self.y) and g.hero.state not in ('dead', 'respawn'):
                g.hero.take(g.cfg['monster_damage'])
                self.state = 'impact'; self.it = 0.25
            elif self.x < -60 or self.y > H or self.y < 0:
                self.state = 'gone'
        elif self.state == 'impact':
            self.it -= dt
            self.x -= g.scroll * dt
            if self.it <= 0: self.state = 'gone'

    def draw(self, s):
        if self.state == 'fly':
            img = self.travel[int(self.t * 8) % len(self.travel)]
        else:
            img = self.impact
        s.blit(img, img.get_rect(center=(self.x, self.y)))


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
        self.x = random.uniform(70, W - 70)
        self.y = random.uniform(260, 640) if self.fly else GROUND_Y + 6
        self.tx, self.ty = self.x, self.y
        self.t = random.uniform(0, 6)
        self.active = self.born = time.time()
        self.state = 'in'; self.st = 0
        self.dir = random.choice([-1, 1])
        self.speed = random.uniform(40, 75)

    def touch(self): self.active = time.time()

    def update(self, dt):
        self.t += dt; self.st += dt
        if self.state == 'in' and self.st > 0.45: self.state = 'live'
        if self.state == 'out':
            if self.st > 0.45: self.state = 'gone'
            return
        if self.fly:
            if math.hypot(self.tx - self.x, self.ty - self.y) < 8:
                self.tx = random.uniform(70, W - 70); self.ty = random.uniform(250, 650)
            dx, dy = self.tx - self.x, self.ty - self.y
            d = math.hypot(dx, dy) or 1
            self.x += dx / d * self.speed * dt; self.y += dy / d * self.speed * dt
            if abs(dx) > 2: self.dir = 1 if dx > 0 else -1
        else:
            self.x += self.dir * self.speed * dt
            if self.x < 60: self.dir = 1
            if self.x > W - 60: self.dir = -1
            if random.random() < dt * 0.15: self.dir *= -1

    def leave(self):
        if self.state != 'out':
            self.state = 'out'; self.st = 0
            self.g.fx.burst(self.x, self.draw_y(), [(255, 255, 255), (200, 200, 255)], 12, 160, 0.5, 5, 0)

    def draw_y(self):
        if self.fly: return self.y + math.sin(self.t * 2.6) * 10
        return self.y - abs(math.sin(self.t * 7)) * 12

    def draw(self, s):
        g = self.g
        k = 1.0
        if self.state == 'in': k = ease_out_back(clamp(self.st / 0.45, 0, 1))
        elif self.state == 'out': k = 1 - clamp(self.st / 0.45, 0, 1)
        if k <= 0.02: return
        cy = self.draw_y()
        img = self.img
        if not self.fly and self.dir < 0:
            img = g.a.get(self.d['img'], self.sc, True)
        hole = self.d['hole']
        if self.fly:
            pos = (self.x - self.w / 2, cy - self.h / 2)
        else:
            pos = (self.x - self.w / 2, cy - self.h)
        hx = (self.w - hole[0] * self.sc) if (not self.fly and self.dir < 0) else hole[0] * self.sc
        hy = hole[1] * self.sc; hr = hole[2] * self.sc
        if k < 0.999:
            img = pygame.transform.smoothscale_by(img, k)
            ox = (self.w - img.get_width()) / 2; oy = (self.h - img.get_height()) / 2
            pos = (pos[0] + ox, pos[1] + oy); hx = hx * k; hy = hy * k; hr *= k
        av = g.av.get(self.uid, hr * 2 + 6)
        if av is not None:
            s.blit(av, av.get_rect(center=(pos[0] + hx, pos[1] + hy)))
        s.blit(img, pos)
        if k > 0.6:
            t = g.text.render(self.name, 22, (255, 255, 255), maxw=150)
            s.blit(t, t.get_rect(midtop=(self.x, pos[1] + img.get_height() - 4)))


# =====================================================================
BUFF_COL = {'damage': (255, 120, 60), 'heal': (120, 255, 120), 'armor': (120, 190, 255)}
BUFF_TXT = {'damage': '+SÁT THƯƠNG', 'heal': '+HỒI MÁU', 'armor': '+GIÁP'}


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
class Helper:
    """Robot (1 xu) & Hiệp sĩ (5 xu)."""

    def __init__(self, g, kind, user):
        self.g = g; self.kind = kind; self.user = user
        self.meta = g.a.meta[kind]
        self.S = 1.28 if kind == 'robot' else 1.18
        self.phase = None; self.pt = 0; self.done = False
        self.alpha = 255
        self.knocked = False
        self.x = HERO_X + 190
        self.last_hole = None
        if kind == 'robot':
            f7 = self.meta['land'][7]
            self.land_y = GROUND_Y + 4 - (f7['bottom'] - f7['hole'][1]) * self.S
            self.y = -160
            self.set('descend')
            g.a.play('robot_in')
            g.banner(f"{user['name']} gọi ROBOT hỗ trợ!", (255, 170, 90))
            g.say('robot', random.choice(V.ROBOT_IN).format(name=V.clean_name(user['name'])), 4, 10)
        else:
            self.y = GROUND_Y
            self.set('appear')
            g.a.play('knight_in')
            g.banner(f"{user['name']} triệu hồi HIỆP SĨ!", (255, 220, 90))
            g.say('knight', random.choice(V.KNIGHT_IN).format(name=V.clean_name(user['name'])), 4, 10)
        self.cam = g.cam.request(self.focus, g.cfg['zoom_scale'])

    def focus(self):
        if self.kind == 'robot':
            return self.x, self.y + 30
        return self.x, GROUND_Y - 110

    def set(self, ph):
        self.phase = ph; self.pt = 0

    def frame_list(self):
        m = self.meta
        if self.kind == 'robot':
            return {'descend': m['land'][:4], 'land': m['land'][4:], 'attack': m['attack'],
                    'takeoff': m['takeoff'], 'fly': m['fly']}[self.phase]
        return {'appear': m['appear'], 'attack': m['attack'], 'vanish': m['vanish'][:6]}[self.phase]

    DURS = {'descend': 1.1, 'land': 0.5, 'attack': 1.15, 'takeoff': 0.8, 'fly': 1.0,
            'appear': 1.25, 'vanish': 0.9}

    def cur(self):
        fl = self.frame_list()
        d = self.DURS[self.phase]
        if self.phase in ('descend', 'fly'):
            i = int(self.pt * 10) % len(fl)
        else:
            i = clamp(int(self.pt / d * len(fl)), 0, len(fl) - 1)
        return i, fl[i]

    def update(self, dt):
        g = self.g
        sp = 1.25 if len(g.helper_q) > 3 else 1.0
        self.pt += dt * sp
        d = self.DURS[self.phase]
        i, f = self.cur()
        if self.kind == 'robot':
            if self.phase == 'descend':
                u = clamp(self.pt / d, 0, 1)
                self.y = -160 + (self.land_y + 30 - -160) * (1 - (1 - u) ** 2)
                if random.random() < 0.6: g.fx.sparkle(self.x, self.y + 90, [(120, 220, 255), (255, 255, 255)], 1, 18)
                if self.pt >= d: self.set('land'); g.cam.shake = 8; g.fx.dust(self.x + 40, GROUND_Y, 10)
            elif self.phase == 'land':
                u = clamp(self.pt / d, 0, 1); self.y = self.land_y + 30 * (1 - u)
                if self.pt >= d:
                    self.cam['done'] = True; self.set('attack')
                    g.say('robot', random.choice(V.ROBOT_ATK), 3, 3)
            elif self.phase == 'attack':
                if i == 5 and not self.knocked:
                    self.knocked = True; g.knock_all(self.y); g.a.play('beam'); g.flash = 0.25
                if self.pt >= d:
                    self.set('takeoff'); g.say('robot', V.ROBOT_OUT[0], 1, 3)
            elif self.phase == 'takeoff':
                if i >= 5: self.y -= 260 * dt
                if self.pt >= d: self.set('fly')
            elif self.phase == 'fly':
                self.x += 560 * dt; self.y -= 420 * dt
                if self.pt >= d or self.y < -200: self.done = True
        else:
            if self.phase == 'appear':
                if random.random() < 0.5: g.fx.sparkle(self.x, GROUND_Y - 80, [(255, 220, 90), (255, 255, 200)], 1, 60)
                if self.pt >= d:
                    self.cam['done'] = True; self.set('attack')
                    g.say('knight', random.choice(V.KNIGHT_ATK), 3, 3)
            elif self.phase == 'attack':
                if i == 6 and not self.knocked:
                    self.knocked = True; g.knock_all(GROUND_Y - 100); g.a.play('slash'); g.flash = 0.2
                if self.pt >= d: self.set('vanish'); g.a.play('fire')
            elif self.phase == 'vanish':
                if self.pt > d - 0.3: self.alpha = int(255 * clamp((d - self.pt) / 0.3, 0, 1))
                if self.pt >= d: self.done = True
        if self.done: self.cam['done'] = True

    def draw(self, s):
        g = self.g
        i, f = self.cur()
        img = g.a.get(f['img'], self.S)
        hole = f['hole'] or self.last_hole
        if f['hole']: self.last_hole = f['hole']
        S = self.S
        if self.kind == 'robot':
            if not hole: hole = self.meta['land'][7]['hole']
            px, py = self.x - hole[0] * S, self.y - hole[1] * S
        else:
            cxh = hole[0] if hole else img.get_width() / 2 / S
            px, py = self.x - cxh * S, GROUND_Y + 8 - f['bottom'] * S
        if hole and not (self.kind == 'knight' and self.phase == 'appear' and i < 1):
            av = g.av.get(self.user['uid'], hole[2] * S * 2 + 8)
            if av is not None:
                if self.alpha < 255: av = av.copy(); av.set_alpha(self.alpha)
                s.blit(av, av.get_rect(center=(px + hole[0] * S, py + hole[1] * S)))
        if self.alpha < 255:
            img = img.copy(); img.set_alpha(self.alpha)
        s.blit(img, (px, py))
        if self.phase not in ('descend', 'fly') and self.alpha > 100:
            g.text.draw(s, self.user['name'], (self.x, GROUND_Y + 14), 28, (255, 236, 150), anchor='midtop', maxw=260)


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
        self.monsters = []; self.mproj = []; self.bullets = []; self.traps = []
        self.guests = {}; self.guest_leaving = []; self.guest_wait = []; self.guest_seen = set()
        self.guest_spawn_cd = 0
        self.buff_q = []; self.buff_cur = None
        self.helper_q = []; self.helper_cur = None
        self.likes = {}; self.likes_given = {}
        self.like_t = {}; self.like_names = {}; self.top_disp = {}; self.top_nudged = {}
        self.stats = {'kills': 0, 'deaths': 0, 'likes': 0, 'coins': 0}
        self.dist = 0.0; self.scroll_x = 0.0; self.scroll = 0.0
        self.mon_timer = 2.0; self.trap_timer = 3.0
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

    @property
    def level(self):
        return 1 + int(self.dist // max(50, self.cfg['meters_per_level']))

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

    def kill_milestone(self):
        k = self.stats['kills']
        if k and k % 25 == 0:
            self.say('hero', V.KILLS[0].format(n=k), 1, 4)

    def guide_lines(self):
        c = self.cfg
        return [l.format(likes=c['likes_per_buff'], robot=c['robot_coin'], knight=c['knight_coin']) for l in V.GUIDE_LINES]

    def prewarm_voice(self):
        if not self.cfg.get('tts_enabled'): return
        fixed = [('narrator', l) for l in self.guide_lines()]
        for lst in (V.HERO_JUMP, V.HERO_SLIDE, V.HERO_HURT, V.HERO_DIE, V.HERO_REVIVE, V.HERO_LOW):
            fixed += [('hero', l) for l in lst]
        fixed += [('robot', l) for l in V.ROBOT_ATK + V.ROBOT_OUT] + [('knight', l) for l in V.KNIGHT_ATK]
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

    def update_guests(self, dt):
        cfg = self.cfg
        now = time.time()
        for gst in list(self.guests.values()):
            if now - gst.born > cfg['guest_life']: self.retire_guest(gst)
        # người mới: chỉ thay con cũ nhất khi con đó đã hiện đủ guest_min_show giây
        self.guest_wait = [w for w in self.guest_wait if now - w[1] < 30]
        self.guest_spawn_cd -= dt
        if self.guest_wait and self.guest_spawn_cd <= 0:
            ok = True
            if len(self.guests) >= max(1, cfg['guest_max']):
                old = min(self.guests.values(), key=lambda x: x.born)   # người xuất hiện lâu nhất
                if now - old.born >= cfg.get('guest_min_show', 8): self.retire_guest(old)
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
            self.stats['coins'] += unit * cnt
            self.a.play('coin')
            rmin, kmin = max(1, cfg['robot_coin']), max(1, cfg['knight_coin'])
            add = []
            if cfg['gift_rule'] == 'total':
                tot = unit * cnt
                add += ['knight'] * (tot // kmin)
                add += ['robot'] * ((tot % kmin) // rmin)
            else:
                if unit >= kmin: add += ['knight'] * cnt
                elif unit >= rmin: add += ['robot'] * cnt
            add = add[:cfg['helper_cap']]
            for k in add:
                if len(self.helper_q) < cfg['helper_queue_max']:
                    self.helper_q.append((k, u))

    def pick_buff(self):
        mode = self.cfg['buff_mode']
        types = ['damage', 'heal', 'armor']
        if mode == 'random': return random.choice(types)
        if mode == 'cycle':
            self.cycle_i += 1; return types[self.cycle_i % 3]
        h = self.hero
        hpk = h.hp / max(1, self.cfg['hero_max_hp'])
        w = [1.0 if h.dmg_lv < self.cfg['buff_damage_max'] else 0.3,
             2.5 if hpk < 0.5 else (1.0 if hpk < 0.9 else 0.15),
             1.0 if h.shield < self.cfg['armor_max'] * 0.6 else 0.25]
        return random.choices(types, w)[0]

    def apply_buff(self, b, user):
        h = self.hero; cfg = self.cfg
        h.last_buff[b] = user['uid']
        cx, cy = h.chest()
        if b == 'damage':
            h.dmg_lv = min(cfg['buff_damage_max'], h.dmg_lv + 1); h.dmg_time = cfg['buff_damage_time']
            self.fx.float_text(f"DAME x{h.damage_mult():.1f}", cx, cy - 90, BUFF_COL[b], 40)
        elif b == 'heal':
            h.hp = min(cfg['hero_max_hp'], h.hp + cfg['buff_heal'])
            self.fx.float_text(f"+{cfg['buff_heal']} HP", cx, cy - 90, BUFF_COL[b], 40)
            self.a.play('heal')
        else:
            h.shield = min(cfg['armor_max'], h.shield + cfg['buff_armor'])
            self.fx.float_text(f"+{cfg['buff_armor']} GIÁP", cx, cy - 90, BUFF_COL[b], 40)
            self.a.play('armor')
        self.fx.sparkle(cx, cy, [BUFF_COL[b], (255, 255, 255)], 24, 70)

    def knock_all(self, y=None):
        for m in self.monsters:
            if m.state == 'alive' and m.x < W + 60:
                m.knock(self)
        self.mproj.clear()
        self.cam.shake = 14
        self.a.play('explode', 0.8)

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
            if self.cfg['hero_max_hp'] != old.get('hero_max_hp'):
                self.hero.hp = min(self.hero.hp, self.cfg['hero_max_hp'])
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
        elif kind == 'hurt':
            self.hero.take(int(value))
        elif kind == 'kill':
            self.hero.invuln = 0; self.hero.take(9999)
        elif kind == 'trap':
            self.spawn_trap(force=True)
        elif kind == 'monster':
            self.spawn_wave(force=True)
        elif kind == 'voice':
            samples = {'narrator': self.guide_lines()[0], 'hero': V.HERO_BUFF['heal'][0].format(name=V.clean_name(u['name'])),
                       'robot': V.ROBOT_IN[0].format(name=V.clean_name(u['name'])),
                       'knight': V.KNIGHT_IN[0].format(name=V.clean_name(u['name']))}
            self.say(value if value in samples else 'narrator', samples.get(value, samples['narrator']), 5, 30)

    # ------------------------------------------------------------
    def spawn_wave(self, force=False):
        alive = [m for m in self.monsters if m.state == 'alive']
        if not force and len(alive) >= self.cfg['monster_max']: return
        n = random.randint(1, min(3, 1 + self.level // 3))
        for i in range(n):
            pool = self.a.meta['monsters']
            if random.random() < 0.28:
                md = random.choice([m for m in pool if m['fly']])
            else:
                md = random.choice([m for m in pool if not m['fly']])
            self.monsters.append(Monster(self, md, W + 70 + i * 120, self.level))

    def spawn_trap(self, force=False):
        if self.traps and self.traps[-1].x > W - 160 and not force: return
        td = random.choice(self.a.meta['traps'])
        self.traps.append(Trap(self, td, W + 60))

    def update(self, dt):
        cfg = self.cfg
        h = self.hero
        # tốc độ cuộn
        target = cfg['scroll_speed']
        if h.state == 'dead': target = 0
        elif h.state == 'respawn': target = cfg['scroll_speed'] * 0.5
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
        # sinh quái / chướng ngại
        if h.state not in ('dead', 'respawn') and self.helper_cur is None:
            self.mon_timer -= dt
            if self.mon_timer <= 0:
                self.spawn_wave()
                self.mon_timer = cfg['monster_interval'] * random.uniform(0.7, 1.3) / (1 + self.level * 0.03)
            self.trap_timer -= dt
            if self.trap_timer <= 0:
                self.spawn_trap()
                self.trap_timer = cfg['obstacle_interval'] * random.uniform(0.75, 1.3)
        # AI né chướng ngại
        self.trap_ai()
        h.update(dt)
        for t in self.traps: t.update(dt, sc)
        self.traps = [t for t in self.traps if t.x > -t.w]
        for m in self.monsters:
            m.update(dt)
            if m.state == 'alive' and not m.fly: m.x -= 0  # đi theo màn hình
        self.monsters = [m for m in self.monsters if m.state != 'gone']
        for p in self.mproj: p.update(dt)
        self.mproj = [p for p in self.mproj if p.state != 'gone']
        for b in self.bullets:
            b.update(dt)
            for m in self.monsters:
                if m.state == 'alive' and m.rect().collidepoint(b.x, b.y):
                    m.hit(b.dmg); b.dead = True
                    self.fx.burst(b.x, b.y, [(140, 230, 255), (255, 255, 255)], 6, 180, 0.25, 4)
                    self.a.play('hit', 0.35)
                    break
        self.bullets = [b for b in self.bullets if not b.dead]
        # khách
        now = time.time()
        self.update_guests(dt)
        # buff tim
        if self.buff_cur is None and self.buff_q and h.state not in ('dead',):
            u, b = self.buff_q.pop(0)
            self.buff_cur = BuffShow(self, u, b)
        if self.buff_cur:
            self.buff_cur.update(dt)
            if self.buff_cur.done: self.buff_cur = None
        # trợ thủ
        if self.helper_cur is None and self.helper_q and h.state not in ('dead',):
            k, u = self.helper_q.pop(0)
            self.helper_cur = Helper(self, k, u)
        if self.helper_cur:
            self.helper_cur.update(dt)
            if self.helper_cur.done: self.helper_cur = None
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
            if not t.triggered and d > 0 and h.state not in ('dead', 'respawn'):
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
                if h.state in ('dead', 'respawn'): continue
                safe = (t.action == 'jump' and h.airborne()) or (t.action == 'slide' and h.low())
                if not safe:
                    h.take(cfg['obstacle_damage'])
                    self.fx.float_text('ÁI DA!', h.x, h.y - 190, (255, 200, 120), 34)

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
        for m in self.monsters: m.draw(s)
        if self.revive_fx > 0:
            k = self.revive_fx / 1.4
            pil = pygame.Surface((110, GROUND_Y), pygame.SRCALPHA)
            pil.fill((255, 255, 200, int(120 * k)))
            pygame.draw.rect(pil, (255, 255, 255, int(200 * k)), (40, 0, 30, GROUND_Y))
            s.blit(pil, (HERO_X - 55, 0))
        if self.helper_cur: self.helper_cur.draw(s)
        self.hero.draw(s)
        for p in self.mproj: p.draw(s)
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
            self.panel_box(s, (8, 8, W - 16, 132))
            self.text.draw(s, cfg['title'], (24, 12), 40, (255, 222, 90), anchor='topleft')
            # máu
            x0, y0, bw = 24, 58, 430
            pygame.draw.rect(s, (10, 6, 14), (x0 - 3, y0 - 3, bw + 6, 30))
            pygame.draw.rect(s, (70, 20, 30), (x0, y0, bw, 24))
            k = clamp(h.hp / max(1, cfg['hero_max_hp']), 0, 1)
            pygame.draw.rect(s, (230, 50, 60), (x0, y0, bw * k, 24))
            pygame.draw.rect(s, (255, 140, 140), (x0, y0, bw * k, 6))
            if h.shield > 0:
                ks = clamp(h.shield / max(1, cfg['armor_max']), 0, 1)
                pygame.draw.rect(s, (90, 170, 255), (x0, y0 + 26, bw * ks, 7))
            self.text.draw(s, f"HP {max(0, int(h.hp))}/{cfg['hero_max_hp']}" + (f"  GIÁP {int(h.shield)}" if h.shield else ''),
                           (x0 + 8, y0 + 12), 26, (255, 255, 255), anchor='midleft', ow=2)
            # chỉ số
            st = self.stats
            self.text.draw(s, f"{int(self.dist)}m   DIỆT {st['kills']}   GỤC {st['deaths']}   LV {self.level}",
                           (24, 104), 28, (200, 230, 255), anchor='midleft', ow=2)
            # 3 khung buff nhỏ
            for i, b in enumerate(['damage', 'heal', 'armor']):
                if b == 'damage': lv = h.dmg_lv; sub = f"x{h.damage_mult():.1f} {int(h.dmg_time)}s" if lv else 'x1.0'
                elif b == 'heal': lv = 3 if k > 0.75 else 2 if k > 0.5 else 1 if k > 0.25 else 0; sub = f"{int(k * 100)}%"
                else: lv = min(3, int(h.shield / max(1, cfg['armor_max']) * 4)); sub = str(int(h.shield))
                lv = clamp(lv, 0, 3)
                m = self.a.meta['buffs'][b]['small'][lv]
                img = self.a.get(m['img'], 0.78)
                cx = 500 + i * 74; cy = 62
                r = img.get_rect(center=(cx, cy))
                uid = h.last_buff[b]
                if uid and m['hole']:
                    hx, hy, hr = [v * 0.78 for v in m['hole']]
                    av = self.av.get(uid, hr * 2 + 4)
                    if av: s.blit(av, av.get_rect(center=(r.x + hx, r.y + hy)))
                s.blit(img, r)
                self.text.draw(s, sub, (cx, 112), 22, BUFF_COL[b], ow=2)
        # banner
        y = 168
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
        # hàng chờ trợ thủ
        if self.helper_q:
            self.text.draw(s, f"Chờ: {len(self.helper_q)} trợ thủ", (W - 16, 156), 24, (255, 220, 140), anchor='topright', ow=2)
        if cfg.get('show_top3', True): self.draw_top3(s)
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
            self.say('narrator', f"{V.clean_name(u['name'])} chỉ còn {th - p} tim nữa là buff cho Hero rồi!", 1, 6, 'nudge', 15)

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
            ('heart', f"{cfg['likes_per_buff']} tim", 'BUFF cho Hero'),
            ('robot', f"{cfg['robot_coin']} xu", 'gọi ROBOT'),
            ('knight', f"{cfg['knight_coin']} xu", 'gọi HIỆP SĨ'),
        ]
        for i, (ic, a, b) in enumerate(items):
            cx = 24 + (i % 2) * 346; cy = y0 + 14 + (i // 2) * 72
            if ic == 'guest':
                img = self.a.get('pet_slime_angel', 0.38)
            elif ic == 'heart':
                img = self.heart_img
            elif ic == 'robot':
                img = self.a.get('robot_land_7', 0.48)
            else:
                img = self.a.get('knight_appear_7', 0.42)
            s.blit(img, img.get_rect(center=(cx + 32, cy + 30)))
            if ic in ('robot', 'knight'):
                s.blit(self.coin_img, (cx + 44, cy + 34))
            self.text.draw(s, a, (cx + 74, cy + 16), 32, (255, 222, 90), anchor='midleft', ow=2)
            self.text.draw(s, b, (cx + 74, cy + 44), 28, (255, 255, 255), anchor='midleft', ow=2)

    # ------------------------------------------------------------
    def send_status(self):
        alive = len([m for m in self.monsters if m.state == 'alive'])
        self.ipc.send({'type': 'status', 'tiktok': self.tt.status, 'fps': round(self.fps_v),
                       'guests': len(self.guests), 'monsters': alive, 'kills': self.stats['kills'],
                       'deaths': self.stats['deaths'], 'dist': int(self.dist), 'likes': self.stats['likes'],
                       'coins': self.stats['coins'], 'buff_q': len(self.buff_q), 'helper_q': len(self.helper_q),
                       'hp': int(self.hero.hp), 'voice': self.voice.state, 'music': self.music.current or '—', 'window': '%dx%d' % tuple(self.win_size), 'vcam': self.vcam.state, 'version': C.version()})

    def keys(self, e):
        k = e.key
        if k == pygame.K_g: self.test('guest')
        elif k == pygame.K_h: self.test('like', self.cfg['likes_per_buff'])
        elif k == pygame.K_j: self.test('like', random.randint(10, 35))
        elif k == pygame.K_n: self.music.next()
        elif k == pygame.K_1: self.test('buff', 'damage')
        elif k == pygame.K_2: self.test('buff', 'heal')
        elif k == pygame.K_3: self.test('buff', 'armor')
        elif k == pygame.K_r: self.test('gift', self.cfg['robot_coin'])
        elif k == pygame.K_k: self.test('gift', self.cfg['knight_coin'])
        elif k == pygame.K_x: self.test('hurt', 20)
        elif k == pygame.K_d: self.test('kill')
        elif k == pygame.K_t: self.test('trap')
        elif k == pygame.K_m: self.test('monster')
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
