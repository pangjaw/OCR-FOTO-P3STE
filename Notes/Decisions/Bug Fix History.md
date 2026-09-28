# Bug Fix History

Catatan ini menjadi rujukan utama untuk memahami bug lama, penyebabnya, perbaikan, dan status terakhirnya.

## 1. Satu PDF terbagi ke dua Tim — 2026-07-17

- **Masalah:** satu PDF yang berisi beberapa aset dapat masuk ke Tim 1 dan Tim 2.
- **Penyebab:** batas jam diperiksa setelah setiap aset, bukan setelah semua aset dalam PDF selesai.
- **Perbaikan:** overflow dipindahkan ke tingkat PDF.
- **Aturan hasil:** semua aset dalam satu PDF tetap berada di satu Tim; Tim berikutnya baru dipakai untuk PDF berikutnya.
- **Hasil validasi:** 0 PDF mixed Tim pada run historis.

## 2. Bentrok tanggal, jam, dan asset ganda — 2026-08-05

- **Masalah:** PDF diurutkan berdasarkan nama file, state jam antar tanggal bercampur, tanggal bisa bergeser saat overflow, dan asset yang sama bisa mendapat jadwal ganda.
- **Perbaikan:** PDF diurutkan berdasarkan tanggal target, state jadwal dipisahkan per tanggal, asset dideduplikasi berdasarkan `(btp, category, identifier, date)`, dan tanggal tidak digeser karena overflow.
- **Hasil historis:** 398 asset unik dan 0 collision waktu.
- **Catatan:** jangan mengganti implementasi historis dengan schema baru sebelum membandingkan kode aktif dan catatan validasinya.

## 3. Collision lookup Tim 2 — 2026-07-17

- **Masalah:** identifier yang muncul di beberapa PDF mengalami bentrok karena lookup memakai key flat.
- **Dampak:** sebagian foto Tim 2 terbaca sebagai Tim 1.
- **Perbaikan historis:** jadwal dengan Tim lebih tinggi diprioritaskan; output lama dibersihkan dan diverifikasi ulang.

## 4. Posisi tanggal manual

- **Sumber posisi:** `04_photos_edited/**/meta.json` menyimpan `initial`, `manualEdit`, `xPos`, `yPos`, dan `latestUserCorrection`.
- **Aturan:** proses ulang Step 4 harus mempertahankan posisi manual dan hanya memperbarui isi tanggal/jam dari jadwal.
- **Pengamanan:** jangan menghapus hasil lama sebelum backup atau manifest dibuat.

## 5. Routing BTP salah untuk JPL BOO-BOP — 2026-08-14

- **Masalah:** `JPL 04 BOO-BOP`, `JPL 07 BOO-BOP`, dan `JPL BNR BOO-BOP` masuk BTP JAK.
- **Penyebab:** sistem membaca kode pertama `BOO`, lalu memakai aturan `BOO → BTP JAK`.
- **Perbaikan:** semua `JPL ... BOO-BOP` diperiksa lebih dahulu dan diarahkan ke `BTP BD`.
- **File yang diperbarui:** `scripts/scheduler.py`, `scripts/export_pdf_foto.py`, dan `schedule.json`.
- **Hasil:** folder aktif berada di BTP BD; salinan lama dipindahkan atau dikarantina secara reversible.
- **Manifest:** `logs/jpl_boo_bop_btp_move_20260814.json` dan `logs/jpl_boo_bop_quarantine_20260814_0034.json`.
- **Status:** routing dan syntax sudah divalidasi; Step 4 dan Step 5 penuh belum dijalankan ulang.

## 6. Auto-Crop Kolase & Koreksi Crop Web UI — 2026-08-15

- **Masalah:**
  - Foto kolase 2x2 dan 3-in-1 memiliki tulisan timemark yang sangat kecil dan buram saat ditempel watermark baru.
  - Skrip pemotong manual `manual_crop_helper.py` memotong path secara keliru saat dipanggil dengan path absolut Windows sehingga file hasil crop tersimpan di root tanpa folder aset.
  - Pada Step 4 (`edit_timemark_ide1.py`), foto kolase cropped yang tidak memiliki guideline oranye di kuadran terpilih masuk ke `stage_fallback` dan menyalin file mentah Folder 3 (foto kolase utuh) ke Folder 4 tanpa pemotongan dan tanpa timemark.
  - Panggilan CLI untuk edit manual 1 file gagal mengenali path absolut sehingga proses dilewati (*skipped*).
- **Perbaikan:**
  - Menerapkan algoritma isolasi garis pembatas putih (*white-seam isolation*) di `scripts/auto_crop_collages.py` (15 kolase terpotong rapi, 0 false positive pada 1.401 foto tunggal).
  - Memperbaiki parsing path relatif berbasis `.resolve()` dan `.parts` di `manual_crop_helper.py` dan `edit_timemark_ide1.py`.
  - Memperbaiki kondisi fallback di `edit_timemark_ide1.py` agar foto kolase cropped selalu memuat `03_photos_cropped_temp` dan menempelkan timemark standar (`y=220`).
  - Menambahkan header `no-store/no-cache` di `server.js` dan menghapus semua popup `alert/confirm` yang mengganggu.
