# Local Setup

## Requirements

- Windows PowerShell
- Python 3.x
- Node.js/npm untuk tooling server bila diperlukan
- Dependency Python yang dipakai script di `scripts/`
- Varian YOLO memerlukan package `ultralytics` dan model `scripts/best.pt`

## Repository

Clone/open repository lalu pastikan folder input, script, dan konfigurasi tersedia. Lihat [[PROJECT_INDEX]] untuk peta folder.

## First validation

```powershell
python --version
node --version
npm --version
```

Lakukan syntax check script sebelum batch. Detail command dan troubleshooting ada di [[OPERATIONS]].

## Data safety

Simpan PDF sumber di `01_pdf_source/`. Jangan menghapus input. Output eksperimen diarahkan ke folder output yang disepakati dan evidence disimpan di `logs/`.
