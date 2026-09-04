# Eksperimen HSV + Canny + HoughLinesP

Tanggal: 2026-08-09

## Tujuan
Menguji apakah Canny + HoughLinesP (HLP) dapat membantu detector guide timemark pada pipeline Step 4 tanpa mengubah script utama.

## Konteks
Script utama berada di:

`C:\Users\dikarm\Documents\Server\OCR-FOTO-P3STE\OCR_Foto_Timemark_App`

Detector utama menggunakan beberapa pendekatan:

- Red/yellow mask berbasis RGB + HSV
- Cyan mask melalui invert RGB
- Custom HSV mask
- Folder consensus
- OCR dan fallback

Canny/HLP diuji pada salinan script:

`scripts/edit_timemark_canny_temp.py`

Input eksperimen:

`03_photos_export/`

Output eksperimen:

`04_photos_canny_pipeline/`

Output utama `04_photos_edited/` tidak diubah.

## Konsep

1. HSV/RGB mask memilih piksel yang kemungkinan merupakan warna guide.
2. Canny mencari tepi pada area tersebut.
3. HoughLinesP mencari segmen garis lurus dari tepi Canny.
4. Segmen yang hampir vertikal disaring dengan sudut sekitar 87–93 derajat.
5. Segmen dikelompokkan berdasarkan posisi X.
6. Rentang Y segmen digabung agar satu guide tidak terpotong menjadi banyak segmen.
7. Posisi hasil Canny/HLP dipakai untuk memperbarui box watermark jika cakupan garis mencukupi.

## Hasil awal eksperimen

Pada empat foto SINYAL:

| Foto | Guide utama | HLP setelah perbaikan | Hasil |
|---|---:|---:|---|
| `L47A BOP/100.jpg` | `(8,159)-(9,243)` | `(7,159)-(7,243)` | Rentang Y sama |
| `JL26A BOP/50.jpg` | `(8,171)-(9,269)` | `(7,171)-(7,269)` | Rentang Y sama |
| `J28 BOP/0.jpg` | `(90,159)-(91,242)` | `(89,159)-(89,242)` | Rentang Y sama |
| `MB101 MSG-CCR/100.jpg` | `(8,180)-(9,292)` | `(7,180)-(7,292)` | Rentang Y sama |

Perbedaan X sekitar 1–2 piksel terjadi karena HLP membaca tepi guide, sedangkan detector utama membaca kolom warna guide.

## Uji pipeline sementara

Duplikat script berhasil memproses:

- Total: 1.428 foto
- Gagal: 0
- Fallback/skipped: 9
- Canny decision aktif pada foto dengan ROI guide valid

Path log:

`OCR_Foto_Timemark_App/logs/canny_pipeline_run.log`

## Foto fallback/skipped

Sembilan foto mencapai `stage_fallback_skipped`:

- `BTP JAK/PTLS/RADIO_CGB/50.jpg`
- `BTP BD/PTLS/RADIO_CGB/50.jpg`
- `BTP BD/PDSE/MSG/50.jpg`
- `BTP BD/CATUDAYA/BTT/50.jpg`
- `BTP BD/CATUDAYA/MSG/0.jpg`
- `BTP BD/CATUDAYA/MSG/100.jpg`
- `BTP BD/AXC/ZP 10C MSG/0.jpg`
- `BTP BD/AXC/ZP 10C MSG/50.jpg`
- `BTP BD/AXC/ZP 10C MSG/100.jpg`

Fallback berarti detector tidak menemukan box tanggal yang cukup dipercaya. Foto disalin tanpa edit agar tidak merusak gambar.

## Temuan penting: RADIO_CGB

Pada `RADIO_CGB/50.jpg`, guide samar terlihat di sisi kanan foto. Detector utama membatasi pencarian guide ke sekitar 35% sisi kiri gambar:

```python
max_x_search = int(max(48, w * 0.35))
```

Akibatnya, guide kanan tidak masuk area pencarian. Canny/HLP pada versi eksperimen juga tidak dapat membantu karena masih bergantung pada ROI dari detector utama.

Uji mandiri menunjukkan:

- Mask utama: tidak menemukan guide RADIO_CGB.
- HLP grayscale independen: menemukan banyak garis, sekitar 170 kandidat.
- Kandidat tersebut belum dapat dianggap guide karena kemungkinan besar merupakan noise/garis objek lain.

Kesimpulan: Canny mungkin melihat tepi guide, tetapi HLP tanpa masking yang tepat tidak dapat membedakan guide samar dari garis objek. Masalah RADIO_CGB bukan hanya kontras rendah; asumsi posisi guide selalu di kiri juga salah.

## Status

- Script utama: tidak diubah.
- Canny/HLP: sudah menjadi pengambil keputusan posisi pada duplikat script ketika mask utama menghasilkan ROI.
- Canny/HLP: belum menjadi detector mandiri untuk foto yang mask utamanya gagal.
- RADIO_CGB: memerlukan eksperimen baru dengan pencarian area kanan atau seluruh gambar dan masking yang lebih toleran.

## Kesimpulan

HSV mask dan Canny/HLP harus bekerja berdampingan. HSV memberikan informasi warna; Canny memberikan tepi; HLP menyusun tepi menjadi garis vertikal. Namun Canny/HLP tidak boleh dijalankan hanya setelah detector utama berhasil jika tujuannya menangani kasus fallback. Tahap berikutnya adalah membuat detector gabungan yang mencari mask di sisi kiri dan kanan, lalu menjalankan Canny/HLP secara mandiri sebelum OCR/fallback.

## Artefak eksperimen

- `OCR_Foto_Timemark_App/scripts/edit_timemark_canny_temp.py`
- `OCR_Foto_Timemark_App/logs/canny_pipeline_run.log`
- `OCR_Foto_Timemark_App/logs/fallback_originals_montage.jpg`
- `OCR_Foto_Timemark_App/04_photos_canny_pipeline/`