- **Hasil:**
  - 1.416 / 1.416 foto di `04_photos_edited` berhasil 100% diproses (0 skipped, 0 failed).
  - Tampilan kartu Folder 4 dan editor timemark manual sinkron secara presisi.

## 7. Aturan tindak lanjut

Saat menemukan bug lama, baca catatan ini sebelum membuat perubahan baru. Setelah behavior berubah, catat tanggal, penyebab, perbaikan, validasi, dan status tindak lanjut.

## 8. Sinkronisasi Routing Wilayah BTP BD untuk Serat Optik — 2026-09-12

- **Masalah:** Berkas Serat Optik BTP BD (seperti `JPL 04 BOO-BOP`, `JPL 07 BOO-BOP`, `JPL BNR BOO-BOP`, dan OTB dengan nama stasiun lengkap seperti `OTB CIOMAS`, `OTB BATU TULIS`, `OTB CIGOMBONG`, `OTB MASENG`) masuk ke folder `BTP JAK` di `05_pdf_merged` atau terjadwal ke `BTP JAK` di `schedule.json`.
- **Penyebab:**
  1. Pada `scripts/merge_pdf_foto.py`, fungsi `determine_btp_from_identifier()` membaca stasiun pertama JPL (`BOO`), sehingga `BOO-BOP` diarahkan ke `BTP JAK`.
  2. Pada `scripts/scheduler.py`, fungsi `_determine_btp()` hanya mencocokkan singkatan 3 huruf dan tidak mendukung nama stasiun lengkap, sehingga nama seperti `CIOMAS` jatuh ke fallback `BTP JAK`.
- **Perbaikan:**
  - Menstandarkan fungsi penentuan wilayah menjadi fungsi tunggal canonical `determine_btp(text, fallback_text)` di `scripts/export_pdf_foto.py`.
  - Pola BTP BD diprioritaskan terlebih dahulu: rute lintas stasiun (`BOO-BOP`, `BOP-BTT`), kode stasiun (`BOP`, `BTT`, `CGB`, `COS`, `CS`, `MSG`, `CCR`, `BNR`), dan nama lengkap stasiun (`BATU TULIS`, `CIOMAS`, `MASENG`, `CIGOMBONG`, `CICURUG`, `BOGOR PALEDANG`).
  - Mengintegrasikan `determine_btp` ke dalam `scripts/merge_pdf_foto.py` dan `scripts/scheduler.py` dengan fallback ke nama file PDF (`pdf_path.name`).
- **Hasil Validasi:**
  - Seluruh 28 file target Serat Optik 100% konsisten antara Step 1, Step 3, dan Step 5 (0 mismatch).
  - Seluruh 431 dokumen target PDF 100% konsisten antar seluruh langkah pipeline (0 mismatch, 0 unknown).

## 9. Penanganan Mode & Folder Fallback pada Single-PDF Re-Merge dari Koreksi Kolase — 2026-09-13

- **Masalah:** Saat melakukan remerge dari modal Koreksi Kolase (Potong & Re-Merge) pada berkas `PERAWATAN CATU DAYA ER SINYAL BOO 08-03-2026.pdf`, muncul error: `failed: no matching edited photos found in 04_photos_edited; output Tim cannot be determined`.
- **Penyebab:**
  1. Pada `templates/index.html` fungsi `executeManualCropAndRemerge()`, pemanggilan `remergePhotoPdf()` memiliki mode `'standard'` yang ter-hardcode, sehingga saat pengguna sedang berada di tab Edit Jam (`04_Time`), skrip merge tetap mencari foto di folder `04_photos_edited` yang belum memuat aset tersebut.
  2. Pada `scripts/edit_timemark_ide1.py`, fungsi `_read_date_txt` melakukan duplikasi sub-path saat argumen `--input` berupa folder aset parsial (`03_photos_export/BTP JAK/CATUDAYA/BOO`), sehingga pembuatan foto bertimemark di `04_photos_edited` terlewat.
  3. Pada `server.js` endpoint `/api/pdf/remerge-single`, belum ada mekanisme cerdas auto-switch dan fallback antar folder `04_photos_edited` dan `04_Time` jika salah satu folder belum memiliki foto bertimemark.
