# Active Pipeline Rules

Aturan yang harus dipakai saat menjalankan atau menjelaskan pipeline.

## Jadwal dan Tim

- Satu file PDF harus tetap berada dalam satu Tim.
- Jika aset terakhir dalam PDF melewati 18:00, jam aset berikutnya dalam PDF tetap dilanjutkan.
- Tim berikutnya hanya dipakai untuk PDF berikutnya.
- Tanggal mengikuti tanggal pada PDF dan `date.txt`; jangan menggeser tanggal hanya karena overflow.
- Jika satu PDF ditemukan pada dua Tim, laporkan konflik dan jangan memilih Tim 1 diam-diam.

## Routing BTP

- `BOO`, `CLT`, dan `BJD` umumnya masuk `BTP JAK`.
- `BOP`, `BTT`, `CGB`, `COS`, `MSG`, `CCR`, dan `BNR` umumnya masuk `BTP BD`.
- Semua `JPL ... BOO-BOP` adalah pengecualian khusus dan masuk `BTP BD`.
- Aturan khusus harus diperiksa sebelum aturan umum yang membaca kode `BOO`.

## Kepemilikan `date.txt`

- `extract_pdf_dates.py` (Step 2) adalah satu-satunya script yang menulis `date.txt`.
- Tanggal `date.txt` berasal dari PDF target di `02_pdf_target`, bukan PDF sumber Step 1.
- `export_pdf_foto.py` (Step 1) tidak menulis `date.txt`.
- Step 1 tetap memakai tanggal khusus untuk suffix folder WESEL dua-kunjungan, misalnya `W13 BOO_02-01`; suffix ini hanya pembeda folder, bukan isi tanggal timemark.
- Kategori biasa memakai tanggal dan identifier filename tanpa membuka PDF. `AXC`, `WESEL`, dan `SINYAL` tetap membaca halaman pertama untuk semua funcloc.
- Fallback `pdfplumber` hanya membaca halaman pertama. Jangan mengganti parser selama hasil pembacaan aktif sudah benar.
- Jika isi `date.txt` sudah sama, Step 2 tidak menulis ulang file.

## Aset Multi-Tanggal pada Dokumen Target

- Jika aset yang sama muncul di lebih dari satu berkas target dengan tanggal berbeda (misal: Sinyal B104 tanggal 10 dan 11):
  1. Step 2 me-rename folder basis ke tanggal pertama (`{identifier}_{DD-MM}`) dan meng-copy ke tanggal berikutnya (`{identifier}_{DD-MM}`).
  2. Riwayat disimpan di `logs/asset_folder_mapping.json`. Re-run Step 2 wajib membaca file mapping ini agar bersifat idempoten dan tidak melakukan rename berulang.
  3. Masing-masing folder bersuffix memiliki berkas `date.txt` tersendiri sesuai tanggal perawatannya.
  4. Step 3 wajib menjadwalkan setiap folder bersuffix secara mandiri di `schedule.json`.
  5. Step 4 memproses folder bersuffix dan men-strip suffix saat pencarian koordinat aset (`04_koordinat`).
  6. Step 5 mencocokkan tanggal filename berkas PDF target (`_DD-MM`) dan memprioritaskan folder bersuffix sebelum folder plain.

## Export Data Aset Excel

- Fitur tersedia di app pada `Daftar Pegawai → Audit Jadwal Dinasan → Export Data Aset (.xlsx)`.
- Sumber mengikuti pilihan `Pipeline project` atau `Folder PDF lain`.
- Output hanya satu sheet `Data Aset` dan satu baris Excel untuk setiap aset.
- Urutan kolom wajib: `TANGGAL`, `FILE NAME`, `KODE ASET`, `ASET`.
- `KODE ASET` adalah kode funcloc sebelum titik dua, misalnya `AXL11540`.
- Pasangan kode dan aset harus berasal dari baris funcloc yang sama; jangan memasangkan berdasarkan urutan tebakan.
- Tanggal memakai format `DD-MM-YYYY`; nilai tidak tersedia ditulis `-`.
- Jika satu PDF memiliki beberapa aset, tanggal dan filename diulang pada setiap baris aset.
- Jangan menambah kolom jadwal, Tim, personil, nomor SC, status, atau path tanpa permintaan pengguna.

