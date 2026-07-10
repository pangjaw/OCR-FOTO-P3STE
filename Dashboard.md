# 🗂️ OCR Foto Timemark - Project Dashboard

> [!abstract] **Project Overview**
> Project ini digunakan untuk melakukan koreksi tanggal watermark Timemark pada foto dokumentasi kerja secara batch, baik dari folder foto langsung maupun hasil ekstraksi file PDF.

---

## 🚀 Quick Access
- 📖 **[[README]]** - Tujuan project & Batasan Utama
- 🛠️ **[[setup]]** - Instalasi, Dependensi & Cara Menjalankan Script
- 🧪 **[[Notes/Test Results|Test Results]]** - Riwayat Hasil Pengujian Script

---

## 📌 Project Status
### Active Scripts
- `[[app.py]]` - Server Web Lokal (Dashboard UI) untuk mempermudah jalannya seluruh alur kerja.
- `[[edit_timemark_ide1.py]]` - Script utama pengedit watermark (Ide 1 / Y-center average + voting folder).
- `[[export_pdf_foto.py]]` - Script ekstraksi foto asli dari PDF.
- `[[merge_pdf_foto.py]]` - Script penggabung foto baru (format 2026) kembali ke PDF lama (format 2025) dengan menghapus kolase lama.
- `[[extract_pdf_dates.py]]` - Script ekstraksi tanggal baru otomatis dari PDF target di folder `pdf_imo/`.

### Status Kerja
```mermaid
kanban
%% Note: Obsidian Kanban plugin supports this or standard lists, this is rendered as code/mermaid %%
graph TD
    todo[To Do] --> in_progress[In Progress] --> done[Done]
    
    click todo href "obsidian://open?vault=OCR-FOTO-P3STE&file=Dashboard"
```

