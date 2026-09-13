"""
Automated Media Uploader v6 — STANDALONE (FIXED)
- Template galeri (index.html)
- Template manager (manager.html)
- Auto-tag tanggal dari nama file
- OCR (Tesseract)
- Deteksi wajah (OpenCV)
- Filter deleted.json (blacklist)
- Auto-cleanup broken cache
"""

import os
import re
import sys
import json
import time
import shutil
import hashlib
import tempfile
import subprocess
import threading
import argparse
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

try:
    from requests_toolbelt.multipart.encoder import MultipartEncoder, MultipartEncoderMonitor
    TOOLBELT_AVAILABLE = True
except ImportError:
    TOOLBELT_AVAILABLE = False

try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS, IFD
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    IFD = None

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

from config_manager import load_config, save_config
from menu import run_menu, clear_screen

C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_PURPLE = "\033[95m"
C_CYAN = "\033[96m"
C_BLUE = "\033[94m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_ORANGE = "\033[33m"
C_RED = "\033[91m"
C_GRAY = "\033[90m"
C_WHITE = "\033[97m"

PROJECT_TITLE = "BARAYAWABELUT"
PHOTOS_DIR = "./media"
CACHE_FILE = "uploads_cache.json"
DELETED_FILE = "deleted.json"
OUTPUT_HTML = "index.html"
OUTPUT_MANAGER = "manager.html"
ITEMS_PER_PAGE = 24

CATBOX_USERHASH = ""
CATBOX_API = "https://catbox.moe/user/api.php"
CATBOX_MAX_FILE_SIZE = 200 * 1024 * 1024

COUNTER_NAMESPACE = "gallery-pemuda-rawabelut"
COUNTER_API_BASE = "https://abacus.jasoncameron.dev"

MAX_WORKERS = 1
VERIFY_CACHED_URLS = False
THUMBNAIL_DIR = os.path.join(tempfile.gettempdir(), "digital_collection_thumbs")
THUMB_MAX_SIZE = 720
THUMB_QUALITY = 80
UPLOAD_IMAGE_THUMBNAILS = True
THUMB_CLEANUP_MAX_AGE_DAYS = 30

SUPPORTED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".ico",
    ".mp4", ".mkv", ".webm", ".mov"
}
VIDEO_EXTS = {"MP4", "MKV", "WEBM", "MOV"}

VIDEO_MIME = {
    "MP4": "video/mp4",
    "WEBM": "video/webm",
    "MOV": "video/quicktime",
    "MKV": "video/x-matroska",
}

FFMPEG_PATH = shutil.which("ffmpeg")
_STATS_LOCK = threading.Lock()
_STDOUT_LOCK = threading.Lock()

SESSION_STATS = {
    "total_scanned": 0,
    "success_uploads": 0,
    "failed_uploads": 0,
    "cached_count": 0,
    "total_bytes_sent": 0,
    "start_time": 0,
    "end_time": 0,
    "item_counter": 0,
}

MONTH_NAMES_ID = [
    "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]


def format_bytes_adaptive(bytes_val):
    if not bytes_val or bytes_val == 0:
        return "0 B"
    val = float(bytes_val)
    if val < 1024:
        return f"{int(val)} B"
    elif val < 1024 * 1024:
        return f"{val / 1024:.1f} kB"
    elif val < 1024 * 1024 * 1024:
        return f"{val / (1024 * 1024):.1f} MB"
    else:
        return f"{val / (1024 * 1024 * 1024):.2f} GB"


format_bytes_apt = format_bytes_adaptive


def stats_inc(key, amount=1):
    with _STATS_LOCK:
        SESSION_STATS[key] = SESSION_STATS.get(key, 0) + amount


def stats_next_counter():
    with _STATS_LOCK:
        SESSION_STATS["item_counter"] += 1
        return SESSION_STATS["item_counter"]


def stats_snapshot():
    with _STATS_LOCK:
        return dict(SESSION_STATS)


_MEDIA_ICONS = {"image": "📷", "video": "🎬", "thumb": "🖼️", "default": "📤"}


def short_label(name, max_len=42):
    if len(name) <= max_len:
        return name
    keep = max_len - 3
    head = keep // 2
    tail = keep - head
    return f"{name[:head]}…{name[-tail:]}"


def print_banner():
    judul = globals().get("PROJECT_TITLE", "Automated Media Uploader")
    print(f"\n{C_PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C_RESET}")
    print(f"  {C_BOLD}🎨 {judul}{C_RESET}")
    print(f"{C_PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C_RESET}\n")


class ProgressPrinter:
    RENDER_INTERVAL = 0.25
    BAR_WIDTH = 10

    def __init__(self, total_size, label, current_idx, total_idx):
        self.total_size = max(1, total_size)
        self.label = label
        self.current_idx = current_idx
        self.total_idx = total_idx
        self._uploaded = 0
        self.start_time = time.time()
        self._last_len = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while not self._stop.is_set():
            with self._lock:
                self._render()
            time.sleep(self.RENDER_INTERVAL)

    def update(self, n):
        with self._lock:
            self._uploaded = n

    def _build_line(self):
        elapsed = max(0.001, time.time() - self.start_time)
        speed = self._uploaded / elapsed
        pct = int((self._uploaded / self.total_size) * 100)
        pct = max(0, min(100, pct))
        bar_w = self.BAR_WIDTH
        filled = int(bar_w * pct / 100)
        if pct >= 100:
            bar_colored = f"{C_GREEN}{'▰' * bar_w}{C_RESET}"
        else:
            bar_colored = f"{C_GREEN}{'▰' * filled}{C_GRAY}{'▱' * (bar_w - filled)}{C_RESET}"
        speed_str = f"{format_bytes_adaptive(speed)}/s"
        pct_str = f"{pct:3d}%"
        idx_str = f"[{self.current_idx}/{self.total_idx}]"
        term_w = shutil.get_terminal_size(fallback=(60, 20)).columns
        fixed_visible = len(idx_str) + 1 + bar_w + 1 + len(pct_str) + 1 + len(speed_str) + 1
        label_budget = term_w - fixed_visible - 2
        if label_budget < 6:
            label_budget = 0
        label = self.label
        if label_budget == 0:
            label = ''
        elif len(label) > label_budget:
            label = label[:max(1, label_budget - 1)] + '…'
        parts = [
            f"{C_PURPLE}{idx_str}{C_RESET}",
            bar_colored,
            f"{C_BOLD}{C_WHITE}{pct_str}{C_RESET}",
            f"{C_CYAN}{speed_str}{C_RESET}",
        ]
        if label:
            parts.append(f"{C_GRAY}{label}{C_RESET}")
        msg = " ".join(parts)
        visible = fixed_visible + (len(label) if label else 0) - 1
        return msg, visible

    def _render(self):
        with _STDOUT_LOCK:
            msg, visible = self._build_line()
            pad = ''
            if visible < self._last_len:
                pad = ' ' * (self._last_len - visible)
            self._last_len = max(visible, self._last_len)
            sys.stdout.write('\r\033[2K' + msg + pad)
            sys.stdout.flush()

    def finish(self):
        with self._lock:
            self._uploaded = self.total_size
            self._render()

    def stop(self):
        self._stop.set()
        try:
            self._thread.join(timeout=0.5)
        except Exception:
            pass
        with _STDOUT_LOCK:
            sys.stdout.write('\r\033[2K')
            sys.stdout.flush()
        self._last_len = 0


def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cache(cache):
    tmp = CACHE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)
    os.replace(tmp, CACHE_FILE)


