# Bảng điều khiển (cửa sổ riêng) — Tkinter
import os, sys, subprocess, threading, queue, time
import tkinter as tk
from tkinter import ttk, messagebox
from . import config as C
from .ipc import Client
from . import updater

BG = '#17131f'; BG2 = '#231d30'; FG = '#f1e9ff'; ACC = '#ffd45a'; ACC2 = '#7cc6ff'

# (key, nhãn, kiểu, tham số)
SPEC = {
    'Gameplay': [
        ('scroll_speed', 'Tốc độ chạy (px/s)', 'int', (80, 500)),
        ('hero_max_hp', 'Máu tối đa Hero', 'int', (10, 1000)),
        ('hero_damage', 'Sát thương mỗi phát', 'int', (1, 500)),
        ('fire_interval', 'Giãn cách bắn (giây)', 'float', (0.05, 2)),
        ('respawn_time', 'Thời gian chờ hồi sinh (giây)', 'float', (0.5, 10)),
        ('monster_interval', 'Giãn cách đợt quái (giây)', 'float', (0.5, 20)),
        ('monster_max', 'Số quái tối đa trên màn', 'int', (1, 20)),
        ('monster_hp', 'Máu quái (cấp 1)', 'int', (1, 2000)),
        ('monster_damage', 'Sát thương quái', 'int', (0, 200)),
        ('monster_fire_interval', 'Quái bắn mỗi (giây)', 'float', (0.3, 10)),
        ('difficulty_per_level', 'Máu quái +% mỗi cấp', 'int', (0, 100)),
        ('meters_per_level', 'Số mét mỗi cấp', 'int', (50, 5000)),
        ('obstacle_interval', 'Giãn cách chướng ngại (giây)', 'float', (1, 30)),
        ('obstacle_damage', 'Sát thương chướng ngại', 'int', (0, 200)),
        ('dodge_fail_pct', '% né hụt chướng ngại', 'int', (0, 100)),
    ],
    'Tương tác': [
        ('guest_on_join', 'Vào xem → thành pet', 'bool', None),
        ('guest_on_comment', 'Bình luận → thành pet', 'bool', None),
        ('guest_on_like', 'Thả tim → thành pet', 'bool', None),
        ('guest_max', 'Pet tối đa cùng lúc', 'int', (1, 80)),
        ('guest_life', 'Mỗi pet tồn tại (giây)', 'int', (5, 3600)),
        ('guest_min_show', 'Hiện tối thiểu trước khi bị thay (giây)', 'int', (1, 120)),
        ('guest_scale', 'Cỡ pet', 'float', (0.4, 1.6)),
        ('likes_per_buff', 'Số tim để buff', 'int', (1, 10000)),
        ('buff_mode', 'Chọn loại buff', 'choice', ['auto', 'random', 'cycle']),
        ('buff_damage_pct', 'Buff dame +% mỗi cấp', 'int', (1, 500)),
        ('buff_damage_time', 'Buff dame kéo dài (giây)', 'int', (1, 600)),
        ('buff_damage_max', 'Buff dame cấp tối đa', 'int', (1, 10)),
        ('buff_heal', 'Buff hồi máu (HP)', 'int', (1, 1000)),
        ('buff_armor', 'Buff giáp (điểm)', 'int', (1, 1000)),
        ('armor_max', 'Giáp tối đa', 'int', (1, 2000)),
        ('zoom_like_time', 'Zoom khi avatar tim xuất hiện (giây)', 'float', (0, 5)),
        ('show_top3', 'Hiện bảng TOP 3 sắp đủ tim', 'bool', None),
        ('top3_window', 'TOP 3 chỉ tính người thả tim trong (giây)', 'int', (10, 3600)),
        ('tts_top_nudge', 'Người dẫn nhắc người sắp đủ tim (≥80%)', 'bool', None),
        ('robot_coin', 'Số xu gọi ROBOT', 'int', (1, 100000)),
        ('knight_coin', 'Số xu gọi HIỆP SĨ', 'int', (1, 100000)),
        ('gift_rule', 'Cách tính quà', 'choice', ['unit', 'total']),
        ('helper_cap', 'Tối đa trợ thủ / 1 lần tặng', 'int', (1, 100)),
        ('helper_queue_max', 'Hàng chờ trợ thủ tối đa', 'int', (1, 200)),
        ('zoom_scale', 'Độ zoom camera', 'float', (1, 3)),
    ],
    'Giọng nói': [
        ('tts_enabled', 'Bật lồng tiếng VieNeu-TTS', 'bool', None),
        ('tts_mode', 'Model', 'choice', ['v3turbo', 'v3nano']),
        ('tts_precision', 'Độ chính xác (v3turbo)', 'choice', ['fp32', 'int8']),
        ('tts_threads', 'Số luồng CPU cho TTS', 'int', (1, 16)),
        ('tts_voice_narrator', 'Giọng người dẫn (hướng dẫn chơi)', 'voice', None),
        ('tts_voice_hero', 'Giọng Hero', 'voice', None),
        ('tts_voice_robot', 'Giọng Robot', 'voice', None),
        ('tts_voice_knight', 'Giọng Hiệp sĩ', 'voice', None),
        ('tts_robot_fx', 'Méo tiếng kiểu robot', 'bool', None),
        ('voice_volume', 'Âm lượng giọng', 'float', (0, 1)),
        ('tts_guide_interval', 'Đọc hướng dẫn mỗi (giây, 0 = tắt)', 'int', (0, 3600)),
        ('tts_greet', 'Chào người mới vào', 'bool', None),
        ('tts_hero_chatter', 'Hero nói khi nhảy/trượt/trúng đòn', 'bool', None),
        ('show_subtitle', 'Hiện phụ đề lời thoại', 'bool', None),
    ],
    'Hiển thị': [
        ('window_size', 'Cửa sổ game (9:16)', 'choice', ['fit', '540x960', '720x1280', '1080x1920']),
        ('fps', 'FPS', 'choice', [30, 60]),
        ('vcam_enabled', 'Xuất CAMERA ẢO (đúng 1080x1920, không cần màn hình to)', 'bool', None),
        ('vcam_size', 'Độ phân giải camera ảo', 'choice', ['1080x1920', '720x1280']),
        ('vcam_fps', 'FPS camera ảo', 'choice', [30, 60]),
        ('title', 'Tiêu đề trên HUD', 'str', None),
        ('show_hud', 'Hiện HUD', 'bool', None),
        ('show_guide', 'Hiện bảng hướng dẫn', 'bool', None),
        ('show_hearts', 'Hiện tim bay', 'bool', None),
        ('music_volume', 'Âm lượng nhạc', 'float', (0, 1)),
        ('music_source', 'Nguồn nhạc nền', 'choice', ['auto', 'folder', 'builtin', 'classic', 'off']),
        ('music_folder', 'Thư mục nhạc của bạn', 'folder', None),
        ('music_shuffle', 'Phát ngẫu nhiên', 'bool', None),
        ('sfx_volume', 'Âm lượng hiệu ứng', 'float', (0, 1)),
    ],
}

