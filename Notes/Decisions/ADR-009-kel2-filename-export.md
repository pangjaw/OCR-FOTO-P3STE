# ADR-009: KEL2 Folder Identifier from Filename (not Funcloc)

> **Status:** Planning | **Date:** 2026-07-16
> ← [[Notes/Decisions/ADR-008-fix-36-missing-funcloc|ADR-008]] | [[Dashboard]]

## Problem

Skrip `export_pdf_foto.py` saat ini menggunakan **funcloc extraction** (`extract_identifier()`) sebagai primary source untuk nama folder, termasuk untuk KEL2 (JPL, PTPP, CATUDAYA, PDSE, CTS, PTDS, PTLS, SERAT OPTIK).

Ini **salah untuk KEL2**, karena:

1. **1 PDF KEL2 = 1 aset** → funcloc extraction berlebihan & rawan mismatch
2. **Merge perlu cocokin folder dengan nama file 2025** → funcloc di 2026 dan 2025 bisa beda format
3. **Kasus konkret**: JPL single/double station (e.g. `NO 07 BOP` vs `NO 07 BOP - BTT`) menyebabkan folder naming inconsistency

## Aturan

| Kategori | Sumber Identifier |
|---|---|
| **KEL1** (WESEL, SINYAL, AXC) | Funcloc (multi-row, 1 PDF >1 asset) |
| **KEL2** (JPL, PTPP, SERAT OPTIK, CATUDAYA, PDSE, CTS, PTDS, PTLS) | **Nama file** PDF |

## Alur Usulan

```
export_kel2_from_filename.py (standalone, tidak edit export_pdf_foto.py)
     │
     ├── 01_pdf_source/*.pdf
     ├── detect_category_from_filename()
     ├── extract_identifier_from_filename() [FUNGSI BARU]
     │   └── ngikut pola nama file, bukan funcloc
     ├── export foto → {output}/{btp}/{category}/{identifier}/
     └── mapping Excel → kel2_folder_mapping.xlsx
```

## Per-Kategori

| Kategori | Contoh Filename | Identifier |
|---|---|---|
| **JPL** | `PERAWATAN PINTU PERLINTASAN JPL 07 BOP-BTT 27-01-2026.pdf` | `JPL 07 BOP-BTT` |
| **PTPP** | `PERAWATAN PTPP JPL 27 BOO-CLT 26-01-2026.pdf` | `JPL 27 BOO-CLT` |
| **SERAT OPTIK** | `PERAWATAN SERAT OPTIK ER BOO 08-01-2026.pdf` | `ER BOO` |
| | `PERAWATAN SERAT OPTIK JPL 26N CLT 17-01-2026.pdf` | `JPL 26N CLT` |
| **CATUDAYA** | `PERAWATAN CATU DAYA ER RADIO BOO 29-01-2026.pdf` | `ER RADIO BOO` |
| **PDSE** | `PERAWATAN PDSE BOP 11-01-2026.pdf` | `PDSE BOP` |
| **CTS** | `PERAWATAN CTC-CTS BOO 08-01-2026.pdf` | `CTS BOO` |
| **PTDS** | `PERAWATAN PTDS BOO 08-01-2026.pdf` | `PTDS BOO` |
| **PTLS** | `PERAWATAN PTLS BOO 29-01-2026.pdf` | `PTLS BOO` |

## Open Questions

1. **PDSE/PTDS/PTLS** — apakah identifier `{kategori} {station}` cukup, atau perlu detail dari deskripsi?
2. **SERAT OPTIK ER TELKOM** — apakah `ER TELKOM` dipertahankan atau `ER` saja?
3. **CATUDAYA** — hanya 2 file (ER RADIO BOO, ER RADIO COS). Folder: `ER RADIO BOO` atau `CATUDAYA ER RADIO BOO`?

## Files

- `export_kel2_from_filename.py` — [NEW] skrip standalone
- `03_photos_export/` — output folder (sama dengan skrip asli)
- `kel2_folder_mapping.xlsx` — mapping hasil
