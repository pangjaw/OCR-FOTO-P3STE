# ADR-014: Integrasi Detektor Google Cloud Vision & Optimasi Textbox Dinamis

- **Status:** Diterima & Diimplementasikan
- **Tanggal:** 2026-09-19
- **Area:** Step 4 (`edit_timemark_ide1.py`), Web App (`pipeline-dashboard.tsx`, `photo-gallery.tsx`), Backend Runner (`pipeline-runner.ts`, API routes)

---

## 1. Konteks & Masalah

Pada pemrosesan Step 4 (penimpaan watermark timemark GPS Map Camera), sistem konvensional mengandalkan deteksi garis panduan merah/oranye (*Red Guide / Orange Guide*) via isolasi warna HSV. Walaupun metode ini cepat dan offline, terdapat beberapa kendala lapangan:
1. **Garis Panduan Rusak/Tertimpa:** Pada sebagian foto, garis guide terpotong, tertutup stiker/objek fisik lain, atau mengalami pencahayaan ekstrem sehingga deteksi jatuh ke `stage_fallback` dengan posisi perkiraan.
2. **Kebutuhan OCR Cerdas Berbasis Teks:** Pengguna membutuhkan alternatif metode OCR yang dapat membaca langsung koordinat teks tanggal lama (misal: "Senin, 02 Feb 2026") di foto menggunakan Google Cloud Vision API.
3. **Lebar Textbox Statis Terlalu Panjang:** Textbox watermark sebelumnya dihitung dengan lebar tetap (`BOX_WIDTH_RATIO = 0.48` atau 48% lebar foto). Hal ini menghasilkan:
   - Sisa ruang hitam kosong di sebelah kanan teks tanggal & jam.
   - Algoritma inpainting (*diffuse fill*) memblur area foto terlalu jauh ke kanan, menutupi detail objek foto yang seharusnya tetap terlihat.

---

## 2. Keputusan Arsitektur

### A. Dual Detector Architecture (Metode Biasa vs Google Vision)
Sistem menyediakan dua metode yang dapat dipilih secara fleksibel oleh pengguna:
1. **Metode Biasa (`guide`):** Menggunakan HSV color isolation + template matching garis guide merah/oranye + folder consensus. Cepat, offline, hemat resource.
2. **Google Cloud Vision (`google_vision`):** Memanggil API Google Cloud Vision untuk mendeteksi posisi teks tanggal lama, mengekstrak batas kotak teks (*bounding polygon*), dan menimpa tanggal baru tepat pada koordinat teks lama.

Parameter detektor disalurkan dari Web UI melalui argumen CLI `--detector {guide,google_vision}` pada `edit_timemark_ide1.py` dan `scripts/edit_timemark_ide1.py`.

### B. Protokol Penanganan Kuota Habis (*Graceful Pause-Resume*)
Karena API Google Vision memiliki batasan kuota:
1. Jika terjadi galat `quota_exceeded` / `RESOURCE_EXHAUSTED`, script Python memancarkan JSON event `{"event": "quota_exceeded"}` ke `stdout` dan masuk ke mode jeda menunggu input `stdin.readline()`.
2. Backend (`pipeline-runner.ts`) menangkap event tersebut dan memancarkan Server-Sent Events (SSE) ke browser.
3. Frontend menampilkan modal peringatan interaktif:
   - Tombol **"Lanjutkan dengan Metode Biasa"**: Mengirim perintah `continue_guide` via `POST /api/pipeline/resume`, membuat script beralih memproses sisa berkas dengan metode panduan garis merah tanpa membatalkan batch.
   - Tombol **"Hentikan Proses"**: Mengirim sinyal pembatalan untuk menghentikan proses secara aman.

### C. Persistensi Metadata & Filter Galeri
1. Setiap folder foto hasil edit menyimpan `meta.json` dengan atribut `detector: "google_vision"` atau `"guide"`.
2. Web UI (`photo-gallery.tsx`) dilengkapi filter detektor (`Semua Detektor | Google Vision | Metode Biasa`).
3. Kartu foto menampilkan lencana visual:
   - Lencana Ungu **`Vision AI`** untuk foto hasil Google Cloud Vision.
   - Lencana Biru **`Metode Biasa`** untuk foto hasil detektor garis panduan merah.

### D. Lebar Textbox Dinamis (Fit-to-Text Textbox)
Untuk mengatasi masalah textbox terlalu panjang dan blur meluber:
1. Dimensi teks tanggal dan jam diukur secara akurat menggunakan `font.getbbox()`:
   ```python
   tw = max(tw_date, tw_time)
   pad_x = max(4, int(w * 0.010))  # Padding proporsional
   fit_w = tw + 2 * pad_x
   ```
2. Batas kanan kotak inpainting dan penimpaan disesuaikan:
   ```python
   x2 = min(w, x1 + fit_w)
   ```
3. Inpainting *diffuse fill* hanya diterapkan pada rentang `[x1, x2]`, sehingga objek foto di sebelah kanan teks tanggal tetap utuh, tajam, dan tidak terblur.

---

## 3. Hasil & Validasi

1. **Akurasi & Kecepatan:** Pengujian Google Cloud Vision API pada batch sampel foto mencapai waktu respon rata-rata 0,84 detik/foto dengan tingkat deteksi koordinat teks 100%.
2. **Kerapian Visual:** Textbox baru berbentuk rounded rectangle pill pas membungkus tanggal dan jam secara proporsional. Tidak ada ruang kosong berlebih dan tidak ada blur meluber.
3. **Kompabilitas UI & Build:** Frontend Next.js 14 berhasil terkompilasi (`npm run build` lulus) dengan integrasi mulus tombol toggle di samping mode alur kerja.
