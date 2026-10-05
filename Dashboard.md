# 🗂️ OCR Foto Timemark — Project Dashboard

> **Baca ini dulu + AGENTS.md** sebelum edit/propose.

## Project Overview
Pipeline 5-tahap koreksi tanggal watermark GPS Map Camera. Input: PDF 2026 (foto asli) + PDF 2025 (template). Output: PDF 2025 upgrade foto baru + timemark terkoreksi.

Script references, detection logic, debugging → lihat [[AGENTS.md]].


## 📌 Status Tracker

### Active Scripts
- [x] `OCR_Foto_Timemark.exe` — Standalone native desktop executable (Windows WebView2 Edge Chromium, zero-prerequisite untuk PC non-Python/non-Node).
- [x] `launcher.py` — Host peluncur desktop window dan pengelola life-cycle proses latar belakang Node.js.
- [x] `bin/python_engine/python_engine.exe` — Standalone Python engine terkompilasi PyInstaller (C-extensions: fitz, pdfplumber, numpy, PIL, openpyxl) mencakup 14 skrip pipeline & ekspor.
- [x] `bin/node.exe` — Standalone portable Node.js runtime untuk menjalankan server Next.js 14 SSR & endpoint API.
- [x] `web/` — Next.js 14 App Router Fullstack Web Application (port 3000, 5 Modul Lengkap: Pipeline & Live SSE Terminal, Galeri Komparasi Foto & Timemark Editor, Daftar Pegawai Multi-Preset, Audit Dokumen & Personil 1 KAUR 2 PNC, Ekspor Excel Resmi Tablo & Dinasan, Integrasi Dual Detektor Google Vision & Metode Biasa)
- [x] **Perbaikan Garis Batas Tabel Terpotong & Penambahan Filter Temuan SC (2026-09-21)**:
  - Mengatasi kendala redaksi sel nomor SC yang memotong garis tepi vertikal kanan tabel pada 5 berkas AXLE COUNTER CLT (`ZP 12A`, `ZP 12B`, `ZP 13`, `ZP 22A`, `ZP 22B`) serta 4 berkas lainnya di `02_pdf_target` dan `05_pdf_merged`.
  - Memperbarui `scripts/employee_manager.py` dengan batas aman: `safe_sc_left = max(466.0, x_sc_left)` dan `safe_sc_right = min(563.5, x_sc_right)`, menjaga jarak aman 2.5–3.0 pt dari garis vertikal sehingga garis batas tabel tidak pernah tersentuh redaksi putih.
  - Memulihkan seluruh 9 berkas yang sebelumnya terpotong garisnya di `02_pdf_target` dan `05_pdf_merged`. Garis tabel kini 100% tersambung utuh, solid, dan rapi tanpa celah (`logs/zp12a_table_repaired.png`).
  - Menambahkan filter khusus "Temuan SC" pada antarmuka web (`web/src/components/personnel-audit.tsx` dan `templates/index.html`): kartu metrik "Temuan SC" kini interaktif/clickable, tersedia tab filter cepat ("Semua Berkas", "🚨 Temuan Utama", "🧾 Temuan SC", "✅ Sesuai Aturan"), serta lencana status amber untuk berkas dengan nomor SC yang belum lengkap.
- [x] **Perbaikan Deteksi & Koreksi Nomor SC pada Dokumen Template Raster (2026-09-21)**:
  - Mengatasi kendala audit dan koreksi nomor SC pada 5 berkas AXLE COUNTER CLT tanggal 14-06-2025 (`ZP 12A`, `ZP 12B`, `ZP 13`, `ZP 22A`, `ZP 22B`) di mana nomor SC teknisi `RAIHAN HERPIAN` tidak terbaca dan gagal dikoreksi.
  - Memperbarui `extract_missing_no_sc` (`scripts/audit_and_correct_personnel.py`) dan `replace_page1_employee_names` (`scripts/employee_manager.py`) dengan pencocokan tingkat baris (*line-level matching*) untuk mengenali nama yang terpecah dalam beberapa span kata terpisah (`RAIHAN` + `HERPIAN`).
  - Memperbaiki deteksi nomor SC hilang untuk sel kosong pada template raster latar belakang (tanda `-` gambar raster).
  - Menyesuaikan batas kolom fallback redaksi (`x_sc_left = 466.0`) agar garis batas vertikal tabel tetap 100% utuh tanpa terpotong.
  - Hasil: Seluruh berkas di `02_pdf_target` dan `05_pdf_merged` kini 100% terkoreksi dengan nomor SC resmi `PRP.170204.72256` dan terverifikasi rapi.
- [x] **Sinkronisasi Profil Pegawai Aktif pada Tablo & Jadwal Dinasan serta Pengaturan Cetak Pas Lebar (2026-09-21)**:
  - Tablo (`scripts/export_tablo_excel.py`) dan Jadwal Dinasan (`scripts/export_dinasan_excel.py`) kini 100% tersinkronisasi dinamis dengan profil personil aktif dari `config/daftar_pegawai.json` (Resor `S. SLAMET RIYADI`, KAUR Preventif `AGUS PRIYONO`, KAUR Perbaikan `DEDI SURYADI`, dan 5 PNC: `RAIHAN HERPIAN`, `IWAN SETIAWAN`, `MUHAMAD SOFYAN`, `DONI FREDIANSYAH`, `SADDAM YUSUF FATHIR`).
  - Menghapus daftar nama lama yang di-hardcode (Furqon Susilo, Sutisna, Yatiyo, Jujun, Dika).
  - Kolom personil Tablo otomatis dinamis menyesuaikan jumlah staf (kolom D..K untuk 8 personil, kolom L pemisah, kolom M..T legenda & data personil), dengan tanda tangan KAUR Preventif (`AGUS PRIYONO`) dan KUPT Resor (`S. SLAMET RIYADI`).
  - **Format Tablo**: Diatur pas **tepat 1 halaman utuh** A4 Landscape (`fitToWidth = 1`, `fitToHeight = 1`, `horizontalCentered = True`, `verticalCentered = True`).
  - **Format Jadwal Dinasan**: Menggunakan format **Portrait** dengan **lebar pas 1 halaman** (`fitToWidth = 1`, `fitToHeight = 0`), tinggi mengalir otomatis mengikuti banyaknya baris data tabel, pengulangan baris judul dan header di setiap halaman (`print_title_rows = "1:4"`), perataan tengah horizontal (`horizontalCentered = True`), dan pembungkusan teks rapi (`wrap_text = True`).
- [x] **Perbaikan Deteksi & Koreksi Personil PDF (2026-09-21)**:
  - Mengatasi kendala berkas seperti `PERAWATAN SINYAL B 207 BOO-CLT 11-06-2025.pdf` dan berkas raster/scan lainnya yang gagal dikoreksi atau hilang pembacaan personilnya.
  - Memperbarui deteksi span kolom `NO. SC.` di `scripts/employee_manager.py` yang sebelumnya terbelah menjadi 2 span terpisah (`NO.` dan `SC.`), ditambah fallback OCR dan koordinat standar formulir A4.
  - Memperbarui `scripts/audit_and_correct_personnel.py` dengan regex toleran variasi spasi (`make_roster_pat`, misal nama conjoined tanpa spasi `DEDISURYADI` maupun spasi acak `IWAN SETI AWAN`), penghapusan break prematur pada loop baris teknisi, dan pemetaan lengkap KAUR/PNC pada fallback halaman penuh.
  - Hasil: Seluruh berkas (termasuk 9 berkas SINYAL tanggal 14-06-2025) kini terbaca akurat 100% lengkap 3 personil (1 KAUR, 2 PNC) dan koreksi tunggal/batch berjalan mulus dengan status sukses HTTP 200.
- [x] **Smart Google Vision + Guide Integration & Default Step 4 (2026-09-20)**:
  - Detektor default Step 4 kini resmi menggunakan `google_vision` di seluruh pipeline (`scripts/edit_timemark_ide1.py`, `edit_timemark_ide1.py`, `server.js`, dan `scripts/replace_export_photo.py`).
  - Kamus bilingual nama hari & bulan (Indonesia & Inggris) plus regex typo OCR tolerance (`Manggu` -> `Minggu`, `Sulcan` -> `Sabtu`, dll.).
  - *Spatial horizontal line sweep* menangkap kata hari di sebelah kiri baris Y yang sama, menyelesaikan bug koordinat tanggal melompat ke kanan (`X ≈ 51..88`) pada foto AXC (`ZP 13 BOO`, `ZP 22A CLT`, `ZP 23A BOO`, `ZP 31B BOO`).
  - Penggunaan titik atas guide (`gy1`) sebagai jangkar vertikal jika teks tanggal terbaca sepotong, serta deteksi mandiri tanpa guide pada layout *Timemark Camera* (`MJ20 BTT-MSG`).
- [x] **Pembersihan Berkas Sisa Eksperimen & Folder Uji Coba (~430 MB) (2026-10-05)**:
  - Mengaudit seluruh repositori dan menghapus model bobot AI YOLO (`yolov8n.pt`, dataset, labels), riset visi AI mandiri (Florence-2, Qwen-2.5-VL), folder output sementara (`04_Output_Temp/`, `04_photos_sementara/`, `scratch/`), skrip sisa riset OpenCV/Canny di `scripts/`, dan duplikat skrip di root.
  - Membebaskan lebih dari 430 MB ruang penyimpanan dan merapikan pohon berkas proyek.
  - Berkas kunci Excel aktif (`~$data_acuan_tenaga_gabungan.xlsx`) serta modul pustaka inti (`employee_manager.py`, `crop_collage_photos.py`) terverifikasi tetap aman terjaga.
- [x] **Fitur Lencana & Filter "⚠️ Perlu Koreksi" (2026-09-20)**:

  - Foto yang memakai konsensus folder atau deteksi fallback otomatis ditandai `needCorrection: true` pada `meta.json`.
  - Lencana filter `0 ⚠️ Perlu Koreksi` di header galeri web (`templates/index.html`) untuk menyaring foto-foto yang perlu dicek dalam 1 klik.
  - Kartu foto menampilkan lencana `⚠️ Perlu Koreksi` hingga pengguna memverifikasi atau mengeditnya.
