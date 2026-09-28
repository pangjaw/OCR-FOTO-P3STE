# ADR-016: Isolasi Edit Teks Foto Tunggal, Inline Timemark Editing, dan Interaksi Galeri Modern

- **Status:** Diterima & Aktif (Accepted)
- **Tanggal:** 2026-09-20
- **Pengambil Keputusan:** Tim Pengembang & Tim Operasional STE
- **Konsultasi Terkait:** [[Notes/Decisions/Active Pipeline Rules]], [[Notes/Decisions/Bug Fix History]], [[ARCHITECTURE]], [[Dashboard]]

---

## 1. Konteks & Latar Belakang Masalah

Pada modul Galeri Foto hasil proses (`04_photos_edited`), pengguna membutuhkan fleksibilitas penuh dalam mengoreksi tanggal, jam, maupun posisi teks watermark timemark pada masing-masing foto. Namun, ditemukan sejumlah kendala mendasar:

1. **Efek Samping Tombol Edit Teks (Side-Effect Collision):**
   Saat pengguna menekan tombol **"✏️ Edit Teks"** pada salah satu foto (misalnya hanya ingin mengoreksi jam pada `0.jpg`), sistem di backend secara otomatis memproses ulang seluruh foto di dalam folder tersebut (`0.jpg`, `50.jpg`, dan `100.jpg`), serta menimpa tanggal/jam foto saudara dengan perhitungan jam otomatis (`helperCalculateDate`). Akibatnya, jam yang sudah benar pada foto `50.jpg` atau `100.jpg` menjadi rusak atau tergeser tanpa persetujuan pengguna.
2. **Masalah Popover Terpotong (*Overflow Clipping*):**
   Popover edit cepat sebelumnya disematkan langsung di dalam kotak foto `.img-box` yang memiliki properti CSS `overflow: hidden`. Karena posisi timemark berada di bagian bawah foto (Y ≈ 73%), separuh bagian bawah popover (termasuk kotak centang dan tombol aksi) terpotong dan tidak dapat dijangkau oleh pengguna pada berbagai resolusi layar.
3. **Kebutuhan Interaksi Cepat di Lapangan:**
   - Menghilangkan proses pembukaan modal slider yang lambat dan berat untuk perbaikan posisi harian.
   - Kebutuhan memperbesar (zoom) foto secara mendetail untuk memeriksa kualitas pekerjaan teknisi sebelum disatukan ke dokumen PDF.
   - Kebutuhan menukar posisi foto yang tertukar (misal teknisi salah memposisikan foto 0% dan 100%) langsung dari antarmuka galeri tanpa membuka Windows Explorer.

---

## 2. Keputusan Desain & Arsitektur

### A. Kontrak Isolasi Edit Teks Foto Tunggal (Backend `server.js`)
Pada endpoint `POST /api/photos/manual-edit`, diberlakukan pemisahan tegas antara **Edit Teks** dan **Penggeseran Koordinat**:

1. **Deteksi Aksi:**
   - Parameter `isTextEdit: true` secara eksplisit dikirim dari antarmuka jika pengguna sedang mengubah teks tanggal/jam.
2. **Evaluasi Penerapan ke Folder (`shouldApplyToAll`):**
   ```javascript
   let shouldApplyToAll = false;
   if (isTextEdit === true) {
     // Edit teks HANYA berlaku ke semua foto jika checkbox dicentang sengaja
     shouldApplyToAll = (applyDateToFolder === true);
   } else {
     // Penggeseran koordinat mengikuti status sinkronisasi posisi grup
     shouldApplyToAll = (applyToFolder === true);
   }
   ```
3. **Penyempitan Target Berkas:**
   - Jika `shouldApplyToAll === false`, sistem secara ketat menetapkan `targetRelPaths = [normalizedRel]`.
   - Skrip Python (`edit_timemark_ide1.py`) **hanya dipanggil satu kali untuk berkas target**.
   - Berkas saudara di folder yang sama sama sekali tidak dipanggil ulang oleh Python, tidak mengalami penulisan disk, dan datanya di `meta.json` dipertahankan 100% utuh.
4. **Penerapan Multi-Foto Eksplisit (Jika Dicentang):**
   - Jika `applyDateToFolder === true`, sistem memproses seluruh foto dengan kalkulasi jam bertahap:
     - `0%` (0.jpg): Jam acuan awal (misal `08:00`).
     - `50%` (50.jpg): Jam acuan + 22 menit (`08:22`).
     - `100%` (100.jpg): Jam acuan + 45 menit (`08:45`).

