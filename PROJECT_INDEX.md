# OCR-FOTO-P3STE — Project Index

> Indeks utama dokumentasi proyek. Mulai dari sini untuk memahami sistem dan menemukan file terkait.

## Core documentation

- [[README]] — Ringkasan proyek dan quick start
- [[PRD]] — Product requirements, scope, dan acceptance criteria
- [[ARCHITECTURE]] — Arsitektur pipeline dan aturan detector
- [[OPERATIONS]] — Command operasi, batch, log, dan troubleshooting
- [[CONTRIBUTING]] — Aturan perubahan kode dan validasi
- [[setup]] — Setup environment lokal
- [[update_app.md]] — SOP & Aturan Wajib Update & Rilis Aplikasi Desktop

## Source map

- [`SintelisUtility.exe`](file:///C:/Users/dikarm/Downloads/SintelisUtility.exe) — Aplikasi desktop terpadu Sintelis Utility 2.0 (v1.6.7) berbasis WebView2 (OCR Ceklis PDF, Downloader P3-STE, dan Timemark Editor)
- [`OCR_Foto_Timemark.exe`](file:///C:/Users/dikarm/Documents/Server/OCR-FOTO-P3STE/OCR_Foto_Timemark.exe) — Launcher aplikasi desktop mandiri Windows lama (WebView2 Edge Chromium)
- [`launcher.py`](file:///C:/Users/dikarm/Documents/Server/OCR-FOTO-P3STE/launcher.py) — Host peluncur desktop window dan life-cycle manager proses latar belakang Node.js
- [`bin/`](file:///C:/Users/dikarm/Documents/Server/OCR-FOTO-P3STE/bin) — Runtime biner portabel: `bin/node.exe` (Node.js v24.16.0) dan `bin/python_engine/` (PyInstaller Python Engine)
- [`web/`](file:///C:/Users/dikarm/Documents/Server/OCR-FOTO-P3STE/web) — Aplikasi web modern Next.js 14 App Router (port 3000, 5 modul lengkap)
- [`scripts/`](file:///C:/Users/dikarm/Documents/Server/OCR-FOTO-P3STE/scripts) — Script ekstraksi, OCR, detector, editing timemark, ekspor Tablo, serta dispatcher terpadu ([`python_engine.py`](file:///C:/Users/dikarm/Documents/Server/OCR-FOTO-P3STE/scripts/python_engine.py))
- [`config/`](file:///C:/Users/dikarm/Documents/Server/OCR-FOTO-P3STE/config) — Konfigurasi aplikasi
- [`server.js`](file:///C:/Users/dikarm/Documents/Server/OCR-FOTO-P3STE/server.js) — Server Express lama (port 5000)
- [`schedule.json`](file:///C:/Users/dikarm/Documents/Server/OCR-FOTO-P3STE/schedule.json) — Data jadwal dan metadata asset

## Data flow folders

- `01_pdf_source/` — PDF sumber
- `02_pdf_target/` — PDF target/date reference
- `03_photos_export/` — Foto hasil ekstraksi
- `04_photos_canny_pipeline/` — Output pipeline detector/edit
- `04_photos_edited/` — Output edited foto
- `04_koordinat/` — Output foto dengan stempel koordinat GPS
- `05_pdf_merged/` — PDF final/merged
- `05_koordinat/` — PDF final dengan foto koordinat
- `logs/` — Log, audit, report, preview investigasi, dan Tablo Excel (`logs/TABLO [BULAN] [TAHUN].xlsx`)

## Knowledge vault

- [[Notes/Architecture Index]] — Peta catatan arsitektur
- [[Notes/Decisions Index]] — Peta keputusan teknis (termasuk [[Notes/Decisions/ADR-010-export-tablo-excel]], [[Notes/Decisions/ADR-011-nextjs-web-app-architecture]], [[Notes/Decisions/ADR-012-standalone-desktop-executable]], [[Notes/Decisions/ADR-013-penanganan-aset-target-multi-tanggal]], [[Notes/Decisions/ADR-014-google-vision-detector-and-dynamic-textbox]], [[Notes/Decisions/ADR-015-ocr-fallback-personnel-audit-image-only]], [[Notes/Decisions/ADR-016 - Isolasi Edit Teks Foto Tunggal, Inline Timemark Editing, dan Interaksi Galeri]], [[Notes/Decisions/ADR-017 - Arsitektur Desktop Utility 2.0, PowerShell Atomic Updater, In-Memory Excel Dispatcher, dan NeuroNest UI]])
- [[Notes/Decisions/Bug Fix History]] — Riwayat bug, penyebab, dan tindak lanjut (27 entri aktif)
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
