# Setup & Menjalankan Aplikasi

## 1. Menjalankan Langsung di PC Lapangan (Zero-Setup / Non-Python)

Untuk komputer operasional stasiun atau pengguna akhir yang **tidak memiliki Python maupun Node.js**:
1. Pastikan seluruh folder proyek tersalin lengkap (termasuk `OCR_Foto_Timemark.exe`, `bin/`, `web/`, `config/`, dan data `01_` s.d. `05_`).
2. Klik dua kali pada berkas:
   ```text
   OCR_Foto_Timemark.exe
   ```
3. Jendela desktop aplikasi WebView2 akan langsung terbuka dalam hitungan detik. Seluruh modul siap digunakan tanpa perlu instalasi atau setting konfigurasi apapun.

---

## 2. Lingkungan Pengembangan Lokal (Developer Setup)

Bila Anda ingin mengembangkan kode sumber, mengedit antarmuka Next.js, atau mengompilasi ulang:

### Persyaratan:
- Windows PowerShell
- Python 3.10+ (dengan package `PyMuPDF`, `pdfplumber`, `pillow`, `numpy`, `openpyxl`, `pywebview`, `pythonnet`, `pyinstaller`)
- Node.js 18+ & npm
- Tesseract OCR (bila menguji OCR fallback)

### Validasi Lingkungan:
```powershell
python --version
node --version
npm --version
```

### Menjalankan Mode Pengembangan:
- **Aplikasi Web Next.js (Port 3000):**
  ```powershell
  cd web
  npm install
  npm run dev
  ```
- **Kompilasi Ulang Produksi Next.js:**
  ```powershell
  npm run web:build
  ```
- **Kompilasi Ulang Python Engine Standalone:**
  ```powershell
  python -m PyInstaller --noconfirm --onedir --name python_engine --distpath bin scripts/python_engine.py
  ```
- **Kompilasi Ulang Launcher Desktop (.exe):**
  ```powershell
  python -m PyInstaller --noconfirm --onefile --windowed --name OCR_Foto_Timemark --distpath . --collect-all webview --hidden-import=clr --hidden-import=webview.platforms.winforms launcher.py
  ```

## Data safety

Simpan PDF sumber di `01_pdf_source/` dan PDF target di `02_pdf_target/`. Jangan menghapus berkas sumber. Output disimpan di `05_pdf_merged/` atau folder output yang dipilih pengguna, dan log audit tersimpan di `logs/`.