### B. Dialog Modal Dedicated `#inlineTextModal` (Frontend `templates/index.html`)
1. Mengganti popover terpotong dengan dialog modal mandiri di lapisan teratas (`z-index: 99999`) yang berada langsung di bawah `<body>`.
2. Menampilkan informasi kontekstual yang jelas:
   - Nama jalur relatif berkas foto (misal `BTP JAK/WESEL/W11 CLT_03-06/0.jpg`).
   - Label tim kerja (`Tim_1` / `Tim_2`).
   - Input teks tanggal dan jam yang otomatis terfokus dan terseleksi saat modal terbuka.
   - Checkbox persetujuan:
     `[ ] Terapkan perubahan teks ini ke seluruh foto (0, 50, 100)` dengan status baku **TIDAK DICENTANG (FALSE)**.
3. Aksesibilitas Keyboard:
   - Tombol `Enter`: Langsung mengeksekusi penyimpanan.
   - Tombol `Escape`: Membatalkan dan menutup modal seketika.

### C. Inline Timemark Editing (Draggable Box)
1. Setiap kartu foto dilengkapi elemen visual `.inline-timemark-box` transparan biru yang menempel langsung di atas foto asli.
2. Pengguna dapat menggeser posisi kotak secara instan menggunakan mouse atau sentuhan pointer.
3. Saat pointer dilepas (`pointerup`), sistem otomatis:
   - Mengonversi koordinat layar ke skala normalisasi (0..300).
   - Memanggil `POST /api/photos/manual-edit` di latar belakang tanpa reload halaman.
   - Memberikan umpan balik kilatan hijau lembut (`saved-flash`).
   - Memperbarui gambar hasil editan di sisi kanan kartu dengan cache-busting timestamp.
   - Menghilangkan badge `⚠️ Perlu Koreksi` secara otomatis.

### D. Fitur Zoom Interaktif (Lightbox Modal) & Drag-and-Drop Swap
1. **Zoom Interaktif:**
   - Mengklik foto asli maupun foto editan membuka viewer resolusi penuh.
   - Mendukung kontrol perbesaran (`+`, `-`, `Fit`, `1:1`), scroll wheel mouse zoom, dan drag-to-pan saat diperbesar.
2. **Tukar Foto Antar-Kartu (Swap):**
   - Pengguna dapat menyeret foto dari satu kartu dan menjatuhkannya ke kartu lain.
   - Backend `POST /api/photos/swap` memanggil `scripts/replace_export_photo.py --action swap` untuk menukar berkas asli di `03_photos_export`, membuat backup otomatis, mereset cache crop, dan menjalankan ulang pemrosesan Step 4.

---

## 3. Hasil Pengujian & Verifikasi

Pengujian terotomatisasi dilakukan langsung pada folder aktif `04_photos_edited/Tim_1/BTP JAK/WESEL/W11 CLT_03-06`:

| Skenario Pengujian | Parameter | Hasil 0.jpg | Hasil 50.jpg | Hasil 100.jpg | Kesimpulan |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Edit Teks Foto Tunggal (0.jpg)** | `isTextEdit: true`, `applyDateToFolder: false` | **CHANGED** (`07:05`) | **UNCHANGED** | **UNCHANGED** | ✅ Lulus (100% terisolasi) |
| **Edit Teks Foto Tunggal (50.jpg)** | `isTextEdit: true`, `applyDateToFolder: false` | **UNCHANGED** | **CHANGED** (`08:35`) | **UNCHANGED** | ✅ Lulus (100% terisolasi) |
| **Terapkan ke Seluruh Foto** | `isTextEdit: true`, `applyDateToFolder: true` | **CHANGED** (`08:00`) | **CHANGED** (`08:23`) | **CHANGED** (`08:45`) | ✅ Lulus (Kalkulasi jam benar) |

---

## 4. Dampak Operasional

1. **Bebas Galat Sampingan:** Teknisi dan operator kini bebas mengoreksi teks tanggal/jam pada foto individual tanpa khawatir merusak jam foto lainnya dalam aset tersebut.
2. **Kenyamanan Visual:** Antarmuka modal edit teks tidak lagi terpotong dan dapat diakses dengan nyaman pada layar monitor standar maupun laptop berlayar kecil.
3. **Produktivitas Tinggi:** Koreksi posisi dan teks dapat dilakukan langsung dari tampilan galeri dalam hitungan detik tanpa membuka berkas fisik di sistem operasi.
