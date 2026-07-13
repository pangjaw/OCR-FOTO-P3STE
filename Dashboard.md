# 🗂️ OCR Foto Timemark - Project Dashboard

> [!warning] **🤖 Untuk AI Assistant: File ini SUDAH berisi arsitektur sistem lengkap.** Baca file ini saja sudah cukup memahami pipeline, fungsi script, logika deteksi, dan struktur data.

> [!abstract] **Project Overview**
> Project ini mengotomatisasi koreksi tanggal watermark (Timemark GPS Map Camera) pada foto dokumentasi kerja batch. Input: PDF 2026 (foto asli) + PDF 2025 (template lama). Output: PDF 2025 yang sudah di-upgrade dengan foto baru ber-timemark koreksi tanggal. Pipeline 5 tahap: Export → Extract Dates → Schedule → Edit Timemark → Merge PDF.

---

## 📖 MANDATORY READING ORDER (Untuk AI Agent)

> [!important] **Setelah baca Dashboard.md ini, WAJIB baca file berikut BERURUTAN untuk konteks lengkap:**

| Urutan | File | Tujuan | Estimasi Waktu Baca |
|--------|------|--------|---------------------|
| 1 | **Dashboard.md** (file ini) | Arsitektur sistem, data flow, detection logic, config schemas, glossary, status tracker, daily logs summary | 3-5 menit |
| 2 | **AGENTS.md** | Complete AI context: function reference dengan nomor line, debugging patterns, critical rules (debug protocol, auto-git commit) | 5-8 menit |
| 3 | **Notes/Daily/2026-07-13.md** | **Update terbaru: 7 asset types synced, merge_pdf_foto.py updated, JSON configs expanded** | 2-3 menit |
| 3 | **Notes/Daily/2026-07-13.md** | Update terbaru: browser freeze fix, EventSource reconnect loop fix | 1-2 menit |
| 4 | **Notes/Daily/2026-07-11.md** | Bug fix folder consensus: `_folder_key_from_path` untuk input folder aset tunggal | 1-2 menit |
| 5 | **Notes/Decisions/ADR-001.md** | ADR-001: Pillow & Numpy vs OpenCV | 1 menit |
| 6 | **Notes/Decisions/ADR-002.md** | ADR-002: Ekstraksi gambar PDF via pypdf | 1 menit |
| 7 | **Notes/Decisions/ADR-003.md** | ADR-003: Aturan parsing layout PDF & struktur output | 1 menit |
| 8 | **setup.md** | Instalasi, dependensi, cara menjalankan (jika perlu setup environment) | 2-3 menit |
| 9 | **README.md** | Tujuan project & batasan utama (jika perlu konteks bisnis) | 1-2 menit |

> [!tip] **Total estimasi: ~15-20 menit untuk konteks penuh.** Agent tidak perlu menunggu instruksi user untuk lanjut ke file berikutnya — baca otomatis berurutan.

---

## 🔄 Complete Data Flow Pipeline

```
┌──────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌──────────────┐
│ 01_pdf_source│     │ 02_pdf_target│     │ 03_photos_export│     │ 04_photos_edited│     │05_pdf_merged │
│  (PDF 2026)  │     │  (PDF 2025)  │     │  (foto asli)    │     │  (foto edit)    │     │  (PDF final) │
└──────┬───────┘     └──────┬───────┘     └────────┬────────┘     └────────┬────────┘     └──────┬───────┘
       │                    │                      │                      │                      │
       ▼                    ▼                      │                      │                      │
┌──────────────┐     ┌──────────────┐              │                      │                      │
│export_pdf_   │     │extract_pdf_  │              │                      │                      │
│foto.py       │     │dates.py      │              │                      │                      │
│(Step 1)      │     │(Step 2)      │              │                      │                      │
└──────┬───────┘     └──────┬───────┘              │                      │                      │
       │                    │                      │                      │                      │
       │         date.txt   │                      │                      │                      │
       │◄───────────────────┤                      │                      │                      │
       │                    │                      ▼                      │                      │
       │                    │            ┌─────────────────┐              │                      │
       │                    │            │   scheduler.py  │              │                      │
       │                    │            │   (Step 3)      │              │                      │
       │                    │            │ schedule.json   │              │                      │
       │                    │            └────────┬────────┘              │                      │
       │                    │                     │                      │                      │
       └────────────────────┼─────────────────────┼──────────────────────┘                      │
                            ▼                     ▼                                             ▼
                   ┌─────────────────┐   ┌─────────────────┐                          ┌──────────────┐
                   │ edit_timemark_  │   │ merge_pdf_foto. │                          │ 05_pdf_merged│
                   │ ide1.py         │   │ py (Step 5)     │                          │ (hasil akhir)│
                   │ (Step 4)        │   │                 │                          └──────────────┘
                   │ --schedule      │   │ --schedule      │
                   └─────────────────┘   └─────────────────┘
```