## Audit dan Koreksi Tanggal PDF

- Fitur tersedia di app pada kartu `Audit & Koreksi Tanggal PDF` di tab Daftar Pegawai dan sebagai tahap 2 menu `AUDIT FILE LAIN`.
- Input dapat memakai `02_pdf_target` atau folder PDF eksternal; scan selalu rekursif.
- Tanggal terakhir berformat `DD-MM-YYYY` pada filename menjadi acuan.
- Audit membandingkan filename dengan tanggal setelah label `Tanggal :` pada halaman pertama dan teks tanggal header halaman `FOTO DOKUMENTASI`.
- Detector mendukung tanggal ISO yang terpecah menjadi beberapa span, misalnya `2025-07-` dan `15`.
- Status: `SESUAI`, `BERBEDA`, `TANGGAL TIDAK TERBACA`, `FILENAME TANPA TANGGAL`, dan `GAGAL DIBACA`.
- Koreksi hanya untuk status `BERBEDA`; format lama dipertahankan (`YYYY-MM-DD` atau `DD-MM-YYYY`).
- Koreksi tidak membaca atau mengubah watermark di dalam foto. Hanya text layer tanggal halaman pertama dan header `FOTO DOKUMENTASI` yang diproses; redaction memakai `PDF_REDACT_IMAGE_NONE`.
- Menu Daftar Pegawai mengoreksi langsung file PDF di folder sumber. Penulisan memakai `.tmp.pdf`, lalu replace hanya setelah save berhasil; kegagalan tidak menghapus file sumber.
- Area redaksi tanggal dibatasi pada bbox teks dengan padding 1.5 pt. Jangan memperpanjang area ke garis tabel di kanan.
- Menu `AUDIT FILE LAIN` tetap menyediakan Folder Baru atau Timpa Sumber dengan backup wajib dan konfirmasi `TIMPA SUMBER`.
- Semua tahap menu `AUDIT FILE LAIN` memakai `workingFolder` yang sama: hasil tanggal menjadi input personil; hasil personil menjadi input kedua export.
- Setelah koreksi, setiap PDF output wajib diaudit ulang. Response dan tabel UI memakai `pdf_date`, `photo_dates`, dan `status` hasil audit output, bukan audit sumber sebelum koreksi.
- PDF tanpa text layer memakai OCR Tesseract sebagai fallback; detector text layer selalu dicoba lebih dahulu.
- OCR harus menemukan label/header dan bbox aktual dari render halaman. Jangan memakai posisi tetap sebagai fallback koreksi.
- Hasil OCR hanya diterima jika confidence memadai, tanggal kalender valid, dan hanya ada satu kandidat tanggal yang jelas; hasil ambigu tetap `TANGGAL TIDAK TERBACA`.
- Header `FOTO DOKUMENTASI` pada PDF vector boleh dibaca OCR dekat judul halaman. Watermark dan teks di dalam foto tetap diabaikan.

## Posisi manual

- Posisi tanggal yang sudah dikoreksi pengguna tersimpan di `meta.json`.
- Proses ulang Step 4 harus mempertahankan posisi tersebut.
- Isi tanggal dan jam boleh diperbarui dari `schedule.json`, tetapi posisi manual tidak boleh hilang.

## Urutan kerja aman

1. Baca histori bug dan aturan ini.
2. Periksa sumber, output, dan manifest.
3. Buat backup atau manifest sebelum pemindahan/batch besar.
4. Jalankan Step 4 dan periksa hasil foto.
5. Jalankan Step 5 hanya setelah Step 4 benar.
6. Catat hasil, jumlah gagal, `unedited`, konflik, dan lokasi output.

## Eksekusi Dispatcher Python & Standalone Engine

- Semua pemanggilan skrip Python dari antarmuka web Next.js (`web/`) WAJIB melalui fungsi perantara `spawnPython()` di `web/src/lib/python-runner.ts`.
- Fungsi `spawnPython()` secara otomatis memprioritaskan pemanggilan `bin/python_engine/python_engine.exe` jika berkas biner tersebut ada (komputer non-Python).
- Bila berkas `python_engine.exe` tidak ditemukan (misalnya saat proses pengembangan lokal), fungsi otomatis beralih menggunakan interpreter `python` bawaan sistem dengan skrip di folder `scripts/`.
- Jangan memanggil `spawn("python", ...)` secara langsung pada route handler atau library Next.js agar aplikasi tetap kompatibel saat dijalankan di komputer tanpa instalasi Python.
- Setiap skrip Python baru yang dibuat di `scripts/` dan perlu dipanggil oleh antarmuka web harus didaftarkan ke `MODULE_MAP` pada `scripts/python_engine.py` sebelum dilakukan kompilasi ulang PyInstaller.

