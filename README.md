# Hero Run Live — game side-scrolling 8-bit cho TikTok LIVE

## Chạy (Windows)
1. Cài Python 3.11+ (tick "Add Python to PATH").
2. Bấm đúp `run.bat` → lần đầu tự cài thư viện, sau đó mở **bảng điều khiển** + **cửa sổ game 9:16**.
3. Trong TikTok LIVE Studio thêm nguồn **Cửa sổ / Window capture** → chọn cửa sổ `Hero Run Live — 9:16`.
4. Tab *Điều khiển* → nhập tên TikTok → **Kết nối**.

Muốn file .exe: chạy `build_exe.bat` → `HeroRunLive.exe` (đặt cùng thư mục với `app\` và `assets\` — code nằm ngoài exe để cập nhật nóng được).

Chạy riêng cửa sổ game: `python launcher.py --game`

## Luật chơi
| Người xem | Kết quả |
|---|---|
| Vào xem / bình luận / thả tim | Thành **pet** dễ thương (bay hoặc chạy dưới đất, có avatar + tên). Tối đa 10 pet cùng lúc, mỗi pet ở 60s; hết giờ (hoặc khi đủ 10 mà có người mới) pet bay ra trước mặt Hero và **bị bắn tan** thành hạt pixel |
| Thả đủ 100 tim | Avatar hiện trong khung, camera zoom 1s rồi bay vào người Hero → Hero được **tiếp sức** (hào quang + tia laser đổi màu) |
| Tặng quà bất kỳ | Hero **bắn tia sáng lên trời, ghép thành avatar 8-bit** của người tặng + tên + số xu. **Tặng càng nhiều xu, avatar càng to và càng chi tiết** (1 xu ≈ 110px / 24×24 ô → 1000 xu ≈ 480px / 72×72 ô). Tốc độ vẽ chỉnh ở tab *Tương tác* (`art_speed`) |

Hero chỉ chạy tới (không còn quái vật). Chướng ngại vật nhảy/trượt có thể bật lại ở tab *Gameplay*.

Phím tắt trong cửa sổ game: `G` khách · `H` 100 tim · `J` vài chục tim · `1/2/3/4` tặng 1/10/100/1000 xu · `E` pet hết giờ · `T` chướng ngại · `N` bài nhạc tiếp · `F5` chơi lại.

## Xuất đúng 1080x1920 (màn hình nhỏ hơn vẫn được)
Cửa sổ game không thể cao hơn màn hình (màn 1080p → tối đa ~556x990). Muốn phát nét 1080x1920:
1. Cài **OBS Studio** (chỉ để có *OBS Virtual Camera*, không cần mở OBS).
2. Tab *Hiển thị* → tick **Xuất CAMERA ẢO** → *Lưu & áp dụng*.
3. TikTok LIVE Studio → thêm nguồn **Camera** → chọn **OBS Virtual Camera** (tắt lật gương). Bỏ nguồn Window capture cũ.

## Nhạc nền (tab *Nhạc nền*)
- 6 bài dựng sẵn (★, nhạc tự tạo, không lo bản quyền) + nhạc của bạn (♪) trong thư mục `music\`.
- Chọn nguồn (tất cả / dựng sẵn / của bạn / nhạc cũ / tắt), phát ngẫu nhiên, kéo âm lượng trực tiếp.
- Bấm đúp 1 bài để **lặp lại bài đó**, hoặc *Phát cả danh sách*. Nút ⏮ ⏯ ⏭, *+ Thêm nhạc...* (chép file vào thư mục nhạc), *Mở thư mục nhạc*.

## Lồng tiếng (VieNeu-TTS)
- Chạy trên máy (CPU, ONNX) — `run.bat` tự cài `vieneu`. Lần đầu bật game sẽ tải model từ HuggingFace (vài trăm MB), sau đó dùng offline.
- 2 vai: **người dẫn** (đọc hướng dẫn chơi mỗi 45s, chào người mới, nhắc người sắp đủ tim) và **Hero** (cảm ơn người tặng quà / tiếp sức, chào tạm biệt pet bị bắn). Mỗi vai chọn giọng riêng ở tab *Giọng nói*, có nút *Nghe thử*.
- Câu đã đọc được lưu ở `voice_cache\` → lần sau phát ngay. Câu có tên người xem sinh lúc chạy (bỏ emoji/ký hiệu trong tên).
- Có phụ đề lời thoại trên màn hình. Nhạc nền tự nhỏ lại khi nhân vật nói.
- Máy yếu: chuyển *Model* sang `v3nano` hoặc giảm *Số luồng CPU cho TTS*.

## Cập nhật nóng qua GitHub
1. Tạo repo công khai (mặc định app đọc `koddrawer/HeroRun---Update`, đổi được ở tab *Cập nhật*).
2. Mỗi lần ra bản mới, tại thư mục app: `python tools/make_manifest.py 1.0.1 "ghi chú"` → đẩy toàn bộ thư mục (kèm `manifest.json`) lên repo.
3. App tự kiểm tra lúc mở (hoặc bấm *Kiểm tra & cập nhật ngay*): chỉ tải file đổi checksum, rồi tự khởi động lại. `config.json` không bị ghi đè.

## Cấu trúc
```
launcher.py        điểm chạy (panel / --game)
app/game.py        game: hero, quái, chướng ngại, khách, buff, robot, hiệp sĩ, camera
app/panel.py       bảng điều khiển (Tkinter)
app/tiktok_client.py  kết nối TikTok LIVE (thư viện TikTokLive)
app/updater.py     cập nhật nóng
app/defaults.py    toàn bộ thông số mặc định
assets/sprites     sprite đã cắt từ ảnh của bạn + meta.json (khung hình, tâm vòng avatar)
assets/sfx         âm thanh + nhạc nền 8-bit
```
