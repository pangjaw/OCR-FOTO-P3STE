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
- Script export foto PDF sudah dibuat dalam `export_pdf_foto.py` dan sudah diuji pada contoh AXC, Wesel, dan Sinyal.

## Keputusan Yang Sudah Diambil

- Aturan dokumentasi ditetapkan: README untuk tujuan, setup untuk tahap/tools, memory untuk update kegiatan.
- `setup.md` dipakai sebagai acuan awal, bukan tempat catatan progres.
- Catatan progres kerja dipindahkan ke `memory.md`.
- File asli tetap tidak ditimpa.
- Output disimpan ke folder baru.
- Tahap 1 didahulukan sebelum membuat pipeline PDF.
- Untuk export foto PDF, pencarian judul aset dimulai dari halaman 2 sampai halaman terakhir agar halaman daftar aset tidak ikut terbaca.
- Halaman 1 dapat berisi daftar aset dengan nama aset yang sama, jadi script export tidak boleh memakai halaman 1 untuk scan judul aset dokumentasi.
- Struktur output export PDF dibuat lebih spesifik: `output_pdf_foto/TIPE_ASET/DETAIL_LOKASI/0.jpg`, `50.jpg`, `100.jpg`.
- Root output sementara tetap `output_pdf_foto/`; struktur final folder bisa disesuaikan lagi setelah script selesai.
- Jika file hasil export sudah ada, script boleh overwrite file lama.
- Tipe aset dideteksi otomatis dari judul aset, misalnya `AXLE COUNTER` menjadi `AXC`, lalu nanti bisa menjadi `SINYAL` atau `WESEL` sesuai isi PDF.
- Untuk `AXLE COUNTER ZPA SDM`, folder detail-lokasi adalah `ZPA SDM`, yaitu teks setelah kata `COUNTER` sampai akhir.
- Untuk `PENGGERAK WESEL ELEKTRIK 21A SRP`, folder detail-lokasi adalah `21A SRP`, yaitu teks setelah kata `ELEKTRIK` sampai akhir.
- Untuk Sinyal, jika judul aset tidak punya kata `ELEKTRIK`, fallback detail-lokasi diambil dari teks setelah `SINYAL MUKA`, misalnya `MJ20 BTT - MSG`.

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
- Menginspeksi contoh PDF `12-06-2026_PERAWATAN AXLE COUNTER SIEMENS 1 BULANAN_Pondokranji-Sudimara.pdf`.
- Menemukan halaman terakhir adalah halaman 4 dan berisi foto dokumentasi Axle Counter.
- Menemukan aset `AXL10414 : AXLE COUNTER ZPA SDM`, `AXL10387 : AXLE COUNTER ZPD SDM`, dan `AXL10388 : AXLE COUNTER ZPE SDM`.
- Memastikan setiap aset pada contoh PDF punya label `Foto 0%`, `Foto 50%`, dan `Foto 100%`.
- Menemukan `pdfplumber` membaca 9 posisi gambar pada halaman terakhir, sedangkan `pypdf` membaca 7 image object unik karena beberapa image object dipakai ulang.
- Keputusan planning: script export harus memetakan gambar berdasarkan posisi di halaman, bukan hanya berdasarkan daftar image object unik.
- Memperjelas rencana struktur folder export PDF: contoh `AXL10414 : AXLE COUNTER ZPA SDM` disimpan ke `output_pdf_foto/AXC/ZPA SDM/`.
- Menginspeksi contoh PDF `17-06-2026_PERAWATAN WESEL ELEKTRIK 2 MINGGUAN_Serpong(1).pdf`.
- Menemukan foto dokumentasi Wesel berada di halaman 4 dan 5; halaman 4 punya 4 aset, halaman 5 punya 1 aset.
- Menemukan aset Wesel: `WSL10032 : PENGGERAK WESEL ELEKTRIK 21A SRP`, `WSL10132 : PENGGERAK WESEL ELEKTRIK 11A SRP`, `WSL10133 : PENGGERAK WESEL ELEKTRIK 11B SRP`, `WSL10033 : PENGGERAK WESEL ELEKTRIK 21B SRP`, dan `WSL10034 : PENGGERAK WESEL ELEKTRIK 23A SRP`.
- Menetapkan tipe folder `WESEL` untuk aset dengan kode `WSL` atau judul berisi `WESEL`.
- Menginspeksi contoh PDF `26-05-2026_PERAWATAN PERAGA SINYAL ELEKTRIK 1 BULANAN_Batutulis-Maseng.pdf`.
- Menemukan foto dokumentasi Sinyal berada di halaman 3 dan punya 2 aset.
- Menemukan aset Sinyal: `SIN11742 : SINYAL MUKA MJ20 BTT - MSG` dan `SIN11741 : SINYAL MUKA MJ10 BTT - MSG`.
- Menetapkan tipe folder `SINYAL` untuk aset dengan kode `SIN` atau judul berisi `SINYAL`.
- Memastikan pola label pada contoh Wesel dan Sinyal tetap `Foto 0%`, `Foto 50%`, dan `Foto 100%`.
- Menetapkan keputusan sementara: output export tetap di `output_pdf_foto/` dan file lama dioverwrite jika nama output sama.
- Menambahkan script `export_pdf_foto.py` untuk crop foto dokumentasi dari PDF berdasarkan posisi gambar di halaman.
- Menjalankan script export pada tiga contoh PDF dan berhasil mengekspor total 30 foto.
- Memastikan output tersimpan ke `output_pdf_foto/AXC/...`, `output_pdf_foto/WESEL/...`, dan `output_pdf_foto/SINYAL/...` sesuai tipe aset dan detail lokasinya.
- Memperbaiki sanitasi nama folder hasil export supaya karakter tersembunyi dari teks PDF tidak membuat Windows menolak path output.
- Menambahkan penanganan error saat save per foto agar satu output bermasalah tidak menghentikan seluruh batch.
- Menjalankan ulang batch dari `input_pdf/` dan berhasil mengekspor total 81 foto tanpa status `failed` di log terbaru.
- Menganalisis hasil `output_foto/` dan menemukan output lama hanya berisi 32 dari 36 foto; file `0 (7).jpg`, `0 (8).jpg`, `0 (10).jpg`, dan `0 (11).jpg` belum ada di folder hasil lama.
- Menemukan akar masalah posisi edit Timemark: deteksi garis merah kiri bawah terlalu ketat, sehingga banyak foto jatuh ke fallback yang posisinya terlalu bawah dan tanggal baru menimpa area alamat.
- Memperbaiki `edit_timemark.py` supaya deteksi anchor menerima variasi merah/oranye, memilih run vertikal guide yang valid, dan memakai fallback tanggal yang lebih dekat ke baris tanggal asli.
- Menguji ulang batch foto ke `output_foto_fixed/` dan berhasil memproses 36/36 foto.
- Memastikan `edit_timemark.py` lolos `py_compile` setelah perubahan locator.

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
- Uji terbaru pada variasi foto Axle Counter menunjukkan posisi tanggal baru sudah naik ke baris tanggal lama, bukan jatuh ke baris alamat.
- Rencana berikutnya: uji `export_pdf_foto.py` pada PDF lain kalau ada layout baru yang agak beda.
- Jika struktur output final sudah disepakati, bisa pindahkan root dari `output_pdf_foto/` ke folder lain tanpa mengubah inti script.

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
2. Buat script export foto PDF, disarankan bernama `export_pdf_foto.py`.
3. Script export scan halaman 2 sampai halaman terakhir, cari judul aset, cocokkan foto terdekat dengan label `Foto 0%`, `Foto 50%`, dan `Foto 100%`.
4. Simpan hasil ke `output_pdf_foto/TIPE_ASET/DETAIL_LOKASI/0.jpg`, `50.jpg`, dan `100.jpg`, overwrite file lama jika ada, lalu tulis log ke `logs/pdf_photo_export_log.csv`.
5. Tambahkan mapping tanggal dari CSV jika tanggal target berbeda per file.
