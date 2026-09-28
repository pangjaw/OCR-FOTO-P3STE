# ADR-012: Aplikasi Desktop Mandiri Windows (.exe) Tanpa Ketergantungan Python & Node.js

- **Status:** Diterima & Diimplementasikan
- **Tanggal:** 2026-09-15
- **Komponen:** `OCR_Foto_Timemark.exe`, `launcher.py`, `bin/node.exe`, `bin/python_engine/python_engine.exe`, `scripts/python_engine.py`, `web/src/lib/python-runner.ts`

---

## 1. Konteks & Latar Belakang

Sistem pemrosesan OCR Foto Timemark dan aplikasi web Next.js pada awalnya membutuhkan lingkungan pengembangan lokal lengkap yang terinstal:
- Python 3.10+ beserta pustaka pihak ketiga (`PyMuPDF/fitz`, `pdfplumber`, `pillow`, `numpy`, `openpyxl`, dll.)
- Node.js 18+ beserta dependensi npm di folder `web/`
- Konfigurasi variabel lingkungan PATH sistem

Di lingkungan operasional lapangan (komputer staf kantor resor atau stasiun), mayoritas PC tidak memiliki hak akses administrator, tidak memiliki koneksi internet bebas untuk `pip/npm install`, dan tidak memiliki runtime bahasa pemrograman pengembang. Pengguna membutuhkan berkas eksekusi tunggal (.exe) yang dapat langsung dijalankan dengan mengklik dua kali (*zero prerequisite / plug-and-play*).

---

## 2. Keputusan Desain & Arsitektur

Dipilih pendekatan distribusi tri-tier mandiri yang mengisolasi runtime tanpa memerlukan instalasi sistem:

```
Root Project/
├── OCR_Foto_Timemark.exe   ← [Tier 1] Launcher GUI Window (WebView2, ~19.9 MB)
├── launcher.py             ← Source code launcher (Edge Chromium WebView2)
├── bin/
│   ├── node.exe            ← [Tier 2] Portable Node.js v24.16.0 (~92.2 MB)
│   └── python_engine/      ← [Tier 3] Standalone PyInstaller Python Engine (~86.7 MB)
│       ├── python_engine.exe
│       └── (C-extensions: fitz, pdfplumber, numpy, PIL, openpyxl, dll.)
└── web/                    ← Next.js production build (.next, node_modules)
```

### A. Tier 1: Host Peluncur Jendela Desktop (`launcher.py` & `OCR_Foto_Timemark.exe`)
- Menggunakan library `pywebview` dengan backend native Windows Edge WebView2 (`edgechromium`).
- **Mode Windowed Murni (`--windowed` / `CREATE_NO_WINDOW`)**: Tidak ada command prompt hitam yang muncul di layar saat aplikasi dibuka.
- **Ukuran Jendela**: Dikonfigurasi `1320 × 860` px, terpusat di layar, dengan batas ukuran minimal `1024 × 700` px.
- **Pembersihan Proses Latar Belakang (*Clean Process Lifecycle*)**:
  - Menyambungkan event penutupan jendela (`window.events.closed`) dan `atexit` ke fungsi pemusnah pohon proses Windows (`taskkill /pid <node_pid> /f /t`).
  - Menjamin tidak ada proses zombie yang tertinggal di background Task Manager saat aplikasi ditutup pengguna.
- Dikompilasi menggunakan PyInstaller mode `--onefile` menjadi `OCR_Foto_Timemark.exe` di root repositori agar tampak sebagai berkas eksekusi tunggal yang bersih bagi pengguna.

### B. Tier 2: Runtime Web Portabel (`bin/node.exe`)
- Menempatkan biner mandiri `node.exe` (v24.16.0) resmi Windows x64 langsung di direktori `bin/`.
- `launcher.py` secara otomatis memeriksa keberadaan `bin/node.exe` sebelum mencoba mencari Node di PATH sistem.
- Menjalankan Next.js dalam mode produksi:
  `bin/node.exe web/node_modules/next/dist/bin/next start web -p <port>`
- Port ditentukan secara dinamis (mulai dari 3000) dengan mencari port yang tidak sedang dipakai, sehingga mencegah konflik jika port 3000 sedang digunakan oleh aplikasi lain.

### C. Tier 3: Engine Python Terpadu (`scripts/python_engine.py` & `bin/python_engine/`)
- Dibuat dispatcher terpusat `scripts/python_engine.py` yang mengimpor seluruh 14 skrip inti pipeline dan ekspor:
  1. `export_pdf_foto` (Step 1)
  2. `auto_crop_collages`
  3. `extract_pdf_dates` (Step 2)
  4. `scheduler` (Step 3)
  5. `audit_and_correct_personnel` (Step 3.5 & Audit Personil)
  6. `extract_file_personnel`
  7. `edit_timemark_ide1` (Step 4)
  8. `merge_pdf_foto` (Step 5)
  9. `correct_serat_optik_cores` (Step 6)
  10. `edit_photo_time_only`
  11. `export_tablo_excel`
  12. `export_dinasan_excel`
  13. `export_asset_data_excel`
  14. `correct_pdf_dates`
- **Keputusan Mode `--onedir` untuk Python Engine**:
  - Jika dikompilasi dengan `--onefile`, setiap kali sebuah tombol step ditekan oleh antarmuka web, sistem operasi harus mendekompresi arsip ~300 MB ke folder `%TEMP%`, menimbulkan jeda awal (*start-up lag*) sebesar 3–5 detik per pemanggilan.
  - Dengan mode `--onedir` di `bin/python_engine/`, seluruh berkas biner C-extensions siap dipanggil secara instan (~50 ms), menjamin responsivitas tinggi pada antarmuka web.

### D. Jembatan Adapter Dinamis (`web/src/lib/python-runner.ts`)
- Fungsi `spawnPython(scriptName, args, options)` bertindak sebagai gerbang tunggal:
  - Memeriksa keberadaan berkas `bin/python_engine/python_engine.exe`.
  - Jika ditemukan, memanggil: `python_engine.exe <scriptName> <args>`.
  - Jika tidak ditemukan (pada komputer pengembang), secara otomatis kembali menggunakan: `python -u scripts/<scriptName>.py <args>`.
- Mengetik kembalian fungsi secara eksplisit sebagai `ChildProcessWithoutNullStreams` untuk memastikan pemeriksaan kompilasi TypeScript Next.js tidak menganggap stream `stdout` dan `stderr` sebagai objek `null`.

---

## 3. Konsekuensi & Keuntungan

1. **Zero Setup**: Pengguna di komputer baru cukup menyalin folder aplikasi dan mengklik `OCR_Foto_Timemark.exe`. Tidak ada langkah instalasi perangkat lunak tambahan.
2. **Kinerja Eksekusi Setara Native**: Seluruh pustaka komputasi numerik dan pengolah gambar (`numpy`, `PIL`, `PyMuPDF`) berjalan pada kecepatan kompilasi C tanpa emulasi.
3. **Kemandirian Lingkungan**: Versi Node.js dan Python yang terpasang di komputer pengguna (atau ketiadaannya) tidak akan pernah mengganggu atau merusak jalannya aplikasi.
