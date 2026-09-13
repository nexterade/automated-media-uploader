"""
Menu interaktif untuk Automated Media Uploader v6.
"""

import os
import sys
import time

from config_manager import save_config

# ─── ANSI Colors ──────────────────────────────────────────────
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_CYAN = "\033[96m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_MAGENTA = "\033[95m"
C_RED = "\033[91m"
C_WHITE = "\033[97m"
C_GRAY = "\033[90m"
C_BLUE = "\033[94m"
C_PURPLE = "\033[95m"


def clear_screen():
    os.system("clear" if os.name != "nt" else "cls")


def print_banner():
    print(f"\n{C_CYAN}  ╔══════════════════════════════════════════════╗")
    print(f"  ║{C_RESET}                                              {C_CYAN}║")
    print(f"  ║{C_RESET}   {C_BOLD}🎨  AUTOMATED MEDIA UPLOADER  v6{C_RESET}          {C_CYAN}║")
    print(f"  ║{C_RESET}        {C_GRAY}Interactive Setup Wizard{C_RESET}             {C_CYAN}║")
    print(f"  ║{C_RESET}                                              {C_CYAN}║")
    print(f"  ║{C_RESET}              {C_MAGENTA}by @nexterade{C_RESET}              {C_CYAN}║")
    print(f"  ╚══════════════════════════════════════════════╝{C_RESET}\n")


def print_user_profile(cfg):
    uh = cfg.get("userhash") or ""
    userhash_display = (uh[:6] + "..." + uh[-4:]) if len(uh) > 12 else (uh or "—")
    judul = str(cfg.get("judul_project", "BARAYAWABELUT"))[:32]
    namespace = str(cfg.get("counter_namespace", "gallery"))[:32]
    folder = str(cfg.get("photos_dir", "./media"))[:32]
    workers = str(cfg.get("workers", 1))

    print(f"{C_CYAN}  ┌──────────────────────────────────────────────┐{C_RESET}")
    print(f"{C_CYAN}  │{C_GREEN}{C_BOLD}              👤 USER PROFILE             {C_CYAN}  │{C_RESET}")
    print(f"{C_CYAN}  ├──────────────────────────────────────────────┤{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_GREEN}🔑 Userhash :{C_RESET} {C_WHITE}{userhash_display:<30}{C_RESET}{C_CYAN}│{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_GREEN}📝 Judul    :{C_RESET} {C_WHITE}{judul:<30}{C_RESET}{C_CYAN}│{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_GREEN}🔢 Namespace:{C_RESET} {C_WHITE}{namespace:<30}{C_RESET}{C_CYAN}│{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_GREEN}📁 Folder   :{C_RESET} {C_WHITE}{folder:<30}{C_RESET}{C_CYAN}│{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_GREEN}⚙️  Workers  :{C_RESET} {C_WHITE}{workers:<30}{C_RESET}{C_CYAN}│{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_GREEN}💾 Config   :{C_RESET} {C_GRAY}config.json{C_RESET}{' ' * 18}{C_CYAN}│{C_RESET}")
    print(f"{C_CYAN}  └──────────────────────────────────────────────┘{C_RESET}")


def print_main_menu():
    print(f"{C_CYAN}  ┌──────────────────────────────────────────────┐{C_RESET}")
    print(f"{C_CYAN}  │{C_MAGENTA}{C_BOLD}              🎯 MAIN MENU               {C_CYAN}  │{C_RESET}")
    print(f"{C_CYAN}  ├──────────────────────────────────────────────┤{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_MAGENTA}ID {C_RESET} {C_GREEN}Action{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_MAGENTA} 1 {C_RESET} {C_WHITE}⚙️   Setup Konfigurasi (Wizard){C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_MAGENTA} 2 {C_RESET} {C_WHITE}✏️   Edit Konfigurasi Cepat{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_MAGENTA} 3 {C_RESET} {C_GREEN}🚀  Jalankan Upload & Generate{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_MAGENTA} 4 {C_RESET} {C_WHITE}👁️   Preview Konfigurasi{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_MAGENTA} 5 {C_RESET} {C_WHITE}🗑️   Hapus Cache Upload{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_MAGENTA} 6 {C_RESET} {C_WHITE}🧹  Bersihkan Thumbnail{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_MAGENTA} 7 {C_RESET} {C_WHITE}📂  Cek Isi Folder Media{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_MAGENTA} 8 {C_RESET} {C_WHITE}📖  Bantuan & Tutorial{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_MAGENTA} 9 {C_RESET} {C_WHITE}⚙️   Generate Manager HTML{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_MAGENTA}10 {C_RESET} {C_WHITE}🛠️   Tools & Utilities{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_MAGENTA} 0 {C_RESET} {C_WHITE}🔄  Reset Blacklist{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_MAGENTA}99 {C_RESET} {C_RED}❌  Keluar{C_RESET}")
    print(f"{C_CYAN}  └──────────────────────────────────────────────┘{C_RESET}")


def input_prompt(prompt_text, default=None):
    if default is not None:
        full_prompt = f"{C_CYAN}{prompt_text}{C_RESET} {C_GRAY}[{default}]{C_RESET}: "
    else:
        full_prompt = f"{C_CYAN}{prompt_text}{C_RESET}: "
    try:
        val = input(full_prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return default if default is not None else ""
    if not val and default is not None:
        return str(default)
    return val


def wizard_setup(cfg):
    clear_screen()
    print_banner()
    print(f"{C_YELLOW}{C_BOLD}  ══════════════ 🧙 SETUP WIZARD (9 LANGKAH) ══════════════{C_RESET}\n")

    print(f"{C_CYAN}  ━━━ STEP 1/9 — 🔑 CATBOX USERHASH ━━━{C_RESET}")
    print(f"{C_GRAY}  Kosongkan jika mau upload sebagai anonymous.{C_RESET}")
    print(f"{C_GRAY}  Dapatkan di: https://catbox.moe/user/manage.php{C_RESET}")
    userhash = input_prompt("  Userhash", default=cfg.get("userhash", ""))
    print()

    print(f"{C_CYAN}  ━━━ STEP 2/9 — 📝 JUDUL PROJECT ━━━{C_RESET}")
    print(f"{C_GRAY}  Judul ini akan muncul di <title> HTML dan header galeri.{C_RESET}")
    judul = input_prompt("  Judul project", default=cfg.get("judul_project", "Tamvan"))
    print()

    print(f"{C_CYAN}  ━━━ STEP 3/9 — 🔢 COUNTER NAMESPACE ━━━{C_RESET}")
    print(f"{C_GRAY}  Namespace untuk view counter (Abacus).{C_RESET}")
    print(f"{C_GRAY}  Contoh: gallery-pemuda-rawabelut{C_RESET}")
    namespace = input_prompt("  Namespace", default=cfg.get("counter_namespace", "tamvan-dan-pemberani"))
    print()

    print(f"{C_CYAN}  ━━━ STEP 4/9 — 📁 FOLDER MEDIA ━━━{C_RESET}")
    print(f"{C_GRAY}  Folder sumber foto & video (relatif atau absolut).{C_RESET}")
    photos_dir = input_prompt("  Folder", default=cfg.get("photos_dir", "./media"))
    print()

    print(f"{C_CYAN}  ━━━ STEP 5/9 — ⚙️  JUMLAH WORKERS ━━━{C_RESET}")
    print(f"{C_GRAY}  Workers paralel (1-4). Rekomendasi: 1 untuk koneksi lambat.{C_RESET}")
    workers_str = input_prompt("  Workers", default=str(cfg.get("workers", 1)))
    try:
        workers = max(1, min(4, int(workers_str)))
    except ValueError:
        workers = 1
    print()

    print(f"{C_CYAN}  ━━━ STEP 6/9 — 🐙 GITHUB USERNAME ━━━{C_RESET}")
    print(f"{C_GRAY}  Username GitHub Anda (opsional, untuk tools upload).{C_RESET}")
    print(f"{C_GRAY}  Contoh: johndoe{C_RESET}")
    gh_user = input_prompt("  GitHub username", default=cfg.get("github_username", ""))
    print()

    print(f"{C_CYAN}  ━━━ STEP 7/9 — 📦 GITHUB REPOSITORY ━━━{C_RESET}")
    print(f"{C_GRAY}  Nama repository untuk galeri (opsional).{C_RESET}")
    print(f"{C_GRAY}  Contoh: galeri-foto{C_RESET}")
    gh_repo = input_prompt("  GitHub repo", default=cfg.get("github_repo", ""))
    print()

    print(f"{C_CYAN}  ━━━ STEP 8/9 — 🔑 GITHUB TOKEN ━━━{C_RESET}")
    print(f"{C_GRAY}  Personal Access Token (opsional).{C_RESET}")
    print(f"{C_GRAY}  Buat di: https://github.com/settings/tokens{C_RESET}")
    print(f"{C_GRAY}  Scope yang diperlukan: repo (full){C_RESET}")
    gh_token = input_prompt("  GitHub token", default=cfg.get("github_token", ""))
    print()

    print(f"{C_CYAN}  ━━━ STEP 9/9 — 🌿 GITHUB BRANCH & AUTO-UPLOAD ━━━{C_RESET}")
    gh_branch = input_prompt("  Branch", default=cfg.get("github_branch", "main"))
    auto_str = input_prompt("  Auto-upload setelah generate? (y/n)",
                            default="y" if cfg.get("github_auto_upload") else "n")
    gh_auto = auto_str.lower() in ("y", "ya", "yes", "true", "1")
    print()

    print(f"{C_YELLOW}  ━━━ ✨ KONFIRMASI ━━━{C_RESET}")
    print(f"{C_CYAN}  ┌──────────────────────────────────────────────┐{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_GREEN}🔑 Userhash    :{C_RESET} {C_WHITE}{(userhash[:20] + '...' if len(userhash) > 20 else userhash) or '(anonymous)'}{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_GREEN}📝 Judul       :{C_RESET} {C_WHITE}{judul}{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_GREEN}🔢 Namespace   :{C_RESET} {C_WHITE}{namespace}{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_GREEN}📁 Folder      :{C_RESET} {C_WHITE}{photos_dir}{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_GREEN}⚙️  Workers     :{C_RESET} {C_WHITE}{workers}{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_GREEN}🐙 GitHub User :{C_RESET} {C_WHITE}{gh_user or '(kosong)'}{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_GREEN}📦 GitHub Repo :{C_RESET} {C_WHITE}{gh_repo or '(kosong)'}{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_GREEN}🔑 GitHub Token:{C_RESET} {C_WHITE}{'•' * min(len(gh_token), 20) if gh_token else '(kosong)'}{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_GREEN}🌿 Branch      :{C_RESET} {C_WHITE}{gh_branch}{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_GREEN}🚀 Auto-upload :{C_RESET} {C_WHITE}{'Ya' if gh_auto else 'Tidak'}{C_RESET}")
    print(f"{C_CYAN}  └──────────────────────────────────────────────┘{C_RESET}")
    print()
    konfirm = input_prompt("  Simpan konfigurasi? (y/n)", default="y").lower()
    if konfirm in ("y", "yes", "ya"):
        new_cfg = dict(cfg)
        new_cfg.update({
            "userhash": userhash,
            "judul_project": judul,
            "counter_namespace": namespace,
            "photos_dir": photos_dir,
            "workers": workers,
            "github_username": gh_user,
            "github_repo": gh_repo,
            "github_token": gh_token,
            "github_branch": gh_branch,
            "github_auto_upload": gh_auto,
        })
        return new_cfg
    print(f"{C_YELLOW}  Dibatalkan.{C_RESET}")
    return cfg


def quick_edit(cfg):
    clear_screen()
    print_banner()
    print(f"{C_YELLOW}{C_BOLD}  ══════════════ ✏️  EDIT KONFIGURASI CEPAT ══════════════{C_RESET}\n")
    print(f"{C_CYAN}  Field yang bisa diedit:{C_RESET}")
    print(f"   {C_MAGENTA} 1{C_RESET} {C_WHITE}🔑 Userhash Catbox{C_RESET}")
    print(f"   {C_MAGENTA} 2{C_RESET} {C_WHITE}📝 Judul Project{C_RESET}")
    print(f"   {C_MAGENTA} 3{C_RESET} {C_WHITE}🔢 Counter Namespace{C_RESET}")
    print(f"   {C_MAGENTA} 4{C_RESET} {C_WHITE}📁 Folder Media{C_RESET}")
    print(f"   {C_MAGENTA} 5{C_RESET} {C_WHITE}⚙️  Jumlah Workers{C_RESET}")
    print(f"   {C_MAGENTA} 6{C_RESET} {C_WHITE}🐙 GitHub Username{C_RESET}")
    print(f"   {C_MAGENTA} 7{C_RESET} {C_WHITE}📦 GitHub Repo{C_RESET}")
    print(f"   {C_MAGENTA} 8{C_RESET} {C_WHITE}🔑 GitHub Token{C_RESET}")
    print(f"   {C_MAGENTA} 9{C_RESET} {C_WHITE}🌿 GitHub Branch{C_RESET}")
    print(f"   {C_MAGENTA}10{C_RESET} {C_WHITE}🚀 Auto-upload GitHub (on/off){C_RESET}")
    print(f"   {C_MAGENTA} 0{C_RESET} {C_GRAY}↩️  Kembali{C_RESET}")
    print()
    pilihan = input_prompt("  Pilih field", default="0")
    if pilihan == "1":
        cfg["userhash"] = input_prompt("  🔑 Userhash baru", default=cfg.get("userhash", ""))
    elif pilihan == "2":
        cfg["judul_project"] = input_prompt("  📝 Judul baru", default=cfg.get("judul_project", ""))
    elif pilihan == "3":
        cfg["counter_namespace"] = input_prompt("  🔢 Namespace baru", default=cfg.get("counter_namespace", ""))
    elif pilihan == "4":
        cfg["photos_dir"] = input_prompt("  📁 Folder baru", default=cfg.get("photos_dir", "./media"))
    elif pilihan == "5":
        w = input_prompt("  ⚙️  Workers baru", default=str(cfg.get("workers", 1)))
        try:
            cfg["workers"] = max(1, min(4, int(w)))
        except ValueError:
            pass
    elif pilihan == "6":
        cfg["github_username"] = input_prompt("  🐙 GitHub username", default=cfg.get("github_username", ""))
    elif pilihan == "7":
        cfg["github_repo"] = input_prompt("  📦 GitHub repo", default=cfg.get("github_repo", ""))
    elif pilihan == "8":
        cfg["github_token"] = input_prompt("  🔑 GitHub token", default=cfg.get("github_token", ""))
    elif pilihan == "9":
        cfg["github_branch"] = input_prompt("  🌿 GitHub branch", default=cfg.get("github_branch", "main"))
    elif pilihan == "10":
        cur = "y" if cfg.get("github_auto_upload") else "n"
        ans = input_prompt("  🚀 Auto-upload GitHub? (y/n)", default=cur)
        cfg["github_auto_upload"] = ans.lower() in ("y", "ya", "yes")
    return cfg


def preview_config(cfg):
    clear_screen()
    print_banner()
    print(f"{C_YELLOW}{C_BOLD}  ══════════════ 👁️  PREVIEW KONFIGURASI ══════════════{C_RESET}\n")
    for key, val in cfg.items():
        if key == "userhash":
            val = (val[:10] + "..." + val[-4:]) if val and len(val) > 14 else (val or "(anonymous)")
        print(f"  {C_GREEN}{key:<22}{C_RESET} {C_WHITE}{val}{C_RESET}")
    print()
    input(f"{C_GRAY}  [Enter untuk kembali]{C_RESET}")


# ═══════════════════════════════════════════════════════════════════
# SPEEDTEST KE CATBOX
# ═══════════════════════════════════════════════════════════════════

def measure_upload_speed_to_catbox(sample_size_kb=50, timeout=20):
    """
    Ukur kecepatan upload ke Catbox dengan upload file dummy.
    
    Args:
        sample_size_kb: Ukuran file test dalam KB (default 50 KB)
        timeout: Timeout request dalam detik
    
    Returns:
        dict: {
            "speed_bps": float,      # bytes per second
            "speed_kbps": float,     # KB per second
            "ok": bool,              # berhasil/gagal
            "msg": str               # pesan info
        }
    """
    import requests
    import time as _time
    
    result = {"speed_bps": 0, "speed_kbps": 0, "ok": False, "msg": ""}
    
    try:
        # Buat file dummy di memory (header JPEG + padding random)
        dummy_data = b'\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01' + os.urandom(sample_size_kb * 1024)
        file_size = len(dummy_data)
        
        files = {
            "fileToUpload": ("speedtest_dummy.jpg", dummy_data, "application/octet-stream")
        }
        data = {"reqtype": "fileupload"}
        
        start = _time.time()
        res = requests.post(
            "https://catbox.moe/user/api.php",
            data=data,
            files=files,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
            timeout=timeout,
        )
        elapsed = _time.time() - start
        
        if res.status_code != 200:
            result["msg"] = f"HTTP {res.status_code}"
            return result
        
        if elapsed > 0:
            speed_bps = file_size / elapsed
            result["speed_bps"] = speed_bps
            result["speed_kbps"] = speed_bps / 1024
            result["ok"] = True
            result["msg"] = f"dari {sample_size_kb} kB sample"
        
        return result
    
    except requests.Timeout:
        result["msg"] = "Timeout — koneksi lambat"
        return result
    except requests.ConnectionError:
        result["msg"] = "Koneksi error — cek VPN/internet"
        return result
    except Exception as e:
        result["msg"] = f"Error: {type(e).__name__}"
        return result


def check_media_folder(cfg):
    clear_screen()
    print_banner()
    print(f"{C_YELLOW}{C_BOLD}  ══════════════ 📂 CEK FOLDER MEDIA ══════════════{C_RESET}\n")
    folder = cfg.get("photos_dir", "./media")
    
    if not os.path.exists(folder):
        print(f"  {C_RED}❌ Folder tidak ditemukan: {folder}{C_RESET}")
        print(f"  {C_GRAY}Buat dulu dengan: mkdir -p {folder}{C_RESET}")
    else:
        total = 0
        ext_count = {}
        total_size = 0
        size_by_ext = {}
        
        for root, dirs, files in os.walk(folder):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".ico",
                           ".mp4", ".mkv", ".webm", ".mov"}:
                    file_path = os.path.join(root, f)
                    try:
                        file_size = os.path.getsize(file_path)
                    except Exception:
                        file_size = 0
                    
                    total += 1
                    ext_count[ext] = ext_count.get(ext, 0) + 1
                    total_size += file_size
                    size_by_ext[ext] = size_by_ext.get(ext, 0) + file_size
        
        # ── Helper format bytes ──
        def fmt_size(b):
            if b == 0:
                return "0 B"
            v = float(b)
            if v < 1024:
                return f"{int(v)} B"
            elif v < 1024 * 1024:
                return f"{v / 1024:.1f} kB"
            elif v < 1024 * 1024 * 1024:
                return f"{v / (1024 * 1024):.1f} MB"
            else:
                return f"{v / (1024 * 1024 * 1024):.2f} GB"
        
        # ── Tampilkan info folder ──
        print(f"  {C_GREEN}📁 Folder:{C_RESET} {C_WHITE}{folder}{C_RESET}")
        print(f"  {C_GREEN}📊 Total file didukung:{C_RESET} {C_WHITE}{total}{C_RESET}")
        
        if total > 0:
            avg_size = total_size / total
            print(f"  {C_GREEN}💾 Total ukuran:{C_RESET} {C_CYAN}{fmt_size(total_size)}{C_RESET}")
            print(f"  {C_GREEN}📏 Rata-rata per file:{C_RESET} {C_WHITE}{fmt_size(avg_size)}{C_RESET}")
            
            # ── SPEEDTEST ke Catbox ──
            print(f"\n  {C_CYAN}⚡ Mengukur kecepatan upload ke Catbox...{C_RESET}")
            speed_result = measure_upload_speed_to_catbox(sample_size_kb=50)
            
            if speed_result["ok"]:
                actual_speed_bps = speed_result["speed_bps"]
                print(f"  {C_GREEN}🚀 Kecepatan upload:{C_RESET} "
                      f"{C_CYAN}{speed_result['speed_kbps']:.1f} kB/s{C_RESET} "
                      f"{C_GRAY}({speed_result['msg']}){C_RESET}")
            else:
                actual_speed_bps = 100 * 1024  # fallback 100 kB/s
                print(f"  {C_YELLOW}⚠️  Speedtest gagal: {speed_result['msg']}{C_RESET}")
                print(f"  {C_GRAY}   Pakai asumsi default 100 kB/s{C_RESET}")
            
            # ── Hitung estimasi upload ──
            est_seconds = total_size / actual_speed_bps if actual_speed_bps > 0 else 0
            # Tambah jeda upload (2s per file + batch pause per 30 file)
            est_seconds += total * 2
            if total >= 30:
                est_seconds += (total // 30) * 60
            
            est_min = int(est_seconds // 60)
            est_sec = int(est_seconds % 60)
            if est_min > 0:
                est_str = f"{est_min}m {est_sec}s"
            else:
                est_str = f"{est_sec}s"
            
            print(f"  {C_GREEN}⏱️  Estimasi upload:{C_RESET} {C_YELLOW}~{est_str}{C_RESET}")
        
        # ── Rincian per ekstensi ──
        if ext_count:
            print(f"\n  {C_GREEN}📋 Rincian per ekstensi:{C_RESET}")
            print(f"  {C_GRAY}{'─' * 44}{C_RESET}")
            print(f"  {C_GRAY}{'Ext':<8}{'File':>6}{'Ukuran':>14}{'Rata-rata':>14}{C_RESET}")
            print(f"  {C_GRAY}{'─' * 44}{C_RESET}")
            
            for ext, cnt in sorted(ext_count.items(), key=lambda x: -x[1]):
                ext_size = size_by_ext.get(ext, 0)
                avg = ext_size / cnt if cnt > 0 else 0
                print(
                    f"  {C_CYAN}{ext:<8}{C_RESET}"
                    f"{C_WHITE}{cnt:>6}{C_RESET}"
                    f"{C_CYAN}{fmt_size(ext_size):>14}{C_RESET}"
                    f"{C_GRAY}{fmt_size(avg):>14}{C_RESET}"
                )
            
            print(f"  {C_GRAY}{'─' * 44}{C_RESET}")
            print(
                f"  {C_BOLD}{C_WHITE}{'Total':<8}"
                f"{total:>6}"
                f"{fmt_size(total_size):>14}{C_RESET}"
            )
    
    # ═══════════════════════════════════════════════════════════
    # 🚀 PROMPT: Jalankan Upload & Generate?
    # ═══════════════════════════════════════════════════════════
    print()
    print(f"  {C_PURPLE}╔═════════════════════════════════════════════════════╗{C_RESET}")
    print(f"  {C_PURPLE}║{C_RESET}  {C_CYAN}{C_BOLD}🚀  JALANKAN UPLOAD & GENERATE SEKARANG?{C_RESET}        {C_PURPLE}║{C_RESET}")
    print(f"  {C_PURPLE}╠═════════════════════════════════════════════════════╣{C_RESET}")
    print(f"  {C_PURPLE}║{C_RESET}                                                     {C_PURPLE}║{C_RESET}")
    print(f"  {C_PURPLE}║{C_RESET}  {C_GREEN}▸{C_RESET} {C_GREEN}{C_BOLD}[y]{C_RESET} {C_WHITE}Lanjut Gas! 🔥{C_RESET}                                {C_PURPLE}║{C_RESET}")
    print(f"  {C_PURPLE}║{C_RESET}  {C_YELLOW}▸{C_RESET} {C_YELLOW}{C_BOLD}[n]{C_RESET} {C_WHITE}Nanti Sajalah 😴{C_RESET}                             {C_PURPLE}║{C_RESET}")
    print(f"  {C_PURPLE}║{C_RESET}                                                     {C_PURPLE}║{C_RESET}")
    print(f"  {C_PURPLE}╚═════════════════════════════════════════════════════╝{C_RESET}")
    print()
    
    pilihan = input(
        f"  {C_CYAN}➜{C_RESET} {C_WHITE}Pilihan{C_RESET} "
        f"{C_GRAY}[y/n]{C_RESET} {C_GRAY}(default: n){C_RESET} : "
    ).strip().lower()
    
    if pilihan in ("y", "ya", "yes", "gas"):
        # ═══════════════════════════════════════════════════════
        # User pilih YES → Jalankan Upload
        # ═══════════════════════════════════════════════════════
        print()
        print(f"  {C_GREEN}🚀 Gas! Menjalankan Upload & Generate...{C_RESET}")
        print()
        time.sleep(1)
        clear_screen()
        
        try:
            from main import scan_and_upload, HTML_TEMPLATE, ITEMS_PER_PAGE
            from main import COUNTER_API_BASE, COUNTER_NAMESPACE
            from main import inject_project_title, generate_manager_html
            from main import _escape_json_for_inline_script, apply_config
            import json as _json
            
            apply_config(cfg)
            
            print(f"\n{'='*54}")
            print(f"  🚀 MENJALANKAN UPLOAD & GENERATE")
            print(f"{'='*54}\n")
            
            data = scan_and_upload()
            if not data:
                print(f"  {C_YELLOW}[!] Tidak ada data yang diproses.{C_RESET}")
                input(f"\n{C_GRAY}  [Enter untuk kembali]{C_RESET}")
                return
            
            json_str = _escape_json_for_inline_script(data)
            rendered_html = HTML_TEMPLATE.replace("/*DATA_PLACEHOLDER*/", json_str)
            rendered_html = rendered_html.replace("/*ITEMS_PER_PAGE_PLACEHOLDER*/", str(ITEMS_PER_PAGE))
            rendered_html = rendered_html.replace("/*COUNTER_API_PLACEHOLDER*/", _json.dumps(COUNTER_API_BASE))
            rendered_html = rendered_html.replace("/*COUNTER_NS_PLACEHOLDER*/", _json.dumps(COUNTER_NAMESPACE))
            judul = cfg.get("judul_project", "Gallery")
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
            
            # ── Prompt upload GitHub ──
            print()
            print(f"  {C_PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C_RESET}")
            print(f"  {C_CYAN}📤 Upload hasil ke GitHub sekarang?{C_RESET}")
            print(f"  {C_GRAY}   [y]{C_RESET} {C_GREEN}Push ke GitHub!{C_RESET}  "
                  f"{C_GRAY}/{C_RESET}  {C_GRAY}[n]{C_RESET} {C_YELLOW}Skip dulu{C_RESET}")
            print(f"  {C_PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C_RESET}")
            print()
            konfirm = input(
                f"  {C_CYAN}➜{C_RESET} {C_WHITE}Pilihan{C_RESET} "
                f"{C_GRAY}[y/n]{C_RESET} {C_GRAY}(default: n){C_RESET} : "
            ).strip().lower()
            
            if konfirm in ("y", "ya", "yes"):
                print()
                print(f"  {C_GREEN}📤 Push ke GitHub...{C_RESET}")
                print()
                time.sleep(1)
                try:
                    from main import tool_upload_github
                    tool_upload_github(cfg)
                except Exception as e:
                    print(f"\n  {C_RED}❌ Gagal upload GitHub: {type(e).__name__}: {e}{C_RESET}")
            else:
                print()
                print(f"  {C_YELLOW}👌 Oke, skip upload GitHub.{C_RESET}")
        
        except Exception as e:
            print()
            print(f"  {C_RED}❌ Error: {type(e).__name__}: {e}{C_RESET}")
        
        input(f"\n{C_GRAY}  [Enter untuk kembali ke menu]{C_RESET}")
    else:
        # ═══════════════════════════════════════════════════════
        # User pilih NO (atau Enter) → Kembali ke menu
        # ═══════════════════════════════════════════════════════
        print()
        print(f"  {C_YELLOW}👌 Oke, nanti aja. Kembali ke menu...{C_RESET}")
        time.sleep(1)


def bantuan():
    while True:
        clear_screen()
        print_banner()
        print(f"{C_YELLOW}{C_BOLD}  ══════════════ 📖 BANTUAN & TUTORIAL ══════════════{C_RESET}\n")
        print(f"{C_CYAN}  ┌──────────────────────────────────────────────┐{C_RESET}")
        print(f"{C_CYAN}  │{C_MAGENTA}{C_BOLD}              📖 BANTUAN & TUTORIAL       {C_CYAN}  │{C_RESET}")
        print(f"{C_CYAN}  ├──────────────────────────────────────────────┤{C_RESET}")
        print(f"{C_CYAN}  │{C_RESET}  {C_MAGENTA} 1 {C_RESET} {C_WHITE}📚 Cara Pakai Aplikasi{C_RESET}")
        print(f"{C_CYAN}  │{C_RESET}  {C_MAGENTA} 2 {C_RESET} {C_WHITE}🐙 Tutorial GitHub (Lengkap){C_RESET}")
        print(f"{C_CYAN}  │{C_RESET}  {C_MAGENTA} 3 {C_RESET} {C_WHITE}🔑 Cara Buat Personal Access Token{C_RESET}")
        print(f"{C_CYAN}  │{C_RESET}  {C_MAGENTA} 4 {C_RESET} {C_WHITE}📦 Struktur Folder{C_RESET}")
        print(f"{C_CYAN}  │{C_RESET}  {C_MAGENTA} 5 {C_RESET} {C_WHITE}💡 Tips & Trik{C_RESET}")
        print(f"{C_CYAN}  │{C_RESET}  {C_MAGENTA} 6 {C_RESET} {C_WHITE}⚠️  Troubleshooting{C_RESET}")
        print(f"{C_CYAN}  │{C_RESET}  {C_MAGENTA} 0 {C_RESET} {C_GRAY}↩️  Kembali{C_RESET}")
        print(f"{C_CYAN}  └──────────────────────────────────────────────┘{C_RESET}")
        print()
        pilihan = input(f"{C_CYAN}  Pilih bantuan: {C_RESET}").strip()

        if pilihan == "1":
            bantuan_cara_pakai()
        elif pilihan == "2":
            bantuan_github()
        elif pilihan == "3":
            bantuan_token()
        elif pilihan == "4":
            bantuan_struktur()
        elif pilihan == "5":
            bantuan_tips()
        elif pilihan == "6":
            bantuan_troubleshooting()
        elif pilihan == "0":
            break
        else:
            print(f"{C_RED}  Pilihan tidak valid.{C_RESET}")
            time.sleep(1)


def bantuan_cara_pakai():
    clear_screen()
    print_banner()
    print(f"{C_YELLOW}{C_BOLD}  ══════════════ 📚 CARA PAKAI APLIKASI ══════════════{C_RESET}\n")
    print(f"""{C_CYAN}  Langkah-Langkah:{C_RESET}

    {C_GREEN}1.{C_RESET} Jalankan aplikasi: {C_WHITE}python main.py{C_RESET} atau alias {C_WHITE}v6{C_RESET}

    {C_GREEN}2.{C_RESET} Pilih menu {C_MAGENTA}1{C_RESET} → {C_WHITE}Setup Konfigurasi (Wizard){C_RESET}
       Isi data yang diminta:
       • {C_CYAN}Userhash Catbox{C_RESET}  → untuk upload (opsional)
       • {C_CYAN}Judul Project{C_RESET}     → nama galeri Anda
       • {C_CYAN}Namespace{C_RESET}        → untuk view counter
       • {C_CYAN}Folder Media{C_RESET}     → folder foto/video
       • {C_CYAN}GitHub Username{C_RESET}  → untuk auto-deploy (opsional)
       • {C_CYAN}GitHub Repo{C_RESET}      → nama repository
       • {C_CYAN}GitHub Token{C_RESET}     → untuk akses push
       • {C_CYAN}Auto-upload{C_RESET}      → y/n

    {C_GREEN}3.{C_RESET} Pilih menu {C_MAGENTA}3{C_RESET} → {C_WHITE}Jalankan Upload & Generate{C_RESET}
       Script akan:
       • Scan folder media
       • Upload ke Catbox.moe
       • Generate {C_WHITE}index.html{C_RESET} (galeri)
       • Generate {C_WHITE}manager.html{C_RESET} (kelola file)
       • Tanya upload ke GitHub (jika di-setup)

    {C_GREEN}4.{C_RESET} Buka {C_WHITE}index.html{C_RESET} di browser untuk lihat galeri

    {C_GREEN}5.{C_RESET} Pilih menu {C_MAGENTA}9{C_RESET} → {C_WHITE}Generate Manager HTML{C_RESET}
       Untuk buka panel kelola file (hapus, blacklist, dll)

    {C_GREEN}6.{C_RESET} Pilih menu {C_MAGENTA}10{C_RESET} → {C_WHITE}Tools & Utilities{C_RESET}
       Upload GitHub, Compress HTML, Export CSV, dll

{C_YELLOW}  Catatan:{C_RESET}
    • Pertama kali pakai, {C_WHITE}wajib{C_RESET} jalankan menu 1 dulu
    • Data config disimpan di {C_WHITE}config.json{C_RESET}
    • Cache upload disimpan di {C_WHITE}uploads_cache.json{C_RESET}
""")
    input(f"{C_GRAY}  [Enter untuk kembali]{C_RESET}")


def bantuan_github():
    clear_screen()
    print_banner()
    print(f"{C_YELLOW}{C_BOLD}  ══════════════ 🐙 TUTORIAL GITHUB UNTUK PEMULA ══════════════{C_RESET}\n")
    print(f"""{C_CYAN}  ╔═══════════════════════════════════════════════════════════╗{C_RESET}
{C_CYAN}  ║{C_RESET}  {C_YELLOW}{C_BOLD}❓ APA ITU GITHUB?{C_RESET}                                          {C_CYAN}║{C_RESET}
{C_CYAN}  ╚═══════════════════════════════════════════════════════════╝{C_RESET}

  GitHub adalah tempat {C_WHITE}gratis{C_RESET} untuk menyimpan file project,
  termasuk {C_WHITE}index.html{C_RESET} galeri Anda. Dengan GitHub Pages,
  galeri Anda bisa diakses online tanpa bayar hosting.

{C_CYAN}  ╔═══════════════════════════════════════════════════════════╗{C_RESET}
{C_CYAN}  ║{C_RESET}  {C_YELLOW}{C_BOLD}📝 LANGKAH 1: DAFTAR AKUN GITHUB{C_RESET}                          {C_CYAN}║{C_RESET}
{C_CYAN}  ╚═══════════════════════════════════════════════════════════╝{C_RESET}

    {C_GREEN}a.{C_RESET} Buka browser → {C_CYAN}https://github.com/signup{C_RESET}

    {C_GREEN}b.{C_RESET} Isi form:
       • {C_WHITE}Email{C_RESET}      → email aktif Anda
       • {C_WHITE}Password{C_RESET}   → minimal 8 karakter
       • {C_WHITE}Username{C_RESET}   → pilih nama unik (huruf, angka, tanda hubung)
                        contoh: {C_GRAY}johndoe123{C_RESET}

    {C_GREEN}c.{C_RESET} Verifikasi email → cek inbox, klik link verifikasi

    {C_GREEN}d.{C_RESET} Setelah login, Anda punya akun GitHub! 🎉

{C_CYAN}  ╔═══════════════════════════════════════════════════════════╗{C_RESET}
{C_CYAN}  ║{C_RESET}  {C_YELLOW}{C_BOLD}📦 LANGKAH 2: BUAT REPOSITORY (FOLDER PROJECT){C_RESET}            {C_CYAN}║{C_RESET}
{C_CYAN}  ╚═══════════════════════════════════════════════════════════╝{C_RESET}

    {C_GREEN}a.{C_RESET} Klik tombol {C_WHITE}+{C_RESET} di kanan atas → {C_WHITE}New repository{C_RESET}

    {C_GREEN}b.{C_RESET} Isi form:
       • {C_WHITE}Repository name{C_RESET} → {C_GRAY}galeri-foto{C_RESET} (atau nama lain)
       • {C_WHITE}Description{C_RESET}      → {C_GRAY}Galeri media pribadi{C_RESET} (opsional)
       • {C_WHITE}Public{C_RESET} / {C_WHITE}Private{C_RESET} → pilih {C_GREEN}Public{C_RESET} (biar bisa diakses)
       • {C_WHITE}Initialize repository{C_RESET} → {C_GREEN}✓ centang{C_RESET} {C_GRAY}Add a README file{C_RESET}

    {C_GREEN}c.{C_RESET} Klik {C_WHITE}Create repository{C_RESET}

    {C_GREEN}d.{C_RESET} Setelah dibuat, URL repo Anda:
       {C_CYAN}https://github.com/USERNAME/NAMA-REPO{C_RESET}

       Contoh: {C_CYAN}https://github.com/johndoe123/galeri-foto{C_RESET}

{C_CYAN}  ╔═══════════════════════════════════════════════════════════╗{C_RESET}
{C_CYAN}  ║{C_RESET}  {C_YELLOW}{C_BOLD}🌿 LANGKAH 3: BUAT BRANCH (OPSIONAL){C_RESET}                     {C_CYAN}║{C_RESET}
{C_CYAN}  ╚═══════════════════════════════════════════════════════════╝{C_RESET}

  Secara default, repo sudah punya branch {C_WHITE}main{C_RESET}.
  Anda {C_GREEN}TIDAK WAJIB{C_RESET} buat branch baru.

  {C_YELLOW}⚠️  Untuk galeri ini, cukup pakai branch "main" saja.{C_RESET}

{C_CYAN}  ╔═══════════════════════════════════════════════════════════╗{C_RESET}
{C_CYAN}  ║{C_RESET}  {C_YELLOW}{C_BOLD}🌐 LANGKAH 4: AKTIFKAN GITHUB PAGES (ONLINE){C_RESET}              {C_CYAN}║{C_RESET}
{C_CYAN}  ╚═══════════════════════════════════════════════════════════╝{C_RESET}

    {C_GREEN}a.{C_RESET} Buka repo → {C_WHITE}Settings{C_RESET} (tab paling kanan)
    {C_GREEN}b.{C_RESET} Menu kiri → {C_WHITE}Pages{C_RESET}
    {C_GREEN}c.{C_RESET} Source: {C_WHITE}Branch:{C_RESET} {C_GREEN}main{C_RESET}, {C_WHITE}Folder:{C_RESET} {C_GREEN}/ (root){C_RESET}
    {C_GREEN}d.{C_RESET} Klik {C_WHITE}Save{C_RESET}
    {C_GREEN}e.{C_RESET} Tunggu 1-2 menit → galeri online di:
       {C_CYAN}https://USERNAME.github.io/NAMA-REPO/{C_RESET}

{C_CYAN}  ╔═══════════════════════════════════════════════════════════╗{C_RESET}
{C_CYAN}  ║{C_RESET}  {C_YELLOW}{C_BOLD}✨ LANGKAH 5: ISI DI MENU WIZARD (MENU 1){C_RESET}                 {C_CYAN}║{C_RESET}
{C_CYAN}  ╚═══════════════════════════════════════════════════════════╝{C_RESET}

  Setelah punya akun + repo + token (lihat menu 3),
  kembali ke aplikasi dan isi:

    • {C_WHITE}GitHub Username{C_RESET} → {C_CYAN}johndoe123{C_RESET}
    • {C_WHITE}GitHub Repo{C_RESET}     → {C_CYAN}galeri-foto{C_RESET}
    • {C_WHITE}GitHub Token{C_RESET}    → {C_CYAN}ghp_xxxxxxxxxxxx{C_RESET}
    • {C_WHITE}GitHub Branch{C_RESET}   → {C_CYAN}main{C_RESET}
    • {C_WHITE}Auto-upload{C_RESET}     → {C_CYAN}y{C_RESET}

{C_YELLOW}  ═══════════════════════════════════════════════════════════{C_RESET}
{C_GREEN}  🎉 SELESAI!{C_RESET} Galeri Anda siap di-deploy ke GitHub.
{C_YELLOW}  ═══════════════════════════════════════════════════════════{C_RESET}
""")
    input(f"{C_GRAY}  [Enter untuk kembali]{C_RESET}")


def bantuan_token():
    clear_screen()
    print_banner()
    print(f"{C_YELLOW}{C_BOLD}  ══════════════ 🔑 CARA BUAT PERSONAL ACCESS TOKEN ══════════════{C_RESET}\n")
    print(f"""{C_CYAN}  Apa itu Token?{C_RESET}

  Token adalah {C_WHITE}pengganti password{C_RESET} untuk script ini push
  file ke GitHub tanpa harus login manual setiap kali.

{C_YELLOW}  ═══════════════════════════════════════════════════════════{C_RESET}

{C_GREEN}  LANGKAH-LANGKAH:{C_RESET}

    {C_GREEN}1.{C_RESET} Buka: {C_CYAN}https://github.com/settings/tokens{C_RESET}

    {C_GREEN}2.{C_RESET} Klik tombol {C_WHITE}Generate new token{C_RESET}
       → pilih {C_WHITE}Generate new token (classic){C_RESET}

    {C_GREEN}3.{C_RESET} Isi form:
       • {C_WHITE}Note{C_RESET}        → {C_GRAY}galeri-bot{C_RESET} (nama bebas)
       • {C_WHITE}Expiration{C_RESET}  → {C_GRAY}90 days{C_RESET} atau {C_GRAY}No expiration{C_RESET}
       • {C_WHITE}Scopes{C_RESET}      → centang {C_GREEN}✓ repo{C_RESET} (full)
                          (wajib! untuk akses baca/tulis repo)

    {C_GREEN}4.{C_RESET} Scroll ke bawah → klik {C_WHITE}Generate token{C_RESET}

    {C_GREEN}5.{C_RESET} Token muncul {C_YELLOW}SEKALI SAJA{C_RESET}! Salin format:
       {C_CYAN}ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx{C_RESET}

    {C_GREEN}6.{C_RESET} Simpan di tempat aman (Notes, Password Manager)

{C_YELLOW}  ═══════════════════════════════════════════════════════════{C_RESET}

{C_RED}  ⚠️  PENTING:{C_RESET}
    • Token {C_RED}TIDAK BISA{C_RESET} dilihat lagi setelah halaman ditutup
    • Kalau hilang → buat token baru
    • {C_RED}JANGAN{C_RESET} share token ke orang lain
    • Kalau token bocor → hapus & buat baru

{C_YELLOW}  ═══════════════════════════════════════════════════════════{C_RESET}

{C_GREEN}  Format Token di Aplikasi:{C_RESET}

    GitHub Token: {C_CYAN}ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx{C_RESET}

    Paste di menu {C_MAGENTA}1{C_RESET} → {C_WHITE}STEP 8/9 — GITHUB TOKEN{C_RESET}
""")
    input(f"{C_GRAY}  [Enter untuk kembali]{C_RESET}")


def bantuan_struktur():
    clear_screen()
    print_banner()
    print(f"{C_YELLOW}{C_BOLD}  ══════════════ 📦 STRUKTUR FOLDER ══════════════{C_RESET}\n")
    print(f"""{C_CYAN}  Struktur Project:{C_RESET}

    {C_GRAY}project/{C_RESET}
    |-- {C_WHITE}main.py{C_RESET}              {C_GRAY}# File utama (jangan dihapus){C_RESET}
    |-- {C_WHITE}menu.py{C_RESET}              {C_GRAY}# Menu interaktif{C_RESET}
    |-- {C_WHITE}config_manager.py{C_RESET}    {C_GRAY}# Pengelola config{C_RESET}
    |
    |-- {C_CYAN}config.json{C_RESET}           {C_GRAY}# Konfigurasi (auto){C_RESET}
    |-- {C_CYAN}uploads_cache.json{C_RESET}    {C_GRAY}# Cache upload (auto){C_RESET}
    |-- {C_CYAN}deleted.json{C_RESET}          {C_GRAY}# Blacklist (auto){C_RESET}
    |
    |-- {C_GREEN}index.html{C_RESET}            {C_GRAY}# Galeri (output){C_RESET}
    |-- {C_GREEN}manager.html{C_RESET}          {C_GRAY}# Panel kelola (output){C_RESET}
    |
    +-- {C_YELLOW}media/{C_RESET}                {C_GRAY}# Folder foto/video Anda{C_RESET}
        |-- Wisata/
        |   |-- pantai.jpg
        |   +-- gunung.mp4
        +-- Keluarga/
            +-- ulang_tahun.jpg

{C_CYAN}  File Penting:{C_RESET}

    {C_GREEN}config.json{C_RESET}
      Menyimpan userhash, judul, token, dll.
      Kalau error → hapus & jalankan ulang menu 1.

    {C_GREEN}uploads_cache.json{C_RESET}
      Menyimpan URL hasil upload.
      Kalau ada URL kosong → menu 10 → 6 (Fix Cache).

    {C_GREEN}index.html{C_RESET}
      Galeri yang dibuka di browser.
      Regenerate dengan menu 3.

    {C_GREEN}manager.html{C_RESET}
      Panel kelola file (hapus, blacklist).
      Regenerate dengan menu 9.

{C_YELLOW}  ═══════════════════════════════════════════════════════════{C_RESET}

{C_CYAN}  Folder Media:{C_RESET}

    • Setiap subfolder = kategori
    • Nama file = judul & tag otomatis
    • Mendukung: JPG, PNG, WEBP, GIF, MP4, MKV, WEBM, MOV
    • Batas Catbox: {C_RED}200 MB per file{C_RESET}
""")
    input(f"{C_GRAY}  [Enter untuk kembali]{C_RESET}")


def bantuan_tips():
    clear_screen()
    print_banner()
    print(f"{C_YELLOW}{C_BOLD}  ══════════════ 💡 TIPS & TRIK ══════════════{C_RESET}\n")
    print(f"""{C_CYAN}  📤 Tips Upload:{C_RESET}

    • Untuk koneksi lambat, pakai {C_WHITE}workers = 1{C_RESET}
    • Untuk upload paralel, pakai {C_WHITE}workers = 2-4{C_RESET}
    • Kalau gagal upload → menu 10 → 6 (Fix Cache) → ulang
    • Hapus {C_WHITE}uploads_cache.json{C_RESET} untuk upload ulang SEMUA file

{C_CYAN}  🖼️  Tips Media:{C_RESET}

    • Beri nama file deskriptif: {C_GREEN}liburan_pantai_2024.jpg{C_RESET}
    • Kelompokkan dalam subfolder: {C_GREEN}media/Wisata/{C_RESET}
    • Tanggal dari nama file otomatis di-tag:
      {C_GRAY}foto_2024-03-15.jpg → tag "Maret 2024"{C_RESET}

{C_CYAN}  🐙 Tips GitHub:{C_RESET}

    • Pakai branch {C_WHITE}main{C_RESET} (default)
    • Aktifkan GitHub Pages di Settings → Pages
    • Repo harus Public untuk GitHub Pages gratis
    • Token expired → buat baru di settings/tokens

{C_CYAN}  🎨 Tips Galeri:{C_RESET}

    • Buka {C_WHITE}index.html{C_RESET} di browser HP
    • Ganti tema dengan tombol 🎨
    • Filter berdasarkan tanggal, tag, kategori
    • Share foto dengan tombol Share

{C_CYAN}  ⚡ Tips Optimasi:{C_RESET}

    • Compress HTML: menu 10 → 2 (minify)
    • Backup project: menu 10 → 4 (zip)
    • Export CSV: menu 10 → 3 (Excel)
    • Verify URL: menu 10 → 5 (cek URL aktif)

{C_CYAN}  🐛 Tips Debug:{C_RESET}

    • Cek syntax: {C_WHITE}python -m py_compile main.py{C_RESET}
    • Cek config: {C_WHITE}cat config.json{C_RESET}
    • Cek cache: {C_WHITE}cat uploads_cache.json{C_RESET}
    • Reset total: hapus {C_WHITE}config.json{C_RESET} + {C_WHITE}uploads_cache.json{C_RESET}
""")
    input(f"{C_GRAY}  [Enter untuk kembali]{C_RESET}")


def bantuan_troubleshooting():
    clear_screen()
    print_banner()
    print(f"{C_YELLOW}{C_BOLD}  ══════════════ ⚠️  TROUBLESHOOTING ══════════════{C_RESET}\n")
    print(f"""{C_RED}  ❌ Error 1: ModuleNotFoundError{C_RESET}
    {C_WHITE}Penyebab:{C_RESET} File .py tidak ditemukan atau nama salah
    {C_WHITE}Solusi:{C_RESET}
      • Cek: {C_WHITE}ls -la{C_RESET} (harus ada main.py, menu.py, config_manager.py)
      • Cek nama file: {C_WHITE}Menu.py ≠ menu.py{C_RESET} (case-sensitive)

{C_RED}  ❌ Error 2: SyntaxError / IndentationError{C_RESET}
    {C_WHITE}Penyebab:{C_RESET} Kode rusak saat edit
    {C_WHITE}Solusi:{C_RESET}
      • Restore dari backup: {C_WHITE}cp main.py.bak main.py{C_RESET}
      • Atau minta file bersih dari author

{C_RED}  ❌ Error 3: Upload gagal / URL kosong{C_RESET}
    {C_WHITE}Penyebab:{C_RESET} Koneksi putus, userhash salah
    {C_WHITE}Solusi:{C_RESET}
      • Cek config: {C_WHITE}cat config.json{C_RESET}
      • Fix cache: menu 10 → 6
      • Upload ulang: menu 3

{C_RED}  ❌ Error 4: Gambar tidak muncul di index.html{C_RESET}
    {C_WHITE}Penyebab:{C_RESET} URL Catbox kosong / expired
    {C_WHITE}Solusi:{C_RESET}
      • Buka URL di browser → cek muncul
      • Hapus cache & re-upload
      • Cek userhash valid

{C_RED}  ❌ Error 5: GitHub push failed{C_RESET}
    {C_WHITE}Penyebab:{C_RESET} Token salah / expired
    {C_WHITE}Solusi:{C_RESET}
      • Buat token baru (lihat menu 3)
      • Cek scope token = repo
      • Update config: menu 2 → 8

{C_RED}  ❌ Error 6: Config tidak tersimpan{C_RESET}
    {C_WHITE}Penyebab:{C_RESET} Bug lama (sudah diperbaiki)
    {C_WHITE}Solusi:{C_RESET}
      • Pastikan menu.py import save_config
      • Update menu.py versi terbaru

{C_YELLOW}  ═══════════════════════════════════════════════════════════{C_RESET}

{C_CYAN}  🔄 Reset Total:{C_RESET}

    Kalau bingung dengan error berantai:
    {C_WHITE}rm config.json uploads_cache.json deleted.json{C_RESET}
    {C_WHITE}v6{C_RESET} → Setup ulang dari menu 1

{C_CYAN}  💬 Bantuan Author:{C_RESET}

    Sertakan info:
    • OS & versi Python
    • Screenshot error lengkap
    • Kode file yang bermasalah
""")
    input(f"{C_GRAY}  [Enter untuk kembali]{C_RESET}")


def run_menu(cfg, callbacks):
    while True:
        clear_screen()
        print_banner()
        print_user_profile(cfg)
        print()
        print_main_menu()
        print()
        pilihan = input(f"{C_CYAN}  Pilih menu: {C_RESET}").strip()

        if pilihan == "1":
            cfg = wizard_setup(cfg)
            save_config(cfg)
            print(f"{C_GREEN}  [✓] Konfigurasi disimpan ke config.json{C_RESET}")
            time.sleep(1)
        elif pilihan == "2":
            cfg = quick_edit(cfg)
            save_config(cfg)
            print(f"{C_GREEN}  [✓] Konfigurasi disimpan ke config.json{C_RESET}")
            time.sleep(1)
        elif pilihan == "3":
            clear_screen()
            callbacks["run_upload"](cfg)
            input(f"\n{C_GRAY}  [Enter untuk kembali ke menu]{C_RESET}")
        elif pilihan == "4":
            preview_config(cfg)
        elif pilihan == "5":
            konfirm = input_prompt("  Hapus uploads_cache.json? (y/n)", default="n").lower()
            if konfirm in ("y", "yes", "ya"):
                callbacks["clear_cache"]()
        elif pilihan == "6":
            konfirm = input_prompt("  Bersihkan thumbnail lama? (y/n)", default="n").lower()
            if konfirm in ("y", "yes", "ya"):
                callbacks["cleanup_thumbs"]()
                input(f"\n{C_GRAY}  [Enter untuk kembali]{C_RESET}")
        elif pilihan == "7":
            check_media_folder(cfg)
        elif pilihan == "8":
            bantuan()
        elif pilihan == "9":
            callbacks["generate_manager"](cfg)
            input(f"\n{C_GRAY}  [Enter untuk kembali ke menu]{C_RESET}")
        elif pilihan == "10":
            menu_tools(cfg, callbacks)
        elif pilihan == "0":
            callbacks["reset_blacklist"]()
        elif pilihan == "99":
            print(f"\n{C_CYAN}  👋 Sampai jumpa!{C_RESET}\n")
            sys.exit(0)
        else:
            print(f"{C_RED}  ⚠️  Pilihan tidak valid.{C_RESET}")
            time.sleep(1)


def print_tools_menu():
    print(f"{C_CYAN}  ┌──────────────────────────────────────────────┐{C_RESET}")
    print(f"{C_CYAN}  │{C_MAGENTA}{C_BOLD}           🛠️  TOOLS & UTILITIES          {C_CYAN}  │{C_RESET}")
    print(f"{C_CYAN}  ├──────────────────────────────────────────────┤{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_MAGENTA} 1 {C_RESET} {C_WHITE}📤 Upload index.html ke GitHub{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_MAGENTA} 2 {C_RESET} {C_WHITE}🗜️  Compress HTML (minify){C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_MAGENTA} 3 {C_RESET} {C_WHITE}📊 Export Data ke CSV{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_MAGENTA} 4 {C_RESET} {C_WHITE}💾 Backup Project (zip){C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_MAGENTA} 5 {C_RESET} {C_WHITE}🔍 Verify Catbox URLs{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_MAGENTA} 6 {C_RESET} {C_WHITE}🔧 Fix Broken Cache{C_RESET}")
    print(f"{C_CYAN}  │{C_RESET}  {C_MAGENTA} 0 {C_RESET} {C_GRAY}↩️  Kembali ke Menu Utama{C_RESET}")
    print(f"{C_CYAN}  └──────────────────────────────────────────────┘{C_RESET}")


def menu_tools(cfg, callbacks):
    while True:
        clear_screen()
        print_banner()
        print(f"{C_YELLOW}{C_BOLD}  ══════════════ 🛠️  TOOLS & UTILITIES ══════════════{C_RESET}\n")
        print_tools_menu()
        print()
        pilihan = input(f"{C_CYAN}  Pilih tool: {C_RESET}").strip()

        if pilihan == "1":
            callbacks["upload_github"](cfg)
            input(f"\n{C_GRAY}  [Enter untuk kembali]{C_RESET}")
        elif pilihan == "2":
            callbacks["compress_html"](cfg)
            input(f"\n{C_GRAY}  [Enter untuk kembali]{C_RESET}")
        elif pilihan == "3":
            callbacks["export_csv"](cfg)
            input(f"\n{C_GRAY}  [Enter untuk kembali]{C_RESET}")
        elif pilihan == "4":
            callbacks["backup_project"](cfg)
            input(f"\n{C_GRAY}  [Enter untuk kembali]{C_RESET}")
        elif pilihan == "5":
            callbacks["verify_urls"](cfg)
            input(f"\n{C_GRAY}  [Enter untuk kembali]{C_RESET}")
        elif pilihan == "6":
            callbacks["fix_cache"](cfg)
            input(f"\n{C_GRAY}  [Enter untuk kembali]{C_RESET}")
        elif pilihan == "0":
            break
        else:
            print(f"{C_RED}  ⚠️  Pilihan tidak valid.{C_RESET}")
            time.sleep(1)