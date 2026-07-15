# OCR Foto Timemark

Koreksi tanggal watermark GPS Map Camera pada foto dokumentasi kerja secara batch.

## Tujuan
- Ganti teks tanggal salah di watermark Timemark
- Proses batch tanpa timpa file asli
- Export foto dari PDF, edit watermark, gabung balik ke PDF
- Dashboard Web UI lokal untuk kontrol pipeline 5-tahap

## Pipeline 5 Tahap
```
01_pdf_source/ (PDF 2026)          02_pdf_target/ (PDF 2025)
       │                                  │
       ▼                                  ▼
  export_pdf_foto.py               extract_pdf_dates.py
  (ekstrak foto asli)              (ambil tanggal halaman 1)
       │                                  │
       └──────────┬───────────────────────┘
                  ▼
           scheduler.py + edit_timemark_ide1.py
           (jadwal Tim → edit watermark)
                  │
                  ▼
           merge_pdf_foto.py
           (gabung foto edit → PDF final)
                  │
                  ▼
           05_pdf_merged/
```

## Batasan
- Hanya area tanggal watermark yang diedit
- Output revisi di folder/file berbeda (tidak timpa asli)
- Export foto ambil image object asli dari PDF, bukan halaman penuh
- **Folder `03_photos_export/` sebagai sumber kebenaran** — struktur `station/asset_type/detail/` dipertahankan di seluruh pipeline

## Dokumentasi
| File | Untuk | Isi |
|------|-------|-----|
| [[setup.md]] | Manusia | Instalasi, dependensi, cara menjalankan |
| [[Dashboard.md]] | Agent + Manusia | Status tracker, daily logs, quick commands |
| [[AGENTS.md]] | Agent | Function reference, detection logic, debugging patterns |
| [[Notes/Daily/\|Daily Logs]] | Catatan | Perubahan harian detail |
| [[system_architecture_gabung foto ke pdf\|Arsitektur Merge PDF]] | Manusia | Flowchart & komponen merge_pdf_foto.py |
| [[Notes/Test Results\|Hasil Test]] | Catatan | Riwayat pengujian batch & unit |
| [[Data Acuan Tenaga Perawatan Gabungan\|Data Acuan]] | Referensi | Standar waktu perawatan per aset |

