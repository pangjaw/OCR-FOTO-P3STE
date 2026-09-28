# ADR-015: OCR Fallback pada Audit dan Ekstraksi Personil untuk Berkas Image-Only (Scanned PDF)

- **Status:** Diterima & Diimplementasikan
- **Tanggal:** 2026-09-19
- **Area:** `scripts/audit_and_correct_personnel.py`, `scripts/extract_file_personnel.py`, Express Backend (`server.js`), Next.js App (`web/`)

---

## 1. Konteks & Masalah

Saat menjalankan fitur audit personil pada folder berkas PDF eksternal (misalnya `C:\Users\dikarm\Downloads\RESOR STL 1.21 BOGOR` yang memuat 208 berkas PDF):
1. **29 Berkas Gagal Terdeteksi Personilnya:** Sistem mengelompokkan 29 berkas ke dalam kategori **CRITICAL / Temuan Utama: Tanpa KAUR & Kurang PNC (0/2)** (`0 KAUR, 0 PNC`). Contohnya adalah berkas `PERAWATAN SINYAL J10 CLT 14-06-2025.pdf`.
2. **Akar Penyebab Teknis (Zero Text Layer):**
   - Ke-29 berkas tersebut adalah PDF hasil scan atau flat bitmap (berukuran ~2.481 × 3.508 piksel per halaman) yang tidak memiliki lapisan teks digital (*digital text layer*) sama sekali (`len(doc[0].get_text('text')) == 0`).
   - Parser personil sebelumnya mengandalkan pembacaan teks digital langsung dari PyMuPDF. Karena teks digitalnya kosong, parser menyimpulkan daftar personil tidak ada.
3. **Kendala Pemindaian OCR Horizontal:**
   - Pada tabel formulir perawatan berkala, teks dibaca horizontal lintas kolom oleh OCR. Frasa `"DILAKSANAKAN OLEH"` dapat terpecah atau tertimpa deretan sel lain (misal terbaca `Ditaksanakan` atau `aimee`), sehingga jika parser melakukan keluar dini (*early return* saat `start is None`), nama-nama personil yang ada di dokumen tidak tercakup meskipun teks fisiknya terbaca jelas oleh OCR.
4. **Karakter Rancu OCR pada Nama:**
   - Sensor OCR kerap menukar huruf vokal kapital `I` dengan tanda seru `!` (contoh: `DEDI SURYADI` terbaca `DED! SURYADI`) atau garis pemisah pipa `|` / angka `1`, sehingga pencocokan string persis (*exact regex match*) gagal mencocokkan nama ke daftar pegawai.

---

## 2. Keputusan Arsitektur

### A. Fallback OCR Otomatis pada `extract_personnel_from_pdf`
Fungsi `extract_page_ocr_text(page)` ditambahkan ke dalam `scripts/audit_and_correct_personnel.py`:
- Jika teks digital Halaman 1 bernilai kurang dari 10 karakter (`len(text.strip()) < 10`), sistem secara otomatis merender halaman 1 (`dpi=150`) dan memprosesnya menggunakan Tesseract OCR (`C:\Program Files\Tesseract-OCR\tesseract.exe`).
- Jika berkas memiliki teks digital normal, proses OCR dilewati secara instan tanpa menurunkan performa pemrosesan berkas-berkas digital.

### B. Normalisasi Karakter Rancu OCR (*Heuristic Disambiguation*)
Sebelum teks OCR dicocokkan dengan basis data pegawai, dilakukan normalisasi karakter cerdas:
```python
# Ubah tanda seru yang berada di antara atau setelah huruf menjadi 'I' (misal DED! -> DEDI)
t = re.sub(r'(?<=[A-Za-z])!', 'I', raw_ocr)
t = re.sub(r'!(?=[A-Za-z])', 'I', t)
# Ubah pipe '|' atau angka '1' di tengah kata menjadi 'I'
t = re.sub(r'(?<=[A-Za-z])[|1](?=[A-Za-z])', 'I', t)
```

### C. Refaktor Alur Pencocokan Roster (Penghapusan Early Exit)
- Menghapus aturan keluar dini saat `start is None`.
- Jika penanda awal tabel pelaksana tidak ditemukan secara terisolasi (khas pada tabel horizontal hasil OCR), parser tetap melanjutkan ke tahap pemindaian nama terhadap roster aktif (`kaur_map` dan `pnc_map`).
- Hanya nama personil yang sah dan terdaftar pada konfigurasi pegawai yang akan diambil, sehingga supervisor/pejabat yang menandatangani kolom "Disetujui" (`S. SLAMET RIYADI`) dan "Diketahui" (`SUYADI`) tidak keliru dimasukkan sebagai teknisi pelaksana.

### D. Penanganan Pengeditan Berkas Image-Only (*White-Patching Contract*)
- **Status Dokumen Scan Saat Ini:** 29 dokumen scan yang diperiksa terbukti sah di lapangan (16 berkas berstatus `1 KAUR, 2 PNC`, 13 berkas berstatus `Kelebihan Personil`), sehingga tidak memerlukan koreksi nama.
- **Kontrak Pengeditan di Masa Depan:** Jika suatu saat dokumen image-only perlu diedit teksnya, mekanisme yang disepakati adalah **White-Patch & Overlay Text**:
  1. Mendapatkan bounding box teks via OCR (`pytesseract.image_to_data`).
  2. Menggambar kotak persegi putih penutup (`page.draw_rect(rect, fill=(1, 1, 1))`) di atas gambar latar belakang.
  3. Mencetak teks baru di atas kotak putih tersebut menggunakan `page.insert_text()`.

---

## 3. Hasil & Validasi

1. **Audit Ulang 208 Berkas `RESOR STL 1.21 BOGOR`:**
   - Status **CRITICAL (`0 KAUR, 0 PNC`)**: Turun dari **29 berkas menjadi 0 berkas** (100% tuntas).
   - Seluruh 208 berkas terbagi menjadi **86 OK** dan **122 Warning (Kelebihan Personil - Aman)**.
   - Sampel berkas `PERAWATAN SINYAL J10 CLT 14-06-2025.pdf` berhasil mendeteksi secara akurat:
     - KAUR: `DEDI SURYADI`
     - PNC: `RAIHAN HERPIAN`, `MUHAMAD SOFYAN`
     - Status: `✅ 1 KAUR, 2 PNC (Sesuai Aturan)`.
2. **Sinkronisasi Ekstraksi Personil Cache (`extract_file_personnel.py`):**
   - Pemrosesan 208 berkas target menghasilkan 208 entri valid pada cache JSON tanpa ada satu pun berkas dengan personil kosong (`Files with empty personnel: 0`).
3. **Integritas Modul:**
   - Kompilasi `python -m py_compile scripts/audit_and_correct_personnel.py` lulus 100%.