from .voice import TURBO_VOICES, NANO_VOICES
VOICE_LIST = TURBO_VOICES + [v for v in NANO_VOICES if v not in TURBO_VOICES]

GUIDE = {'vcam_enabled': 'Cần cài OBS Studio (để có OBS Virtual Camera, không cần mở OBS).\nTrong LIVE Studio: thêm nguồn Camera → chọn "OBS Virtual Camera" (tắt lật gương).','window_size': 'fit = lớn nhất vừa màn hình. Cửa sổ không được cao hơn màn hình, nếu không LIVE Studio capture bị lỗi;\nmàn 1080p dùng fit hoặc 540x960. Kéo giãn cửa sổ thoải mái, game luôn giữ 9:16.','music_source': 'auto = thư mục của bạn nếu có bài, không thì 3 bài dựng sẵn; folder = chỉ thư mục của bạn;\nbuiltin = 3 bài dựng sẵn; classic = nhạc cũ của game; off = tắt',
         'music_folder': 'Bỏ file mp3/ogg/wav/flac vào đây (mặc định thư mục music\\ cạnh app)','tts_mode': 'v3turbo hay hơn; v3nano nhẹ cho máy yếu (giọng riêng: Minh Quân, Ái Hân, Hữu Quân...)',
         'tts_precision': 'int8 nhanh ~1.6x nhưng CPU phải hỗ trợ VNNI, nếu méo tiếng thì để fp32',
         'tts_threads': 'Lần đầu chạy sẽ tải model từ HuggingFace; câu đã đọc được lưu ở voice_cache\\','buff_mode': 'auto = ưu tiên thứ Hero cần; random; cycle = lần lượt',
         'gift_rule': 'unit = theo giá 1 món (5 hoa hồng = 5 robot); total = theo tổng xu'}