### Struktur Folder (Dipertahankan Seluruh Pipeline — Baru: Berbasis Station)
```
root/
├── 01_pdf_source/          ← PDF 2026 mentah (input export_pdf_foto.py)
├── 02_pdf_target/          ← PDF 2025 target (input merge_pdf_foto.py & extract_pdf_dates.py)
├── 03_photos_export/       ← Hasil ekstraksi foto dari PDF (kerja edit)
│   └── {station}/          ← Subfolder per Station (BOO, CLT, BOP, BTT, MSG, CGB, BJD, CCR, COS, CS, BNR, dst)
│       └── {asset_type}/   ← Subfolder per tipe aset (AXC, WESEL, SINYAL, CATU_DAYA, PINTU_PERLINTASAN, TELEKOMUNIKASI, PERSINYALAN_ELEKTRIK)
│           └── {detail_aset}/  ← Subfolder per detail aset
│               ├── 0.jpg
│               ├── 50.jpg
│               ├── 100.jpg
│               └── date.txt    ← Dari extract_pdf_dates.py
├── 04_photos_edited/       ← Output foto hasil edit timemark
│   └── Tim_{n}/            ← Subfolder per Tim jika pakai --schedule
│       └── {station}/
│           └── {asset_type}/
│               └── {detail_aset}/
│                   ├── 0.jpg
│                   ├── 50.jpg
│                   └── 100.jpg
├── 05_pdf_merged/          ← PDF final hasil gabung
├── backup_script_v1/       ← Backup kode lama
├── logs/                   ← Log CSV export & merge
├── templates/              ← HTML template untuk app.py (Flask)
└── Notes/                  ← Obsidian vault (Daily/, Decisions/, Templates/)
```

**Aturan penting:** Subfolder dipertahankan di seluruh pipeline. Hierarchy baru: `station/asset_type/detail`. Jika PDF ada di `01_pdf_source/sub/`, maka outputnya akan di `03_photos_export/sub/`, dst.

---

## 🐍 Script Reference Table

| Script | Fungsi Utama | Input | Output | Key Functions |
|--------|--------------|-------|--------|---------------|
| **export_pdf_foto.py** | Ekstrak foto asli dari PDF 2026 | `01_pdf_source/*.pdf` | `03_photos_export/{type}/{detail}/0,50,100.jpg` | `extract_asset_rows()`, `export_pdf()`, `asset_output_dir()`, `sanitize_segment()` |
| **extract_pdf_dates.py** | Ambil tanggal dari PDF 2025 halaman 1 | `02_pdf_target/*.pdf` | `date.txt` per folder aset di `03_photos_export/` | `parse_date_indonesian()`, `format_date_target()`, `extract_date_from_pdf()` |
| **scheduler.py** | Jadwal Tim 1/2 (07:00-18:00) + timestamp per foto | PDF target + `asset_waktu_mapping.json` + `data_acuan_tenaga_gabungan.json` | `schedule.json` | `build_schedule()`, `get_waktu()`, `load_mapping()`, `_parse_date()` |
| **edit_timemark_ide1.py** | **Core**: Deteksi Red Guide → Hapus tanggal lama → Tulis timemark baru | `03_photos_export/` + `date.txt` atau `schedule.json` | `04_photos_edited/` (struktur dipertahankan) | `find_red_guide()`, `place_textbox_fixed_offset()`, `locate_date_box()`, `process_image()`, `_collect_folder_consensus()` |
| **merge_pdf_foto.py** | Gabung foto edit ke PDF 2025 (hapus kolase lama) | `02_pdf_target/*.pdf` + `04_photos_edited/` | `05_pdf_merged/*.pdf` | `extract_asset_rows()`, `process_pdf()`, `draw_header()`, `draw_centered_label()` |
| **app.py** | Flask Web Dashboard (port 5000) | - | UI 5-step pipeline + SSE logs | `pipeline_thread()`, `run_command_stream()`, `/api/run`, `/api/stream-logs` |

---

## 🔬 Core Detection Logic (edit_timemark_ide1.py)

### 4-Stage Priority System (`locate_date_box`)
```
STAGE 0 (--y-override): Paksa posisi manual Y
    │
    ▼ (tanpa override)
STAGE 1C - Red Guide Original: find_red_guide() di gambar asli → fixed offset textbox
    │ gagal
    ▼
STAGE 1C - Folder Consensus: ≥2 foto di folder sama punya Red Guide gy1 konsisten (≤10px) → synthetic guide
    │ gagal
    ▼
STAGE FALLBACK: get_text_box() → posisi default kiri bawah (x=4.7%, y=73.5%, w=49%, h=82%)
```

### HSV Orange Isolation (`preprocess_for_guide`)
- Grayscale semua warna KECUALI merah murni guide: Hue 0-10°/350-360°, Sat≥65%, Val 25-85%
- Mengecualikan oranye (15-35°) yang muncul di belakang Red Guide