- [x] **Inline Timemark Editing di Kartu Galeri & Isolasi Edit Teks (2026-09-20)**:
  - Kotak biru `.inline-timemark-box` langsung tertempel di atas foto asli pada kartu galeri, menggantikan modal pop-up yang berat.
  - Fitur drag-and-drop real-time dengan auto-save instan saat mouse/pointer dilepas (`pointerup`), disertai feedback kedipan hijau lembut (`saved-flash`).
  - **Isolasi Edit Teks Mutlak**: Klik tombol "✏️ Edit Teks" atau klik kotak timemark membuka dialog modal `#inlineTextModal` yang bersih dan tidak terpotong tepi gambar. Secara default (checkbox `[ ] Terapkan ke semua foto (0, 50, 100)` TIDAK dicentang), backend `server.js` HANYA mengubah berkas foto yang dipilih (`targetRelPaths = [normalizedRel]`). Foto saudara (0, 50, atau 100) dijamin 100% utuh tanpa kalkulasi otomatis yang tidak diinginkan.
  - Opsi Terapkan ke Semua: Jika pengguna mencentang checkbox, barulah perubahan teks tanggal diterapkan serentak ke seluruh foto dalam folder dengan jeda menit proporsional (+22m pada 50%, +45m pada 100%).
  - **Sinkronisasi Posisi**: Checkbox di header kelompok aset (`🔗 Samakan posisi ke 0, 50, 100`) hanya menyamakan koordinat X & Y tanpa menimpa teks tanggal/jam masing-masing foto saudara.
- [x] **Zoom Foto Interaktif saat Diklik & Tukar Foto Antar Kartu via Drag-and-Drop (2026-09-20)**:
  - **Zoom Foto saat Diklik**: Setiap foto di kartu galeri (foto asli sebelah kiri maupun foto editan sebelah kanan) kini dapat diklik untuk membuka modal Lightbox Zoom layar besar. Dilengkapi kontrol zoom (`+`, `-`, `Fit`, `1:1`), mouse wheel zoom, click toggle zoom (1x/2.2x), drag-to-pan saat diperbesar, tombol tutup `✕`, dan penutupan otomatis dengan tombol `Esc` atau klik di luar gambar.
  - **Tukar Menukar Foto Antar Kartu (Swap Photos)**: Pengguna dapat menyeret (drag) foto dari satu kartu galeri ke foto kartu lain untuk saling bertukar posisi berkas secara instan.
  - Backend `server.js` menyediakan endpoint `POST /api/photos/swap` dan `scripts/replace_export_photo.py --action swap` yang menukar berkas fisik di `03_photos_export`, membuat backup otomatis, membersihkan cache cropped temp, mereset `meta.json` lama, dan otomatis menjalankan pemrosesan Step 4 untuk foto-foto yang ditukar.
  - Frontend membedakan drag swap internal (`⇄ Lepaskan untuk tukar posisi foto`) dan drag file dari komputer (`📥 Lepaskan untuk ganti foto`), dengan update gambar seketika tanpa refresh manual halaman.
- [x] **Perbaikan Ekspor Log Gagal & Fallback (Excel `.xlsx` + Companion `.json`) (2026-09-21)**:
  - Memperbarui fungsi `export_gagal_fallback()` di `scripts/merge_pdf_foto.py` agar mengintegrasikan kegagalan merge PDF Step 5 (`merge_failed.xlsx` / `failed_files`) dengan metadata lengkap dari `schedule.json`.
  - Otomatis mengekspor berkas pendamping format **JSON (`.json`)** pada setiap ekspor log (`logs/{month}_GAGAL_FALLBACK.json`, `logs/merge_failed.json`, `logs/merge_skipped.json`, serta log Step 4 `edit_failed.json`, `missing_dates.json`, `unedited_photos.json`). Format JSON dipilih karena terstruktur tegas, hemat token, dan paling efisien dibaca/dianalisis oleh AI agent.
  - Memperbaiki file `logs/JUNI_2025_GAGAL_FALLBACK.xlsx` dan menghasilkan `logs/JUNI_2025_GAGAL_FALLBACK.json`.
- [x] **Penanganan Spasi Filename & PDF Scan: 100% Sukses Gabung (237/237 Dokumen) (2026-09-21)**:
  - Skrip `scripts/merge_pdf_foto.py` kini menangani variasi spasi nama berkas & folder foto secara *space-insensitive* (`_find_candidate_folders`). Perbedaan spasi seperti `UB 206 BOO-CLT` vs `UB206 BOO-CLT` otomatis cocok akurat.
  - Fallback resolusi identifier cerdas jika PDF target adalah dokumen hasil scan (0 teks digital): otomatis merujuk ke `schedule.json` dan `parse_target_filename` sebelum fallback ke nama file mentah.
  - Deteksi OCR cerdas pada `_delete_photo_pages` untuk dokumen scan agar hanya menghapus halaman foto lama dan mempertahankan halaman checklist formulir (halaman 1 & 2).
  - Hasil: Seluruh **237 dari 237 target PDF (100%)** sukses digabung ke `05_pdf_merged` (0 gagal, 0 skip). Berkas log `logs/JUNI_2025_GAGAL_FALLBACK.json` tercatat `gagal_merge: 0`.
- [x] **Penyelesaian Tuntas Kartu Galeri Terpecah / Split Card (`J10 BOO`) (2026-09-20)**:
  - Mengubah penentuan grup Tim galeri di `server.js` dari tingkat per-file menjadi tingkat folder aset utuh (`getFolderTimGroup`).
  - Penentuan grup memprioritaskan jadwal resmi `schedule.json` (`getScheduledTim`), lalu berkas terbanyak di disk.
  - Memastikan seluruh foto (`0.jpg`, `50.jpg`, `100.jpg`) selalu berbagi `timGroup` dan `folderKey` identik, mencegah aset terbelah menjadi dua kartu terpisah di galeri.
  - Penyelarasan otomatis pada manual edit sehingga berkas selalu tersimpan ke Tim resmi aset.
  - Terverifikasi 100% tuntas: 0 split assets pada seluruh 409 aset di galeri.
- [x] **Integrasi Detektor Google Cloud Vision di Step 4 & Web UI (2026-09-19)**:
  - Opsi detektor ganda: `Metode Biasa (Garis Merah)` vs `Google Cloud Vision` via argumen CLI `--detector {guide,google_vision}` pada `edit_timemark_ide1.py` & `scripts/edit_timemark_ide1.py`.
  - Tag metadata detektor pada `meta.json` di setiap folder output (`detector: "google_vision" | "guide"`).
  - Penanganan batas kuota (`quota_exceeded`): Pause otomatis dengan modal konfirmasi interaktif di Web UI untuk melanjutkan sisa berkas menggunakan metode biasa atau menghentikan proses via `/api/pipeline/resume`.
  - Web UI: Bilah tombol pemilih metode di Dashboard sejajar tombol alur kerja, lencana status detektor pada kartu foto (`Vision AI` ungu vs `Metode Biasa` biru), dan filter galeri berdasarkan detektor di `photo-gallery.tsx`.
  - **Optimasi Lebar Textbox Dinamis**: Lebar textbox watermark kini dihitung otomatis pas membungkus panjang teks tanggal dan jam (`tw + 2 * pad_x`), menggantikan lebar tetap 48% yang sebelumnya terlalu panjang dan menyebabkan blur meluber.
- [x] `server.js` — Node.js Express Web Dashboard (port 5000)
- [x] **Optimasi Kecepatan Ekstrem Pemuatan Galeri Foto & Berkas Target (2026-09-19)**:
  - Backend `server.js`: Pemindaian direktori cepat (`fastScanPhotos`) dengan `withFileTypes: true` meniadakan ribuan pemanggilan `fs.statSync`; pembacaan `auto_crop_manifest.json` dipindahkan ke luar loop; cache `date.txt` dan `meta.json` per folder; in-memory cache dengan invalidasi otomatis. Kecepatan API meningkat drastis dari 2.633ms menjadi 500ms (cold scan) dan **13–20ms (cache hit, 200x lebih cepat)**.
  - Frontend `templates/index.html`: Guard `targetMappingLoaded` mencegah pemanggilan ganda; pemuatan bertahap (*progressive pagination*) 24 aset awal dengan tombol `Tampilkan Lebih Banyak` dan `Tampilkan Semua`; peramban memanfaatkan cache HTTP lokal dengan `?v=${p.modifiedMs}` tanpa mengunduh ulang ribuan gambar setiap filter diganti.
- [x] **Fitur Pencarian Real-Time di Seluruh Daftar Berkas (File List) (2026-09-19)**:
  - Kotak pencarian `🔍 Cari file PDF...` di bilah sisi kiri penampil PDF (Tab 3: `pdfFileList`), memfilter dokumen PDF hasil merge (standar, jam, koordinat) secara instan.
  - Kotak pencarian `🔍 Cari berkas...` di atas tabel `01_pdf_source` (442 berkas) dan `02_pdf_target` (237 berkas) pada Tab 1, dengan tombol clear `✕` dan pembaruan jumlah berkas dinamis.
- [x] **Perbaikan Pencarian & Pemetaan Lintas Stasiun Galeri Foto (PTPP JPL 27 & 28) (2026-09-19)**:
  - Frontend & Backend: Mengimplementasikan `expandIdentifierVariants` untuk menangani variasi kode stasiun compound JPL (misal `JPL 27 CLT-BOO` otomatis mengenali `JPL 27 BOO-CLT`, `JPL 27 CLT`, dan `JPL 27 BOO`).
  - Menghubungkan berkas target `02_pdf_target` ke folder `03_photos_export` secara akurat pada Express (`templates/index.html`), `server.js` (`getTargetFileMapping`), dan Next.js (`web/src/app/api/photos/route.ts`).
  - Pencarian multi-token di galeri foto memungkinkan pencarian bebas multi-kata (misal: "ptpp jpl 27" atau "jpl 28").
  - Memperbaiki normalisasi hyphen di `export_pdf_foto.py` dan `scripts/export_pdf_foto.py` agar nama stasiun compound tidak terpotong saat diekspor.
  - Berkas gabungan `05_pdf_merged` untuk PTPP JPL 27 dan 28 terverifikasi selesai dan berstatus OK.
