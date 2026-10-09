# ADR-017 — Arsitektur Desktop Utility 2.0, PowerShell Atomic Updater, In-Memory Excel Dispatcher, dan NeuroNest UI

- **Status**: Diterima & Diimplementasikan (v1.5.0 s/d v1.5.6)
- **Tanggal**: 2026-10-07
- **Pengambil Keputusan**: Tim Pengembang & AI Assistant
- **Konteks**: Aplikasi desktop mandiri `SintelisUtility` (`ganti-nama-app`) mengintegrasikan seluruh kapabilitas OCR Foto Timemark, koreksi dokumen, profil pegawai, dan ekspor formulir Excel resmi KAI.

---

## 1. Konteks & Masalah

Pada fase pengembangan v1.5.0 hingga v1.5.5, ditemukan beberapa tantangan teknis kritis pada pengoperasian desktop di Windows:
1. **Jendela Aplikasi Ganda**: Pemanggilan `sys.executable` oleh PyInstaller tanpa argumen CLI dispatcher memicu peluncuran ulang WebView2 (`webview.create_window()`), membuka GUI baru saat mengekspor Excel.
2. **Kegagalan Auto-Updater di Windows**: Perintah `timeout /t 1` pada skrip batch `.bat` gagal di latar belakang Windows (`Input redirection is not supported`), dan sistem operasi mengunci file executable yang sedang berjalan sehingga penimpaan file biner gagal.
3. **Pembengkakan Biner (Recursive Bundling)**: Konfigurasi PyInstaller memaketkan folder `dist/` yang berisi biner build sebelumnya, menyebabkan ukuran file melonjak hingga 1.11 GB.
4. **Pembacaan Folder Bersubfolder**: Ekspor dokumen gagal ketika pengguna memilih folder bertingkat (`siap di OCR`) karena pencarian berkas masih bersifat dangkal (`.glob("*.pdf")`).
5. **Kebutuhan Pengguna**:
   - Pengguna membutuhkan kontrol penuh untuk memilih folder penyimpanan output Excel kustom.
   - Sinkronisasi profil pegawai yang dipilih pengguna harus mengalir otomatis ke kop dan isi dokumen Tablo & Jadwal Dinasan.
   - Bar atas (Header Bento) perlu disederhanakan agar fokus hanya pada versi aktif (menyala oranye neon jika update baru tersedia) dan profil preset terpilih.

---

## 2. Keputusan Arsitektur

### A. Eksekusi Ekspor Excel In-Memory & CLI Dispatcher
- **In-Memory Generation**: Mengeliminasi pemanggilan subproses bertingkat (`subprocess.run([sys.executable, "--run-script", ...])`). Eksekusi penjadwalan `scheduler.build_schedule` dan pembuatan workbook `generate_tablo_workbook` serta `build_dinasan_workbook` dijalankan langsung di memori thread server Python. Waktu eksekusi terpangkas dari 20+ detik menjadi 2-3 detik.
- **CLI Dispatcher**: Baris awal `main()` pada `run_desktop_webview.py` memeriksa argumen CLI. Jika terdapat argumen skrip `.py` atau `--run-script`, eksekusi dialihkan ke `runpy.run_path()` dan langsung keluar (`sys.exit(0)`), mencegah munculnya jendela WebView kedua.

### B. PowerShell Native Atomic Updater (`sintelis_updater.ps1`)
- Menggantikan file batch `.bat` dengan skrip PowerShell native.
- Menggunakan `Start-Sleep -Seconds 1` yang aman dijalankan di background process Windows.
- Mengimplementasikan retry-loop berjangka waktu untuk perintah `Copy-Item` hingga kunci file proses yang ditutup sepenuhnya dilepas oleh kernel Windows.

### C. Pembersihan Bersih & Batas Ukuran Biner (Anti-Bloatware SOP)
- **Size Guardrail**: Menetapkan batas ukuran biner resmi **180 MB – 195 MB**.
- Skrip build server secara otomatis menghapus `dist/SintelisUtility.exe` sebelum PyInstaller dijalankan, mencegah penumpukan biner berulang.
- Konfigurasi `build_exe.spec` hanya membungkus file web statis dan secara eksplisit menyertakan modul kritis `cryptography` dan `pypdf._crypt_providers._cryptography`.

### D. Pencarian Rekursif & Deduplikasi Aset Cerdas
- Seluruh pemindaian dokumen PDF diubah menggunakan `.rglob("*.pdf")`, sehingga folder dengan kedalaman subfolder berapa pun (seperti `siap di OCR\BTP BD\AXLE COUNTER\...`) terbaca 100%.
- Menerapkan deduplikasi aset cerdas untuk mencocokkan funcloc aktual pada file PDF yang telah di-split, mencegah pembengkakan jadwal (dari 1.504 aset terduplikasi menjadi tepat 418 aset pada 414 PDF).

### E. Sinkronisasi Profil Pegawai Aktif & Pemilih Folder Output Kustom
- Menambahkan endpoint `/api/timemark/set-active-preset` dan fungsi `get_active_pegawai_config()`.
- Data KUPT dan roster personil tim dinasan dialirkan langsung ke formulir Tablo STE-RECORD-13.4.01 dan Daftar Dinasan Pegawai.
- Menambahkan dialog pemilihan folder output kustom native OS pada form ekspor (`ExcelExportPanel.jsx`), dengan fallback otomatis ke folder `logs/`.

### F. Desain UI NeuroNest & Minimalist Bento Header
- Mengadopsi bahasa desain modern NeuroNest (Collapsible Sidebar, Deep Slate `#0B0E14`, Neon Orange `#FF7300`).
- Menyederhanakan Header Bento menjadi 2 kartu:
  1. **Kartu Versi Aplikasi**: Menampilkan versi aktif (`v1.5.6`). Otomatis menyala outline dan glow oranye neon (`box-shadow: 0 0 16px rgba(255, 115, 0, 0.4)`) dan badge `● UPDATE TERSEDIA` yang dapat diklik saat ada rilis baru.
  2. **Kartu Profil Preset Aktif**: Menampilkan nama profil pegawai (KUPT & Personil) yang sedang digunakan.

---

## 3. Konsekuensi & Dampak

- **Positif**:
  - Aplikasi desktop berjalan sangat stabil, responsif, dan bebas dari kendala jendela ganda.
  - Pembaruan aplikasi berjalan 100% mulus di seluruh komputer Windows klien tanpa kendala izin kunci berkas.
  - File Excel Tablo dan Dinasan akurat sesuai personil lapangan dan tersimpan di folder pilihan pengguna.
  - Ukuran installer tetap ramping dan efisien (~183.9 MB).
- **Kepatuhan SOP**:
  - Setiap pembaruan wajib mengikuti aturan dan langkah kerja di [[update_app.md]].

---

> Kembali ke [[Notes/Decisions Index]]
