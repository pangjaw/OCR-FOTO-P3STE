# Setup Project OCR Foto Timemark

Dokumen ini berisi tahap kerja dan tools yang dibutuhkan. Deskripsi tujuan project ada di `README.md`, sedangkan log harian dan status berada di dalam sistem Obsidian (`Dashboard.md` & `Notes/Daily/`).

## Aturan Dokumentasi

- `README.md`: tujuan dibuatnya project dan batasan bisnis.
- `setup.md`: tahap kerja, struktur folder, perintah, dan dependensi teknis.
- `Dashboard.md`: halaman indeks utama di Obsidian yang menghubungkan catatan status kerja.
- `Notes/Daily/`: log perkembangan harian yang diperbarui setiap ada perubahan (menggantikan `memory.md`).
- `Notes/Decisions/`: catatan keputusan teknis / arsitektur (ADR).

## Struktur Folder

```text
OCR-FOTO-P3STE/
  app.py                    # Server Web Lokal (Dashboard UI)
  edit_timemark_ide1.py     # Script utama edit watermark (4-Stage Priority)
  export_pdf_foto.py        # Script ekstraksi foto dari PDF
  extract_pdf_dates.py      # Script ekstraksi tanggal dari PDF target (02_pdf_target) -> date.txt
  scheduler.py              # Script penjadwalan Tim & waktu pengerjaan
  merge_pdf_foto.py         # Script penggabung foto baru ke PDF lama
  Dashboard.md              # Halaman indeks Obsidian
  README.md                 # Tujuan project & batasan
  setup.md                  # Panduan setup ini
  requirements.txt          # Dependensi Python

  templates/                # Halaman UI Dashboard Web
    index.html

  01_pdf_source/            # Folder PDF sumber untuk diekstrak fotonya (PDF 2026)
  02_pdf_target/            # Folder berisi PDF target (untuk diambil tanggal barunya) (PDF 2025)
  03_photos_export/          # Hasil ekstraksi PDF → foto per aset (folder kerja edit)
  04_photos_edited/          # Hasil edit foto timemark dengan Tim subfolder
  05_pdf_merged/             # Hasil akhir penggabungan PDF laporan baru

  Notes/                    # Obsidian vault
    Daily/                  #   Log harian
    Decisions/              #   ADR
    Templates/              #   Template catatan
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

### Opsi A: Alur Manual (Menentukan Tanggal Sendiri)
1. Jalankan script edit timemark:
   ```bash
   python edit_timemark_ide1.py
   ```
2. Isi lokasi folder input foto (misalnya `03_photos_export`) dan masukkan tanggal target secara manual (misal: `Sabtu, Apr 29 2025`).
3. Cek hasil revisi foto di dalam folder `04_photos_edited/`.

### Opsi B: Alur Otomatis (Mengambil Tanggal dari PDF Laporan)
1. Kumpulkan seluruh file PDF laporan target yang ingin direvisi tanggal fotonya ke dalam folder `02_pdf_target/`.
2. Jalankan script ekstraksi tanggal:
   ```bash
   python extract_pdf_dates.py
   ```
   Script ini akan memindai **Halaman Pertama (Halaman 1)** di setiap PDF target, mengekstrak tanggalnya menggunakan regex, menerjemahkannya ke format tanggal bahasa Indonesia singkat (contoh: `Senin, Jan 06 2025`), dan menyimpannya sebagai file `date.txt` di subfolder aset `03_photos_export/` yang sesuai secara otomatis.
3. Jalankan script edit timemark secara batch untuk seluruh folder:
   ```bash
   python edit_timemark_ide1.py
   ```
   Masukkan lokasi folder input: `C:\Users\dikarm\Documents\Server\OCR-FOTO-P3STE\03_photos_export`
   Masukkan tanggal baru: (Langsung tekan **Enter** / kosongkan, karena script akan otomatis memuat tanggal dari file `date.txt` yang ada di tiap subfolder aset).

### Opsi C: Menjalankan Untuk Folder Spesifik
Jika Anda hanya ingin memproses subfolder aset tertentu saja, gunakan parameter `--input` diikuti path folder aset tersebut:
```bash
python edit_timemark_ide1.py --input "03_photos_export/AXC/ZP 22A CLT"
```
*(Kosongkan tanggal baru jika ingin otomatis membaca file `date.txt` di dalam folder tersebut).*

### Opsi D: Menjalankan Lewat Web UI (Dashboard Terpadu)
1. Aktifkan virtual environment Anda dan pastikan dependensi terbaru terinstall:
   ```bash
   pip install -r requirements.txt
   ```
2. Jalankan aplikasi server web lokal:
   ```bash
   python app.py
   ```
3. Browser Anda akan terbuka secara otomatis ke alamat `http://localhost:5000`. Jika tidak, silakan buka browser secara manual dan ketik alamat tersebut.
4. Melalui Web UI Dashboard, Anda dapat:
   - Melihat dan merubah konfigurasi jalur folder input/output.
   - Memantau jumlah dan file PDF target yang terdeteksi di subfolder secara otomatis.
    - Menjalankan pemrosesan per tahap (Ekstraksi Foto, Edit Watermark, atau Gabung PDF) atau sekaligus ("Jalankan Semua Tahap").
    - Memantau log jalannya program secara real-time di area terminal dashboard.

