# System Architecture

## Data flow

```text
PDF source
  -> photo extraction
  -> 03_photos_export/
  -> guide/date detection
  -> timemark editing
  -> 04_photos_edited/Tim_N/
  -> optional PDF merge from 02_pdf_target/
  -> 05_pdf_merged/Tim_N/
```

## Components

- `scripts/` — executable pipeline logic
- `schedule.json` — asset/date metadata
- `03_photos_export/` — normalized image input
- `04_photos_canny_pipeline/` — edited image output
- `logs/` — operational evidence and audit artifacts
- `server.js` — local UI/server support

## Positioning contract

Untuk setiap foto:

1. Cari kandidat guide pada seluruh lebar foto tersebut.
2. Validasi warna, bentuk, tinggi, dan lokasi kandidat.
3. Pilih guide kiri, kanan, atau tengah berdasarkan bukti foto, bukan median folder.
4. Hitung anchor textbox dari guide terpilih; textbox tetap ditempatkan di sisi kanan guide sesuai keputusan operasi saat ini.
5. Jika beberapa kandidat mirip, pilih skor tertinggi tetapi tulis catatan review agar operator mengetahui selector sedang ragu.
6. Jika tidak ada guide, gunakan OCR tanggal lama bila tersedia; jika tidak, tandai foto sebagai fallback.

## Detector stages

Stage label harus tetap readable. Stage internal mencakup guide warna utama, orange/amber, kuning, detector inversi, OCR fallback, dan no-guide fallback. `stage_0_override` tidak digunakan pada full-detector script sementara.

## Evidence and reproducibility

Setiap batch harus memiliki command, input root, output root, summary stage, dan log. Audit visual yang menampilkan gambar disimpan di `logs/`.
