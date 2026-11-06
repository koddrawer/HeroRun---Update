# Lồng tiếng bằng VieNeu-TTS (chạy trên máy, CPU/ONNX) — sinh trong luồng nền, cache ra đĩa
import os, re, time, hashlib, threading, queue, random
import pygame
from .config import ROOT

CACHE = os.path.join(ROOT, 'voice_cache')

# giọng sẵn có của VieNeu (v3 Turbo + v3 Nano)
TURBO_VOICES = ['Hải Đăng', 'Trúc Ly', 'Thiện Minh', 'Mai Anh', 'Thùy Dung', 'Thiền Tâm Đức', 'Ngọc Huyền', 'Quang Sơn',
                'Ngọc Trân', 'Minh Đức', 'Phạm Tuyên', 'Thái Sơn', 'Xuân Vĩnh', 'Thanh Bình', 'Ngọc Linh', 'Đoan Trang',
                'Thục Đoan', 'Minh Triết', 'Mỹ Duyên', 'Quỳnh Anh', 'Đức Trí', 'Kim Thanh', 'Adam', 'Adam bựa', 'Quốc Tuấn']
NANO_VOICES = ['Minh Quân', 'Adam', 'Ái Hân', 'Mỹ Duyên', 'Đức Trí', 'Hữu Quân', 'Xuân Tiên', 'Mai Anh', 'Trúc Ly',
               'Anh Khôi', 'Mạnh Dũng']

ROLES = ('narrator', 'hero', 'robot', 'knight')


