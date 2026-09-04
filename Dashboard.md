# 🗂️ OCR Foto Timemark — Project Dashboard

> **Baca ini dulu + AGENTS.md** sebelum edit/propose.

## Project Overview
Pipeline 5-tahap koreksi tanggal watermark GPS Map Camera. Input: PDF 2026 (foto asli) + PDF 2025 (template). Output: PDF 2025 upgrade foto baru + timemark terkoreksi.

Script references, detection logic, debugging → lihat [[AGENTS.md]].


## 📌 Status Tracker

### Active Scripts
- [x] `server.js` — Node.js Express Web Dashboard (port 5000)
- [x] `export_dinasan_excel.py` — Generator Excel Daftar Dinasan Pegawai (Format Resmi KAI)
- [x] `edit_timemark_ide1.py` — Core watermark editor. HSV + Red Guide + Folder Consensus
- [x] `edit_photo_time_only.py` — Standalone 24h Time Stamper (output: `04_Time`)
- [x] `employee_manager.py` — Roster Personil Tim 2 (KAUR/PNC) & True PDF Redaction
- [x] `export_pdf_foto.py` — Ekstrak foto dari PDF
- [x] `merge_pdf_foto.py` — Gabung foto edit ke PDF lama
- [x] `extract_pdf_dates.py` — Ekstrak tanggal dari PDF target
- [x] `scheduler.py` — Penjadwalan Tim (07:00-18:00)

### Pipeline Status (Post-Audit)
- [x] Detailed Error Logging & Exit Code Fix pada `export_pdf_foto.py` (Step 1)
- [x] Generator & Export **Daftar Dinasan Pegawai (Format Resmi KAI .xlsx)**
- [x] Menu Web **👥 Daftar Pegawai** & Alokasi Otomatis Roster Tim 2 per Tanggal
- [x] Modul mandiri **Edit Jam Foto** (Step 1-5 Time, `04_Time` & `05_pdf_merged_Time`)
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
- **2026-07-16 09:30 WIB** — PTPP/JPL folder naming fix:
  - `extract_jpl_from_filename()`: parse `PERAWATAN PTPP JPL 27 BOO-CLT 26-01-2026.pdf` → `JPL 27 BOO-CLT`
  - `JPL_IDENTIFIER_OVERRIDES`: `JPL 26N BJD-CLT` → `JPL 26N CLT`
  - Verifikasi: 3 PTPP PDF test export → folder bener (`JPL 27 BOO-CLT`, `JPL 28 BOO-CLT`, `JPL 26N CLT`)
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
  - **Auto-Crop Kolase (White-Seam Isolation):** Selesai diimplementasikan di `scripts/auto_crop_collages.py` dan terintegrasi di `server.js` (Step 1.5 & Run All).
  - **Filter & Koreksi Kolase Web UI:** Filter `🗂️ FOTO KOLASE`, badge filter, dan `Editor Timemark Manual` telah terintegrasi untuk menampilkan foto hasil potong (cropped 300x300) secara presisi.
  - **Sinkronisasi Tim 1 & Tim 2 Multi-Team:** Parameter `--schedule` di `edit_timemark_ide1.py` telah diset default ke `schedule.json`. Distribusi output:
    - `04_photos_edited`: Tim_1 = 1.341 foto, Tim_2 = 75 foto (Total 1.416 foto, semua `meta.json` dan `detector.json` aman).
    - `05_pdf_merged`: Tim_1 = 310 PDF, Tim_2 = 25 PDF (Total 335 PDF sukses). 1 PDF (`PERAWATAN PTLS CGB 28-08-2025.pdf` / MULTIPLEX CGB) dilewati sesuai konfirmasi karena tidak ada dokumen inspeksi di sumber 2026.
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
| [[Notes/Daily/2026-08-30\|**30 Agt**]] | Modul Edit Jam Foto (`04_Time`), Galeri Asset Row Grouping (0/50/100%), Filter Kalender per Tanggal, dan Tab Baru `📅 Schedule Sheet` (Spreadsheet Viewer + Export Excel). | `scripts/edit_photo_time_only.py`, `scripts/export_schedule_excel.py`, `server.js`, `templates/index.html` |
| [[Notes/Daily/2026-07-16\|**16 Jul**]] | Investigasi JPL naming inconsistency. Root cause: KEL2 pakai funcloc (salah), harusnya filename. Buat ADR-009, plan skrip `export_kel2_from_filename.py`. | `export_pdf_foto.py`, `Notes/Decisions/ADR-009-kel2-filename-export.md` |
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
| [[Notes/Decisions/ADR-009-kel2-filename-export\|ADR-009]] | KEL2 folder dari filename, bukan funcloc (planning) |