class Panel:
    def __init__(self, game_cmd):
        self.game_cmd = game_cmd
        self.cfg = C.load()
        self.proc = None
        self.ipc = Client()
        self.root = tk.Tk()
        self.root.title(f'Hero Run Live — Bảng điều khiển  v{C.version()}')
        self.root.geometry('500x880')
        self.root.configure(bg=BG)
        self.vars = {}
        self.style()
        self.build()
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.start_game()
        self.root.after(300, self.poll)
        if self.cfg.get('auto_update'):
            self.start_update(True)
        threading.Thread(target=self.ensure_deps, daemon=True).start()

    # ------------------------------------------------------------
    def style(self):
        s = ttk.Style(self.root)
        try: s.theme_use('clam')
        except Exception: pass
        s.configure('.', background=BG, foreground=FG, fieldbackground=BG2, font=('Segoe UI', 10))
        s.configure('TNotebook', background=BG, borderwidth=0)
        s.configure('TNotebook.Tab', background=BG2, foreground=FG, padding=(10, 5))
        s.map('TNotebook.Tab', background=[('selected', ACC)], foreground=[('selected', '#1a1206')])
        s.configure('TButton', background=BG2, foreground=FG, padding=6, borderwidth=1)
        s.map('TButton', background=[('active', '#3a2f52')])
        s.configure('Acc.TButton', background=ACC, foreground='#1a1206', font=('Segoe UI', 10, 'bold'))
        s.map('Acc.TButton', background=[('active', '#ffe48f')])
        s.configure('TLabel', background=BG, foreground=FG)
        s.configure('H.TLabel', foreground=ACC, font=('Segoe UI', 12, 'bold'))
        s.configure('S.TLabel', foreground='#b9add0', font=('Segoe UI', 9))
        s.configure('TCheckbutton', background=BG, foreground=FG)
        s.configure('TEntry', fieldbackground=BG2, foreground=FG, insertcolor=FG)
        s.configure('TCombobox', fieldbackground=BG2, foreground=FG)
        s.configure('TSpinbox', fieldbackground=BG2, foreground=FG, arrowcolor=FG)
        s.configure('TLabelframe', background=BG, foreground=ACC)
        s.configure('TLabelframe.Label', background=BG, foreground=ACC, font=('Segoe UI', 10, 'bold'))

    def build(self):
        nb = ttk.Notebook(self.root); nb.pack(fill='both', expand=True, padx=8, pady=8)
        self.nb = nb
        nb.add(self.tab_control(nb), text='Điều khiển')
        for name, items in SPEC.items():
            nb.add(self.tab_form(nb, items), text=name)
        nb.add(self.tab_update(nb), text='Cập nhật')
        # log
        lf = ttk.LabelFrame(self.root, text='Nhật ký'); lf.pack(fill='x', padx=8, pady=(0, 8))
        self.logbox = tk.Text(lf, height=8, bg=BG2, fg='#d8cdf0', relief='flat', font=('Consolas', 9), wrap='word')
        self.logbox.pack(fill='x', padx=4, pady=4)

    def tab_control(self, nb):
        f = ttk.Frame(nb)
        lf = ttk.LabelFrame(f, text='TikTok LIVE'); lf.pack(fill='x', padx=8, pady=8)
        ttk.Label(lf, text='Tên TikTok (@...)').grid(row=0, column=0, sticky='w', padx=6, pady=4)
        self.v_user = tk.StringVar(value=self.cfg.get('username', ''))
        ttk.Entry(lf, textvariable=self.v_user, width=28).grid(row=0, column=1, sticky='we', padx=6)
        ttk.Label(lf, text='Sign API key (nếu có)').grid(row=1, column=0, sticky='w', padx=6, pady=4)
        self.v_key = tk.StringVar(value=self.cfg.get('sign_api_key', ''))
        ttk.Entry(lf, textvariable=self.v_key, width=28, show='•').grid(row=1, column=1, sticky='we', padx=6)
        self.v_auto = tk.BooleanVar(value=self.cfg.get('auto_connect', False))
        ttk.Checkbutton(lf, text='Tự kết nối khi mở', variable=self.v_auto).grid(row=2, column=0, columnspan=2, sticky='w', padx=6)
        bf = ttk.Frame(lf); bf.grid(row=3, column=0, columnspan=2, pady=6)
        ttk.Button(bf, text='Kết nối', style='Acc.TButton', command=self.connect).pack(side='left', padx=4)
        ttk.Button(bf, text='Ngắt', command=lambda: self.ipc.send({'cmd': 'disconnect'})).pack(side='left', padx=4)
        self.l_tt = ttk.Label(lf, text='Trạng thái: —', style='S.TLabel'); self.l_tt.grid(row=4, column=0, columnspan=2, sticky='w', padx=6)
        lf.columnconfigure(1, weight=1)

        sf = ttk.LabelFrame(f, text='Thống kê'); sf.pack(fill='x', padx=8, pady=4)
        self.stat_lbl = {}
        keys = [('fps', 'FPS'), ('hp', 'Máu Hero'), ('dist', 'Quãng đường (m)'), ('kills', 'Quái đã diệt'),
                ('deaths', 'Số lần gục'), ('guests', 'Pet'), ('monsters', 'Quái trên màn'),
                ('likes', 'Tổng tim'), ('coins', 'Tổng xu'), ('buff_q', 'Buff đang chờ'), ('helper_q', 'Trợ thủ đang chờ'),
                ('voice', 'Giọng nói'), ('music', 'Đang phát'), ('window', 'Cửa sổ game'), ('vcam', 'Camera ảo')]
        for i, (k, lbl) in enumerate(keys):
            ttk.Label(sf, text=lbl, style='S.TLabel').grid(row=i // 2, column=(i % 2) * 2, sticky='w', padx=6, pady=1)
            l = ttk.Label(sf, text='—'); l.grid(row=i // 2, column=(i % 2) * 2 + 1, sticky='w', padx=6)
            self.stat_lbl[k] = l
        self.l_game = ttk.Label(f, text='Game: đang khởi động...', style='S.TLabel'); self.l_game.pack(anchor='w', padx=12)

        tf = ttk.LabelFrame(f, text='Thử nghiệm (không cần LIVE)'); tf.pack(fill='x', padx=8, pady=6)
        tests = [('+ Khách vào', {'kind': 'guest'}), ('+100 tim', {'kind': 'like', 'value': 100}),
                 ('+15 tim', {'kind': 'like', 'value': 15}), ('+40 tim', {'kind': 'like', 'value': 40}),
                 ('Buff DAME', {'kind': 'buff', 'value': 'damage'}), ('Buff MÁU', {'kind': 'buff', 'value': 'heal'}),
                 ('Buff GIÁP', {'kind': 'buff', 'value': 'armor'}), ('Tặng 1 xu', {'kind': 'gift', 'value': 1}),
                 ('Tặng 5 xu', {'kind': 'gift', 'value': 5}), ('Thêm quái', {'kind': 'monster'}),
                 ('Chướng ngại', {'kind': 'trap'}), ('Hero -20 máu', {'kind': 'hurt', 'value': 20}),
                 ('Hero gục', {'kind': 'kill'})]
        for i, (t, d) in enumerate(tests):
            ttk.Button(tf, text=t, command=lambda d=d: self.ipc.send(dict(cmd='test', **d))).grid(
                row=i // 3, column=i % 3, sticky='we', padx=3, pady=3)
        for c in range(3): tf.columnconfigure(c, weight=1)

        gf = ttk.Frame(f); gf.pack(fill='x', padx=8, pady=6)
        ttk.Button(gf, text='Chơi lại', command=lambda: self.ipc.send({'cmd': 'reset'})).pack(side='left', padx=3)
        ttk.Button(gf, text='Xoá pet', command=lambda: self.ipc.send({'cmd': 'clear_guests'})).pack(side='left', padx=3)
        ttk.Button(gf, text='Mở lại cửa sổ game', command=self.restart_game).pack(side='left', padx=3)
        ttk.Button(gf, text='Bài nhạc tiếp', command=lambda: self.ipc.send({'cmd': 'music_next'})).pack(side='left', padx=3)
        ttk.Label(f, text='Phím tắt trong cửa sổ game: G khách · H 100 tim · 1/2/3 buff · R robot · K hiệp sĩ\n'
                         'J vài chục tim · M quái · T chướng ngại · X -20 máu · D gục · N bài nhạc tiếp · F5 chơi lại', style='S.TLabel').pack(anchor='w', padx=12)
        return f

    def tab_form(self, nb, items):
        outer = ttk.Frame(nb)
        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient='vertical', command=canvas.yview)
        f = ttk.Frame(canvas)
        f.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=f, anchor='nw')
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side='left', fill='both', expand=True); sb.pack(side='right', fill='y')
        wheel = lambda e: canvas.yview_scroll(int(-e.delta / 120), 'units')
        canvas.bind('<Enter>', lambda e: canvas.bind_all('<MouseWheel>', wheel))
        canvas.bind('<Leave>', lambda e: canvas.unbind_all('<MouseWheel>'))
        for r, (key, label, typ, arg) in enumerate(items):
            ttk.Label(f, text=label).grid(row=r * 2, column=0, sticky='w', padx=8, pady=(6, 0))
            val = self.cfg.get(key)
            if typ == 'bool':
                v = tk.BooleanVar(value=bool(val)); ttk.Checkbutton(f, variable=v).grid(row=r * 2, column=1, sticky='w')
            elif typ == 'voice':
                v = tk.StringVar(value=str(val))
                ttk.Combobox(f, textvariable=v, values=VOICE_LIST, width=16).grid(row=r * 2, column=1, sticky='w', padx=6)
                role = key.replace('tts_voice_', '')
                ttk.Button(f, text='Nghe thử', command=lambda role=role, k=key: (self.apply(), self.ipc.send(
                    {'cmd': 'test', 'kind': 'voice', 'value': role}))).grid(row=r * 2, column=2, padx=4)
            elif typ == 'folder':
                v = tk.StringVar(value=str(val))
                ttk.Entry(f, textvariable=v, width=22).grid(row=r * 2, column=1, sticky='w', padx=6)
                def pick(v=v):
                    from tkinter import filedialog
                    d = filedialog.askdirectory(title='Chọn thư mục nhạc')
                    if d: v.set(d)
                ttk.Button(f, text='Chọn...', command=pick).grid(row=r * 2, column=2, padx=4)
            elif typ == 'choice':
                v = tk.StringVar(value=str(val))
                ttk.Combobox(f, textvariable=v, values=[str(x) for x in arg], width=14, state='readonly').grid(row=r * 2, column=1, sticky='w', padx=6)
            elif typ in ('int', 'float'):
                v = tk.StringVar(value=str(val))
                inc = 1 if typ == 'int' else (0.05 if arg[1] <= 3 else 0.1)
                ttk.Spinbox(f, textvariable=v, from_=arg[0], to=arg[1], increment=inc, width=12).grid(row=r * 2, column=1, sticky='w', padx=6)
            else:
                v = tk.StringVar(value=str(val)); ttk.Entry(f, textvariable=v, width=22).grid(row=r * 2, column=1, sticky='w', padx=6)
            self.vars[key] = (v, typ, arg)
            if key in GUIDE:
                ttk.Label(f, text=GUIDE[key], style='S.TLabel').grid(row=r * 2 + 1, column=0, columnspan=2, sticky='w', padx=8)
        ttk.Button(f, text='Lưu & áp dụng', style='Acc.TButton', command=self.apply).grid(
            row=len(items) * 2 + 1, column=0, columnspan=2, pady=12)
        return outer

    def tab_update(self, nb):
        f = ttk.Frame(nb)
        ttk.Label(f, text='Cập nhật nóng qua GitHub', style='H.TLabel').pack(anchor='w', padx=10, pady=(10, 4))
        self.l_ver = ttk.Label(f, text=f'Phiên bản hiện tại: {C.version()}'); self.l_ver.pack(anchor='w', padx=10)
        g = ttk.Frame(f); g.pack(fill='x', padx=10, pady=8)
        ttk.Label(g, text='Repo (user/tên-repo)').grid(row=0, column=0, sticky='w')
        self.v_repo = tk.StringVar(value=self.cfg.get('update_repo', ''))
        ttk.Entry(g, textvariable=self.v_repo, width=34).grid(row=0, column=1, padx=6, pady=3)
        ttk.Label(g, text='Nhánh').grid(row=1, column=0, sticky='w')
        self.v_branch = tk.StringVar(value=self.cfg.get('update_branch', 'main'))
        ttk.Entry(g, textvariable=self.v_branch, width=14).grid(row=1, column=1, sticky='w', padx=6, pady=3)
        self.v_autoupd = tk.BooleanVar(value=self.cfg.get('auto_update', True))
        ttk.Checkbutton(g, text='Tự kiểm tra khi mở app', variable=self.v_autoupd).grid(row=2, column=0, columnspan=2, sticky='w')
        ttk.Button(f, text='Kiểm tra & cập nhật ngay', style='Acc.TButton',
                   command=self.start_update).pack(anchor='w', padx=10, pady=6)
        self.l_upd = ttk.Label(f, text='', style='S.TLabel', wraplength=440); self.l_upd.pack(anchor='w', padx=10)
        ttk.Label(f, text='Cập nhật xong app sẽ tự khởi động lại game + bảng điều khiển.\n'
                         'config.json (cài đặt của bạn) không bao giờ bị ghi đè.', style='S.TLabel').pack(anchor='w', padx=10, pady=8)
        return f

    # ------------------------------------------------------------
    def log(self, msg):
        self.logbox.insert('end', msg.rstrip() + '\n')
        self.logbox.see('end')
        if int(self.logbox.index('end-1c').split('.')[0]) > 400:
            self.logbox.delete('1.0', '100.0')

    def collect(self):
        cfg = dict(self.cfg)
        for k, (v, typ, arg) in self.vars.items():
            raw = v.get()
            try:
                if typ == 'int': val = int(float(raw)); val = max(arg[0], min(arg[1], val))
                elif typ == 'float': val = float(raw); val = max(arg[0], min(arg[1], val))
                elif typ == 'bool': val = bool(raw)
                elif typ == 'choice': val = int(raw) if isinstance(arg[0], int) else raw
                else: val = raw.strip() if isinstance(raw, str) else raw
            except ValueError:
                val = self.cfg.get(k)
            cfg[k] = val
        cfg['username'] = self.v_user.get().strip().lstrip('@')
        cfg['sign_api_key'] = self.v_key.get().strip()
        cfg['auto_connect'] = bool(self.v_auto.get())
        cfg['update_repo'] = self.v_repo.get().strip()
        cfg['update_branch'] = self.v_branch.get().strip() or 'main'
        cfg['auto_update'] = bool(self.v_autoupd.get())
        return cfg

    def apply(self):
        self.cfg = self.collect()
        C.save(self.cfg)
        ok = self.ipc.send({'cmd': 'config', 'data': self.cfg})
        self.log('Đã lưu cài đặt' + ('' if ok else ' (game chưa kết nối — sẽ dùng khi mở game)'))

    def connect(self):
        self.apply()
        self.ipc.send({'cmd': 'connect', 'username': self.cfg['username'], 'sign_api_key': self.cfg['sign_api_key']})
        self.log(f"Đang kết nối @{self.cfg['username']}...")

    # ------------------------------------------------------------
    def start_game(self):
        if self.proc and self.proc.poll() is None: return
        try:
            self.proc = subprocess.Popen(self.game_cmd, cwd=C.ROOT)
            self.log('Đã mở cửa sổ game')
        except Exception as e:
            self.log(f'Không mở được game: {e}')

    def restart_game(self):
        self.stop_game()
        self.root.after(800, self.start_game)

    def stop_game(self):
        if self.proc and self.proc.poll() is None:
            self.ipc.send({'cmd': 'quit'})
            try:
                self.proc.wait(3)
            except Exception:
                self.proc.kill()

    def poll(self):
        try:
            while True:
                m = self.ipc.recv_q.get_nowait()
                if m.get('type') == 'status':
                    self.l_tt.config(text='Trạng thái: ' + str(m.get('tiktok')))
                    for k, l in self.stat_lbl.items():
                        if k in m: l.config(text=str(m[k]))
                elif m.get('type') == 'log':
                    self.log(m.get('msg', ''))
        except queue.Empty:
            pass
        alive = self.proc and self.proc.poll() is None
        self.l_game.config(text='Game: ' + ('đang chạy' + (' · đã nối bảng điều khiển' if self.ipc.connected else ' · đang nối...')
                                           if alive else 'đã đóng — bấm "Mở lại cửa sổ game"'))
        self.root.after(300, self.poll)

    DEPS = {'pygame': 'pygame-ce', 'PIL': 'Pillow', 'TikTokLive': 'TikTokLive', 'vieneu': 'vieneu',
            'pyvirtualcam': 'pyvirtualcam'}

    def ensure_deps(self):
        """tự cài thư viện còn thiếu (khi bản cập nhật cần thư viện mới)"""
        if getattr(sys, 'frozen', False): return
        import importlib.util
        miss = [pkg for mod, pkg in self.DEPS.items() if importlib.util.find_spec(mod) is None]
        if not miss: return
        self.root.after(0, lambda: self.log('Đang cài thư viện còn thiếu: ' + ', '.join(miss) + ' ...'))
        flags = 0x08000000 if sys.platform == 'win32' else 0   # CREATE_NO_WINDOW
        py = sys.executable
        if py.lower().endswith('pythonw.exe'): py = py[:-11] + 'python.exe'
        try:
            r = subprocess.run([py, '-m', 'pip', 'install', '-q'] + miss, capture_output=True, text=True,
                               creationflags=flags, timeout=1800)
            ok = r.returncode == 0
            msg = 'Đã cài xong: ' + ', '.join(miss) + ' — mở lại cửa sổ game' if ok else 'Cài thư viện lỗi: ' + (r.stderr or '')[-300:]
        except Exception as e:
            ok = False; msg = f'Cài thư viện lỗi: {e}'
        self.root.after(0, lambda: self.log(msg))
        if ok: self.root.after(0, self.restart_game)

    def start_update(self, silent=False):
        repo = self.v_repo.get().strip(); br = self.v_branch.get().strip() or 'main'
        threading.Thread(target=self.do_update, args=(repo, br, silent), daemon=True).start()

    def do_update(self, repo, br, silent=False):
        if not repo:
            self.root.after(0, lambda: self.l_upd.config(text='Chưa điền repo')); return
        msgs = []
        def lg(s):
            msgs.append(s); self.root.after(0, lambda s=s: (self.l_upd.config(text=s), self.log(s)))
        def pr(i, n, p):
            self.root.after(0, lambda: self.l_upd.config(text=f'Đang tải {i}/{n}: {p}'))
        try:
            changed = updater.apply(repo, br, lg, pr)
        except Exception as e:
            if not silent: lg(f'Không cập nhật được: {e}')
            else: self.root.after(0, lambda: self.log(f'Kiểm tra cập nhật: {e}'))
            return
        if changed:
            self.root.after(0, self.restart_all)

    def restart_all(self):
        self.log('Khởi động lại sau cập nhật...')
        self.stop_game()
        self.ipc.alive = False
        self.root.destroy()
        args = sys.argv[1:] if getattr(sys, 'frozen', False) else sys.argv
        subprocess.Popen([sys.executable] + args, cwd=C.ROOT)
        os._exit(0)

    def close(self):
        try:
            self.cfg = self.collect(); C.save(self.cfg)
        except Exception:
            pass
        self.stop_game()
        self.ipc.alive = False
        self.root.destroy()

    def run(self):
        self.root.mainloop()