def clean_name(name):
    """tên người xem -> đọc được (bỏ emoji/ký hiệu, cắt ngắn)"""
    s = re.sub(r'[^\w\sÀ-ỹ]', ' ', str(name or ''), flags=re.UNICODE)
    s = re.sub(r'_+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    if not s or not re.search(r'[A-Za-zÀ-ỹ]', s):
        return 'bạn'
    return s[:24]


class Voice:
    def __init__(self, game):
        self.g = game
        self.items = []                 # (prio, t, role, text, ttl, gen_only, key)
        self.lock = threading.Lock()
        self.ready = queue.Queue()      # (role, text, path, hạn chót)
        self.engine = None
        self.state = 'tắt'
        self.cool = {}
        self.ev = threading.Event()
        self.chan = None
        self.playing = None             # (role, text, until)
        self.loaded_key = None
        os.makedirs(CACHE, exist_ok=True)
        threading.Thread(target=self._worker, daemon=True).start()

    @property
    def cfg(self): return self.g.cfg

    # ---------------- API cho game ----------------
    def say(self, role, text, prio=1, ttl=12.0, key=None, cooldown=0.0, gen_only=False):
        if not self.cfg.get('tts_enabled'): return
        now = time.time()
        if key:
            if now < self.cool.get(key, 0): return
            self.cool[key] = now + cooldown
        with self.lock:
            self.items.append((prio, now, role, text, ttl, gen_only))
            if len(self.items) > 14:     # bỏ câu ưu tiên thấp / cũ nhất
                self.items.sort(key=lambda x: (x[0], x[1]))
                self.items.pop(0)
        self.ev.set()

    def pump(self, music_vol):
        """gọi mỗi frame ở luồng chính: phát câu đã sinh xong, hạ nhạc khi đang nói"""
        if not pygame.mixer.get_init(): return
        if self.chan is None:
            try:
                pygame.mixer.set_num_channels(16)
                self.chan = pygame.mixer.Channel(15)
            except Exception:
                return
        busy = self.chan.get_busy()
        if not busy:
            self.playing = None
            try:
                role, text, path, dl = self.ready.get_nowait()
                if time.time() > dl: role = None      # quá hạn thì bỏ
            except queue.Empty:
                role = None
            if role:
                try:
                    snd = pygame.mixer.Sound(path)
                    snd.set_volume(self.cfg.get('voice_volume', 1.0))
                    self.chan.play(snd)
                    self.playing = (role, text, time.time() + snd.get_length())
                    busy = True
                except Exception as e:
                    self.g.log(f'Lỗi phát giọng: {e}')
        try:
            pygame.mixer.music.set_volume(music_vol * (0.3 if busy else 1.0))
        except Exception:
            pass

    def voice_for(self, role):
        return self.cfg.get('tts_voice_' + role) or 'Hải Đăng'

    # ---------------- luồng nền ----------------
    def _load(self):
        mode = self.cfg.get('tts_mode', 'v3turbo')
        prec = self.cfg.get('tts_precision', 'fp32')
        thr = int(self.cfg.get('tts_threads', 2))
        key = (mode, prec, thr)
        if self.engine is not None and self.loaded_key == key: return True
        self.state = 'đang tải model (lần đầu sẽ tải từ HuggingFace)...'
        self.g.log('VieNeu: ' + self.state)
        try:
            from vieneu import Vieneu
            kw = {}
            if mode == 'v3turbo':
                kw = {'precision': prec, 'threads': thr}
            self.engine = Vieneu(mode=mode, **kw)
            self.loaded_key = key
            self.voices = [v[1] for v in self.engine.list_preset_voices()]
            self.state = f'sẵn sàng ({mode})'
            self.g.log(f'VieNeu sẵn sàng — {len(self.voices)} giọng')
            return True
        except ImportError:
            self.state = 'chưa cài vieneu (pip install vieneu)'
        except Exception as e:
            self.state = f'lỗi: {str(e)[:80]}'
        self.g.log('VieNeu ' + self.state)
        self.engine = None
        return False

    def _pick(self):
        with self.lock:
            if not self.items: return None
            now = time.time()
            self.items = [x for x in self.items if x[5] or now - x[1] <= x[4]]
            if not self.items: return None
            self.items.sort(key=lambda x: (-x[0], x[1]))
            return self.items.pop(0)

    def _path(self, role, voice, text):
        mode = self.cfg.get('tts_mode', 'v3turbo')
        fx = 'robo' if (role == 'robot' and self.cfg.get('tts_robot_fx', True)) else ''
        h = hashlib.md5(f'{mode}|{voice}|{fx}|{text}'.encode('utf-8')).hexdigest()[:16]
        return os.path.join(CACHE, h + '.wav'), fx

    def _worker(self):
        fails = 0
        while True:
            self.ev.wait(1.0); self.ev.clear()
            while self.cfg.get('tts_enabled'):
                it = self._pick()
                if it is None: break
                prio, t0, role, text, ttl, gen_only = it
                voice = self.voice_for(role)
                path, fx = self._path(role, voice, text)
                if not os.path.exists(path):
                    if not self._load():
                        fails += 1
                        time.sleep(min(60, 5 * fails))
                        break
                    try:
                        v = voice if voice in self.voices else None
                        audio = self.engine.infer(text, voice=v) if v else self.engine.infer(text)
                        if fx: audio = self._robot(audio, self.engine.sample_rate)
                        import soundfile as sf
                        tmp = path + '.tmp.wav'
                        sf.write(tmp, audio, self.engine.sample_rate, subtype='PCM_16')
                        os.replace(tmp, path)
                    except Exception as e:
                        self.g.log(f'VieNeu lỗi câu "{text[:30]}": {e}')
                        continue
                if gen_only: continue
                if time.time() - t0 > ttl: continue
                self.ready.put((role, text, path, t0 + ttl + 4))

    @staticmethod
    def _robot(a, sr):
        import numpy as np
        a = np.asarray(a, dtype=np.float32).reshape(-1)
        t = np.arange(len(a)) / sr
        ring = a * np.sin(2 * np.pi * 55 * t)
        out = 0.55 * a + 0.6 * ring
        out = np.round(out * 48) / 48            # hơi "bitcrush"
        m = np.max(np.abs(out)) or 1
        return (out / m * 0.9).astype(np.float32)

    def subtitle(self):
        if self.playing and time.time() < self.playing[2]:
            return self.playing[0], self.playing[1]
        return None


# ---------------- kịch bản lời thoại ----------------
GUIDE_LINES = [
    'Chào mừng các bạn đến với Hero Run Live! Vào xem là bạn sẽ biến thành quái khách bay lượn quanh màn hình.',
    'Thả đủ {likes} tim, avatar của bạn sẽ bay vào người Hero để tăng sát thương, hồi máu hoặc thêm giáp!',
    'Tặng {robot} xu để gọi Robot đáp xuống, bắn chưởng quét sạch quái vật!',
    'Tặng {knight} xu để triệu hồi Hiệp sĩ hoàng kim, một nhát kiếm hạ gục tất cả!',
    'Hero sắp mệt rồi, cả nhà thả tim tiếp sức cho Hero nhé!',
]
HERO_JUMP = ['Hây! Nhảy qua nào!', 'Bật cao lên!', 'Hụp! Qua rồi!']
HERO_SLIDE = ['Cúi xuống! Trượt qua!', 'Trượt nào!', 'Suýt nữa thì trúng!']
HERO_HURT = ['Ui da! Đau quá!', 'Á! Trúng rồi!']
HERO_DIE = ['Á... mình sẽ quay lại ngay!', 'Gục mất rồi... đợi mình chút!']
HERO_REVIVE = ['Hồi sinh rồi! Chạy tiếp thôi!', 'Mình trở lại rồi đây!']
HERO_LOW = ['Sắp hết máu rồi, thả tim cứu mình với!', 'Máu yếu quá, cả nhà tiếp sức cho mình nhé!']
HERO_BUFF = {
    'damage': ['Cảm ơn {name}! Sức mạnh tăng vọt rồi!', 'Cảm ơn {name}! Súng mạnh hơn rồi!'],
    'heal': ['Cảm ơn {name}! Mình hồi máu rồi!', 'Cảm ơn {name}, khỏe lại rồi!'],
    'armor': ['Cảm ơn {name}! Có giáp rồi, không sợ nữa!', 'Giáp của {name} chắc quá!'],
}
ROBOT_IN = ['Robot của {name} xuất kích!', '{name} đã gọi Robot! Đang hạ cánh!']
ROBOT_ATK = ['Chưởng năng lượng! Bắn!', 'Quét sạch mục tiêu!']
ROBOT_OUT = ['Nhiệm vụ hoàn thành. Tạm biệt!']
KNIGHT_IN = ['Hiệp sĩ của {name} đã tới!', 'Ta là hiệp sĩ của {name}, đến bảo vệ ngươi!']
KNIGHT_ATK = ['Xem kiếm đây!', 'Kiếm quang trảm!']
GREET = ['Chào {name}! Bạn đã thành quái khách rồi đó!', 'Chào mừng {name} đến chơi!']
KILLS = ['Hạ gục {n} quái rồi!']
