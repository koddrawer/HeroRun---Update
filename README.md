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
| Vào xem / bình luận / thả tim | Thành **quái khách** (bay lơ lửng hoặc chạy dưới đất, có avatar + tên), không đánh nhân vật. Tối đa 10 con cùng lúc, mỗi con sống 60s; người mới vào khi đủ 10 thì con xuất hiện lâu nhất biến mất |
| Thả đủ 100 tim (chỉnh được) | Avatar hiện trong khung buff (Dame đỏ / Máu xanh lá / Giáp xanh dương), camera zoom 1s, rồi bay vào người Hero |
| Tặng 1 xu | **ROBOT** đáp xuống (camera zoom tới khi hạ cánh), ra chưởng đánh bay quái, rồi bay đi |
| Tặng 5 xu | **HIỆP SĨ** xuất hiện (zoom tới khi đứng vững), chém đánh bay quái, rồi cháy biến mất |

Hero tự chạy + bắn (bắn thẳng quái đất, bắn chéo quái bay), tự **nhảy** qua chướng ngại dưới đất và **trượt** dưới chướng ngại treo/ngang đầu. Hết máu → gục → chạy lại vào màn hình hồi sinh, chạy tiếp.

Phím tắt trong cửa sổ game: `G` khách · `H` 100 tim · `1/2/3` buff · `R` robot · `K` hiệp sĩ · `M` quái · `T` chướng ngại · `X` -20 máu · `D` gục · `F5` chơi lại.

## Lồng tiếng (VieNeu-TTS)
- Chạy trên máy (CPU, ONNX) — `run.bat` tự cài `vieneu`. Lần đầu bật game sẽ tải model từ HuggingFace (vài trăm MB), sau đó dùng offline.
- 4 vai: **người dẫn** (đọc hướng dẫn chơi mỗi 45s + chào người mới), **Hero** (cảm ơn người buff, kêu khi nhảy/trượt/trúng đòn/gục/hồi sinh, xin tim khi yếu máu), **Robot** (giọng méo kiểu robot), **Hiệp sĩ**. Mỗi vai chọn giọng riêng ở tab *Giọng nói*, có nút *Nghe thử*.
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