- **Perbaikan:**
  - `templates/index.html`: `executeManualCropAndRemerge()` mendeteksi mode aktif (`'time'` vs `'standard'`) secara dinamis berdasarkan data foto dan active tab `timeTab`. `openManualCropModal()` mempertahankan flag `isTime`.
  - `scripts/edit_timemark_ide1.py`: `_read_date_txt` mendukung beragam kandidat path (`DEFAULT_INPUT`, direct `input_dir / "date.txt"`, dan `input_dir / btp / category / identifier / "date.txt"`).
  - `scripts/merge_pdf_foto.py`: Pesan kegagalan dan log diperbarui agar dinamis mengikuti nama `photos_dir.name`.
  - `server.js`: `/api/pdf/remerge-single` dilengkapi helper `checkPhotosExistForRel()`, otomatis beralih mode (`auto-switch`) jika foto ditemukan di folder alternatif, serta fallback otomatis jika percobaan utama melaporkan foto belum ada di folder tujuan. Format error disederhanakan dalam bahasa Indonesia yang mudah dipahami.
- **Hasil Validasi:**
  - Pengujian `POST /api/pdf/remerge-single` pada `PERAWATAN CATU DAYA ER SINYAL BOO 08-03-2026.pdf` berhasil 100% baik pada Mode Standar (`05_pdf_merged`) maupun Mode Time (`05_pdf_merged_Time`) dalam ~2.8 detik (`status: ok`).
  - Pengujian via `rawRelPath` foto berhasil mendeteksi dokumen target secara akurat.

## 10. Penyelarasan Penuh Baris Header & Standarisasi Penamaan Berkas Excel Tablo — 2026-09-13

- **Masalah:**
  1. Blok pengesahan "dibuat oleh : (Kepala Urusan Preventif)" berada salah posisi di atas kolom personil (G4:J6), terpotong menjadi 3 baris kecil dengan garis sekat horizontal, tidak memiliki ruang tanda tangan fisik basah, dan barisnya tidak sejajar dengan baris `WAKTU` dan nama personil di sisi kiri.
  2. Format nama file keluaran tidak terstandar dan sempat menggunakan ekstensi kapital (`.XLSX`), serta tertahan oleh sistem *case-preservation* Windows NTFS.
- **Penyebab:**
  1. Pemetaan baris header di `scripts/export_tablo_excel.py` menempatkan `WAKTU` di Baris 7 sedangkan `dibuat oleh :` di Baris 4, sehingga matriks kiri dan kanan tidak seimbang secara horizontal.
  2. Kotak tanda tangan pengesahan belum dibuat dalam satu range sel utuh tanpa garis sekat dalam (*no internal horizontal divider*).
  3. File lama dengan nama kapital tidak dihapus sebelum penulisan baru sehingga Windows mempertahankan nama lama.
- **Perbaikan:**
  - **Penyelarasan Baris Horizontal (Row-level sync)**:
    - **Baris 4 (18 pt)**: `WAKTU` (Kolom A..C, hijau muda `#C6E0B4`), pita kuning personil (Kolom D..J, `#FFE599`), dan `dibuat oleh :` (Kolom L..S, biru muda `#B4C6E7`) 100% sejajar.
    - **Baris 5 (68 pt)**: Kolom waktu vertikal (`BULAN`, `HARI`, `TANGGAL`), nama 7 personil aktif (`FURQON SUSILO` s.d. `RAIHAN HERPIAN`), dan kotak tanda tangan pengesahan (`Kepala Urusan Preventif` + ruang tanda tangan luas + `Yatiyo / Nipp. 49957`) 100% sejajar tanpa garis pembatas di tengahnya.
    - **Baris 6 (18.5 pt)**: Baris pembatas spacer (kiri) dan judul `KELOMPOK PERALATAN` (kanan, abu-abu `#D9D9D9`) 100% sejajar.
    - **Baris 7 (18.5 pt)**: Tanggal 1 (`Sabtu 1`) dan header stasiun legenda (`BOGOR`, `BOGOR-CILEBUT`, `MASENG`) 100% sejajar.
    - **Baris 8+ (18.5 pt)**: Tanggal 2 s.d. akhir bulan dan item legenda 1 s.d. 46 100% sejajar.
  - **Standarisasi Penamaan**: Format nama berkas otomatis `TABLO [BULAN] [TAHUN].xlsx` (huruf kecil). File lama otomatis di-unlink sebelum save untuk memastikan case `.xlsx` tercatat dengan benar pada Windows NTFS.
  - Server API (`server.js`) dan Web UI (`templates/index.html`) diperbarui untuk membaca nama file dinamis dari stdout script `[OUTPUT_FILE]`.
- **Hasil Validasi:**
  - Ekspor CLI dan Web API menghasilkan berkas `logs/TABLO MARET 2026.xlsx` (31.175 bytes) dengan tata letak matriks yang 100% lurus presisi dan siap cetak.

## 11. Audit Tanggal Seluruh PDF Tidak Terbaca — 2026-09-14

