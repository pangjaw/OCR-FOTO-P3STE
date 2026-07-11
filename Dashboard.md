# 🗂️ OCR Foto Timemark - Project Dashboard

> [!warning] **🤖 Untuk AI Assistant: Baca [[AGENTS]] terlebih dahulu!**
> File ini berisi status tracker dan checklist. Untuk memahami kode, fungsi, dan alur data, **wajib** baca [[AGENTS]] sebelum melanjutkan.

> [!abstract] **Project Overview**
> Project ini digunakan untuk melakukan koreksi tanggal watermark Timemark pada foto dokumentasi kerja secara batch, baik dari folder foto langsung maupun hasil ekstraksi file PDF.

---

## 🚀 Quick Access
- 📖 **[[README]]** - Tujuan project & Batasan Utama
- 🛠️ **[[setup]]** - Instalasi, Dependensi & Cara Menjalankan Script
- 🧪 **[[Notes/Test Results|Test Results]]** - Riwayat Hasil Pengujian Script

---

## 📁 Struktur Folder (Baru — 2026-07-11)

```
root/
├── 01_pdf_source/          ← PDF mentah
├── 02_pdf_target/          ← PDF target/imo
├── 03_photos_export/       ← source images hasil export
├── 04_photos_edited/       ← foto sudah edit timemark
├── 05_pdf_merged/          ← PDF hasil gabung
├── backup_script_v1/
├── Notes/
├── logs/
├── *.py, *.json, *.md di root
```

## 📌 Project Status
### Active Scripts
- `[[app.py]]` - Server Web Lokal (Dashboard UI) untuk mempermudah jalannya seluruh alur kerja.
- `[[edit_timemark_ide1.py]]` - Script utama pengedit watermark: **HSV Orange Isolation + Fixed-offset Stage 1c** (Red Guide anchor, X=6px offset, Y-center aligned). Fallback: `get_text_box()`. No OCR, no consensus voting. 237/237 sukses.
- `[[export_pdf_foto.py]]` - Script ekstraksi foto asli dari PDF.
- `[[merge_pdf_foto.py]]` - Script penggabung foto baru (format 2026) kembali ke PDF lama (format 2025) dengan menghapus kolase lama.
- `[[extract_pdf_dates.py]]` - Script ekstraksi tanggal baru otomatis dari PDF target di folder `02_pdf_target/`.
- `[[scheduler.py]]` - [NEW] Script penjadwalan 2 Tim (07:00-18:00) — baca PDF urut + `asset_waktu_mapping.json` → output `schedule.json`.

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
	- [x] **Dukungan Subfolder Aset Seluruh Pipeline:** Modifikasi alur kerja pada skrip ekspor, ekstraksi tanggal, dan penggabungan PDF agar mempertahankan struktur subfolder aset ke dalam hasil akhir.
	- [x] **Ekstraksi Tanggal Otomatis & Pemetaan `date.txt`:** Implementasi script `extract_pdf_dates.py` untuk mengambil tanggal baru dari halaman foto dokumentasi PDF target di folder `02_pdf_target/`, menerjemahkannya ke Bahasa Indonesia disingkat, dan menyimpannya sebagai file metadata `date.txt` per folder aset.
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

- **Done (Time + 2 Teams Scheduling):**
	- [x] **Mapping Manual Aset → Waktu:** `asset_waktu_mapping.json` — scan PDF halaman 1.
	- [x] **`scheduler.py` [NEW]:** Baca PDF + mapping + date → hitung jadwal 07:00-18:00 per Tim → output `schedule.json`.
	- [x] **`edit_timemark_ide1.py` — Arg `--schedule` & Tim folder:** `--schedule schedule.json`, format `"Rabu, Jul 08 2026 09:30"`, output ke `04_photos_edited/Tim_{n}/...`.
	- [x] **`merge_pdf_foto.py` — Arg `--schedule`:** path foto dari `Tim_{n}` folder via schedule.json lookup.
	- [x] **Overflow Aman:** Aset mulai < 18:00 tetap selesai 3 fotonya, file berikutnya pindah Tim/reset jam.
	- [x] **Stage 1c (Red Guide Anchor):** Untuk foto dengan Red Guide terdeteksi tapi OCR gagal total (seperti CLT), gunakan posisi baru: textbox di KANAN guide, center sejajar dengan bagian ATAS guide, box extends 25% up / 75% down. Berhasil menangani 18/18 foto gagal sebelumnya (6 folder: ZP 12B/13/14B/20A/24B CLT + ZP 31D BOO). Total: 237/237 foto berhasil (100%).

- **Done (Testing Pipeline Penuh):**
	- [x] **Testing pipeline penuh (Stage 1→5):** `export_pdf_foto.py` → `extract_pdf_dates.py` → `scheduler.py` → `edit_timemark_ide1.py --schedule` → `merge_pdf_foto.py --schedule`. **43 PDF berhasil digabung**, 36 di-skip (foto tidak lengkap), 0 error. Tim rotation & overflow berfungsi.
	- [x] **Verifikasi visual Stage 1c:** 18 foto Red Guide Anchor (CLT + ZP 31D BOO) berhasil diproses dengan posisi textbox benar di kanan guide, center sejajar atas guide.
	- [x] **Step Indicator Bar di Web UI Dashboard:** Visual bar dinamis (Step 1-5) dengan indikasi warna (Indigo: Active, Hijau: Done, Merah: Error) yang tersinkronisasi via polling status API `/api/status`.
	- [x] **Perbaikan Path Lookup Foto pada `merge_pdf_foto.py`:** Memperbaiki pencarian foto di folder flat per tim (`Tim_N/...`) pada mode `--schedule` sehingga pipeline tahap 5 dapat menyisipkan foto hasil edit secara sukses.

- **Done (Full Pipeline Batch 2025 - 165 PDF):**
	- [x] **Pipeline end-to-end 2025 dataset:** `export_pdf_foto.py` (1782 foto) → `extract_pdf_dates.py` (541 date.txt) → `scheduler.py` (schedule.json) → `edit_timemark_ide1.py --schedule` (1530/1530 sukses) → `merge_pdf_foto.py --schedule` (**97 PDF sukses, 15 skip, 53 gagal**).
	- [x] **53 PDF gagal:** Format SERAT OPTIK, TELEKOMUNIKASI, CATU DAYA, PINTU PERLINTASAN, CTC CTS — tidak memiliki aset di halaman 1 (layout beda dari AXC/WESEL/SINYAL). Perlu parser terpisah kalau mau diproses.
	- [x] **Fix Browser Freeze (`app.py`):** Limit file listing API ke 100 file + metadata total/truncated. Frontend hanya render 100 `<li>` max + info count.

---

## 📅 Daily Logs & Notes
- [[Notes/Daily/2026-07-11|Log Hari Ini - 2026-07-11]]
- [[Notes/Daily/2026-07-10|Log Kemarin - 2026-07-10]]
- [[Notes/Daily/2026-07-09|Log - 2026-07-09]]
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
