# Project OCR Foto

Project ini dibuat untuk eksperimen batch edit teks tanggal pada watermark foto Timemark. Fokus utama: mengganti baris tanggal di bagian kiri bawah foto tanpa mengubah foto asli.

## Ringkasan Alur

1. Foto asli disimpan di folder project.
2. Script membaca semua file gambar dari folder input.
3. Area tanggal lama di watermark bawah kiri ditutup atau dibersihkan.
4. Tanggal baru ditulis ulang di posisi yang sama.
5. Hasil disimpan ke folder output terpisah.

## Struktur File

```text
project_ocr_foto/
  ocr.py
  ocr-ai.py
  2026-07-03 11.22.42_Cilebut.jpg
  2026-07-03 11.22.51_Cilebut.jpg
  Hasil_Edit/
  Hasil_Generative/
```

## File Utama

`ocr.py`

- Versi sederhana.
- Memakai OpenCV.
- Cara kerja: menutup area tanggal lama dengan kotak warna gelap, lalu menulis tanggal baru.
- Output: `Hasil_Edit/`.
- Cocok untuk proses cepat dan batch banyak foto.

`ocr-ai.py`

- Versi AI generative fill.
- Memakai OpenCV, Pillow, Torch, dan Diffusers.
- Cara kerja: membuat mask pada area tanggal, membersihkan area itu dengan model inpainting, lalu menulis tanggal baru.
- Output: `Hasil_Generative/`.
- Cocok untuk hasil lebih halus, tapi lebih berat dan butuh model AI.

## Dependensi

Versi sederhana:

```bash
pip install opencv-python numpy
```

Versi AI:

```bash
pip install opencv-python numpy pillow torch diffusers
```

## Cara Pakai

1. Taruh foto `.jpg`, `.jpeg`, atau `.png` di folder project.
2. Buka `ocr.py`.
3. Ubah nilai:

```python
TANGGAL_BARU = "Sabtu, Jul 04, 2025"
```

4. Jalankan:

```bash
python ocr.py
```

5. Cek hasil di:

```text
Hasil_Edit/
```

Untuk versi AI:

```bash
python ocr-ai.py
```

Lalu cek:

```text
Hasil_Generative/
```

## Area Yang Diedit

Script saat ini memakai posisi relatif dari ukuran gambar:

```python
x1, y1 = int(w * 0.05), int(h * 0.778)
x2, y2 = int(w * 0.35), int(h * 0.812)
```

Artinya script diasumsikan untuk foto dengan layout watermark mirip contoh: tanggal berada di kiri bawah.

## Kelebihan

- Bisa batch banyak foto.
- File asli tidak ditimpa.
- Posisi edit mengikuti ukuran gambar.
- Versi sederhana cepat.
- Versi AI bisa lebih bersih.

## Batasan

- Jika posisi watermark berbeda jauh, koordinat perlu dikalibrasi lagi.
- `ocr.py` belum benar-benar menghapus teks lama; hanya menutup area tanggal.
- `ocr-ai.py` lebih berat dan hasilnya bisa berbeda-beda tiap foto.
- Format tanggal saat ini masih hardcoded satu nilai untuk semua foto.
- Belum ada mode tanggal berbeda per folder atau per file CSV.

## Rencana Lanjutan

Paling sederhana untuk kebutuhan banyak aset dengan tanggal berbeda:

```text
input/
  2026-07-01/
    foto1.jpg
    foto2.jpg
  2026-07-02/
    foto3.jpg
```

Script bisa membaca nama folder sebagai tanggal, lalu menerapkan tanggal itu ke semua foto di dalam folder tersebut.

Alternatif lebih fleksibel:

```csv
filename,date
foto1.jpg,2026-07-01
foto2.jpg,2026-07-01
foto3.jpg,2026-07-02
```

## Catatan Penting

`ocr-ai.py` berisi token Hugging Face hardcoded. Jangan bagikan file itu ke publik sebelum token dipindahkan ke environment variable.

Untuk dokumen bukti resmi, lebih aman menyimpan foto asli dan memberi catatan koreksi terpisah, bukan hanya mengubah gambar final.
