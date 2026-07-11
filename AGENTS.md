# 🤖 AGENTS.md — Complete AI Context for OCR Foto Timemark

> **TL;DR:** Baca file ini dulu sebelum menyentuh kode. File ini pengganti membaca semua `.py` satu per satu. Jika perlu detail lebih, baru buka file sumbernya.

---

## 📋 Quick References

| File | What It Does | Lines |
|------|-------------|-------|
| [README.md](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/README.md) | Tujuan project, batasan, 4-Stage detection guide | 105 |
| [setup.md](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/setup.md) | Instalasi, dependensi, cara menjalankan | 303 |
| [Dashboard.md](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/Dashboard.md) | Status tracker, checklist, daily logs | 117 |
| [system_architecture_gabung foto ke pdf.md](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/system_architecture_gabung%20foto%20ke%20pdf.md) | Diagram alur merge_pdf_foto.py | 107 |
| [Notes/Decisions/](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/Notes/Decisions/) | ADR (Architecture Decision Records) | 3 docs |
| [Notes/Test Results.md](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/Notes/Test%20Results.md) | Riwayat hasil pengujian | - |
| **[Notes/Handover/2026-07-11 - Handover to Claude.md](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/Notes/Handover/2026-07-11%20-%20Handover%20to%20Claude.md)** | **🔄 Handover task — baca ini dulu** | **state penuh** |

---

## 📁 Folder Structure (Working Directories)

```
root/
├── 01_pdf_source/          ← PDF 2026 mentah (input export_pdf_foto.py)
├── 02_pdf_target/          ← PDF 2025 target (input merge_pdf_foto.py & extract_pdf_dates.py)
├── 03_photos_export/       ← hasil ekstraksi foto dari PDF (kerja edit)
├── 04_photos_edited/       ← output foto hasil edit timemark
│   └── Tim_{n}/            ← subfolder per Tim jika pakai --schedule
├── 05_pdf_merged/          ← PDF final hasil gabung
├── backup_script_v1/       ← backup kode lama
├── logs/                   ← log CSV export & merge
├── templates/              ← HTML template untuk app.py (Flask)
├── Notes/                  ← Obsidian vault (Daily/, Decisions/, Templates/)
```

**Aturan penting:** Subfolder dipertahankan di seluruh pipeline. Jika PDF ada di `01_pdf_source/sub/`, maka outputnya akan di `03_photos_export/sub/`, dst.

---

## 📦 Dependencies

```
numpy, pillow, pdfplumber, pypdf, pymupdf (fitz), opencv-python, pytesseract, flask
```

Tesseract OCR harus terinstall di `C:\Program Files\Tesseract-OCR\tesseract.exe`.

Semua ada di [requirements.txt](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/requirements.txt):
```
pip install -r requirements.txt
```

---

## 🔄 Complete Data Flow Pipeline

```
01_pdf_source/                          02_pdf_target/
     │                                        │
     ▼                                        ▼
export_pdf_foto.py                    extract_pdf_dates.py
(ekstrak foto asli)                   (ambil tanggal dari halaman 1)
     │                                        │
     ▼                                        ▼
03_photos_export/                     date.txt per subfolder aset
     │                                        │
     └────────────┬───────────────────────────┘
                  ▼
           scheduler.py
     (mapping aset → Tim + jam)
                  │
                  ▼
           schedule.json
                  │
                  ▼
         edit_timemark_ide1.py
    (Stage 1→2→3→4 detection + draw)
                  │
                  ▼
         04_photos_edited/
         ┌── Tim_1/  ...
         │
         ▼ (dengan --schedule)
       merge_pdf_foto.py
   (gabung foto baru → PDF)
                  │
                  ▼
          05_pdf_merged/
```

---

## 🐍 Python Script Reference

### 1. [export_pdf_foto.py](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/export_pdf_foto.py) — Ekstraksi Foto dari PDF
**Input:** `01_pdf_source/*.pdf`  
**Output:** `03_photos_export/{AXC|WESEL|SINYAL}/{detail_aset}/0.jpg, 50.jpg, 100.jpg`

```
python export_pdf_foto.py [--input 01_pdf_source] [--output 03_photos_export]
```

