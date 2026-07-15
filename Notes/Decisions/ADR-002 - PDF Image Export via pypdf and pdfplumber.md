# ADR-002: Ekstraksi Gambar Asli PDF menggunakan pypdf

- **Status:** 🟢 Accepted
- **Tanggal:** 2026-07-08
- **Pembuat:** Antigravity / User

> ← [[Notes/Decisions/ADR-001 - Pillow and Numpy instead of OpenCV|ADR-001]] | [[Dashboard]] | [[Notes/Decisions/ADR-003 - PDF Layout Parsing and Output Structure|ADR-003 →]]

## Konteks & Latar Belakang
Program perlu mengekstrak foto dokumentasi yang tertanam di halaman PDF. Jika menggunakan library rendering halaman penuh, resolusi gambar hasil ekstraksi berpotensi terkompresi atau terpotong kasar, yang merusak orisinalitas foto dokumentasi kerja.

## Keputusan yang Diambil
Menggunakan **`pypdf`** untuk mengekstrak data raw bytes dari gambar yang tertanam di dalam PDF, sementara **`pdfplumber`** tetap digunakan untuk memetakan koordinat teks/judul aset pada halaman guna menamai foldernya secara dinamis.

## Konsekuensi
- **Positif (+):**
  - Kualitas foto hasil ekstraksi 100% identik dengan foto asli yang di-upload ke PDF (tidak ada kompresi ulang atau blur akibat rendering).
  - Kecepatan pemrosesan jauh lebih tinggi karena tidak melakukan kalkulasi piksel render halaman.
- **Negatif (-):**
  - Kami bergantung pada dua library PDF (`pypdf` dan `pdfplumber`), yang meningkatkan dependensi proyek. Namun, karena keduanya memiliki fungsi spesifik (satu untuk raw bytes extraction, satu untuk layout coordinate detection), kombinasi ini adalah yang paling andal.
