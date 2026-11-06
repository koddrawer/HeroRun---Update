# Cập nhật nóng từ GitHub repo (raw.githubusercontent.com)
# Repo chứa: manifest.json + toàn bộ file của app (cùng cấu trúc thư mục)
import json, os, hashlib, urllib.request, time, tempfile, shutil
from . import config as C

SKIP = {'config.json'}


def _get(url, timeout=15):
    req = urllib.request.Request(url + ('&' if '?' in url else '?') + 't=' + str(int(time.time())),
                                 headers={'User-Agent': 'HeroRunLive-Updater', 'Cache-Control': 'no-cache'})
    return urllib.request.urlopen(req, timeout=timeout).read()


def _sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 16), b''):
            h.update(b)
    return h.hexdigest()


def _vt(v):
    try:
        return tuple(int(x) for x in str(v).split('.'))
    except Exception:
        return (0,)


def check(repo, branch='main'):
    """trả về (manifest, [file cần tải]) hoặc (None, [])"""
    base = f'https://raw.githubusercontent.com/{repo}/{branch}/'
    man = json.loads(_get(base + 'manifest.json').decode('utf-8'))
    need = []
    for f in man.get('files', []):
        p = f['path']
        if p in SKIP: continue
        local = os.path.join(C.ROOT, p)
        if not os.path.exists(local) or _sha(local) != f['sha256']:
            need.append(f)
    return man, need


def apply(repo, branch='main', log=print, progress=None):
    """tải file thay đổi; trả về True nếu đã cập nhật"""
    base = f'https://raw.githubusercontent.com/{repo}/{branch}/'
    man, need = check(repo, branch)
    cur = C.version()
    if not need:
        log(f'Đang ở bản mới nhất ({cur})')
        return False
    log(f'Có bản {man.get("version")} (hiện {cur}) — tải {len(need)} file...')
    tmpdir = tempfile.mkdtemp(prefix='hrl_upd_')
    try:
        for i, f in enumerate(need):
            data = _get(base + urllib.request.quote(f['path']), 60)
            if hashlib.sha256(data).hexdigest() != f['sha256']:
                raise RuntimeError(f'Sai checksum: {f["path"]}')
            dst = os.path.join(tmpdir, f['path'])
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as o: o.write(data)
            if progress: progress(i + 1, len(need), f['path'])
        # chép đè sau khi tải đủ
        for f in need:
            src = os.path.join(tmpdir, f['path']); dst = os.path.join(C.ROOT, f['path'])
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            try:
                os.replace(src, dst)
            except OSError:
                shutil.copyfile(src, dst)
        with open(os.path.join(C.ROOT, 'version.json'), 'w', encoding='utf-8') as o:
            json.dump({'version': man.get('version', cur), 'notes': man.get('notes', '')}, o, ensure_ascii=False)
        log(f'Đã cập nhật lên {man.get("version")}. ' + (man.get('notes') or ''))
        return True
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
