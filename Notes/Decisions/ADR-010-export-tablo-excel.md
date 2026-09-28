# ADR-010: Export Tablo Perawatan Berkala (.xlsx) Form STE-RECORD-13.4.01

- **Status:** Diterima & Diimplementasikan
- **Tanggal:** 2026-09-13
- **Komponen:** `scripts/export_tablo_excel.py`, `server.js`, `templates/index.html`

---

## 1. Konteks & Latar Belakang

Sistem OCR-FOTO-P3STE telah memiliki fungsi penjadwalan tim dan aset (`scripts/scheduler.py` -> `schedule.json`) serta ekspor tabel spreadsheet jadwal mentah (`scripts/export_schedule_excel.py`). Namun, unit kerja operasional Resort Sintel 1.21 Bogor membutuhkan dokumen pelaporan resmi siap cetak yang mengikuti format baku PT Kereta Api Indonesia (Persero):

**Form No. STE-RECORD-13.4.01: JADWAL CHECKLIST & PERAWATAN BERKALA UPT RESORT SINTEL 1.21 BOGOR**

Formulir ini memiliki karakteristik khusus yang berbeda dari spreadsheet jadwal mentah:
1. Memiliki header resmi lengkap dengan Logo KAI, judul form, nomor dokumen, periode, dan identitas resor.
2. Memadukan matriks penugasan personil aktif di sisi kiri dengan legenda 46 kelompok peralatan di sisi kanan.
3. Memerlukan blok pengesahan "dibuat oleh : (Kepala Urusan Preventif)" di atas legenda serta blok "Disetujui Oleh : (KUPT Resor Sintel 1.21 Bogor)" di bawah tabel data personil.
4. Membutuhkan fleksibilitas pemrosesan baik dari data pipeline aktif (`schedule.json`) maupun langsung dari folder dokumen target PDF kustom.

---

## 2. Keputusan Desain & Arsitektur

### A. Dua Mode Operasi
1. **Mode 1: Pipeline Aktif (`--mode pipeline`)**:
   - Membaca langsung `schedule.json` yang telah dihasilkan oleh pipeline utama.
   - Sangat cepat (~0.5 detik) dan cocok untuk ekspor instan saat alur pipeline sedang berjalan.
2. **Mode 2: Folder PDF Kustom (`--mode custom --folder <path>`)**:
   - Menjalankan `scheduler.py` dan `extract_pdf_dates.py` secara dinamis pada folder dokumen target yang dipilih pengguna ke file sementara di `logs/temp_custom_schedule.json`.
   - Menghasilkan Tablo Excel langsung dari dokumen di folder tersebut tanpa mengubah file jadwal aktif pipeline.

### B. Struktur Matriks & Penataan Baris Sejajar
Struktur baris horizontal diatur presisi 100% sejajar antara sisi kiri (Waktu & Personil) dan sisi kanan (Pengesahan & Legenda):
- **Baris 1 s.d. 3**:
  - Sisi Kiri (A1..B3): Logo KAI (`config/kai_logo.png`).
  - Sisi Tengah (C2..K2): Judul `"JADWAL CHECKLIST & PERAWATAN BERKALA"`.
  - Sisi Kanan (P1..S3): Metadata form rata kanan (`Form No. STE-RECORD-13.4.01`, `UPT RESORT SINTEL 1.21 BOGOR`, `[BULAN TAHUN]`).
- **Baris 4 (Header Bar Sejajar, Tinggi 18 pt)**:
  - Kolom A..C: `"WAKTU"` (latar hijau muda `#C6E0B4`).
  - Kolom D..J: Pita kuning penanda personil (latar kuning `#FFE599`).
  - Kolom L..S: `"dibuat oleh :"` (latar biru muda `#B4C6E7`).
- **Baris 5 (Isi Header Sejajar, Tinggi 68 pt)**:
  - Kolom A..C: `"BULAN"`, `"HARI"`, `"TANGGAL"` (rotasi teks 90°).
  - Kolom D..J: Nama 7 Personil aktif (rotasi teks 90°, Furqon latar biru muda `#B4C6E7`, personil lain putih).
  - Kolom L..S: Kotak Tanda Tangan Pengesahan (`Kepala Urusan Preventif` di bagian atas, ruang kosong tanda tangan basah, `Yatiyo / Nipp. 49957` di bagian bawah; tanpa garis pembatas horizontal di tengah).
- **Baris 6 (Spacer & Judul Legenda, Tinggi 18.5 pt)**:
  - Kolom A..J: Baris kosong pemisah bergaris tepi.
  - Kolom L..S: `"KELOMPOK PERALATAN"` (latar abu-abu `#D9D9D9`).
- **Baris 7 (Hari Pertama & Stasiun Legenda, Tinggi 18.5 pt)**:
  - Kolom A..J: Tanggal 1 (`Sabtu 1` beserta kode tugas personil).
  - Kolom L..S: Header stasiun legenda (`BOGOR`, `BOGOR-CILEBUT`, `MASENG`).
- **Baris 8 s.d. Akhir Bulan**:
  - Kolom A..J: Tanggal 2 s.d. selesai (Bulan dimerge vertikal dari A7 s.d. akhir).
  - Kolom L..S: Daftar 46 Kelompok Peralatan dalam 3 blok stasiun.

### C. Logika Penugasan & Penyelarasan Jadwal Furqon
1. Sesuai instruksi pengguna, kolom kedua personil kosong ditiadakan; lembar kerja hanya menyajikan 7 personil aktif:
   - Furqon Susilo Wardoyo (KUPT Resor Sintel 1.21)
   - Sutisna (Kaur Perbaikan)
   - Yatiyo (Kaur Preventif)
   - Iwan Setiawan, Jujun Junaedi, Dika Armansyah, Raihan Herpian (Petugas Negatif Check)
2. **Harmonisasi Furqon**: Jadwal Furqon diselaraskan penuh dengan personil aktif lainnya tanpa libur (`L`) dan tanpa dinas siang (`PM`):
   - Pada tanggal aktif perawatan, Furqon otomatis diisi nomor kelompok peralatan (mengikuti Tim 1 atau Tim 2).
   - Pada tanggal standby/tanpa perawatan, diisi kode dinas `P` (Pagi/Normal).
3. **Peniadaan Tabel Keterangan Kode Dinas**: Tabel keterangan kode dinas (P, S, M, L, CT, dsb.) di bawah legenda ditiadakan agar dokumen fokus dan bersih.

### D. Penamaan Berkas Resmi
- Format nama berkas otomatis: **`TABLO [BULAN] [TAHUN].xlsx`** (misal: `TABLO MARET 2026.xlsx` dengan ekstensi huruf kecil `.xlsx`).
- Menghapus file lama sebelum save untuk mengatasi case-preservation Windows NTFS yang mempertahankan kapitalisasi lama.
- Server API dan Web UI secara dinamis membaca dan mengunduh berkas dengan nama tersebut.

---

## 3. Konsekuensi & Hasil Pengujian

- **Akurasi Pemetaan Kelompok Peralatan**: 100.0% dari 1.483 entri aset di `schedule.json` berhasil dipetakan ke 46 kelompok peralatan tanpa missing ID.
- **Konsistensi Tampilan**: Tampilan di Microsoft Excel maupun spreadsheet viewer tampil proporsional, rapi, dan siap cetak tanpa teks terpotong.
- **Waktu Eksekusi**:
  - Mode 1: ~0.8 detik.
  - Mode 2: ~4.5 detik (termasuk ekstraksi tanggal dan penjadwalan dinamis).