## Prioritas Pencocokan Kandidat Foto & Thread-Safety pada Step 5

- **Prioritas Pencocokan Kandidat Persis**:
  - Saat Step 5 (`merge_pdf_foto.py`) mencari folder foto untuk suatu identifier (misalnya `BOO`), kandidat nama persis (`cand == identifier`) WAJIB dievaluasi terlebih dahulu di seluruh folder tim.
  - Jika kandidat nama persis ditemukan dan memiliki foto valid, proses pencarian harus langsung dihentikan (`break`).
  - Varian nama (misalnya `RADIO_BOO` atau format fallback lainnya) HANYA boleh dievaluasi jika kandidat nama persis tidak ditemukan sama sekali.
  - Jangan pernah mencampur kandidat persis dan kandidat varian ke dalam satu pool pengurutan timestamp (`latest_mtime`), karena berkas varian yang disentuh belakangan akan menimpa foto aset utama yang benar.

- **Aturan Thread-Safety Logging**:
  - DILARANG menggunakan `contextlib.redirect_stdout` di dalam thread worker (`ThreadPoolExecutor`). Python membagi `sys.stdout` secara global, sehingga pembungkusan ini menyebabkan balapan thread (*race condition*) dan memicu *hang* / deadlock.
  - Gunakan parameter callback thread-local (`log_fn=buffer.append`) untuk menangkap log per worker secara mandiri dan aman.
  - Gunakan `concurrent.futures.as_completed()` untuk streaming log secara responsif.

- **Batas Waktu Proses (Safety Timeout) & Keandalan Tombol UI**:
  - Setiap pemanggilan proses eksternal/Python dari backend (`server.js` atau Next.js) wajib memiliki batas waktu penghentian otomatis (maksimal 120 detik) agar worker tidak menjadi proses zombi jika terjadi kendala IO.
  - Setiap tombol aksi pemrosesan di Web UI (seperti tombol `⚡ Merge PDF` per kartu atau per foto) wajib dilindungi oleh `AbortController` dengan timeout maksimal 60 detik, dan status tombol harus selalu dipulihkan pada blok `finally` agar tidak pernah macet dalam status loading (`⏳ Merging...`).

## Audit dan Ekstraksi Personil pada Dokumen Scan / Image-Only

- Deteksi personil (`scripts/audit_and_correct_personnel.py` dan `scripts/extract_file_personnel.py`) memprioritaskan pembacaan teks digital bawaan PDF.
- Jika teks digital Halaman 1 kosong atau kurang dari 10 karakter (`len(text.strip()) < 10`), sistem WAJIB mengalihkan ke Tesseract OCR (`dpi=150`) sebagai fallback otomatis.
- Sebelum pencocokan regex dengan roster pegawai, teks OCR dinormalisasi untuk mengatasi karakter rancu (misal: tanda seru `!` diubah menjadi `I` seperti `DED!` -> `DEDI`, dan `|` atau `1` di tengah huruf dinormalisasi menjadi `I`).
- Alur pencocokan roster tidak boleh melakukan *early return* saat `start is None`, agar teks formulir hasil OCR yang terbaca horizontal tetap dipindai nama personilnya.
- Dokumen scan yang sah di lapangan tidak perlu dikoreksi. Jika pengeditan teks pada dokumen scan diperlukan di masa depan, gunakan metode *White-Patch & Overlay Text* (menutup area teks via `page.draw_rect` warna putih, lalu mencetak teks baru via `page.insert_text`).

## Aturan Isolasi Edit Teks Manual & Sinkronisasi Folder Foto

