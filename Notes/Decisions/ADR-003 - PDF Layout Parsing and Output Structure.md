# ADR-003: Aturan Parsing Layout PDF & Struktur Output Foto

- **Status:** 🟢 Accepted
- **Tanggal:** 2026-07-07
- **Pembuat:** Antigravity / User

> ← [[Notes/Decisions/ADR-002 - PDF Image Export via pypdf and pdfplumber|ADR-002]] | [[Dashboard]] | [[Notes/Decisions/ADR-008-fix-36-missing-funcloc|ADR-008 →]]

## Konteks & Latar Belakang
Program `export_pdf_foto.py` perlu memilah halaman PDF, mengenali judul aset, mengekstrak foto yang sesuai dengan label persentase (Foto 0%, 50%, 100%), dan menyimpannya secara otomatis ke folder yang terstruktur dengan nama lokasi yang bersih dari karakter ilegal Windows.

## Keputusan yang Diambil
1. **Rentang Scan Halaman**: Scan judul aset dimulai dari halaman 2 sampai halaman terakhir. Halaman 1 diabaikan karena berisi daftar isi/daftar aset umum yang berpotensi menghasilkan *false positive*.
2. **Pemetaan Gambar**: Pemetaan gambar dilakukan berdasarkan koordinat posisi pada halaman menggunakan `pdfplumber` (untuk menentukan foto mana yang berada di bawah judul aset mana), bukan hanya mengekstrak semua image object di dalam PDF secara berurutan.
3. **Overwrite Policy**: Jika file foto target dengan nama yang sama sudah ada di folder output, script diizinkan untuk melakukan *overwrite* otomatis.
4. **Deteksi Tipe Aset Otomatis**:
   - Kata kunci `AXLE COUNTER` atau kode `AXL` dipetakan ke folder `AXC`.
   - Kata kunci `WESEL` atau kode `WSL` dipetakan ke folder `WESEL`.
   - Kata kunci `SINYAL` atau kode `SIN` dipetakan ke folder `SINYAL`.
5. **Pembersihan Nama Folder (Sanitasi)**:
   - Detail lokasi diambil dari substring setelah kata kunci utama (misal setelah kata `COUNTER` atau `ELEKTRIK`).
   - Karakter-karakter tersembunyi atau ilegal untuk filesystem Windows dibersihkan dari string sebelum folder dibuat.

## Konsekuensi
- **Positif (+):**
  - Hasil ekstraksi tersusun rapi langsung sesuai klasifikasi tipe aset dan lokasi fisiknya.
  - Aman dijalankan di OS Windows tanpa kendala error `Invalid Path`.
- **Negatif (-):**
  - Pola parsing teks bersifat sangat terikat dengan template dokumen PDF saat ini. Jika layout atau tata bahasa judul aset di PDF berubah, aturan regex/substring pada parser perlu disesuaikan kembali.
