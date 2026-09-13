"""
Config Manager untuk Automated Media Uploader v6
Mengelola config.json — baca, tulis, default.
"""

import os
import json

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "userhash": "Harap diisi agar tidak anonym",
    "judul_project": "Tamvan",
    "counter_namespace": "Contoh: tamvan-dan-pemberani",
    "photos_dir": "./media",
    "workers": 1,
    "verify_cached_urls": False,
    "upload_thumbnails": True,
    "output_html": "index.html",
    "items_per_page": 24,
    # ─── GitHub ───
    "github_username": "",
    "github_repo": "",
    "github_token": "",
    "github_branch": "main",
    "github_auto_upload": False,
}


def load_config():
    """Baca config.json, atau buat baru dengan default."""
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        merged = dict(DEFAULT_CONFIG)
        merged.update(cfg)
        return merged
    except Exception:
        return dict(DEFAULT_CONFIG)


def save_config(cfg):
    """Simpan config ke config.json."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def update_config(key, value):
    """Update satu key dan simpan."""
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)
    return cfg