### Red Guide Detection (`find_red_guide`)
- Filter RGB: `r > 145` & `r > g*1.5` & `r > b*1.5` & `g < 195` & `b < 155`
- Area search: kolom kiri (x < 16% lebar), bawah (y > 54% tinggi)
- Min height: max(25px, 5.5% tinggi gambar)
- Pilih kandidat skor tertinggi (jumlah pixel merah)

### Fixed Offset Textbox Placement (`place_textbox_fixed_offset`)
- `X_OFFSET_FROM_GUIDE = 6px` (kanan tepi guide)
- `Y_CENTER_OFFSET = 0` (center textbox = guide top/gy1)
- `BOX_HEIGHT_RATIO = 0.053` (5.3% tinggi gambar ≈ 16px @ 300px)
- `BOX_WIDTH_RATIO = 0.42` (42% lebar gambar)

### Folder-Level Consensus Voting (`_collect_folder_consensus`)
- Pre-scan seluruh folder sebelum proses
- Kumpulkan `gy1` (guide top-Y) per folder aset
- Jika ≥2 foto setuju dalam radius 10px → median jadi `consensus_gy1`
- Dipakai sebagai fallback Stage 1C consensus untuk foto yang guide-nya gagal terdeteksi

### Drawing Details
- Font: Arial/Calibri/DejaVu (auto-detect), size = `int(w * 0.038)`
- Textbox: rounded rect hitam transparan (alpha 140), shadow + stroke
- Erase: `diffuse_fill_region` 60 iterasi, mask 1px padding, radius rounded
- Box height: `int(h * 0.053)` (16px untuk h=300)
- Narrow mask: 5px extra ke atas (bukan 14px lama)

---

## ⚙️ Config Schemas

### schedule.json
```json
{
  "version": 1,
  "schedules": [
    {
      "file": "nama.pdf",
      "date": "Rabu, Jul 08 2026",
      "tim": 1,
      "assets": [
        {
          "type": "AXC",
          "detail": "ZP 60 BOO",
          "code": "AXL11468",
          "waktu_menit": 45,
          "photos": {
            "0.jpg": "2026-07-08T07:00:00",
            "50.jpg": "2026-07-08T07:22:30",
            "100.jpg": "2026-07-08T07:45:00"
          }
        }
      ]
    }
  ]
}
```

### asset_waktu_mapping.json
```json
{
  "AXC": {
    "ZP 60 BOO": { "asset_id": 11468 },
    "ZP 41 BOO": { "asset_id": 11469 }
  },
  "WESEL": { ... },
  "SINYAL": { ... }
}
```

### data_acuan_tenaga_gabungan.json
```json
{
  "aset": [
    { "id": 11468, "waktu_menit": 45, ... },
    { "id": 11469, "waktu_menit": 30, ... }
  ]
}
```

### date.txt (per folder aset)
```
Rabu, Jul 08 2026
```
*Format: `Hari, BulanSingkat DD YYYY` (singkat untuk watermark). `merge_pdf_foto.py` pakai bulan panjang untuk header PDF.*

---

## 📚 Domain Glossary

| Istilah | Arti |
|---------|------|
| **Timemark** | Watermark GPS Map Camera di pojok kiri bawah foto dokumentasi |
| **Red Guide** | Garis oren/merah vertikal asli dari GPS Map Camera, anchor posisi |
| **Stage 1-4** | Sistem prioritas deteksi posisi textbox (lihat diagram di atas) |
| **AXC** | Axle Counter — kode aset prefix AXL (contoh: AXL11468) |
| **WESEL** | Wesel — kode aset prefix WSL (contoh: WSL11080) |
| **SINYAL** | Sinyal — kode aset prefix SIN |
| **CATU_DAYA** | Catu Daya — kode aset prefix CDA (Genset, UPS, Battery Bank) |
| **PINTU_PERLINTASAN** | Pintu Perlintasan — kode aset prefix JPL (Telepon, Elektrik, Gentanik) |
| **TELEKOMUNIKASI** | Telekomunikasi — kode aset prefix TLK/TWR (Radio, Telepon) |
| **PERSINYALAN_ELEKTRIK** | Persinyalan Elektrik — kode aset prefix TRA/INB (Serat Optik, Bangunan) |
| **CATU_DAYA** | Catu Daya — kode aset prefix CDA (Genset, UPS, Battery Bank) |
| **PINTU_PERLINTASAN** | Pintu Perlintasan — kode aset prefix JPL (Telepon, Elektrik, Gentanik) |
| **TELEKOMUNIKASI** | Telekomunikasi — kode aset prefix TLK/TWR (Radio, Telepon) |
| **PERSINYALAN_ELEKTRIK** | Persinyalan Elektrik — kode aset prefix TRA/INB (Serat Optik, Bangunan) |
| **0%, 50%, 100%** | 3 foto dokumentasi per aset: awal, tengah, akhir |
| **PDF 2025 vs 2026** | Format lama (2025) = foto kolase halaman terakhir. Format baru (2026) = foto hasil edit disusun ulang |
| **date.txt** | File metadata di folder aset berisi tanggal target format "Rabu, Jul 08 2026" |
| **schedule.json** | File penjadwalan: mapping aset→Tim→timestamp ISO per foto |
| **Konsensus Folder** | Pre-scan folder: 2+ file setuju Y dalam 10px → apply ke semua file |
| **Overflow Rule** | Aset mulai < 18:00 tetap selesai 3 fotonya. File berikutnya → Tim berikutnya/reset jam |
| **Waktu Menit** | Durasi pengerjaan per aset (default: AXC/WESEL=45, SINYAL=30, CATU_DAYA=45, PINTU_PERLINTASAN=45, TELEKOM=60-120, PERSINYALAN=420) |
| **ZP 41B fix** | Typo di PDF 2025: ZP 41B BOO seharusnya ZP 41 BOO |
| **diffuse_fill_region** | Inpainting berbasis difusi untuk hapus teks tanggal lama |

