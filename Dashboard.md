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
- **2026-07-15 08:50 WIB** — Full pipeline re-run (KEL1/KEL2 multi-funcloc + UNKNOWN elimination):
  - Step 1: **1,095 foto** diekspor, **UNKNOWN = 0** ⭐
  - Step 2: **133 date.txt** updated
  - Step 3: **351 schedule entries** (was 159, +120%) — KEL1 multi-funcloc
  - Step 4: **873/873 sukses, 0 gagal** (stage_1c: 833, consensus: 5, fallback: 35)
  - Step 5: **165 PDF merged, 0 failed** ⭐
- Fix yang diterapkan:
  - **UNKNOWN elimination**: INB→PDSE, TRA→PDSE/SERAT OPTIK/PTLS, RADIO/WAYSTATION→PTLS
  - **KEL1 multi-funcloc**: WESEL/SINYAL/AXC = 1 entry per funcloc (timestamp unik)
  - **KEL2 single identifier**: lainnya = 1 entry per folder
  - **JPL BNR parsing**: named JPL ("BNR BOP - BTT") properly extracted
  - **normalize_jpl_identifier**: spaced dash handling ("BOP - BTT" → "BOP-BTT")
- ⚠️ **Known issue (FIXED 2026-07-15 09:30)**: `extract_pdf_dates.py` rewrite pakai pre-scan folder lookup. Result: **278/291 (95.5%)** folder punya date.txt. 13 orphan folders tanpa matching PDF di `02_pdf_target`.
  - Root cause 13 missing: identifier "CLT" (generic station) produce collision across CATUDAYA/CTS/PDSE/PTDS/PTLS → folder created tapi no matching source PDF. Bukan bug logic, tapi structural gap antara 01_pdf_source (2026) dan 02_pdf_target (2025).
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
| [[Notes/Daily/2026-07-15\|**15 Jul**]] | KEL1/KEL2 multi-funcloc scheduler (159→351 entries). UNKNOWN elimination. JPL BNR parsing. Full clean run: 1095 foto, 873 edit, 165 PDF. | `scheduler.py`, `export_pdf_foto.py` |
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
