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
    "vcam_enabled": False,          # xuất ra camera ảo (OBS Virtual Camera) đúng độ phân giải
    "vcam_size": "1080x1920",
    "vcam_fps": 30,
    "vcam_backend": "",             # "" = tự chọn | obs | unitycapture

    # ---- nhân vật ----
    "scroll_speed": 230,            # px/giây
    "fire_interval": 0.28,          # giây giữa 2 phát bắn pet hết giờ
    "obstacles_enabled": False,     # chướng ngại vật (nhảy/trượt) — mặc định tắt: Hero chỉ chạy tới
    "obstacle_interval": 4.5,
    "dodge_fail_pct": 8,

    # ---- người xem = pet ----
    "guest_max": 10,                # tối đa cùng lúc; đầy thì pet xuất hiện lâu nhất bị bắn
    "guest_life": 60,               # mỗi pet tồn tại (giây), hết giờ bị Hero bắn tan
    "guest_min_show": 8,            # pet hiện ít nhất N giây mới bị người mới thay
    "guest_scale": 0.85,
    "guest_on_join": True,
    "guest_on_comment": True,
    "guest_on_like": True,

    # ---- thả tim ----
    "likes_per_buff": 100,
    "buff_mode": "random",          # random | cycle (kiểu hào quang tiếp sức)
    "power_time": 8,                # giây Hero được tiếp sức
    "zoom_like_time": 1.0,
    "show_hearts": True,
    "show_top3": True,              # bảng TOP 3 sắp đủ tim
    "top3_window": 300,             # chỉ tính người thả tim trong N giây gần nhất
    "tts_top_nudge": True,          # người dẫn nhắc người sắp đủ tim

    # ---- donate: avatar 8-bit trên trời ----
    "art_min_px": 110,              # cỡ avatar khi tặng ít (1 xu)
    "art_max_px": 480,              # cỡ avatar tối đa
    "art_coins_max": 1000,          # số xu để đạt cỡ tối đa (tăng theo log)
    "art_grid_min": 24,             # độ phân giải avatar nhỏ nhất (ô pixel mỗi cạnh)
    "art_grid_max": 72,             # độ phân giải avatar lớn nhất (avatar to = chi tiết hơn)
    "art_speed": 1.0,               # tốc độ vẽ avatar (x1 = bình thường, 2 = nhanh gấp đôi, 0.5 = chậm)
    "art_show_time": 5,             # giây hiển thị (+ tới 3s cho quà lớn)
    "art_queue_max": 20,
    "zoom_scale": 1.6,

    # ---- âm thanh / giao diện ----
    "music_volume": 0.35,
    "music_source": "all",          # all | builtin | folder | classic | off
    "music_track": "",              # "" = phát cả danh sách | key 1 bài (builtin/x.ogg, folder/y.mp3)
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