- [x] **Perbaikan & Restrukturisasi Fitur Merge PDF per Baris Aset (`⚡ Merge PDF`) (2026-09-19)**:
  - **Restrukturisasi UX**: Tombol `⚡ Merge PDF` dipindahkan dari tiap kartu foto individu (`0.jpg`, `50.jpg`, `100.jpg`) ke header baris aset di samping judul kartu (`📍 BTP JAK / {CAT} / {DETAIL} ({TIM})`), sesuai model data dokumen perawatan (1 dokumen PDF memuat seluruh baris foto aset 0%, 50%, 100%).
  - **Solusi Tuntas Masalah Foto Lama di PDF**:
    - Backend Express `server.js`: Menambahkan opsi `noCacheStatic` (`Cache-Control: no-store, no-cache, must-revalidate, proxy-revalidate`) pada route berkas PDF hasil gabungan (`/static/pdf-merged`, `/static/pdf-merged-time`, `/static/pdf-merged-coord`).
    - Cache-Busting URL: Menambahkan parameter query timestamp `?v=${Date.now()}` pada URL berkas PDF yang dikembalikan endpoint `/api/pdf/remerge-single` dan pada tautan `📄 Buka PDF` notifikasi toast peramban. Peramban (Chrome/Edge) kini dijamin 100% memuat dokumen PDF terbaru yang baru saja digabungkan tanpa menggunakan cache lama.
  - Backend `server.js` (`/api/pdf/remerge-single`): Menggunakan pencocokan cerdas berbasis `getTargetFileMapping()` dan `expandIdentifierVariants()` sehingga kartu foto lintas stasiun (`JPL 27 BOO`, `JPL 28 BOO`), typo (`ZP 41 BOO` <-> `ZP 41B BOO`), alias (`JPL 26N`), dan leading zero otomatis menemukan berkas PDF targetnya.
  - Skrip penggabung `scripts/merge_pdf_foto.py`: Menambahkan `get_identifier_candidates()` untuk memperluas nama aset dokumen target ke variasi folder edit di disk, menghilangkan error `no matching edited photos found`.
  - Frontend `templates/index.html`: Fungsi `remergeGroupPdf()` menggabungkan seluruh baris foto aset secara instan dengan dukungan semua mode (Standar, Jam, Koordinat).
  - Sinkronisasi Next.js: Route `web/src/app/api/pdf/remerge-single/route.ts` dan antarmuka `photo-gallery.tsx` turut diselaraskan dengan penempatan tombol Merge PDF di header kartu aset.
  - Verifikasi: Pengujian `POST /api/pdf/remerge-single` untuk `PTLS BOO` dan `PTPP JPL 27/28` teruji sukses 100% (1.5s), hash foto terverifikasi identik byte-for-byte, dan header HTTP `Cache-Control: no-store, no-cache` aktif.
- [x] **Sinkronisasi Pemetaan Target PDF & Perbaikan Remerge Foto (2026-09-19)**:
  - `scripts/scheduler.py`: Memprioritaskan funcloc baris pertama untuk kategori single-row bila lebih spesifik (misal `TRA10095` -> `RADIO_BOO` pada `PERAWATAN PTLS BOO 26-02-2025 (2).pdf`, bukan sekadar `BOO` dari nama file).
  - Regenerasi `schedule.json`: Memisahkan dokumen target `RADIO_BOO` (boks putih) dan `BOO` (rak kabinet), sehingga filter berkas target di galeri web menampilkan foto yang tepat dan tidak tertukar.
  - `server.js` (`/api/pdf/remerge-single`): Validasi ketidakcocokan antara berkas target yang dikirim frontend dengan folder foto yang diklik, perbaikan pemotongan string `cleanIdent`, serta pengurutan prioritas berkas target utama tanpa angka duplikat (`preferUnnumbered`).
  - `templates/index.html`: Tombol `⚡ Merge PDF` hanya menyertakan filter target aktif jika asetnya cocok, mencegah salah target PDF.
- [x] **Pemetaan 1 Foto ke Banyak Berkas PDF Target (`photo_target_mapping.json`) & Multi-Merge Cepat (2026-09-19)**:
  - `scripts/scheduler.py` (Step 3): Otomatis memproduksi `photo_target_mapping.json` (402 aset foto) yang memetakan setiap baris foto aset ke seluruh berkas checklist PDF target yang menggunakannya (misal 1 foto sinyal `B104` dipakai di 5 dokumen PDF berbeda).
  - `scripts/merge_pdf_foto.py` (Step 5): Mendukung argumen `--file "file1.pdf,file2.pdf,..."` sehingga runtime Python/PyMuPDF cukup start 1 kali untuk menggabungkan banyak berkas sekaligus (~2.8 detik untuk 5–6 berkas).
  - Backend `server.js`: Rute `GET /api/photo-targets-mapping` dan `POST /api/pdf/remerge-single` yang otomatis menggabungkan seluruh berkas target terkait saat tombol `⚡ Merge PDF` baris aset ditekan, dengan URL cache-busting per dokumen.
  - Antarmuka Web (`templates/index.html` & `web/src/components/photo-gallery.tsx`): Menampilkan badge `📄 X Target PDF` di samping tombol `⚡ Merge PDF` pada header kartu aset beserta tooltip daftar berkas target, dan toast alert informatif saat multi-merge selesai.
- [x] **Sinkronisasi Multi-Tim Folder & Prioritas Edit Manual (`manualEdit`) di Merge PDF (2026-09-19)**:
  - Backend `server.js` (`/api/photos/manual-edit`, `/api/photos/time-manual-edit`, `/api/photos/coord-manual-edit`): Setiap kali pengguna menyimpan hasil edit foto manual (misal mengubah posisi/tanggal timemark), sistem otomatis menyinkronkan foto dan `meta.json` ke seluruh folder Tim lainnya yang memuat aset tersebut (misal dari `Tim_1` otomatis disalin ke `Tim_2`).
  - Skrip penggabung `scripts/merge_pdf_foto.py`: Seleksi cerdas kandidat foto lintas direktori Tim. Mengutamakan folder yang memiliki bendera `manualEdit: true` dan waktu modifikasi paling baru (`latest_mtime`), sehingga berkas PDF selalu memuat foto editan terbaru pengguna.
  - Verifikasi: Pengujian edit timemark dan remerge pada `BOO` sukses memperbarui 6 dokumen target PDF, dan hash foto di dalam PDF terbukti 100% identik byte-for-byte dengan hasil editan pengguna.
- [x] **Perbaikan Seleksi Prioritas Kandidat Foto Persis & Thread-Safe Logging pada Merge PDF (2026-09-19)**:
  - **Prioritas Mutlak Nama Aset Persis**: Memperbaiki logika pencarian di `scripts/merge_pdf_foto.py`. Skrip kini mencari nama aset persis (kandidat 0) terlebih dahulu ke seluruh folder Tim. Jika ditemukan, skrip langsung memilih folder terbaik dan menghentikan pencarian (`break`), mencegah varian sekunder (`RADIO_BOO`) menimpa nama aset utama (`BOO`) meski waktu modifikasi varian lebih baru.
  - **Thread-Safe Logging & Streaming Instan**: Menghapus `contextlib.redirect_stdout` yang tidak thread-safe dari `_merge_worker_wrapper` dan menggantinya dengan penampung log lokal (`log_fn`). Mengganti `executor.map` dengan `concurrent.futures.as_completed` sehingga setiap berkas yang selesai langsung mencetak log secara real-time ke web SSE tanpa tertahan.
  - **Multi-Worker Remerge & Safety Timeout**: Remerge multi-berkas (`--file`) kini memproses hingga 4 worker paralel (6 berkas selesai dalam < 3 detik). Menambahkan batas waktu keamanan 120 detik di `server.js` dan 60 detik di `templates/index.html` (`AbortController`) sehingga tombol `⚡ Merge PDF` di samping judul baris aset dijamin tidak pernah macet (*hang*) selamanya di status `⏳ Merging...`.