- **Pemisahan Edit Teks vs Penggeseran Koordinat Posisi**:
  - Pengubahan teks timemark melalui tombol **"✏️ Edit Teks"** atau klik kotak timemark WAJIB mengirimkan `isTextEdit: true`.
  - Secara baku (*default*), edit teks HANYA boleh memproses dan mengubah berkas foto yang dipilih (`targetRelPaths = [normalizedRel]`). Foto saudara (0, 50, atau 100) DILARANG diubah, dirender ulang, atau ditimpa tanggalnya di `meta.json`.
  - Perubahan teks tanggal ke seluruh foto saudara di folder aset hanya boleh terjadi jika pengguna secara eksplisit dan sadar mencentang kotak pilihan `[x] Terapkan perubahan teks ini ke seluruh foto (0, 50, 100)`.
  - Penggeseran koordinat posisi (drag-and-drop box) mengikuti opsi sinkronisasi posisi grup (`🔗 Samakan posisi ke 0, 50, 100`), yang hanya menyamakan koordinat X dan Y tanpa pernah mengubah tanggal/jam foto saudara.
- **Bebas Potongan Antarmuka (*Unclipped Dialog*)**:
  - Komponen input teks tanggal/jam wajib berupa dialog modal mandiri di lapisan `z-index: 99999` pada elemen terluar halaman, dan tidak boleh disematkan di dalam kontainer yang memiliki `overflow: hidden`.

## Aturan Ekspor Excel (Tablo & Jadwal Dinasan)

- **Eksekusi Wajib In-Memory**: Pembuatan berkas Tablo Form STE-RECORD-13.4.01 dan Jadwal Dinasan Pegawai dieksekusi langsung di memori proses server (`generate_tablo_workbook` dan `build_dinasan_workbook`) tanpa menggunakan subproses ganda PyInstaller (`--run-script`), agar berjalan instan dalam hitungan detik.
- **Pencarian Berkas Rekursif**: Seluruh pemindaian berkas PDF untuk penjadwalan dan pembuatan dokumen WAJIB menggunakan `.rglob("*.pdf")` (rekursif) agar folder yang memiliki struktur subfolder bertingkat (seperti `siap di OCR\BTP BD\AXLE COUNTER\...`) terbaca secara menyeluruh.
- **Dukungan Folder Simpan Kustom**: Generator dokumen menerima parameter direktori output kustom (`output_path`) yang dipilih pengguna melalui dialog native Windows, dengan fallback otomatis ke folder `logs/` jika tidak ditentukan.
- **Injeksi Profil Pegawai Aktif**: Konfigurasi personil (KUPT Resor, KAUR, dan teknisi PNC) wajib disuplai secara langsung dari konfigurasi preset aktif (`get_active_pegawai_config`), baik via parameter `config` (in-memory dict) maupun `config_path` (file json sinkron).

## Aturan Rilis & Pengemasan Desktop App (update_app.md)

- **Ukuran Biner Normal (Size Guardrail)**: Ukuran biner terkompilasi `SintelisUtility.exe` wajib berada di rentang **180 MB – 195 MB**. Jika ukuran membengkak di atas 250 MB, rilis wajib dibatalkan karena terindikasi penumpukan berkas lama (*recursive bundling*).
- **Pembersihan Wajib Sebelum Kompilasi**: File `dist/SintelisUtility.exe` lama WAJIB dihapus sebelum PyInstaller dijalankan (`del /f /q ...\dist\SintelisUtility.exe`).
- **Sinkronisasi Versi 4 Titik**: Nomor versi wajib dinaikkan serentak di:
  1. `updater_engine.py` (`APP_VERSION = "..."`)
  2. `run_desktop_webview.py` (`webview.create_window(...)`)
  3. UI components (`Sidebar.jsx` & `BentoHeader.jsx`)
  4. Server `version.json`
- **Auto-Updater Native PowerShell**: Skrip pembaruan otomatis di Windows wajib menggunakan PowerShell (`sintelis_updater.ps1`) dengan perulangan jeda 1 detik (`Start-Sleep -Seconds 1`) untuk menangani pelepasan kunci berkas oleh sistem operasi secara atomik.

## Gaya komunikasi agent

- Gunakan bahasa Indonesia sederhana.
- Jelaskan seperti kepada pengguna aplikasi yang tidak memahami program.
- Sampaikan kesimpulan terlebih dahulu.
- Jelaskan istilah teknis dengan contoh.
- Bedakan dengan jelas: sudah diperbaiki, belum dilakukan, dan langkah berikutnya.