def load_deleted():
    if os.path.exists(DELETED_FILE):
        try:
            with open(DELETED_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_deleted(deleted):
    tmp = DELETED_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(deleted, f, indent=2, ensure_ascii=False)
    os.replace(tmp, DELETED_FILE)


def check_url_active(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Range": "bytes=0-0",
    }
    try:
        res = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
        if res.status_code in (200, 206):
            return True
        if res.status_code == 404:
            return False
        if res.status_code in (403, 405):
            r = requests.get(url, headers=headers, stream=True, timeout=10)
            try:
                return r.status_code in (200, 206)
            finally:
                r.close()
        return True
    except requests.RequestException:
        return True


def _upload_streaming(file_path, data_fields, printer):
    """
    Upload streaming dengan progress bar.
    FIX: Pastikan file pointer di posisi 0, dan baca file dengan benar.
    """
    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    
    # FIX: Buka file fresh, jangan share file object
    file_obj = open(file_path, "rb")
    
    # FIX: Reset pointer ke awal untuk memastikan baca dari awal
    file_obj.seek(0, os.SEEK_SET)
    
    fields = dict(data_fields)
    fields["fileToUpload"] = (filename, file_obj, "application/octet-stream")
    
    try:
        encoder = MultipartEncoder(fields=fields)

        def _on_progress(monitor):
            printer.update(monitor.bytes_read)

        monitor = MultipartEncoderMonitor(encoder, _on_progress)
        res = requests.post(
            CATBOX_API,
            data=monitor,
            headers={
                "Content-Type": monitor.content_type,
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            },
            timeout=600,
        )
        res.raise_for_status()
        
        result = res.text.strip()
        
        # FIX: Validasi response — pastikan URL valid
        if not result or not result.startswith("http"):
            raise RuntimeError(f"Catbox response tidak valid: {result[:100]}")
        
        # FIX: Cek apakah ukuran file yang diupload sesuai
        # (dengan membandingkan bytes_read dengan file_size)
        if hasattr(monitor, 'bytes_read') and monitor.bytes_read < file_size:
            raise RuntimeError(
                f"Upload tidak lengkap: {monitor.bytes_read}/{file_size} bytes"
            )
        
        return result
    finally:
        try:
            file_obj.close()
        except Exception:
            pass


def _upload_simple(file_path, data_fields):
    """
    Upload sederhana tanpa progress bar.
    FIX: Validasi response & ukuran file.
    """
    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    
    with open(file_path, "rb") as f:
        f.seek(0, os.SEEK_SET)  # FIX: pastikan dari awal
        files = {"fileToUpload": (filename, f, "application/octet-stream")}
        res = requests.post(
            CATBOX_API,
            data=data_fields,
            files=files,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
            timeout=600,
        )
        res.raise_for_status()
        result = res.text.strip()
        
        # FIX: Validasi response
        if not result or not result.startswith("http"):
            raise RuntimeError(f"Catbox response tidak valid: {result[:100]}")
        return result
        


def _do_catbox_request(file_path, data_fields, printer):
    if TOOLBELT_AVAILABLE:
        return _upload_streaming(file_path, data_fields, printer)
    else:
        result = _upload_simple(file_path, data_fields)
        printer.update(os.path.getsize(file_path))
        return result


def upload_to_catbox(file_path, label=None, is_thumb=False, max_retry=3):
    """
    Upload file ke Catbox dengan retry & rate limit handling.
    FIX: 
    - Retry otomatis kalau gagal (timeout/rate limit)
    - Delay untuk anonymous user (hindari rate limit)
    - Validasi ukuran file
    """
    file_size = os.path.getsize(file_path)
    
    if not is_thumb and file_size > CATBOX_MAX_FILE_SIZE:
        raise RuntimeError(
            f"File melebihi batas Catbox ({format_bytes_adaptive(file_size)} > "
            f"{format_bytes_adaptive(CATBOX_MAX_FILE_SIZE)})"
        )
    
    raw_label = label or os.path.basename(file_path)
    label_display = short_label(raw_label, 42)
    
    if not is_thumb:
        idx = stats_next_counter()
    else:
        # FIX: Untuk thumbnail, pakai counter saat ini tanpa increment
        idx = stats_snapshot().get("item_counter", 0)
    
    total = stats_snapshot()["total_scanned"]
    ext = Path(file_path).suffix.lower().lstrip(".")
    
    if is_thumb:
        icon = _MEDIA_ICONS["thumb"]
        kind_txt = f"{C_ORANGE}THUMB{C_RESET}"
    elif ext in {"mp4", "mkv", "webm", "mov"}:
        icon = _MEDIA_ICONS["video"]
        kind_txt = f"{C_BLUE}MEDIA{C_RESET}"
    else:
        icon = _MEDIA_ICONS["image"]
        kind_txt = f"{C_BLUE}MEDIA{C_RESET}"
    
    # ── FIX: Ambil waktu upload ──
    upload_time_str = time.strftime("%H:%M:%S", time.localtime())
    # ── END FIX ──
    
    with _STDOUT_LOCK:
        sys.stdout.write(
            f"  {icon}  {C_PURPLE}{C_BOLD}[{idx}/{total}]{C_RESET}  {kind_txt}  "
            f"{C_WHITE}{label_display}{C_RESET}  {C_GRAY}⤷  {format_bytes_adaptive(file_size)}{C_RESET}  "
            f"{C_CYAN}🕐 {upload_time_str}{C_RESET}\n"
        )
        sys.stdout.flush()
    
    data_fields = {"reqtype": "fileupload"}
    if CATBOX_USERHASH:
        data_fields["userhash"] = CATBOX_USERHASH
    
    upload_start = time.time()
    result_url = None
    last_error = None
    
    # FIX: Retry loop
    for attempt in range(max_retry):
        printer = ProgressPrinter(
            total_size=file_size,
            label=label_display,
            current_idx=idx,
            total_idx=total,
        )
        
        try:
            try:
                result_url = _do_catbox_request(file_path, data_fields, printer)
                break  # sukses
            except requests.HTTPError as he:
                status = getattr(he.response, "status_code", None)
                
                # FIX: Handle rate limit (429) — tunggu & retry
                if status == 429:
                    printer.stop()
                    wait_time = (attempt + 1) * 15  # 15s, 30s, 45s
                    with _STDOUT_LOCK:
                        sys.stdout.write(
                            f"  {C_GRAY}╰─{C_RESET} {C_YELLOW}⏳ Rate limit, "
                            f"tunggu {wait_time}s... (attempt {attempt+1}/{max_retry}){C_RESET}\n"
                        )
                        sys.stdout.flush()
                    time.sleep(wait_time)
                    last_error = he
                    continue
                
                # FIX: Handle userhash invalid (412, 401, 403)
                elif status in (412, 401, 403) and "userhash" in data_fields:
                    printer.stop()
                    with _STDOUT_LOCK:
                        sys.stdout.write(
                            f"  {C_GRAY}╰─{C_RESET} {C_YELLOW}⚠️  Userhash invalid, "
                            f"coba anonymous...{C_RESET}\n"
                        )
                        sys.stdout.flush()
                    
                    # Fallback ke anonymous
                    printer2 = ProgressPrinter(
                        total_size=file_size,
                        label=label_display,
                        current_idx=idx,
                        total_idx=total,
                    )
                    try:
                        result_url = _do_catbox_request(
                            file_path, {"reqtype": "fileupload"}, printer2
                        )
                        printer2.finish()
                        time.sleep(0.15)
                        printer2.stop()
                        break
                    except Exception as e2:
                        printer2.stop()
                        last_error = e2
                        continue
                else:
                    printer.stop()
                    last_error = he
                    raise
            
            except requests.RequestException as re:
                # FIX: Handle timeout / connection error — retry
                printer.stop()
                last_error = re
                
                if attempt < max_retry - 1:
                    wait_time = (attempt + 1) * 5  # 5s, 10s
                    with _STDOUT_LOCK:
                        sys.stdout.write(
                            f"  {C_GRAY}╰─{C_RESET} {C_YELLOW}⚠️  {type(re).__name__}, "
                            f"retry dalam {wait_time}s... ({attempt+1}/{max_retry}){C_RESET}\n"
                        )
                        sys.stdout.flush()
                    time.sleep(wait_time)
                    continue
                else:
                    raise
        
        except Exception as e:
            printer.stop()
            last_error = e
            if attempt < max_retry - 1:
                continue
            else:
                raise
    
    if result_url is None:
        raise last_error or RuntimeError("Upload gagal setelah retry")
    
    elapsed = max(0.001, time.time() - upload_start)
    avg_speed = file_size / elapsed
    
    # ── FIX: Stop progress bar dulu ──
    try:
        printer.finish()
        time.sleep(0.1)
        printer.stop()
    except Exception:
        pass
    # ── END FIX ──
    
    # ── FIX: Waktu selesai ──
    finish_time_str = time.strftime("%H:%M:%S", time.localtime())
    # ── END FIX ──
    
    with _STDOUT_LOCK:
        sys.stdout.write(
            f"  {C_GRAY}╰─{C_RESET} {C_GREEN}✅{C_RESET}  "
            f"{C_WHITE}{format_bytes_adaptive(file_size)}{C_RESET}  "
            f"{C_GRAY}dalam{C_RESET} {C_YELLOW}{elapsed:.1f}s{C_RESET}  "
            f"{C_GRAY}({C_YELLOW}{format_bytes_adaptive(avg_speed)}/s{C_GRAY}){C_RESET}  "
            f"{C_CYAN}✓ {finish_time_str}{C_RESET}\n"
        )
        sys.stdout.flush()
    
        stats_inc("total_bytes_sent", file_size)
    
    # ── FIX: Batch Rate Limiting — pause tiap 30 file ──
    if not is_thumb:
        # Delay pendek antar file (2 detik)
        time.sleep(2)
        
                # Cek counter: kalau sudah 30 file, pause lebih lama
        current_count = stats_snapshot().get("item_counter", 0)
        if current_count > 0 and current_count % 30 == 0:
            pause_seconds = 60  # 1 menit
            with _STDOUT_LOCK:
                sys.stdout.write(
                    f"\n  {C_YELLOW}⏸️  Batch {current_count} file selesai. "
                    f"Istirahat dulu boss biar ameh teu ka banned!{C_RESET}\n"
                )
                sys.stdout.flush()
            
            # ── FIX: Hitungan mundur real-time ──
            for remaining in range(pause_seconds, 0, -1):
                # Format waktu: tampilkan MM:SS kalau > 60 detik, atau "X detik" kalau ≤ 60
                if remaining >= 60:
                    mins = remaining // 60
                    secs = remaining % 60
                    time_display = f"{mins}:{secs:02d}"
                else:
                    time_display = f"{remaining} detik"
                
                # Bar visual
                bar_len = 20
                filled = int(bar_len * (pause_seconds - remaining) / pause_seconds)
                bar = f"{C_GREEN}{'█' * filled}{C_GRAY}{'░' * (bar_len - filled)}{C_RESET}"
                
                with _STDOUT_LOCK:
                    sys.stdout.write(
                        f"\r  {C_CYAN}⏳{C_RESET} Lanjut dalam "
                        f"{C_YELLOW}{time_display:>10}{C_RESET}  {bar}  "
                    )
                    sys.stdout.flush()
                
                time.sleep(1)
            
            # Clear baris hitungan mundur
            with _STDOUT_LOCK:
                sys.stdout.write("\r" + " " * 80 + "\r")
                sys.stdout.write(f"  {C_GREEN}▶️  Gas! Lanjut upload...{C_RESET}\n\n")
                sys.stdout.flush()
            # ── END FIX ──
    # ── END FIX ──
    
    return result_url
def verify_uploaded_file(url, original_size, tolerance=0.05):
    """
    Verifikasi file yang diupload punya ukuran yang wajar.
    Catbox kadang kompres file untuk anonymous user.
    """
    try:
        r = requests.head(url, timeout=10, allow_redirects=True)
        remote_size = int(r.headers.get("Content-Length", 0))
        
        if remote_size == 0:
            return True, "size unknown"
        
        ratio = remote_size / original_size
        if ratio < (1 - tolerance):
            return False, f"file dikompres: {original_size} -> {remote_size} bytes ({ratio*100:.0f}%)"
        
        return True, "OK"
    except Exception as e:
        return True, f"verify gagal: {e}"

def _convert_to_degrees(value):
    try:
        d = float(value[0]); m = float(value[1]); s = float(value[2])
        return d + (m / 60.0) + (s / 3600.0)
    except Exception:
        return None


def _ref_str(v):
    if v is None:
        return ""
    if isinstance(v, bytes):
        v = v.decode("utf-8", errors="ignore")
    return str(v).strip().upper()


def _merge_exif_ifds(exif_obj, exif_dict):
    merged = dict(exif_dict) if exif_dict else {}
    try:
        if IFD is not None and exif_dict:
            for name in ("ExifIFD", "GPSInfo"):
                ifd_id = getattr(IFD, name, None)
                if ifd_id is None:
                    continue
                sub = exif_dict.get(ifd_id)
                if isinstance(sub, dict):
                    merged.update(sub)
    except Exception:
        pass
    try:
        if exif_obj is not None and hasattr(exif_obj, "get_ifd"):
            for ifd_id in (0x8769, 0x8825):
                try:
                    sub = exif_obj.get_ifd(ifd_id)
                    if sub:
                        merged.update(sub)
                except Exception:
                    pass
    except Exception:
        pass
    return merged


def extract_detailed_exif(file_path):
    result = {"geo": None, "original_date": None, "camera_make": None, "camera_model": None,
              "lens_model": None, "f_number": None, "exposure_time": None, "iso": None,
              "focal_length": None, "dimensions": None}
    if not PILLOW_AVAILABLE:
        return result
    if file_path.suffix.lower() not in {".jpg", ".jpeg", ".tiff", ".webp", ".png"}:
        return result
    try:
        with Image.open(file_path) as img:
            result["dimensions"] = img.size
            exif_obj = None
            exif = None
            try:
                exif_obj = img.getexif()
            except Exception:
                exif_obj = None
            try:
                exif = img._getexif() if hasattr(img, "_getexif") else None
            except Exception:
                exif = None
            merged = _merge_exif_ifds(exif_obj, exif)
            if not merged:
                return result
            gps_info = {}
            for tag_id, val in merged.items():
                tag_name = TAGS.get(tag_id, tag_id)
                if tag_name == "DateTimeOriginal":
                    try:
                        result["original_date"] = datetime.strptime(str(val), "%Y:%m:%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        pass
                elif tag_name == "DateTime" and not result["original_date"]:
                    try:
                        result["original_date"] = datetime.strptime(str(val), "%Y:%m:%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        pass
                elif tag_name == "Make":
                    result["camera_make"] = str(val).strip()
                elif tag_name == "Model":
                    result["camera_model"] = str(val).strip()
                elif tag_name == "LensModel":
                    result["lens_model"] = str(val).strip()
                elif tag_name == "FNumber":
                    try:
                        result["f_number"] = f"f/{float(val):.1f}"
                    except Exception:
                        pass
                elif tag_name == "ExposureTime":
                    try:
                        fval = float(val)
                        result["exposure_time"] = f"1/{int(round(1 / fval))}s" if fval < 1 else f"{fval}s"
                    except Exception:
                        result["exposure_time"] = str(val)
                elif tag_name == "ISOSpeedRatings":
                    result["iso"] = f"ISO {val}"
                elif tag_name == "FocalLength":
                    try:
                        result["focal_length"] = f"{float(val):.1f}mm"
                    except Exception:
                        pass
                elif tag_name == "GPSInfo":
                    for key, sub in (val.items() if isinstance(val, dict) else []):
                        gps_info[GPSTAGS.get(key, key)] = sub
            if gps_info:
                lat = _convert_to_degrees(gps_info.get("GPSLatitude"))
                lon = _convert_to_degrees(gps_info.get("GPSLongitude"))
                if lat is not None and lon is not None:
                    if _ref_str(gps_info.get("GPSLatitudeRef")) == "S":
                        lat = -lat
                    if _ref_str(gps_info.get("GPSLongitudeRef")) == "W":
                        lon = -lon
                    result["geo"] = {"lat": round(lat, 6), "lon": round(lon, 6)}
    except Exception:
        pass
    return result


def generate_video_thumbnail(video_path):
    if not FFMPEG_PATH:
        return None
    try:
        temp_dir = tempfile.gettempdir()
        thumb_name = f"thumb_{hashlib.md5(str(video_path).encode()).hexdigest()[:12]}.jpg"
        thumb_path = os.path.join(temp_dir, thumb_name)
        if os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0:
            return thumb_path
        cmd = [FFMPEG_PATH, "-y", "-ss", "0.5", "-i", str(video_path), "-vframes", "1",
               "-vf", f"scale='min({THUMB_MAX_SIZE},iw)':-2", "-q:v", "3", thumb_path]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        if os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0:
            return thumb_path
        return None
    except Exception:
        return None


def generate_image_thumbnail(image_path):
    if not PILLOW_AVAILABLE:
        return None
    ext = Path(image_path).suffix.lower()
    if ext in {".svg", ".ico"}:
        return None
    try:
        os.makedirs(THUMBNAIL_DIR, exist_ok=True)
        stat = os.stat(image_path)
        key = hashlib.md5(f"{image_path}|{stat.st_mtime_ns}|{stat.st_size}".encode("utf-8")).hexdigest()[:20]
        out_path = os.path.join(THUMBNAIL_DIR, f"{key}.webp")
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            return out_path
        with Image.open(image_path) as img:
            if getattr(img, "is_animated", False):
                img.seek(0)
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGBA")
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1])
                img = bg
            else:
                img = img.convert("RGB")
            img.thumbnail((THUMB_MAX_SIZE, THUMB_MAX_SIZE), Image.Resampling.LANCZOS)
            img.save(out_path, "WEBP", quality=THUMB_QUALITY, method=4)
        return out_path
    except Exception:
        return None


def cleanup_old_thumbnails(max_age_days=THUMB_CLEANUP_MAX_AGE_DAYS):
    if not os.path.isdir(THUMBNAIL_DIR):
        return
    cutoff = time.time() - max_age_days * 86400
    removed = 0
    for f in os.listdir(THUMBNAIL_DIR):
        p = os.path.join(THUMBNAIL_DIR, f)
        try:
            if os.path.isfile(p) and os.path.getmtime(p) < cutoff:
                os.remove(p)
                removed += 1
        except Exception:
            pass
    temp_dir = tempfile.gettempdir()
    for f in os.listdir(temp_dir):
        if f.startswith("thumb_") and f.endswith(".jpg"):
            p = os.path.join(temp_dir, f)
            try:
                if os.path.isfile(p) and os.path.getmtime(p) < cutoff:
                    os.remove(p)
                    removed += 1
            except Exception:
                pass
    if removed:
        print(f"{C_GRAY}[i] Cleanup thumbnail: {removed} file lama dihapus.{C_RESET}")


_STOP_WORDS = {
    "img", "vid", "video", "photo", "pic", "picture", "image", "images",
    "dsc", "dscf", "dscn", "screenshot", "screen", "shot", "capture",
    "transformed", "upscale", "upscaled", "upscalemedia", "enhanced",
    "wallpaper", "background", "bg", "hd", "fhd", "uhd", "4k", "1080",
    "general", "copy", "final", "edit", "edited", "output", "result",
    "download", "downloaded", "saved", "new", "old", "temp", "tmp",
    "untitled", "unnamed", "file", "files", "doc", "document",
    "wa", "whatsapp", "fb", "facebook", "ig", "instagram", "tw", "twitter",
    "tiktok", "yt", "youtube", "telegram", "line", "snapchat",
    "official", "verified", "story", "reels", "shorts", "post",
    "app", "camera", "pix", "pixel", "snapseed", "lightroom", "photoshop",
    "canva", "picsart", "vscocam", "vsco", "meitu", "beautyplus",
    "remastered", "remaster", "heic", "jpeg", "jpg", "png", "webp",
    "and", "the", "for", "with", "from", "into", "onto", "over", "under",
    "this", "that", "these", "those", "here", "there", "when", "where",
    "what", "which", "who", "why", "how", "also", "just", "only", "very",
    "more", "most", "less", "least", "many", "much", "some", "any",
    "all", "each", "every", "both", "either", "neither", "none",
    "yang", "dan", "atau", "untuk", "dengan", "dari", "ke", "di", "pada",
    "adalah", "akan", "sudah", "telah", "sedang", "masih", "belum",
    "ini", "itu", "sini", "sana", "mana", "kapan", "siapa", "apa",
    "juga", "saja", "hanya", "sangat", "lebih", "paling", "kurang",
    "banyak", "sedikit", "semua", "setiap", "beberapa", "para",
    "format", "size", "version", "beta", "alpha", "stable", "preview",
    "thumbnail", "thumb", "sample", "test", "demo",
    "audio", "media", "content",
    "red", "green", "blue", "yellow", "black", "white", "pink",
    "purple", "orange", "brown", "gray", "grey",
    "px", "mp", "kb", "mb", "gb", "tb",
    "usb", "hdr", "gps", "iso", "raw", "exif", "mp4", "mov", "mkv",
}

_BRAND_CASE = {
    "iphone": "iPhone", "ipad": "iPad", "ipod": "iPod",
    "gopro": "GoPro", "dji": "DJI", "sony": "Sony",
    "canon": "Canon", "nikon": "Nikon", "fujifilm": "Fujifilm",
    "panasonic": "Panasonic", "olympus": "Olympus", "leica": "Leica",
    "samsung": "Samsung", "xiaomi": "Xiaomi", "oppo": "OPPO",
    "vivo": "vivo", "realme": "realme", "huawei": "Huawei",
    "oneplus": "OnePlus", "google": "Google", "pixel": "Pixel",
    "adobe": "Adobe", "lightroom": "Lightroom",
    "android": "Android", "ios": "iOS",
}


def _clean_token(tok):
    if not tok:
        return None
    t = tok.strip()
    if len(t) < 3:
        return None
    if t.isdigit():
        return None
    if re.match(r"^[a-f0-9]{8,}$", t, re.IGNORECASE):
        return None
    if re.match(r"^[a-z]{1,3}\d{4,}$", t, re.IGNORECASE):
        return None
    if re.match(r"^(19|20)\d{6,}$", t):
        return None
    if re.match(r"^[a-f0-9]{4}-[a-f0-9]{4}", t, re.IGNORECASE):
        return None
    if t.lower() in _STOP_WORDS:
        return None
    return t


def _normalize_case(tok):
    low = tok.lower()
    if low in _BRAND_CASE:
        return _BRAND_CASE[low]
    if tok.isupper() and len(tok) <= 5:
        return tok
    return tok[0].upper() + tok[1:].lower() if len(tok) > 1 else tok.upper()


_MONTH_NAMES_ID_FULL = [
    "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]

_DATE_PATTERNS = [
    (r"(20\d{2})[-_.]?(\d{2})[-_.]?(\d{2})[_\-\s](\d{2})[-_.]?(\d{2})[-_.]?(\d{2})", "ymd_hms"),  # ← BARU
    (r"(20\d{2})[-_.](\d{1,2})[-_.](\d{1,2})", "ymd"),
    (r"(\d{1,2})[-_.](\d{1,2})[-_.](20\d{2})", "dmy"),
    (r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)", "ymd"),
    (r"(?<!\d)(\d{2})(\d{2})(20\d{2})(?!\d)", "dmy"),
    (r"(20\d{2})[-_.](\d{1,2})(?![-_.]\d)", "ym"),
]


def extract_date_from_filename(filename):
    stem = Path(filename).stem
    for pattern, order in _DATE_PATTERNS:
        m = re.search(pattern, stem)
        if not m:
            continue
        try:
            if order == "ymd_hms":
                # Format: YYYYMMDD_HHMMSS atau YYYY-MM-DD_HH-MM-SS
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                hh, mm, ss = int(m.group(4)), int(m.group(5)), int(m.group(6))
            elif order == "ymd":
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                hh, mm, ss = 0, 0, 0
            elif order == "dmy":
                d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
                hh, mm, ss = 0, 0, 0
            elif order == "ym":
                y, mo = int(m.group(1)), int(m.group(2))
                d, hh, mm, ss = 1, 0, 0, 0
            else:
                continue
            if not (2000 <= y <= 2099): continue
            if not (1 <= mo <= 12): continue
            if not (1 <= d <= 31): continue
            if not (0 <= hh <= 23): continue
            if not (0 <= mm <= 59): continue
            if not (0 <= ss <= 59): continue
            return {
                "year": y, "month": mo, "day": d,
                "hour": hh, "minute": mm, "second": ss,
                "date_str": f"{y:04d}-{mo:02d}-{d:02d}",
                "datetime_str": f"{y:04d}-{mo:02d}-{d:02d} {hh:02d}:{mm:02d}:{ss:02d}",
                "month_display": f"{_MONTH_NAMES_ID_FULL[mo]} {y}",
                "month_key": f"{y:04d}-{mo:02d}",
            }
        except (ValueError, IndexError):
            continue
    return None


_OCR_STOP_WORDS = {
    "the", "and", "for", "with", "from", "this", "that", "have", "has",
    "are", "was", "were", "will", "would", "could", "should", "can",
    "you", "your", "our", "their", "his", "her", "its", "it's",
    "but", "not", "all", "any", "some", "each", "every",
    "dan", "atau", "untuk", "dengan", "dari", "yang", "ini", "itu",
    "ada", "akan", "sudah", "telah", "juga", "saja", "hanya",
    "http", "https", "www", "com", "net", "org",
}


def extract_text_from_image(image_path, max_words=5):
    if not TESSERACT_AVAILABLE or not PILLOW_AVAILABLE:
        return []
    try:
        with Image.open(image_path) as img:
            if getattr(img, "is_animated", False):
                img.seek(0)
            img = img.convert("RGB")
            if max(img.size) < 800:
                scale = max(2, 1200 // max(img.size))
                img = img.resize((img.width * scale, img.height * scale), Image.LANCZOS)
            text = pytesseract.image_to_string(img, lang="ind+eng", config="--psm 3")
        words = re.findall(r"[A-Za-z]{3,}", text)
        seen = set()
        result = []
        for w in words:
            wl = w.lower()
            if wl in _OCR_STOP_WORDS or wl in seen:
                continue
            if wl.isdigit():
                continue
            seen.add(wl)
            result.append(w.capitalize())
            if len(result) >= max_words:
                break
        return result
    except Exception:
        return []


_FACE_CASCADE = None
_FACE_DETECTION_LOCK = threading.Lock()


def detect_faces(image_path):
    global _FACE_CASCADE
    if not CV2_AVAILABLE:
        return 0
    try:
        with _FACE_DETECTION_LOCK:
            if _FACE_CASCADE is None:
                cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                _FACE_CASCADE = cv2.CascadeClassifier(cascade_path)
        img = cv2.imread(str(image_path))
        if img is None:
            return 0
        if max(img.shape[:2]) > 1200:
            scale = 1200 / max(img.shape[:2])
            img = cv2.resize(img, None, fx=scale, fy=scale)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        faces = _FACE_CASCADE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        return len(faces) if faces is not None else 0
    except Exception:
        return 0


def detect_simple_objects(image_path):
    """
    Deteksi warna dominan & brightness dari gambar.
    FIX: Kompatibel dengan Pillow baru (get_flattened_data) & lama (getdata).
    """
    if not PILLOW_AVAILABLE:
        return []
    try:
        with Image.open(image_path) as img:
            if getattr(img, "is_animated", False):
                img.seek(0)
            
            img = img.convert("RGB")
            
            if max(img.size) > 400:
                img.thumbnail((400, 400), Image.Resampling.LANCZOS)
            
            # FIX: Coba method baru dulu, fallback ke lama
            try:
                pixels = list(img.get_flattened_data())
            except AttributeError:
                pixels = list(img.getdata())
            
            total = len(pixels)
            if total == 0:
                return []
            
            # FIX: Sampling untuk gambar besar (hemat CPU)
            MAX_SAMPLES = 10000
            if total > MAX_SAMPLES:
                step = total // MAX_SAMPLES
                pixels = pixels[::step]
                total = len(pixels)
            
            r_sum = sum(p[0] for p in pixels) / total
            g_sum = sum(p[1] for p in pixels) / total
            b_sum = sum(p[2] for p in pixels) / total
            brightness = (r_sum + g_sum + b_sum) / 3
            
            tags = []
            if r_sum > g_sum + 40 and r_sum > b_sum + 40:
                tags.append("Merah")
            elif g_sum > r_sum + 30 and g_sum > b_sum + 30:
                tags.append("Hijau")
            elif b_sum > r_sum + 40 and b_sum > g_sum + 30:
                tags.append("Biru")
            
            if brightness < 50:
                tags.append("Gelap")
            elif brightness > 200:
                tags.append("Terang")
            
            max_c = max(r_sum, g_sum, b_sum)
            min_c = min(r_sum, g_sum, b_sum)
            if max_c - min_c < 20:
                if brightness > 180:
                    tags.append("Putih")
                elif brightness < 80:
                    tags.append("Hitam")
                else:
                    tags.append("Abu-abu")
            
            return tags
    except Exception:
        return []


def extract_auto_tags(file_path, category, exif_meta=None, media_type="image"):
    collected = []
    seen_lower = set()

    def add(tag, priority=5):
        if not tag:
            return
        t = str(tag).strip()
        if not t or len(t) < 2:
            return
        low = t.lower()
        if low in seen_lower or low in _STOP_WORDS:
            return
        seen_lower.add(low)
        collected.append((priority, t))

    cat_clean = (category or "").strip()
    if cat_clean and cat_clean.lower() not in ("general", ".", ""):
        for part in re.split(r"[\s_\-]+", cat_clean):
            c = _clean_token(part)
            if c:
                add(_normalize_case(c), priority=2)

    date_info = extract_date_from_filename(file_path.name)
    if date_info:
        add(date_info["month_display"], priority=2)
        add(str(date_info["year"]), priority=3)

    if exif_meta:
        make = exif_meta.get("camera_make")
        model = exif_meta.get("camera_model")
        if make:
            m = _clean_token(make.split()[0] if make.split() else make)
            if m:
                add(_normalize_case(m), priority=1)
        if model:
            for part in re.split(r"[\s_\-]+", model):
                p = _clean_token(part)
                if p and (not make or p.lower() not in make.lower()):
                    add(_normalize_case(p), priority=1)
                    break
        dims = exif_meta.get("dimensions")
        if dims and isinstance(dims, (tuple, list)):
            w, h = dims
            if w > h:
                add("Landscape", priority=4)
            elif h > w:
                add("Portrait", priority=4)
            elif w == h and w > 0:
                add("Square", priority=4)
        if exif_meta.get("geo"):
            add("Geotagged", priority=3)

    if media_type == "image" and CV2_AVAILABLE:
        try:
            fc = detect_faces(file_path)
            if fc >= 1:
                add("Wajah", priority=3)
                add("Orang", priority=3)
            if fc >= 2:
                add("Grup", priority=3)
        except Exception:
            pass

    if media_type == "image":
        try:
            for ot in detect_simple_objects(file_path):
                add(ot, priority=6)
        except Exception:
            pass

    if media_type == "image" and TESSERACT_AVAILABLE:
        try:
            for w in extract_text_from_image(file_path, max_words=4):
                add(w, priority=7)
        except Exception:
            pass

    raw_name = file_path.stem
    cleaned = re.sub(r"(IMG|VID|WA|FB_IMG|Screenshot|Screen_Shot|PXL|DSC|DSCF|DSCN|GOPR|lv_\d+)[_\-\s]*", " ", raw_name, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(19|20)\d{6,}\b", " ", cleaned)
    cleaned = re.sub(r"\b\d{4}[-_]\d{2}[-_]\d{2}\b", " ", cleaned)
    cleaned = re.sub(r"\b\d{2}[-_]\d{2}[-_]\d{4}\b", " ", cleaned)
    cleaned = re.sub(r"[_\-–—\.\(\)\[\]\{\}\+\#\@\&\|/,;:]+", " ", cleaned)
    for t in re.findall(r"[A-Za-z][A-Za-z0-9]+", cleaned):
        c = _clean_token(t)
        if c:
            add(_normalize_case(c), priority=5)

    collected.sort(key=lambda x: (x[0], x[1].lower()))
    return [tag for _, tag in collected[:10]]


def _cache_meta_is_valid(entry, stat):
    if not isinstance(entry, dict):
        return False
    if entry.get("file_mtime_ns") != stat.st_mtime_ns:
        return False
    if entry.get("file_size") != stat.st_size:
        return False
    return "meta" in entry


def process_single_file(file_p, photos_path, cache):
    rel_path = str(file_p.relative_to(photos_path)).replace("\\", "/")
    folder_category = file_p.parent.relative_to(photos_path).as_posix()
    if folder_category == ".":
        folder_category = "General"
    stat = file_p.stat()
    file_mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))
    ext = file_p.suffix.lower().replace(".", "").upper()
    cached_entry = cache.get(rel_path)
    catbox_url = None
    video_thumb_url = None
    thumb_url = None
    upload_time = None
    cached_meta = None
    if isinstance(cached_entry, dict):
        catbox_url = cached_entry.get("url")
        video_thumb_url = cached_entry.get("video_thumb_url")
        thumb_url = cached_entry.get("thumb_url")
        upload_time = cached_entry.get("uploaded_at")
        if _cache_meta_is_valid(cached_entry, stat):
            cached_meta = cached_entry.get("meta")
    elif isinstance(cached_entry, str):
        catbox_url = cached_entry
    if catbox_url and VERIFY_CACHED_URLS and not check_url_active(catbox_url):
        catbox_url = None
    if not catbox_url:
        try:
            catbox_url = upload_to_catbox(file_p, label=file_p.name, is_thumb=False)
            upload_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            stats_inc("success_uploads")
            
            # ── FIX: Verifikasi ukuran file di Catbox ──
            ok, msg = verify_uploaded_file(catbox_url, stat.st_size)
            if not ok:
                with _STDOUT_LOCK:
                    sys.stdout.write(f"      {C_YELLOW}└─ ⚠️  {msg}{C_RESET}\n")
                    sys.stdout.flush()
                cache.pop(rel_path, None)
                stats_inc("failed_uploads")
                return None
            # ── END FIX ──
        
        except Exception as e:
            stats_inc("failed_uploads")
            # FIX: Error logging lebih detail
            with _STDOUT_LOCK:
                sys.stdout.write(f"  {C_YELLOW}⚠️  {C_RESET}  Gagal: {file_p.name}\n")
                sys.stdout.write(f"      {C_GRAY}└─ {type(e).__name__}: {str(e)[:200]}{C_RESET}\n")
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        body = e.response.text[:300]
                        sys.stdout.write(
                            f"      {C_GRAY}└─ HTTP {e.response.status_code}: {body}{C_RESET}\n"
                        )
                    except Exception:
                        pass
                sys.stdout.flush()
            return None
    else:
        stats_inc("cached_count")
        idx = stats_next_counter()
        total = stats_snapshot()["total_scanned"]
        icon = _MEDIA_ICONS["video"] if ext in VIDEO_EXTS else _MEDIA_ICONS["image"]
        with _STDOUT_LOCK:
            print(f"  {icon}  {C_PURPLE}[{idx}/{total}]{C_RESET}  {C_GRAY}CACHE{C_RESET}  {C_WHITE}{short_label(file_p.name, 42)}{C_RESET}  {C_GRAY}⤷  {format_bytes_adaptive(stat.st_size)}{C_RESET}  {C_GREEN}⚡{C_RESET}")
    media_type = "video" if ext in VIDEO_EXTS else "image"
    if media_type == "video" and not video_thumb_url:
        local_thumb = generate_video_thumbnail(file_p)
        if local_thumb and os.path.exists(local_thumb):
            try:
                video_thumb_url = upload_to_catbox(local_thumb, label=f"thumb_{file_p.stem[:12]}.jpg", is_thumb=True)
            except Exception:
                video_thumb_url = None
    if media_type == "image" and UPLOAD_IMAGE_THUMBNAILS and not thumb_url:
        local_thumb = generate_image_thumbnail(file_p)
        if local_thumb and os.path.exists(local_thumb):
            try:
                thumb_url = upload_to_catbox(local_thumb, label=f"thumb_{file_p.stem[:12]}.webp", is_thumb=True)
            except Exception:
                thumb_url = None
    if cached_meta is not None:
        exif_meta = cached_meta.get("exif", {})
        auto_tags = cached_meta.get("tags", [])
        media_date = cached_meta.get("date", file_mtime)
        year_str = cached_meta.get("year", "1970")
        year_month = cached_meta.get("month_key", "1970-01")
        month_display = cached_meta.get("month_display", "")
    else:
        exif_meta = extract_detailed_exif(file_p) if media_type == "image" else {}
        date_from_name = extract_date_from_filename(file_p.name)
        if exif_meta.get("original_date"):
            media_date = exif_meta["original_date"]
        elif date_from_name:
            # Pakai datetime kalau ada jam, atau tanggal saja kalau tidak
            if date_from_name.get("hour", 0) or date_from_name.get("minute", 0) or date_from_name.get("second", 0):
                media_date = date_from_name["datetime_str"]
            else:
                media_date = date_from_name["date_str"]
        else:
            media_date = file_mtime
        date_parts = media_date.split(" ")[0].split("-")
        year_str = date_parts[0]
        month_idx = int(date_parts[1]) if len(date_parts) > 1 else 1
        year_month = f"{year_str}-{date_parts[1]:0>2}" if len(date_parts) > 1 else f"{year_str}-01"
        month_name = MONTH_NAMES_ID[month_idx] if 1 <= month_idx <= 12 else ""
        month_display = f"{month_name} {year_str}".strip()
        auto_tags = extract_auto_tags(file_p, folder_category, exif_meta, media_type)
    effective_thumb_url = thumb_url
    if media_type == "image":
        effective_thumb_url = thumb_url or f"https://wsrv.nl/?url={catbox_url}&w={THUMB_MAX_SIZE}&q=80&output=webp"
    else:
        effective_thumb_url = video_thumb_url or thumb_url or ""
    cache_record = {
        "url": catbox_url,
        "uploaded_at": upload_time or file_mtime,
        "video_thumb_url": video_thumb_url,
        "thumb_url": thumb_url,
        "file_mtime_ns": stat.st_mtime_ns,
        "file_size": stat.st_size,
        "meta": {
            "exif": exif_meta or {},
            "tags": auto_tags or [],
            "date": media_date,
            "year": year_str,
            "month_key": year_month,
            "month_display": month_display,
        },
    }
    media_id = f"media_{hashlib.md5(rel_path.encode('utf-8')).hexdigest()[:12]}"
    item_data = {
        "id": media_id,
        "title": file_p.stem.replace("_", " ").title(),
        "filename": file_p.name,
        "category": folder_category,
        "date": media_date,
        "uploaded_at": upload_time,
        "year": year_str,
        "month_key": year_month,
        "month_display": month_display,
        "size": stat.st_size,
        "ext": ext,
        "type": media_type,
        "url": catbox_url,
        "thumb": effective_thumb_url,
        "video_thumb": video_thumb_url,
        "video_mime": VIDEO_MIME.get(ext, "") if media_type == "video" else None,
        "geo": (exif_meta or {}).get("geo"),
        "camera": {
            "make": (exif_meta or {}).get("camera_make"),
            "model": (exif_meta or {}).get("camera_model"),
            "lens": (exif_meta or {}).get("lens_model"),
            "f_number": (exif_meta or {}).get("f_number"),
            "exposure": (exif_meta or {}).get("exposure_time"),
            "iso": (exif_meta or {}).get("iso"),
            "focal": (exif_meta or {}).get("focal_length"),
        },
        "tags": auto_tags,
    }
    return rel_path, cache_record, item_data


def get_uploader_info():
    info = {"ip": "—", "location": "—", "isp": "—", "vpn": None, "ok": False}
    try:
        r = requests.get(
            "https://ip-api.com/json/?fields=status,message,country,countryCode,regionName,city,isp,org,as,proxy,hosting,query",
            timeout=8, headers={"User-Agent": "Mozilla/5.0"},
        )
        if r.status_code == 200:
            d = r.json()
            if d.get("status") == "success":
                info["ip"] = d.get("query") or "—"
                parts = [d.get("city"), d.get("regionName"), d.get("country")]
                info["location"] = ", ".join([p for p in parts if p]) or "—"
                info["isp"] = d.get("isp") or d.get("org") or "—"
                info["vpn"] = bool(d.get("proxy", False) or d.get("hosting", False))
                info["ok"] = True
    except Exception:
        pass
    return info


def print_summary_report():
    s = stats_snapshot()
    duration = max(1, int(s["end_time"] - s["start_time"]))
    mins, secs = divmod(duration, 60)
    dur_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
    speed_bps = s["total_bytes_sent"] / duration
    speed_str = f"{format_bytes_adaptive(speed_bps)}/s"
    
    # ── FIX: Info waktu ──
    start_str = time.strftime("%H:%M:%S", time.localtime(s["start_time"])) if s["start_time"] else "—"
    end_str = time.strftime("%H:%M:%S", time.localtime(s["end_time"])) if s["end_time"] else "—"
    # ── END FIX ──
    
    print("\n" + "=" * 54)
    print(f"        {C_CYAN}{C_BOLD}📊 ATOS BERES BOSS!{C_RESET}")
    print("=" * 54)
    print(f" 📂 Total File Terdeteksi   : {C_WHITE}{s['total_scanned']} file{C_RESET}")
    print(f" ⚡ Menggunakan Cache       : {C_GRAY}{s['cached_count']} file (Lewati){C_RESET}")
    print(f" ✅ Berhasil Diupload       : {C_GREEN}{s['success_uploads']} file{C_RESET}")
    print(f" ❌ Gagal Diupload          : {s['failed_uploads']} file")
    print("-" * 54)
    # ── FIX: Baris waktu ──
    print(f" 🕐 Mulai                   : {C_CYAN}{start_str}{C_RESET}")
    print(f" 🕐 Selesai                 : {C_CYAN}{end_str}{C_RESET}")
    print(f" ⏱️  Durasi                  : {C_YELLOW}{dur_str}{C_RESET}")
    print("-" * 54)
    # ── END FIX ──
    print(f" 🌐 Kuota Internet Dipakai  : {C_CYAN}{format_bytes_adaptive(s['total_bytes_sent'])}{C_RESET}")
    print(f" 🚀 Rata-rata Kecepatan     : {C_YELLOW}{speed_str}{C_RESET}")
    print("-" * 54)
    # ... sisa tetap sama ...


def scan_and_upload():
    cache = load_cache()
    photos_path = Path(PHOTOS_DIR)
    cleanup_old_thumbnails()
    if not photos_path.exists():
        os.makedirs(photos_path, exist_ok=True)
        print(f"[*] Folder '{PHOTOS_DIR}' dibuat. Silakan letakkan subfolder media di dalamnya.")
        return []
    
    files_to_process = [
        p for p in photos_path.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    total_files = len(files_to_process)
    
    # ── FIX: Reset SEMUA stat counter di awal run ──
    with _STATS_LOCK:
        SESSION_STATS["total_scanned"] = total_files
        SESSION_STATS["success_uploads"] = 0
        SESSION_STATS["failed_uploads"] = 0
        SESSION_STATS["cached_count"] = 0
        SESSION_STATS["total_bytes_sent"] = 0
        SESSION_STATS["start_time"] = time.time()
        SESSION_STATS["end_time"] = 0
        SESSION_STATS["item_counter"] = 0
    # ── END FIX ──
    
        # ── FIX: Header info lengkap (Bahasa Indonesia) ──
    HARI_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    BULAN_ID = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
                "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    
    now = time.localtime()
    start_time_str = time.strftime("%H:%M:%S", now)
    hari_str = HARI_ID[now.tm_wday]
    tanggal_str = f"{hari_str}, {now.tm_mday} {BULAN_ID[now.tm_mon]} {now.tm_year}"
    
    # Hitung total ukuran semua file
    total_bytes = sum(p.stat().st_size for p in files_to_process if p.is_file())
    total_size_str = format_bytes_adaptive(total_bytes)
    
    # Info fitur aktif
    fitur_ocr = f"{C_GREEN}✓{C_RESET}" if TESSERACT_AVAILABLE else f"{C_GRAY}✗{C_RESET}"
    fitur_wajah = f"{C_GREEN}✓{C_RESET}" if CV2_AVAILABLE else f"{C_GRAY}✗{C_RESET}"
    fitur_thumb = f"{C_GREEN}✓{C_RESET}" if UPLOAD_IMAGE_THUMBNAILS else f"{C_GRAY}✗{C_RESET}"
    
    print(f"{C_GREEN}Reading package lists... Done{C_RESET}")
    print(f"{C_GREEN}Building dependency tree... Done{C_RESET}")
    print()
    print(f"{C_PURPLE}╭─────────────────────────────────────────────────────╮{C_RESET}")
    print(f"{C_PURPLE}│{C_RESET}  {C_CYAN}{C_BOLD}🕐 MULAI UPLOAD{C_RESET}")
    print(f"{C_PURPLE}╰─────────────────────────────────────────────────────╯{C_RESET}")
    print(f"  {C_CYAN}🕐 Waktu    :{C_RESET} {C_WHITE}{start_time_str}{C_RESET}")
    print(f"  {C_CYAN}📅 Tanggal  :{C_RESET} {C_WHITE}{tanggal_str}{C_RESET}")
    print(f"  {C_CYAN}📂 Folder   :{C_RESET} {C_WHITE}{PHOTOS_DIR}{C_RESET}")
    print(f"  {C_CYAN}🎨 Project  :{C_RESET} {C_WHITE}{PROJECT_TITLE}{C_RESET}")
    print(f"  {C_CYAN}👷 Workers  :{C_RESET} {C_WHITE}{MAX_WORKERS}{C_RESET}")
    print(f"  {C_CYAN}📊 Total    :{C_RESET} {C_WHITE}{total_files} file{C_RESET} {C_GRAY}({total_size_str}){C_RESET}")
    print(f"  {C_CYAN}💡 Fitur    :{C_RESET} OCR {fitur_ocr}  Wajah {fitur_wajah}  Thumbnail {fitur_thumb}")
    print()
    print_banner()
    # ── END FIX ──
    if not TOOLBELT_AVAILABLE:
        print(f"{C_YELLOW}[!] requests-toolbelt tidak terinstall.{C_RESET}")
    if not FFMPEG_PATH:
        print(f"{C_YELLOW}[!] ffmpeg tidak ditemukan.{C_RESET}")
    if TESSERACT_AVAILABLE:
        print(f"{C_GREEN}[✓] OCR aktif (Tesseract).{C_RESET}")
    else:
        print(f"{C_GRAY}[ ] OCR nonaktif. Install: pkg install tesseract{C_RESET}")
    if CV2_AVAILABLE:
        print(f"{C_GREEN}[✓] Deteksi wajah aktif (OpenCV).{C_RESET}")
    else:
        print(f"{C_GRAY}[ ] Deteksi wajah nonaktif. Install: pip install opencv-python-headless{C_RESET}")
    print(f"{C_GREEN}[✓] Deteksi tanggal dari nama file aktif.{C_RESET}")
    print()
    gallery_data = []
    cache_dirty = False
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_single_file, fp, photos_path, cache) for fp in files_to_process]
        for fut in as_completed(futures):
            res = fut.result()
            if res:
                rel_path, cache_record, item_data = res
                cache[rel_path] = cache_record
                gallery_data.append(item_data)
                cache_dirty = True
    if cache_dirty:
        save_cache(cache)
    SESSION_STATS["end_time"] = time.time()
    print_summary_report()
    gallery_data.sort(key=lambda x: x["date"], reverse=True)
    deleted = load_deleted()
    if deleted:
        before = len(gallery_data)
        gallery_data = [item for item in gallery_data if item["id"] not in deleted]
        removed = before - len(gallery_data)
        if removed > 0:
            print(f"{C_GRAY}[i] {removed} item di-skip karena blacklist (deleted.json).{C_RESET}")
    return gallery_data


def apply_config(cfg):
    global PROJECT_TITLE, PHOTOS_DIR, MAX_WORKERS, VERIFY_CACHED_URLS
    global UPLOAD_IMAGE_THUMBNAILS, COUNTER_NAMESPACE, OUTPUT_HTML, OUTPUT_MANAGER, ITEMS_PER_PAGE
    global CATBOX_USERHASH

    PROJECT_TITLE = cfg.get("judul_project", "BARAYAWABELUT")
    CATBOX_USERHASH = cfg.get("userhash", "")
    PHOTOS_DIR = cfg.get("photos_dir", "./media")
    MAX_WORKERS = cfg.get("workers", 1)
    VERIFY_CACHED_URLS = cfg.get("verify_cached_urls", False)
    UPLOAD_IMAGE_THUMBNAILS = cfg.get("upload_thumbnails", True)
    COUNTER_NAMESPACE = cfg.get("counter_namespace", "gallery-pemuda-rawabelut")
    OUTPUT_HTML = cfg.get("output_html", "index.html")
    OUTPUT_MANAGER = cfg.get("output_manager", "manager.html")
    ITEMS_PER_PAGE = cfg.get("items_per_page", 24)


def _escape_json_for_inline_script(obj):
    s = json.dumps(obj, ensure_ascii=False)
    s = s.replace("</", "<\\/")
    s = s.replace("<!--", "<\\!--")
    s = s.replace("*/", "*\\/")
    s = s.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return s


def inject_project_title(html, judul):
    judul_escaped = judul.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    judul_js = json.dumps(judul, ensure_ascii=False)
    html = html.replace("/*PROJECT_TITLE*/", judul_escaped)
    html = html.replace("/*PROJECT_TITLE_JS*/", judul_js)
    html = html.replace("<title>BARAYAWABELUT</title>", f"<title>{judul_escaped}</title>")
    html = html.replace(
        '<h1 id="view-title">BARAYAWABELUT</h1>',
        f'<h1 id="view-title">{judul_escaped}</h1>'
    )
    html = html.replace(
        'cat === "Semua" ? "BARAYAWABELUT" : cat',
        f'cat === "Semua" ? {judul_js} : cat'
    )
    return html

# ============================================================================
# HTML TEMPLATE — PART 1 (CSS)
# ============================================================================

HTML_TEMPLATE_PART1 = r"""<!DOCTYPE html>
<html lang="id" data-theme="dark" data-density="normal">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover" />
<meta name="theme-color" content="#121316" />
<meta name="referrer" content="no-referrer" />
<title>/*PROJECT_TITLE*/</title>
<style>
:root[data-theme="dark"]{
  --bg:#121316; --surface:#1b1c20; --surface-variant:#252830;
  --accent:#58a6ff; --accent-2:#79c0ff; --text:#ffffff; --text-muted:#9aa0a6;
  --border:#2d3139; --header-bg:rgba(18,19,22,.92);
  --shimmer-1:#1f2229; --shimmer-2:#2a2e38;
  --shadow:0 4px 16px rgba(0,0,0,.4);
  --gradient:linear-gradient(135deg,#58a6ff,#a371f7);
}
:root[data-theme="light"]{
  --bg:#f4f6f9; --surface:#ffffff; --surface-variant:#e8ecf2;
  --accent:#0969da; --accent-2:#0550ae; --text:#1f2328; --text-muted:#656d76;
  --border:#d0d7de; --header-bg:rgba(244,246,249,.92);
  --shimmer-1:#e2e5e9; --shimmer-2:#edf0f5;
  --shadow:0 4px 16px rgba(0,0,0,.08);
  --gradient:linear-gradient(135deg,#0969da,#8250df);
}
:root[data-theme="midnight"]{
  --bg:#0a0e1a; --surface:#111827; --surface-variant:#1e293b;
  --accent:#22d3ee; --accent-2:#06b6d4; --text:#e2e8f0; --text-muted:#94a3b8;
  --border:#1e293b; --header-bg:rgba(10,14,26,.92);
  --shimmer-1:#111827; --shimmer-2:#1e293b;
  --shadow:0 4px 20px rgba(34,211,238,.15);
  --gradient:linear-gradient(135deg,#22d3ee,#818cf8);
}
:root[data-theme="sunset"]{
  --bg:#1a0f1e; --surface:#2a1a30; --surface-variant:#3a2440;
  --accent:#f97316; --accent-2:#fb923c; --text:#fff5eb; --text-muted:#c9a9d1;
  --border:#3a2440; --header-bg:rgba(26,15,30,.92);
  --shimmer-1:#2a1a30; --shimmer-2:#3a2440;
  --shadow:0 4px 20px rgba(249,115,22,.2);
  --gradient:linear-gradient(135deg,#f97316,#ec4899,#a855f7);
}
:root[data-theme="forest"]{
  --bg:#0d1a0f; --surface:#14261a; --surface-variant:#1e3626;
  --accent:#4ade80; --accent-2:#22c55e; --text:#ecfdf5; --text-muted:#86a38e;
  --border:#1e3626; --header-bg:rgba(13,26,15,.92);
  --shimmer-1:#14261a; --shimmer-2:#1e3626;
  --shadow:0 4px 20px rgba(74,222,128,.15);
  --gradient:linear-gradient(135deg,#4ade80,#22d3ee);
}
:root[data-theme="rosegold"]{
  --bg:#fdf8f3; --surface:#ffffff; --surface-variant:#fce7e0;
  --accent:#e11d48; --accent-2:#be123c; --text:#3d2b2b; --text-muted:#a08989;
  --border:#f3d7cf; --header-bg:rgba(253,248,243,.92);
  --shimmer-1:#fce7e0; --shimmer-2:#fdf2f0;
  --shadow:0 4px 16px rgba(225,29,72,.12);
  --gradient:linear-gradient(135deg,#e11d48,#f59e0b);
}
:root[data-theme="amoled"]{
  --bg:#000000; --surface:#0a0a0a; --surface-variant:#141414;
  --accent:#ffffff; --accent-2:#cccccc; --text:#ffffff; --text-muted:#888888;
  --border:#1f1f1f; --header-bg:rgba(0,0,0,.95);
  --shimmer-1:#0a0a0a; --shimmer-2:#141414;
  --shadow:0 4px 16px rgba(255,255,255,.08);
  --gradient:linear-gradient(135deg,#ffffff,#888888);
}
:root[data-theme="cyberpunk"]{
  --bg:#0d0221; --surface:#190935; --surface-variant:#2a1055;
  --accent:#ff00aa; --accent-2:#00fff7; --text:#f0e6ff; --text-muted:#9b7eb8;
  --border:#2a1055; --header-bg:rgba(13,2,33,.92);
  --shimmer-1:#190935; --shimmer-2:#2a1055;
  --shadow:0 4px 24px rgba(255,0,170,.3);
  --gradient:linear-gradient(135deg,#ff00aa,#00fff7,#ffea00);
}
:root[data-theme="sepia"]{
  --bg:#f4ecd8; --surface:#faf3e0; --surface-variant:#e8dcc0;
  --accent:#8b4513; --accent-2:#a0522d; --text:#3d2817; --text-muted:#8b7355;
  --border:#d4c4a0; --header-bg:rgba(244,236,216,.92);
  --shimmer-1:#e8dcc0; --shimmer-2:#f0e6cc;
  --shadow:0 4px 16px rgba(139,69,19,.15);
  --gradient:linear-gradient(135deg,#8b4513,#d4a373);
}
:root[data-theme="macos"]{
  --bg:#ececec; --surface:#ffffff; --surface-variant:#f5f5f7;
  --accent:#007aff; --accent-2:#0051d5; --text:#1d1d1f; --text-muted:#86868b;
  --border:#d2d2d7; --header-bg:rgba(236,236,236,.72);
  --shimmer-1:#e8e8ed; --shimmer-2:#f5f5f7;
  --shadow:0 8px 24px rgba(0,0,0,.08);
  --gradient:linear-gradient(135deg,#007aff,#5e5ce6);
}
:root[data-density="compact"]{--item-min:100px;--gap:4px;--pad:4px;--radius:4px;--list-thumb:52px;--title-size:.78rem;}
:root[data-density="normal"]{--item-min:130px;--gap:6px;--pad:8px;--radius:6px;--list-thumb:68px;--title-size:.88rem;}
:root[data-density="comfortable"]{--item-min:180px;--gap:10px;--pad:12px;--radius:10px;--list-thumb:88px;--title-size:.95rem;}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent;}
html{scroll-behavior:smooth;}
body{
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  background-color:var(--bg); color:var(--text); padding-bottom:70px;
  user-select:none; transition:background-color .4s ease, color .4s ease;
}
body.theme-transitioning *{transition:background-color .4s ease, color .4s ease, border-color .4s ease !important;}
::-webkit-scrollbar{width:8px;height:8px;}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:4px;}
::-webkit-scrollbar-thumb:hover{background:var(--accent);}
header{
  position:sticky; top:0; z-index:100;
  background:var(--header-bg); backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px);
  padding:10px 14px; border-bottom:1px solid var(--border);
  transition:background-color .4s ease, border-color .4s ease;
}
.top-bar{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;gap:8px;}
.top-bar .brand{display:flex;flex-direction:column;min-width:0;}
.top-bar h1{font-size:1.15rem;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.top-bar .counter{font-size:.75rem;color:var(--text-muted);}
.top-actions{display:flex;align-items:center;gap:6px;flex-shrink:0;}
.icon-btn{
  background:var(--surface); border:1px solid var(--border); color:var(--text);
  padding:6px 10px; border-radius:8px; font-size:.78rem; cursor:pointer;
  display:flex; align-items:center; gap:4px;
  transition:transform .15s ease, background-color .2s ease, border-color .2s ease;
}
.icon-btn:hover{background:var(--surface-variant);}
.icon-btn:active{transform:scale(.94);}
.search-wrap{position:relative;margin-bottom:8px;}
.search-box{
  width:100%; display:flex; align-items:center;
  background:var(--surface); border:1px solid var(--border);
  border-radius:10px; padding:5px 8px 5px 12px; gap:6px;
  transition:border-color .2s ease, box-shadow .2s ease;
}
.search-box:focus-within{border-color:var(--accent);box-shadow:0 0 0 3px rgba(88,166,255,.15);}
.search-box input{flex:1;background:transparent;border:none;outline:none;color:var(--text);font-size:.88rem;}
.search-box input::placeholder{color:var(--text-muted);}
.suggestions{
  position:absolute; top:100%; left:0; right:0; margin-top:4px;
  background:var(--surface); border:1px solid var(--border);
  border-radius:10px; box-shadow:var(--shadow);
  max-height:280px; overflow-y:auto; z-index:150; display:none;
  animation:suggestIn .18s ease-out;
}
.suggestions.show{display:block;}
@keyframes suggestIn{from{opacity:0;transform:translateY(-4px);}to{opacity:1;transform:translateY(0);}}
.suggestion-item{
  padding:9px 12px; cursor:pointer; display:flex; align-items:center; gap:8px;
  border-bottom:1px solid var(--border); font-size:.82rem;
  transition:background-color .12s ease;
}
.suggestion-item:last-child{border-bottom:none;}
.suggestion-item:hover,.suggestion-item.active{background:var(--surface-variant);}
.suggestion-icon{font-size:.9rem;opacity:.7;}
.suggestion-text{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.suggestion-text mark{background:transparent;color:var(--accent);font-weight:700;}
.suggestion-meta{font-size:.68rem;color:var(--text-muted);}
.active-tag-chip{
  background:rgba(88,166,255,.18); border:1px solid var(--accent); color:var(--accent);
  padding:2px 8px; border-radius:6px; font-size:.72rem;
  display:flex; align-items:center; gap:4px; font-weight:600; cursor:pointer; flex-shrink:0;
}
.search-filter-btn{
  background:var(--surface-variant); border:1px solid var(--border);
  color:var(--text-muted); padding:4px 8px; border-radius:6px;
  font-size:.75rem; cursor:pointer; display:flex; align-items:center; gap:4px;
  transition:.2s; white-space:nowrap; flex-shrink:0;
}
.search-filter-btn.active{background:rgba(88,166,255,.15); border-color:var(--accent); color:var(--accent); font-weight:600;}
.filter-indicator-dot{width:6px;height:6px;border-radius:50%;background:var(--accent);display:none;}
.search-filter-btn.active .filter-indicator-dot{display:inline-block;}
.sub-bar{display:flex;flex-direction:column;gap:6px;}
.filter-row{display:flex;align-items:center;justify-content:space-between;gap:6px;}
.pills-container{display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;flex:1;}
.pills-container::-webkit-scrollbar{display:none;}
.pill{
  white-space:nowrap; padding:4px 10px; border-radius:16px;
  background:var(--surface); border:1px solid var(--border);
  font-size:.73rem; font-weight:500; color:var(--text-muted); cursor:pointer;
  transition:background-color .2s ease, color .2s ease, border-color .2s ease, transform .12s ease;
}
.pill:hover{background:var(--surface-variant);}
.pill:active{transform:scale(.96);}
.pill.active{background:var(--gradient); color:#fff; border-color:transparent; font-weight:600; box-shadow:0 2px 8px rgba(88,166,255,.3);}
.pill-badge{display:inline-block;font-size:.62rem;background:rgba(255,255,255,.2);padding:1px 5px;border-radius:10px;margin-left:4px;}
.controls-row{display:flex;align-items:center;justify-content:space-between;gap:6px;padding-top:2px;flex-wrap:wrap;}
.type-switcher,.view-switcher,.density-switcher{display:flex;background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:2px;}
.sw-btn{background:transparent;border:none;color:var(--text-muted);padding:4px 7px;font-size:.7rem;border-radius:6px;cursor:pointer;transition:background-color .18s ease, color .18s ease;}
.sw-btn:hover{color:var(--text);}
.sw-btn.active{background:var(--surface-variant);color:var(--text);font-weight:600;}
.sort-select{background:var(--surface); border:1px solid var(--border); color:var(--text); padding:4px 8px; border-radius:8px; font-size:.72rem; outline:none; cursor:pointer;}
.gallery-container{padding:var(--pad);}
.layout-mosaic{column-count:2;column-gap:var(--gap);}
@media (min-width:600px){.layout-mosaic{column-count:3;}}
@media (min-width:1024px){.layout-mosaic{column-count:4;}}
@media (min-width:1440px){.layout-mosaic{column-count:5;}}
.layout-mosaic .gallery-item{break-inside:avoid;margin-bottom:var(--gap);border-radius:var(--radius);overflow:hidden;position:relative;cursor:pointer;box-shadow:var(--shadow);min-height:100px;}
.layout-mosaic .gallery-item img,.layout-mosaic .gallery-item video{width:100%;height:auto;display:block;}
.layout-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(var(--item-min),1fr));gap:var(--gap);}
.layout-grid .gallery-item{position:relative;aspect-ratio:1/1;border-radius:var(--radius);overflow:hidden;cursor:pointer;box-shadow:var(--shadow);}
.layout-grid .gallery-item img,.layout-grid .gallery-item video{width:100%;height:100%;object-fit:cover;display:block;}
.layout-list{display:flex;flex-direction:column;gap:var(--gap);}
.layout-list .gallery-item{display:flex;gap:10px;align-items:center;padding:8px;border-radius:var(--radius);border:1px solid var(--border);cursor:pointer;min-height:var(--list-thumb);background:var(--surface);transition:border-color .2s ease, transform .15s ease;}
.layout-list .gallery-item:hover{border-color:var(--accent);}
.layout-list .gallery-item img,.layout-list .gallery-item video{width:var(--list-thumb);height:var(--list-thumb);object-fit:cover;border-radius:6px;flex-shrink:0;display:block;}
.layout-list .list-info{display:flex;flex-direction:column;gap:3px;overflow:hidden;flex:1;}
.layout-list .list-title{font-size:var(--title-size);font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.layout-list .list-meta{font-size:.7rem;color:var(--text-muted);}
.layout-cinema{display:flex;flex-direction:column;gap:var(--gap);}
.layout-cinema .gallery-item{position:relative;width:100%;border-radius:var(--radius);overflow:hidden;cursor:pointer;box-shadow:var(--shadow);max-height:82vh;}
.layout-cinema .gallery-item img,.layout-cinema .gallery-item video{width:100%;height:auto;max-height:82vh;object-fit:contain;display:block;background:#000;}
.layout-cinema .cinema-info{position:absolute;bottom:0;left:0;right:0;padding:18px 16px 14px;background:linear-gradient(to top,rgba(0,0,0,.85) 0%,rgba(0,0,0,.5) 60%,transparent 100%);color:#fff;pointer-events:none;}
.layout-cinema .cinema-title{font-size:1rem;font-weight:700;margin-bottom:4px;}
.layout-cinema .cinema-meta{font-size:.75rem;opacity:.85;}
.layout-magazine{display:grid;gap:var(--gap);grid-template-columns:repeat(2,1fr);grid-auto-rows:minmax(120px,auto);}
@media (min-width:768px){.layout-magazine{grid-template-columns:repeat(4,1fr);}}
.layout-magazine .gallery-item{position:relative;overflow:hidden;border-radius:var(--radius);cursor:pointer;box-shadow:var(--shadow);min-height:120px;}
.layout-magazine .gallery-item img,.layout-magazine .gallery-item video{width:100%;height:100%;object-fit:cover;display:block;}
.layout-magazine .gallery-item.hero{grid-column:span 2;grid-row:span 2;}
.layout-magazine .gallery-item.hero img,.layout-magazine .gallery-item.hero video{min-height:280px;}
.layout-magazine .hero-info{position:absolute;bottom:0;left:0;right:0;padding:14px 12px 10px;background:linear-gradient(to top,rgba(0,0,0,.85),transparent);color:#fff;}
.layout-magazine .hero-title{font-size:.95rem;font-weight:700;}
.layout-seamless{column-count:2;column-gap:0;padding:0;}
@media (min-width:600px){.layout-seamless{column-count:3;}}
@media (min-width:1024px){.layout-seamless{column-count:4;}}
.layout-seamless .gallery-item{break-inside:avoid;margin:0;border-radius:0;overflow:hidden;position:relative;cursor:pointer;min-height:100px;}
.layout-seamless .gallery-item img,.layout-seamless .gallery-item video{width:100%;height:auto;display:block;}
@keyframes shimmer{0%{background-position:-200% 0;}100%{background-position:200% 0;}}
.gallery-item{background:linear-gradient(90deg,var(--shimmer-1) 25%,var(--shimmer-2) 50%,var(--shimmer-1) 75%);background-size:200% 100%;animation:shimmer 1.5s infinite;contain:layout paint style;}
.gallery-item img,.gallery-item video{opacity:0;transition:opacity .5s ease;}
.gallery-item.loaded{animation:none;background:var(--surface);}
.gallery-item.loaded img,.gallery-item.loaded video{opacity:1;}
.reveal-item{opacity:0;transform:translateY(20px);transition:opacity .5s ease, transform .5s cubic-bezier(.2,.7,.2,1);}
.reveal-item.revealed{opacity:1;transform:translateY(0);}
@media (prefers-reduced-motion: reduce){
  .gallery-item,.reveal-item{animation:none !important;transition:none !important;opacity:1 !important;transform:none !important;}
  *{transition:none !important;}
}
.media-wrap{position:relative;width:100%;height:100%;}
.media-video-poster,.media-video-placeholder{min-height:110px;aspect-ratio:16/9;background:var(--surface-variant);}
.media-video-poster img{width:100%;height:100%;object-fit:cover;}
.media-video-placeholder::before{content:"🎬 Video";position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--text-muted);font-size:.85rem;opacity:.8;}
.play-icon-overlay{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.2);pointer-events:none;z-index:5;}
.play-icon-circle{width:44px;height:44px;border-radius:50%;background:rgba(0,0,0,.7);border:1.5px solid rgba(255,255,255,.5);color:#fff;display:flex;align-items:center;justify-content:center;font-size:1.15rem;padding-left:3px;backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);transition:transform .25s ease;}
.gallery-item:hover .play-icon-circle{transform:scale(1.1);}
.badge{position:absolute;bottom:6px;left:6px;background:rgba(0,0,0,.65);backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px);padding:2px 6px;border-radius:4px;font-size:.62rem;color:#fff;}
.video-tag{position:absolute;top:6px;right:6px;background:rgba(0,0,0,.7);backdrop-filter:blur(4px);padding:3px 6px;border-radius:4px;font-size:.62rem;color:#fff;z-index:6;}
.popular-badge{position:absolute;top:6px;left:6px;background:rgba(255,165,0,.85);backdrop-filter:blur(4px);padding:2px 6px;border-radius:4px;font-size:.62rem;color:#fff;font-weight:600;z-index:6;}
.views-badge{position:absolute;bottom:6px;right:6px;background:rgba(0,0,0,.65);backdrop-filter:blur(4px);padding:2px 6px;border-radius:4px;font-size:.62rem;color:#fff;z-index:6;}
.geo-badge{left:auto;right:6px;top:6px;}
.toast-container{position:fixed;bottom:80px;left:50%;transform:translateX(-50%);z-index:2000;display:flex;flex-direction:column;gap:8px;align-items:center;pointer-events:none;}
.toast{background:rgba(30,32,38,.96);color:#fff;padding:10px 16px;border-radius:10px;font-size:.82rem;font-weight:500;box-shadow:0 4px 20px rgba(0,0,0,.4);border:1px solid rgba(255,255,255,.1);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);animation:toastIn .25s ease-out, toastOut .25s ease-in 2.5s forwards;max-width:80vw;text-align:center;pointer-events:auto;}
.toast.success{border-color:rgba(74,222,128,.4);}
.toast.error{border-color:rgba(248,113,113,.4);}
.toast.info{border-color:rgba(96,165,250,.4);}
@keyframes toastIn{from{opacity:0;transform:translateY(20px);}to{opacity:1;transform:translateY(0);}}
@keyframes toastOut{to{opacity:0;transform:translateY(20px);}}
.modal{position:fixed;inset:0;z-index:1100;background:rgba(0,0,0,.85);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);display:none;align-items:center;justify-content:center;animation:modalFadeIn .25s ease-out;}
.modal.active{display:flex;}
@keyframes modalFadeIn{from{opacity:0;}to{opacity:1;}}
.modal-page{background:var(--bg);width:100%;height:100%;max-width:540px;display:flex;flex-direction:column;overflow-y:auto;color:var(--text);animation:modalSlideIn .3s cubic-bezier(.2,.7,.2,1);}
@keyframes modalSlideIn{from{transform:translateY(20px);opacity:0;}to{transform:translateY(0);opacity:1;}}
.modal-header{position:sticky;top:0;background:var(--bg);display:flex;align-items:center;gap:14px;padding:14px;border-bottom:1px solid var(--border);z-index:5;}
.modal-header h2{font-size:1rem;font-weight:700;letter-spacing:.5px;}
.theme-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;padding:16px;}
@media (min-width:480px){.theme-grid{grid-template-columns:repeat(3,1fr);}}
.theme-card{border-radius:12px;overflow:hidden;cursor:pointer;border:2px solid var(--border);transition:transform .2s ease, border-color .2s ease, box-shadow .2s ease;position:relative;aspect-ratio:4/5;}
.theme-card:hover{transform:translateY(-3px);box-shadow:0 8px 24px rgba(0,0,0,.3);}
.theme-card.active{border-color:var(--accent);box-shadow:0 0 0 3px rgba(88,166,255,.25);}
.theme-preview{width:100%;height:100%;display:flex;flex-direction:column;padding:10px;}
.theme-preview-bar{height:8px;border-radius:4px;margin-bottom:6px;opacity:.9;}
.theme-preview-dot{width:14px;height:14px;border-radius:50%;margin-top:auto;margin-bottom:4px;}
.theme-name{position:absolute;bottom:0;left:0;right:0;padding:6px 8px;font-size:.72rem;font-weight:600;background:linear-gradient(to top,rgba(0,0,0,.85),transparent);color:#fff;text-align:center;}
.theme-check{position:absolute;top:6px;right:6px;width:22px;height:22px;border-radius:50%;background:var(--accent);color:#fff;display:none;align-items:center;justify-content:center;font-size:.7rem;font-weight:700;}
.theme-card.active .theme-check{display:flex;}
.lightbox{position:fixed;inset:0;z-index:1000;background:#000;display:none;width:100vw;height:100vh;overflow:hidden;}
.lightbox.active{display:flex;flex-direction:column;}
.lightbox.entering{animation:lbFadeScale .35s cubic-bezier(.2,.7,.2,1) forwards;}
@keyframes lbFadeScale{from{opacity:0;transform:scale(.94);}to{opacity:1;transform:scale(1);}}
.lb-ui{transition:opacity .25s ease,transform .25s ease,visibility .25s ease;opacity:1;visibility:visible;}
.lightbox.ui-hidden .lb-ui{opacity:0;visibility:hidden;pointer-events:none;transform:translateY(15px);}
.lightbox.ui-hidden .lightbox-header{transform:translateY(-15px);}
.lightbox-header{position:absolute;top:0;left:0;right:0;padding:10px 14px;display:flex;justify-content:space-between;align-items:center;background:rgba(18,19,22,.85);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);border-bottom:1px solid rgba(255,255,255,.08);z-index:60;}
.lb-controls{display:flex;align-items:center;gap:6px;}
.lb-ctrl-btn{background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.12);color:#fff;padding:5px 9px;border-radius:6px;font-size:.78rem;cursor:pointer;transition:background-color .15s ease, transform .12s ease;}
.lb-ctrl-btn:hover{background:rgba(255,255,255,.24);}
.lb-ctrl-btn:active{transform:scale(.92);}
.lb-close-btn{background:transparent;border:none;color:#fff;font-size:1.8rem;cursor:pointer;line-height:1;padding:2px 6px;}
.lightbox-body{position:relative;width:100%;height:100%;flex:1;display:flex;align-items:center;justify-content:center;overflow:hidden;z-index:10;padding-top:50px;padding-bottom:150px;}
#lbMediaContainer{position:relative;display:flex;align-items:center;justify-content:center;width:100%;height:100%;transform-origin:center center;transition:transform .06s ease-out;will-change:transform;}
.lb-img-wrap{position:relative;max-width:100%;max-height:100%;display:flex;align-items:center;justify-content:center;}
.lb-img-wrap img{max-width:100%;max-height:100%;width:auto;height:auto;object-fit:contain;display:block;-webkit-user-drag:none;user-select:none;}
.lb-img-wrap.kenburns img{animation:kenburns 20s ease-in-out infinite alternate;}
@keyframes kenburns{0%{transform:scale(1) translate(0,0);}100%{transform:scale(1.08) translate(-2%,-1.5%);}}
#lbMediaContainer video{max-width:100%;max-height:100%;width:auto;height:auto;object-fit:contain;z-index:25;pointer-events:auto;background:#000;}
.lb-video-error{color:#fff;text-align:center;padding:24px;font-size:.95rem;line-height:1.7;max-width:80%;}
.lb-video-error a{color:var(--accent);text-decoration:none;font-weight:600;}
.media-spinner{position:absolute;width:44px;height:44px;border:4px solid rgba(255,255,255,.2);border-top-color:var(--accent);border-radius:50%;animation:spin .8s linear infinite;z-index:20;display:none;}
@keyframes spin{100%{transform:rotate(360deg);}}
.lightbox-footer{position:absolute;bottom:0;left:0;right:0;padding:8px 12px calc(8px + env(safe-area-inset-bottom,0px));background:rgba(15,17,21,.9);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border-top:1px solid rgba(255,255,255,.1);display:flex;flex-direction:column;gap:5px;z-index:60;color:#fff;}
.prop-box{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);border-radius:8px;padding:6px 10px;display:flex;flex-direction:column;gap:3px;font-size:.72rem;}
.prop-row{display:flex;justify-content:space-between;gap:8px;align-items:center;}
.prop-item{display:flex;align-items:center;gap:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.prop-val{font-weight:600;color:#e1e7f0;}
.tags-container{display:flex;flex-wrap:wrap;gap:4px;}
.tag-pill{background:rgba(88,166,255,.2);border:1px solid rgba(88,166,255,.4);color:#9cd1ff;padding:2px 7px;border-radius:8px;font-size:.68rem;cursor:pointer;display:inline-flex;align-items:center;transition:background-color .15s ease, transform .12s ease;}
.tag-pill:hover{background:rgba(88,166,255,.35);}
.tag-pill:active{transform:scale(.94);}
.action-bar{display:flex;gap:6px;align-items:center;}
.btn-act{flex:1;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.15);color:#fff;padding:6px 8px;border-radius:7px;font-size:.74rem;font-weight:500;display:flex;align-items:center;justify-content:center;gap:5px;cursor:pointer;transition:background-color .15s ease, transform .12s ease;}
.btn-act:hover{background:rgba(255,255,255,.22);}
.btn-act:active{background:rgba(255,255,255,.3);transform:scale(.97);}
.lb-nav{position:absolute;top:50%;transform:translateY(-50%);background:rgba(0,0,0,.5);border:1px solid rgba(255,255,255,.25);color:#fff;font-size:1.5rem;width:44px;height:44px;border-radius:50%;display:flex;align-items:center;justify-content:center;cursor:pointer;backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);z-index:70;transition:background-color .15s ease, transform .15s ease;}
.lb-nav:hover{background:rgba(0,0,0,.75);}
.lb-prev{left:8px;}
.lb-next{right:8px;}
.pagination{display:flex;align-items:center;justify-content:center;gap:12px;padding:20px 14px;font-size:.85rem;}
.pg-btn{background:var(--surface);border:1px solid var(--border);color:var(--text);padding:7px 14px;border-radius:7px;cursor:pointer;transition:background-color .15s ease, transform .12s ease;}
.pg-btn:hover:not(:disabled){background:var(--surface-variant);}
.pg-btn:active:not(:disabled){transform:scale(.96);}
.pg-btn:disabled{opacity:.3;cursor:not-allowed;}
#infiniteLoader{text-align:center;padding:20px;font-size:.8rem;color:var(--text-muted);display:none;}
.top-list{display:flex;flex-direction:column;gap:8px;margin-top:8px;}
.top-item{display:flex;gap:10px;align-items:center;background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:8px;cursor:pointer;transition:transform .15s ease, border-color .15s ease;}
.top-item:hover{transform:translateX(3px);border-color:var(--accent);}
.top-item img{width:56px;height:56px;object-fit:cover;border-radius:6px;flex-shrink:0;background:var(--surface-variant);}
.top-item-info{display:flex;flex-direction:column;gap:2px;flex:1;overflow:hidden;}
.top-item-title{font-size:.82rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.top-item-meta{font-size:.7rem;color:var(--text-muted);}
#mapView{width:100%;height:calc(100vh - 60px);min-height:400px;}
.date-range-row{display:flex;gap:8px;align-items:center;flex-wrap:wrap;}
.date-input{flex:1;min-width:130px;background:var(--surface);border:1px solid var(--border);color:var(--text);padding:7px 10px;border-radius:8px;font-size:.78rem;outline:none;color-scheme:dark;}
:root[data-theme="light"] .date-input,
:root[data-theme="rosegold"] .date-input,
:root[data-theme="sepia"] .date-input,
:root[data-theme="macos"] .date-input{color-scheme:light;}
.date-input:focus{border-color:var(--accent);}
.flip-ghost{position:fixed;z-index:1500;pointer-events:none;border-radius:8px;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.5);transition:all .38s cubic-bezier(.2,.7,.2,1);}
.flip-ghost img,.flip-ghost video{width:100%;height:100%;object-fit:cover;display:block;}
.fab-top{position:fixed;bottom:20px;right:20px;width:44px;height:44px;border-radius:50%;background:var(--gradient);color:#fff;border:none;font-size:1.2rem;cursor:pointer;z-index:90;box-shadow:0 6px 20px rgba(0,0,0,.35);display:flex;align-items:center;justify-content:center;opacity:0;visibility:hidden;transform:translateY(20px);transition:opacity .3s ease, transform .3s ease, visibility .3s ease;}
.fab-top.show{opacity:1;visibility:visible;transform:translateY(0);}
.fab-top:hover{transform:translateY(-3px) scale(1.05);}
.fab-top:active{transform:translateY(0) scale(.94);}
.fab-manager{position:fixed;bottom:20px;left:20px;width:44px;height:44px;border-radius:50%;background:var(--surface);border:1px solid var(--border);color:var(--text);font-size:1.1rem;cursor:pointer;z-index:90;box-shadow:0 6px 20px rgba(0,0,0,.35);display:flex;align-items:center;justify-content:center;opacity:0;visibility:hidden;transform:translateY(20px);transition:opacity .3s ease, transform .3s ease, visibility .3s ease;}
.fab-manager.show{opacity:1;visibility:visible;transform:translateY(0);}
.fab-manager:hover{background:var(--surface-variant);transform:translateY(-3px) scale(1.05);}
</style>
</head>
<body>
"""


# ============================================================================
# HTML TEMPLATE — PART 2 (Body HTML)
# ============================================================================

HTML_TEMPLATE_PART2 = r"""
<!-- ================= HEADER ================= -->
<header>
  <div class="top-bar">
    <div class="brand">
      <h1 id="view-title">/*PROJECT_TITLE*/</h1>
      <span class="counter" id="total-counter">0 item</span>
    </div>
    <div class="top-actions">
      <button class="icon-btn" onclick="openMapModal()" title="Peta lokasi">🗺️ <span class="hide-xs">Peta</span></button>
      <button class="icon-btn" onclick="openThemePicker()" title="Ganti tema">🎨 <span class="hide-xs">Tema</span></button>
      <button class="icon-btn" onclick="openStats()" title="Statistik">📊 <span class="hide-xs">Stats</span></button>
      <button class="icon-btn" onclick="openManager()" title="Kelola file">⚙️ <span class="hide-xs">Kelola</span></button>
    </div>
  </div>

  <div class="search-wrap">
    <div class="search-box">
      <div id="activeTagChip" style="display:none;" class="active-tag-chip" onclick="clearActiveTag()"></div>
      <input type="text" id="searchInput" placeholder="🔍 Cari media, album, tanggal, atau #tag..."
             oninput="onSearch()" onfocus="onSearchFocus()" onblur="onSearchBlur()"
             autocomplete="off" />
      <button class="search-filter-btn" id="searchFilterBtn" onclick="openFilterModal()" title="Filter lanjutan">
        <span>⚙️ <span class="hide-xs">Filter</span></span>
        <span class="filter-indicator-dot"></span>
      </button>
    </div>
    <div class="suggestions" id="suggestionsBox"></div>
  </div>

  <div class="sub-bar">
    <div class="filter-row">
      <div class="pills-container" id="pillsContainer"></div>
    </div>

    <div class="controls-row">
      <div class="type-switcher">
        <button class="sw-btn active" id="type-all" onclick="setMediaType('all')">Semua</button>
        <button class="sw-btn" id="type-image" onclick="setMediaType('image')">🖼️ <span class="hide-xs">Gambar</span></button>
        <button class="sw-btn" id="type-video" onclick="setMediaType('video')">🎬 <span class="hide-xs">Video</span></button>
      </div>

      <select class="sort-select" id="sortSelect" onchange="onSortChange(this.value)">
        <option value="date_desc">📅 Terbaru</option>
        <option value="date_asc">📅 Terlama</option>
        <option value="size_desc">💾 Ukuran (Besar)</option>
        <option value="size_asc">💾 Ukuran (Kecil)</option>
        <option value="views_desc">🔥 Terpopuler</option>
      </select>

      <div class="view-switcher" id="viewSwitcher">
        <button class="sw-btn" data-layout="mosaic" onclick="setLayout('mosaic')" title="Mosaic">▦</button>
        <button class="sw-btn" data-layout="grid" onclick="setLayout('grid')" title="Grid">▩</button>
        <button class="sw-btn" data-layout="list" onclick="setLayout('list')" title="List">☰</button>
        <button class="sw-btn" data-layout="cinema" onclick="setLayout('cinema')" title="Cinema">🎬</button>
        <button class="sw-btn" data-layout="magazine" onclick="setLayout('magazine')" title="Magazine">📰</button>
        <button class="sw-btn" data-layout="seamless" onclick="setLayout('seamless')" title="Seamless">▤</button>
      </div>

      <div class="density-switcher" id="densitySwitcher">
        <button class="sw-btn" data-density="compact" onclick="setDensity('compact')" title="Compact">S</button>
        <button class="sw-btn" data-density="normal" onclick="setDensity('normal')" title="Normal">M</button>
        <button class="sw-btn" data-density="comfortable" onclick="setDensity('comfortable')" title="Comfortable">L</button>
      </div>
    </div>
  </div>
</header>

<main class="gallery-container layout-mosaic" id="galleryContainer" role="main" aria-label="Galeri Media"></main>

<div id="infiniteLoader">⏳ Memuat media berikutnya...</div>

<div class="pagination" id="paginationBar">
  <button class="pg-btn" id="prevBtn" onclick="prevPage()">← Sebelumnya</button>
  <span id="pageInfo">1 / 1</span>
  <button class="pg-btn" id="nextBtn" onclick="nextPage()">Selanjutnya →</button>
</div>

<button class="fab-top" id="fabTop" onclick="scrollToTop()" title="Ke atas" aria-label="Scroll ke atas">↑</button>
<button class="fab-manager" id="fabManager" onclick="openManager()" title="Kelola file" aria-label="Kelola file">⚙️</button>

<!-- ================= FILTER MODAL ================= -->
<div class="modal" id="filterModal" role="dialog" aria-label="Filter">
  <div style="background:var(--surface);border:1px solid var(--border);border-radius:14px;max-width:460px;width:92%;max-height:88vh;overflow-y:auto;padding:18px;display:flex;flex-direction:column;gap:16px;">
    <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border);padding-bottom:10px;">
      <h3 style="font-size:1rem;font-weight:700;">⚙️ Filter & Navigasi</h3>
      <button onclick="closeFilterModal()" style="background:none;border:none;color:var(--text);font-size:1.4rem;cursor:pointer;">&times;</button>
    </div>

    <div>
      <div style="font-size:.75rem;font-weight:700;color:var(--text-muted);margin-bottom:8px;text-transform:uppercase;">📅 Rentang Tanggal</div>
      <div class="date-range-row">
        <input type="date" id="dateFrom" class="date-input" onchange="onDateRangeChange()" placeholder="Dari" />
        <span style="color:var(--text-muted);font-size:.8rem;">→</span>
        <input type="date" id="dateTo" class="date-input" onchange="onDateRangeChange()" placeholder="Sampai" />
      </div>
      <div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap;">
        <button class="pill" onclick="setQuickRange('7d')">7 Hari</button>
        <button class="pill" onclick="setQuickRange('30d')">30 Hari</button>
        <button class="pill" onclick="setQuickRange('90d')">3 Bulan</button>
        <button class="pill" onclick="setQuickRange('1y')">1 Tahun</button>
        <button class="pill" onclick="setQuickRange('clear')">Bersihkan</button>
      </div>
    </div>

    <div style="display:flex;justify-content:space-between;align-items:center;background:var(--surface-variant);padding:10px 12px;border-radius:8px;">
      <span style="font-size:.8rem;font-weight:600;">🔄 Mode Infinite Scroll</span>
      <input type="checkbox" id="infiniteToggle" onchange="toggleInfiniteScroll(this.checked)" style="transform:scale(1.2);cursor:pointer;" />
    </div>

    <div>
      <div style="font-size:.75rem;font-weight:700;color:var(--text-muted);margin-bottom:8px;text-transform:uppercase;">🗓️ Periode Waktu</div>
      <div class="tags-container" id="modalMonthContainer"></div>
    </div>

    <div>
      <div style="font-size:.75rem;font-weight:700;color:var(--text-muted);margin-bottom:8px;text-transform:uppercase;">🏷️ Auto Tags (Top 60)</div>
      <div class="tags-container" id="modalTagContainer"></div>
    </div>

    <div style="display:flex;gap:8px;margin-top:6px;border-top:1px solid var(--border);padding-top:12px;">
      <button onclick="resetModalFilters()" style="flex:1;padding:9px;border-radius:8px;border:1px solid var(--border);background:var(--surface-variant);color:var(--text);cursor:pointer;font-size:.8rem;">Reset Filter</button>
      <button onclick="closeFilterModal()" style="flex:1;padding:9px;border-radius:8px;border:none;background:var(--gradient);color:#fff;cursor:pointer;font-size:.8rem;font-weight:600;">Selesai</button>
    </div>
  </div>
</div>

<!-- ================= THEME PICKER MODAL ================= -->
<div class="modal" id="themeModal" role="dialog" aria-label="Pilih Tema">
  <div class="modal-page">
    <div class="modal-header">
      <button onclick="closeThemePicker()" style="background:transparent;border:none;color:var(--text);font-size:1.4rem;cursor:pointer;">&#8592;</button>
      <h2>🎨 PILIH TEMA</h2>
    </div>
    <div style="font-size:.78rem;color:var(--text-muted);padding:0 16px 8px;">
      Pilih tema favoritmu. Tersimpan otomatis di perangkat ini.
    </div>
    <div class="theme-grid" id="themeGrid"></div>
  </div>
</div>

<!-- ================= MAP MODAL ================= -->
<div class="modal" id="mapModal" role="dialog" aria-label="Peta">
  <div class="modal-page">
    <div class="modal-header">
      <button onclick="closeMapModal()" style="background:transparent;border:none;color:var(--text);font-size:1.4rem;cursor:pointer;">&#8592;</button>
      <h2>🗺️ PETA SEBARAN LOKASI</h2>
    </div>
    <div id="mapView"></div>
  </div>
</div>

<!-- ================= STATS MODAL ================= -->
<div class="modal" id="statsModal" role="dialog" aria-label="Statistik">
  <div class="modal-page">
    <div class="modal-header">
      <button onclick="closeStats()" style="background:transparent;border:none;color:var(--text);font-size:1.4rem;cursor:pointer;">&#8592;</button>
      <h2>📊 STATISTIK KOLEKSI</h2>
    </div>
    <div style="padding:16px;display:flex;flex-direction:column;gap:20px;" id="statsContent"></div>
  </div>
</div>

<!-- ================= MANAGER LINK MODAL ================= -->
<div class="modal" id="managerModal" role="dialog" aria-label="Kelola File">
  <div style="background:var(--surface);border:1px solid var(--border);border-radius:14px;max-width:420px;width:92%;padding:22px;display:flex;flex-direction:column;gap:14px;">
    <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border);padding-bottom:10px;">
      <h3 style="font-size:1rem;font-weight:700;">⚙️ Kelola File</h3>
      <button onclick="closeManager()" style="background:none;border:none;color:var(--text);font-size:1.4rem;cursor:pointer;">&times;</button>
    </div>
    <p style="font-size:.85rem;line-height:1.6;color:var(--text-muted);">
      Buka <b>manager.html</b> untuk melihat semua file, menandai untuk dihapus, dan mengelola blacklist.
    </p>
    <div style="display:flex;flex-direction:column;gap:8px;">
      <a href="manager.html" target="_blank" style="display:flex;align-items:center;justify-content:center;gap:8px;padding:12px;border-radius:8px;background:var(--gradient);color:#fff;text-decoration:none;font-weight:600;font-size:.9rem;">⚙️ Buka Manager Panel</a>
      <a href="https://catbox.moe/user/manage.php" target="_blank" rel="noopener" style="display:flex;align-items:center;justify-content:center;gap:8px;padding:12px;border-radius:8px;background:rgba(255,255,255,.08);border:1px solid var(--border);color:var(--text);text-decoration:none;font-weight:500;font-size:.85rem;">🌐 Buka Catbox Manager</a>
    </div>
    <p style="font-size:.72rem;color:var(--text-muted);text-align:center;">
      File yang di-blacklist akan otomatis tersembunyi saat re-generate galeri.
    </p>
  </div>
</div>

<!-- ================= LIGHTBOX ================= -->
<div class="lightbox" id="lightbox" role="dialog" aria-label="Media Viewer">
  <div class="lightbox-header lb-ui">
    <span id="lbIndex" style="font-size:.82rem;color:#aaa;"></span>
    <div class="lb-controls">
      <button class="lb-ctrl-btn" onclick="zoomAction(-0.4)" title="Zoom out">−</button>
      <span id="zoomLevelText" style="font-size:.75rem;min-width:38px;text-align:center;">100%</span>
      <button class="lb-ctrl-btn" onclick="zoomAction(0.4)" title="Zoom in">+</button>
      <button class="lb-ctrl-btn" onclick="resetZoom()" title="Reset zoom">Reset</button>
      <button class="lb-ctrl-btn" id="kenburnsToggle" onclick="toggleKenBurns()" title="Ken Burns effect">🎞️</button>
    </div>
    <button class="lb-close-btn" onclick="closeLightbox()" aria-label="Tutup">&times;</button>
  </div>

  <div class="lightbox-body" id="lightboxBody">
    <div class="media-spinner" id="lbSpinner"></div>
    <button class="lb-nav lb-prev lb-ui" onclick="event.stopPropagation();navLightbox(-1);" aria-label="Sebelumnya">&#10094;</button>
    <div id="lbMediaContainer"></div>
    <button class="lb-nav lb-next lb-ui" onclick="event.stopPropagation();navLightbox(1);" aria-label="Berikutnya">&#10095;</button>
  </div>

  <div class="lightbox-footer lb-ui">
    <div class="prop-box">
      <div class="prop-row">
        <div class="prop-item">🏷️ <b>Nama:</b> <span class="prop-val" id="propName">-</span></div>
        <div class="prop-item">📁 <b>Album:</b> <span class="prop-val" id="propCat">-</span></div>
      </div>
      <div class="prop-row">
        <div class="prop-item">📅 <b>Tanggal:</b> <span class="prop-val" id="propMtime">-</span></div>
        <div class="prop-item">💾 <b>Ukuran:</b> <span class="prop-val" id="propSize">-</span> (<span id="propExt"></span>)</div>
      </div>
      <div class="prop-row">
        <div class="prop-item" style="width:100%;">📤 <b>Uploaded:</b> <span class="prop-val" id="propUploadedAt">-</span></div>
      </div>
      <div class="prop-row">
        <div class="prop-item" style="width:100%;">👁️ <b>Dilihat:</b> <span class="prop-val" id="propViews">—</span> kali</div>
      </div>
      <div class="prop-row" id="propCameraRow" style="display:none;">
        <div class="prop-item" style="width:100%;">📷 <b>Kamera:</b> <span class="prop-val" id="propCamera">-</span></div>
      </div>
      <div class="prop-row" id="propExposureRow" style="display:none;">
        <div class="prop-item" style="width:100%;">⚙️ <b>Eksposur:</b> <span class="prop-val" id="propExposure">-</span></div>
      </div>
      <div class="prop-row" id="propGeoRow" style="display:none;">
        <div class="prop-item" style="width:100%;">📍 <b>Lokasi EXIF:</b> <span class="prop-val" id="propGeo">-</span></div>
      </div>
      <div id="propTagsRow" style="display:none;flex-direction:column;gap:3px;">
        <div style="font-weight:600;color:var(--text-muted);font-size:.72rem;">🏷️ Tag Otomatis:</div>
        <div class="tags-container" id="propTags"></div>
      </div>
    </div>

    <div class="action-bar">
      <button class="btn-act" onclick="downloadCurrentOriginal()" title="Download file asli">⬇️ Download</button>
      <button class="btn-act" onclick="copyDirectLink()" title="Salin URL file langsung">📋 Copy Link</button>
      <button class="btn-act" onclick="shareCurrentMedia()" title="Bagikan">🔗 Share</button>
      <button class="btn-act" id="geoBtn" style="display:none;" onclick="openGeoMap()" title="Buka di Google Maps">📍 Lokasi</button>
    </div>
  </div>
</div>

<div class="toast-container" id="toastContainer"></div>

<style>
  @media (max-width:480px){
    .hide-xs{display:none;}
    .top-actions .icon-btn{padding:6px 8px;}
    .controls-row{gap:4px;}
    .view-switcher .sw-btn,
    .density-switcher .sw-btn{padding:4px 6px;font-size:.65rem;}
    .type-switcher .sw-btn{padding:4px 6px;font-size:.65rem;}
  }
  @media (min-width:1024px){
    .gallery-container{padding:16px;}
  }
  @media (min-width:1440px){
    .gallery-container{padding:20px;}
  }
</style>
"""

# ============================================================================
# HTML TEMPLATE — PART 3 (JavaScript Galeri)
# ============================================================================

HTML_TEMPLATE_PART3 = r"""
<script>
/* GALLERY APP — CORE */
const RAW_DATA = /*DATA_PLACEHOLDER*/;
const ITEMS_PER_PAGE = /*ITEMS_PER_PAGE_PLACEHOLDER*/;
const COUNTER_API_BASE = /*COUNTER_API_PLACEHOLDER*/;
const COUNTER_NAMESPACE = /*COUNTER_NS_PLACEHOLDER*/;
const PROJECT_TITLE = /*PROJECT_TITLE_JS*/;

function esc(s){return String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");}
const escAttr = esc;
function formatBytes(b){if(!b||b===0)return"0 B";const k=1024,s=["B","KB","MB","GB","TB"];const i=Math.floor(Math.log(b)/Math.log(k));return parseFloat((b/Math.pow(k,i)).toFixed(1))+" "+s[i];}

RAW_DATA.forEach(item=>{if(typeof item.views!=="number")item.views=0;item._search=[item.title,item.filename,item.date,item.month_display,item.category,...(item.tags||[])].join(" ").toLowerCase();});

let currentCategory="Semua",currentMediaType="all",currentMonth="Semua",currentTag="Semua",currentSort="date_desc";
let isInfiniteScroll=false,searchQuery="",currentPage=1,currentLayout="mosaic",currentDensity="normal";
let filteredData=[],activeLbIndex=0,dateFrom="",dateTo="",zoomScale=1,panX=0,panY=0;
let leafletMap=null,mapMarkers=[],kenBurnsEnabled=false;
const viewedThisSession=new Set(),viewCache=new Map(),mediaCache=new Map();

const THEMES=[
{id:"dark",name:"Dark",bg:"#121316",fg:"#ffffff",accent:"#58a6ff"},
{id:"light",name:"Light",bg:"#f4f6f9",fg:"#1f2328",accent:"#0969da"},
{id:"midnight",name:"Midnight",bg:"#0a0e1a",fg:"#e2e8f0",accent:"#22d3ee"},
{id:"sunset",name:"Sunset",bg:"#1a0f1e",fg:"#fff5eb",accent:"#f97316"},
{id:"forest",name:"Forest",bg:"#0d1a0f",fg:"#ecfdf5",accent:"#4ade80"},
{id:"rosegold",name:"Rose Gold",bg:"#fdf8f3",fg:"#3d2b2b",accent:"#e11d48"},
{id:"amoled",name:"AMOLED",bg:"#000000",fg:"#ffffff",accent:"#ffffff"},
{id:"cyberpunk",name:"Cyberpunk",bg:"#0d0221",fg:"#f0e6ff",accent:"#ff00aa"},
{id:"sepia",name:"Sepia Retro",bg:"#f4ecd8",fg:"#3d2817",accent:"#8b4513"},
{id:"macos",name:"macOS",bg:"#ececec",fg:"#1d1d1f",accent:"#007aff"}];

function initTheme(){const s=localStorage.getItem("app_theme");if(s&&THEMES.some(t=>t.id===s))setTheme(s,false);else{const p=window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches;setTheme(p?"dark":"light",false);}
const sl=localStorage.getItem("app_layout");if(sl)currentLayout=sl;const sd=localStorage.getItem("app_density");if(sd)currentDensity=sd;}

function setTheme(id,animate=true){const t=THEMES.find(x=>x.id===id)||THEMES[0];if(animate){document.body.classList.add("theme-transitioning");setTimeout(()=>document.body.classList.remove("theme-transitioning"),450);}
document.documentElement.setAttribute("data-theme",t.id);localStorage.setItem("app_theme",t.id);
const m=document.querySelector('meta[name="theme-color"]');if(m)m.setAttribute("content",t.bg);
document.querySelectorAll(".theme-card").forEach(c=>c.classList.toggle("active",c.dataset.theme===t.id));}

function buildThemeGrid(){const g=document.getElementById("themeGrid");if(!g)return;
g.innerHTML=THEMES.map(t=>`<div class="theme-card" data-theme="${escAttr(t.id)}" onclick="selectTheme('${escAttr(t.id)}')"><div class="theme-preview" style="background:${escAttr(t.bg)};color:${escAttr(t.fg)};"><div class="theme-preview-bar" style="background:${escAttr(t.accent)};"></div><div class="theme-preview-bar" style="background:${escAttr(t.fg)};opacity:.3;width:70%;"></div><div class="theme-preview-bar" style="background:${escAttr(t.fg)};opacity:.2;width:50%;"></div><div class="theme-preview-dot" style="background:${escAttr(t.accent)};"></div></div><div class="theme-name">${esc(t.name)}</div><div class="theme-check">✓</div></div>`).join("");
const cur=document.documentElement.getAttribute("data-theme")||"dark";g.querySelectorAll(".theme-card").forEach(c=>c.classList.toggle("active",c.dataset.theme===cur));}

function selectTheme(id){setTheme(id);const t=THEMES.find(x=>x.id===id);if(t)showToast(`Tema: ${t.name}`,"success");}
function openThemePicker(){buildThemeGrid();document.getElementById("themeModal").classList.add("active");}
function closeThemePicker(){document.getElementById("themeModal").classList.remove("active");}
function openManager(){document.getElementById("managerModal").classList.add("active");}
function closeManager(){document.getElementById("managerModal").classList.remove("active");}

function showToast(msg,type="info",duration=2500){const c=document.getElementById("toastContainer");if(!c)return;const el=document.createElement("div");el.className="toast "+type;el.textContent=msg;c.appendChild(el);setTimeout(()=>{try{el.remove()}catch(e){}},duration+300);}

async function fetchViewCount(id){if(viewCache.has(id))return viewCache.get(id);try{const r=await fetch(`${COUNTER_API_BASE}/get/${encodeURIComponent(COUNTER_NAMESPACE)}/${encodeURIComponent(id)}`,{cache:"no-store"});if(r.status===404){viewCache.set(id,0);return 0;}if(r.status===429)return null;if(!r.ok)return null;const d=await r.json();const v=typeof d.value==="number"?d.value:0;viewCache.set(id,v);return v;}catch(e){return null;}}

async function incrementViewCount(id){try{const r=await fetch(`${COUNTER_API_BASE}/hit/${encodeURIComponent(COUNTER_NAMESPACE)}/${encodeURIComponent(id)}`,{cache:"no-store"});if(!r.ok)return null;const d=await r.json();const v=typeof d.value==="number"?d.value:null;if(v!==null)viewCache.set(id,v);return v;}catch(e){return null;}}

async function loadAllViewCounts(){const C=6;let cursor=0;const items=RAW_DATA;async function worker(){while(cursor<items.length){const i=cursor++;const it=items[i];const c=await fetchViewCount(it.id);if(c!==null)it.views=c;}}
await Promise.all(Array.from({length:C},()=>worker()));if(currentSort==="views_desc")applyFilters();else renderGrid();}

function trackView(item){if(!item||viewedThisSession.has(item.id))return;viewedThisSession.add(item.id);
const el=document.getElementById("propViews");if(el)el.textContent=item.views>0?item.views:"…";
incrementViewCount(item.id).then(c=>{if(c!==null){item.views=c;const e=document.getElementById("propViews");if(e&&filteredData[activeLbIndex]&&filteredData[activeLbIndex].id===item.id)e.textContent=c;}});}

function init(){initTheme();applyDensityToDOM();applyLayoutToDOM();setupCategories();setupModalMonthFilters();setupModalTagFilters();applyFilters();setupGestures();setupInfiniteScrollListener();setupScrollTopFAB();handleHashRouting();window.addEventListener("hashchange",handleHashRouting);
const fM=document.getElementById("filterModal");if(fM)fM.onclick=e=>{if(e.target===fM)closeFilterModal();};
const tM=document.getElementById("themeModal");if(tM)tM.onclick=e=>{if(e.target===tM)closeThemePicker();};
const mM=document.getElementById("managerModal");if(mM)mM.onclick=e=>{if(e.target===mM)closeManager();};
const ss=localStorage.getItem("app_sort");if(ss){currentSort=ss;const el=document.getElementById("sortSelect");if(el)el.value=ss;}
loadAllViewCounts();}

function setupCategories(){const cc={};RAW_DATA.forEach(d=>{cc[d.category]=(cc[d.category]||0)+1;});const cats=["Semua",...Object.keys(cc).sort()];const c=document.getElementById("pillsContainer");if(!c)return;
c.innerHTML=cats.map(cat=>{const cnt=cat==="Semua"?RAW_DATA.length:cc[cat];const a=cat===currentCategory?" active":"";return `<div class="pill${a}" data-cat="${escAttr(cat)}" onclick="onCategoryClick(this)">${esc(cat)} <span class="pill-badge">${cnt}</span></div>`;}).join("");}

function onCategoryClick(el){setCategory(el.dataset.cat);}
function setCategory(cat){currentCategory=cat;searchQuery="";const si=document.getElementById("searchInput");if(si)si.value="";
const vt=document.getElementById("view-title");if(vt)vt.innerText=cat==="Semua"?PROJECT_TITLE:cat;setupCategories();currentPage=1;applyFilters();}

function setMediaType(type){currentMediaType=type;document.querySelectorAll(".type-switcher .sw-btn").forEach(b=>b.classList.remove("active"));const btn=document.getElementById(`type-${type}`);if(btn)btn.classList.add("active");currentPage=1;applyFilters();}

function onSortChange(v){currentSort=v;localStorage.setItem("app_sort",v);currentPage=1;applyFilters();}
function sortDataset(list){switch(currentSort){case"date_asc":return list.sort((a,b)=>a.date.localeCompare(b.date));case"size_desc":return list.sort((a,b)=>(b.size||0)-(a.size||0));case"size_asc":return list.sort((a,b)=>(a.size||0)-(b.size||0));case"views_desc":return list.sort((a,b)=>(b.views||0)-(a.views||0));default:return list.sort((a,b)=>b.date.localeCompare(a.date));}}

function openFilterModal(){document.getElementById("filterModal").classList.add("active");}
function closeFilterModal(){document.getElementById("filterModal").classList.remove("active");}

function setupModalMonthFilters(){const map=new Map();const cnt={};RAW_DATA.forEach(d=>{if(d.month_key&&d.month_display){if(!map.has(d.month_key))map.set(d.month_key,d.month_display);cnt[d.month_key]=(cnt[d.month_key]||0)+1;}});
const keys=Array.from(map.keys()).sort().reverse();const c=document.getElementById("modalMonthContainer");if(!c)return;
let html=`<div class="pill${currentMonth==="Semua"?" active":""}" data-month="Semua" onclick="onMonthClick(this)">🗓️ Semua Waktu</div>`;
html+=keys.map(k=>{const a=k===currentMonth?" active":"";return `<div class="pill${a}" data-month="${escAttr(k)}" onclick="onMonthClick(this)">${esc(map.get(k))} <span class="pill-badge">${cnt[k]}</span></div>`;}).join("");
c.innerHTML=html;updateFilterTriggerState();}

function onMonthClick(el){setMonthFilter(el.dataset.month);}
function setupModalTagFilters(){const cnt={};RAW_DATA.forEach(d=>{if(Array.isArray(d.tags))d.tags.forEach(t=>{cnt[t]=(cnt[t]||0)+1;});});
const sorted=Object.keys(cnt).sort((a,b)=>cnt[b]-cnt[a]).slice(0,60);const c=document.getElementById("modalTagContainer");if(!c)return;
let html=`<div class="pill${currentTag==="Semua"?" active":""}" data-tag="Semua" onclick="onTagClick(this)">🏷️ Semua Tag</div>`;
html+=sorted.map(tag=>{const a=tag===currentTag?" active":"";return `<div class="pill${a}" data-tag="${escAttr(tag)}" onclick="onTagClick(this)">#${esc(tag)} <span class="pill-badge">${cnt[tag]}</span></div>`;}).join("");
c.innerHTML=html;updateFilterTriggerState();}

function onTagClick(el){setTagFilter(el.dataset.tag);}
function setMonthFilter(k){currentMonth=k;searchQuery="";const si=document.getElementById("searchInput");if(si)si.value="";setupModalMonthFilters();currentPage=1;applyFilters();}
function setTagFilter(tag){currentTag=tag;searchQuery="";const si=document.getElementById("searchInput");if(si)si.value="";
const chip=document.getElementById("activeTagChip");if(chip){if(tag!=="Semua"){chip.innerHTML=`#${esc(tag)} <span style="font-size:.9rem;font-weight:bold;">&times;</span>`;chip.style.display="flex";}else chip.style.display="none";}
setupModalTagFilters();currentPage=1;applyFilters();}

function clearActiveTag(){setTagFilter("Semua");}
function resetModalFilters(){currentMonth="Semua";currentTag="Semua";dateFrom="";dateTo="";
const df=document.getElementById("dateFrom");if(df)df.value="";const dt=document.getElementById("dateTo");if(dt)dt.value="";
const chip=document.getElementById("activeTagChip");if(chip)chip.style.display="none";
setupModalMonthFilters();setupModalTagFilters();updateFilterTriggerState();currentPage=1;applyFilters();}

function updateFilterTriggerState(){const btn=document.getElementById("searchFilterBtn");if(!btn)return;const has=currentMonth!=="Semua"||currentTag!=="Semua"||dateFrom||dateTo;btn.classList.toggle("active",has);}

function onDateRangeChange(){const f=document.getElementById("dateFrom");const t=document.getElementById("dateTo");dateFrom=f?f.value:"";dateTo=t?t.value:"";updateFilterTriggerState();currentPage=1;applyFilters();}

function setQuickRange(range){const now=new Date();let from=null;switch(range){case"7d":from=new Date(now.getTime()-7*86400000);break;case"30d":from=new Date(now.getTime()-30*86400000);break;case"90d":from=new Date(now.getTime()-90*86400000);break;case"1y":from=new Date(now.getTime()-365*86400000);break;case"clear":dateFrom="";dateTo="";const df=document.getElementById("dateFrom");if(df)df.value="";const dt=document.getElementById("dateTo");if(dt)dt.value="";updateFilterTriggerState();currentPage=1;applyFilters();return;}
const fmt=d=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
dateFrom=fmt(from);dateTo=fmt(now);const dfE=document.getElementById("dateFrom");if(dfE)dfE.value=dateFrom;const dtE=document.getElementById("dateTo");if(dtE)dtE.value=dateTo;
updateFilterTriggerState();currentPage=1;applyFilters();showToast(`Filter: ${dateFrom} → ${dateTo}`,"info");}

let searchTimer=null;
function onSearch(){searchQuery=document.getElementById("searchInput").value.toLowerCase().trim();currentPage=1;clearTimeout(searchTimer);searchTimer=setTimeout(()=>{applyFilters();updateSuggestions();},120);}
function onSearchFocus(){updateSuggestions();}
function onSearchBlur(){setTimeout(()=>{const b=document.getElementById("suggestionsBox");if(b)b.classList.remove("show");},200);}

function updateSuggestions(){const box=document.getElementById("suggestionsBox");if(!box)return;const q=searchQuery.replace(/^#/,"").trim();if(!q){box.classList.remove("show");box.innerHTML="";return;}
const matches=[],seen=new Set(),qL=q.toLowerCase();
const tagC={};RAW_DATA.forEach(d=>{if(Array.isArray(d.tags))d.tags.forEach(t=>{tagC[t]=(tagC[t]||0)+1;});});
Object.keys(tagC).filter(t=>t.toLowerCase().includes(qL)).sort((a,b)=>tagC[b]-tagC[a]).slice(0,5).forEach(t=>{if(!seen.has("t:"+t)){seen.add("t:"+t);matches.push({type:"tag",text:t,meta:`${tagC[t]} item`,icon:"🏷️"});}});
const catC={};RAW_DATA.forEach(d=>{catC[d.category]=(catC[d.category]||0)+1;});
Object.keys(catC).filter(c=>c.toLowerCase().includes(qL)).sort((a,b)=>catC[b]-catC[a]).slice(0,3).forEach(c=>{if(!seen.has("c:"+c)){seen.add("c:"+c);matches.push({type:"category",text:c,meta:`${catC[c]} item`,icon:"📁"});}});
RAW_DATA.filter(d=>d.title.toLowerCase().includes(qL)).slice(0,4).forEach(d=>{if(!seen.has("i:"+d.id)){seen.add("i:"+d.id);matches.push({type:"item",id:d.id,text:d.title,meta:d.category,icon:"🖼️"});}});
if(!matches.length){box.classList.remove("show");box.innerHTML="";return;}
const hl=t=>{const i=t.toLowerCase().indexOf(qL);if(i===-1)return esc(t);return esc(t.slice(0,i))+"<mark>"+esc(t.slice(i,i+q.length))+"</mark>"+esc(t.slice(i+q.length));};
box.innerHTML=matches.map(m=>{let oc;if(m.type==="tag")oc=`applySuggestion('tag','${escAttr(m.text)}')`;else if(m.type==="category")oc=`applySuggestion('category','${escAttr(m.text)}')`;else if(m.type==="item")oc=`applySuggestion('item','${escAttr(m.id)}')`;
return `<div class="suggestion-item" onclick="${oc}"><span class="suggestion-icon">${m.icon}</span><span class="suggestion-text">${hl(m.text)}</span><span class="suggestion-meta">${esc(m.meta)}</span></div>`;}).join("");
box.classList.add("show");}

function applySuggestion(type,value){const box=document.getElementById("suggestionsBox");if(box)box.classList.remove("show");const si=document.getElementById("searchInput");
if(type==="tag"){if(si)si.value="";searchQuery="";setTagFilter(value);showToast(`Tag: #${value}`,"info");}
else if(type==="category"){if(si)si.value="";searchQuery="";setCategory(value);showToast(`Kategori: ${value}`,"info");}
else if(type==="item"){if(si)si.value="";searchQuery="";applyFilters();const i=filteredData.findIndex(x=>x.id===value);if(i!==-1)openLightbox(i);}}

function applyFilters(){const q=searchQuery.replace(/^#/,"").trim();
const base=RAW_DATA.filter(item=>{if(currentCategory!=="Semua"&&item.category!==currentCategory)return false;if(currentMediaType!=="all"&&item.type!==currentMediaType)return false;if(currentMonth!=="Semua"&&item.month_key!==currentMonth)return false;if(currentTag!=="Semua"&&!(item.tags&&item.tags.includes(currentTag)))return false;
if(dateFrom||dateTo){const d=(item.date||"").slice(0,10);if(dateFrom&&d<dateFrom)return false;if(dateTo&&d>dateTo)return false;}return !q||item._search.includes(q);});
filteredData=sortDataset(base);const tc=document.getElementById("total-counter");if(tc)tc.innerText=`${filteredData.length} item`;renderGrid();}

function applyLayoutToDOM(){const c=document.getElementById("galleryContainer");if(!c)return;c.className=`gallery-container layout-${currentLayout}`;document.querySelectorAll("#viewSwitcher .sw-btn").forEach(b=>b.classList.toggle("active",b.dataset.layout===currentLayout));}
function applyDensityToDOM(){document.documentElement.setAttribute("data-density",currentDensity);document.querySelectorAll("#densitySwitcher .sw-btn").forEach(b=>b.classList.toggle("active",b.dataset.density===currentDensity));}
function setLayout(m){currentLayout=m;localStorage.setItem("app_layout",m);applyLayoutToDOM();renderGrid();}
function setDensity(d){currentDensity=d;localStorage.setItem("app_density",d);applyDensityToDOM();}
function markLoaded(el){const p=el.closest(".gallery-item");if(p)p.classList.add("loaded");}
function isPopular(item){return (item.views||0)>=5;}
function viewsLabel(item){return item.views>0?`👁️ ${item.views}`:"";}

function renderItemMedia(item){const st=escAttr(item.thumb),su=escAttr(item.url),sv=escAttr(item.video_thumb||"");let html;
if(item.type==="video"){if(item.video_thumb){html=`<div class="media-wrap media-video-poster"><img src="${sv}" loading="lazy" decoding="async" alt="" onload="markLoaded(this)" onerror="this.parentElement.className='media-wrap media-video-placeholder';this.style.display='none';"><div class="play-icon-overlay"><div class="play-icon-circle">▶</div></div></div>`;}
else{html=`<div class="media-wrap media-video-placeholder"><div class="play-icon-overlay"><div class="play-icon-circle">▶</div></div></div>`;}}
else{html=`<img src="${st}" loading="lazy" decoding="async" alt="" onload="markLoaded(this)" onerror="this.onerror=null;this.src='${su}';markLoaded(this);">`;}
return html;}

function renderGrid(){const c=document.getElementById("galleryContainer");const pag=document.getElementById("paginationBar");if(!c)return;
let items,start=0;
if(isInfiniteScroll){if(pag)pag.style.display="none";items=filteredData.slice(0,currentPage*ITEMS_PER_PAGE);}
else{if(pag)pag.style.display="flex";const total=Math.ceil(filteredData.length/ITEMS_PER_PAGE)||1;if(currentPage>total)currentPage=total;if(currentPage<1)currentPage=1;start=(currentPage-1)*ITEMS_PER_PAGE;items=filteredData.slice(start,start+ITEMS_PER_PAGE);
const pi=document.getElementById("pageInfo");if(pi)pi.innerText=`${currentPage} / ${total}`;
const pb=document.getElementById("prevBtn");if(pb)pb.disabled=currentPage<=1;
const nb=document.getElementById("nextBtn");if(nb)nb.disabled=currentPage>=total;}
renderItemsToContainer(c,items,start);}

function renderItemsToContainer(container,items,startIndex){const isMagazine=currentLayout==="magazine";const isCinema=currentLayout==="cinema";
const html=items.map((item,idx)=>{const gIdx=startIndex+idx;const pop=isPopular(item);const vLabel=viewsLabel(item);const geo=item.geo?'<span class="video-tag geo-badge">📍</span>':'';
const isHero=isMagazine&&(idx===0);const extraClass=isHero?" hero":"";
let badges;
if(currentLayout==="list"){badges=`<div class="list-info"><div class="list-title">${esc(item.title)}</div><div class="list-meta">${esc(item.category)} • ${esc(item.date)} • ${esc(item.ext)} ${item.geo?"• 📍":""} ${vLabel?"• "+vLabel:""} ${pop?"• 🔥":""}</div></div>`;}
else if(isCinema){badges=`<div class="cinema-info"><div class="cinema-title">${esc(item.title)}</div><div class="cinema-meta">${esc(item.category)} • ${esc(item.date)} ${vLabel?"• "+vLabel:""} ${pop?"• 🔥 Populer":""}</div></div>`;}
else if(isHero){badges=`<div class="hero-info"><div class="hero-title">${esc(item.title)}</div></div>`;}
else{badges=`${pop?'<span class="popular-badge">🔥 Populer</span>':''}<span class="badge">${esc(item.category)}</span>${item.type==="video"?'<span class="video-tag">🎬 Video</span>':''}${vLabel?`<span class="views-badge">${vLabel}</span>`:''}${geo}`;}
return `<div class="gallery-item reveal-item${extraClass}" data-index="${gIdx}">${renderItemMedia(item)}${badges}</div>`;}).join("");
container.innerHTML=html;
container.querySelectorAll(".gallery-item").forEach(el=>{el.addEventListener("click",e=>openLightbox(Number(el.dataset.index),true,e.currentTarget));});
requestAnimationFrame(()=>{const its=container.querySelectorAll(".reveal-item");its.forEach((el,i)=>setTimeout(()=>el.classList.add("revealed"),Math.min(i*12,300)));});}

function prevPage(){if(currentPage>1){currentPage--;renderGrid();window.scrollTo(0,0);}}
function nextPage(){currentPage++;renderGrid();window.scrollTo(0,0);}
function toggleInfiniteScroll(enabled){isInfiniteScroll=enabled;currentPage=1;renderGrid();}

let scrollTick=false;
function setupInfiniteScrollListener(){window.addEventListener("scroll",()=>{if(scrollTick)return;scrollTick=true;requestAnimationFrame(()=>{scrollTick=false;if(!isInfiniteScroll)return;
if((window.innerHeight+window.scrollY)>=document.body.offsetHeight-700){const total=Math.ceil(filteredData.length/ITEMS_PER_PAGE)||1;if(currentPage<total){currentPage++;renderGrid();}}});},{passive:true});}

function scrollToTop(){window.scrollTo({top:0,behavior:"smooth"});}
function setupScrollTopFAB(){const fab=document.getElementById("fabTop");const mgr=document.getElementById("fabManager");
window.addEventListener("scroll",()=>{if(window.scrollY>500){if(fab)fab.classList.add("show");if(mgr)mgr.classList.add("show");}else{if(fab)fab.classList.remove("show");if(mgr)mgr.classList.remove("show");}},{passive:true});}

window.addEventListener("keydown",e=>{if(e.key==="Escape"){const fM=document.getElementById("filterModal");const tM=document.getElementById("themeModal");const mM=document.getElementById("mapModal");const sM=document.getElementById("statsModal");const gM=document.getElementById("managerModal");
if(fM&&fM.classList.contains("active")){closeFilterModal();return;}if(tM&&tM.classList.contains("active")){closeThemePicker();return;}if(mM&&mM.classList.contains("active")){closeMapModal();return;}if(sM&&sM.classList.contains("active")){closeStats();return;}if(gM&&gM.classList.contains("active")){closeManager();return;}}
if((e.ctrlKey||e.metaKey)&&e.key==="k"){e.preventDefault();const si=document.getElementById("searchInput");if(si)si.focus();}});

function handleHashRouting(){const hash=window.location.hash.replace("#","");if(!hash){const lb=document.getElementById("lightbox");if(lb&&lb.classList.contains("active"))closeLightbox(false);return;}
let idx=filteredData.findIndex(x=>x.id===hash);
if(idx===-1){currentCategory="Semua";currentMediaType="all";currentMonth="Semua";currentTag="Semua";searchQuery="";dateFrom="";dateTo="";
const si=document.getElementById("searchInput");if(si)si.value="";
const df=document.getElementById("dateFrom");if(df)df.value="";
const dt=document.getElementById("dateTo");if(dt)dt.value="";
const chip=document.getElementById("activeTagChip");if(chip)chip.style.display="none";
document.querySelectorAll(".type-switcher .sw-btn").forEach(b=>b.classList.remove("active"));
const ta=document.getElementById("type-all");if(ta)ta.classList.add("active");
setupCategories();setupModalMonthFilters();setupModalTagFilters();applyFilters();
idx=filteredData.findIndex(x=>x.id===hash);}
if(idx!==-1)openLightbox(idx,false);}

function openLightbox(index,updateHash=true,sourceEl=null){activeLbIndex=index;const item=filteredData[index];if(!item)return;
if(updateHash)history.pushState(null,"",`#${item.id}`);resetZoom();
const container=document.getElementById("lbMediaContainer");const spinner=document.getElementById("lbSpinner");const lb=document.getElementById("lightbox");
if(!container||!lb)return;if(spinner)spinner.style.display="block";
if(sourceEl&&!prefersReducedMotion())runFlipTransition(sourceEl,()=>renderLightboxContent(item,container,spinner));else renderLightboxContent(item,container,spinner);
updateLightboxInfo(item,index);lb.classList.remove("ui-hidden");lb.classList.add("active","entering");setTimeout(()=>lb.classList.remove("entering"),400);trackView(item);}

function renderLightboxContent(item,container,spinner){if(item.type==="video"){const p=item.video_thumb?`poster="${escAttr(item.video_thumb)}"`:"";
container.innerHTML=`<video id="lbVideoPlayer" controls playsinline webkit-playsinline preload="metadata" src="${escAttr(item.url)}" ${p}></video><div id="lbVideoError" class="lb-video-error" style="display:none;">⚠️ Video tidak dapat diputar.<br><a href="${escAttr(item.url)}" target="_blank" rel="noopener">Buka di tab baru</a></div>`;
const v=document.getElementById("lbVideoPlayer");if(v){v.addEventListener("waiting",()=>{if(spinner)spinner.style.display="block";});v.addEventListener("playing",()=>{if(spinner)spinner.style.display="none";});v.addEventListener("canplay",()=>{if(spinner)spinner.style.display="none";});v.addEventListener("loadeddata",()=>{if(spinner)spinner.style.display="none";});v.addEventListener("error",()=>{if(spinner)spinner.style.display="none";v.style.display="none";const err=document.getElementById("lbVideoError");if(err)err.style.display="block";});v.addEventListener("touchstart",e=>e.stopPropagation(),{passive:true});}}
else{const kb=kenBurnsEnabled?" kenburns":"";container.innerHTML=`<div class="lb-img-wrap${kb}"><img id="lbImg" src="${escAttr(item.url)}" alt="${escAttr(item.title)}" decoding="async" draggable="false" /></div>`;
const img=document.getElementById("lbImg");if(img){img.onload=()=>{if(spinner)spinner.style.display="none";};img.onerror=()=>{if(item.thumb&&item.thumb!==item.url){img.src=item.thumb;img.onerror=()=>{if(spinner)spinner.style.display="none";};}else{if(spinner)spinner.style.display="none";}};}}}

function updateLightboxInfo(item,index){const set=(id,val)=>{const el=document.getElementById(id);if(el)el.textContent=val;};
set("lbIndex",`${index+1} / ${filteredData.length}`);set("propName",item.filename||"-");set("propCat",item.category||"-");set("propMtime",item.date||"-");set("propSize",formatBytes(item.size));set("propExt",item.ext||"");set("propViews",item.views>0?item.views:"—");set("propUploadedAt",item.uploaded_at||"—");
const camRow=document.getElementById("propCameraRow");const expRow=document.getElementById("propExposureRow");
if(item.camera&&(item.camera.make||item.camera.model)){set("propCamera",`${item.camera.make||""} ${item.camera.model||""}`.trim());if(camRow)camRow.style.display="flex";}else if(camRow)camRow.style.display="none";
const exp=[item.camera?.f_number,item.camera?.exposure,item.camera?.iso,item.camera?.focal].filter(Boolean).join(" • ");
if(exp){set("propExposure",exp);if(expRow)expRow.style.display="flex";}else if(expRow)expRow.style.display="none";
const geoRow=document.getElementById("propGeoRow");const geoBtn=document.getElementById("geoBtn");
if(item.geo&&item.geo.lat&&item.geo.lon){set("propGeo",`${item.geo.lat}, ${item.geo.lon}`);if(geoRow)geoRow.style.display="flex";if(geoBtn)geoBtn.style.display="flex";}else{if(geoRow)geoRow.style.display="none";if(geoBtn)geoBtn.style.display="none";}
const tagsRow=document.getElementById("propTagsRow");const tagsC=document.getElementById("propTags");
if(item.tags&&item.tags.length>0&&tagsC){tagsC.innerHTML=item.tags.map(t=>`<span class="tag-pill" data-tag="${escAttr(t)}" onclick="onPropTagClick(this)">#${esc(t)}</span>`).join("");if(tagsRow)tagsRow.style.display="flex";}else if(tagsRow)tagsRow.style.display="none";}

function onPropTagClick(el){const tag=el.dataset.tag;closeLightbox();setTagFilter(tag);window.scrollTo({top:0,behavior:"smooth"});}

function closeLightbox(updateHash=true){const v=document.getElementById("lbVideoPlayer");if(v){try{v.pause();}catch(e){}v.removeAttribute("src");try{v.load();}catch(e){}}
const c=document.getElementById("lbMediaContainer");if(c)c.innerHTML="";
const s=document.getElementById("lbSpinner");if(s)s.style.display="none";
const lb=document.getElementById("lightbox");if(lb)lb.classList.remove("active","ui-hidden");resetZoom();
if(updateHash&&window.location.hash)history.pushState(null,"",window.location.pathname+window.location.search);}

function navLightbox(dir){const n=activeLbIndex+dir;if(n>=0&&n<filteredData.length)openLightbox(n);}
function toggleUi(){const lb=document.getElementById("lightbox");if(lb)lb.classList.toggle("ui-hidden");}
function prefersReducedMotion(){return window.matchMedia&&window.matchMedia("(prefers-reduced-motion: reduce)").matches;}

function runFlipTransition(sourceEl,onMidpoint){try{const img=sourceEl.querySelector("img, video");if(!img){onMidpoint();return;}
const startRect=(img.tagName==="IMG"?img:sourceEl).getBoundingClientRect();const ghost=document.createElement("div");ghost.className="flip-ghost";
const src=img.tagName==="IMG"?img.src:(img.poster||"");if(src)ghost.innerHTML=`<img src="${escAttr(src)}" alt="">`;else{onMidpoint();return;}
ghost.style.left=startRect.left+"px";ghost.style.top=startRect.top+"px";ghost.style.width=startRect.width+"px";ghost.style.height=startRect.height+"px";
document.body.appendChild(ghost);sourceEl.style.opacity="0";
try{requestAnimationFrame(()=>{try{onMidpoint();}finally{requestAnimationFrame(()=>{ghost.style.opacity="0";ghost.style.transform="scale(1.05)";setTimeout(()=>{try{ghost.remove();}catch(e){}sourceEl.style.opacity="";},400);});}});}catch(e){sourceEl.style.opacity="";try{ghost.remove();}catch(_){}}}catch(e){onMidpoint();}}

function updateZoomTransform(){const c=document.getElementById("lbMediaContainer");if(c)c.style.transform=`translate(${panX}px, ${panY}px) scale(${zoomScale})`;const z=document.getElementById("zoomLevelText");if(z)z.innerText=`${Math.round(zoomScale*100)}%`;}
function zoomAction(d){zoomScale=Math.min(Math.max(1,zoomScale+d),4);if(zoomScale===1){panX=0;panY=0;}updateZoomTransform();}
function resetZoom(){zoomScale=1;panX=0;panY=0;updateZoomTransform();}
function toggleKenBurns(){kenBurnsEnabled=!kenBurnsEnabled;localStorage.setItem("app_kenburns",kenBurnsEnabled?"1":"0");
const t=document.getElementById("kenburnsToggle");if(t)t.style.background=kenBurnsEnabled?"rgba(88,166,255,.5)":"";
const w=document.querySelector(".lb-img-wrap");if(w)w.classList.toggle("kenburns",kenBurnsEnabled);showToast(`Ken Burns: ${kenBurnsEnabled?"ON":"OFF"}`,"info");}

function downloadCurrentOriginal(){const item=filteredData[activeLbIndex];if(!item||!item.url){showToast("URL file tidak tersedia","error");return;}window.open(item.url,"_blank");}

async function copyDirectLink(){const item=filteredData[activeLbIndex];if(!item||!item.url)return;const url=item.url;
if(navigator.clipboard&&window.isSecureContext){try{await navigator.clipboard.writeText(url);showToast("Link disalin ✓","success");return;}catch(e){}}
try{const ta=document.createElement("textarea");ta.value=url;ta.setAttribute("readonly","");ta.style.position="fixed";ta.style.top="-1000px";ta.style.left="-1000px";ta.style.opacity="0";document.body.appendChild(ta);ta.select();ta.setSelectionRange(0,ta.value.length);const ok=document.execCommand("copy");document.body.removeChild(ta);if(ok){showToast("Link disalin ✓","success");return;}}catch(e){}
window.prompt("Salin link (Ctrl/Cmd + C):",url);}

function buildShareUrl(item){if(!item||!item.id)return"";const loc=window.location;if(loc.protocol==="file:")return`#${item.id}`;
let base;try{const u=new URL(loc.href);u.hash="";u.search="";base=u.toString();}catch(e){base=`${loc.origin}${loc.pathname}`;}
return`${base.replace(/#+$/,"")}#${item.id}`;}

async function shareCurrentMedia(){const item=filteredData[activeLbIndex];if(!item){showToast("Tidak ada media","error");return;}const isOnline=window.location.protocol.startsWith("http");const galleryUrl=buildShareUrl(item);const fileUrl=item.url||"";const title=item.title||item.filename||"Media";const text=`${title} — ${item.category||""}`;if(navigator.share){try{const shareUrl=isOnline?galleryUrl:fileUrl;await navigator.share({title:title,text:text,url:shareUrl||undefined});showToast("Berhasil dibagikan ✓","success");return;}catch(err){if(err&&err.name==="AbortError")return;}}showShareDialog(item,galleryUrl,fileUrl,title);}
function showShareDialog(item,galleryUrl,fileUrl,title){const modal=document.createElement("div");modal.className="share-modal";modal.style.cssText="position:fixed;inset:0;z-index:3000;background:rgba(0,0,0,.85);display:flex;align-items:center;justify-content:center;backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);";const shareText=encodeURIComponent(title+" — "+(item.category||""));const encodedFileUrl=encodeURIComponent(fileUrl);const encodedGalleryUrl=encodeURIComponent(galleryUrl);modal.innerHTML='<div style="background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:20px;max-width:420px;width:92%;color:var(--text);max-height:88vh;overflow-y:auto;">'+'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;"><h3 style="font-size:1rem;font-weight:700;">🔗 Bagikan Media</h3><button onclick="this.closest(\'.share-modal\').remove()" style="background:none;border:none;color:var(--text);font-size:1.4rem;cursor:pointer;">&times;</button></div>'+'<div style="font-size:.78rem;color:var(--text-muted);margin-bottom:14px;">Pilih cara berbagi:</div>'+'<div style="display:flex;flex-direction:column;gap:8px;">'+'<button onclick="copyToClipboard(\''+fileUrl+'\');this.closest(\'.share-modal\').remove();" style="display:flex;align-items:center;gap:10px;padding:12px;border-radius:10px;background:rgba(88,166,255,.1);border:1px solid rgba(88,166,255,.3);color:var(--text);cursor:pointer;font-size:.85rem;text-align:left;width:100%;"><span style="font-size:1.2rem;">📋</span><div style="flex:1;"><div style="font-weight:600;">Copy Link File</div><div style="font-size:.7rem;color:var(--text-muted);">URL file langsung dari Catbox</div></div></button>'+'<button onclick="copyToClipboard(\''+galleryUrl+'\');this.closest(\'.share-modal\').remove();" style="display:flex;align-items:center;gap:10px;padding:12px;border-radius:10px;background:rgba(74,222,128,.1);border:1px solid rgba(74,222,128,.3);color:var(--text);cursor:pointer;font-size:.85rem;text-align:left;width:100%;"><span style="font-size:1.2rem;">🌐</span><div style="flex:1;"><div style="font-weight:600;">Copy Link Galeri</div><div style="font-size:.7rem;color:var(--text-muted);">Link ke halaman galeri (perlu online)</div></div></button>'+'<div style="height:1px;background:var(--border);margin:4px 0;"></div>'+'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:4px;">'+'<a href="https://wa.me/?text='+shareText+'%20'+encodedFileUrl+'" target="_blank" rel="noopener" style="display:flex;flex-direction:column;align-items:center;gap:4px;padding:10px 4px;border-radius:10px;background:rgba(37,211,102,.1);border:1px solid rgba(37,211,102,.3);color:var(--text);text-decoration:none;font-size:.65rem;"><span style="font-size:1.3rem;">💬</span>WhatsApp</a>'+'<a href="https://t.me/share/url?url='+encodedFileUrl+'&text='+shareText+'" target="_blank" rel="noopener" style="display:flex;flex-direction:column;align-items:center;gap:4px;padding:10px 4px;border-radius:10px;background:rgba(0,136,204,.1);border:1px solid rgba(0,136,204,.3);color:var(--text);text-decoration:none;font-size:.65rem;"><span style="font-size:1.3rem;">✈️</span>Telegram</a>'+'<a href="https://twitter.com/intent/tweet?text='+shareText+'&url='+encodedFileUrl+'" target="_blank" rel="noopener" style="display:flex;flex-direction:column;align-items:center;gap:4px;padding:10px 4px;border-radius:10px;background:rgba(29,161,242,.1);border:1px solid rgba(29,161,242,.3);color:var(--text);text-decoration:none;font-size:.65rem;"><span style="font-size:1.3rem;">🐦</span>Twitter</a>'+'<a href="https://www.facebook.com/sharer/sharer.php?u='+encodedFileUrl+'" target="_blank" rel="noopener" style="display:flex;flex-direction:column;align-items:center;gap:4px;padding:10px 4px;border-radius:10px;background:rgba(24,119,242,.1);border:1px solid rgba(24,119,242,.3);color:var(--text);text-decoration:none;font-size:.65rem;"><span style="font-size:1.3rem;">📘</span>Facebook</a>'+'</div></div></div>';modal.onclick=(e)=>{if(e.target===modal)modal.remove();};document.body.appendChild(modal);}
function copyToClipboard(text){if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(text).then(()=>{showToast("Link disalin ✓","success");}).catch(()=>fallbackCopy(text));}else{fallbackCopy(text);}}
function fallbackCopy(text){const ta=document.createElement("textarea");ta.value=text;ta.setAttribute("readonly","");ta.style.position="fixed";ta.style.top="-1000px";document.body.appendChild(ta);ta.select();try{document.execCommand("copy");showToast("Link disalin ✓","success");}catch(e){window.prompt("Salin link (Ctrl/Cmd + C):",text);}document.body.removeChild(ta);}

function openGeoMap(){const item=filteredData[activeLbIndex];if(item&&item.geo)window.open(`https://www.google.com/maps?q=${item.geo.lat},${item.geo.lon}`,"_blank");}

function setupGestures(){const lbBody=document.getElementById("lightboxBody");if(!lbBody)return;
let startT=[],pinch0=0,scale0=1,isDragging=false,dragX0=0,dragY0=0,lastTap=0;
const dist=(a,b)=>Math.hypot(a.clientX-b.clientX,a.clientY-b.clientY);
lbBody.addEventListener("touchstart",e=>{if(e.target.closest("video, .lb-nav, .media-spinner"))return;startT=Array.from(e.touches);
if(e.touches.length===2){pinch0=dist(e.touches[0],e.touches[1]);scale0=zoomScale;}else if(e.touches.length===1){isDragging=true;dragX0=e.touches[0].clientX-panX;dragY0=e.touches[0].clientY-panY;}},{passive:true});
lbBody.addEventListener("touchmove",e=>{if(e.target.closest("video, .lb-nav, .media-spinner"))return;
if(e.touches.length===2&&pinch0>0){const s=dist(e.touches[0],e.touches[1])/pinch0;zoomScale=Math.min(Math.max(1,scale0*s),4);if(zoomScale===1){panX=0;panY=0;}updateZoomTransform();}
else if(e.touches.length===1&&zoomScale>1&&isDragging){panX=e.touches[0].clientX-dragX0;panY=e.touches[0].clientY-dragY0;updateZoomTransform();}},{passive:true});
lbBody.addEventListener("touchend",e=>{if(e.target.closest("video, .lb-nav, .media-spinner"))return;
if(e.touches.length===0){const now=Date.now(),tE=e.changedTouches[0],tS=startT[0];
if(tS){const dx=tE.clientX-tS.clientX,dy=tE.clientY-tS.clientY;
if(zoomScale===1&&Math.abs(dx)>50&&Math.abs(dx)>Math.abs(dy)){if(dx<0)navLightbox(1);else navLightbox(-1);return;}
if(Math.abs(dx)<10&&Math.abs(dy)<10){if(now-lastTap<300){if(zoomScale>1)resetZoom();else{zoomScale=2.2;updateZoomTransform();}lastTap=0;return;}
lastTap=now;setTimeout(()=>{if(Date.now()-lastTap>=280&&lastTap!==0)toggleUi();},290);}}
isDragging=false;}},{passive:true});}

window.addEventListener("keydown",e=>{const lb=document.getElementById("lightbox");if(!lb||!lb.classList.contains("active"))return;
switch(e.key){case"Escape":closeLightbox();break;case"ArrowLeft":navLightbox(-1);break;case"ArrowRight":navLightbox(1);break;
case" ":e.preventDefault();const v=document.getElementById("lbVideoPlayer");if(v){if(v.paused)v.play();else v.pause();}break;
case"+":case"=":zoomAction(0.4);break;case"-":case"_":zoomAction(-0.4);break;case"0":resetZoom();break;}});

let leafletLoadingPromise=null;
function loadLeaflet(){if(window.L)return Promise.resolve();if(leafletLoadingPromise)return leafletLoadingPromise;
leafletLoadingPromise=new Promise((res,rej)=>{const css=document.createElement("link");css.rel="stylesheet";css.href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";document.head.appendChild(css);
const sc=document.createElement("script");sc.src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";sc.onload=res;sc.onerror=()=>rej(new Error("Leaflet gagal dimuat"));document.head.appendChild(sc);});
return leafletLoadingPromise;}

function openMapModal(){const m=document.getElementById("mapModal");if(m)m.classList.add("active");setTimeout(()=>loadLeaflet().then(initLeafletMap).catch(()=>showToast("Gagal memuat peta","error")),100);}
function closeMapModal(){const m=document.getElementById("mapModal");if(m)m.classList.remove("active");}

function initLeafletMap(){const geo=RAW_DATA.filter(d=>d.geo&&d.geo.lat&&d.geo.lon);
if(!leafletMap){leafletMap=L.map("mapView").setView([-2.5,118.0],5);L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:19,attribution:"&copy; OpenStreetMap"}).addTo(leafletMap);}else leafletMap.invalidateSize();
mapMarkers.forEach(m=>leafletMap.removeLayer(m));mapMarkers=[];
if(!geo.length)return;const bounds=[];
geo.forEach(item=>{const mk=L.marker([item.geo.lat,item.geo.lon]).addTo(leafletMap);
const src=item.type==="video"?(item.video_thumb||""):item.thumb;const img=src?`<img src="${escAttr(src)}" style="width:120px;height:80px;object-fit:cover;border-radius:4px;margin-bottom:4px;" /><br/>`:"";
mk.bindPopup(`<div style="font-size:.8rem;text-align:center;">${img}<b>${esc(item.title)}</b><br/><span style="color:#666;">${esc(item.date)}</span><br/><a href="#${escAttr(item.id)}" onclick="closeMapModal()" style="color:var(--accent);text-decoration:none;font-weight:600;">Lihat Detail</a></div>`);
mapMarkers.push(mk);bounds.push([item.geo.lat,item.geo.lon]);});
if(bounds.length)leafletMap.fitBounds(bounds,{padding:[30,30]});}

function openStats(){const images=RAW_DATA.filter(d=>d.type==="image");const videos=RAW_DATA.filter(d=>d.type==="video");
const totalBytes=RAW_DATA.reduce((a,c)=>a+(c.size||0),0);const totalGB=(totalBytes/(1024*1024*1024)).toFixed(2);
const totalViews=RAW_DATA.reduce((a,c)=>a+(c.views||0),0);
const sorted=[...RAW_DATA].sort((a,b)=>(b.views||0)-(a.views||0)).slice(0,10);
const topHtml=sorted.map(item=>{const src=item.type==="video"?(item.video_thumb||""):item.thumb;
const img=src?`<img src="${escAttr(src)}" alt="" loading="lazy">`:`<div style="width:56px;height:56px;border-radius:6px;background:var(--surface-variant);flex-shrink:0;"></div>`;
return `<div class="top-item" data-id="${escAttr(item.id)}" onclick="onTopItemClick(this)">${img}<div class="top-item-info"><div class="top-item-title">${esc(item.title)}</div><div class="top-item-meta">👁️ ${item.views||0} kali • ${esc(item.category)} • ${esc(item.date)}</div></div></div>`;}).join("");
const sc=document.getElementById("statsContent");if(!sc)return;
sc.innerHTML=`<div style="background:var(--surface);padding:14px;border-radius:10px;border:1px solid var(--border);display:flex;justify-content:space-around;text-align:center;flex-wrap:wrap;gap:12px;"><div><div style="font-size:1.2rem;font-weight:700;">${images.length}</div><span style="font-size:.75rem;color:var(--text-muted);">🖼️ Gambar</span></div><div><div style="font-size:1.2rem;font-weight:700;">${videos.length}</div><span style="font-size:.75rem;color:var(--text-muted);">🎬 Video</span></div><div><div style="font-size:1.2rem;font-weight:700;">${totalGB} GB</div><span style="font-size:.75rem;color:var(--text-muted);">💾 Total</span></div><div><div style="font-size:1.2rem;font-weight:700;">${totalViews}</div><span style="font-size:.75rem;color:var(--text-muted);">👁️ Views</span></div></div><div><div style="font-size:.85rem;font-weight:700;margin-bottom:6px;">🔥 Top 10 Paling Banyak Dilihat</div><div class="top-list">${topHtml||"<div style='color:var(--text-muted);font-size:.8rem;'>Belum ada data views.</div>"}</div></div><div style="font-size:.72rem;color:var(--text-muted);text-align:center;">Statistik views via Abacus.<br>Namespace: <code>${esc(COUNTER_NAMESPACE)}</code></div>`;
const sm=document.getElementById("statsModal");if(sm)sm.classList.add("active");}
function closeStats(){const sm=document.getElementById("statsModal");if(sm)sm.classList.remove("active");}

function onTopItemClick(el){const id=el.dataset.id;closeStats();let idx=filteredData.findIndex(x=>x.id===id);
if(idx===-1){currentCategory="Semua";currentMonth="Semua";currentTag="Semua";currentMediaType="all";searchQuery="";dateFrom="";dateTo="";
const si=document.getElementById("searchInput");if(si)si.value="";
const df=document.getElementById("dateFrom");if(df)df.value="";
const dt=document.getElementById("dateTo");if(dt)dt.value="";
const chip=document.getElementById("activeTagChip");if(chip)chip.style.display="none";
document.querySelectorAll(".type-switcher .sw-btn").forEach(b=>b.classList.remove("active"));
const ta=document.getElementById("type-all");if(ta)ta.classList.add("active");
setupCategories();setupModalMonthFilters();setupModalTagFilters();applyFilters();
idx=filteredData.findIndex(x=>x.id===id);}
if(idx!==-1)openLightbox(idx);}

(function restoreKenBurns(){const s=localStorage.getItem("app_kenburns");if(s==="1"){kenBurnsEnabled=true;const t=document.getElementById("kenburnsToggle");if(t)t.style.background="rgba(88,166,255,.5)";}})();

init();
</script>
</body>
</html>
"""


# ============================================================================
# HTML TEMPLATE — MANAGER
# ============================================================================

MANAGER_TEMPLATE = r"""<!DOCTYPE html>
<html lang="id" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Catbox Manager</title>
<style>
:root{--bg:#0d1117;--surface:#161b22;--border:#30363d;--text:#c9d1d9;--muted:#8b949e;--accent:#58a6ff;--danger:#f85149;--success:#3fb950;}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:var(--bg);color:var(--text);padding:16px;font-size:14px;}
h1{font-size:1.4rem;margin-bottom:4px;}
.sub{color:var(--muted);font-size:.85rem;margin-bottom:16px;}
.bar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px;}
input,select,button{padding:8px 12px;border-radius:6px;border:1px solid var(--border);background:var(--surface);color:var(--text);font-size:.85rem;}
input{flex:1;min-width:200px;}
button{cursor:pointer;transition:.15s;}
button:hover{background:#21262d;}
button.primary{background:var(--accent);color:#fff;border-color:var(--accent);font-weight:600;}
button.danger{background:rgba(248,81,73,.15);color:var(--danger);border-color:var(--danger);}
button.success{background:rgba(63,185,80,.15);color:var(--success);border-color:var(--success);}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:16px;}
.stat{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:12px;text-align:center;}
.stat b{display:block;font-size:1.4rem;color:var(--accent);}
.stat span{font-size:.75rem;color:var(--muted);}
table{width:100%;border-collapse:collapse;background:var(--surface);border-radius:8px;overflow:hidden;}
th,td{padding:10px;text-align:left;border-bottom:1px solid var(--border);font-size:.82rem;}
th{background:#0d1117;color:var(--muted);font-weight:600;text-transform:uppercase;font-size:.7rem;letter-spacing:.5px;}
tr:hover{background:#1c2128;}
tr.blacklisted{opacity:.4;text-decoration:line-through;}
tr.blacklisted td:first-child::before{content:"🗑️ ";}
.thumb{width:40px;height:40px;object-fit:cover;border-radius:4px;background:#0d1117;}
.url{color:var(--accent);text-decoration:none;font-size:.78rem;word-break:break-all;}
.url:hover{text-decoration:underline;}
.tag{display:inline-block;background:rgba(88,166,255,.15);color:var(--accent);padding:2px 6px;border-radius:4px;font-size:.68rem;margin:2px 2px 0 0;}
.empty{text-align:center;padding:60px 20px;color:var(--muted);}
.toast{position:fixed;bottom:20px;right:20px;background:#1c2128;border:1px solid var(--border);color:var(--text);padding:12px 18px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,.4);animation:slideIn .3s ease-out;z-index:1000;}
@keyframes slideIn{from{transform:translateX(100%);}to{transform:translateX(0);}}
</style>
</head>
<body>

<h1>🗑️ Catbox Manager</h1>
<p class="sub">Kelola file di Catbox. Tandai untuk dihapus, lalu download <code>deleted.json</code>.</p>

<div class="stats" id="stats"></div>

<div class="bar">
  <input type="text" id="search" placeholder="🔍 Cari nama file / tag / kategori..." oninput="render()">
  <select id="filter-type" onchange="render()">
    <option value="all">Semua Tipe</option>
    <option value="image">🖼️ Gambar</option>
    <option value="video">🎬 Video</option>
  </select>
  <select id="filter-status" onchange="render()">
    <option value="all">Semua Status</option>
    <option value="active">✅ Aktif</option>
    <option value="blacklist">🗑️ Blacklist</option>
  </select>
</div>

<div class="bar">
  <button class="primary" onclick="downloadBlacklist()">⬇️ Download deleted.json</button>
  <button class="danger" onclick="clearBlacklist()">🗑️ Bersihkan Blacklist</button>
  <button onclick="openCatboxManager()">🌐 Buka Catbox Manager</button>
</div>

<table id="table">
  <thead><tr><th>Thumb</th><th>Nama</th><th>Kategori</th><th>Tanggal</th><th>Ukuran</th><th>URL</th><th>Aksi</th></tr></thead>
  <tbody id="tbody"></tbody>
</table>

<div class="empty" id="empty" style="display:none;">Tidak ada file yang cocok.</div>

<script>
const DATA = /*DATA_PLACEHOLDER*/;
const DELETED_FROM_FILE = /*DELETED_PLACEHOLDER*/;
const CATBOX_MANAGE_URL = "https://catbox.moe/user/manage.php";

let blacklist = {};
try { blacklist = JSON.parse(localStorage.getItem("catbox_blacklist") || "{}"); } catch (e) { blacklist = {}; }
Object.keys(DELETED_FROM_FILE || {}).forEach(k => { if (!blacklist[k]) blacklist[k] = DELETED_FROM_FILE[k]; });

function saveBlacklist(){ localStorage.setItem("catbox_blacklist", JSON.stringify(blacklist)); }
function formatBytes(b){ if (!b) return "0 B"; const k=1024,s=["B","KB","MB","GB"]; const i=Math.floor(Math.log(b)/Math.log(k)); return parseFloat((b/Math.pow(k,i)).toFixed(1))+" "+s[i]; }
function esc(s){ return String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }

function renderStats() {
  const total = DATA.length;
  const images = DATA.filter(d => d.type === "image").length;
  const videos = DATA.filter(d => d.type === "video").length;
  const bl = Object.keys(blacklist).length;
  const totalSize = DATA.reduce((a,c) => a + (c.size || 0), 0);
  document.getElementById("stats").innerHTML = `<div class="stat"><b>${total}</b><span>Total File</span></div><div class="stat"><b>${images}</b><span>🖼️ Gambar</span></div><div class="stat"><b>${videos}</b><span>🎬 Video</span></div><div class="stat"><b>${bl}</b><span>🗑️ Blacklist</span></div><div class="stat"><b>${formatBytes(totalSize)}</b><span>Total Ukuran</span></div>`;
}

function render() {
  const q = document.getElementById("search").value.toLowerCase().trim();
  const typeF = document.getElementById("filter-type").value;
  const statusF = document.getElementById("filter-status").value;
  let items = DATA.filter(item => {
    if (typeF !== "all" && item.type !== typeF) return false;
    const isBl = !!blacklist[item.id];
    if (statusF === "active" && isBl) return false;
    if (statusF === "blacklist" && !isBl) return false;
    if (q) {
      const s = [item.title, item.filename, item.category, ...(item.tags || [])].join(" ").toLowerCase();
      if (!s.includes(q)) return false;
    }
    return true;
  });
  const tb = document.getElementById("tbody");
  const em = document.getElementById("empty");
  if (!items.length) { tb.innerHTML = ""; em.style.display = "block"; return; }
  em.style.display = "none";
  tb.innerHTML = items.map(item => {
    const isBl = !!blacklist[item.id];
    const thumb = item.type === "video" ? (item.video_thumb || "") : item.thumb;
    const tags = (item.tags || []).slice(0, 3).map(t => `<span class="tag">#${esc(t)}</span>`).join("");
    return `<tr class="${isBl ? 'blacklisted' : ''}"><td><img class="thumb" src="${esc(thumb)}" loading="lazy" onerror="this.style.background='#30363d';this.src='';"></td><td><div><b>${esc(item.title)}</b></div><div style="color:var(--muted);font-size:.72rem;">${esc(item.filename)}</div><div>${tags}</div></td><td>${esc(item.category)}</td><td>${esc(item.date)}</td><td>${formatBytes(item.size)}</td><td><a class="url" href="${esc(item.url)}" target="_blank" rel="noopener">${esc(item.url)}</a></td><td>${isBl ? `<button class="success" onclick="toggleBlacklist('${item.id}')">↩️ Pulihkan</button>` : `<button class="danger" onclick="toggleBlacklist('${item.id}')">🗑️ Hapus</button>`}</td></tr>`;
  }).join("");
}

function toggleBlacklist(id) {
  if (blacklist[id]) { delete blacklist[id]; showToast("Item dipulihkan"); }
  else {
    const item = DATA.find(d => d.id === id);
    if (!item) return;
    if (!confirm(`Tandai "${item.title}" untuk dihapus?\n\nFile di Catbox TIDAK otomatis terhapus. Setelah download deleted.json, buka ${CATBOX_MANAGE_URL} untuk hapus manual.`)) return;
    blacklist[id] = { filename: item.filename, url: item.url, deleted_at: new Date().toISOString(), reason: "user" };
    showToast("Item ditandai untuk dihapus");
  }
  saveBlacklist(); renderStats(); render();
}

function downloadBlacklist() {
  if (!Object.keys(blacklist).length) { showToast("Blacklist kosong"); return; }
  const blob = new Blob([JSON.stringify(blacklist, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = "deleted.json"; a.click();
  URL.revokeObjectURL(url);
  showToast("deleted.json didownload");
}

function clearBlacklist() {
  if (!Object.keys(blacklist).length) { showToast("Blacklist sudah kosong"); return; }
  if (!confirm("Bersihkan semua blacklist?")) return;
  blacklist = {};
  saveBlacklist(); renderStats(); render();
  showToast("Blacklist dibersihkan");
}

function openCatboxManager() { window.open(CATBOX_MANAGE_URL, "_blank"); }

function showToast(msg) {
  const t = document.createElement("div");
  t.className = "toast"; t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 2500);
}

renderStats();
render();
</script>
</body>
</html>
"""


# ============================================================================
# HTML_TEMPLATE — Gabungan
# ============================================================================

HTML_TEMPLATE = HTML_TEMPLATE_PART1 + HTML_TEMPLATE_PART2 + HTML_TEMPLATE_PART3


# ============================================================================
# CALLBACKS UNTUK MENU
# ============================================================================

def run_upload(cfg):
    apply_config(cfg)
    print(f"\n{'='*54}")
    print(f"  🚀 MENJALANKAN UPLOAD & GENERATE")
    print(f"{'='*54}\n")
    data = scan_and_upload()
    if not data:
        print("[!] Tidak ada data yang diproses.")
        print("[!] Kemungkinan: folder kosong, atau semua upload gagal.")
        return
    json_str = _escape_json_for_inline_script(data)
    rendered_html = HTML_TEMPLATE.replace("/*DATA_PLACEHOLDER*/", json_str)
    rendered_html = rendered_html.replace("/*ITEMS_PER_PAGE_PLACEHOLDER*/", str(ITEMS_PER_PAGE))
    rendered_html = rendered_html.replace("/*COUNTER_API_PLACEHOLDER*/", json.dumps(COUNTER_API_BASE))
    rendered_html = rendered_html.replace("/*COUNTER_NS_PLACEHOLDER*/", json.dumps(COUNTER_NAMESPACE))
    judul = cfg["judul_project"]
    rendered_html = inject_project_title(rendered_html, judul)
    output = cfg.get("output_html", "index.html")
    with open(output, "w", encoding="utf-8") as f:
        f.write(rendered_html)
    print(f"\n\033[92m[v] Sukses! File '{output}' berhasil dibuat.\033[0m")
    print(f"\033[96m[v] Total entri galeri: {len(data)}\033[0m")
    print(f"\033[96m[v] Judul project: {judul}\033[0m\n")

    try:
        generate_manager_html(cfg)
    except Exception as e:
        print(f"\033[93m[!] Gagal generate manager.html: {e}\033[0m")

    # Tanya upload GitHub
    if cfg.get("github_auto_upload") and cfg.get("github_repo"):
        default_choice = "y"
        hint = "[y]"
    else:
        default_choice = "n"
        hint = "[n]"


    # Tanya mau upload ke GitHub
    print()
    konfirm = input(f"\033[96m📤 Upload hasil ke GitHub sekarang? (y/n) \033[90m[n]\033[0m: ").strip().lower()
    if konfirm in ("y", "ya", "yes"):
        tool_upload_github(cfg)


def clear_cache_callback():
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
        print(f"\033[92m[v] {CACHE_FILE} dihapus.\033[0m")
    else:
        print(f"\033[93m[!] {CACHE_FILE} tidak ditemukan.\033[0m")
    input("\033[90m[Enter untuk kembali ke menu]\033[0m")


def cleanup_thumbs_callback():
    cleanup_old_thumbnails(max_age_days=0)
    print(f"\033[92m[v] Cleanup thumbnail selesai.\033[0m")


def generate_manager_callback(cfg):
    apply_config(cfg)
    generate_manager_html(cfg)


def reset_blacklist_callback():
    if os.path.exists(DELETED_FILE):
        konfirm = input(f"\033[93mHapus semua blacklist? (y/n): \033[0m").strip().lower()
        if konfirm in ("y", "ya", "yes"):
            os.remove(DELETED_FILE)
            print(f"\033[92m[v] {DELETED_FILE} dihapus.\033[0m")
    else:
        print(f"\033[93m[!] {DELETED_FILE} tidak ditemukan.\033[0m")
    input("\033[90m[Enter untuk kembali ke menu]\033[0m")


def generate_manager_html(cfg):
    cache = load_cache()
    if not cache:
        print(f"{C_YELLOW}[!] uploads_cache.json kosong. Jalankan upload dulu.{C_RESET}")
        return False
    deleted = load_deleted()
    items = []
    for rel_path, entry in cache.items():
        if not isinstance(entry, dict):
            continue
        meta = entry.get("meta", {})
        ext = rel_path.rsplit(".", 1)[-1].upper() if "." in rel_path else ""
        media_type = "video" if ext in {"MP4", "MKV", "WEBM", "MOV"} else "image"
        media_id = f"media_{hashlib.md5(rel_path.encode('utf-8')).hexdigest()[:12]}"
        thumb = entry.get("thumb_url") or ""
        if not thumb and media_type == "image" and entry.get("url"):
            thumb = f"https://wsrv.nl/?url={entry['url']}&w=100&q=70&output=webp"
        if media_type == "video":
            thumb = entry.get("video_thumb_url") or thumb
        items.append({
            "id": media_id,
            "title": rel_path.rsplit("/", 1)[-1].rsplit(".", 1)[0].replace("_", " ").title(),
            "filename": rel_path.rsplit("/", 1)[-1],
            "category": (rel_path.rsplit("/", 1)[0] if "/" in rel_path else "General"),
            "date": meta.get("date", ""),
            "size": entry.get("file_size", 0),
            "type": media_type,
            "url": entry.get("url", ""),
            "thumb": thumb,
            "video_thumb": entry.get("video_thumb_url"),
            "tags": meta.get("tags", []),
        })
    items.sort(key=lambda x: x["date"], reverse=True)
    json_str = json.dumps(items, ensure_ascii=False)
    json_str = json_str.replace("</", "<\\/")
    html = MANAGER_TEMPLATE.replace("/*DATA_PLACEHOLDER*/", json_str)
    html = html.replace("/*DELETED_PLACEHOLDER*/", json.dumps(deleted, ensure_ascii=False))
    with open(OUTPUT_MANAGER, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"{C_GREEN}[v] Sukses! File '{OUTPUT_MANAGER}' dibuat ({len(items)} item).{C_RESET}")
    return True


def tool_fix_cache(cfg):
    """Bersihkan cache entri rusak (tanpa URL)."""
    print(f"\n{C_CYAN}━━━ FIX BROKEN CACHE ━━━{C_RESET}\n")

    cache = load_cache()
    if not cache:
        print(f"{C_YELLOW}[!] Cache kosong.{C_RESET}")
        return

    total = len(cache)
    before = total
    cleaned = {}

    for rel_path, entry in cache.items():
        if not isinstance(entry, dict):
            continue
        # Skip kalau URL kosong
        if not entry.get("url"):
            continue
        cleaned[rel_path] = entry

    removed = before - len(cleaned)
    if removed == 0:
        print(f"{C_GREEN}[✓] Cache sehat. Tidak ada yang perlu dibersihkan.{C_RESET}")
        return

    print(f"{C_GRAY}Ditemukan {removed} entri rusak.{C_RESET}")
    konfirm = input(f"{C_CYAN}Hapus {removed} entri rusak? (y/n): {C_RESET}").strip().lower()
    if konfirm in ("y", "ya", "yes"):
        save_cache(cleaned)
        print(f"{C_GREEN}[✓] Cache dibersihkan. {len(cleaned)} entri tersisa.{C_RESET}")
    else:
        print(f"{C_YELLOW}Dibatalkan.{C_RESET}")

# ============================================================================
# TOOLS & UTILITIES
# ============================================================================

def tool_upload_github(cfg):
    """Upload index.html + manager.html ke GitHub."""
    import subprocess

    print(f"\n{C_CYAN}━━━ UPLOAD KE GITHUB ━━━{C_RESET}\n")

    index_exists = os.path.exists(OUTPUT_HTML)
    manager_exists = os.path.exists(OUTPUT_MANAGER)
    if not index_exists and not manager_exists:
        print(f"{C_YELLOW}[!] Tidak ada file HTML. Jalankan upload dulu (menu 3).{C_RESET}")
        return

    # Ambil config GitHub
    gh_user = cfg.get("github_username", "")
    gh_repo = cfg.get("github_repo", "")
    gh_token = cfg.get("github_token", "")
    gh_branch = cfg.get("github_branch", "main")

    # Bangun URL otomatis dari config
    if gh_user and gh_repo:
        if gh_token:
            default_url = f"https://{gh_user}:{gh_token}@github.com/{gh_user}/{gh_repo}.git"
            display_url = f"https://github.com/{gh_user}/{gh_repo}.git"
            print(f"{C_GREEN}Repo (dari config):{C_RESET} {display_url}")
            use_default = input(f"{C_CYAN}Pakai repo ini? (y/n) {C_GRAY}[y]{C_RESET}: ").strip().lower()
            if use_default in ("", "y", "ya", "yes"):
                repo_url = default_url
            else:
                repo_url = input(f"{C_CYAN}Repo URL: {C_RESET}").strip()
        else:
            default_url = f"https://github.com/{gh_user}/{gh_repo}.git"
            print(f"{C_GREEN}Repo (dari config):{C_RESET} {default_url}")
            use_default = input(f"{C_CYAN}Pakai repo ini? (y/n) {C_GRAY}[y]{C_RESET}: ").strip().lower()
            if use_default in ("", "y", "ya", "yes"):
                repo_url = default_url
            else:
                repo_url = input(f"{C_CYAN}Repo URL: {C_RESET}").strip()
    else:
        print(f"{C_YELLOW}[i] GitHub belum di-setup. Jalankan menu 1 (Wizard) untuk setup.{C_RESET}")
        repo_url = input(f"{C_CYAN}Repo URL {C_GRAY}(https://github.com/user/repo.git){C_RESET}: ").strip()

    if not repo_url:
        print(f"{C_YELLOW}Dibatalkan.{C_RESET}")
        return

    print(f"{C_GREEN}File yang akan di-upload:{C_RESET}")
    if index_exists:
        print(f"  ✓ {OUTPUT_HTML} ({os.path.getsize(OUTPUT_HTML) / 1024:.1f} KB)")
    if manager_exists:
        print(f"  ✓ {OUTPUT_MANAGER} ({os.path.getsize(OUTPUT_MANAGER) / 1024:.1f} KB)")
    print()

    branch = input(f"{C_CYAN}Branch {C_GRAY}[{gh_branch}]{C_RESET}: ").strip() or gh_branch
    commit_msg = input(f"{C_CYAN}Commit message {C_GRAY}[Update galeri]{C_RESET}: ").strip() or "Update galeri"

    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print(f"{C_RED}[!] Git tidak terinstall. Install: pkg install git{C_RESET}")
        return

    deploy_dir = tempfile.mkdtemp(prefix="gallery_deploy_")
    print(f"\n{C_GRAY}[i] Working dir: {deploy_dir}{C_RESET}")

    try:
        print(f"{C_CYAN}[1/5] Clone repository...{C_RESET}")
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "-b", branch, repo_url, deploy_dir],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, deploy_dir],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode != 0:
                print(f"{C_RED}[!] Gagal clone: {result.stderr[:200]}{C_RESET}")
                return

        print(f"{C_CYAN}[2/5] Copy file...{C_RESET}")
        if index_exists:
            shutil.copy(OUTPUT_HTML, os.path.join(deploy_dir, "index.html"))
        if manager_exists:
            shutil.copy(OUTPUT_MANAGER, os.path.join(deploy_dir, "manager.html"))

        print(f"{C_CYAN}[3/5] Setup git...{C_RESET}")
        subprocess.run(["git", "-C", deploy_dir, "config", "user.email", "bot@local"], capture_output=True)
        subprocess.run(["git", "-C", deploy_dir, "config", "user.name", "AutoBot"], capture_output=True)

        print(f"{C_CYAN}[4/5] Commit...{C_RESET}")
        subprocess.run(["git", "-C", deploy_dir, "add", "-A"], capture_output=True)
        commit_result = subprocess.run(
            ["git", "-C", deploy_dir, "commit", "-m", commit_msg],
            capture_output=True, text=True
        )
        if "nothing to commit" in (commit_result.stdout + commit_result.stderr):
            print(f"{C_YELLOW}[i] Tidak ada perubahan.{C_RESET}")
            return

        print(f"{C_CYAN}[5/5] Push ke {branch}...{C_RESET}")
        push_result = subprocess.run(
            ["git", "-C", deploy_dir, "push", "origin", branch],
            capture_output=True, text=True, timeout=120
        )
        if push_result.returncode == 0:
            print(f"\n{C_GREEN}[✓] Berhasil upload ke GitHub!{C_RESET}")
            print(f"{C_GRAY}  Repo: {repo_url.split('@')[-1] if '@' in repo_url else repo_url}{C_RESET}")
            print(f"{C_GRAY}  Branch: {branch}{C_RESET}")
            if gh_user and gh_repo:
                print(f"\n{C_GRAY}GitHub Pages (kalau aktif):{C_RESET}")
                print(f"{C_CYAN}  https://{gh_user}.github.io/{gh_repo}/{C_RESET}")
        else:
            print(f"{C_RED}[!] Gagal push: {push_result.stderr[:300]}{C_RESET}")
            print(f"{C_GRAY}Pastikan token valid dan scope = repo.{C_RESET}")
    except subprocess.TimeoutExpired:
        print(f"{C_RED}[!] Timeout. Cek koneksi internet.{C_RESET}")
    except Exception as e:
        print(f"{C_RED}[!] Error: {e}{C_RESET}")
    finally:
        shutil.rmtree(deploy_dir, ignore_errors=True)