**Key functions:**
| Function | Line | Purpose |
|----------|------|---------|
| `AssetRow` dataclass | 19-27 | Struct: page_number, code, title, asset_type, detail, top |
| `detect_asset_type(code, title)` | 92-100 | Klasifikasi: AXL→AXC, WSL→WESEL, SIN→SINYAL |
| `extract_detail(title, asset_type)` | 103-126 | Parsing nama detail aset dari title (e.g. "ZP 22A CLT") |
| `extract_asset_rows(page)` | 129-166 | Cari baris aset di halaman PDF via pdfplumber word extraction |
| `original_images_by_name(reader, page_index)` | 179-184 | Ambil image object asli dari pypdf |
| `export_pdf(pdf_path, ...)` | 191-284 | **Core:** loop halaman→aset→3 foto, export via pypdf original images |
| `asset_output_dir(root, asset_type, detail)` | 187-188 | Path: `root/ASSET_TYPE/sanitized_detail/` |
| `sanitize_segment(text)` | 84-89 | Bersihkan nama folder (hapus karakter ilegal) |

**Workaround spesial:** `ZP 41B BOO` → `ZP 41 BOO` (line 124-125, typo di PDF asli)

---

### 2. [extract_pdf_dates.py](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/extract_pdf_dates.py) — Ekstraksi Tanggal dari PDF Target
**Input:** `02_pdf_target/*.pdf`  
**Output:** `date.txt` di setiap subfolder `03_photos_export/.../`

```
python extract_pdf_dates.py [--pdf-dir 02_pdf_target] [--output-dir 03_photos_export]
```

**Key functions:**
| Function | Line | Purpose |
|----------|------|---------|
| `parse_date_indonesian(text)` | 38-80 | Regex 3 pola: DD Bulan YYYY, YYYY-MM-DD, DD-MM-YYYY |
| `format_date_target(dt)` | 83-86 | `"Senin, Jan 06 2025"` (format target) |
| `extract_date_from_pdf(pdf_path)` | 89-112 | Baca halaman 1 pdfplumber → parse date |
| `main()` | 115-194 | Loop PDF → extract date → tulis `date.txt` per folder aset |
| `INDONESIAN_DAYS` | 16 | `["Senin", "Selasa", ..., "Minggu"]` |
| `INDONESIAN_MONTHS` | 17-20 | `{1: "Jan", 2: "Feb", ...}` **singkat** |
| `MONTH_MAP` | 22-35 | Nama bulan lengkap+singkat → angka |

**⚠️ Catatan:** `format_date_target` pakai bulan **singkat** (Jan, Feb, dst). `extract_date_from_page1` di merge_pdf_foto pakai bulan **panjang** (Januari, Februari). Ini disengaja — format singkat untuk watermark, format panjang untuk header halaman PDF.

**Dependency:** Import `extract_asset_rows`, `asset_output_dir`, `ensure_dir` dari `export_pdf_foto.py`.

---

### 3. [scheduler.py](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/scheduler.py) — Penjadwalan Tim & Waktu
**Input:** `02_pdf_target/*.pdf` + `asset_waktu_mapping.json` + `data_acuan_tenaga_gabungan.json`  
**Output:** `schedule.json`

```
python scheduler.py [--pdf-dir 02_pdf_target] [--photos-dir 03_photos_export]
                    [--mapping asset_waktu_mapping.json]
                    [--data-acuan data_acuan_tenaga_gabungan.json]
                    [--jam-mulai 7] [--jam-selesai 18] [--tim-max 2]
                    [--output schedule.json]
```

**Key functions:**
| Function | Line | Purpose |
|----------|------|---------|
| `load_mapping(path)` | 61-72 | asset_waktu_mapping.json → dict `{(type,detail): asset_id}` |
| `load_data_acuan(path)` | 75-78 | data_acuan_tenaga_gabungan.json → dict `{id: {waktu_menit, ...}}` |
| `get_waktu(asset_type, detail, mapping, acuan)` | 81-87 | Lookup waktu pengerjaan aset (default: AXC/WESEL=45, SINYAL=30) |
| `build_schedule(...)` | 109-203 | **Core:** urutkan PDF → hitung jam per aset → rotasi Tim 1/2 → overflow rule |
| `_parse_date(text)` | 31-58 | Parse "Rabu, Jul 08 2026" → date object |

**Overflow rule:** Aset yang mulai < 18:00 tetap selesai 3 fotonya. File berikutnya pindah Tim/reset jam. Jika Tim > tim_max, reset ke Tim 1 dan geser ke hari berikutnya.

