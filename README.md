# OCR-FOTO-P3STE

Pipeline lokal untuk mengekstrak foto dari PDF, membaca tanggal referensi, mendeteksi guide timemark, menempatkan tanggal, dan menghasilkan output foto/PDF.

## Start here

Baca [[PROJECT_INDEX]] untuk peta lengkap. Dokumen utama:

- [[PRD]] — kebutuhan produk
- [[ARCHITECTURE]] — alur sistem
- [[OPERATIONS]] — penggunaan dan troubleshooting
- [[CONTRIBUTING]] — aturan kontribusi
- [[setup]] — setup environment

## Prinsip penting

Posisi tanggal berasal dari guide yang terlihat pada foto yang sedang diproses. Posisi dari foto lain atau override manual hanya boleh digunakan bila secara eksplisit disetujui untuk eksperimen tertentu.

## Repository areas

Input/output utama berada pada `01_pdf_source/` sampai `05_pdf_merged/`. Script berada di `scripts/`, konfigurasi di `config/`, dan hasil audit/diagnostik di `logs/`.