---

## 📌 Status Tracker

### Active Scripts
- [x] `app.py` - Server Web Lokal (Dashboard UI) untuk mempermudah jalannya seluruh alur kerja
- [x] `edit_timemark_ide1.py` - Script utama pengedit watermark: HSV Orange Isolation + Fixed-offset Stage 1c. Folder Consensus fix untuk input folder aset tunggal. 237/237 sukses.
- [x] `export_pdf_foto.py` - Script ekstraksi foto asli dari PDF
- [x] `merge_pdf_foto.py` - Script penggabung foto baru (format 2026) kembali ke PDF lama (format 2025)
- [x] `extract_pdf_dates.py` - Script ekstraksi tanggal otomatis dari PDF target
- [x] `scheduler.py` - Script penjadwalan 2 Tim (07:00-18:00)

### Done (Selesai) - Core Pipeline
- [x] **Web UI Dashboard Terpadu (`app.py`)**: Penggabungan seluruh skrip ke dalam satu UI web lokal modern dengan visual dark glassmorphism, pemantauan progres real-time via log terminal, dan konfigurasi direktori kerja.
- [x] **Dukungan Subfolder Aset Seluruh Pipeline**: Modifikasi alur kerja pada skrip ekspor, ekstraksi tanggal, dan penggabungan PDF agar mempertahankan struktur subfolder aset ke dalam hasil akhir.
- [x] **Ekstraksi Tanggal Otomatis & Pemetaan `date.txt`**: Implementasi script `extract_pdf_dates.py` untuk mengambil tanggal baru dari halaman foto dokumentasi PDF target di folder `02_pdf_target/`, menerjemahkannya ke Bahasa Indonesia disingkat, dan menyimpannya sebagai file metadata `date.txt` per folder aset.
- [x] **Integrasi Tanggal Dinamis di Script Utama**: Modifikasi `edit_timemark_ide1.py` agar secara otomatis membaca tanggal baru dari file `date.txt` di subfolder aset secara dinamis tanpa intervensi manual (prompt) dari user.
- [x] **Gabung Foto PDF (`merge_pdf_foto.py`)**: Berhasil membuat skrip penggabung foto hasil edit (format 2026) kembali ke PDF lama 2025. Hasil batch 19 PDF: 19 berkas sukses ter-upgrade dengan layout 2026 yang baru secara dinamis dan rapi.
- [x] **FINAL — Semua 168 foto Berhasil**: Deteksi noise kuning Red Guide di ZP 13 dengan Opsi A (ratio-based `r > g*1.3`) sukses. Stage logging ditambahkan agar user tahu stage mana yang dipakai per file. Semua file lolos dengan Stage 1 (Tanggal), Stage 2 (Alamat), atau Stage 3 (Red Guide).
- [x] **Integrasi 3 Stage ke Script Utama (Tukar Stage)**: Prioritas 1 (Tanggal Konsensus), Prioritas 2 (Alamat Konsensus), Prioritas 3 (Red Guide Lokal) untuk mengabaikan Red Guide Palsu.
- [x] **Deteksi Kegagalan (Stage 4)**: Melewati (skip/tidak memproses) file yang gagal dideteksi secara otomatis dan menampilkan warning detail di akhir run konsol.
- [x] **Implementasi penyejajaran batas atas Red Guide (`y1 = guide_y1`), tinggi box 13px, dan padding mask 2px untuk visual 100% rapi dan aman dari tabrakan alamat.**
- [x] **Rerun Batch seluruh 168 foto dengan logic Tukar Stage sukses diproses 100% tuntas ke `output_proses_all`.**
- [x] **Logika Folder-Level Red Guide Consensus Voting**: Mempindai semua file di folder untuk menentukan Red Guide mayoritas dan mencegah Red Guide Palsu (seperti Y1=185 pada JL52 50.jpg) mengacaukan penempatan.
- [x] **Logika Folder-Level Cross-File Reference (Konsensus Cerdas)**: Implementasi pre-scan folder untuk menentukan posisi Y tanggal/alamat berdasarkan voting mayoritas ≥2 file sejenis.
- [x] **Batch Ulang seluruh 168 foto dengan logic Mask Mepet Textbox + Tinggi Box 16px (Final) sukses diproses 100% bersih ke `output_proses_all`.**
- [x] **Optimasi Mask Mepet Textbox**: Menghilangkan perluasan mask ke atas dan menaikkan tinggi date box baru `box_h` menjadi `int(h * 0.053)` (16px), menutupi tanggal lama secara bersih di dalam area textbox tanpa blur yang lebar di luar.
- [x] **Optimasi lebar blur (Narrow Mask)**: Mempersempit tinggi perluasan area hapus ke atas dari `14px` menjadi `5px`.
- [x] **Perbaikan bug logika pada Erase Mask di `process_image`**: Memperluas range mask biner `rounded_rectangle` ke arah atas (dimulai dari Y=0 pada area crop) agar tambahan tinggi 14px untuk penghapusan tanggal lama benar-benar diproses oleh `diffuse_fill_region`.
- [x] **Batch Ulang seluruh 168 foto dengan logic Stage 1 Thresh 215 + Fallback clipping range (Gap 0px) selesai sukses diproses ke `output_proses_all`.**
- [x] **Optimasi loop binarisasi Stage 1 dengan menambahkan threshold tinggi `215` (melawan noise latar belakang abu-abu terang), membuat ZP 92 50 berhasil dideteksi via Stage 1 dengan confidence 95%.**
- [x] **Batch Ulang seluruh 168 foto dengan logic Dynamic Gap terbaru (Gap 0px untuk baris 1 alamat) sukses diproses ke `output_proses_all`.**
- [x] **Implementasi Dynamic Gap pada Stage 2 fallback berbasis rasio Y alamat teratas yang rata-kiri (`left < 30px`), menyelesaikan perbedaan deteksi baris alamat secara otomatis.**
- [x] **Verifikasi Stage 2 fallback (address detection) sukses pada L62A 50 dan JL32A 50.**
- [x] **Confidence filter (< 30) di Stage 1 keyword detection — kurangi false positive AM/PM dari noise OCR.**
- [x] **Stage 2 fallback: deteksi alamat area kiri-bawah (threshold 150 PSM 4), prioritaskan text rata-kiri (left < 30).**
- [x] **Folder-level OCR voting: 2+ file setuju Y → apply ke semua file di folder itu.**
- [x] **Expanded erase area (+14px ke atas) nutup teks lama 2 baris.**
- [x] **`--y-override` CLI arg buat paksa Y manual (skip OCR).**
- [x] **Batch 168/168 foto: lulus bersih mutlak (final).**
- [x] **Opsi A (ratio-based red detection):** Toleransi noise kuning di Red Guide — `r > g*1.3` menggantikan `r > g+22` — ZP 13 guide_y1 kembali normal 185px.
- [x] **Stage Logging:** Setiap file cetak stage yang dipakai (Stage 0/1/2/3/4) untuk transparansi proses.
- [x] **Cleanup total project:** Hapus semua scratch, debug scripts, test output, stale directories. Hanya menyisakan script utama + folder kerja.
- [x] **Eksperimen PaddleOCR — gagal (oneDNN bug di Windows, skip).**
- [x] **Eksperimen EasyOCR — preprocessing gak bantu (gak bisa fokus 1 baris).**
- [x] **Tesseract `--psm 7` tetap engine terbaik untuk kasus ini.**