- [x] `audit_and_correct_personnel.py` — Engine Audit & Koreksi Aturan Personil (1 KAUR, 2 PNC, 2 Mode: Pipeline 02_pdf_target & Custom Folder, PyMuPDF Vector Redaction, OCR Fallback untuk berkas scan/image-only)
- [x] `extract_file_personnel.py` — Ekstraktor Personil Berkas PDF Halaman 1 & Penentu Roster Tim 2 (Cache JSON)
- [x] `export_tablo_excel.py` — Generator Excel Tablo Checklist & Perawatan Berkala (Form No. STE-RECORD-13.4.01, 2 Mode, 46 Legenda Kelompok Peralatan)
- [x] `correct_serat_optik_cores.py` — Koreksi Jumlah Core Serat Optik (2 Mode, Fast Filter, Presisi Outline Utuh)
- [x] `export_dinasan_excel.py` — Generator Excel Daftar Dinasan Pegawai (Format Resmi KAI)
- [x] `edit_timemark_ide1.py` — Core watermark editor. HSV + Red Guide + Folder Consensus
- [x] `edit_photo_time_only.py` — Standalone 24h Time Stamper (output: `04_Time`)
- [x] `employee_manager.py` — Roster Personil Tim 2 (KAUR/PNC) & True PDF Redaction
- [x] `export_pdf_foto.py` — Ekstrak foto dari PDF (default: raw image stream, plus opsi `--render-crop` 300 DPI untuk PDF dengan watermark vektor melayang); tidak menulis `date.txt`; tanggal tetap dipakai khusus suffix folder WESEL dua-kunjungan
- [x] `merge_pdf_foto.py` — Gabung foto edit ke PDF lama
- [x] `extract_pdf_dates.py` — Satu-satunya penulis `date.txt` dari PDF target; kategori biasa memakai filename tanpa membuka PDF, sedangkan `AXC`/`WESEL`/`SINYAL` tetap membaca funcloc halaman pertama. (Fix 2026-09-19: penambahan mapping `SERAT OPTIK` untuk prefiks `OTB ` dan pemetaan `BOO` -> `RUANG RADIO BOO`, mencapai 0 MISS pada seluruh berkas).
- [x] `scheduler.py` — Penjadwalan Tim (07:00-18:00)
- [x] `export_asset_data_excel.py` — Export satu baris per aset ke Excel; kolom `TANGGAL`, `FILE NAME`, `KODE ASET`, dan `ASET`
- [x] `correct_pdf_dates.py` — Audit/koreksi tanggal halaman pertama dan header `FOTO DOKUMENTASI`, tanpa mengubah watermark/isi gambar; text layer tetap detector utama, Tesseract menjadi fallback untuk PDF vector tanpa text layer; kandidat ambigu ditolak; redaksi dibatasi ke bbox hasil detector agar garis tabel utuh; menu Daftar Pegawai menimpa file sumber secara atomik melalui `.tmp.pdf`; hasil diaudit ulang menjadi `SESUAI`. Uji ZP 105: halaman pertama dan header foto terkoreksi, 616/616 garis panjang tetap sama.
- [x] **Menu AUDIT FILE LAIN** — Wizard folder eksternal: pilih folder/output → audit dan koreksi tanggal → audit dan koreksi personil → Export Data Aset / Jadwal Dinasan + Personil. Profil aktif tersinkron dengan Daftar Pegawai dan tampil di samping `System Ready`. Mode Folder Baru mempertahankan tree lengkap; Timpa Sumber wajib backup dan konfirmasi `TIMPA SUMBER`.
- [x] **Eksperimen & Validasi Batch Penuh PTLS & SERAT OPTIK (96 Foto, 32 Folder)**: Pemrosesan 96 foto kategori PTLS dan Serat Optik dengan spektrum warna guide diperluas (Orange + Dark Red), layout atas/samping/kolase bawah, diffuse inpainting, dan resolusi outlier baju/noise via konsensus folder. Hasil audit Tesseract OCR: 0 leaks (100% tanggal lama 2026 tertutup rapi). Tersimpan di `logs/ptls_and_serat_optik_output/` beserta 16 montase komparasi visual.
- [x] **Penanganan Otomatis Aset Multi-Tanggal (Tanggal Ganda Target 2025)**: Deteksi otomatis aset target dengan tanggal berbeda (25 aset Februari 2025 termasuk Sinyal B104/B209, AXC ZP 104/209, dan Wesel). Step 2 me-rename folder basis ke tanggal pertama (`_DD-MM`), meng-copy ke tanggal kedua (`_DD-MM`), menulis `date.txt` masing-masing, dan mencatat riwayat pemisahan di `logs/asset_folder_mapping.json`. Step 3 menjadwalkan kedua folder, Step 4 mencap timemark sesuai tanggal, dan Step 5 memprioritaskan folder bersuffix sesuai tanggal pada nama berkas PDF target. Terverifikasi pada `PERAWATAN SINYAL B104 CLT-BOO 10-02-2025.pdf` (Tim 2) dan `11-02-2025.pdf` (Tim 1).


- [x] **Integrasi Step 3.5: Audit & Koreksi Personil ke Pipeline (Edit Tanggal & Edit Jam Foto)**: Disisipkan tepat setelah Step 3 (Scheduler) pada alur otomatis `Run All Pipeline Steps` dan `Run All Time Pipeline`, mengoreksi otomatis seluruh berkas temuan utama (< 1 KAUR atau < 2 PNC) di `02_pdf_target` menjadi 1 KAUR & 2 PNC sebelum masuk ke Step 4 & 5, serta menyediakan tombol eksekusi mandiri `Step 3.5: Koreksi Personil` di kedua tab dashboard.
- [x] **Audit Mode 2 Rekursif**: Folder kustom audit personil memindai PDF di folder utama dan seluruh subfolder menggunakan `Path.rglob('*.pdf')`.
- [x] **Perbaikan Parser Koreksi Personil Mode 2**: Log `[STEP 3.5]` dipindahkan ke `stderr`; stdout kini hanya JSON sehingga `JSON.parse(stdout)` tidak lagi gagal dengan `Unexpected token 'S'`.
- [x] **Export Jadwal Dinasan Terbaru**: Output Excel berisi `NO`, `PERAWATAN`, `PROGRAM`, `REALISASI`; nama aset sejenis digabung memakai koma dengan lokasi tetap di akhir, Program dan Realisasi berisi tanggal sama, tinggi baris otomatis, layout landscape, dan logo KAI tetap digunakan.
- [x] **Tautan Berkas PDF Target (Membuka di Tab Peramban & Aplikasi Komputer)**: Nama berkas PDF target pada tabel `List Personil`, modal koreksi tunggal, dan tabel dashboard dapat diklik langsung untuk membuka dan merender berkas PDF di tab baru peramban (`/api/pdf/view-target`), serta dilengkapi tombol `💻 Buka di Komputer` (`/api/pdf/open-system`) untuk membuka di aplikasi PDF default Windows (Adobe Acrobat, Foxit, SumatraPDF, dll).
- [x] **Audit & Koreksi Aturan Personil (1 KAUR, 2 PNC)**: Fitur pemeriksaan kepatuhan personil berkas PDF dengan 2 mode (Mode 1: Pipeline `02_pdf_target` & Mode 2: Folder Luar / Kustom), kartu metrik interaktif (Total: 430, Temuan Utama: 64, Temuan Biasa: 180, Sesuai: 186), filter cepat per jenis temuan, tombol batch auto-correct khusus temuan utama, serta modal koreksi berkas tunggal (`✏️ Koreksi`).
- [x] **Tabel Interaktif Personil Berkas & Zero-Popup UX**: Tabel spreadsheet penugasan personil di berkas PDF target (Format Schedule Sheet: No, Tanggal, Tim, List Personil, Status Aturan, Detail Aset, File PDF, Aksi), panel pengaturan profil yang dapat di-*expand/collapse*, dan 100% bebas dari popup peramban (`alert`, `prompt`, `confirm`).
- [x] **Multi-Preset / Simpanan List Pegawai**: Sistem profil simpanan personil (KUPT, KAUR, PNC) di tab `👥 Daftar Pegawai` (Buat Baru, Ganti Nama, Hapus, dan Pilih List Aktif otomatis tersinkron ke pipeline & ekspor Excel).
- [x] **Penyatuan Menu Web "Edit Tanggal Timemark"**: Penggabungan menu sidebar `Pipeline & Execution` dan `Photo Viewer` menjadi 1 tab terpadu **`Edit Tanggal Timemark`** (Upload Dropzones + Execution Controls + Dual Comparison Photo Gallery).
- [x] **Export Tablo Jadwal Perawatan Berkala (.xlsx)**: Generator Form Resmi KAI STE-RECORD-13.4.01 (2 Mode: Pipeline `schedule.json` & Folder Kustom via `scheduler.py`, 46 kelompok peralatan 100% matched, filter dinas P, dan UI modal di Web Dashboard)
- [x] **Sinkronisasi Routing BTP BD (Serat Optik)**: Standardisasi fungsi canonical `determine_btp()` di seluruh pipeline (Step 1, 3, 5) untuk menangani JPL lintas batas (`BOO-BOP`, `BOP-BTT`) dan OTB nama stasiun lengkap (`CIOMAS`, `BATU TULIS`, `CIGOMBONG`, `MASENG`) 100% konsisten ke BTP BD
- [x] **Selective Single-PDF Re-Merge**: Pembaruan berkas PDF individual secara instan (~1-2s) dari modal edit timemark, crop kolase, dan kartu foto tanpa re-run Step 5 seluruh 426 PDF
- [x] **Pipeline Integration Opsi 1**: Koreksi Core Serat Optik dijalankan otomatis di akhir "Run All" (Standar & Time)
- [x] Menu Web **🔌 Koreksi Core Optik** (2 Mode: Folder 5 / Pipeline vs Custom Folder, Fast Search `SERAT OPTIK`/`OTB`, JPL 12 Core & OTB 24*N, Outline Utuh 100%, Auto-Backup)
- [x] Detailed Error Logging & Exit Code Fix pada `export_pdf_foto.py` (Step 1)
- [x] Generator & Export **Daftar Dinasan Pegawai (Format Resmi KAI .xlsx)**
- [x] Menu Web **👥 Daftar Pegawai** & Alokasi Otomatis Roster Tim 2 per Tanggal
- [x] **Pipeline Edit Koordinat Foto** — Mapping Excel ke JSON, stempel koordinat dari `03_photos_export` ke `04_koordinat`, dan merge PDF target ke `05_koordinat`; backend Express/Next.js serta selector galeri Next.js 3-mode tersedia. (Fix 2026-09-16: penambahan inisialisasi `funcloc` dari schedule lookup untuk mengatasi `NameError`, serta penambahan koordinat Sinyal Muka MJ20 CLT `-6.527237, 106.800950` dan alias Catu Daya Cilebut `-6.530543, 106.800952` -> 135/135 foto 100% sukses, 0 skipped). Build Next.js lulus; masih ada warning lint unused lama.
- [x] **UI Express 1 Tab 3 Mode (2026-09-15 malam, SELESAI)** — 1 tab `📸 Pemrosesan Foto` + 3 tombol mode di atas (Tanggal/Jam/Koordinat); tombol step ikut mode (Tanggal=step1-5, Jam=step1-3.5+4_time+5_time, Koordinat=step1-3.5+4_coord+5_coord); 1 galeri kanan otomatis ganti (04_photos_edited / 04_Time / 04_koordinat); PDF Preview & Run All ikut mode. `node --check` + `py_compile` lulus.
- [x] **Fitur Geser Langsung Kotak Biru Tanggal (Interactive Drag & Nudge) di Modal Edit Timemark**:
  - Kotak overlay biru timemark kini dapat diklik dan digeser (*interactive drag & drop*) secara bebas langsung di atas gambar foto preview modal (`templates/index.html`).
  - Nilai slider Posisi X dan Posisi Y serta label piksel tersinkronisasi secara instan (*real-time*) saat kotak digeser.
  - Dilengkapi navigasi tombol panah keyboard (↑ ↓ ← →) untuk pergeseran presisi per 1 pixel (atau per 10 pixel dengan tombol Shift).
  - Mendukung kontrol mouse dan gesture layar sentuh (*touch events*).
