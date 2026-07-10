# 🏛️ Arsitektur & Diagram Sistem Kerja `merge_pdf_foto.py`

Dokumen ini menjelaskan alur kerja dan arsitektur pemrosesan dari skrip [merge_pdf_foto.py](file:///c:/Users/dikarm/Documents/Server/OCR-FOTO-P3STE/merge_pdf_foto.py) yang digunakan untuk menggabungkan foto-foto dokumentasi baru (format 2026) ke dalam berkas laporan PDF lama (format 2025).

---

## 📊 Diagram Alur Pemrosesan (Flowchart)

Berikut adalah diagram alur logis yang menunjukkan bagaimana skrip memilah dokumen, mengekstrak data, melakukan validasi, dan membangun halaman dokumentasi baru:

```mermaid
flowchart TD
    %% Styling
    classDef startEnd fill:#f9f,stroke:#333,stroke-width:2px,color:#000;
    classDef process fill:#bbf,stroke:#333,stroke-width:1px,color:#000;
    classDef decision fill:#ff9,stroke:#333,stroke-width:1px,color:#000;
    classDef database fill:#dfd,stroke:#333,stroke-width:1px,color:#000;

    start([Mulai Program]):::startEnd
    read_folder[Pindai folder pdf_imo]:::process
    loop_pdf{Untuk Setiap PDF asli}:::decision
    
    %% Input databases
    pdf_imo[(pdf_imo/ - PDF 2025 asli)]:::database
    export_foto[(Export_Foto/ - Foto hasil edit)]:::database
    
    %% Steps
    parse_pdf[Buka dengan pdfplumber]:::process
    extract_meta[Ekstrak Metadata Page 1:\n1. Tanggal Laporan\n2. Judul Ceklis Dinamis\n3. Nama Lokasi\n4. Daftar Aset]:::process
    
    check_photos{Semua 3 Foto\n0%, 50%, 100%\ntersedia di\nExport_Foto?}:::decision
    
    skip_pdf[Log SKIP & Warning:\nLewati berkas PDF ini]:::process
    
    open_fitz[Buka dengan PyMuPDF/fitz]:::process
    del_page[Hapus Halaman Terakhir\n- Halaman Kolase 2025 lama]:::process
    
    loop_assets{Loop Aset\nmulai k = 0}:::decision
    
    need_page{k % 4 == 0?}:::decision
    create_page[Buat Halaman A4 baru]:::process
    draw_header[Gambar Header Halaman:\n- FOTO DOKUMENTASI\n- JUDUL + LOKASI\n- TANGGAL LAPORAN]:::process
    
    draw_asset[Gambar Baris Aset:\n1. Judul Aset\n2. Tempel 3 Foto\n3. Gambar Label Foto]:::process
    
    save_pdf[Simpan PDF hasil ke\nhasil_gabung/output/]:::process
    
    done([Selesai]):::startEnd

    %% Connections
    start --> read_folder
    pdf_imo -.-> read_folder
    read_folder --> loop_pdf
    
    loop_pdf -- "Ada PDF" --> parse_pdf
    parse_pdf --> extract_meta
    extract_meta --> check_photos
    export_foto -.-> check_photos
    
    check_photos -- "Tidak Lengkap" --> skip_pdf
    skip_pdf --> loop_pdf
    
    check_photos -- "Lengkap" --> open_fitz
    open_fitz --> del_page
    del_page --> loop_assets
    
    loop_assets -- "Aset k" --> need_page
    need_page -- "Ya" --> create_page
    create_page --> draw_header
    draw_header --> draw_asset
    
    need_page -- "Tidak" --> draw_asset
    draw_asset --> loop_assets
    
    loop_assets -- "Selesai semua aset" --> save_pdf
    save_pdf --> loop_pdf
    
    loop_pdf -- "Semua PDF Selesai" --> done
```

---

## 🛠️ Komponen Utama Sistem Kerja

### 1. **Parser & Detektor Dinamis (`pdfplumber`)**
Mengambil informasi dari berkas PDF input tanpa berasumsi format tanggal atau judulnya statis:
- **Nama Lokasi**: Diekstrak dari nama berkas PDF (contoh: `..._Cilebut-Bogor (2).pdf` $\rightarrow$ `CILEBUT-BOGOR`).
- **Judul Ceklis**: Dicari baris pada Halaman 1 yang memiliki kata kunci `"PERAWATAN"` (contoh: `PERAWATAN AXLE COUNTER SIEMENS 1 BULANAN` atau `PERAWATAN WESEL ELEKTRIK 2 MINGGUAN`).
- **Tanggal Laporan**: Dicari dari kolom `Tanggal : YYYY-MM-DD` dan diterjemahkan ke format Indonesia.
- **Identifikasi Aset**: Mencari baris kode aset seperti `AXL11468` dan detail namanya (`ZP 60 BOO`) dengan mengabaikan baris komparasi/palsu di bagian bawah halaman.

### 2. **Pencocokan & Proteksi Foto (Option B)**
Skrip menuntut kelengkapan mutlak berkas gambar sebelum mengubah PDF:
- Menghubungkan nama detail aset dengan direktori penyimpanan foto hasil edit: `output_pdf_foto/Export_Foto/[ASSET_TYPE]/[DETAIL_ASSET]/`.
- Skrip memverifikasi keberadaan berkas `0.jpg`, `50.jpg`, dan `100.jpg`.
- **Jika ada satu saja aset yang kekurangan foto**, pemrosesan berkas PDF tersebut langsung dihentikan secara aman untuk menghindari hilangnya data dokumentasi, lalu skrip melompat ke berkas PDF berikutnya.

### 3. **Penyusun Layout PDF (`fitz` / PyMuPDF)**
Merekondisi halaman PDF secara langsung tanpa *rendering* gambar yang menurunkan kualitas:
- **Penghapusan Kolase Lama**: `doc.delete_page(-1)` memotong halaman terakhir PDF yang berisi kolase foto format 2025.
- **Pembuatan Halaman Baru**: Menghasilkan halaman A4 kosong (`595 x 842` pt).
- **Penataan Grid Baris & Kolom**:
  - Judul aset ditaruh di sisi kiri atas setiap baris.
  - Gambar ditempel secara horizontal di X = `31.5`, `210.4`, dan `389.8` dengan ukuran `148.8 x 148.8` pt.
  - Skrip menghitung secara dinamis titik tengah kolom gambar untuk menempatkan label `Foto 0%`, `Foto 50%`, dan `Foto 100%` agar simetris di bawah foto.
  - Skrip mengalirkan baris aset secara dinamis (maksimal 4 aset per halaman). Jika terdapat 5 aset, skrip otomatis membuat 2 halaman dokumentasi foto baru.