**schedule.json format:**
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
          "type": "AXC", "detail": "ZP 60 BOO", "code": "AXL11468",
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

---

### 4. [edit_timemark_ide1.py](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/edit_timemark_ide1.py) — Script Utama Edit Watermark (922 lines)
**Input:** `03_photos_export/` (atau folder spesifik)  
**Output:** `04_photos_edited/` (dengan struktur dipertahankan)

```
# Opsi A: Manual
python edit_timemark_ide1.py  # prompt interaktif

# Opsi B: CLI
python edit_timemark_ide1.py --input 03_photos_export --date "Sabtu, Apr 29 2026"

# Opsi C: Dengan schedule (timestamp per-foto + Tim subfolder)
python edit_timemark_ide1.py --input 03_photos_export --schedule schedule.json

# Opsi D: Override Y manual
python edit_timemark_ide1.py --input folder --date "..." --y-override 195

# Opsi E: Folder spesifik
python edit_timemark_ide1.py --input "03_photos_export/WESEL/ZP 22A CLT"
```

#### 🔬 Core Detection Functions

| Function | Line | Purpose |
|----------|------|---------|
| `find_red_guide(arr)` | 144-181 | Deteksi garis merah vertikal (GPS Map Camera) di kiri bawah. Filter: r>145, r>g×1.3, r>b×1.3. Cari di kolom kiri (x<16%) dan y>54%. Return (x1,y1,x2,y2) atau None. |
| `determine_template(image_path, arr)` | 184-213 | Tentukan template 1 (WESEL) atau 2 (AXC/SINYAL) berdasarkan path atau Red Guide position. |
| `detect_date_y_center(arr, h, w)` | 216-326 | **Stage 1 core:** OCR Tesseract `--psm 6` di crop kiri bawah. Cari tahun 20xx, nama bulan, AM/PM/WIB. Multi-threshold binning (180, 160, 200, 215, adaptive). Confidence filter per tipe kata. Return rata-rata Y-center. |
| `detect_address_y_top(arr, h, w)` | 329-379 | **Stage 2 core:** OCR Tesseract `--psm 4` di crop kiri bawah. Deteksi baris teks alamat, prioritaskan rata-kiri (left<30). Return Y-top baris alamat pertama. |
| `locate_date_box(arr, image_path, ...)` | 434-532 | **Main router:** Stage 1→1b→2→3→4 decision tree. Menerima folder_address_consensus dan folder_date_consensus. |
| `diffuse_fill_region(arr, mask, steps)` | 537-552 | Inpainting berbasis difusi 120 iterasi. |
| `process_image(image_path, output_path, ...)` | 661-727 | **Entry point per gambar:** buka→detect→erase→draw→save. |
| `iso_to_timemark(iso_str)` | 26-31 | `"2026-07-11T09:30:00"` → `"Rabu, Jul 11 2026 09:30"` |

#### 📊 4-Stage Priority System (locate_date_box)

```
STAGE 0 (--y-override): Paksa posisi manual
    │
    ▼ (tanpa override)
STAGE 1 (Tanggal Lokal): detect_date_y_center → OCR sukses + validasi Red Guide
    │ gagal
    ▼
STAGE 1b (Konsensus Tanggal Folder): 2+ file di folder sama setuju Y-tanggal
    │ gagal
    ▼
STAGE 2 (Alamat Konsensus): folder_address_consensus → hitung gap → textbox di atas alamat
    │ gagal
    ▼
STAGE 3 (Red Guide Lokal): find_red_guide → sejajarkan textbox dengan guide
    │ gagal
    ▼
STAGE 4 (SKIP): tidak diproses, masuk list warning
```

#### 🗳️ Folder-Level Consensus Voting (main function, lines 764-814)

Sebelum memproses gambar, script melakukan **pre-scan seluruh folder**:
- **Alamat consensus:** minimal 2 file punya `detect_address_y_top` yang kluster dalam 10px → rata-rata disimpan
- **Tanggal consensus:** minimal 2 file punya `detect_date_y_center` yang kluster dalam 10px → rata-rata disimpan
- Hasil voting dipakai sebagai fallback (Stage 1b & Stage 2) untuk file yang OCR-nya gagal

#### 🗓️ Schedule Mode (--schedule)

- Baca `schedule.json` → lookup `(asset_type, detail, photo_name)` → dapat `(iso_timestamp, tim_n)`
- Output ke `04_photos_edited/Tim_{tim_n}/...` (bukan root `04_photos_edited/`)
- Tanggal per foto dari schedule (bukan dari `date.txt` atau `global_date_text`)