- [x] **Tombol Opsi Crop Render vs Export Asli di Web App (2026-09-16, SELESAI)**:
  - Tombol mandiri di panel kontrol pipeline: `Step 1: Export Foto (Asli)` dan `📷 Step 1: Export Crop Render (300 DPI)` tersedia pada ketiga mode (Tanggal/Jam/Koordinat).
  - Tombol ganda di setiap kartu galeri foto: `🔄 Re-export Asli` (ekstrak stream foto mentah) & `📷 Crop Render` (render halaman PDF 300 DPI & crop foto agar watermark teks/vektor bawaan PDF ikut terbawa).
  - Tombol ganda di modul kolase foto: `🔄 Re-export Ori` & `📷 Crop Render`.
  - Backend & script pendukung: `scripts/export_pdf_foto.py` (--render-crop & RENDER_CROP), `scripts/reexport_single_asset.py` (--render-crop), dan `server.js` (`step1_crop` & `/api/photos/reexport-original` dengan `render_crop: true`). Next.js `pipeline-runner.ts` & `pipeline-dashboard.tsx` juga disinkronkan.
- [x] **Deteksi Personil & Audit Folder Kustom / Eksternal (2026-09-16, SELESAI)**:
  - Perbaikan bug cache server pada endpoint `/api/employees/file-personnel` di `server.js` (membaca `outputPath` hasil pemindaian folder kustom, bukan hardcoded `cachePath` dari 45 file bawaan target).
  - Mode pemindaian mandiri (*direct folder scan*) pada `scripts/extract_file_personnel.py` saat diarahkan ke folder luar pipeline (seperti 227 berkas Maret `SUDAH ADA KOORDINAT`).
  - Pembaruan `scripts/audit_and_correct_personnel.py` (penambahan kata henti dan full-page fallback pencocokan roster aktif untuk layout non-standar seperti CTC-CTS).
  - Integrasi ekstraksi personil pada `scripts/scheduler.py` dan `scripts/export_dinasan_excel.py` (pencarian PDF rekursif di subfolder dan konsolidasi seluruh teknisi per tanggal tugas).
  - **Optimasi Pemisahan Kolom Pengesahan vs Pelaksana**:
    - Kolom pengesahan resmi ("DISETUJUI OLEH" untuk KUPT seperti `S. SLAMET RIYADI` dan "DIKETAHUI OLEH" untuk Pengawas seperti `SUYADI`) adalah kolom pengesahan sah dan BUKAN temuan.
    - Pembacaan blok "DILAKSANAKAN OLEH" dibatasi ketat agar berhenti sebelum "NO. SC", "DISETUJUI", atau "DIKETAHUI", sehingga berkas CTC-CTS 100% bersih dari Suyadi & KUPT serta lolos berstatus OK (1 KAUR, 2 PNC).
    - Berkas yang terketik nama KUPT di kolom "Dilaksanakan Oleh" (5 berkas: Wesel W11, W13, W21, W23 CLT dan Catu Daya ER Radio BOO) tepat dilaporkan sebagai temuan `CRITICAL` (Temuan: Ada Personil Non-Teknisi di Kolom Pelaksana - Perlu Koreksi).
- [x] **Pencegahan Teks "NO. SC." Dobel pada Koreksi Nomor SC (2026-09-17, SELESAI)**:
  - Penghapusan teks `NO. SC.` tambahan pada fungsi `replace_page1_employee_names()` di `scripts/employee_manager.py`; koreksi nomor SC kini 100% murni mengisi nomor sertifikasi teknisi pada kolom nilai tanpa menulis teks `NO. SC.`.
  - Penambahan mekanisme deteksi dan peredaksian otomatis (`deduplicate_no_sc_in_doc`) untuk membersihkan berkas yang sempat memiliki teks `NO. SC.` dobel akibat proses sebelumnya.
  - Verifikasi dan pembersihan massal otomatis: 170 berkas di folder Juni (`6. JUNI\siap di OCR`) dan 73 berkas di folder Maret (`3. MARET`) berhasil dibersihkan (sisa berkas dengan NO. SC dobel: 0). Berkas contoh peraga `PERAWATAN AXLE COUNTER ZP 101A MSG-CCR 07-06-2025.pdf` terverifikasi rapi dan presisi dengan 1 label `NO. SC.`.

- [x] Stage 1-5 pipeline: export → extract dates → schedule → edit → merge
- [x] Web UI dengan SSE real-time log & stage indicator
- [x] All asset types + funcloc1 categories (PDSE, PTDS, PTLS, CATUDAYA, SERAT OPTIK, **JPL, CTS**)
- [x] Station-based folder hierarchy (`station/asset_type/detail/`)
- [x] SAP mapping dari Excel lokasi sheets (547 entries, clean)
- [x] CS→COS alias fix (output folder gak ada duplikat)
- [x] Step indicator bug fix: statuses reset on stop/re-run
- [x] Merged output hierarchy: `Tim_N/BTP/Station/Category/file.pdf` (funcloc1 regular)
- [x] Merged output hierarchy: `Tim_N/BTP/Station/file.pdf` (regular assets)
- [x] **PTPP → JPL** (folder JPL, Tim/BTP/Lokasi/JPL/0,50,100)
- [x] **CTS → folder CTS** (berdiri sendiri)
- [x] **BOP-BTT → BTP BD** (dulu BTP JAK, now join BOP/BTT/CGB/COS/MSG)
- [x] **WESEL/SINYAL/AXC → multi-row export** (1 PDF = 4-5 baris foto, funcloc per baris)

- **FIXED:** Deteksi personil kini membaca section `Dilaksanakan oleh` sampai `NO. SC`, memisahkan segmen koma, dan membuang checklist (`TIDAK MIRING`, `BERSIH`, `RETAK`, `KOTOR`, `TERTAMBAT`). Uji PDF menghasilkan `YATIYO`, `RAIHAN HERPIAN`, `IWAN SETIAWAN` tanpa teks checklist.
- **FIXED:** Parser personil mempertahankan batas baris PDF; nama `DONI FREDIANSYAH`, `MUHAMAD SOFYAN`, `AGUS PRIYONO`, dan lainnya tidak lagi menyatu dengan nama sebelah.
- **FIXED:** Export Excel memakai satu PDF representatif per tanggal, normalisasi roster, dan deduplikasi nama. Hasil Maret 2025 diuji: kolom PERSONIL berisi nama unik dipisah koma.
- **UPDATED:** Profil Personil — field Resor kini `Nama Lengkap`, `NIPP`, dan `Nomor SC`; field `Jabatan / Unit` dihapus.
- **UPDATED:** Kolom PERSONIL Excel memakai satu nama per baris, wrap text, dan tinggi baris dinamis agar nama tidak tampak menyatu.

- **FIXED:** Endpoint koreksi massal tahan warning `MuPDF error` sebelum output JSON; parser mengambil objek JSON valid dari stdout.

- **FIXED:** Pemindaian personil folder kustom mencari `pdf_path`, path relatif, dan basename secara recursive; validasi 406 PDF: `detected 406`, `empty 0`.

- **FIXED:** List Personil memakai `targetDir` folder kustom Mode 2; cache custom terpisah dari cache `02_pdf_target`, sehingga status tidak lagi memakai hasil pindai folder lama.

- **FIXED:** Parser personil mendeteksi nama yang berada setelah tabel checklist, selama setiap nama diikuti identifier `PRP`/`NIPP`; file AXC ZP 101A terbaca 3 nama.

- **FIXED:** Nama personil hasil fallback kini dicocokkan ulang ke profil KAUR/PNC sebelum status aturan dihitung; AXC ZP 101A menjadi `1 KAUR, 2 PNC`.

- **FIXED:** Audit menampilkan temuan nomor SC kosong atau `-` secara terpisah dari status KAUR/PNC, misalnya `✅ 1 KAUR, 2 PNC | ⚠️ SC belum lengkap: 2`.
- **FIXED:** Koreksi Nomor SC memakai profil pegawai dan hanya menulis kolom SC; nama personil tidak diganti.
- **VALIDATED:** Smoke test audit menemukan temuan SC pada folder sumber Maret; writer SC-only berhasil pada salinan PDF.

- **FIXED:** Koreksi Nomor SC memakai koordinat Y setiap nama pada PDF, lalu menulis SC profil pada baris yang sama; tidak lagi mengasumsikan urutan KAUR lalu PNC.
- **FIXED:** Semua nama terdaftar pada tabel diproses, termasuk file dengan lebih dari 3 personil.
- **VALIDATED:** `IWAN SETIAWAN`, `RAIHAN HERPIAN`, dan `DEDI SURYADI` menghasilkan SC pada koordinat Y baris masing-masing.

- **FIXED:** SC kosong dideteksi dari tanda `-` pada sel nilai di koordinat Y baris nama; bukan dari urutan teks halaman.
- **RULE:** Label `NO. SC.` dan `:` dipertahankan. Koreksi hanya mengganti `-` pada sel kanan dengan nomor profil nama pada baris yang sama.
- **FIXED:** Nama pejabat `Disetujui oleh` tidak dihitung sebagai SC kosong; baris personil wajib memiliki pasangan `PRP/NIPP` atau `-` di sel kanan.
- **VALIDATED:** `SADDAM YUSUF FATHIR` terbaca dari profil sebagai `PRP.181002.72321`; probe `ZP 10B MSG` berubah dari `-` ke nomor tersebut dan audit ulang menghasilkan nol SC kosong.

