# Product Requirements Document

## Product

OCR-FOTO-P3STE — pipeline pengolahan foto timemark dan tanggal dari sumber PDF.

## Problem

Foto hasil ekstraksi perlu diberi tanggal yang konsisten, terbaca, dan ditempatkan berdasarkan guide visual pada foto itu sendiri.

## Goals

- Ekstrak foto dari PDF tanpa kehilangan struktur folder.
- Tentukan tanggal dari sumber target/OCR.
- Deteksi guide warna pada setiap foto.
- Tempatkan tanggal pada anchor guide foto yang sama.
- Sediakan stage readable, log, dan audit yang dapat ditelusuri.

## Non-goals

- Menggunakan posisi foto lain sebagai sumber kebenaran posisi.
- Memaksa posisi pada foto tanpa guide yang dapat dipercaya.
- Mengubah sumber PDF asli.

## Functional requirements

1. Input PDF/foto diproses secara recursive.
2. Output mempertahankan struktur asset dan frame.
3. Detector mendukung guide kiri maupun kanan.
4. Guide ambigu atau tidak ditemukan harus dilaporkan.
5. Stage output menggunakan label yang mudah dibaca.
6. Batch menghasilkan summary success, failed, skipped, dan fallback.

## Acceptance criteria

- Posisi textbox mengikuti guide aktual pada foto yang sama.
- Tidak ada override tersembunyi pada full-detector run.
- Setiap fallback memiliki alasan dan path.
- Output dapat diaudit melalui log dan report.
- Perubahan kode tervalidasi dengan syntax check dan targeted test.
