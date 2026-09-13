📸 Automated Media Uploader v6 — README.md (Versi Pendek)
<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=12,20,24,30&height=180&section=header&text=Automated%20Media%20Uploader&fontSize=44&fontColor=fff&animation=fadeIn&fontAlignY=35&desc=v6%20%E2%80%94%20Upload.%20Generate.%20Deploy.&descAlignY=58&descSize=16&descFontColor=FFE5B4" width="100%"/>

<h3><i>"Dari folder HP ke website online, dalam 20 menit."</i></h3>

<p>
<img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/Termux-Ready-000000?style=flat-square&logo=termux&logoColor=white"/>
<img src="https://img.shields.io/badge/GitHub_Pages-Deploy-181717?style=flat-square&logo=github&logoColor=white"/>
<img src="https://img.shields.io/badge/Catbox.moe-Host-FF6B6B?style=flat-square"/>
<img src="https://img.shields.io/badge/License-MIT-22c55e?style=flat-square"/>
</p>

</div>

---

## 📖 Daftar Isi

<table align="center">
<tr>
<td width="50%" valign="top">

**🎯 Untuk Pemula**
- [Kenalan Dulu Yuk](#-kenalan-dulu-yuk)
- [Kenapa Harus Pakai?](#-kenapa-harus-pakai)
- [Quick Start](#-quick-start)
- [Tutorial Lengkap](#-tutorial-lengkap)
- [Setup Userhash (WAJIB)](#-setup-userhash-catbox-wajib)

</td>
<td width="50%" valign="top">

**🚀 Untuk Lanjutan**
- [Dari Lokal ke Online](#-dari-lokal-ke-online)
- [Roadmap Visual](#-roadmap-visual)
- [Troubleshooting](#-troubleshooting)
- [Support & Donasi](#-support--donasi)
- [Author](#-author)

</td>
</tr>
</table>

---

## ✨ Kenalan Dulu Yuk

<div align="center">

### 💭 *"Pulang liburan bawa 5.000 foto. 20 menit kemudian semua sudah jadi website galeri."*

**Itu bukan mimpi. Itu Automated Media Uploader v6.** 🎉

</div>

Script Python yang bekerja seperti **pipa ajaib**:

```mermaid
flowchart LR
    A["📁 Folder Anda"] --> B["☁️ Catbox"]
    B --> C["🎨 Website HTML"]
    C --> D["🌐 Online"]
    
    style A fill:#FFE5B4,stroke:#FF9800,stroke-width:2px,color:#000
    style B fill:#FFB6C1,stroke:#E91E63,stroke-width:2px,color:#000
    style C fill:#B4E5FF,stroke:#2196F3,stroke-width:2px,color:#000
    style D fill:#B4FFB4,stroke:#4CAF50,stroke-width:2px,color:#000
3 menit setup, 1 klik upload, langsung online. 🚀

💡 Kenapa Harus Pakai?
🆚 Perbandingan Jujur
Fitur	Media Uploader v6	Google Photos	Flickr	Self-host VPS
Gratis total	✅	⚠️ (15GB)	⚠️ (1000)	❌ (Rp 50rb+)
Tanpa login viewer	✅	❌	❌	✅
Website pribadi	✅	❌	⚠️	✅
Unlimited upload	✅	❌	❌	✅
Setup time	⚡ 3 menit	1 menit	5 menit	🐌 2 jam
Butuh coding	❌	❌	❌	✅
Open source	✅	❌	❌	✅
🎯 Cocok Untuk
📸
Fotografer
Portofolio gratis	👨‍👩‍👧‍👦
Keluarga
Arsip generasi	🎨
Creator
Backup visual	🏪
UMKM
Katalog produk
✨ Fitur Utama
📤 Upload massal ke Catbox.moe dengan progress bar
🧠 Auto-tag dari nama file + EXIF + OCR + deteksi wajah
🎨 10 tema galeri — Dark, Light, Cyberpunk, dll
📐 6 layout — Mosaic, Grid, List, Cinema, dll
🔍 Search & filter lengkap
🌐 Deploy otomatis ke GitHub Pages
💾 Cache system — hindari upload ulang
🛠️ Manager panel untuk kelola file
⚡ Quick Start
# 1. Clone
git clone https://github.com/nexterade/automated-media-uploader.git
cd automated-media-uploader

# 2. Install
pip install requests requests-toolbelt Pillow

# 3. Siapkan folder
mkdir -p media/Wisata
# Copy foto ke media/Wisata/

# 4. Jalankan
python main.py

# 5. Setup wizard (menu 1) — WAJIB isi userhash!
# 6. Upload & generate (menu 3)
# 7. Buka index.html
Selesai! 🎉

📚 Tutorial Lengkap
🛠️ Persiapan Awal
Step 1: Install Python & Dependencies
Step 2: Siapkan Folder Media
Step 3: Buat Shortcut (Optional, tapi Recommended)
Step 4: Jalankan & Ikuti Wizard
🔑 Setup Userhash Catbox (WAJIB)
⚠️ PENTING: Userhash WAJIB diisi. Tanpa userhash, upload akan sering gagal & kena rate limit.

❌ Tanpa Userhash (Anonymous)
Masalah	Dampak
🚫 Rate limit ketat	~10 file per 30 menit
❌ Sering gagal	Server tolak request
🗑️ Tidak bisa manage	Tidak bisa hapus/edit
⏳ Batch pause lama	60 detik tiap 30 file
🔥 Risiko banned	IP bisa diblokir
✅ Dengan Userhash
Benefit	Penjelasan
⚡ Upload stabil	Tanpa rate limit ketat
🚀 Lebih cepat	Upload ribuan file lancar
🛠️ Manage file	Bisa hapus via Catbox panel
🔐 Ownership jelas	File terhubung akun Anda
📝 Cara Mendapatkan Userhash
Step 1: Buka catbox.moe → klik Create Account → isi form → verifikasi email.

Step 2: Login → buka catbox.moe/user/manage.php → scroll ke "User Hash" → COPY.

Format userhash:

a1b2c3d4e5f6789012345678abcdef01
Step 3: Paste di wizard Step 1/9, atau edit manual di config.json:

{
  "userhash": "a1b2c3d4e5f6789012345678abcdef01"
}
Step 4: Test upload via menu 3. Kalau lancar, userhash valid! ✅

🔐 Jangan share userhash ke publik — treat seperti password!

🚀 Upload & Generate
Setelah wizard selesai, pilih menu 3. Script akan:

[1/5] 📂 Scan folder media...        ✅
[2/5] ☁️ Upload ke Catbox.moe...      ✅
[3/5] 🧠 Extract metadata...         ✅
[4/5] 📄 Generate index.html...      ✅
[5/5] ⚙️ Generate manager.html...    ✅

📊 ATOS BERES BOSS!
📂 Total: 47 file | ✅ 35 upload | ⚡ 12 cache
⏱️  Durasi: 12m 27s | 🌐 Kuota: 245.3 MB

📤 Upload ke GitHub sekarang? [y/n]: _
y → Push ke GitHub (butuh token)
n atau Enter → Simpan lokal
Buka galeri:

termux-open index.html          # Termux
xdg-open index.html             # Linux
open index.html                 # macOS
start index.html                # Windows

# ATAU via HTTP (recommended):
python -m http.server 8000
# Buka http://localhost:8000
🌐 Dari Lokal ke Online
🎯 Deploy ke GitHub Pages (GRATIS)
Step 1: Buat Akun — github.com/signup

Step 2: Buat Repository — Klik + → New repository

Repository name:  galeri-keluarga
Visibility:       ✅ Public
Add README:       ✅ Centang
Step 3: Buat Token — github.com/settings/tokens

Note:     galeri-bot
Scopes:   ✅ repo (centang semua)
SALIN TOKEN (hanya muncul sekali!)

Step 4: Aktifkan Pages — Settings → Pages → Branch: main, Folder: / (root) → Save

Step 5: Deploy — Jalankan menu 3, ketika ditanya GitHub pilih y. Galeri online di:

https://USERNAME.github.io/galeri-keluarga/
Update nanti: Tambah foto → menu 3 → y → selesai!

🗺️ Roadmap Visual
📊 Timeline
Apr 2025
May 2025
Jun 2025
Jul 2025
Aug 2025
Sep 2025
Oct 2025
Nov 2025
Dec 2025
Jan 2026
Feb 2026
Mar 2026
Apr 2026
May 2026
Jun 2026
Enkripsi Token
PWA Support
JPG to WebP
Auto Dark Mode
ImgBB & Telegraph
Video Transcoding
AI Auto-Caption
Duplicate Detection
Face Recognition
Password Protect
GUI Desktop
Mobile App Flutter
v6.1 Polish
v6.2 Multi-Cloud
v6.3 Smart
v7.0 Next Gen
Roadmap Automated Media Uploader v6
📊 Progress Overview
v6.0 ████████████████████████████████ 100% ✅ RILIS
v6.1 ████████████░░░░░░░░░░░░░░░░░░░░  40% 🚧 IN PROGRESS
v6.2 ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░  10% 📅 PLANNED
v6.3 ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   0% 💭 BACKLOG
v7.0 ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   0% 💭 VISION
🎯 Detail per Versi
🔷 v6.1 — "Polish" (Q2 2025) — 40%
🔷 v6.2 — "Multi-Cloud" (Q3 2025) — 10%
🔷 v6.3 — "Smart" (Q4 2025) — 0%
🔷 v7.0 — "Next Gen" (2026) — 0%
🛠️ Troubleshooting
🔥 Error: ModuleNotFoundError
🔥 Upload gagal terus
🔥 Gambar tidak muncul di HTML
🔥 GitHub push failed
🔥 Reset Total
💎 Support & Donasi
💖 Kalau project ini bermanfaat, dukung saya!
Setiap donasi = semangat baru untuk terus update! 🚀

☕ Traktir Kopi
Saweria

Saweria (Indonesia)


QRIS, GoPay, OVO, Dana, ShopeePay

Ko-fi

Ko-fi (Internasional)


PayPal, Credit Card, Apple Pay

🪙 Crypto Donation
₿ Bitcoin (BTC)
bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh
Network: Bitcoin (BTC)

Ξ Ethereum (ETH)
0x71C7656EC7ab88b098defB751B7401B5f6d8976F
Network: ERC-20 (Ethereum)

₮ USDT (TRC-20)
TN9RRaXkCFtTXRso2GdTZxSxxwBb2dFd4S
Network: TRON (TRC-20)

◎ Solana (SOL)
DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK
Network: Solana

💡 Tips: Scan dengan crypto wallet, atau copy-paste. Pastikan network sesuai sebelum kirim!

🎁 Cara Lain Mendukung
⭐
Star Repo
Di GitHub	🐛
Report Bug
Bantu perbaiki	📢
Share
Ke teman	🤝
Kontribusi
Pull request
👨‍💻 Author
@nexterade
@nexterade
Full-stack Developer • Automation Enthusiast • Indonesia 🇮🇩

  

"Code with passion, share with love."
📖 Tentang Author
Halo! Saya @nexterade 👋 Developer yang suka bikin tool automation untuk mempermudah hidup. Project ini awalnya dibuat untuk kebutuhan pribadi (backup galeri keluarga), tapi setelah sharing di komunitas, banyak yang request — jadi saya putuskan untuk open source.

💭 "Bikin teknologi yang powerful, tapi tetap sederhana. Untuk siapa pun, di mana pun."

Kanal	Untuk	Response
🐛 Issues	Bug report	1-3 hari
💡 Discussions	Ide	1-7 hari
✈️ Telegram	Chat	1-24 jam
📄 Lisensi
MIT License — Bebas digunakan, dimodifikasi, didistribusikan.

Copyright (c) 2025 @nexterade

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

⭐ Kalau bermanfaat, jangan lupa star! ⭐
╔═══════════════════════════════════════════════╗
║   📸 Upload  →  🎨 Generate  →  🌐 Deploy    ║
║                                               ║
║   Automated Media Uploader v6                 ║
║   Made with ❤️  in Indonesia 🇮🇩              ║
╚═══════════════════════════════════════════════╝
⬆ Kembali ke Atas

```