- **Masalah:** seluruh 430 PDF berstatus `TANGGAL TIDAK TERBACA`, walau tanggal terlihat jelas pada halaman pertama.
- **Penyebab:** `correct_pdf_dates.py` mengharuskan label `Tanggal :` dan nilai berada dalam satu line internal. Layout tabel menyimpan label, titik dua, dan nilai sebagai span/blok terpisah.
- **Perbaikan:** `find_page_date()` mengumpulkan seluruh span, mencari label `Tanggal`, lalu memilih nilai tanggal terdekat di kanan label pada baris visual yang sama berdasarkan koordinat Y dan jarak X.
- **Hasil Validasi:** 392 `SESUAI`, 38 `BERBEDA`, 0 `TANGGAL TIDAK TERBACA`, 0 gagal dari 430 PDF. Satu koreksi PDF nyata berhasil dan sumber tidak berubah.
- **Bug visual lanjutan:** area redaksi dihitung memakai lebar Helvetica yang lebih pendek daripada DejaVu Sans, sehingga digit terakhir tanggal lama masih terlihat; Helvetica juga tampak lebih kecil.
- **Perbaikan visual:** area redaksi memakai bbox penuh hasil `page.search_for()`. Tanggal baru memakai `DejaVuSans-Bold.ttf` utuh dari Matplotlib; font subset PDF dihindari karena menghasilkan karakter nol pada text layer.
- **Validasi visual:** teks lama `2026-03-31` hilang; teks baru tepat `2026-03-29`; font tetap `DejaVuSans-Bold`, ukuran tetap `7.202 pt`, posisi X sama, baseline berbeda kurang dari `0.002 pt`, dan lebar teks setara.
- **Kasus span terpecah:** `PERAWATAN AXLE COUNTER ZP 10A CLT 14-07-2025.pdf` menyimpan tanggal halaman pertama sebagai `2025-07-` dan `15` pada dua span/baris. Detector kini menggabungkannya menjadi `2025-07-15`.
- **Koreksi header foto:** halaman pertama diubah menjadi `2025-07-14`; teks header `FOTO DOKUMENTASI` diubah dari `15 Juli 2025` menjadi `14 Juli 2025`.
- **Batas perubahan:** watermark dan isi foto tidak dipindai atau diubah. Digest seluruh gambar yang tampil tetap identik; pergeseran koordinat internal kurang dari `0.001 pt`.

## 12. Koreksi Tanggal Terlihat Tidak Bekerja di Daftar Pegawai — 2026-09-14

- **Masalah:** tombol koreksi menghasilkan PDF yang benar, tetapi tabel tetap menampilkan `BERBEDA`.
- **Penyebab:** `run()` mengembalikan record audit sumber sebelum `correct_file()`; status output tidak pernah dibaca ulang.
- **Perbaikan:** setiap PDF hasil koreksi diaudit ulang dengan `audit_file()`, lalu response diperbarui memakai `pdf_date`, `photo_dates`, `status`, dan `error` dari output.
- **Hasil Validasi:** endpoint lama mengoreksi 2 PDF, 0 gagal; response menjadi `SESUAI, SESUAI` dan total `BERBEDA` menjadi 0.

## 13. Garis Tabel Hilang dan Output Folder Baru — 2026-09-14

- **Masalah:** garis vertikal di kanan tanggal hilang; koreksi membuat folder sibling baru.
- **Penyebab garis:** bbox tanggal berakhir di X `181.35` dan garis mulai X `186.94`, tetapi padding redaksi kanan `12 pt` mencapai X `193.35`.
- **Perbaikan garis:** padding kanan menjadi `1.5 pt`, cukup menutup teks tanpa menyentuh garis.
- **Perbaikan output:** endpoint Daftar Pegawai memakai folder input sebagai output. Writer menyimpan `.tmp.pdf`, menutup dokumen, lalu atomic replace; kegagalan tidak menghapus sumber.
- **Hasil Validasi:** PDF nyata menjadi `SESUAI`; dua segmen garis X `186.94` tetap ada. Endpoint menghasilkan 1 berhasil, 0 gagal, output sama dengan input, dan 0 folder baru.
- **Pemulihan:** file ZP 101A MSG-CCR yang dilaporkan user dipulihkan dari sumber dan dikoreksi ulang; tanggal `2025-07-27`, header `27 Juli 2025`, garis utuh.

## 14. TypeScript ChildProcess stdout/stderr Null Check & Stream Event Typing — 2026-09-15

- **Masalah:** Saat `npm run build` dijalankan pada aplikasi web `web/`, kompilasi TypeScript gagal pada route handler (`src/app/api/employees/audit/route.ts`) dengan galat: `Type error: 'pyProc.stdout' is possibly 'null'` dan saat di-cast sembarangan ke `any`, memicu `Parameter 'd' implicitly has an 'any' type`.
- **Penyebab:** Pada `@types/node`, tipe bawaan `ChildProcess.stdout` dan `ChildProcess.stderr` didefinisikan sebagai `Readable | null` karena konfigurasi `stdio` dapat berupa `'ignore'` atau `'inherit'`.
- **Perbaikan:**
  - Menstandarkan fungsi pembungkus eksekusi `spawnPython` di `web/src/lib/python-runner.ts` agar mengembalikan tipe resmi `ChildProcessWithoutNullStreams` dari modul `child_process`.
  - Melakukan casting aman: `spawn(...) as unknown as ChildProcessWithoutNullStreams`.
