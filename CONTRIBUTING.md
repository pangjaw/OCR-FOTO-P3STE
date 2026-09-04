# Contributing

## Before changing code

- Baca [[PROJECT_INDEX]], [[PRD]], dan [[ARCHITECTURE]] yang relevan.
- Jelaskan apakah perubahan menyentuh detector, OCR, extraction, atau UI.
- Untuk debug stage, tampilkan evidence internal sebelum melakukan fix.

## Change rules

- Pertahankan comments/docstrings yang tidak terkait.
- Prefer perubahan kecil dan targeted.
- Jangan gunakan posisi foto lain sebagai ground truth posisi.
- Jangan menambahkan dependency tanpa alasan dan versi yang jelas.
- Simpan visual audit di `logs/`.

## Validation

- Syntax check untuk script yang berubah.
- Targeted test untuk detector yang berubah.
- Batch smoke test bila perubahan menyentuh pipeline.
- Periksa `git diff --check`.

## Documentation

Perbarui dokumen root jika behavior pipeline berubah. Gunakan `Notes/Decisions/` untuk keputusan arsitektur dan `Notes/Daily/` untuk catatan kronologis.
