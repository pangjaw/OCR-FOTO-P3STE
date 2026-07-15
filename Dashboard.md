# 🗂️ OCR Foto Timemark — Project Dashboard

> **Baca ini dulu + AGENTS.md** sebelum edit/propose.

## Project Overview
Pipeline 5-tahap koreksi tanggal watermark GPS Map Camera. Input: PDF 2026 (foto asli) + PDF 2025 (template). Output: PDF 2025 upgrade foto baru + timemark terkoreksi.

Script references, detection logic, debugging → lihat [[AGENTS.md]].


## 📌 Status Tracker

### Active Scripts
- [x] `app.py` — Flask Web Dashboard (port 5000)
- [x] `edit_timemark_ide1.py` — Core watermark editor. HSV + Red Guide + Folder Consensus
- [x] `export_pdf_foto.py` — Ekstrak foto dari PDF
- [x] `merge_pdf_foto.py` — Gabung foto edit ke PDF lama
- [x] `extract_pdf_dates.py` — Ekstrak tanggal dari PDF target
- [x] `scheduler.py` — Penjadwalan Tim (07:00-18:00)

### Pipeline Status (Post-Audit)
- [x] Stage 1-5 pipeline: export → extract dates → schedule → edit → merge
- [x] Web UI dengan SSE real-time log & stage indicator
- [x] All asset types + funcloc1 categories (PDSE, PTDS, PTLS, CATUDAYA, SERAT OPTIK, **JPL, CTS**)
- [x] Station-based folder hierarchy (`station/asset_type/detail/`)
- [x] SAP mapping dari Excel lokasi sheets (547 entries, clean)
- [x] CS→COS alias fix (output folder gak ada duplikat)
- [x] Step indicator bug fix: statuses reset on stop/re-run
- [x] Merged output hierarchy: `Tim_N/BTP/Station/Category/file.pdf` (funcloc1 regular)
- [x] Merged output hierarchy: `Tim_N/BTP/Station/file.pdf` (regular assets)
- [x] **PTPP → JPL** (folder JPL, Tim/BTP/Lokasi/JPL/0,50,100)
- [x] **CTS → folder CTS** (berdiri sendiri)
- [x] **BOP-BTT → BTP BD** (dulu BTP JAK, now join BOP/BTT/CGB/COS/MSG)
- [x] **WESEL/SINYAL/AXC → multi-row export** (1 PDF = 4-5 baris foto, funcloc per baris)

### Batch Results
- **2026-07-15 15:55 WIB** — Full pipeline re-run (BTP routing + WESEL suffix + SINYAL multi-page):
  - Step 1: **4,521 foto** diekspor, **470 folder** (was 3594, +927)
  - Step 2: **278 date.txt** updated
  - Step 3: **schedule.json** updated (all 470 assets)
  - Step 4: **1,290/1,290 sukses, 0 gagal** (stage_1c: 1242, consensus: 6, fallback: 42)
  - BTP split: **311 BTP JAK + 159 BTP BD**
- Fix yang diterapkan:
  - **JPL fallback fix**: strip `JPL\d+ :` prefix before regex, handle `JPL 07 BOP-BTT` correctly
  - **Error logging**: `_log_error()` → `logs/export_errors.xlsx` (only for true failures)
  - **Multi-page export**: scan ALL pages with ≥3 images for SINYAL/WESEL/AXC
  - **WESEL date suffix**: `_extract_date_suffix()` → `W21B2 BOO_02-01/` folders
  - **SINYAL dotted codes**: regex `\.?` for B, J, JL, L prefixes (B.108, J.10)
  - **BTP routing**: `determine_btp()` now uses `re.findall` for compound identifiers (W23 MSG → BTP BD)
  - **BTP reorg**: 107+15 assets moved from BTP JAK to BTP BD
  - **Edit timemark date.txt**: `_read_date_txt()` reads from `03_photos_export/` folder
  - **Edit timemark blur/textbox sync**: same `(x1,y1,x2,y2)` dimensions
  - **BOX_HEIGHT_RATIO**: reverted to 0.053 (original size)
- **2026-07-14 17:48 WIB** — Full pipeline clean run (BTP cross-search + no-photo fallback):
  - Step 1: 5,340 foto, Step 2: 852 sukses, Step 5: 165 PDF merged
  - BTP cross-search + no-photo fallback
- **2026-07-14 16:35 WIB** — WESEL/SINYAL/AXC multi-row support (sebelumnya)

---

## Quick Commands

### Web UI
```powershell
python app.py   # → http://localhost:5000
```

