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
- `[[edit_timemark.py]]` - Script utama untuk mengedit tanggal watermark Timemark pada foto.
- `[[export_pdf_foto.py]]` - Script untuk mengekstrak foto asli dari dokumen PDF berdasarkan posisi layout halaman.

### Status Kerja
```mermaid
kanban
%% Note: Obsidian Kanban plugin supports this or standard lists, this is rendered as code/mermaid %%
graph TD
    todo[To Do] --> in_progress[In Progress] --> done[Done]
    
    click todo href "obsidian://open?vault=OCR-FOTO-P3STE&file=Dashboard"
```

- **In Progress (Sedang Berjalan):**
	- [ ] Uji lebih banyak variasi latar belakang watermark.
	- [ ] Uji script `export_pdf_foto.py` dengan PDF berlayout baru.
- **Done (Selesai):**
	- [x] Deteksi anchor garis merah/oranye Timemark.
	- [x] Ekstraksi original image dari PDF memakai `pypdf`.
	- [x] Recursive subfolder scan untuk input foto.

---

## 📅 Daily Logs & Notes
- [[Notes/Daily/2026-07-08|Log Hari Ini - 2026-07-08]]
- [[Notes/Daily/2026-07-07|Log Kemarin - 2026-07-07]]
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
