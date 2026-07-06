# Project OCR Foto Timemark

Project ini dibuat untuk membantu koreksi tanggal watermark Timemark pada foto dokumentasi kerja.

## Tujuan Project

- Mengganti teks tanggal yang salah pada watermark Timemark.
- Memproses banyak foto secara batch tanpa menimpa file asli.
- Mengekspor foto dokumentasi dari PDF dan mengelompokkannya berdasarkan aset.
- Menjaga hasil revisi tetap rapi dan mudah dicek ulang.
- Menyiapkan alur lanjutan untuk foto yang tertanam di file PDF.
- Menyimpan jejak perubahan melalui output baru dan log proses.

## Batasan Utama

- Area yang diedit hanya baris tanggal watermark.
- Export foto PDF harus mengambil foto dokumentasi, bukan halaman penuh.
- Pencarian kelompok aset pada PDF dimulai dari halaman 2 sampai halaman terakhir agar halaman daftar aset tidak ikut terbaca.
- Foto asli harus tetap disimpan.
- Output revisi harus memakai folder atau nama file berbeda.
- Untuk kebutuhan administrasi resmi, perubahan tanggal harus mengikuti instruksi yang valid dan dapat dilacak.

## Rencana Output PDF Foto

Foto dari PDF akan dikelompokkan berdasarkan judul aset, misalnya:

```text
output_pdf_foto/
  WSL11080_PENGGERAK_WESEL_W23A_BOO/
    Foto_0_persen.jpg
    Foto_50_persen.jpg
    Foto_100_persen.jpg
```

## Aturan Dokumentasi

- `README.md`: tujuan dibuatnya project.
- `setup.md`: tahap kerja dan tools yang dibutuhkan.
- `memory.md`: update dari setiap kegiatan terhadap project.
