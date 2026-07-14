# ADR-008: Fix 36 Missing Funcloc Photos

> **Status:** Pending | **Date:** 2026-07-14

## Problem

36 funclocs di 32 PDF 2025 tidak memiliki foto di `03_photos_export`, meskipun PDF 2026-nya **ada** di `01_pdf_source` (kecuali 1 funcloc: J12B MSG yang memang tidak ada PDF 2026-nya).

## Audit Results

| Kategori | Count |
|----------|-------|
| AXC (ZP ...) | 15 |
| SINYAL (J..., JL..., L..., MJ...) | 11 |
| WESEL (W...) | 2 |
| TELEKOM/PTLS (JPL..., TLK..., TRA...) | 4 |
| TOTAL | **36 funclocs / 32 PDFs** |

## Root Cause Hypothesis

`export_pdf_foto.py` menggunakan `rglob("*.pdf")` yang seharusnya menemukan semua PDF. Tapi ada 2 kemungkinan:
1. **PDF gagal diekspor** — export gagal silently (0 foto), mungkin karena layout PDF berbeda (single funcloc vs multi-row)
2. **Identifier tidak match** — folder yang dibuat berbeda nama dari yang dicari merge (misal `ZP 22B` tanpa `BTT`)

## Proposed Fix

### Step 1: Trace 1 kasus end-to-end
- Pilih `ZP 22B BTT` → jalankan `export_pdf_foto.py` khusus untuk 2026 PDF-nya
- Lihat apa yang terjadi: folder apa yang dibuat, berapa foto
- Jika 0 foto → debug kenapa export gagal
- Jika berhasil → bandingkan folder name dengan yang dicari merge

### Step 2: Fix export_pdf_foto.py
- Berdasarkan hasil trace, perbaiki logika ekspor untuk menangani PDF single-funcloc
- Pastikan identifier konsisten antara export dan merge

### Step 3: Re-run pipeline (hanya untuk funcloc yang hilang)
- Export ulang 36 funcloc yang hilang
- Re-run `edit_timemark_ide1.py` untuk folder baru
- Re-run `merge_pdf_foto.py` untuk 32 PDF yang terpengaruh

## Files to Modify

- [export_pdf_foto.py](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/export_pdf_foto.py) — fix export logic
- [merge_pdf_foto.py](file:///c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/merge_pdf_foto.py) — sudah ok (BTP cross-search), tapi judul foto masih pendek

## Estimated Impact

- 32 dari 165 PDF akan berubah (ada foto baru)
- Full pipeline re-run mungkin diperlukan jika fix-nya kompleks
