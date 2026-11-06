# Cấu hình mặc định — panel ghi đè vào config.json
DEFAULTS = {
    # ---- kết nối ----
    "username": "",
    "sign_api_key": "",
    "auto_connect": False,

    # ---- cửa sổ ----
    "window_size": "720x1280",      # 540x960 | 720x1280 | 1080x1920
    "fps": 60,
    "window_x": -1, "window_y": -1,  # -1 = để hệ điều hành tự đặt

    # ---- nhân vật ----
    "scroll_speed": 230,           # px/giây
    "hero_max_hp": 100,
    "hero_damage": 10,
    "fire_interval": 0.28,          # giây giữa 2 phát bắn
    "dodge_fail_pct": 8,            # % né chướng ngại thất bại
    "obstacle_damage": 12,
    "respawn_time": 1.6,

    # ---- quái mặc định ----
    "monster_interval": 2.4,        # giây giữa các đợt quái
    "monster_max": 6,
    "monster_hp": 30,
    "monster_damage": 6,
    "monster_fire_interval": 2.2,
    "obstacle_interval": 4.5,       # giây giữa chướng ngại vật
    "difficulty_per_level": 8,      # % máu quái tăng mỗi cấp
    "meters_per_level": 300,

    # ---- khách xem (guest monster) ----
    "guest_max": 10,                # tối đa cùng lúc; đầy thì người xuất hiện lâu nhất biến mất
    "guest_life": 60,               # mỗi quái khách tồn tại (giây)
    "guest_min_show": 8,            # quái khách hiện ít nhất N giây mới bị người mới thay
    "guest_scale": 0.85,
    "guest_on_join": True,
    "guest_on_comment": True,
    "guest_on_like": True,

    # ---- thả tim ----
    "likes_per_buff": 100,
    "buff_mode": "auto",            # auto | random | cycle
    "buff_damage_pct": 50,          # +% sát thương mỗi cấp
    "buff_damage_time": 20,         # giây
    "buff_damage_max": 4,
    "buff_heal": 35,
    "buff_armor": 30,
    "armor_max": 100,
    "zoom_like_time": 1.0,
    "show_hearts": True,
    "show_top3": True,              # bảng TOP 3 sắp đủ tim
    "top3_window": 300,             # chỉ tính người thả tim trong N giây gần nhất
    "tts_top_nudge": True,          # người dẫn nhắc người sắp đủ tim

    # ---- donate ----
    "robot_coin": 1,
    "knight_coin": 5,
    "gift_rule": "unit",            # unit = theo giá 1 món | total = theo tổng xu
    "helper_cap": 5,                # tối đa trợ thủ cho 1 lần tặng
    "helper_queue_max": 15,
    "zoom_scale": 1.6,

    # ---- âm thanh / giao diện ----
    "music_volume": 0.35,
    "music_source": "auto",         # auto | folder | builtin | classic | off
    "music_folder": "music",        # thư mục nhạc của bạn (tương đối thư mục app hoặc đường dẫn đầy đủ)
    "music_shuffle": True,
    "sfx_volume": 0.7,
    "show_guide": True,
    "show_hud": True,
    "title": "HERO RUN LIVE",

    # ---- lồng tiếng VieNeu-TTS ----
    "tts_enabled": True,
    "tts_mode": "v3turbo",          # v3turbo (hay, 48kHz) | v3nano (nhẹ cho CPU yếu)
    "tts_precision": "fp32",        # fp32 | int8 (nhanh hơn, cần CPU hỗ trợ VNNI)
    "tts_threads": 2,               # số luồng CPU cho TTS (để dành CPU cho game/live)
    "tts_voice_narrator": "Trúc Ly",
    "tts_voice_hero": "Hải Đăng",
    "tts_voice_robot": "Minh Đức",
    "tts_voice_knight": "Thiện Minh",
    "tts_robot_fx": True,           # méo tiếng kiểu robot
    "voice_volume": 1.0,
    "tts_guide_interval": 45,       # giây giữa các câu hướng dẫn (0 = tắt)
    "tts_greet": True,              # chào người mới vào
    "tts_hero_chatter": True,       # hero nói khi nhảy/trượt/trúng đòn
    "show_subtitle": True,

    # ---- cập nhật ----
    "update_repo": "koddrawer/HeroRun---Update",
    "update_branch": "main",
    "auto_update": True,
}
