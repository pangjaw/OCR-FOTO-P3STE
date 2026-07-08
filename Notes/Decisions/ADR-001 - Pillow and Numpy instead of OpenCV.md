# ADR-001: Penggunaan Pillow & Numpy untuk Manipulasi Watermark

- **Status:** 🟢 Accepted
- **Tanggal:** 2026-07-07
- **Pembuat:** Antigravity / User

## Konteks & Latar Belakang
Proyek ini membutuhkan kemampuan untuk mendeteksi warna anchor (garis merah/oranye) pada watermark foto Timemark, menghapus tanggal lama, lalu menimpa dengan tanggal baru. 
Sebelumnya ada opsi untuk menggunakan OpenCV (cv2) yang umum digunakan untuk image processing.

## Keputusan yang Diambil
Memilih untuk menggunakan kombinasi **Pillow (PIL)** dan **Numpy** dibandingkan OpenCV.

## Konsekuensi
- **Positif (+):** 
  - Dependensi proyek menjadi lebih ringan karena OpenCV cenderung memiliki file biner yang sangat besar.
  - Pillow sangat andal dalam penulisan teks dengan font kustom (TrueType) menggunakan modul `ImageFont` dan `ImageDraw`.
  - Numpy mempermudah pencarian warna (array slicing/masking) secara cepat pada kanal RGB tanpa overhead library grafis berat.
- **Negatif (-):**
  - Fungsionalitas computer vision tingkat lanjut (seperti image registration/alignment otomatis) lebih terbatas dibanding OpenCV jika di kemudian hari dibutuhkan pencocokan pola tingkat tinggi.
