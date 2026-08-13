# Active Pipeline Rules

Aturan yang harus dipakai saat menjalankan atau menjelaskan pipeline.

## Jadwal dan Tim

- Satu file PDF harus tetap berada dalam satu Tim.
- Jika aset terakhir dalam PDF melewati 18:00, jam aset berikutnya dalam PDF tetap dilanjutkan.
- Tim berikutnya hanya dipakai untuk PDF berikutnya.
- Tanggal mengikuti tanggal pada PDF dan `date.txt`; jangan menggeser tanggal hanya karena overflow.
- Jika satu PDF ditemukan pada dua Tim, laporkan konflik dan jangan memilih Tim 1 diam-diam.

## Routing BTP

- `BOO`, `CLT`, dan `BJD` umumnya masuk `BTP JAK`.
- `BOP`, `BTT`, `CGB`, `COS`, `MSG`, `CCR`, dan `BNR` umumnya masuk `BTP BD`.
- Semua `JPL ... BOO-BOP` adalah pengecualian khusus dan masuk `BTP BD`.
- Aturan khusus harus diperiksa sebelum aturan umum yang membaca kode `BOO`.

## Posisi manual

- Posisi tanggal yang sudah dikoreksi pengguna tersimpan di `meta.json`.
- Proses ulang Step 4 harus mempertahankan posisi tersebut.
- Isi tanggal dan jam boleh diperbarui dari `schedule.json`, tetapi posisi manual tidak boleh hilang.

## Urutan kerja aman

1. Baca histori bug dan aturan ini.
2. Periksa sumber, output, dan manifest.
3. Buat backup atau manifest sebelum pemindahan/batch besar.
4. Jalankan Step 4 dan periksa hasil foto.
5. Jalankan Step 5 hanya setelah Step 4 benar.
6. Catat hasil, jumlah gagal, `unedited`, konflik, dan lokasi output.

## Gaya komunikasi agent

- Gunakan bahasa Indonesia sederhana.
- Jelaskan seperti kepada pengguna aplikasi yang tidak memahami program.
- Sampaikan kesimpulan terlebih dahulu.
- Jelaskan istilah teknis dengan contoh.
- Bedakan dengan jelas: sudah diperbaiki, belum dilakukan, dan langkah berikutnya.