### Done (Time + 2 Teams Scheduling)
- [x] **Mapping Manual Aset → Waktu:** `asset_waktu_mapping.json` — scan PDF halaman 1.
- [x] **`scheduler.py` [NEW]:** Baca PDF + mapping + date → hitung jadwal 07:00-18:00 per Tim → output `schedule.json`.
- [x] **`edit_timemark_ide1.py` — Arg `--schedule` & Tim folder:** `--schedule schedule.json`, format `"Rabu, Jul 08 2026 09:30"`, output ke `04_photos_edited/Tim_{n}/...`.
- [x] **`merge_pdf_foto.py` — Arg `--schedule`:** Path foto dari `Tim_{n}` folder via schedule.json lookup.
- [x] **Overflow Aman:** Aset mulai < 18:00 tetap selesai 3 fotonya, file berikutnya pindah Tim/reset jam.
- [x] **Stage 1c (Red Guide Anchor):** Untuk foto dengan Red Guide terdeteksi tapi OCR gagal total (seperti CLT), gunakan posisi baru: textbox di KANAN guide, center sejajar dengan bagian ATAS guide, box extends 25% up / 75% down. Berhasil menangani 18/18 foto gagal sebelumnya (6 folder: ZP 12B/13/14B/20A/24B CLT + ZP 31D BOO). Total: 237/237 foto berhasil (100%).

