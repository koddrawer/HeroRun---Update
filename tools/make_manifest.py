# Tạo manifest.json cho repo cập nhật nóng.
# Cách dùng (tại thư mục gốc app):  python tools/make_manifest.py 1.0.1 "Ghi chú bản cập nhật"
import hashlib, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {'.git', '__pycache__', 'build', 'dist', 'tools', 'voice_cache'}
SKIP_FILES = {'config.json', 'manifest.json', 'error.log', '.deps_ok', 'HeroRunLive.exe', 'HeroRunLive.spec'}

ver = sys.argv[1] if len(sys.argv) > 1 else json.load(open(os.path.join(ROOT, 'version.json')))['version']
notes = sys.argv[2] if len(sys.argv) > 2 else ''
json.dump({'version': ver, 'notes': notes}, open(os.path.join(ROOT, 'version.json'), 'w', encoding='utf-8'), ensure_ascii=False)

files = []
for d, dirs, fs in os.walk(ROOT):
    dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
    for f in sorted(fs):
        if f in SKIP_FILES or f.endswith('.pyc'): continue
        p = os.path.join(d, f)
        rel = os.path.relpath(p, ROOT).replace('\\', '/')
        h = hashlib.sha256(open(p, 'rb').read()).hexdigest()
        files.append({'path': rel, 'sha256': h, 'size': os.path.getsize(p)})
json.dump({'version': ver, 'notes': notes, 'files': files}, open(os.path.join(ROOT, 'manifest.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'manifest.json: v{ver}, {len(files)} file')
