# ADR-013: Penanganan Otomatis Aset Target Multi-Tanggal (Tanggal Ganda)

- **Status:** Diterima & Diimplementasikan
- **Tanggal:** 2026-09-18
- **Area:** Step 1 (Export), Step 2 (Dates), Step 3 (Scheduler), Step 4 (Timemark), Step 5 (Merge PDF)

---

## 1. Konteks & Masalah

Pada dokumen target tahun 2025 (`02_pdf_target`), terdapat kondisi di mana aset yang sama dilakukan perawatan pada tanggal yang berbeda dalam satu bulan yang sama. Contohnya:
- `PERAWATAN SINYAL B104 CLT-BOO 10-02-2025.pdf` (Tanggal perawatan: 10 Februari 2025)
- `PERAWATAN SINYAL B104 CLT-BOO 11-02-2025.pdf` (Tanggal perawatan: 11 Februari 2025)

Kondisi ini juga terjadi pada 25 aset lainnya di bulan Februari 2025, termasuk Sinyal (B209), Axle Counter (ZP 104, ZP 209), serta seluruh Wesel perawatan dua-mingguan.

Sebaliknya, pada dokumen sumber foto tahun 2026 (`01_pdf_source`), aset-aset tersebut hanya diambil fotonya satu kali kunjungan (1 set foto 0%, 50%, 100%), kecuali wesel yang memang memiliki 2 dokumen sumber berbeda.

**Dampak jika tidak ditangani:**
1. Di Step 2, pemrosesan berkas kedua akan menimpa berkas `date.txt` pada folder aset tunggal tersebut, sehingga salah satu tanggal hilang.
2. Di Step 3, aset hanya memiliki satu slot jadwal dan satu tanggal timemark.
3. Di Step 5, berkas PDF target pada tanggal yang berbeda akan mengambil foto yang salah atau salah satu PDF gagal memperoleh foto yang sesuai.

---

## 2. Keputusan Arsitektur

Diputuskan arsitektur terintegrasi lintas langkah (Step 1 s/d Step 5) dengan pola **Rename + Copy + Manifest Tracking**:

```
01_pdf_source/
       │
       ▼ [Step 1: export_pdf_foto.py]
03_photos_export/.../{identifier}/ (Ekstraksi murni 1 set foto)
       │
       ▼ [Step 2: extract_pdf_dates.py]
       ├── 1. Pre-scan 02_pdf_target: deteksi identifier yang muncul di >1 tanggal.
       ├── 2. Rename folder basis: {identifier} -> {identifier}_{DD-MM-1}
       ├── 3. Duplikasi folder: copy foto ke {identifier}_{DD-MM-2}
       ├── 4. Catat riwayat ke logs/asset_folder_mapping.json (Idempotent saat re-run)
       └── 5. Tulis date.txt spesifik di tiap folder bersuffix
       │
       ▼ [Step 3: scheduler.py]
schedule.json: Mendeteksi ketersediaan folder bersuffix di 03_photos_export
               dan menjadwalkan kedua entri secara independen.
       │
       ▼ [Step 4: edit_timemark_ide1.py / edit_photo_coordinate_only.py]
04_photos_edited/.../{identifier}_{DD-MM}/: Watermark tanggal dicap sesuai jadwal.
(Pada mode koordinat, suffix _DD-MM dibersihkan saat lookup ke mapping koordinat dasar).
       │
       ▼ [Step 5: merge_pdf_foto.py]
Mencocokkan tanggal pada nama berkas target (_DD-MM).
Memprioritaskan pencarian {cand}_{DD-MM} sebelum fallback ke {cand}.
```

---

## 3. Rincian Implementasi

### A. Step 2 (`scripts/extract_pdf_dates.py`)
- Fungsi `prepare_multi_date_folders()` memindai seluruh berkas target di awal eksekusi.
- Mengelompokkan tanggal per identifier aset berdasarkan ekstraksi funcloc / filename.
- Membaca `logs/asset_folder_mapping.json` terlebih dahulu agar saat script dijalankan ulang (*re-run*), sistem mengenali folder yang sudah pernah di-rename dan tidak menghasilkan nama bertingkat (seperti `_10-02_10-02`).
- Menuliskan `date.txt` yang tepat untuk masing-masing folder bersuffix.

### B. Step 3 (`scripts/scheduler.py`)
- Fungsi identifikasi aset pass 1 menerima argumen `photos_dir`.
- Melakukan pengecekan: jika folder bersuffix `f"{cand}_{DD-MM}"` ada di direktori foto, maka kandidat bersuffix tersebut dimasukkan sebagai identitas aset di `schedule.json`.

### C. Step 4 (`scripts/edit_timemark_ide1.py` & `scripts/edit_photo_coordinate_only.py`)
- Skrip timemark membaca folder bersuffix sebagai entitas aset mandiri dan mencocokkannya ke `schedule.json`.
- Skrip koordinat men-strip suffix tanggal (`_DD-MM`) pada fungsi `resolve_coordinate()` agar koordinat GPS tetap cocok dengan database acuan.

### D. Step 5 (`scripts/merge_pdf_foto.py`)
- Ekstraksi tanggal dari nama file PDF target menghasilkan `expected_suffix = f"_{DD}-{MM}"`.
- Urutan prioritas pencarian direktori foto:
  1. `cat_dir / f"{cand}{expected_suffix}"`
  2. `cat_dir / cand`
- Berlaku untuk seluruh kategori aset (tidak terbatas pada Wesel).

---

## 4. Konsekuensi & Validasi

- **Idempotensi:** Sistem aman dijalankan berulang kali (*re-run*) tanpa resiko folder hilang atau nama rusak berkat manifest `logs/asset_folder_mapping.json`.
- **Hasil Pengujian Nyata (Februari 2025):**
  - Berkas `PERAWATAN SINYAL B104 CLT-BOO 10-02-2025.pdf`: Sukses digabung ke Tim 2 dengan mengambil foto dari `B104 CLT-BOO_10-02` (Watermark: 10 Feb 2025).
  - Berkas `PERAWATAN SINYAL B104 CLT-BOO 11-02-2025.pdf`: Sukses digabung ke Tim 1 dengan mengambil foto dari `B104 CLT-BOO_11-02` (Watermark: 11 Feb 2025).
  - 25 aset multi-tanggal lainnya (Sinyal B209, Axle Counter ZP 104, ZP 209, dan Wesel 2-mingguan) terpecah rapi tanpa intervensi manual.