### Batch Results
- **2026-09-15 — Eksperimen segmentasi piksel tanggal lama (Gagal - Clutter tinggi):** Diuji metode segmentasi piksel terang (stroke/contrast) tanpa membaca teks dan tanpa acuan guide pada 18 PTLS dan 27 SERAT OPTIK via `logs/edit_timemark_segmentation_experiment.py`. Hasil visual pada foto 300x300: **gagal total**. Karena resolusi rendah dan foto buram, pola piksel putih dari rak server, kabel, rompi oranye, dan stiker panel memiliki kontras yang sama kuat dengan huruf tanggal. Akibatnya mask merah menempel di rak kabel dan baju petugas, tanggal lama tetap terlihat, dan textbox baru ditaruh di posisi acak. Kesimpulan: segmentasi piksel tanpa model AI terlatih (ground truth annotation) tidak bisa membedakan teks buram dari objek latar. Skrip produksi tidak disentuh; evidence montase: `logs/timemark_segmentation/ptls_montage_{1,2,3}.jpg` dan `serat_optik_montage_{1..5}.jpg`.
- **2026-09-15 — Selector tanggal lengkap PTLS v9 (12 otomatis, 6 manual aman):** Akar masalah `locate_date_box()` adalah berhenti pada detector pertama, sehingga guide merah/fallback dapat menang sebelum tanggal aktual. Script eksperimen kini mencoba OCR baris tanggal lengkap lebih dulu khusus PTLS memakai dua preprocessing (`threshold 140/PSM 6` dan `180/PSM 11`), menggabungkan hasil bbox yang sama, lalu menempatkan textbox ukuran tetap dari kiri-atas bbox tanggal. Bila OCR lengkap gagal, jalur amber lama tetap dipakai; bila amber juga tidak ada, hasil menjadi `stage_ptls_manual_review` tanpa output—tidak lagi memakai guide merah/fallback berisiko. Batch 18 PTLS: 12 otomatis, 6 manual tanpa file (`CGB/0,100`, `MSG/50,100`, `RADIO_CGB/50,100`), 0 fallback. Targeted assertions lulus untuk BOP, BTT, CGB, COS, MSG, RADIO_CGB. Regresi SERAT OPTIK: 27 diproses, 3 `JPL 01 BOO` tetap manual, dan 24/24 output identik SHA-256 dengan v8. Evidence: `logs/ptls_unified_date_detector_v9/all_ptls_v9.jpg` dan `logs/regression_serat_optik_unified_v9`. Masih script eksperimen; produksi tidak diubah.
- **2026-09-15 — OCR tanggal dekat guide v8 (`Sab, 28 Feb 2026` terdeteksi 3/3):** Untuk layout atas PTLS, OCR kini lebih dulu memindai crop dari tepi kiri sampai 70% lebar foto, maksimal 42 px di atas guide dan 2 px di bawahnya. Grayscale threshold 140, skala 10×, Tesseract PSM 6 menemukan token `Sab` pada BTT 0/50/100 dengan confidence 92–96. Textbox ukuran tetap sekarang dimulai dari bbox token hari: BTT/0 `x=6, y=179`, BTT/50 `x=6, y=180`, BTT/100 `x=6, y=179`; tidak lagi memakai anchor global salah `x=46`. Regresi seluruh PTLS BTP BD: 18 foto, 0 error; MSG tetap detector lama, CGB/50 tetap layout atas v7, CGB/0 dan CGB/100 tetap manual tanpa output. Regresi lintas kategori SERAT OPTIK memproses 27 foto; 24 output fisik identik SHA-256 dengan baseline v7 dan 3 `JPL 01 BOO` tetap manual tanpa output. Syntax dan `git diff --check` lulus. Evidence: `logs/debug_ptls_btt_sab_detector_v8/report.json`, `comparison_sab_detector_auto.jpg`, `logs/regression_ptls_near_guide_v8`, dan `logs/regression_serat_optik_near_guide_v8/sha256_vs_v7.json`. Masih script eksperimen; produksi tidak diubah.
- **2026-09-15 — Auto-layout PTLS v7 final (7 output benar, 2 manual aman):** Opsi layout tanggal di atas guide hanya dibuka untuk kategori `PTLS`, tetapi tetap wajib dibuktikan OCR pada setiap foto. Ukuran textbox tetap; X mengikuti anchor OCR; tepi bawah 2 px sebelum ujung guide. `BTT/{0,50,100}.jpg` berhasil pada `y=192–208`; `CGB/50.jpg` berhasil pada `y=207–222`; `MSG/{0,50,100}.jpg` tetap memakai detector merah lama pada `y=222–237`. `CGB/0.jpg` dan `CGB/100.jpg` tidak menemukan token hari/bulan/tahun, sehingga masuk `stage_amber_manual_review` dan tidak disimpan—posisi salah v6 tidak lagi dibuat. Fallback jumlah piksel putih untuk kandidat amber berbeda jauh dihapus. Regresi SERAT OPTIK: 24 output identik SHA-256 dengan v6; hanya `JPL 01 BOO/{0,50,100}.jpg` dihentikan manual karena tetap tanpa bukti OCR. Evidence: `logs/guide_experiment_dual_ocr_v7_final_ptls_btp_bd/final_audit.json` dan `comparison_7_outputs.jpg`. Masih script eksperimen; produksi tidak diubah.
- **2026-09-15 — Batch PTLS BTT/MSG/CGB v6 (9/9 output, 2 salah posisi):** `BTT` 3/3 konsisten pada textbox `y=207–223`; `MSG` 3/3 konsisten pada `y=222–237`; `CGB/50.jpg` benar pada `y=222–237`. `CGB/0.jpg` salah pada `y=3–18` dan `CGB/100.jpg` salah pada `y=117–132` karena OCR global/lokal gagal lalu fallback putih memilih kandidat v4; detector initial konsisten `y=224` pada ketiga CGB. Evidence: `logs/guide_experiment_dual_ocr_v6_ptls_btp_bd/report.json` dan `comparison_9.jpg`. Produksi tidak diubah; detector belum diperbaiki untuk dua kasus CGB.
- **2026-09-15 — Batch SERAT OPTIK BTP JAK v6 (27/27 lulus audit perbandingan):** Semua 27 foto berhasil dibuat ke `logs/guide_experiment_dual_ocr_v6_serat_optik_btp_jak`; gagal 0, tanggal hilang 0. Perbandingan SHA-256 terhadap batch v5: 26 output identik, hanya `ER SINYAL BOO/0.jpg` berubah sesuai target dari textbox salah `y=142–157` menjadi `y=184–199`. Evidence: `comparison_report.json` dan `changed_only_2x.jpg`. Produksi tidak diubah.
- **2026-09-15 — OCR lokal guide-aware v6 (`ER SINYAL BOO/0.jpg` fixed):** OCR global gagal karena area alamat terlalu besar. Fallback baru memindai strip sempit di sekitar masing-masing kandidat memakai grayscale, threshold 180, skala 8×, dan Tesseract PSM 13. Kandidat initial membaca `�Feb` (confidence 50, bbox `y=176–193`), kandidat v4 tidak membaca token tanggal; selector memilih guide fisik `y=186` dan textbox `y=184–199`. Regresi 8 foto lulus; tujuh posisi acuan tidak berubah. Evidence: `logs/guide_experiment_dual_ocr_v6_er_sinyal_boo_0`.
- **2026-09-15 — Batch SERAT OPTIK BTP JAK v5 (27/27 output, 4 perlu review):** Semua 27 foto dari 9 folder berhasil dibuat di `logs/guide_experiment_dual_ocr_v5_serat_optik_btp_jak`; gagal 0, manual 0, tanggal hilang 0. Stage: kandidat setuju 10, OCR pilih initial 9, OCR pilih v4 1, fallback putih 4, detector merah lama 3. Empat fallback putih (`ER SINYAL BOO/0.jpg` dan `JPL 01 BOO/{0,50,100}.jpg`) dipisahkan ke `review_ocr_failed_4.jpg` untuk pemeriksaan user; `ER SINYAL BOO/0.jpg` kemudian diperbaiki oleh OCR lokal v6. Report: `batch_report.json`; seluruh hasil: `contact_sheet_27.jpg`. Produksi tidak diubah.
- **2026-09-19 — Fitur Filter Berkas Target (02) & Penggantian/Revert Foto Cepat di Web:**
  - Penambahan dropdown Berkas Target di Galeri Pemrosesan Foto (Express port 5000 & Next.js port 3000) yang memfilter foto aset sesuai berkas target terpilih.
  - Tombol pintasan `🖼️ Foto` di tabel daftar berkas target di panel atas untuk langsung memfilter galeri dan scroll otomatis.
  - Fitur `📤 Ganti Foto` (upload foto pengganti dari komputer langsung ke `03_photos_export` dengan auto-reprocess Step 4) dan `↩️ Revert Asli` (memulihkan versi asli dari `{stem}.original_backup.jpg`).
  - Implementasi skrip `scripts/replace_export_photo.py` dan endpoint API terkait di server Express (`server.js`) dan Next.js (`web/`).
- **2026-09-21 — Fitur Baru Tombol `⚡ Fast Update Timemark` (Update Cepat Textbox dari Scheduler):**
  - Implementasi skrip `scripts/fast_update_timemark.py` yang memperbarui cap tanggal & jam pada foto berdasar `schedule.json` terbaru menggunakan cache koordinat `meta.json` tanpa OCR/deteksi ulang.
  - Menambahkan tombol pintasan `⚡ Fast Update Timemark` pada panel kontrol pipeline di samping Step 4 pada `templates/index.html`.
  - Terintegrasi penuh dengan auto-invalidation cache galeri web dan auto-reload visual.
- **2026-09-21 — Perbaikan Tombol Export Jadwal Dinasan + Personil & Export Tablo di Schedule Sheet:**
  - Menutup tag `<div>` lightbox modal (`photoZoomModal`) di `templates/index.html` yang sebelumnya membuat seluruh modal aplikasi (termasuk modal Tablo dan Dinasan) bersarang di dalam elemen tersembunyi berukuran 0x0 piksel.
  - Memperbaiki endpoint `GET /api/schedule/export-dinasan-excel` di `server.js` agar langsung menyajikan berkas hasil unduhan dan menangani ekspor tanpa personil dengan akurat.
  - Mengoptimalkan `scripts/export_dinasan_excel.py` dengan memanfaatkan personil yang sudah ada di `schedule.json`, mempercepat proses ekspor dari 21 detik menjadi 3 detik.
  - Pengujian otomatis Playwright memvalidasi tombol `Export Jadwal Dinasan`, `Export Jadwal + Personil`, dan `Export Tablo` berjalan 100% mulus dengan modal interaktif dan unduhan instan.
- **2026-09-19 — Pembatasan Baris Foto Non-Multi-Row PTLS BOO (Opsi A):**
  - Pembatasan kategori non-multi-row di `scripts/merge_pdf_foto.py` agar menghentikan pencarian aset segera setelah 1 baris foto lengkap (3 foto).
  - Dokumen `PERAWATAN PTLS BOO 26-02-2025.pdf` terverifikasi hanya menghasilkan 1 baris foto (3 foto), sementara kategori multi-row (AXC, Wesel, Sinyal) tetap mempertahankan seluruh baris foto lengkap.
