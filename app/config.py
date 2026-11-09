import json, os, sys
from .defaults import DEFAULTS


def app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


ROOT = app_dir()
CFG_PATH = os.path.join(ROOT, 'config.json')
ASSETS = os.path.join(ROOT, 'assets')


def load():
    cfg = dict(DEFAULTS)
    try:
        with open(CFG_PATH, encoding='utf-8') as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    if cfg.get('music_source') == 'auto':
        cfg['music_source'] = 'all'
    if cfg.get('update_repo') in ('', 'koddrawer/hero-run-live-updates'):
        cfg['update_repo'] = DEFAULTS['update_repo']
    return cfg


def save(cfg):
    tmp = CFG_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CFG_PATH)


def version():
    try:
        with open(os.path.join(ROOT, 'version.json'), encoding='utf-8') as f:
            return json.load(f).get('version', '0.0.0')
    except Exception:
        return '0.0.0'
