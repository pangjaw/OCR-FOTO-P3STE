# Memory Log

Catatan update dari setiap kegiatan terhadap project. `README.md` dipakai untuk tujuan project, `setup.md` dipakai untuk tahap kerja dan tools.

## Aturan Dokumentasi

- `README.md`: tujuan dibuatnya project.
- `setup.md`: tahap kerja, struktur folder, perintah, dan tools yang dibutuhkan.
- `memory.md`: update dari setiap kegiatan terhadap project.

## Status Saat Ini

- Tujuan project: koreksi tanggal watermark Timemark pada foto dokumentasi, lalu memprosesnya secara batch termasuk PDF.
- Tahap 1 sudah dibuat dan dikalibrasi dalam `edit_timemark.py`.
- Tahap 1 saat ini memakai `Pillow + numpy`, bukan OpenCV.
- Script tahap 1 sudah diuji ulang pada dua foto contoh Cilebut.
- Rencana export foto PDF ditambahkan ke dokumentasi, tetapi script export belum dibuat.

## Keputusan Yang Sudah Diambil

- Aturan dokumentasi ditetapkan: README untuk tujuan, setup untuk tahap/tools, memory untuk update kegiatan.
- `setup.md` dipakai sebagai acuan awal, bukan tempat catatan progres.
- Catatan progres kerja dipindahkan ke `memory.md`.
- File asli tetap tidak ditimpa.
- Output disimpan ke folder baru.
- Tahap 1 didahulukan sebelum membuat pipeline PDF.
- Untuk export foto PDF, pencarian judul aset dimulai dari halaman 2 sampai halaman terakhir agar halaman daftar aset tidak ikut terbaca.

## Update Kegiatan

### 2026-07-07

- Menetapkan aturan dokumentasi project.
- Merapikan `README.md` supaya fokus pada tujuan project.
- Merapikan `setup.md` supaya fokus pada tahap kerja dan tools yang dibutuhkan.
- Memperbarui `memory.md` sebagai catatan kegiatan project.
- Memperbaiki deteksi garis merah Timemark agar tidak ikut menangkap warna oranye logo KAI.
- Memperkuat pembersihan area tanggal lama supaya teks belakang lebih blur dan tidak dobel.
- Memproses ulang 3 foto di `input_foto/` ke `output_foto/` dengan tanggal `Sabtu, Agt 02 2025`.
- Menambahkan shape hitam semi-transparan di belakang teks tanggal baru.
- Memproses ulang 3 foto di `input_foto/` setelah shape tanggal ditambahkan.
- Menginspeksi PDF contoh untuk rencana export foto per aset tanpa membuat script export.
- Menemukan halaman 4 berisi aset W23A, W43, W61A1, W61A2; halaman 5 berisi aset W41.
- Memastikan setiap aset punya 3 foto dengan label `Foto 0%`, `Foto 50%`, dan `Foto 100%`.
- Menambahkan rencana export foto PDF ke `README.md` dan `setup.md` tanpa menghapus informasi OCR foto.
- Memastikan planning export PDF tetap belum dieksekusi sebagai script.

## Kondisi Script Tahap 1

- Input default: `./input_foto`
- Output default: `./output_foto`
- Opsi penting:
  - `--date`
  - `--input`
  - `--output`
  - `--preview`
- Script punya fallback ke folder kerja saat `input_foto/` belum ada.
- Ada dua komponen utama:
  - deteksi anchor garis merah Timemark untuk menemukan baris tanggal
  - fill ringan pada crop tanggal supaya proses lebih cepat
  - penulisan ulang tanggal baru dengan ukuran font adaptif

## Hasil Uji Sementara

- Script berhasil memproses 2/2 foto contoh ke `output_foto/`.
- Posisi tanggal baru sudah masuk pada baris tanggal lama, bukan area alamat.
- Ukuran font sudah menyesuaikan kotak tanggal dan lebih mendekati watermark asli.
- Script berhasil memproses ulang 3/3 foto Maseng dari `input_foto/`.
- Tanggal baru sekarang memakai background shape hitam semi-transparan.
- Rencana berikutnya: buat otomasi export foto dari PDF berdasarkan judul aset dan label persen.
- Aturan rencana export PDF: scan dimulai dari halaman 2, lalu berjalan sampai halaman terakhir berapa pun jumlah halaman PDF.

## Folder Yang Sudah Ada

- `Hasil_Edit/`
- `Hasil_Generative/`
- `tmp/pdfs/`
- `output_foto_test/`
- `output_foto_test2/`
- `output_foto_test3/`
- `output_foto_test4/`
- `output_foto_test5/`
- `preview/`

## File Referensi Penting

- [README.md](README.md)
- [setup.md](setup.md)
- [edit_timemark.py](edit_timemark.py)
- [ocr.py](ocr.py)
- [01-06-2026_PERAWATAN WESEL ELEKTRIK 2 MINGGUAN_Bogor (1).pdf](01-06-2026_PERAWATAN%20WESEL%20ELEKTRIK%202%20MINGGUAN_Bogor%20(1).pdf)

## Next Step

1. Uji lebih banyak foto dengan variasi latar watermark.
2. Jika hasil batch foto sudah stabil, lanjut rancang `pdf_batch_timemark.py`.
3. Setelah planning disetujui, buat script export foto PDF dengan default scan halaman 2 sampai halaman terakhir.
4. Tambahkan mapping tanggal dari CSV jika tanggal target berbeda per file.
