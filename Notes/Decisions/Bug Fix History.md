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