def tool_compress_html(cfg):
    """Compress HTML (hapus komentar, whitespace)."""
    print(f"\n{C_CYAN}━━━ COMPRESS HTML ━━━{C_RESET}\n")

    if not os.path.exists(OUTPUT_HTML):
        print(f"{C_YELLOW}[!] {OUTPUT_HTML} belum ada.{C_RESET}")
        return

    orig_size = os.path.getsize(OUTPUT_HTML)
    print(f"{C_GRAY}Original: {orig_size / 1024:.1f} KB{C_RESET}")

    with open(OUTPUT_HTML, "r", encoding="utf-8") as f:
        html = f.read()

    data_blocks = re.findall(r'(const RAW_DATA = )(\[.*?\])(;)', html, re.DOTALL)
    placeholders = {}
    for i, (pre, data, post) in enumerate(data_blocks):
        ph = f"___DATA_BLOCK_{i}___"
        placeholders[ph] = data
        html = html.replace(pre + data + post, pre + ph + post)

    html = re.sub(r'/\*.*?\*/', '', html, flags=re.DOTALL)
    html = re.sub(r'\s+', ' ', html)
    html = re.sub(r'\s*([{};:,])\s*', r'\1', html)
    html = re.sub(r'>\s+<', '><', html)

    for ph, data in placeholders.items():
        html = html.replace(ph, data)

    out_file = OUTPUT_HTML.replace(".html", ".min.html")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html)

    new_size = os.path.getsize(out_file)
    saved = orig_size - new_size
    pct = (saved / orig_size) * 100 if orig_size > 0 else 0

    print(f"{C_GRAY}Compressed: {new_size / 1024:.1f} KB{C_RESET}")
    print(f"{C_GREEN}[✓] Hemat: {saved / 1024:.1f} KB ({pct:.1f}%){C_RESET}")
    print(f"{C_GRAY}Output: {out_file}{C_RESET}")