#### 🎨 Drawing Details

- Font: Arial/Calibri/DejaVu (auto-detect), size = `int(w * 0.038)`
- Textbox: rounded rectangle hitam transparan (alpha 140), shadow + stroke
- Erase: `diffuse_fill_region` 60 steps, mask 2px padding, radius rounded
- Box height: `int(h * 0.053)` (16px untuk h=300)
- Narrow mask: 5px extra ke atas (bukan 14px)

---

### 5. [merge_pdf_foto.py](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/merge_pdf_foto.py) — Gabung Foto Baru ke PDF Lama
**Input:** `02_pdf_target/*.pdf` + `04_photos_edited/...`  
**Output:** `05_pdf_merged/*.pdf`

```
python merge_pdf_foto.py [--input 02_pdf_target] [--photos 04_photos_edited]
                         [--output 05_pdf_merged] [--schedule schedule.json]
```

**Key functions:**
| Function | Line | Purpose |
|----------|------|---------|
| `extract_location_from_filename(filename)` | 152-159 | Parse nama file PDF → nama lokasi (e.g. "CILEBUT-BOGOR") |
| `extract_date_from_page1(page)` | 161-177 | Cari "Tanggal : YYYY-MM-DD" di halaman 1 |
| `extract_checklist_title(page, filename)` | 179-191 | Cari baris mengandung "PERAWATAN" |
| `draw_header(page, location, date_str, checklist_title)` | 207-210 | Gambar header halaman A4 baru |
| `process_pdf(...)` | 212-316 | **Core:** buka pdfplumber→parse assets→verifikasi 3 foto→buka fitz→hapus halaman terakhir→buat halaman baru dengan 4 aset/halaman |
| `draw_centered_label(...)` | 201-205 | Label "Foto 0%", "Foto 50%", "Foto 100%" di bawah gambar |

**Layout constants:**
- Halaman A4: 595×842 pt
- Gambar: 148.8×148.8 pt, kolom di X=31.5, 210.4, 389.8
- Maksimal 4 aset per halaman
- **Proteksi:** jika ada 1 aset yang kekurangan foto → seluruh PDF di-skip

**Schedule mode (--schedule):** Cari foto di `04_photos_edited/Tim_{n}/...` (bukan root `04_photos_edited/`)

---

### 6. [app.py](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/app.py) — Flask Web Dashboard
**Port:** 5000  
**Entry:** `python app.py` → auto-buka browser ke `http://localhost:5000`

**5-stage pipeline via Web UI:**
| Step | Key | Script | Progress |
|------|-----|--------|----------|
| Step 1 | `step1` | export_pdf_foto.py | 10-25% |
| Step 2 | `step2` | extract_pdf_dates.py | 30-45% |
| Step 3 | `step3` | scheduler.py | 50-60% |
| Step 4 | `step4` | edit_timemark_ide1.py | 65-80% |
| Step 5 | `step5` | merge_pdf_foto.py | 85-100% |
| All | `all` | Semua berurutan | 0-100% |

**API Endpoints:**
- `GET /api/config` — folder paths
- `GET /api/status` — is_running, current_step, progress, status_text
- `GET /api/files` — daftar PDF di 01, 02, 05
- `POST /api/run {"step": "all"}` — jalankan pipeline
- `GET /api/stream-logs` — SSE real-time log
- `GET /api/open-folder/<key>` — buka folder di Explorer

**Global state:** `state` dict + `log_queue` (thread-safe dengan `log_lock`)

---

## 📚 Domain Glossary