- **Done (Selesai):**
	- [x] **Web UI Dashboard Terpadu (`app.py`):** Penggabungan seluruh skrip ke dalam satu UI web lokal modern dengan visual *dark glassmorphism*, pemantauan progres real-time via log terminal, dan konfigurasi direktori kerja.
	- [x] **Dukungan Subfolder Aset Seluruh Pipeline:** Modifikasi alur kerja pada skrip ekspor, ekstraksi tanggal, dan penggabungan PDF agar mempertahankan struktur subfolder aset (seperti subfolder per resor di `input_pdf/` dan `pdf_imo/`) ke dalam hasil akhir di `hasil_gabung/`.
	- [x] **Ekstraksi Tanggal Otomatis & Pemetaan `date.txt`:** Implementasi script `extract_pdf_dates.py` untuk mengambil tanggal baru dari halaman foto dokumentasi PDF target di folder `pdf_imo/`, menerjemahkannya ke Bahasa Indonesia disingkat, dan menyimpannya sebagai file metadata `date.txt` per folder aset.
	- [x] **Integrasi Tanggal Dinamis di Script Utama:** Modifikasi `edit_timemark_ide1.py` agar secara otomatis membaca tanggal baru dari file `date.txt` di subfolder aset secara dinamis tanpa intervensi manual (prompt) dari user.
	- [x] **Gabung Foto PDF (`merge_pdf_foto.py`):** Berhasil membuat skrip penggabung foto hasil edit (format 2026) kembali ke PDF lama 2025. Hasil batch 19 PDF: 19 berkas sukses ter-upgrade dengan layout 2026 yang baru secara dinamis dan rapi.
	- [x] **FINAL — Semua 168 foto Berhasil:** Deteksi noise kuning Red Guide di ZP 13 dengan Opsi A (ratio-based `r > g*1.3`) sukses. Stage logging ditambahkan agar user tahu stage mana yang dipakai per file. Semua file lolos dengan Stage 1 (Tanggal), Stage 2 (Alamat), atau Stage 3 (Red Guide).
	- [x] Integrasi 3 Stage ke Script Utama (Tukar Stage): Prioritas 1 (Tanggal Konsensus), Prioritas 2 (Alamat Konsensus), Prioritas 3 (Red Guide Lokal) untuk mengabaikan Red Guide Palsu.
	- [x] Deteksi Kegagalan (Stage 4): Melewati (skip/tidak memproses) file yang gagal dideteksi secara otomatis dan menampilkan warning detail di akhir run konsol.
	- [x] Implementasi penyejajaran batas atas Red Guide (`y1 = guide_y1`), tinggi box 13px, dan padding mask 2px untuk visual 100% rapi dan aman dari tabrakan alamat.
	- [x] Rerun Batch seluruh 168 foto dengan logic Tukar Stage sukses diproses 100% tuntas ke `output_proses_all`.
	- [x] Logika Folder-Level Red Guide Consensus Voting: Mempindai semua file di folder untuk menentukan Red Guide mayoritas dan mencegah Red Guide Palsu (seperti Y1=185 pada JL52 50.jpg) mengacaukan penempatan.
	- [x] Logika Folder-Level Cross-File Reference (Konsensus Cerdas): implementasi pre-scan folder untuk menentukan posisi Y tanggal/alamat berdasarkan voting mayoritas $\ge 2$ file sejenis.
	- [x] Batch Ulang seluruh 168 foto dengan logic Mask Mepet Textbox + Tinggi Box 16px (Final) sukses diproses 100% bersih ke `output_proses_all`.
	- [x] Optimasi Mask Mepet Textbox: Menghilangkan perluasan mask ke atas dan menaikkan tinggi date box baru `box_h` menjadi `int(h * 0.053)` (16px), menutupi tanggal lama secara bersih di dalam area textbox tanpa blur yang lebar di luar.
	- [x] Optimasi lebar blur (Narrow Mask): mempersempit tinggi perluasan area hapus ke atas dari `14px` menjadi `5px`.
	- [x] Perbaikan bug logika pada Erase Mask di `process_image`: memperluas range mask biner `rounded_rectangle` ke arah atas (dimulai dari Y=0 pada area crop) agar tambahan tinggi 14px untuk penghapusan tanggal lama benar-benar diproses oleh `diffuse_fill_region`.
	- [x] Batch Ulang seluruh 168 foto dengan logic Stage 1 Thresh 215 + Fallback clipping range (Gap 0px) selesai sukses diproses ke `output_proses_all`.
	- [x] Optimasi loop binarisasi Stage 1 dengan menambahkan threshold tinggi `215` (melawan noise latar belakang abu-abu terang), membuat ZP 92 50 berhasil dideteksi via Stage 1 dengan confidence 95%.
	- [x] Batch Ulang seluruh 168 foto dengan logic Dynamic Gap terbaru (Gap 0px untuk baris 1 alamat) sukses diproses ke `output_proses_all`.
	- [x] Implementasi Dynamic Gap pada Stage 2 fallback berbasis rasio Y alamat teratas yang rata-kiri (`left < 30px`), menyelesaikan perbedaan deteksi baris alamat secara otomatis.
	- [x] Verifikasi Stage 2 fallback (address detection) sukses pada L62A 50 dan JL32A 50.
	- [x] Confidence filter (< 30) di Stage 1 keyword detection — kurangi false positive AM/PM dari noise OCR.
	- [x] Stage 2 fallback: deteksi alamat area kiri-bawah (threshold 150 PSM 4), prioritaskan text rata-kiri (left < 30).
	- [x] Folder-level OCR voting: 2+ file setuju Y → apply ke semua file di folder itu.
	- [x] Expanded erase area (+14px ke atas) nutup teks lama 2 baris.
	- [x] `--y-override` CLI arg buat paksa Y manual (skip OCR).
	- [x] Batch 168/168 foto: lulus bersih mutlak (final).
	- [x] **Opsi A (ratio-based red detection):** Toleransi noise kuning di Red Guide — `r > g*1.3` menggantikan `r > g+22` — ZP 13 guide_y1 kembali normal 185px.
	- [x] **Stage Logging:** Setiap file cetak stage yang dipakai (Stage 0/1/2/3/4) untuk transparansi proses.
	- [x] **Cleanup total project:** Hapus semua scratch, debug scripts, test output, stale directories. Hanya menyisakan script utama + folder kerja.
	- [x] Cleanup project: hapus scratch, tmp, old scripts.
	- [x] Eksperimen PaddleOCR — gagal (oneDNN bug di Windows, skip).
	- [x] Eksperimen EasyOCR — preprocessing gak bantu (gak bisa fokus 1 baris).
	- [x] Tesseract `--psm 7` tetap engine terbaik untuk kasus ini.

---

## 📅 Daily Logs & Notes
- [[Notes/Daily/2026-07-10|Log Hari Ini - 2026-07-10]]
- [[Notes/Daily/2026-07-09|Log Kemarin - 2026-07-09]]
- [[Notes/Daily/2026-07-08|Log - 2026-07-08]]
- [[Notes/Daily/2026-07-07|Log - 2026-07-07]]
- 📂 [[Notes/Templates/Template - Daily Note|Daily Note Template]]
- 📂 [[Notes/Templates/Template - Bug Report|Bug Report Template]]
- 📂 [[Notes/Templates/Template - Architecture Decision|ADR Template]]

---

## 🏛️ Architecture Decisions (ADR)
1. **[[Notes/Decisions/ADR-001 - Pillow and Numpy instead of OpenCV|ADR-001: Penggunaan Pillow & Numpy untuk Manipulasi Watermark]]**
2. **[[Notes/Decisions/ADR-002 - PDF Image Export via pypdf and pdfplumber|ADR-002: Ekstraksi Gambar Asli PDF menggunakan pypdf]]**
3. **[[Notes/Decisions/ADR-003 - PDF Layout Parsing and Output Structure|ADR-003: Aturan Parsing Layout PDF & Struktur Output Foto]]**

---

> [!tip] **Tips Obsidian**
> Tekan `Ctrl + Klik` (atau `Cmd + Klik` di Mac) pada link di atas untuk langsung membuka atau membuat catatan tersebut. Gunakan **Graph View** (ikon jaring laba-laba di kiri) untuk melihat koneksi visualnya!
