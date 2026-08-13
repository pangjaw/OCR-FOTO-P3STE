# Project Rules & Agent Instructions

Repository ini adalah project OCR-FOTO-P3STE sekaligus Obsidian vault dokumentasi.

## Documentation entry point

- [[PROJECT_INDEX]] — indeks utama project dan peta file.
- [[README]] — ringkasan untuk developer.
- [[PRD]] — requirements dan acceptance criteria.
- [[ARCHITECTURE]] — data flow, detector, dan positioning contract.
- [[OPERATIONS]] — command, log, batch, dan troubleshooting.
- [[CONTRIBUTING]] — aturan perubahan dan validasi.
- [[setup]] — setup environment.
- [[Notes/Decisions Index]] — keputusan teknis.
- [[Notes/Experiments Index]] — eksperimen.
- [[Notes/Daily Index]] — catatan kronologis.
- [[Notes/Templates Index]] — template.

## Agent workflow

1. Baca file ini sebelum mengedit atau membuat rencana.
2. Baca [[PROJECT_INDEX]] untuk menemukan file yang terkait dengan tugas.
3. Baca [[PRD]] dan [[ARCHITECTURE]] jika tugas menyentuh behavior pipeline.
4. Baca [[OPERATIONS]] sebelum menjalankan batch atau validasi operasional.
5. Setelah bekerja, perbarui dokumentasi yang relevan jika status/behavior berubah.
6. Jangan membuat atau merujuk path dokumentasi yang tidak ada.

## Project map

- `scripts/` — source pipeline Python/JavaScript.
- `config/` — konfigurasi aplikasi.
- `01_pdf_source/` sampai `05_pdf_merged/` — data flow input/output.
- `logs/` — evidence, audit, report, dan preview.
- `Notes/` — keputusan, eksperimen, daily log, dan template.

## Communication preference

- Gunakan bahasa Indonesia sederhana, seperti menjelaskan kepada pengguna aplikasi yang tidak memahami program.
- Sampaikan kesimpulan utama terlebih dahulu.
- Jelaskan istilah teknis dengan contoh sederhana.
- Bedakan dengan jelas: sudah diperbaiki, belum dilakukan, dan langkah berikutnya.
- Sebelum menangani bug lama, baca [[Notes/Decisions/Bug Fix History]] dan [[Notes/Decisions/Active Pipeline Rules]].

## Safety rules

- Jika user meminta debug OCR/stage, tampilkan data internal dan alasan stage; jangan langsung memperbaiki kode sebelum ada persetujuan tertulis.
- Posisi tanggal harus ditentukan dari guide pada foto yang sedang diproses; posisi foto lain bukan ground truth.
- Jika user meminta menampilkan gambar, salin hasil ke `logs/` terlebih dahulu lalu tampilkan path `logs/`.
- Pertahankan comments/docstrings yang tidak terkait dengan perubahan.
