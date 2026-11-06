# Giao tiếp game <-> bảng điều khiển qua TCP localhost (JSON mỗi dòng)
import json, socket, threading, time, queue

PORT = 47821


class Server:
    """Chạy trong tiến trình game."""

    def __init__(self, inbox):
        self.inbox = inbox
        self.clients = []
        self.lock = threading.Lock()
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        for _ in range(30):
            try:
                srv.bind(('127.0.0.1', PORT)); break
            except OSError:
                time.sleep(0.5)
        srv.listen(4)
        while True:
            c, _ = srv.accept()
            with self.lock:
                self.clients.append(c)
            threading.Thread(target=self._read, args=(c,), daemon=True).start()

    def _read(self, c):
        buf = b''
        try:
            while True:
                d = c.recv(65536)
                if not d: break
                buf += d
                while b'\n' in buf:
                    line, buf = buf.split(b'\n', 1)
                    try:
                        self.inbox.put(('panel', json.loads(line.decode('utf-8'))))
                    except Exception:
                        pass
        except OSError:
            pass
        with self.lock:
            if c in self.clients: self.clients.remove(c)

    def send(self, obj):
        data = (json.dumps(obj, ensure_ascii=False) + '\n').encode('utf-8')
        with self.lock:
            for c in list(self.clients):
                try:
                    c.sendall(data)
                except OSError:
                    self.clients.remove(c)


class Client:
    """Chạy trong bảng điều khiển; tự kết nối lại."""

    def __init__(self):
        self.sock = None
        self.recv_q = queue.Queue()
        self.alive = True
        threading.Thread(target=self._loop, daemon=True).start()

    @property
    def connected(self):
        return self.sock is not None

    def _loop(self):
        while self.alive:
            try:
                s = socket.create_connection(('127.0.0.1', PORT), timeout=2)
                s.settimeout(None)
                self.sock = s
                buf = b''
                while True:
                    d = s.recv(65536)
                    if not d: break
                    buf += d
                    while b'\n' in buf:
                        line, buf = buf.split(b'\n', 1)
                        try:
                            self.recv_q.put(json.loads(line.decode('utf-8')))
                        except Exception:
                            pass
            except OSError:
                pass
            self.sock = None
            time.sleep(1)

    def send(self, obj):
        if not self.sock: return False
        try:
            self.sock.sendall((json.dumps(obj, ensure_ascii=False) + '\n').encode('utf-8'))
            return True
        except OSError:
            return False