### Opsi E: Alur Kerja Penjadwalan Tim (Time & Team Scheduling)
Untuk membagi pekerjaan pengeditan secara realistis ke dalam tim kerja (misal: Tim 1 & Tim 2) dengan rentang jam tertentu (contoh: 07:00 s.d 18:00) serta durasi pengerjaan per tipe aset, Anda dapat menggunakan alur berikut:
1. Buat jadwal pengerjaan tim terlebih dahulu:
   ```bash
   python scheduler.py --pdf-dir 02_pdf_target --photos-dir 03_photos_export --output schedule.json
   ```
   Perintah ini akan membaca PDF target secara berurutan, menghitung waktu mulai dan selesai untuk 3 foto dari setiap aset berdasarkan `asset_waktu_mapping.json` dan `data_acuan_tenaga_gabungan.json`, membagi rotasi kerja antara Tim 1 & Tim 2, serta menghasilkan file `schedule.json`.
2. Jalankan pengeditan watermark dengan parameter `--schedule`:
   ```bash
   python edit_timemark_ide1.py --input 03_photos_export --schedule schedule.json
   ```
   Script akan membaca `schedule.json`, mengambil stempel waktu (timestamp) unik untuk setiap foto dari jadwal, dan mengelompokkan output foto yang telah di-watermark ke dalam subfolder tim yang bersangkutan (misal: `04_photos_edited/Tim_1/` atau `04_photos_edited/Tim_2/`).
3. Gabungkan foto hasil edit tersebut kembali ke berkas PDF:
   ```bash
   python merge_pdf_foto.py --input 02_pdf_target --photos 04_photos_edited --output 05_pdf_merged --schedule schedule.json
   ```
   Script penggabung PDF akan mendeteksi opsi `--schedule`, mencari foto-foto hasil edit di subfolder flat per tim (misal `Tim_N/asset_type/detail/0.jpg`) sesuai pemetaan jadwal, dan menggabungkannya ke PDF target di folder output `05_pdf_merged/`.

---

## Detail Tahap Foto

Area yang diedit adalah baris tanggal pada watermark Timemark di pojok kiri bawah, misalnya:
```text
Jumat, Jul 03, 2026
```

Script `edit_timemark_ide1.py` mencari garis merah kiri bawah Timemark sebagai anchor (Red Guide). Jika anchor tidak ditemukan, script memakai koordinat fallback relatif terhadap ukuran foto.

Jika `--input` tidak diisi, script akan bertanya lokasi folder input. Jika `--date` tidak diisi dan tidak ada file `date.txt` di subfolder aset, script akan bertanya tanggal baru secara interaktif.

Contoh CLI tanpa prompt:
```bash
python edit_timemark_ide1.py --input "C:\...\OCR-FOTO-P3STE\03_photos_export" --date "Sabtu, Apr 29 2025"
```

Script membaca foto `.jpg`, `.jpeg`, dan `.png` sampai ke subfolder. Folder hasil output (`04_photos_edited`) akan dilewati supaya hasil edit lama tidak diproses ulang.

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
03_photos_export/
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
04_photos_edited/
  Tim_1/
    WESEL/
      W23A BOO/
        image.jpg
```

Output PDF:

```text
05_pdf_merged/
  01-06-2026_PERAWATAN WESEL ELEKTRIK 2 MINGGUAN_Bogor (1).pdf
```
```

Output foto dari PDF:

```text
03_photos_export/
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
