# OCR-FOTO-P3STE — Project Index

> Indeks utama dokumentasi proyek. Mulai dari sini untuk memahami sistem dan menemukan file terkait.

## Core documentation

- [[README]] — Ringkasan proyek dan quick start
- [[PRD]] — Product requirements, scope, dan acceptance criteria
- [[ARCHITECTURE]] — Arsitektur pipeline dan aturan detector
- [[OPERATIONS]] — Command operasi, batch, log, dan troubleshooting
- [[CONTRIBUTING]] — Aturan perubahan kode dan validasi
- [[setup]] — Setup environment lokal

## Source map

- [`scripts/`](file:///C:/Users/dikarm/Documents/Server/OCR-FOTO-P3STE/scripts) — Script ekstraksi, OCR, detector, dan editing timemark; termasuk varian [`edit_timemark_YOLO.py`](file:///C:/Users/dikarm/Documents/Server/OCR-FOTO-P3STE/scripts/edit_timemark_YOLO.py)
- [`config/`](file:///C:/Users/dikarm/Documents/Server/OCR-FOTO-P3STE/config) — Konfigurasi aplikasi
- [`server.js`](file:///C:/Users/dikarm/Documents/Server/OCR-FOTO-P3STE/server.js) — Server/UI tooling
- [`schedule.json`](file:///C:/Users/dikarm/Documents/Server/OCR-FOTO-P3STE/schedule.json) — Data jadwal dan metadata asset

## Data flow folders

- `01_pdf_source/` — PDF sumber
- `02_pdf_target/` — PDF target/date reference
- `03_photos_export/` — Foto hasil ekstraksi
- `04_photos_canny_pipeline/` — Output pipeline detector/edit
- `04_photos_edited/` — Output edited foto
- `05_pdf_merged/` — PDF final/merged
- `logs/` — Log, audit, report, dan preview investigasi

## Knowledge vault

- [[Notes/Architecture Index]] — Peta catatan arsitektur
- [[Notes/Decisions Index]] — Peta keputusan teknis
- [[Notes/Decisions/Bug Fix History]] — Riwayat bug, penyebab, dan tindak lanjut
- [[Notes/Decisions/Active Pipeline Rules]] — Aturan pipeline yang sedang berlaku
- [[Notes/Experiments Index]] — Peta eksperimen
- [[Notes/Daily Index]] — Daily logs
- [[Notes/Templates Index]] — Template dokumentasi
- [[Notes/Test Results]] — Ringkasan hasil pengujian historis

## Working rules

- Posisi tanggal harus ditentukan dari guide pada foto yang sama.
- `y_override` tidak dipakai pada script sementara full-detector.
- Debug stage hanya melaporkan data internal sampai ada persetujuan tertulis untuk fix.
- Gambar yang diminta untuk ditampilkan harus disalin ke `logs/` terlebih dahulu.