- **Hasil Validasi:** `npm run build` berhasil 100% dengan kode keluar 0 untuk seluruh 18 route static dan dynamic API.

## 15. Penanganan Aset Target Multi-Tanggal (Tanggal Ganda Target 2025) — 2026-09-18

- **Masalah:** Aset tertentu pada dokumen target 2025 (`02_pdf_target`) memiliki lebih dari satu tanggal perawatan dalam satu bulan (contoh: `PERAWATAN SINYAL B104 CLT-BOO 10-02-2025.pdf` dan `11-02-2025.pdf`, serta 25 aset lainnya pada Februari 2025), sedangkan sumber foto 2026 hanya memiliki 1 set foto kunjungan. Eksekusi Step 2 menimpa berkas `date.txt` dan menyebabkan foto pada salah satu PDF target tidak memiliki watermark tanggal yang sesuai atau gagal digabung.
- **Penyebab:** Step 1 mengekstrak foto ke folder flat `{identifier}` tanpa tanggal target, dan Step 2 menulis `date.txt` ke folder tunggal tersebut secara berurutan sehingga tanggal berkas terakhir menimpa tanggal berkas sebelumnya.
- **Perbaikan:**
  1. Step 2 (`scripts/extract_pdf_dates.py`) melakukan *pre-scan* berkas target di awal untuk mendeteksi identifier yang memiliki tanggal ganda.
  2. Folder basis di-rename menjadi `{identifier}_{DD-MM}` untuk tanggal pertama dan di-copy ke `{identifier}_{DD-MM}` untuk tanggal berikutnya.
  3. Relasi pemisahan folder disimpan persisten di `logs/asset_folder_mapping.json` agar *re-run* bersifat idempotent.
  4. Step 3 (`scripts/scheduler.py`) mengenali folder bersuffix dan menjadwalkannya secara mandiri di `schedule.json`.
  5. Step 4 (`scripts/edit_timemark_ide1.py` & `scripts/edit_photo_coordinate_only.py`) memproses folder bersuffix dan men-strip suffix saat pencarian koordinat.
  6. Step 5 (`scripts/merge_pdf_foto.py`) memprioritaskan folder foto bersuffix tanggal sesuai nama berkas PDF target.
- **Hasil Validasi:**
  - `PERAWATAN SINYAL B104 CLT-BOO 10-02-2025.pdf` berhasil digabung ke Tim 2 dengan foto dari folder `_10-02` (watermark 10 Feb 2025).
  - `PERAWATAN SINYAL B104 CLT-BOO 11-02-2025.pdf` berhasil digabung ke Tim 1 dengan foto dari folder `_11-02` (watermark 11 Feb 2025).

## 16. Integrasi Detektor Google Cloud Vision & Optimasi Textbox Dinamis — 2026-09-19

- **Masalah:**
  1. Pada beberapa kondisi foto lapangan, garis panduan merah/oranye rusak, buram, atau tertimpa objek sehingga metode konvensional HSV/Red Guide jatuh ke `stage_fallback` dengan posisi perkiraan.
  2. Textbox watermark sebelumnya memiliki lebar tetap yang terlalu panjang (`BOX_WIDTH_RATIO = 0.48` atau 48% lebar foto). Hal ini meninggalkan ruang hitam kosong berlebih di kanan teks tanggal/jam dan menyebabkan inpainting (diffuse fill) memblur area objek foto yang sebenarnya tidak perlu ditutup.
- **Perbaikan:**
  1. **Detektor Ganda Step 4**: Integrasi Google Cloud Vision OCR via CLI argumen `--detector {guide,google_vision}` di `edit_timemark_ide1.py` & `scripts/edit_timemark_ide1.py`.
  2. **Penanganan Kuota Habis Interaktif**: Jika kuota API habis, proses otomatis jeda (`stdin.readline()`), memancarkan event SSE `quota_exceeded`, dan memunculkan modal di Web Dashboard untuk konfirmasi beralih ke `Metode Biasa` atau menghentikan proses.
  3. **Tagging Metadata & Filter Galeri**: Setiap folder hasil mencatat `meta.json` dengan atribut `detector: "google_vision" | "guide"`. Tampilan Web UI dilengkapi lencana warna dan filter galeri berdasarkan detektor.
  4. **Lebar Textbox Dinamis**: Lebar box dihitung otomatis sesuai dimensi teks sebenarnya (`tw + 2 * pad_x`) menggunakan `font.getbbox()`. Batas inpainting dibatasi ke lebar pas tersebut sehingga objek di sebelah kanan watermark tetap jernih dan tajam.
- **Hasil Validasi:**
  - Deteksi tanggal via Google Cloud Vision bekerja presisi tinggi (~0.84s per foto).
  - Textbox membungkus teks tanggal dan jam secara proporsional dan rapi tanpa sisa blur meluber.

