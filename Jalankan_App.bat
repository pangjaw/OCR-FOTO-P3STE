@echo off
title OCR Foto Timemark Portable Server
echo ==================================================
echo 🚀 Memulai Server OCR Foto Timemark...
echo ==================================================
cd /d "%~dp0"
start http://localhost:5000
node server.js
pause
