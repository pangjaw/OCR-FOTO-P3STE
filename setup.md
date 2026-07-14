# Setup & Cara Jalankan

## Kebutuhan
- Python 3.10+
- Tesseract OCR di `C:\Program Files\Tesseract-OCR\tesseract.exe`

## Instalasi
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Struktur Folder
```
root/
├── 01_pdf_source/          ← PDF 2026 mentah (input export_pdf_foto.py)
├── 02_pdf_target/          ← PDF 2025 target
├── 03_photos_export/       ← Hasil ekstraksi foto (folder kerja edit)
│   └── {station}/{asset_type}/{detail_aset}/{0,50,100}.jpg
├── 04_photos_edited/       ← Hasil edit watermark
│   └── Tim_{n}/{station}/{asset_type}/{detail_aset}/{0,50,100}.jpg
├── 05_pdf_merged/          ← PDF final hasil gabung
├── logs/                   ← Log CSV export & merge
└── templates/              ← HTML UI dashboard
```

## Cara Jalankan

### CLI Manual
```powershell
# Step 1: Export foto dari PDF 2026
python export_pdf_foto.py

# Step 2: Ekstrak tanggal dari PDF 2025
python extract_pdf_dates.py

# Step 3: Generate jadwal Tim
python scheduler.py

# Step 4: Edit watermark (pakai schedule.json)
python edit_timemark_ide1.py --schedule schedule.json

# Step 5: Gabung foto ke PDF 2025
python merge_pdf_foto.py --schedule schedule.json
```

### Web UI (Rekomendasi)
```powershell
python app.py
# Buka http://localhost:5000
```

### Opsi Spesifik
```powershell
# Folder aset tunggal
python edit_timemark_ide1.py --input "03_photos_export/AXC/ZP 22A CLT"

# Paksa posisi Y manual
python edit_timemark_ide1.py --input "folder" --date "Sabtu, Apr 29 2026 08:00" --y-override 195

# Hapus output sebelum mulai
python edit_timemark_ide1.py --clear-output

# Scheduler custom jam & mapping
python scheduler.py --jam-mulai 7 --jam-selesai 18 --tim-max 2
```

## Cek Kualitas
1. Bekas tanggal lama tidak terlalu terlihat
2. Tanggal baru sejajar dengan posisi Timemark asli
3. Ukuran font natural, warna & shadow sesuai
4. Setiap folder aset berisi 3 foto (0%, 50%, 100%)