## 17. Investigasi Masalah Duplikasi Baris Foto PTLS BOO — 2026-09-19

- **Masalah:** Dokumen gabungan `PERAWATAN PTLS BOO 26-02-2025.pdf` hasil Step 5 memiliki 2 baris foto (6 foto), padahal pengguna menghendaki hanya 1 baris foto (3 foto).
- **Akar Penyebab (Root Cause):**
  1. *Perbedaan Struktur Sumber vs Target*: PDF Sumber 2026 (`PERAWATAN PTLS BOO 04-02-2026.pdf`) hanya memuat 1 baris foto (3 foto), namun tabel halaman 1 mencantumkan 3 funcloc (`TLK10705 : SENTRAL TOKA LIM 1 BOO`, `TRA10121 : TOWER RADIO BOO`, `TWR10025 : BANGUNAN TOWER BOO`).
  2. *Step 1*: Karena terdapat beberapa funcloc, 3 foto yang sama diekspor ganda ke 2 folder aset: `PTLS/BOO` dan `PTLS/RADIO_BOO`.
  3. *PDF Target 2025*: Template asli 2025 mencantumkan 2 aset (`TLK10705` dan `TRA10121`) dengan template 2 baris foto.
  4. *Step 5*: Merger memindai seluruh funcloc target, menemukan foto di kedua folder, lalu merender 2 baris foto (duplikat).
- **Perbaikan & Validasi (Opsi A):**
  - Pada `scripts/merge_pdf_foto.py`, ditambahkan pembatasan `MULTI_ROW_CATEGORIES = {"SINYAL", "WESEL", "AXC"}`. Untuk kategori non-multi-row, pencarian foto dihentikan (*break*) segera setelah foto untuk 1 aset ditemukan lengkap.
  - Verifikasi: `PERAWATAN PTLS BOO 26-02-2025.pdf` kini tepat menghasilkan **1 baris foto** (3 foto: 0%, 50%, 100% untuk `TLK10705`), sementara berkas multi-row seperti `PERAWATAN AXLE COUNTER ZP 101 BJD-CLT 13-02-2025.pdf` tetap mempertahankan 5 baris foto secara utuh.

## 18. Fitur Filter Berkas Target (02) & Penggantian/Revert Foto Cepat dari Web — 2026-09-19

- **Kebutuhan Pengguna:**
  1. Filter galeri foto berdasarkan berkas target spesifik di folder `02_pdf_target` agar pengguna dapat langsung menginspeksi foto-foto yang akan masuk ke PDF tersebut.
  2. Tombol pintasan "🖼️ Foto" langsung di tabel daftar berkas target di panel atas.
  3. Fitur mengganti foto hasil ekspor (`03_photos_export`) langsung dari Web UI (upload berkas baru dari komputer), otomatis menjalankan ulang proses watermark (Step 4), serta tombol "↩️ Revert Asli" untuk memulihkan foto asli jika ada kekeliruan.
- **Perbaikan & Implementasi:**
  1. **Core Skrip (`scripts/replace_export_photo.py`)**:
     - Mode `replace`: Menyimpan cadangan `{stem}.original_backup.jpg` (hanya jika belum ada), membersihkan cache crop kolase di `03_photos_cropped_temp/`, menulis foto baru dalam format JPEG RGB, lalu memicu eksekusi otomatis Step 4 (`scripts/edit_timemark_ide1.py`).
     - Mode `revert`: Mengembalikan file backup ke nama asli, menghapus file backup, dan menjalankan ulang Step 4.
  2. **Express Backend (`server.js` - Port 5000)**:
     - Menambahkan endpoint `GET /api/target-mapping` yang memetakan seluruh 237 berkas target dari `schedule.json` ke daftar identifier, tanggal, dan kategori aset.
     - Menambahkan endpoint `POST /api/photos/replace` dan `POST /api/photos/revert`.
     - Menyertakan flag boolean `hasBackup` pada setiap objek foto di endpoint galeri.
  3. **Next.js Backend & UI (`web/` - Port 3000)**:
     - Menambahkan route API `/api/target-files`, `/api/photos/replace`, dan `/api/photos/revert`.
     - Memperbarui `/api/photos` untuk menerima parameter query `targetFile`.
     - Menambahkan kontrol dropdown Target File, dropzone Drag & Drop pada area gambar dan bar kartu foto, serta tombol "Revert Asli" pada komponen `photo-gallery.tsx`.
  4. **Express Frontend UI (`templates/index.html`)**:
     - Menambahkan dropdown `galleryTargetFilter` di kontrol galeri dan tombol reset.
     - Menambahkan tombol `🖼️ Foto` pada baris berkas di tabel berkas target `02_pdf_target` untuk memfilter galeri dan scroll otomatis.
     - Area foto asli (`.img-box-drop`) dan bar (`.photo-dropzone-bar`) menjadi target Drag & Drop langsung dari komputer tanpa membuka jendela Windows Explorer dan tanpa popup konfirmasi.
     - Menambahkan tombol dinamis `↩️ Revert Asli` pada setiap kartu foto galeri.
