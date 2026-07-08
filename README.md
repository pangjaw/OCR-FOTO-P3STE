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

## Output PDF Foto

Foto dari PDF akan dikelompokkan berdasarkan judul aset, misalnya:

```text
output_pdf_foto/
  WESEL/
    W23A BOO/
      0.jpg
      50.jpg
      100.jpg
```

## Panduan Dokumentasi

Gunakan format ini supaya pengerjaan tetap konsisten di device lain.

### `README.md`

- Berisi tujuan project, batasan utama, output yang diharapkan, dan aturan dokumentasi.
- Jangan dipakai untuk catatan progres harian.
- Perbarui jika tujuan, batasan, atau format output project berubah.

### `setup.md`

- Berisi tahap kerja, struktur folder, perintah, tools, dependensi, dan alur menjalankan script.
- Perbarui jika ada script baru, command berubah, dependensi berubah, atau struktur folder berubah.
- Tulis instruksi yang bisa langsung diikuti di device baru.

### `memory.md`

- Berisi status terbaru, keputusan teknis, update penting, hasil uji, file referensi, dan next step.
- Jangan isi dengan output terminal panjang atau semua percobaan kecil.
- Catatan lama yang tidak lagi penting cukup diringkas; archive terpisah tidak diperlukan.
- Bagian atas harus selalu mencerminkan kondisi project terbaru.
