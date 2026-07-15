# 🤖 AGENTS.md — AI Context for OCR Foto Timemark

> Baca ini sebelum edit kode. Pengganti baca semua `.py` satu per satu.

## Quick References
| File | What It Does |
|------|-------------|
| [README.md](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/README.md) | Tujuan project, batasan |
| [setup.md](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/setup.md) | Instalasi, cara menjalankan |
| [Dashboard.md](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/Dashboard.md) | Status tracker, daily logs |
| [Notes/Decisions/](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/Notes/Decisions/) | ADR |
| [Notes/Test Results.md](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/Notes/Test%20Results.md) | Riwayat pengujian |

## Folder Structure
```
root/
├── 01_pdf_source/          ← PDF 2026 mentah
├── 02_pdf_target/          ← PDF 2025 target
├── 03_photos_export/       ← hasil ekstraksi foto
│   └── {station}/{asset_type}/{detail_aset}/{0,50,100.jpg, date.txt}
├── 04_photos_edited/       ← hasil edit timemark
│   └── Tim_{n}/{station}/{asset_type}/{detail_aset}/{0,50,100.jpg}
├── 05_pdf_merged/          ← PDF final
├── logs/
├── templates/              ← HTML untuk app.py (Flask)
└── Notes/                  ← Obsidian vault
```

## Data Flow
```
01_pdf_source/          02_pdf_target/
     │                        │
     ▼                        ▼
export_pdf_foto.py     extract_pdf_dates.py
(step 1, ekstrak foto) (step 2, ambil tanggal hlm 1)
     │                        │
     └──────────┬─────────────┘
                ▼
         scheduler.py (step 3)
         → schedule.json
                │
                ▼
         edit_timemark_ide1.py (step 4)
         → 04_photos_edited/Tim_{n}/...
                │
                ▼
         merge_pdf_foto.py (step 5)
         → 05_pdf_merged/
```

## Python Script Reference

### 1. [export_pdf_foto.py](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/export_pdf_foto.py) — Ekstraksi Foto
**Input:** `01_pdf_source/*.pdf` → **Output:** `03_photos_export/{station}/{asset_type}/{detail}/`

| Function | Line | Purpose |
|----------|------|---------|
| `AssetRow` dataclass | 19-27 | Struct: page_number, code, title, asset_type, detail, top, station |
| `detect_asset_type(code, title)` | 92-100 | AXL→AXC, WSL→WESEL, SIN→SINYAL, CDA→CATU_DAYA, JPL→PINTU_PERLINTASAN, TLK/TWR/OTB→TELEKOMUNIKASI, **INB→PDSE, TRA→PDSE/SERAT OPTIK/PTLS** |
| `detect_category_from_filename(name)` | 159-210 | Detect WESEL/SINYAL/AXC/PDSE/CTS/PTLS/CATUDAYA/SERAT OPTIK/PTPP/JPL. "SINYAL" but NOT "PERSINYALAN". **RADIO BASESTATION/WAYSTATION/SISTEM WAYSTATION→PTLS** |
| `extract_detail(title, asset_type)` | 103-126 | Parse nama detail aset (e.g. "ZP 22A CLT") |
| `extract_asset_rows(page, sap_mapping)` | 129-166 | Cari baris aset di halaman PDF via pdfplumber word extraction |
| `extract_all_funclocs(page_text)` | ~550 | Ekstrak SEMUA funcloc dari halaman (regex: (SIN|WSL|AXL|OTB|OTG|TEK|TRA|TLK|TWR|PDSE|PTDS|PTLS|JPL|PTPP|CTS|CATUDAYA)\\d+...) |
| `extract_identifier(funcloc_text, category)` | 503-610 | Extract folder identifier. Auto-detect category from funcloc prefix. WESEL: "W23A BOO", AXC: "ZP 201B MSG", SINYAL: "J10 BOO"/"JL42A BOO", **JPL: named JPL ("JPL BNR BOP-BTT") + numbered ("JPL 28 BOO-CLT")** |
| `extract_station_from_description(desc, sap_mapping, funcloc)` | 189-228 | Extrak station code dari desc/FLoc. Priority: SAP mapping → exact code → dash-split → name map. `CODE_ALIASES = {"CS": "COS"}` |
| `original_images_by_name(reader, page_index)` | 179-184 | Ambil image object asli dari pypdf |
| `export_multi_row(pdf, reader, ...)` | **644-790** | **NEW**: Multi-row export (WESEL/SINYAL/AXC). Ekstrak words→cari funcloc positions→group images by top clustering→map ke funcloc terdekat→export 3 foto per row |
| `export_pdf(pdf_path, ..., sap_mapping)` | 795- | Core: detect category→read funclocs→delegasi ke `export_multi_row()` jika multi-row→else standard 3-foto export |
| `asset_output_dir(root, station, asset_type, detail)` | 187-188 | Path: `root/station/asset_type/sanitized_detail/` |
| `sanitize_segment(text)` | 84-89 | Bersihkan nama folder |
| `load_sap_mapping(path)` | 109-116 | Baca JSON → dict `{funcloc: station_string}` |

