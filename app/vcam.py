# Xuất hình game ra CAMERA ẢO (OBS Virtual Camera / Unity Capture) đúng độ phân giải, không phụ thuộc cỡ màn hình
import threading, time
import pygame


class VirtualCam:
    def __init__(self, game):
        self.g = game
        self.cam = None
        self.size = None
        self.fps = 30
        self.state = 'tắt'
        self.frame = None
        self.lock = threading.Lock()
        self.ev = threading.Event()
        self.next_t = 0
        self.next_frame_t = 0
        self.alive = True
        threading.Thread(target=self._sender, daemon=True).start()

    def _open(self, w, h, fps):
        self._close()
        try:
            import pyvirtualcam
        except ImportError:
            self.state = 'chưa cài pyvirtualcam'; self.g.log('Camera ảo: ' + self.state); return
        err = None
        for backend in (self.g.cfg.get('vcam_backend') or None, None):
            try:
                self.cam = pyvirtualcam.Camera(width=w, height=h, fps=fps, fmt=pyvirtualcam.PixelFormat.RGB, backend=backend)
                break
            except Exception as e:
                err = e; self.cam = None
        if self.cam is None:
            self.state = f'lỗi: {str(err)[:90]}'
            self.g.log('Camera ảo lỗi — cần cài OBS Studio (có sẵn OBS Virtual Camera). ' + str(err)[:120])
            return
        self.size = (w, h); self.fps = fps
        self.state = f'đang xuất {w}x{h} @{fps}fps → {self.cam.device}'
        self.g.log('Camera ảo: ' + self.state)

    def _close(self):
        if self.cam:
            try: self.cam.close()
            except Exception: pass
        self.cam = None; self.size = None

    def update(self, screen):
        """gọi mỗi frame ở luồng chính"""
        cfg = self.g.cfg
        if not cfg.get('vcam_enabled'):
            if self.cam: self._close(); self.state = 'tắt'
            return
        try:
            w, h = [int(v) for v in str(cfg.get('vcam_size', '1080x1920')).lower().split('x')]
        except Exception:
            w, h = 1080, 1920
        fps = int(cfg.get('vcam_fps', 30))
        if self.cam is None or self.size != (w, h) or self.fps != fps:
            if time.time() < self.next_t: return
            self._open(w, h, fps)
            if self.cam is None:
                self.next_t = time.time() + 15     # thử lại sau 15s
                return
        now = time.time()
        if now < self.next_frame_t: return
        self.next_frame_t = now + 1.0 / fps * 0.95
        img = screen if screen.get_size() == (w, h) else pygame.transform.smoothscale(screen, (w, h))
        data = pygame.image.tobytes(img, 'RGB')
        with self.lock:
            self.frame = data
        self.ev.set()

    def _sender(self):
        import numpy as np
        while self.alive:
            self.ev.wait(0.5); self.ev.clear()
            with self.lock:
                data, self.frame = self.frame, None
            cam = self.cam
            if data is None or cam is None: continue
            try:
                w, h = self.size
                cam.send(np.frombuffer(data, np.uint8).reshape(h, w, 3))
            except Exception as e:
                self.state = f'lỗi gửi: {str(e)[:60]}'

    def stop(self):
        self.alive = False
        self._close()