### Done (Testing Pipeline Penuh)
- [x] **Testing pipeline penuh (Stage 1→5):** `export_pdf_foto.py` → `extract_pdf_dates.py` → `scheduler.py` → `edit_timemark_ide1.py --schedule` → `merge_pdf_foto.py --schedule`. **43 PDF berhasil digabung**, 36 di-skip (foto tidak lengkap), 0 error. Tim rotation & overflow berfungsi.
- [x] **Verifikasi visual Stage 1c:** 18 foto Red Guide Anchor (CLT + ZP 31D BOO) berhasil diproses dengan posisi textbox benar di kanan guide, center sejajar atas guide.
- [x] **Step Indicator Bar di Web UI Dashboard:** Visual bar dinamis (Step 1-5) dengan indikasi warna (Indigo: Active, Hijau: Done, Merah: Error) yang tersinkronisasi via polling status API `/api/status`.
- [x] **Perbaikan Path Lookup Foto pada `merge_pdf_foto.py`:** Memperbaiki pencarian foto di folder flat per tim (`Tim_N/...`) pada mode `--schedule` sehingga pipeline tahap 5 dapat menyisipkan foto hasil edit secara sukses.
- [x] **Fix Path Integrity pada `edit_timemark_ide1.py`:** Menambahkan pengecekan `Path.resolve()` untuk memastikan struktur folder `Tim_N` dibuat secara absolut sebelum operasi penulisan file berlangsung, mencegah error `FileNotFound` pada sistem file Windows.
- [x] **Folder Consensus Fix (`edit_timemark_ide1.py`):** Perbaikan `_folder_key_from_path` agar mendukung input folder aset tunggal (mis. `03_photos_export/AXC/ZP 42B BOO/`) selain full tree. Saat `relative_to(input_dir)` hanya mengembalikan nama file, fungsi sekarang mengambil `asset_type` dari `input_dir.parent.name` dan `detail` dari `input_dir.name`. Terverifikasi: ZP 42B BOO (3 foto) → 3/3 sukses, consensus gy1=185; Full AXC (402 foto) → 402/402 sukses.


### 🆕 Done (2026-07-13) - 7 Asset Types Full Support
- [x] **Sync detect_asset_type() di merge_pdf_foto.py ke 7 tipe:** CATU_DAYA, PINTU_PERLINTASAN, TELEKOMUNIKASI, PERSINYALAN_ELEKTRIK (seimbang dengan export_pdf_foto.py). Verified: return values identik.
- [x] **Sync extract_detail() di merge_pdf_foto.py:** Tambah handling detail untuk 4 tipe baru (GENSET/UPS/BATTERE, JPL/JPLE/GENTANIK, TELEPON/RADIO/OTB, BANGUNAN/DALAM PERSINYALAN).
- [x] **Sync is_valid_asset_title() di merge_pdf_foto.py:** Tambah keywords untuk 7 tipe asset (CATU DAYA, PINTU PERLINTASAN, TELEKOMUNIKASI, PERSINYALAN ELEKTRIK, JPL, GENTANIK, RADIO, SERAT OPTIK, OTB, BANGUNAN, GENSET, UPS, BATTERE, PANEL, RECTIFIER, MESIN, MOTOR, TOWER, ANTENA, INTERLOCKING, INPUT).
- [x] **ZP 41B workaround dipertahankan** di kedua extract_detail (export & merge).
- [x] **Update asset_waktu_mapping.json:** Tambah mapping lengkap untuk CATU_DAYA (23 entry), PINTU_PERLINTASAN (7 entry), TELEKOM_STASIUN/LUAR/PINTU (3 split), PERSINYALAN_ELEKTRIK (2 entry) — referensi data_acuan_tenaga_gabungan.json id 5,16,17,34-38.
- [x] **Update checklist_types.json:** Category split per folder — CATU_DAYA, PINTU_PERLINTASAN, TELEKOM_STASIUN, TELEKOM_LUAR, TELEKOM_PINTU, PERSINYALAN_ELEKTRIK (bukan semua TELEKOM).
- [x] **Semua 6 script syntax OK**, 3 JSON valid, cross-check detect_asset_type & extract_detail konsisten 100%.