**ZP 41B workaround:** line 124-125 — typo di PDF asli `ZP 41B BOO` → `ZP 41 BOO`

---

### 2. [extract_pdf_dates.py](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/extract_pdf_dates.py) — Ekstraksi Tanggal
**Input:** `02_pdf_target/*.pdf` → **Output:** `date.txt` per folder aset

| Function | Line | Purpose |
|----------|------|---------|
| `parse_date_indonesian(text)` | 38-80 | Regex 3 pola: DD Bulan YYYY, YYYY-MM-DD, DD-MM-YYYY |
| `format_date_target(dt)` | 83-86 | `"Senin, Jan 06 2025"` (format singkat untuk watermark) |
| `extract_date_from_pdf(pdf_path)` | 89-112 | Baca halaman 1 pdfplumber → parse date |
| `main()` | 115-274 | Loop PDF → extract date → tulis `date.txt` per folder |

**KEL1 vs KEL2 date writing:**
- **KEL1** (WESEL, SINYAL, AXC): Uses `extract_all_funclocs()` → writes `date.txt` per funcloc folder
- **KEL2** (lainnya): Uses first funcloc → writes 1 `date.txt` per folder

**Catatan:** `format_date_target` pakai bulan **singkat** (Jan, Feb). `merge_pdf_foto.py` pakai bulan **panjang** (Januari) — disengaja.

---

### 3. [scheduler.py](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/scheduler.py) — Penjadwalan Tim
**Input:** `02_pdf_target/*.pdf` + 3 JSON mapping → **Output:** `schedule.json`

| Function | Line | Purpose |
|----------|------|---------|
| `load_mapping(path)` | 61-72 | `asset_waktu_mapping.json` → dict |
| `load_data_acuan(path)` | 75-78 | `data_acuan_tenaga_gabungan.json` → dict |
| `load_sap_mapping(path)` | 80-85 | `sap_station_mapping.json` → dict `{funcloc: station}` |
| `get_waktu(asset_type, detail, mapping, acuan)` | 81-87 | Lookup waktu. Default: AXC/WESEL=45, SINYAL=30, CATU_DAYA=45, PINTU_PERLINTASAN=45, TELEKOM=60-120, PERSINYALAN=420 |
| `build_schedule(...)` | 109-203 | Core: KEL1/KEL2 grouping + multi-funcloc scheduling |
| `_parse_date(text)` | 31-58 | Parse "Rabu, Jul 08 2026" → date object |

**KEL1 vs KEL2:**
- **KEL1** (WESEL, SINYAL, AXC): 1 schedule entry per funcloc. Foto per funcloc = 3 (0/50/100). Uses `extract_all_funclocs()`.
- **KEL2** (lainnya): 1 schedule entry per identifier. 3 foto regardless of funcloc count.

**Overflow rule:** Aset mulai < 18:00 tetap selesai. File berikutnya pindah Tim/reset jam. Tim > max → reset ke Tim 1, geser hari.

---

### 4. [edit_timemark_ide1.py](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/edit_timemark_ide1.py) — Edit Watermark (Core)
**Input:** `03_photos_export/...` → **Output:** `04_photos_edited/...`

| Feature | Detail |
|---------|--------|
| HSV Isolation | Grayscale kecuali merah murni guide: Hue 0-10°/350-360°, Sat≥65%, Val 25-85% |
| Red Guide Detection | Filter RGB `r > 145 & r > g*1.5 & r > b*1.5 & g < 195 & b < 155`. Area: x<16% w, y>54% h. Min height: max(25px, 5.5% h) |
| Fixed-offset | Textbox kanan guide (X_OFFSET=6px), center sejajar guide top. W=42% lebar, H=5.3% tinggi |
| Folder Consensus | Pre-scan ≥2 foto gy1 konsisten (≤10px) → median gy1 dipakai untuk semua file di folder. **Key:** `(station, asset_type, detail)` |
| Diffuse Fill | Inpainting 60 iterasi, 4-arah neighbor averaging |

**Stage Priority (0→4):**
1. `stage_0_override` (`--y-override`)
2. `stage_1c_guide_original` (`find_red_guide`)
3. `stage_1c_guide_consensus` (folder consensus)
4. `stage_fallback` (`get_text_box()` — default: x=4.7%, y=73.5%, w=49%, h=82%)