| Istilah | Arti |
|---------|------|
| **Timemark** | Watermark GPS Map Camera di foto dokumentasi (pojok kiri bawah) |
| **Red Guide** | Garis oren/merah vertikal asli dari GPS Map Camera, digunakan sebagai anchor posisi |
| **Stage 1-4** | Sistem prioritas deteksi posisi textbox (lihat diagram di atas) |
| **AXC** | Axle Counter — kode aset prefix AXL (e.g. AXL11468) |
| **WESEL** | Wesel — kode aset prefix WSL (e.g. WSL11080) |
| **SINYAL** | Sinyal — kode aset prefix SIN |
| **0%, 50%, 100%** | Tiga foto dokumentasi per aset: awal (0%), tengah (50%), akhir (100%) |
| **PDF 2025 vs 2026** | Format lama (2025) = foto kolase di halaman terakhir. Format baru (2026) = foto hasil edit disusun ulang |
| **date.txt** | File metadata di folder aset berisi tanggal target dalam format "Rabu, Jul 08 2026" |
| **schedule.json** | File penjadwalan: mapping aset→Tim→timestamp ISO per foto |
| **Konsensus Folder** | Pre-scan folder: 2+ file setuju Y dalam 10px → apply ke semua file |
| **Overflow Rule** | Aset yang mulai < jam_selesai tetap selesai. File berikutnya → Tim berikutnya |
| **Waktu Menit** | Durasi pengerjaan per aset (default: AXC/WESEL=45, SINYAL=30) |
| **ZP 41B fix** | Typo di PDF 2025: ZP 41B BOO seharusnya ZP 41 BOO |
| **diffuse_fill_region** | Inpainting berbasis difusi untuk menghapus teks tanggal lama |

---

## 🚨 Critical Rules (Dari AGENTS.md Asli)

1. **Read Before Working:** Baca file ini + [Dashboard.md](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/Dashboard.md) sebelum edit/propose.
2. **Update After Working:** Update [Dashboard.md](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/Dashboard.md) jika status task berubah.
3. **Daily Logs:** Jika hari baru, buat log di [Notes/Daily/](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/Notes/Daily/) pakai template.
4. **Debug & Fix Rule (CRITICAL):** Jika user minta "debug ocr dan stage nya": **HANYA tampilkan hasil pembacaan OCR + jelaskan stage yang terpilih. JANGAN langsung fix/edit kode sebelum konfirmasi user!**
5. **Auto-Update Obsidian & GitHub (PERMANENT AGENT INSTRUCTION):** **SETIAP kali ada update kode/script/config, WAJIB otomatis (tanpa perlu diminta user):**
   - Update `Dashboard.md` (status tracker, checklist, daily logs)
   - Buat/append `Notes/Daily/YYYY-MM-DD.md` dengan ringkasan perubahan
   - `git add . && git commit -m "<type>: <subject>" && git push`
   - **Conventional Commits format:** `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, `style:`
   - Subject ≤ 50 chars, body only when "why" isn't obvious
5. **Auto-Update Obsidian & GitHub (PERMANENT AGENT INSTRUCTION):** **SETIAP kali ada update kode/script/config, WAJIB otomatis (tanpa perlu diminta user):**
   - Update `Dashboard.md` (status tracker, checklist, daily logs)
   - Buat/append `Notes/Daily/YYYY-MM-DD.md` dengan ringkasan perubahan
   - `git add . && git commit -m "<type>: <subject>" && git push`
   - **Conventional Commits format:** `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, `style:`
   - Subject ≤ 50 chars, body only when "why" isn't obvious

---

## 🧪 Common Debugging Patterns

### Debug Stage Detection
```bash
python edit_timemark_ide1.py --input "03_photos_export/AXC/ZP 60 BOO"
# Output akan menunjukkan STAGE 1/2/3/4 per file
```

### Force Manual Y Position
```bash
python edit_timemark_ide1.py --input "folder" --date "..." --y-override 195
```

### Run Specific Step Only
```bash
# Via Web UI: POST /api/run {"step": "step4"}
# Via CLI: jalankan script individual
```

### Check schedule.json
```bash
python scheduler.py --pdf-dir 02_pdf_target --photos-dir 03_photos_export
```

---

## 🔑 Key Architectural Decisions (ADR)

Lihat [Notes/Decisions/](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/Notes/Decisions/) untuk detail:
1. **ADR-001:** Pakai Pillow + Numpy, bukan OpenCV
2. **ADR-002:** Ekstraksi gambar PDF via pypdf (original images)
3. **ADR-003:** Aturan parsing layout PDF & struktur output

**Experimen yang gagal (jangan diulang):**
- PaddleOCR → gagal (oneDNN bug di Windows)
- EasyOCR preprocessing → tidak membantu (gak fokus 1 baris)
- **Tesseract `--psm 7` tetap terbaik** untuk deteksi watermark

---

## ⚙️ Environment Setup

```bash
# 1. Virtual env
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Dependencies
pip install -r requirements.txt

# 3. Tesseract OCR harus terinstall di:
# C:\Program Files\Tesseract-OCR\tesseract.exe

# 4. Run
python app.py  # Web UI
```
