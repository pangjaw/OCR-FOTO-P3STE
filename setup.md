# Setup Project OCR Foto Timemark

Dokumen ini berisi tahap kerja dan tools yang dibutuhkan. Tujuan project ada di `README.md`, sedangkan catatan kegiatan harian ada di `memory.md`.

## Aturan Dokumentasi

- `README.md`: tujuan dibuatnya project.
- `setup.md`: tahap kerja, struktur folder, perintah, dan tools yang dibutuhkan.
- `memory.md`: update dari setiap kegiatan terhadap project.

## Struktur Folder Yang Disarankan

```text
OCR-FOTO-P3STE/
  README.md
  setup.md
  memory.md
  edit_timemark.py
  export_pdf_foto.py
  pdf_batch_timemark.py

  input_foto/                    # opsional untuk contoh lokal
    contoh_1.jpg
    contoh_2.jpg

  input_pdf/
    file_001.pdf
    file_002.pdf

  output_pdf/

  output_pdf_foto/

  logs/
    batch_log.csv
    pdf_photo_export_log.csv

  preview/
```

## Tools Yang Dibutuhkan

- Python 3.10 atau lebih baru.
- `numpy` untuk pemrosesan array gambar.
- `pillow` untuk membaca, membersihkan, dan menulis gambar.
- `pdfplumber` untuk membaca teks, posisi judul aset, label foto, dan posisi image object pada PDF.
- `pypdf` untuk export image object asli dari PDF jika diperlukan.
- `reportlab` atau `pymupdf` hanya jika nanti perlu membuat atau menyusun ulang PDF.

Dependensi minimal edit foto:

```bash
pip install numpy pillow
```

Dependensi inti project:

```bash
pip install -r requirements.txt
```

Dependensi untuk tahap PDF jika dipasang manual:

```bash
pip install pypdf pdfplumber
```

Dependensi opsional untuk eksperimen lain:

```bash
pip install opencv-python torch diffusers
```

## Setup Python

1. Cek versi Python:

```bash
python --version
```

2. Buat virtual environment:

```bash
python -m venv .venv
```

3. Aktifkan virtual environment di PowerShell:

```bash
.\.venv\Scripts\Activate.ps1
```

4. Upgrade pip:

```bash
python -m pip install --upgrade pip
```

5. Instal dependensi project:

```bash
pip install -r requirements.txt
```

## Tahap Kerja

1. Siapkan folder foto asli. Folder boleh berada di mana saja dan boleh punya subfolder.
2. Jalankan edit foto tahap 1:

```bash
python edit_timemark.py
```

3. Saat diminta, isi lokasi folder input dan tanggal baru.
4. Cek hasil di `<folder input>/Export_Foto/` dan preview beberapa sampel.
5. Kalibrasi jika posisi watermark berbeda jauh dari contoh.
6. Setelah hasil foto stabil, lanjut tahap PDF sesuai kebutuhan:
   - `pdf_batch_timemark.py` untuk edit tanggal pada foto di dalam PDF.
   - `export_pdf_foto.py` untuk mengambil foto dokumentasi dan mengelompokkannya per aset.
7. Uji PDF contoh, render preview halaman hasil, lalu baru jalankan batch.
8. Simpan log perubahan di `logs/batch_log.csv` atau `logs/pdf_photo_export_log.csv`.

## Detail Tahap Foto

Area yang diedit cukup baris tanggal, misalnya:

```text
Jumat, Jul 03, 2026
```

Script `edit_timemark.py` mencari garis merah kiri bawah Timemark sebagai anchor. Jika anchor tidak ditemukan, script memakai koordinat fallback relatif terhadap ukuran foto.

Jika `--input` tidak diisi, script akan bertanya lokasi folder input. Jika `--date` tidak diisi, script akan bertanya tanggal baru.

Contoh tanpa prompt:

```bash
python edit_timemark.py --input "D:\Foto Timemark" --date "Sabtu, Agt 02 1999"
```

Script membaca foto `.jpg`, `.jpeg`, dan `.png` sampai ke subfolder. Folder bernama `Export_Foto` akan dilewati supaya hasil export lama tidak diproses ulang.

## Detail Tahap PDF

Alur edit tanggal pada foto dalam PDF:

```text
PDF asli
-> cari foto pada halaman
-> ekstrak atau akses image object
-> edit tanggal pada foto
-> pasang kembali ke PDF
-> simpan PDF revisi
-> tulis log perubahan
```

## Detail Tahap Export Foto PDF

Alur export foto dokumentasi dari PDF:

```text
PDF asli
-> hitung jumlah halaman
-> mulai scan dari halaman 2 sampai halaman terakhir
-> cari judul aset dengan pola WSLxxxxx : PENGGERAK WESEL ...
-> ambil foto dokumentasi di bawah judul aset
-> cocokkan urutan foto dengan label Foto 0%, Foto 50%, Foto 100%
-> export foto asli dari PDF
-> simpan ke folder sesuai aset
-> tulis log export
```

Script yang dipakai: `export_pdf_foto.py`.

Halaman 1 tidak discan untuk judul aset karena biasanya berisi daftar aset dan bisa menyebabkan false positive.

Contoh kelompok:

```text
WSL11080 : PENGGERAK WESEL W23A BOO
WSL11079 : PENGGERAK WESEL W43 BOO
```

Contoh output:

```text
output_pdf_foto/
  WESEL/
    W23A BOO/
      0.jpg
      50.jpg
      100.jpg
```

Nama file memakai angka persen tanpa karakter `%`, supaya aman di Windows dan command line.

## Mapping Tanggal

Pilihan sederhana: ambil tanggal dari nama file PDF.

```text
01-06-2026_PERAWATAN WESEL ELEKTRIK 2 MINGGUAN_Bogor (1).pdf
```

Tanggal target:

```text
Senin, Jun 01, 2026
```

Pilihan fleksibel: pakai CSV.

```csv
file,tanggal_baru
file_001.pdf,"Senin, Jun 01, 2026"
file_002.pdf,"Selasa, Jun 02, 2026"
```

## Format Output

Jangan menimpa file asli.

Output foto:

```text
root_folder_input/
  Export_Foto/
    subfolder_asli/
      image.jpg
```

Output PDF:

```text
output_pdf/
  01-06-2026_PERAWATAN WESEL ELEKTRIK 2 MINGGUAN_Bogor (1)_revisi.pdf
```

Output foto dari PDF:

```text
output_pdf_foto/
  WESEL/
    W23A BOO/
      0.jpg
      50.jpg
      100.jpg
```

Log:

```csv
file,page,photo_index,old_date,new_date,status
```

Log export foto PDF:

```csv
pdf,page,asset_code,asset_name,label,image_name,output_file,status
```

## Cek Kualitas

1. Bekas tanggal lama tidak terlalu terlihat.
2. Tanggal baru sejajar dengan posisi Timemark asli.
3. Ukuran font tidak terlalu besar atau kecil.
4. Warna dan shadow teks terlihat natural.
5. File hasil tetap tajam dan tidak rusak layout.
6. Untuk export PDF, setiap folder aset idealnya berisi 3 foto: 0%, 50%, dan 100%.