### CLI Pipeline
```powershell
python export_pdf_foto.py           # Step 1
python extract_pdf_dates.py          # Step 2
python scheduler.py                  # Step 3
python edit_timemark_ide1.py --schedule schedule.json   # Step 4
python merge_pdf_foto.py --schedule schedule.json       # Step 5
```

---

## 📅 Daily Logs

| Tanggal | Ringkasan Update | File Terkait |
|---------|------------------|--------------|
| [[Notes/Daily/2026-07-15\|**15 Jul**]] | BTP routing fix (re.findall compound ID). WESEL suffix folders. SINYAL multi-page. Edit timemark: date.txt reading, blur/textbox sync. BTP reorg 122 assets. 4521 foto, 1290 edit, 278 dates. | `export_pdf_foto.py`, `edit_timemark_ide1.py` |
| [[Notes/Daily/2026-07-14\|**14 Jul**]] | Full pipeline fix: OTB→TELEKOM, BANGUNAN→PDSE, MULTIPLEX→PTLS, BOP-BTT split. Clean run: 474 foto, 156 edit, 79 PDF. | `export_pdf_foto.py`, `merge_pdf_foto.py` |
| [[Notes/Daily/2026-07-13\|**13 Jul**]] | Station-based folder hierarchy (BREAKING CHANGE). 7 asset types full support. Dead code cleanup. | Semua 6 script + 3 JSON |
| [[Notes/Daily/2026-07-12\|**12 Jul**]] | Browser freeze fix (limit 100 files). EventSource reconnect fix. | `app.py`, `index.html` |
| [[Notes/Daily/2026-07-11\|**11 Jul**]] | Folder Consensus fix: input folder aset tunggal. | `edit_timemark_ide1.py` |
| [[Notes/Daily/2026-07-10\|**10 Jul**]] | Pipeline full batch 2025: 1782 foto → 1530 edit → 97 PDF merged | Semua script |
| [[Notes/Daily/2026-07-09\|**9 Jul**]] | Stage 1c Red Guide Anchor. 237/237 sukses. | `edit_timemark_ide1.py` |
| [[Notes/Daily/2026-07-08\|**8 Jul**]] | Optimasi mask (16px tinggi, narrow mask 5px). Cleanup. | `edit_timemark_ide1.py` |
| [[Notes/Daily/2026-07-07\|**7 Jul**]] | Dynamic Gap Stage 2. Thresh 215. Opsi A ratio-based. | `edit_timemark_ide1.py` |

📄 Detail lengkap → [[Notes/Daily/]]


---

## API Endpoints (app.py)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/status` | is_running, current_step, progress, step_statuses |
| `POST /api/run {"step":"all|step1..5"}` | Jalankan pipeline |
| `POST /api/stop` | Hentikan proses |
| `GET /api/stream-logs` | SSE real-time stdout |
| `GET /api/stream-stages` | SSE stage events (dari edit_timemark) |
| `GET /api/stage-summary` | counts + details per stage |
| `GET /api/files` | PDF list (limit 100) |
| `GET /api/open-folder/<key>` | Buka folder di Explorer |

---

## 📎 Referensi Lengkap

| Dokumen | Keterangan |
|---------|------------|
| [[AGENTS.md]] | Function reference, detection logic, debugging patterns |
| [[README.md]] | Tujuan project, batasan, pipeline overview |
| [[setup.md]] | Instalasi, dependensi, cara menjalankan |
| [[system_architecture_gabung foto ke pdf\|Arsitektur Merge PDF]] | Flowchart & komponen merge_pdf_foto.py |
| [[Data Acuan Tenaga Perawatan Gabungan\|Data Acuan Tenaga]] | Standar waktu perawatan per aset (Sinyal + Telekom) |
| [[Notes/Test Results\|Hasil Test]] | Riwayat pengujian batch & unit |

### ADR (Architecture Decision Records)

| ADR | Keputusan |
|-----|----------|
| [[Notes/Decisions/ADR-001 - Pillow and Numpy instead of OpenCV\|ADR-001]] | Pillow + Numpy, bukan OpenCV |
| [[Notes/Decisions/ADR-002 - PDF Image Export via pypdf and pdfplumber\|ADR-002]] | Ekstraksi gambar via pypdf (original images) |
| [[Notes/Decisions/ADR-003 - PDF Layout Parsing and Output Structure\|ADR-003]] | Aturan parsing layout PDF & struktur output |
| [[Notes/Decisions/ADR-008-fix-36-missing-funcloc\|ADR-008]] | Fix 36 missing funcloc photos (pending) |

