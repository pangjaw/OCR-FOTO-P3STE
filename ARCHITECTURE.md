# System Architecture

## Data flow

```text
PDF source
  -> photo extraction
  -> 03_photos_export/
  -> guide/date detection
  -> timemark editing
  -> 04_photos_edited/Tim_N/
  -> optional PDF merge from 02_pdf_target/
  -> 05_pdf_merged/Tim_N/
```

## Components

- `OCR_Foto_Timemark.exe` — Standalone native desktop launcher (Edge Chromium WebView2)
- `bin/node.exe` — Portable Node.js v24.16.0 runtime
- `bin/python_engine/` — Standalone compiled PyInstaller Python Engine (14 scripts + C-extensions)
- `web/` — Next.js 14 App Router Fullstack Web Application (port 3000, 5 modul terpadu)
- `scripts/` — Executable pipeline logic & unified dispatcher `python_engine.py`
- `schedule.json` — Asset/date metadata
- `03_photos_export/` — Normalized image input
- `04_photos_edited/` — Edited image output
- `logs/` — Operational evidence and audit artifacts
- `server.js` — Legacy local Express UI support (port 5000)

## Desktop & Web Architecture

```text
Double Click: OCR_Foto_Timemark.exe (PyInstaller --onefile)
  │
  ├── 1. Deteksi Port Bebas (>=3000)
  ├── 2. Background Process: bin/node.exe (Next.js 14 Production Server, CREATE_NO_WINDOW)
  ├── 3. Render Native Window: Microsoft Edge WebView2 (1320x860 px)
  │      └── 5 Modul Web:
  │            ├── 1. Pipeline Runner & Live Terminal (SSE)
  │            ├── 2. Dual Photo Gallery & Timemark Manual Editor
  │            ├── 3. Employee Multi-Preset Manager
  │            ├── 4. Personnel Compliance Audit & Document Date Audit
  │            └── 5. KAI Official Excel Exporters (Tablo, Dinasan, Asset Data)
  └── 4. API Execution Bridge:
         └── spawnPython() in web/src/lib/python-runner.ts
               ├── Mode Non-Python: bin/python_engine/python_engine.exe <script> <args>
               └── Mode Developer: python -u scripts/<script>.py <args>
```

## Positioning contract

Untuk setiap foto:

1. Cari kandidat guide pada seluruh lebar foto tersebut.
2. Validasi warna, bentuk, tinggi, dan lokasi kandidat.
3. Pilih guide kiri, kanan, atau tengah berdasarkan bukti foto, bukan median folder.
4. Hitung anchor textbox dari guide terpilih; textbox tetap ditempatkan di sisi kanan guide sesuai keputusan operasi saat ini.
5. Jika beberapa kandidat mirip, pilih skor tertinggi tetapi tulis catatan review agar operator mengetahui selector sedang ragu.
6. Jika tidak ada guide, gunakan OCR tanggal lama bila tersedia; jika tidak, tandai foto sebagai fallback.

## Detector stages

Stage label harus tetap readable. Stage internal mencakup guide warna utama, orange/amber, kuning, detector inversi, OCR fallback, dan no-guide fallback. `stage_0_override` tidak digunakan pada full-detector script sementara.

## Manual editing & single photo isolation contract

1. **Isolasi Mutlak Edit Teks**: Perubahan teks tanggal/jam manual dari Web UI (tombol "✏️ Edit Teks" atau modal `#inlineTextModal`) hanya memproses 1 berkas foto target (`shouldApplyToAll = false`), kecuali opsi `[x] Terapkan ke seluruh foto (0, 50, 100)` dicentang pengguna. Berkas saudara tidak dirender ulang dan tanggalnya di `meta.json` dipertahankan utuh.
2. **Sinkronisasi Posisi Tanpa Merusak Teks**: Penggeseran posisi kotak timemark (drag & drop) menyinkronkan koordinat X & Y ke seluruh foto aset tanpa mengubah teks tanggal/jam saudara.
3. **Unclipped Dialog**: Kontrol input teks wajib berada pada dialog modal mandiri di lapisan root (`z-index: 99999`) dan bebas dari pemotongan kontainer gambar (`overflow: hidden`).


## Evidence and reproducibility

Setiap batch harus memiliki command, input root, output root, summary stage, dan log. Audit visual yang menampilkan gambar disimpan di `logs/`.
