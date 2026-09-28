# ADR-011: Arsitektur Aplikasi Web Modern Berbasis Next.js 14 (App Router)

- **Status:** Diterima & Diimplementasikan
- **Tanggal:** 2026-09-15
- **Komponen:** `web/` (Next.js 14, TypeScript, Tailwind CSS, Lucide React), `web/src/app/`, `web/src/components/`, `web/src/lib/`

---

## 1. Konteks & Latar Belakang

Sebelumnya, antarmuka grafis sistem OCR-FOTO-P3STE menggunakan antarmuka lawas berbasis Express.js (`server.js`) dan template HTML statis tunggal (`templates/index.html`). Seiring bertambahnya fitur sistem (koreksi manual timemark, audit personil 1 KAUR 2 PNC, audit tanggal dokumen PDF, manajemen multi-preset pegawai, dan generator Tablo Excel resmi KAI), antarmuka lama memiliki beberapa keterbatasan:

1. **Kompleksitas State**: Manajemen interaksi DOM manual (vanilla JS) dalam satu file HTML besar menjadi rapuh terhadap bug dan sulit diperluas.
2. **Keterbatasan UX**: Penggunaan popup peramban bawaan (`alert`, `confirm`) mengganggu alur kerja pengguna dan tidak mendukung validasi real-time.
3. **Keterikatan Pipeline & Visual**: Tidak ada pemisahan modular yang bersih antara eksekusi pipeline terminal, peninjauan visual komparasi foto (sebelum vs sesudah), pengaturan personil, audit kepatuhan, dan ekspor dokumen dinas.

Oleh karena itu, diputuskan untuk membangun aplikasi web modern berskala penuh (*fullstack*) di dalam direktori `web/` menggunakan framework Next.js 14.

---

## 2. Keputusan Desain & Arsitektur

### A. Teknologi Inti
- **Framework:** Next.js 14 dengan App Router (`src/app/`)
- **Bahasa:** TypeScript (Strict Type Checking)
- **Styling:** Tailwind CSS (Modern Industrial Dark Theme)
- **Komponen Ikon:** Lucide React
- **Komunikasi Data:** Server-Sent Events (SSE) untuk live streaming output pipeline log

### B. 5 Modul Utama Antarmuka
Aplikasi web dibagi menjadi 5 modul terpadu dengan tab navigasi:

1. 🚀 **Pipeline & Eksekusi (`pipeline-dashboard.tsx` & `terminal-console.tsx`)**:
   - Kartu metrik penghitung berkas real-time untuk folder `01_pdf_source` s.d. `05_pdf_merged`.
   - Tombol eksekusi cepat: *Run All Pipeline*, *Run All Time Pipeline*, dan pembatalan eksekusi (*Stop Process*).
   - Grid kontrol individual untuk Step 1 s.d. Step 6 (ekstraksi, tanggal, scheduler, koreksi personil 3.5, watermark, merge, dan koreksi core optik).
   - Konsol terminal interaktif dengan auto-scroll, pencarian log, salin clipboard, dan pembersihan layar.

2. 🖼️ **Galeri Foto & Editor Timemark (`photo-gallery.tsx` & `timemark-editor-modal.tsx`)**:
   - Tampilan visual komparasi foto dual-view (Foto Mentah dari `03_photos_export` vs Foto Terkoreksi dari `04_photos_edited` / `04_Time`).
   - Filter cepat berdasarkan wilayah kerja (BTP JAK, BTP BD, Semua) dan kategori aset (AXC, WESEL, SINYAL, JPL, dll.).
   - Modal interaktif penggeser posisi textbox (koordinat Y dan X) dengan tombol presisi (+/- 1px atau 5px), input tanggal/jam dinas, dan tombol *Simpan & Re-Merge PDF* instan (~1-2 detik).

3. 👥 **Daftar Pegawai & Roster (`employee-manager.tsx`)**:
   - Pengelolaan profil pegawai multi-preset (Buat Simpanan Baru, Ganti Nama, Hapus, Pilih Preset Aktif).
   - Formulir KUPT Resor, tabel data KAUR, dan tabel data PNC dengan penambahan/penghapusan baris dinamis.
   - Sinkronisasi otomatis ke `config/employee_presets.json` dan `config/daftar_pegawai.json`.

4. 🛡️ **Audit Dokumen & Personil (`personnel-audit.tsx` & `document-date-audit.tsx`)**:
   - **Audit Kepatuhan Personil**: Memeriksa pemenuhan aturan 1 KAUR & 2 PNC pada berkas PDF target (Mode Pipeline `02_pdf_target` maupun Folder Luar). Menyediakan metrik temuan (Utama, Biasa, Sesuai), auto-correct massal temuan utama, dan modal koreksi berkas tunggal.
   - **Audit Tanggal PDF**: Memindai kesesuaian tanggal text layer halaman pertama dan header `FOTO DOKUMENTASI` terhadap tanggal filename PDF via `correct_pdf_dates.py`. Tombol auto-koreksi atomik langsung memperbaiki berkas PDF berstatus BERBEDA.

5. 📊 **Export Excel Resmi KAI (`excel-export-panel.tsx`)**:
   - **Form Tablo Checklist & Perawatan Berkala (STE-RECORD-13.4.01)**: Generator Excel resmi dengan logo KAI, legenda 46 kelompok peralatan, dan matriks penugasan personil.
   - **Daftar Dinasan Pegawai**: Generator Excel jadwal dinasan resmi KAI per tanggal.
   - **Data Aset**: Generator tabel inventaris aset per baris.

### C. Abstraksi Resolusi Jalur (`web/src/lib/paths.ts`)
Fungsi `getRootDir()` secara otomatis mendeteksi apakah proses berjalan dari dalam subfolder `web/` atau dari direktori root proyek (`APP_DIR`), memastikan seluruh path folder data (`01_` s.d. `05_`), `scripts/`, `config/`, dan `logs/` selalu mengarah ke lokasi fisik yang benar.

### D. Streaming Berkas Statis Anti-Cache (`web/src/app/api/static/[...path]/route.ts`)
Endpoint khusus yang membaca file foto JPG dan PDF dari sistem berkas lokal lalu mengalirkannya ke antarmuka web dengan header:
`Cache-Control: no-store, no-cache, must-revalidate, proxy-revalidate`
Hal ini menjamin preview foto yang baru saja diedit atau di-remerge langsung tampil terkini di browser tanpa tertahan cache.

---

## 3. Konsekuensi & Keuntungan

1. **Zero-Popup UX**: Seluruh pesan kesalahan, konfirmasi, dan peringatan ditampilkan melalui dialog modal in-app atau badge visual non-intrusif.
2. **Modular & Maintainable**: Kode antarmuka terstruktur rapi per fitur dengan pemisahan client component dan server route handler.
3. **Independensi Bersama**: Aplikasi web Next.js dapat dijalankan di port 3000 berdampingan dengan `server.js` lama di port 5000 tanpa menimbulkan konflik berkas.