- **2026-09-19 — Integrasi Detektor Google Cloud Vision & Lebar Textbox Dinamis:**
  - Opsi detektor ganda di Step 4 (`guide` vs `google_vision`) dengan tag metadata di `meta.json` dan penanganan jeda kuota interaktif.
  - Lebar textbox watermark kini dihitung dinamis sesuai panjang teks sebenarnya (`tw + 2 * pad_x`), menghasilkan kotak melengkung yang rapi tanpa sisa blur meluber.
- **2026-09-15 — Detector gabungan amber + OCR v5 (targeted lulus):** Empat sampel lulus assertion. `CLT/{0,50,100}.jpg` memakai textbox `y=207`; `ER SINYAL CLT/50.jpg` memakai `y=185`. Stage: initial menang 2, v4 menang 1, kandidat setuju tanpa OCR 1, manual 0. Tesseract hanya berjalan saat selisih kandidat >2 px; anchor dibatasi ke komponen putih bbox kata hari/bulan. Output dan montage: `logs/guide_experiment_dual_ocr_v5`. Syntax check lulus. Masih eksperimen; script utama dan `04_photos_edited` tidak diubah, batch penuh belum dijalankan.
- **2026-09-15 — Batch SERAT OPTIK/CLT v4 (audit belum lulus):** Tiga foto diproses ke `logs/guide_experiment_serat_optik_clt_v4`. `50.jpg` tetap benar pada guide `y=209`; `0.jpg` terdeteksi `y=125` dan `100.jpg` `y=193`, sehingga keduanya ditandai mencurigakan dan detector v4 belum siap untuk batch/produksi. Input/output 3/3, file terbaca, compile lulus; script utama dan `04_photos_edited` tidak diubah.
- **2026-09-14 — Optimasi Step 2 Extract Dates:** Step 1 berhenti menulis `date.txt`; Step 2 menjadi pemilik tunggal. Kategori biasa tidak lagi membuka PDF, `AXC`/`WESEL`/`SINYAL` tetap membaca halaman pertama, fallback dibatasi halaman pertama, write idempotent, dan log diringkas. Test sintetis lulus; validasi 4 PDF nyata menghasilkan 15 `date.txt`, 0 error, parity isi 15/15 dengan produksi.
- **2026-09-14 — Fix personil pada export Excel:** Export Jadwal Dinasan dan Export Jadwal + Personil kini memakai extractor yang sama dengan Audit Personil. Nama dibaca langsung dari kolom `Dilaksanakan oleh`, termasuk nama yang belum ada Profil Pegawai; schedule lama tanpa `pdf_path` memakai fallback field `file` ke `02_pdf_target`.
- **2026-09-14 — List personil asli PDF:** audit kini menyimpan teks personil yang terbaca langsung dari kolom `Dilaksanakan oleh` pada PDF, termasuk nama yang belum terdaftar di Profil Pegawai. Klasifikasi 1 KAUR/2 PNC tetap memakai roster profil.
- **2026-09-14 — Fix audit personil MuPDF warning:** parser API kini mengambil JSON valid dari output campuran, sehingga warning `MuPDF error` di stdout tidak lagi menyebabkan `Unexpected token 'M'`.
- **2026-09-14 — Export Jadwal + Personil:** ditambahkan tombol terpisah di Schedule Sheet dan Daftar Pegawai. Output `DAFTAR_DINASAN_PEGAWAI_DENGAN_PERSONIL_*.xlsx` memiliki kolom tambahan `PERSONIL`; tombol export lama tetap tanpa kolom tersebut.
- **2026-09-14 — Audit Jadwal Dinasan & Koreksi Personil:** menu Daftar Pegawai kini memiliki satu kartu untuk memilih sumber Pipeline/Folder PDF lain, menampilkan preview jadwal, mengoreksi personil per baris, lalu export Excel.
- **2026-09-14 — Format Excel Dinasan:** output memakai A4 landscape, fit width 1, tinggi halaman otomatis (`fitToHeight=0`), margin rapih, header berulang, lebar kolom dan tinggi baris mengikuti teks.
- **2026-09-14 — Popup pilihan sumber Schedule Sheet:** Export Jadwal Dinasan kini menampilkan dua mode: `Pipeline project` memakai `schedule.json`, atau `Folder PDF lain` memakai scan rekursif dan schedule sementara.
- **2026-09-14 — Schedule Sheet folder PDF eksternal:** tombol Export Jadwal Dinasan menerima root folder PDF, scheduler scan rekursif semua subfolder, membuat `logs/schedule_[BULAN]_[TAHUN].json`, lalu membuat `logs/DAFTAR_DINASAN_PEGAWAI_[BULAN]_[TAHUN].xlsx`; path PDF absolute dipakai untuk ekstraksi personil Tim 1.
- **2026-09-14 07:18 WIB** — PTPP JPL BTT Time pipeline: `edit_photo_time_only.py` memproses 3 foto sukses; merge Time sukses; total output 430 PDF.
- **2026-09-13** — PTPP JPL BTT regular/date pipeline: export, date extraction, timemark, dan merge sukses 430/430.
- **2026-07-16 09:30 WIB** — PTPP/JPL folder naming fix:
  - `extract_jpl_from_filename()`: parse `PERAWATAN PTPP JPL 27 BOO-CLT 26-01-2026.pdf` → `JPL 27 BOO-CLT`
  - `JPL_IDENTIFIER_OVERRIDES`: `JPL 26N BJD-CLT` → `JPL 26N CLT`
  - Verifikasi: 3 PTPP PDF test export → folder bener (`JPL 27 BOO-CLT`, `JPL 28 BOO-CLT`, `JPL 26N CLT`)
- **2026-07-15 15:55 WIB** — Full pipeline re-run (BTP routing + WESEL suffix + SINYAL multi-page):
  - Step 1: **4,521 foto** diekspor, **470 folder** (was 3594, +927)
  - Step 2: **278 date.txt** updated
  - Step 3: **schedule.json** updated (all 470 assets)
  - Step 4: **1,290/1,290 sukses, 0 gagal** (stage_1c: 1242, consensus: 6, fallback: 42)
  - BTP split: **311 BTP JAK + 159 BTP BD**
- Fix yang diterapkan:
  - **JPL fallback fix**: strip `JPL\d+ :` prefix before regex, handle `JPL 07 BOP-BTT` correctly
  - **PTPP JPL tanpa nomor fix (2026-09-13)**: `JPL10514 : SENTRANIK PPKA BTT` kini dipetakan ke `JPL BTT`, BTP BD; export menghasilkan 3 foto dan merge single-file sukses
  - **Error logging**: `_log_error()` → `logs/export_errors.xlsx` (only for true failures)
  - **Multi-page export**: scan ALL pages with ≥3 images for SINYAL/WESEL/AXC
  - **WESEL date suffix**: `_extract_date_suffix()` → `W21B2 BOO_02-01/` folders
  - **SINYAL dotted codes**: regex `\.?` for B, J, JL, L prefixes (B.108, J.10)
  - **PTPP JPL BTT Time fix (2026-09-14)**: `edit_photo_time_only.py` memproses 3 foto ke `04_Time/BTP BD/PTPP/JPL BTT`; merge Time sukses ke `05_pdf_merged_Time`; total output terverifikasi 430 PDF.
  - **Auto-Crop Kolase (White-Seam Isolation):** Selesai diimplementasikan di `scripts/auto_crop_collages.py` dan terintegrasi di `server.js` (Step 1.5 & Run All).
  - **Filter & Koreksi Kolase Web UI:** Filter `🗂️ FOTO KOLASE`, badge filter, dan `Editor Timemark Manual` telah terintegrasi untuk menampilkan foto hasil potong (cropped 300x300) secara presisi.
  - **Sinkronisasi Tim 1 & Tim 2 Multi-Team:** Parameter `--schedule` di `edit_timemark_ide1.py` telah diset default ke `schedule.json`. Distribusi output:
    - `04_photos_edited`: Tim_1 = 1.341 foto, Tim_2 = 75 foto (Total 1.416 foto, semua `meta.json` dan `detector.json` aman).
    - `05_pdf_merged`: Tim_1 = 310 PDF, Tim_2 = 25 PDF (Total 335 PDF sukses). 1 PDF (`PERAWATAN PTLS CGB 28-08-2025.pdf` / MULTIPLEX CGB) dilewati sesuai konfirmasi karena tidak ada dokumen inspeksi di sumber 2026.
  - **Edit timemark blur/textbox sync**: same `(x1,y1,x2,y2)` dimensions
  - **BOX_HEIGHT_RATIO**: reverted to 0.053 (original size)
- **2026-07-14 17:48 WIB** — Full pipeline clean run (BTP cross-search + no-photo fallback):
  - Step 1: 5,340 foto, Step 2: 852 sukses, Step 5: 165 PDF merged
  - BTP cross-search + no-photo fallback
- **2026-07-14 16:35 WIB** — WESEL/SINYAL/AXC multi-row support (sebelumnya)

---

## Quick Commands

### Web UI
```powershell
python app.py   # → http://localhost:5000
```

### CLI Pipeline
```powershell
python export_pdf_foto.py           # Step 1
python extract_pdf_dates.py          # Step 2
python scheduler.py                  # Step 3
python edit_timemark_ide1.py --schedule schedule.json   # Step 4
python merge_pdf_foto.py --schedule schedule.json       # Step 5
```

---

## 📅 Daily Logs