### 🆕 Done (2026-07-13) - 7 Asset Types Full Support
- [x] **Sync detect_asset_type() di merge_pdf_foto.py ke 7 tipe:** CATU_DAYA, PINTU_PERLINTASAN, TELEKOMUNIKASI, PERSINYALAN_ELEKTRIK (seimbang dengan export_pdf_foto.py). Verified: return values identik.
- [x] **Sync extract_detail() di merge_pdf_foto.py:** Tambah handling detail untuk 4 tipe baru (GENSET/UPS/BATTERE, JPL/JPLE/GENTANIK, TELEPON/RADIO/OTB, BANGUNAN/DALAM PERSINYALAN).
- [x] **Sync is_valid_asset_title() di merge_pdf_foto.py:** Tambah keywords untuk 7 tipe asset (CATU DAYA, PINTU PERLINTASAN, TELEKOMUNIKASI, PERSINYALAN ELEKTRIK, JPL, GENTANIK, RADIO, SERAT OPTIK, OTB, BANGUNAN, GENSET, UPS, BATTERE, PANEL, RECTIFIER, MESIN, MOTOR, TOWER, ANTENA, INTERLOCKING, INPUT).
- [x] **ZP 41B workaround dipertahankan** di kedua extract_detail (export & merge).
- [x] **Update asset_waktu_mapping.json:** Tambah mapping lengkap untuk CATU_DAYA (23 entry), PINTU_PERLINTASAN (7 entry), TELEKOM_STASIUN/LUAR/PINTU (3 split), PERSINYALAN_ELEKTRIK (2 entry) — referensi data_acuan_tenaga_gabungan.json id 5,16,17,34-38.
- [x] **Update checklist_types.json:** Category split per folder — CATU_DAYA, PINTU_PERLINTASAN, TELEKOM_STASIUN, TELEKOM_LUAR, TELEKOM_PINTU, PERSINYALAN_ELEKTRIK (bukan semua TELEKOM).
- [x] **Semua 6 script syntax OK**, 3 JSON valid, cross-check detect_asset_type & extract_detail konsisten 100%.

### Done (Full Pipeline Batch 2025 - 165 PDF)
- [x] **Pipeline end-to-end 2025 dataset:** `export_pdf_foto.py` (1782 foto) → `extract_pdf_dates.py` (541 date.txt) → `scheduler.py` (schedule.json) → `edit_timemark_ide1.py --schedule` (1530/1530 sukses) → `merge_pdf_foto.py --schedule` (**97 PDF sukses, 15 skip, 53 gagal**).
- [x] **53 PDF gagal:** Format SERAT OPTIK, TELEKOMUNIKASI, CATU DAYA, PINTU PERLINTASAN, CTC CTS — tidak memiliki aset di halaman 1 (layout beda dari AXC/WESEL/SINYAL). Perlu parser terpisah kalau mau diproses.
- [x] **Fix Browser Freeze (`app.py`):** Limit file listing API ke 100 file + metadata total/truncated. Frontend hanya render 100 `<li>` max + info count.
- [x] **Fix EventSource Reconnect Loop:** Cegah multiple SSE connections, tambah cleanup `beforeunload`, delay reconnect 3s, error handling di `loadFiles()`.
- [x] **Simplify File Listing:** Ganti daftar file per folder menjadi tampilan "TOTAL FILE = N" saja untuk menghilangkan freeze dari render banyak DOM element.

---

## 📅 Daily Logs & Update Terakhir (Ringkasan)

> [!tip] **Untuk AI:** Baca file daily log untuk konteks detail perubahan kode, root cause, dan verifikasi. Link di bawah sudah include ringkasan 1 baris.

| Tanggal | Ringkasan Update | File Terkait | Link |
|---------|------------------|--------------|------|
| **2026-07-13** | **Station-based Folder Hierarchy (BREAKING CHANGE)**: Restructured entire pipeline to use Functional Loc → Station mapping. `export_pdf_foto.py` now outputs `station/asset_type/detail/`, all downstream scripts updated (`extract_pdf_dates.py`, `scheduler.py`, `merge_pdf_foto.py`, `edit_timemark_ide1.py`) to handle 4-level depth. Resolves duplicate asset names across stations (e.g., ZP 41 BOO di BOO vs ZP 41 BOO di CLT). SAP mapping via `sap_station_mapping.json`. All 6 scripts syntax OK. | `export_pdf_foto.py`, `extract_pdf_dates.py`, `scheduler.py`, `merge_pdf_foto.py`, `edit_timemark_ide1.py`, `sap_station_mapping.json` | [[Notes/Daily/2026-07-13-Station|📄 Detail]] |
| **2026-07-13** | **7 Asset Types Full Support**: Sync merge_pdf_foto.py detect_asset_type/extract_detail/is_valid_asset_title ke 7 tipe (AXC, WESEL, SINYAL, CATU_DAYA, PINTU_PERLINTASAN, TELEKOMUNIKASI, PERSINYALAN_ELEKTRIK). Update asset_waktu_mapping.json (35+ entry), checklist_types.json (category split TELEKOM_STASIUN/LUAR/PINTU), ZP 41B workaround kept. Audit passed: 6 scripts syntax OK, 3 JSON valid, cross-check 100% match. | merge_pdf_foto.py, asset_waktu_mapping.json, checklist_types.json, export_pdf_foto.py | [[Notes/Daily/2026-07-13|📄 Detail]] |
| **2026-07-12** | **Fix browser freeze**: Limit API `/api/files` ke 100 file + metadata total/truncated. Frontend render "TOTAL FILE = N" saja. Fix EventSource reconnect loop (cleanup beforeunload, delay 3s). | `app.py`, `templates/index.html` | [[Notes/Daily/2026-07-12\|📄 Detail]] |
| **2026-07-11** | **Bug fix Folder Consensus**: `_folder_key_from_path` mendukung input folder aset tunggal (`03_photos_export/AXC/ZP 42B BOO/`). Root cause: `relative_to(input_dir)` return nama file saja. Fix: ambil `asset_type` dari `input_dir.parent.name`, `detail` dari `input_dir.name`. Verified: ZP 42B BOO 3/3 sukses, Full AXC 402/402 sukses. | `edit_timemark_ide1.py` | [[Notes/Daily/2026-07-11\|📄 Detail]] |
| **2026-07-10** | Pipeline penuh batch 2025: 1782 foto → 1530 edit sukses → 97 PDF merged. 53 gagal (layout SERAT OPTIK, TELEKOM, CATU DAYA, dll). | `export_pdf_foto.py`, `scheduler.py`, `edit_timemark_ide1.py`, `merge_pdf_foto.py` | [[Notes/Daily/2026-07-10\|📄 Detail]] |
| **2026-07-09** | Stage 1c Red Guide Anchor: textbox di kanan guide, center sejajar atas guide. Menangani 18 foto gagal OCR (CLT + ZP 31D BOO). Total 237/237 sukses. | `edit_timemark_ide1.py` | [[Notes/Daily/2026-07-09\|📄 Detail]] |
| **2026-07-08** | Optimasi mask mepet textbox (tinggi 16px, narrow mask 5px). Stage logging transparency. Cleanup project. | `edit_timemark_ide1.py` | [[Notes/Daily/2026-07-08\|📄 Detail]] |
| **2026-07-07** | Dynamic Gap Stage 2 (Gap 0px untuk baris 1 alamat rata-kiri). Thresh 215 Stage 1. Opsi A ratio-based red detection. | `edit_timemark_ide1.py` | [[Notes/Daily/2026-07-07\|📄 Detail]] |

