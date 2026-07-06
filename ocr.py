import os
import cv2
import numpy as np

# ====== KONFIGURASI ======
# Kosongkan atau samakan jika kamu membuka terminal/CMD langsung di folder foto
FOLDER_INPUT = "./" 
FOLDER_OUTPUT = "./Hasil_Edit/"

# Teks tanggal baru yang ingin kamu masukkan
TANGGAL_BARU = "Sabtu, Jul 04, 2025" 

if not os.path.exists(FOLDER_OUTPUT):
    os.makedirs(FOLDER_OUTPUT)

def proses_ganti_tanggal(image_path, output_path):
    img = cv2.imread(image_path)
    if img is None:
        return False
        
    h, w, _ = img.shape
    
    # =================================================================
    # PERBAIKAN 1: Kalibrasi Kotak Penutup (Lebih pas & presisi)
    # =================================================================
    # Kita buat kotaknya lebih tipis dan pas di atas teks tanggal
    x1, y1 = int(w * 0.05), int(h * 0.778)
    x2, y2 = int(w * 0.35), int(h * 0.812)
    
    # Menggunakan warna hitam semi-transparan khas Timemark (bukan hitam pekat)
    warna_penutup = (35, 35, 35) 
    cv2.rectangle(img, (x1, y1), (x2, y2), warna_penutup, -1)
    
    # =================================================================
    # PERBAIKAN 2: Kalibrasi Teks Baru (Lebih besar & tebal)
    # =================================================================
    # Menggeser posisi teks agar pas di tengah kotak baru
    posisi_teks = (x1 + 15, y2 - 25)
    
    font = cv2.FONT_HERSHEY_DUPLEX
    
    # Ditambah ukurannya dari 1.1 menjadi 2.2 agar besar dan jelas
    font_scale = 2.2  
    warna_teks = (255, 255, 255) # Putih bersih
    ketebalan = 4 # Dipertebal dari 2 menjadi 4
    
    cv2.putText(img, TANGGAL_BARU, posisi_teks, font, font_scale, warna_teks, ketebalan, cv2.LINE_AA)
    
    cv2.imwrite(output_path, img)
    return True

# ====== PROSES BATCH AUTOMATION ======
print("Memulai proses penggantian tanggal massal...")
jumlah_sukses = 0

for filename in os.listdir(FOLDER_INPUT):
    # Filter hanya file gambar
    if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        jalur_foto = os.path.join(FOLDER_INPUT, filename)
        jalur_hasil = os.path.join(FOLDER_OUTPUT, filename)
        
        # Proses eksekusi
        if proses_ganti_tanggal(jalur_foto, jalur_hasil):
            print(f"[OK] Berhasil mengubah tanggal: {filename}")
            jumlah_sukses += 1

print(f"\n--- Selesai! {jumlah_sukses} foto berhasil diperbarui di folder '{FOLDER_OUTPUT}' ---")