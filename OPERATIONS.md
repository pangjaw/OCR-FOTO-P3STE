# Operations Guide

## Quick checks

```powershell
python -c "import ast; from pathlib import Path; ast.parse(Path('scripts/edit_timemark_temp.py').read_text(encoding='utf-8')); print('SYNTAX_OK')"
```

## Full-detector batch

Gunakan script sementara hanya untuk eksperimen yang sudah disetujui. Contoh pola operasi:

```powershell
python scripts/edit_timemark_temp.py --input 03_photos_export --output 04_photos_temp_pipeline --schedule schedule.json --clear-output *> logs/temp_pipeline_run.log
```

## Evidence

- `logs/canny_pipeline_run.log` — summary dan stage batch
- `logs/edit_stages.xlsx` — stage per foto
- `logs/*audit*.json` — audit internal
- `logs/` — preview/montage yang diminta untuk inspeksi visual

## Step 5 PDF merge

Step 5 mencocokkan PDF dari `02_pdf_target/` dengan foto hasil edit di `04_photos_edited/`. Folder `Tim_N` pada path foto adalah sumber Tim untuk output `05_pdf_merged/Tim_N/`; Step 5 tidak membaca `schedule.json` untuk routing Tim.

Jalankan tanpa `--schedule`:

```powershell
python scripts/merge_pdf_foto.py --input 02_pdf_target --photos 04_photos_edited --output 05_pdf_merged
```

Jika aset dalam satu PDF ditemukan pada beberapa `Tim_N`, proses melaporkan konflik dan tidak memindahkannya diam-diam ke `Tim_1`. Jika tidak ada foto yang cocok, proses gagal agar masalah pencocokan terlihat.

## Troubleshooting

- Periksa stage dan koordinat internal sebelum mengubah detector.
- Bedakan no-guide/black image dari salah posisi.
- Periksa guide pada foto itu sendiri; jangan memakai median folder sebagai ground truth.
- Gunakan targeted samples sebelum batch penuh.
- Warning ZBar saat boundary detection terpisah dari routing Tim; periksa hasil merge dan log statusnya.

## Safety

Jangan menghapus input PDF/foto. Jangan menimpa script utama ketika eksperimen masih memakai script sementara. Simpan artefak visual di `logs/`.

## YOLO training capture

`edit_timemark_YOLO.py` otomatis menulis hasil deteksi guideline setiap foto diproses:

- Label: `logs/yolo_dataset/labels/<path-relatif>.txt`
- Manifest: `logs/yolo_dataset/manifest.jsonl`
- Format label: `class_id x_center y_center width height`, ternormalisasi 0–1.
- Class guideline saat ini: `0`.
- Foto tanpa deteksi dicatat sebagai `no_detection` di manifest tanpa label palsu.
- Bounding box label berasal dari bbox guideline YOLO aktual, bukan dari textbox timemark hasil offset.
- Foto input tidak disalin dan tidak diubah.