| Tanggal | Ringkasan Update | File Terkait |
|---------|------------------|--------------|
| [[Notes/Daily/2026-10-05\|**05 Okt**]] | **Pembersihan Berkas Sisa Eksperimen & Folder Uji Coba (~430 MB)**: Penghapusan model bobot AI YOLO (`yolov8n.pt`, dataset, labels), riset visi AI (Florence-2, Qwen-2.5-VL), folder output sementara (`04_Output_Temp`, `04_photos_sementara`, `scratch`), duplikat skrip di root, dan sisa berkas debug. Mempertahankan berkas kunci Excel aktif dan modul inti pipeline. | `scripts/`, `root`, `templates/`, `Notes/Daily/2026-10-05.md` |
| [[Notes/Daily/2026-09-21\|**21 Sep**]] | **100% Sukses Gabung (237/237 Dokumen)**: Penanganan variasi spasi nama berkas & folder, deteksi OCR dokumen scan, format pendamping log JSON (`logs/{month}_GAGAL_FALLBACK.json`), serta perbaikan tombol modal ekspor dinasan di Schedule Sheet. | `scripts/merge_pdf_foto.py`, `server.js`, `templates/index.html` |
| [[Notes/Daily/2026-09-20\|**20 Sep**]] | **Inline Timemark Editing & Swap Foto**: Kotak biru draggable langsung di galeri kartu, modal edit teks terisolasi per file (tanpa mengubah foto saudara), Zoom Lightbox interaktif, drag-and-drop tukar foto antar kartu, dan penuntasan split card `J10 BOO`. | `server.js`, `templates/index.html`, `scripts/replace_export_photo.py` |
| [[Notes/Daily/2026-09-19\|**19 Sep**]] | **Google Vision OCR, Fit Textbox Dinamis, & Fix Tuntas Merge PDF**: Dual Detector CLI `--detector`, filter galeri Web UI, lebar box pas ke teks; Restrukturisasi tombol `⚡ Merge PDF` per baris aset di header kartu, Pemetaan 1 foto ke multi-target PDF (`photo_target_mapping.json`), Sinkronisasi Multi-Tim Folder saat edit foto, Fix prioritas mutlak kandidat aset persis (`BOO` vs `RADIO_BOO`), Eliminasi thread-race `redirect_stdout` & streaming instan (`as_completed`), serta pencegahan tombol macet via safety timeout. | `scripts/merge_pdf_foto.py`, `scripts/scheduler.py`, `server.js`, `templates/index.html`, `scripts/edit_timemark_ide1.py`, `extract_pdf_dates.py`, `web/` |

| [[Notes/Daily/2026-09-18\|**18 Sep**]] | Fitur Geser Langsung Kotak Biru Tanggal (Interactive Drag & Nudge) di Modal Edit Timemark Manual & Optimasi Kecepatan Eksekusi Pipeline (Step 1-3 & Step 5). | `templates/index.html`, `scripts/export_pdf_foto.py`, `scripts/extract_pdf_dates.py`, `scripts/scheduler.py`, `scripts/merge_pdf_foto.py` |
| [[Notes/Daily/2026-09-17\|**17 Sep**]] | Perbaikan Koreksi Nomor SC: Pencegahan Duplikasi Label NO. SC. & Verifikasi Batch Otomatis Folder Maret & Juni (100% Bersih). | `scripts/employee_manager.py` |
| [[Notes/Daily/2026-09-16\|**16 Sep**]] | Integrasi Koreksi Personil 1 KAUR 2 PNC ke Pipeline Step 3.5 & Penyelarasan Koordinat Foto Sinyal Muka MJ20 CLT & Catu Daya Cilebut. | `scripts/employee_manager.py`, `scripts/edit_photo_coordinate_only.py`, `server.js` |
| [[Notes/Daily/2026-09-15\|**15 Sep**]] | **Aplikasi Web Next.js Fullstack (`web/`)**: Dashboard Modern Port 3000, Live Terminal SSE, Kontrol Pipeline Step 1-6 (Standar & Edit Jam), Dual Comparison Photo Gallery, Editor Timemark Modal + Single PDF Re-Merge, serta eksperimen detector tanggal lengkap PTLS v9. | `web/`, `web/src/app/`, `web/src/components/`, `scripts/edit_timemark_guide_experiment.py`, `package.json` |
| [[Notes/Daily/2026-09-13\|**13 Sep**]] | Fitur Baru **Export Tablo (.xlsx)** (Form STE-RECORD-13.4.01, 2 Mode, 46 Legenda, Penyelarasan Jadwal Furqon, Format `TABLO [BULAN] [TAHUN].xlsx`), Fix Single-PDF Re-Merge Modal Kolase, Penyatuan Menu Web **Edit Tanggal Timemark**, Fitur **Multi-Preset Simpanan List Pegawai**, serta **Tabel Interaktif Personil Berkas (Schedule Sheet Format)** & **Zero-Popup UX**. | `scripts/extract_file_personnel.py`, `config/employee_presets.json`, `scripts/export_tablo_excel.py`, `server.js`, `templates/index.html` |
| [[Notes/Daily/2026-09-12\|**12 Sep**]] | Fitur Koreksi Core Serat Optik (2 Mode, Outline Utuh), Selective Single-PDF Re-Merge modal, dan Sinkronisasi Wilayah BTP BD (0 mismatch). | `scripts/correct_serat_optik_cores.py`, `scripts/merge_pdf_foto.py`, `scripts/scheduler.py`, `server.js` |
| [[Notes/Daily/2026-08-30\|**30 Agt**]] | Modul Edit Jam Foto (`04_Time`), Galeri Asset Row Grouping (0/50/100%), Filter Kalender per Tanggal, dan Tab Baru `📅 Schedule Sheet` (Spreadsheet Viewer + Export Excel). | `scripts/edit_photo_time_only.py`, `scripts/export_schedule_excel.py`, `server.js`, `templates/index.html` |
| [[Notes/Daily/2026-07-16\|**16 Jul**]] | Investigasi JPL naming inconsistency. Root cause: KEL2 pakai funcloc (salah), harusnya filename. Buat ADR-009, plan skrip `export_kel2_from_filename.py`. | `export_pdf_foto.py`, `Notes/Decisions/ADR-009-kel2-filename-export.md` |
| [[Notes/Daily/2026-07-15\|**15 Jul**]] | BTP routing fix (re.findall compound ID). WESEL suffix folders. SINYAL multi-page. Edit timemark: date.txt reading, blur/textbox sync. BTP reorg 122 assets. 4521 foto, 1290 edit, 278 dates. | `export_pdf_foto.py`, `edit_timemark_ide1.py` |
| [[Notes/Daily/2026-07-14\|**14 Jul**]] | Full pipeline fix: OTB→TELEKOM, BANGUNAN→PDSE, MULTIPLEX→PTLS, BOP-BTT split. Clean run: 474 foto, 156 edit, 79 PDF. | `export_pdf_foto.py`, `merge_pdf_foto.py` |
| [[Notes/Daily/2026-07-13\|**13 Jul**]] | Station-based folder hierarchy (BREAKING CHANGE). 7 asset types full support. Dead code cleanup. | Semua 6 script + 3 JSON |
| [[Notes/Daily/2026-07-12\|**12 Jul**]] | Browser freeze fix (limit 100 files). EventSource reconnect fix. | `app.py`, `index.html` |
| [[Notes/Daily/2026-07-11\|**11 Jul**]] | Folder Consensus fix: input folder aset tunggal. | `edit_timemark_ide1.py` |
| [[Notes/Daily/2026-07-10\|**10 Jul**]] | Pipeline full batch 2025: 1782 foto → 1530 edit → 97 PDF merged | Semua script |
| [[Notes/Daily/2026-07-09\|**9 Jul**]] | Stage 1c Red Guide Anchor. 237/237 sukses. | `edit_timemark_ide1.py` |
| [[Notes/Daily/2026-07-08\|**8 Jul**]] | Optimasi mask (16px tinggi, narrow mask 5px). Cleanup. | `edit_timemark_ide1.py` |
| [[Notes/Daily/2026-07-07\|**7 Jul**]] | Dynamic Gap Stage 2. Thresh 215. Opsi A ratio-based. | `edit_timemark_ide1.py` |

📄 Detail lengkap → [[Notes/Daily/]]


---

## API Endpoints (app.py)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/status` | is_running, current_step, progress, step_statuses |
| `POST /api/run {"step":"all|step1..5"}` | Jalankan pipeline |
| `POST /api/stop` | Hentikan proses |
| `GET /api/stream-logs` | SSE real-time stdout |
| `GET /api/stream-stages` | SSE stage events (dari edit_timemark) |
| `GET /api/stage-summary` | counts + details per stage |
| `GET /api/files` | PDF list (limit 100) |
| `GET /api/open-folder/<key>` | Buka folder di Explorer |

---

## 📎 Referensi Lengkap

| Dokumen | Keterangan |
|---------|------------|
| [[AGENTS.md]] | Function reference, detection logic, debugging patterns |
| [[README.md]] | Tujuan project, batasan, pipeline overview |
| [[setup.md]] | Instalasi, dependensi, cara menjalankan |
| [[system_architecture_gabung foto ke pdf\|Arsitektur Merge PDF]] | Flowchart & komponen merge_pdf_foto.py |
| [[Data Acuan Tenaga Perawatan Gabungan\|Data Acuan Tenaga]] | Standar waktu perawatan per aset (Sinyal + Telekom) |
| [[Notes/Test Results\|Hasil Test]] | Riwayat pengujian batch & unit |

### ADR (Architecture Decision Records)

| ADR | Keputusan |
|-----|----------|
| [[Notes/Decisions/ADR-001 - Pillow and Numpy instead of OpenCV\|ADR-001]] | Pillow + Numpy, bukan OpenCV |
| [[Notes/Decisions/ADR-002 - PDF Image Export via pypdf and pdfplumber\|ADR-002]] | Ekstraksi gambar via pypdf (original images) |
| [[Notes/Decisions/ADR-003 - PDF Layout Parsing and Output Structure\|ADR-003]] | Aturan parsing layout PDF & struktur output |
| [[Notes/Decisions/ADR-008-fix-36-missing-funcloc\|ADR-008]] | Fix 36 missing funcloc photos (pending) |
| [[Notes/Decisions/ADR-009-kel2-filename-export\|ADR-009]] | KEL2 folder dari filename, bukan funcloc (planning) |
| [[Notes/Decisions/ADR-010-export-tablo-excel\|ADR-010]] | Generator Excel Tablo Checklist Form STE-RECORD-13.4.01 |
| [[Notes/Decisions/ADR-011-nextjs-web-app-architecture\|ADR-011]] | Arsitektur Web App Fullstack Next.js 14 (Port 3000) |
| [[Notes/Decisions/ADR-012-standalone-desktop-executable\|ADR-012]] | Standalone Desktop Executable WebView2 & Portable Node |
| [[Notes/Decisions/ADR-013-penanganan-aset-target-multi-tanggal\|ADR-013]] | Penanganan Otomatis Aset Target Multi-Tanggal (Tanggal Ganda) |
| [[Notes/Decisions/ADR-014-google-vision-detector-and-dynamic-textbox\|ADR-014]] | Integrasi Detektor Google Cloud Vision & Optimasi Textbox Dinamis |