**SSE:** emit JSON `{"type":"stage","file":"...","stage":"..."}` → dashboard real-time

---

### 5. [merge_pdf_foto.py](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/merge_pdf_foto.py) — Gabung PDF
**Input:** `02_pdf_target/*.pdf` + `04_photos_edited/` → **Output:** `05_pdf_merged/*.pdf`

| Function | Line | Purpose |
|----------|------|---------|
| `extract_location_from_filename(filename)` | 152-159 | Parse "CILEBUT-BOGOR" dari nama file |
| `extract_date_from_page1(page)` | 161-177 | Cari "Tanggal : YYYY-MM-DD" |
| `extract_checklist_title(page, filename)` | 179-191 | Cari baris "PERAWATAN" |
| `draw_header(page, location, date_str, checklist_title)` | 207-210 | Header A4 baru |
| `determine_btp_from_identifier(identifier)` | **263-296** | **NEW**: Generic BTP extraction. Support "W31D BOO", "J10 BOO", "ZP 201B MSG", "JPL 15 CLT-BOO" formats |
| `process_pdf(...)` | 265-452 | Core: parse aset → **scan ALL funclocs for identifier** → verif 3 foto → hapus halaman terakhir → buat halaman baru (4 aset/hlm) |
| `draw_centered_label(...)` | 201-205 | Label "Foto 0%/50%/100%" |

---

### 6. [app.py](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/app.py) — Flask Web Dashboard

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Dashboard HTML |
| `/api/config` | GET | Folder paths 01-05 |
| `/api/status` | GET | `is_running`, `current_step`, `progress`, `status_text`, `step_statuses` |
| `/api/files` | GET | PDF list (limit 100 + total) |
| `/api/run` | POST | `{"step":"all|step1..5", "overwrite":"1|0"}` |
| `/api/stop` | POST | Kill process |
| `/api/stream-logs` | GET | SSE real-time log |
| `/api/stream-stages` | GET | SSE stage events |
| `/api/stage-summary` | GET | counts + details per stage |
| `/api/step-summary` | GET | success/failed/skipped per step |
| `/api/open-folder/<key>` | GET | Buka folder di Explorer |

**`clear_stage_data()`** (line 63): reset `stage_counts`, `stage_details`, AND `step_statuses` → `"waiting"`. Dipanggil di `/api/run`.

---

## Critical Rules
1. **Read Before Working:** Baca AGENTS.md + Dashboard.md sebelum edit/propose.
2. **Update After Working:** Update Dashboard.md + daily log jika status task berubah. **WAJIB setiap perbaikan**.
3. **Daily Logs:** Hari baru → buat `Notes/Daily/YYYY-MM-DD.md`.
4. **Debug & Fix Rule (CRITICAL):** Jika user minta "debug ocr dan stage nya" — **HANYA** tampilkan hasil pembacaan + jelaskan stage terpilih. JANGAN fix kode sebelum konfirmasi user.
5. **Auto-Update Obsidian:** Setiap update kode/script/config, update Dashboard.md + daily log.
6. **Git:** Hanya push kalau diperintah user (`git add . && git commit -m "<type>: <subject>"`).

## ⚠️ Known Issues (2026-07-15)
- **17/291 folders missing date.txt**: Edge cases — BTP mismatch (W27A BOO→W27A BOP) atau identifier di PDF tidak match folder. **Mitigasi**: `edit_timemark_ide1.py` fallback ke tanggal hari ini. Tidak kritis selama 274/291 (94%) terisi.



## Debugging Patterns
```bash
# Debug stage detection
python edit_timemark_ide1.py --input "03_photos_export/AXC/ZP 60 BOO"

# View stage summary via API
curl http://localhost:5000/api/stage-summary

# Force manual Y position
python edit_timemark_ide1.py --input "folder" --date "..." --y-override 195

# Check schedule.json
python scheduler.py --pdf-dir 02_pdf_target --photos-dir 03_photos_export

# Debug HSV isolation
python -c "from edit_timemark_ide1 import preprocess_for_guide; from PIL import Image; img=Image.open('test.jpg'); out=preprocess_for_guide(img); Image.fromarray(out).save('debug_hsv.jpg')"
```

## Key ADR & Failed Experiments
- **ADR-001:** Pillow + Numpy, bukan OpenCV
- **ADR-002:** Ekstraksi gambar PDF via pypdf (original images)
- **ADR-003:** Aturan parsing layout PDF & struktur output
- **Gagal:** PaddleOCR (oneDNN bug Windows), EasyOCR preprocessing
- **Terbaik:** Tesseract `--psm 7`
