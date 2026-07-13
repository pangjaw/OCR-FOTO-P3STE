# 🤖 AGENTS.md — Complete AI Context for OCR Foto Timemark

> **TL;DR:** Baca file ini dulu sebelum menyentuh kode. File ini pengganti membaca semua `.py` satu per satu. Jika perlu detail lebih, baru buka file sumbernya.

---

## 📋 Quick References

| File | What It Does | Lines |
|------|-------------|-------|
| [README.md](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/README.md) | Tujuan project, batasan, single-stage guide-based detection | 105 |
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
│   └── {station}/          ← Subfolder per Station (BOO, CLT, BOP, BTT, MSG, CGB, BJD, CCR, COS, CS, BNR, dst)
│       └── {asset_type}/   ← Subfolder per tipe aset (AXC, WESEL, SINYAL, CATU_DAYA, PINTU_PERLINTASAN, TELEKOMUNIKASI, PERSINYALAN_ELEKTRIK)
│           └── {detail_aset}/  ← Subfolder per detail aset
│               ├── 0.jpg
│               ├── 50.jpg
│               ├── 100.jpg
│               └── date.txt    ← Dari extract_pdf_dates.py
├── 04_photos_edited/       ← output foto hasil edit timemark
│   └── Tim_{n}/            ← subfolder per Tim jika pakai --schedule
│       └── {station}/
│           └── {asset_type}/
│               └── {detail_aset}/
│                   ├── 0.jpg
│                   ├── 50.jpg
│                   └── 100.jpg
├── 05_pdf_merged/          ← PDF final hasil gabung
├── backup_script_v1/       ← backup kode lama
├── logs/                   ← log CSV export & merge
├── templates/              ← HTML template untuk app.py (Flask)
└── Notes/                  ← Obsidian vault (Daily/, Decisions/, Templates/)
```

**Aturan penting:** Subfolder dipertahankan di seluruh pipeline. Hierarchy baru: `station/asset_type/detail`. Jika PDF ada di `01_pdf_source/sub/`, maka outputnya akan di `03_photos_export/sub/`, dst.

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
     (HSV Orange Isolation + Fixed-offset Guide + Folder Consensus)
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
**Output:** `03_photos_export/{station}/{asset_type}/{detail_aset}/0.jpg, 50.jpg, 100.jpg`

```
python export_pdf_foto.py [--input 01_pdf_source] [--output 03_photos_export]
```

**Key functions:**
| Function | Line | Purpose |
|----------|------|---------|
| `AssetRow` dataclass | 19-27 | Struct: page_number, code, title, asset_type, detail, top, station |
| `detect_asset_type(code, title)` | 92-100 | Klasifikasi: AXL→AXC, WSL→WESEL, SIN→SINYAL, CDA→CATU_DAYA, JPL→PINTU_PERLINTASAN, TLK/TWR→TELEKOMUNIKASI, TRA/INB→PERSINYALAN_ELEKTRIK |
| `extract_detail(title, asset_type)` | 103-126 | Parsing nama detail aset dari title (e.g. "ZP 22A CLT") |
| `extract_asset_rows(page, sap_mapping)` | 129-166 | Cari baris aset di halaman PDF via pdfplumber word extraction |
| `original_images_by_name(reader, page_index)` | 179-184 | Ambil image object asli dari pypdf |
| `export_pdf(pdf_path, ..., sap_mapping)` | 191-284 | **Core:** loop halaman→aset→3 foto, export via pypdf original images |
| `asset_output_dir(root, station, asset_type, detail)` | 187-188 | Path: `root/station/asset_type/sanitized_detail/` |
| `sanitize_segment(text)` | 84-89 | Bersihkan nama folder (hapus karakter ilegal) |

**Workaround spesial:** `ZP 41B BOO` → `ZP 41 BOO` (line 124-125, typo di PDF asli)

---

### 2. [extract_pdf_dates.py](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/extract_pdf_dates.py) — Ekstraksi Tanggal dari PDF Target
**Input:** `02_pdf_target/*.pdf`  
**Output:** `date.txt` di setiap subfolder `03_photos_export/{station}/{asset_type}/{detail_aset}/`

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

**Dependency:** Import `extract_asset_rows`, `asset_output_dir`, `ensure_dir` dari `export_pdf_foto.py`. Updated signature: `asset_output_dir(root, station, asset_type, detail)`.

---

### 3. [scheduler.py](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/scheduler.py) — Penjadwalan Tim & Waktu
**Input:** `02_pdf_target/*.pdf` + `asset_waktu_mapping.json` + `data_acuan_tenaga_gabungan.json` + `sap_station_mapping.json`  
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
| `load_data_acuan(path)` | 75-78 | data_acuan_tenaga_gabungan.json → dict `{id: {waktu_menit, ...}} |
| `load_sap_mapping(path)` | 80-85 | sap_station_mapping.json → dict `{(type,detail): station}` |
| `get_waktu(asset_type, detail, mapping, acuan)` | 81-87 | Lookup waktu pengerjaan aset (default: AXC/WESEL=45, SINYAL=30, CATU_DAYA=45, PINTU_PERLINTASAN=45, TELEKOM=60-120, PERSINYALAN=420) |
| `build_schedule(..., sap_mapping)` | 109-203 | **Core:** urutkan PDF → hitung jam per aset → rotasi Tim 1/2 → overflow rule. Now loads `sap_mapping` and passes station to `extract_asset_rows` |
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

### 4. [edit_timemark_ide1.py](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/edit_timemark_ide1.py) — Script Utama Edit Watermark
**Input:** `03_photos_export/{station}/{asset_type}/{detail_aset}/` (atau folder spesifik)  
**Output:** `04_photos_edited/Tim_{n}/{station}/{asset_type}/{detail_aset}/` (jika --schedule) atau `04_photos_edited/{station}/{asset_type}/{detail_aset}/`

**Key features:**
- **HSV Isolation:** Isolasi warna oranye untuk deteksi Red Guide yang akurat.
- **Fixed-offset Detection:** Penempatan textbox berdasarkan offset tetap dari posisi Red Guide.
- **Folder Consensus:** Pre-scan folder untuk menentukan posisi Y watermark yang konsisten (median gy1) untuk seluruh aset dalam folder tersebut jika guide individu sulit dideteksi. **Kunci konsensus: (station, asset_type, detail) — 3-level folder.**
- **Diffuse Fill:** Inpainting (60 iterasi) untuk menghapus watermark tanggal lama dengan mulus.

**CLI Options:**
```
--input PATH        Folder foto input (default: 03_photos_export)
--output PATH       Folder output (default: 04_photos_edited)
--date TEXT         Tanggal manual (e.g. 'Sabtu, Apr 29 2026 08:00')
--schedule PATH     schedule.json untuk per-photo timestamps
--y-override INT    Paksa posisi Y textbox
--clear-output      Hapus folder output sebelum mulai
```

**Stage Priority:** `y_override` → `find_red_guide` (original) → folder consensus gy1 → `get_text_box()` (fallback)

**Stage Codes:** `stage_0_override`, `stage_1c_guide_original`, `stage_1c_guide_consensus`, `stage_fallback`

**Output Files:** `logs/edit_stages.xlsx` (detail per foto), `logs/edit_failed.xlsx` (foto gagal), JSON `__SUMMARY__` (dibaca app.py)

**SSE Logging:** Setiap foto emit JSON `{"type":"stage","file":"...","stage":"..."}` → dibaca `app.py` untuk dashboard real-time

---

### 5. [merge_pdf_foto.py](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/merge_pdf_foto.py) — Gabung Foto Baru ke PDF Lama
**Input:** `02_pdf_target/*.pdf` + `04_photos_edited/...` (struktur `Tim_{n}/{station}/{asset_type}/{detail_aset}/`)  
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
| `process_pdf(...)` | 212-316 | **Core:** buka pdfplumber→parse assets→verifikasi 3 foto→buka fitz→hapus halaman terakhir→buat halaman baru dengan 4 aset/halaman. **Navigasi folder pakai station/asset_type/detail sesuai export_pdf_foto** |
| `draw_centered_label(...)` | 201-205 | Label "Foto 0%", "Foto 50%", "Foto 100%" di bawah gambar |

---

### 6. [app.py](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/app.py) — Flask Web Dashboard

**Fungsi Utama:** Menyediakan UI berbasis web untuk menjalankan pipeline 5-tahap dengan monitoring SSE real-time.

**API Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Render dashboard HTML |
| `/api/config` | GET | Folder paths (01-05), schedule path |
| `/api/status` | GET | `is_running`, `current_step`, `progress`, `status_text` |
| `/api/files` | GET | Daftar PDF di 01, 02, 05 (limit 100, return `total`+`truncated`) |
| `/api/run` | POST | Jalankan pipeline. Body: `{"step":"all|step1|...", "overwrite":"1|0"}` |
| `/api/stop` | POST | Kill proses pipeline (`process.kill()`) |
| `/api/stream-logs` | GET | SSE real-time stdout log |
| `/api/stream-stages` | GET | SSE real-time stage events dari edit_timemark |
| `/api/stage-summary` | GET | `stage_counts` + `stage_details` (setelah step4) |
| `/api/step-summary` | GET | Summary per step: success/failed/skipped |
| `/api/open-folder/<key>` | GET | Buka folder di Explorer (`os.startfile`) |

**Global state:** `state` dict + `log_queue`/`stage_queue`/`stage_counts`/`stage_details` (thread-safe dengan `threading.Lock`). `step_summaries` di-populate dari `__SUMMARY__:...` output script. `run_command_stream()` spawn subprocess + stream stdout + parse JSON stage events.

**Overwrite/Skip:** Toggle di frontend (`templates/index.html`) diteruskan sebagai `overwrite` parameter ke `/api/run`. Semua 5 script membaca `os.environ.get("OVERWRITE", "1")`. `"0"` = skip, `"1"` = timpa.

---

## 📚 Domain Glossary

| Istilah | Arti |
|---------|------|
| **Timemark** | Watermark GPS Map Camera di foto dokumentasi (pojok kiri bawah) |
| **Red Guide** | Garis oren/merah vertikal asli dari GPS Map Camera, digunakan sebagai anchor posisi |
| **Stage 1c** | Single-stage fixed-offset detection: Red Guide → textbox sejajar guide |
| **AXC** | Axle Counter — kode aset prefix AXL |
| **WESEL** | Wesel — kode aset prefix WSL |
| **SINYAL** | Sinyal — kode aset prefix SIN |
| **0%, 50%, 100%** | Tiga foto dokumentasi per aset: awal (0%), tengah (50%), akhir (100%) |
| **PDF 2025 vs 2026** | Format lama (2025) = foto kolase di halaman terakhir. Format baru (2026) = foto hasil edit disusun ulang |
| **date.txt** | File metadata di folder aset berisi tanggal target dalam format "Rabu, Jul 08 2026" |
| **schedule.json** | File penjadwalan: mapping aset→Tim→timestamp ISO per foto |
| **Konsensus Folder** | Pre-scan folder: 2+ file punya Red Guide dengan **gy1** kluster dalam 10px → median gy1 dipakai untuk semua file di folder |
| **diffuse_fill** | Inpainting berbasis difusi (4-arah neighbor averaging, 60 iterasi) untuk menghapus watermark lama |
| **Waktu Menit** | Durasi pengerjaan per aset (default: AXC/WESEL=45, SINYAL=30) |
| **ZP 41B fix** | Typo di PDF 2025: ZP 41B BOO seharusnya ZP 41 BOO |

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

---

## 🧪 Common Debugging Patterns

### Debug Stage Detection
```bash
python edit_timemark_ide1.py --input "03_photos_export/AXC/ZP 60 BOO"
# Output akan menunjukkan stage_1c_guide_original / stage_1c_guide_consensus / stage_fallback per file
```

### View Stage Summary (via API)
```bash
curl http://localhost:5000/api/stage-summary
# Returns: {"stage_counts": {"stage_1c_guide_original": N, ...}, "stage_details": [...]}
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

### Debug HSV Isolation
```bash
python -c "from edit_timemark_ide1 import preprocess_for_guide; from PIL import Image; img=Image.open('test.jpg'); out=preprocess_for_guide(img); Image.fromarray(out).save('debug_hsv.jpg')"
# Visualisasi: semua warna grayscale, kecuali pure red yang tetap merah"

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
