# 🗂️ OCR Foto Timemark — Project Dashboard

> **Baca ini dulu + AGENTS.md** sebelum edit/propose.

## Project Overview
Pipeline 5-tahap koreksi tanggal watermark GPS Map Camera. Input: PDF 2026 (foto asli) + PDF 2025 (template). Output: PDF 2025 upgrade foto baru + timemark terkoreksi.

Script references, detection logic, debugging → lihat [AGENTS.md](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/AGENTS.md).

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
- **2026-07-14 17:48 WIB** — Full pipeline clean run (BTP cross-search + no-photo fallback):
  - Step 1: **5,340 foto** diekspor dari semua PDF 2026
  - Step 2: **852 sukses, 0 gagal** (stage_1c: 820, consensus: 5, fallback: 27)
  - Step 3: schedule.json dibuat (165 jobs)
  - Step 4: — (digabung step 2)
  - Step 5: **165 PDF merged, 0 failed, 0 skipped** ⭐ (02=165, 05=165 — match!)
- Fix yang diterapkan:
  - **BTP cross-search**: merge sekarang cari foto di semua folder BTP (JAK + BD) kalau tidak ketemu di BTP spesifik
  - **No-photo fallback**: PDF yang tidak punya foto tetap di-copy ke output, bukan di-skip
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
| **2026-07-14** | Full pipeline fix: OTB→TELEKOM, BANGUNAN→PDSE, MULTIPLEX→PTLS, BOP-BTT split. Clean run: 474 foto, 156 edit, 79 PDF. | `export_pdf_foto.py`, `merge_pdf_foto.py` |
| **2026-07-13** | Station-based folder hierarchy (BREAKING CHANGE). 7 asset types full support. Dead code cleanup. | Semua 6 script + 3 JSON |
| **2026-07-12** | Browser freeze fix (limit 100 files). EventSource reconnect fix. | `app.py`, `index.html` |
| **2026-07-11** | Folder Consensus fix: input folder aset tunggal. | `edit_timemark_ide1.py` |
| **2026-07-10** | Pipeline full batch 2025: 1782 foto → 1530 edit → 97 PDF merged | Semua script |
| **2026-07-09** | Stage 1c Red Guide Anchor. 237/237 sukses. | `edit_timemark_ide1.py` |
| **2026-07-08** | Optimasi mask (16px tinggi, narrow mask 5px). Cleanup. | `edit_timemark_ide1.py` |
| **2026-07-07** | Dynamic Gap Stage 2. Thresh 215. Opsi A ratio-based. | `edit_timemark_ide1.py` |

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