- **Hasil Validasi:**
  - Automated test script `test_api.js` berhasil memvalidasi alur replace dan revert secara end-to-end dengan hasil 100% sukses.
  - Next.js production build (`npm --prefix web run build`) berhasil tanpa peringatan maupun galat tipe.
  - Server Express (port 5000) dan Next.js (port 3000) terverifikasi dapat memfilter foto sesuai berkas target dan melakukan penggantian foto via Drag & Drop secara langsung dari browser tanpa membuka File Explorer.

## 19. Implementasi OCR Fallback pada Audit & Ekstraksi Personil untuk Berkas Image-Only — 2026-09-19

- **Masalah:** Pada audit berkas eksternal `C:\Users\dikarm\Downloads\RESOR STL 1.21 BOGOR` (total 208 berkas PDF), terdapat 29 berkas yang tidak terdeteksi personilnya (`0 KAUR, 0 PNC` / Critical), salah satunya `PERAWATAN SINYAL J10 CLT 14-06-2025.pdf`.
- **Akar Penyebab (Root Cause):**
  1. *Zero Text Layer*: Ke-29 berkas tersebut adalah PDF hasil scan (bitmap utuh ~2.481 × 3.508 piksel per halaman) tanpa lapisan teks digital (`len(doc[0].get_text('text')) == 0`).
  2. *Parser Digital-Only*: Skrip audit personil `scripts/audit_and_correct_personnel.py` sebelumnya hanya mengekstrak teks digital via PyMuPDF. Saat panjang teks 0, sistem menganggap tidak ada nama teknisi.
  3. *Distorsi Tabel OCR & Early-Exit*: Pemindaian OCR pada formulir multi-kolom membaca teks melintasi baris secara horizontal. Kata `"DILAKSANAKAN OLEH"` dapat terpecah atau tertimpa deretan sel lain, memicu *early return* kosong jika penanda awal `start is None`.
  4. *Karakter Rancu*: Tesseract membaca `DEDI SURYADI` sebagai `DED! SURYADI` (huruf `I` terbaca sebagai tanda seru `!`), sehingga pencocokan string regex eksak gagal.
- **Perbaikan yang Diterapkan:**
  1. Menambahkan fungsi `extract_page_ocr_text()` di `scripts/audit_and_correct_personnel.py`: jika panjang teks halaman 1 kurang dari 10 karakter (`len(text.strip()) < 10`), sistem merender halaman 1 (150 DPI) dan memprosesnya dengan Tesseract OCR.
  2. Menormalkan karakter rancu OCR: mengubah tanda seru `!` dan pipa `|` / angka `1` di tengah huruf menjadi `I` (contoh: `DED!` -> `DEDI`).
  3. Menghapus *early return* saat `start is None`, sehingga pemindaian roster tetap berjalan pada teks dokumen hasil OCR.
  4. Seluruh modul terkait (`scripts/extract_file_personnel.py`, `scripts/scheduler.py`, `scripts/export_dinasan_excel.py`) otomatis ter-upgrade karena mengimpor fungsi ekstraksi dari modul ini.
- **Hasil Validasi:**
  - Status Critical (`0 KAUR, 0 PNC`) pada folder `RESOR STL 1.21 BOGOR` berkurang dari 29 berkas menjadi **0 berkas (100% tuntas)**.
  - Berkas `PERAWATAN SINYAL J10 CLT 14-06-2025.pdf` terdeteksi valid: 1 KAUR (`DEDI SURYADI`) + 2 PNC (`RAIHAN HERPIAN`, `MUHAMAD SOFYAN`) dengan status `OK (Sesuai Aturan)`.
  - Ekstraksi personil cache `extract_file_personnel.py` pada 208 berkas menghasilkan 208 entri lengkap (`Files with empty personnel: 0`).

## 20. Tombol Edit Teks Mengubah Seluruh Foto dalam Folder (Single Photo Isolation & Modal Timemark) — 2026-09-20

- **Masalah:** Tombol "✏️ Edit Teks" pada kartu galeri mengubah seluruh foto (0, 50, dan 100) di folder aset yang bersangkutan, padahal pengguna hanya bermaksud mengedit satu foto individual.
- **Akar Penyebab (Root Cause):**
  1. *Evaluasi Folder Otomatis di Backend*: Pada rute `POST /api/photos/manual-edit`, ketiadaan pemisahan ketat antara edit teks manual dan penggeseran posisi menyebabkan server memindai seluruh direktori dan memproses seluruh foto saudara jika variabel sinkronisasi aktif.
  2. *Penimpaan Tanggal Otomatis*: Foto saudara yang diproses ulang ditimpa teks tanggalnya menggunakan `helperCalculateDate(dateText, stem)`, merusak waktu asli yang sudah ada.
  3. *Overflow Clipping pada UI Popover*: Popover edit teks yang lama disematkan di dalam `.img-box` dengan `overflow: hidden`, sehingga kotak centang penentu cakupan berada di luar area pandang layar pengguna.
  4. *In-Memory Staleness*: Server Express masih menjalankan instans memori lama sebelum isolasi foto dimuat.