---

## 🏛️ Architecture Decisions (ADR)

1. **[[Notes/Decisions/ADR-001 - Pillow and Numpy instead of OpenCV|ADR-001: Penggunaan Pillow & Numpy untuk Manipulasi Watermark]]**
2. **[[Notes/Decisions/ADR-002 - PDF Image Export via pypdf and pdfplumber|ADR-002: Ekstraksi Gambar Asli PDF menggunakan pypdf]]**
3. **[[Notes/Decisions/ADR-003 - PDF Layout Parsing and Output Structure|ADR-003: Aturan Parsing Layout PDF & Struktur Output Foto]]**

---

## 🚀 Quick Commands

### CLI (Manual)
```bash
# Step 1: Export foto dari PDF 2026
python export_pdf_foto.py --input 01_pdf_source --output 03_photos_export

# Step 2: Ekstrak tanggal dari PDF 2025
python extract_pdf_dates.py --pdf-dir 02_pdf_target --output-dir 03_photos_export

# Step 3: Generate schedule.json
python scheduler.py --pdf-dir 02_pdf_target --photos-dir 03_photos_export

# Step 4: Edit timemark (pakai schedule.json)
python edit_timemark_ide1.py --input 03_photos_export --schedule schedule.json

# Step 5: Merge foto ke PDF 2025
python merge_pdf_foto.py --input 02_pdf_target --photos 04_photos_edited --output 05_pdf_merged --schedule schedule.json

# Atau jalankan semua via Web UI:
python app.py  # → buka http://localhost:5000
```

### Web UI (app.py)
- `GET /api/config` — folder paths
- `GET /api/status` — is_running, current_step, progress, status_text
- `GET /api/files` — daftar PDF di 01, 02, 05 (limit 100 + metadata total)
- `POST /api/run {"step": "all"}` — jalankan pipeline (step1..5 atau "all")
- `GET /api/stream-logs` — SSE real-time log
- `GET /api/stream-stages` — SSE real-time stage events
- `GET /api/stage-summary` — counts per stage + detail
- `GET /api/open-folder/<key>` — buka folder di Explorer
- `POST /api/stop` — hentikan proses

---

## 🔗 Quick Links

- **README.md** — Tujuan project & batasan utama
- **setup.md** — Instalasi, dependensi, cara menjalankan
- **AGENTS.md** — Complete AI context (function reference, line numbers, debugging patterns)
- **Notes/Daily/** — Daily logs lengkap (2026-07-07 s.d 2026-07-12)
- **Notes/Decisions/** — ADR-001, ADR-002, ADR-003
- **system_architecture_gabung foto ke pdf.md** — Diagram alur merge_pdf_foto.py

---

> [!tip] **Catatan untuk AI**
> File ini sudah berisi arsitektur sistem lengkap + pointer ke daily logs untuk konteks update terbaru. Jika butuh detail implementasi spesifik (nomor line, signature fungsi, edge case handling), buka `AGENTS.md` atau script `.py` terkait. Untuk memahami "kenapa" suatu perubahan dilakukan, baca daily log tanggal terkait.
