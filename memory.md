# Memory Log

Catatan ringkas progres penting project. Simpan status terbaru, keputusan teknis, hasil uji, dan next step yang masih relevan. Catatan lama yang tidak lagi penting cukup diringkas di file ini; tidak perlu archive terpisah.

## Aturan Dokumentasi

- `README.md`: tujuan dibuatnya project.
- `setup.md`: tahap kerja, struktur folder, perintah, dan tools yang dibutuhkan.
- `memory.md`: status terbaru, keputusan, progres penting, hasil uji, dan next step.

## Status Saat Ini

- Tujuan project: koreksi tanggal watermark Timemark pada foto dokumentasi, lalu memprosesnya secara batch termasuk PDF.
- Tahap edit foto utama ada di `edit_timemark.py` dan memakai `Pillow + numpy`, bukan OpenCV.
- Deteksi posisi tanggal Timemark sudah diperbaiki agar menerima variasi merah/oranye dan fallback tidak turun ke area alamat.
- Script export foto PDF sudah dibuat di `export_pdf_foto.py`.
- Export PDF sudah diuji pada contoh AXC, Wesel, dan Sinyal.
- `requirements.txt` sudah tersedia untuk setup device baru.

## Keputusan Yang Sudah Diambil

- File asli tidak ditimpa; hasil disimpan ke folder output.
- Untuk export foto PDF, scan judul aset dimulai dari halaman 2 sampai halaman terakhir.
- Halaman 1 tidak dipakai untuk scan judul aset dokumentasi karena bisa berisi daftar aset dan memicu false positive.
- Export foto PDF memetakan gambar berdasarkan posisi di halaman, bukan hanya daftar image object unik dari PDF.
- Struktur output export PDF: `output_pdf_foto/TIPE_ASET/DETAIL_LOKASI/0.jpg`, `50.jpg`, `100.jpg`.
- Root output sementara tetap `output_pdf_foto/`; bisa diganti nanti tanpa mengubah inti script.
- Jika file hasil export sudah ada, script boleh overwrite file lama.
- Tipe aset dideteksi otomatis:
  - `AXLE COUNTER` atau kode `AXL` menjadi `AXC`.
  - `WESEL` atau kode `WSL` menjadi `WESEL`.
  - `SINYAL` atau kode `SIN` menjadi `SINYAL`.
- Detail lokasi diambil dari judul aset:
  - AXC: teks setelah `COUNTER`, contoh `AXLE COUNTER ZPA SDM` -> `ZPA SDM`.
  - WESEL: teks setelah `ELEKTRIK`, contoh `PENGGERAK WESEL ELEKTRIK 21A SRP` -> `21A SRP`.
  - SINYAL: teks setelah `ELEKTRIK`, atau fallback setelah `SINYAL MUKA` / `SINYAL`.

## Update Kegiatan

### 2026-07-07

- Menetapkan aturan dokumentasi: `README.md` untuk tujuan, `setup.md` untuk tahap/tools, `memory.md` untuk progres penting.
- Merapikan `README.md`, `setup.md`, dan `memory.md`.
- Menambahkan `requirements.txt` berisi dependensi inti: `numpy`, `pillow`, `pdfplumber`, dan `pypdf`.
- Memperbaiki deteksi garis merah Timemark agar tidak ikut menangkap warna oranye logo KAI.
- Memperkuat pembersihan area tanggal lama dan menambahkan background hitam semi-transparan di belakang tanggal baru.
- Menginspeksi PDF contoh Wesel, AXC, dan Sinyal untuk pola judul aset, label `Foto 0%`, `Foto 50%`, dan `Foto 100%`.
- Menemukan bahwa `pdfplumber` membaca posisi gambar di halaman lebih sesuai untuk export foto dibanding daftar image object unik dari `pypdf`.
- Menambahkan `export_pdf_foto.py` untuk crop foto dokumentasi dari PDF berdasarkan posisi gambar di halaman.
- Menjalankan export pada tiga contoh PDF dan berhasil mengekspor total 30 foto.
- Menjalankan ulang batch dari `input_pdf/` dan berhasil mengekspor total 81 foto tanpa status `failed` di log terbaru.
- Memperbaiki sanitasi nama folder hasil export supaya karakter tersembunyi dari teks PDF tidak membuat Windows menolak path output.
- Menambahkan penanganan error saat save per foto agar satu output bermasalah tidak menghentikan seluruh batch.
- Menemukan hasil lama `output_foto/` hanya berisi 32 dari 36 foto.
- Memperbaiki `edit_timemark.py` supaya deteksi anchor menerima variasi merah/oranye, memilih run vertikal guide yang valid, dan fallback tanggal lebih dekat ke baris tanggal asli.
- Menguji ulang batch foto ke `output_foto_fixed/` dan berhasil memproses 36/36 foto.
- Memastikan `edit_timemark.py` lolos `py_compile` setelah perubahan locator.

## Kondisi Script

### `edit_timemark.py`

- Input default: `./input_foto`.
- Output default: `./output_foto`.
- Opsi penting: `--date`, `--input`, `--output`, `--preview`.
- Jika `input_foto/` belum ada, script punya fallback ke folder kerja.
- Alur utama:
  - deteksi anchor garis merah/oranye Timemark untuk menemukan baris tanggal;
  - bersihkan crop tanggal lama;
  - tulis ulang tanggal baru dengan ukuran font adaptif dan background semi-transparan.

### `export_pdf_foto.py`

- Input default: `./input_pdf`.
- Output default: `./output_pdf_foto`.
- Log default: `./logs/pdf_photo_export_log.csv`.
- Scan default mulai halaman 2.
- Label output: `0.jpg`, `50.jpg`, `100.jpg`.
- Folder output dikelompokkan berdasarkan tipe aset dan detail lokasi.

## Hasil Uji Penting

- Edit foto awal berhasil pada 2/2 foto contoh Cilebut.
- Edit foto Maseng berhasil pada 3/3 foto.
- Uji terbaru `edit_timemark.py` berhasil memproses 36/36 foto ke `output_foto_fixed/`.
- Export tiga PDF contoh AXC, Wesel, dan Sinyal berhasil menghasilkan 30 foto.
- Batch export dari `input_pdf/` berhasil menghasilkan 81 foto tanpa status `failed` di log terbaru.

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
- [requirements.txt](requirements.txt)
- [edit_timemark.py](edit_timemark.py)
- [export_pdf_foto.py](export_pdf_foto.py)
- [ocr.py](ocr.py)
- [01-06-2026_PERAWATAN WESEL ELEKTRIK 2 MINGGUAN_Bogor (1).pdf](01-06-2026_PERAWATAN%20WESEL%20ELEKTRIK%202%20MINGGUAN_Bogor%20(1).pdf)

## Next Step

1. Uji lebih banyak foto dengan variasi latar watermark.
2. Uji `export_pdf_foto.py` pada PDF lain kalau ada layout baru yang agak beda.
3. Jika struktur output final sudah disepakati, pindahkan root dari `output_pdf_foto/` ke folder final.
4. Tambahkan mapping tanggal dari CSV jika tanggal target berbeda per file.