def tool_export_csv(cfg):
    """Export data galeri ke CSV."""
    import csv

    print(f"\n{C_CYAN}━━━ EXPORT CSV ━━━{C_RESET}\n")

    cache = load_cache()
    if not cache:
        print(f"{C_YELLOW}[!] Cache kosong. Jalankan upload dulu.{C_RESET}")
        return

    out_file = "gallery_export.csv"
    rows = []
    for rel_path, entry in cache.items():
        if not isinstance(entry, dict):
            continue
        meta = entry.get("meta", {})
        rows.append({
            "filename": rel_path.rsplit("/", 1)[-1],
            "path": rel_path,
            "url": entry.get("url", ""),
            "thumb_url": entry.get("thumb_url", ""),
            "size_bytes": entry.get("file_size", 0),
            "date": meta.get("date", ""),
            "year": meta.get("year", ""),
            "month": meta.get("month_display", ""),
            "tags": ", ".join(meta.get("tags", [])),
            "camera_make": meta.get("exif", {}).get("camera_make", ""),
            "camera_model": meta.get("exif", {}).get("camera_model", ""),
        })

    with open(out_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"{C_GREEN}[✓] Export {len(rows)} item ke: {out_file}{C_RESET}")


def tool_backup_project(cfg):
    """Backup project ke file zip."""
    import zipfile
    from datetime import datetime

    print(f"\n{C_CYAN}━━━ BACKUP PROJECT ━━━{C_RESET}\n")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = f"backup_{timestamp}.zip"

    files_to_backup = [
        "config.json", "uploads_cache.json", "deleted.json",
        "index.html", "manager.html",
        "main.py", "menu.py", "config_manager.py",
    ]

    count = 0
    with zipfile.ZipFile(out_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files_to_backup:
            if os.path.exists(f):
                zf.write(f)
                count += 1
                print(f"  {C_GREEN}✓{C_RESET} {f} ({os.path.getsize(f) / 1024:.1f} KB)")

    print(f"\n{C_GREEN}[✓] Backup {count} file ke: {out_file}{C_RESET}")
    print(f"{C_GRAY}Total: {os.path.getsize(out_file) / 1024:.1f} KB{C_RESET}")


def tool_verify_urls(cfg):
    """Cek apakah URL Catbox masih aktif."""
    print(f"\n{C_CYAN}━━━ VERIFY CATBOX URLS ━━━{C_RESET}\n")

    cache = load_cache()
    if not cache:
        print(f"{C_YELLOW}[!] Cache kosong.{C_RESET}")
        return

    total = len(cache)
    print(f"{C_GRAY}Cek {total} URL...{C_RESET}\n")

    ok = 0
    broken = 0
    broken_list = []

    for i, (rel_path, entry) in enumerate(cache.items(), 1):
        if not isinstance(entry, dict):
            continue
        url = entry.get("url", "")
        if not url:
            continue
        try:
            r = requests.head(url, timeout=8, allow_redirects=True)
            if r.status_code in (200, 206):
                ok += 1
            else:
                broken += 1
                broken_list.append((rel_path, r.status_code))
        except Exception:
            broken += 1
            broken_list.append((rel_path, "timeout"))
        if i % 10 == 0 or i == total:
            print(f"\r{C_GRAY}  Progress: {i}/{total} ({ok} OK, {broken} broken){C_RESET}", end="")

    print(f"\n\n{C_GREEN}[✓] Aktif: {ok} file{C_RESET}")
    if broken:
        print(f"{C_RED}[!] Broken: {broken} file{C_RESET}")
        for path, status in broken_list[:20]:
            print(f"  {C_RED}[{status}]{C_RESET} {path}")


def tool_fix_cache(cfg):
    """Bersihkan cache entri rusak (tanpa URL)."""
    print(f"\n{C_CYAN}━━━ FIX BROKEN CACHE ━━━{C_RESET}\n")

    cache = load_cache()
    if not cache:
        print(f"{C_YELLOW}[!] Cache kosong.{C_RESET}")
        return

    before = len(cache)
    cleaned = {}
    for rel_path, entry in cache.items():
        if not isinstance(entry, dict):
            continue
        if not entry.get("url"):
            continue
        cleaned[rel_path] = entry

    removed = before - len(cleaned)
    if removed == 0:
        print(f"{C_GREEN}[✓] Cache sehat.{C_RESET}")
        return

    print(f"{C_GRAY}Ditemukan {removed} entri rusak.{C_RESET}")
    konfirm = input(f"{C_CYAN}Hapus? (y/n): {C_RESET}").strip().lower()
    if konfirm in ("y", "ya", "yes"):
        save_cache(cleaned)
        print(f"{C_GREEN}[✓] {len(cleaned)} entri tersisa.{C_RESET}")
def main():
    cfg = load_config()
    callbacks = {
        "run_upload": run_upload,
        "clear_cache": clear_cache_callback,
        "cleanup_thumbs": cleanup_thumbs_callback,
        "generate_manager": generate_manager_callback,
        "reset_blacklist": reset_blacklist_callback,
        "upload_github": tool_upload_github,
        "compress_html": tool_compress_html,
        "export_csv": tool_export_csv,
        "backup_project": tool_backup_project,
        "verify_urls": tool_verify_urls,
        "fix_cache": tool_fix_cache,
    }
    try:
        while True:
            run_menu(cfg, callbacks)
            save_config(cfg)
    except KeyboardInterrupt:
        print(f"\n\n\033[93mDibatalkan oleh user.\033[0m")
        save_config(cfg)
        sys.exit(0)


if __name__ == "__main__":
    main()