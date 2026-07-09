# 🧪 Catatan Hasil Uji Coba (Test Results)

Catatan hasil pengetesan script `edit_timemark.py` dan `export_pdf_foto.py` dari waktu ke waktu.

---

## 📈 Rekap Uji Coba Terbaru

### 📅 Uji Coba 2026-07-09

#### Pemrosesan Foto Timemark (`edit_timemark_ide1.py`)
- **Implementasi Ide 1 (Y-center average)**: Uji coba pemosisian vertikal watermark menggunakan rata-rata koordinat tengah dari kata-kata yang dideteksi oleh Tesseract. Mengatasi pergeseran kotak watermark akibat bounding box Tesseract yang melebar secara vertikal.
- **Pelebaran Jangkauan Tahun**: Memperluas deteksi tahun ke rentang 2001–2999 dengan regex `20\d{2}` untuk menangkap tahun yang tergabung akibat noise OCR (misalnya `2026` dibaca `832006`). Terbukti sukses pada berkas `LANGSIR L20 BOO/50.jpg`.
- **Pembersihan Kata Kunci Bahasa Inggris**: Menghapus singkatan Inggris (`MAY`, `AUG`, `OCT`, `DEC`) untuk menghindari kecocokan palsu pada kawat pagar/tiang latar belakang (misalnya `"May,"` dibaca pada `JL32A BOO/50.jpg`).
- **Integrasi Adaptive Thresholding (BoxBlur)**: Menambahkan binarisasi adaptif lokal (`BoxBlur(8)` + offset `C = -8` + penajaman) sebagai pertahanan terakhir OCR. Berhasil mengisolasi teks putih pada tembok beton/semen abu-abu dan peron diagonal stasiun pada berkas `ZP 21A BOO/100.jpg`.
- **Uji Kelulusan Batch (168/168)**: Pemrosesan ulang seluruh folder input menghasilkan kelulusan mutlak dengan visualisasi rapi tanpa ada bocoran teks lama di foto mana pun.

### 📅 Uji Coba 2026-07-08

#### Pemrosesan Foto Timemark (`edit_timemark.py`)
- **Uji Recursive Subfolder**: Berhasil memproses subfolder uji `tmp/test_recursive/` dan mengeluarkan output ke `tmp/test_recursive/Export_Foto/WESEL/W23A BOO/0.jpg` dengan tetap mempertahankan struktur folder asli.
- **Uji Batch Foto (45/45)**: Berhasil memproses 45 foto berukuran 300x300 ke `output_foto/`. Sizing font, padding, shadow, dan radius hitam adaptif berfungsi dengan baik.
- **Uji Ringan Blur**: Pengurangan intensitas blur pada proses pembersihan teks lama diuji pada 45/45 foto dan memberikan hasil yang jauh lebih natural/tidak terlalu kabur.
- **Uji Fallback Posisi**: Anchor fallback diperbaiki sehingga pada foto 300x300 tanpa garis merah/oranye Timemark yang jelas, posisi tanggal tidak menimpa logo KAI (turun sedikit di atasnya).
- **Uji Folder PDF Exported (3/3)**: Berhasil memproses folder `WESEL/PENGGERAK WESEL W43 BOO` di `output_pdf_foto/` dengan tanggal target `Senin, Jun 01, 2026`.

#### Ekstraksi PDF (`export_pdf_foto.py`)
- **Uji Kualitas Image**: Sampel gambar diekstrak langsung dari bytes JPEG asli pada PDF Wesel (15 foto berukuran 300x300). Hash sampel output terbukti identik dengan file biner di dalam PDF (100% lossless).

---

### 📅 Uji Coba 2026-07-07

#### Pemrosesan Foto Timemark (`edit_timemark.py`)
- **Uji Batch Awal (36/36)**: Berhasil memproses 36/36 foto ke `output_foto_fixed/` setelah perbaikan toleransi deteksi anchor warna oranye logo KAI dan oranye/merah Timemark.

#### Ekstraksi PDF (`export_pdf_foto.py`)
- **Uji Contoh PDF Awal**: Ekstraksi dari 3 contoh PDF (AXC, Wesel, Sinyal) berhasil mengekstrak total 30 foto.
- **Uji Batch PDF (`input_pdf/`)**: Berhasil mengekstrak total 81 foto tanpa ada kegagalan (`failed` status) di log.