- **Perbaikan yang Diterapkan:**
  1. *Kontrak Isolasi Mutlak*: Pada `server.js`, jika `isTextEdit === true`, cakupan folder `shouldApplyToAll` HANYA bernilai `true` bila parameter `applyDateToFolder === true`. Jika tidak, `targetRelPaths` secara mutlak dibatasi hanya untuk `[normalizedRel]`. Foto saudara sama sekali tidak dieksekusi oleh Python.
  2. *Dialog Modal Dedicated `#inlineTextModal`*: Menggantikan popover terpotong dengan dialog modal mandiri berlapisan tertinggi (`z-index: 99999`) yang menampilkan info foto, input teks, dan opsi `[ ] Terapkan perubahan teks ini ke seluruh foto (0, 50, 100)` dengan default TIDAK DICENTANG.
  3. *Penanganan Keyboard*: Tombol `Enter` untuk menyimpan dan `Escape` untuk membatalkan.
- **Hasil Validasi:**
  - Pengujian API terotomatisasi pada `04_photos_edited/Tim_1/BTP JAK/WESEL/W11 CLT_03-06`:
    - Edit `0.jpg` dengan `applyDateToFolder: false`: `0.jpg` berstatus `CHANGED`, sementara `50.jpg` dan `100.jpg` berstatus `UNCHANGED`.
    - Edit `50.jpg` dengan `applyDateToFolder: false`: `50.jpg` berstatus `CHANGED`, sementara `0.jpg` dan `100.jpg` berstatus `UNCHANGED`.
    - Edit dengan `applyDateToFolder: true`: Seluruh foto ter-update serentak dengan penyesuaian jam proporsional.
  - Server Express di-restart dan terverifikasi aktif pada port 5000.

## 21. Kartu Galeri Aset Terpecah Menjadi Dua Kartu (Split Card pada J10 BOO) — 2026-09-20

- **Masalah:** Kartu galeri `📍 BTP JAK / SINYAL / J10 BOO (Tim_1)` hanya memuat 1 foto (`0.jpg`), sedangkan foto `50.jpg` dan `100.jpg` berada di kartu terpisah `(Tim_2)` di bagian lain halaman galeri.
- **Akar Penyebab (Root Cause):**
  1. *Jadwal Resmi Tim 2*: Pada `schedule.json`, aset `BTP JAK/SINYAL/J10 BOO` terdaftar resmi di bawah Tim 2. Seluruh 3 foto awalnya tersimpan lengkap di `04_photos_edited/Tim_2/...`.
  2. *Editan Manual Tersimpan di Tim 1*: Saat pengguna melakukan koreksi teks manual pada `0.jpg`, nilai `timGroup` tidak terkirim sehingga server menyimpan hasil editan ke folder `Tim_1` (hanya ada 1 file `0.jpg`).
  3. *Penetapan Tim Berbasis Per-Berkas*: Di `server.js` (`/api/photos/gallery`), pemetaan `editedMap` mencocokkan keberadaan file satu per satu secara independen. Karena `0.jpg` cocok di Tim 1 dan dua foto lainnya cocok di Tim 2, frontend mengelompokkan berdasarkan `folderKey`, memecah aset menjadi 2 kartu terpisah.
- **Perbaikan yang Diterapkan:**
  1. *Folder-Level Tim Assignment (`getFolderTimGroup`)*: Pada `server.js`, penentuan grup Tim dilakukan seragam untuk seluruh isi direktori aset (`relDir`). Penentuan memprioritaskan jadwal resmi dari `schedule.json`, dengan fallback ke folder Tim yang memiliki berkas foto terbanyak.
  2. *Resolusi Tim pada Manual Edit*: Memindahkan `getScheduledTim` ke level modul agar endpoint `POST /api/photos/manual-edit` otomatis menulis ke folder Tim resmi aset tersebut (`schedTim || timGroup || 'Tim_1'`).
  3. *Sinkronisasi Berkas*: Menyelaraskan berkas `0.jpg` hasil editan pengguna dan metadata ke dalam `Tim_2`, serta melengkapi foto saudara di `Tim_1`.
- **Hasil Validasi:**
  - `GET /api/photos/gallery` terverifikasi mengelompokkan ketiga foto `J10 BOO` ke dalam satu `folderKey` tunggal (`Tim_2/BTP JAK/SINYAL/J10 BOO`).
  - Audit terhadap seluruh 409 aset di galeri membuktikan 0 aset terbelah (*0 split assets*).
  - Kartu foto `J10 BOO` tampil lengkap dengan 3 foto dan lencana "3 Foto".
