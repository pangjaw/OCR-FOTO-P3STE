---
created: 2026-07-10
tags:
  - reference/data
  - acuan
  - perawatan
  - sinyal
  - telekomunikasi
aliases:
  - Data Acuan Tenaga
  - Kebutuhan Minimal Tenaga Perawatan
---

# Data Acuan Tenaga Perawatan Fasilitas Operasi Kereta Api

> Kembali ke [[Dashboard]] | Lihat juga: [[AGENTS.md]] (`scheduler.py` → `get_waktu()`)

> [!abstract] **Sumber**
> - **Sinyal:** `1.a. Pedoman Perawatan Persinyalan.pdf` (STE-PR-01, Rev.5, Mei 2019)
> - **Telekomunikasi:** `2.a. Pedoman Perawatan Telekomunikasi.pdf` (STE-PR-02, Rev.3, Juli 2023)
> - **Dasar:** SDM Pelaksana — Tenaga Perawatan Fasilitas Pengoperasian Kereta Api

---

## Ringkasan

| Kategori | Jumlah Aset | Pelaksana | Pelaksana Lanjutan | Total Tenaga |
|:---------|:-----------:|:---------:|:------------------:|:------------:|
| **Sinyal** | 20 | 38 | 16 | 54 |
| **Telekomunikasi** | 18 | 20 | 9 | 29 |
| **Gabungan** | **38** | **58** | **25** | **83** |

> [!warning] Catatan
> - Data ini merupakan **kebutuhan MINIMAL** tenaga **per jenis aset per kegiatan perawatan**.
> - 1 petugas bisa menangani beberapa jenis aset tergantung penugasan lapangan.

---

## Data Sinyal (20 Aset)

| # | Aset | Pelaksana | Pelaksana Lanjutan | Waktu (Menit) | Waktu (Jam) |
|:-:|:-----|:---------:|:------------------:|:--------------:|:-----------:|
| 1 | Peralatan Dalam Sinyal Mekanik | 2 | 1 | 180 | 3,0 |
| 2 | Peraga Sinyal Mekanik | 1 | 1 | 30 | 0,5 |
| 3 | Penggerak Wesel Mekanik | 2 | 1 | 45 | 0,8 |
| 4 | Saluran Kawat | 2 | 0 | 60 | 1,0 |
| 5 | Peralatan Dalam Sinyal Elektrik | 2 | 1 | 420 | 7,0 |
| 6 | Peraga Sinyal Elektrik | 2 | 1 | 30 | 0,5 |
| 7 | Peralatan CTC/CTS | 2 | 1 | 30 | 0,5 |
| 8 | Axle Counter Siemens | 2 | 1 | 45 | 0,8 |
| 9 | Axle Counter Altpro | 2 | 1 | 45 | 0,8 |
| 10 | Axle Counter Frausher | 2 | 1 | 45 | 0,8 |
| 11 | Axle Counter Thales | 2 | 1 | 60 | 1,0 |
| 12 | Axle Counter ESSO-M | 2 | 1 | 45 | 0,8 |
| 13 | Track Circuit | 2 | 0 | 60 | 1,0 |
| 14 | Location Case | 2 | 1 | 30 | 0,5 |
| 15 | Point Lock / Perintang / Pelalau | 2 | 1 | 30 | 0,5 |
| 16 | Pintu Perlintasan | 2 | 1 | 45 | 0,8 |
| 17 | Catu Daya | 2 | 0 | 45 | 0,8 |
| 18 | Penggerak Wesel Elektrik | 2 | 1 | 45 | 0,8 |
| 19 | Kontak Rel dan WSR (Wheel Sensor) | 1 | 1 | 30 | 0,5 |
| 20 | Wesel Terlayan Setempat Elektrik | 2 | 1 | 45 | 0,8 |

---

## Data Telekomunikasi (18 Aset)

| # | Aset | Pelaksana | Pelaksana Lanjutan | Waktu (Menit) | Waktu (Jam) |
|:-:|:-----|:---------:|:------------------:|:--------------:|:-----------:|
| 21 | Radio Lokomotif | 1 | 1 | 30 | 0,5 |
| 22 | Radio Waystation | 1 | 0 | 40 | 0,7 |
| 23 | Sistem Waystation | 1 | 0 | 80 | 1,3 |
| 24 | Radio Base Station | 1 | 1 | 65 | 1,1 |
| 25 | Pusat Kendali (PK) | 1 | 1 | 60 | 1,0 |
| 26 | Radio Waystation Digital | 1 | 0 | 60 | 1,0 |
| 27 | Sistem Radio Base Station Digital | 1 | 1 | 60 | 1,0 |
| 28 | Pusat Kendali (PK) Digital | 1 | 1 | 60 | 1,0 |
| 29 | Radio Lokomotif TAIT | 1 | 1 | 60 | 1,0 |
| 30 | Radio Waystation TAIT | 1 | 0 | 60 | 1,0 |
| 31 | Sistem Waystation TAIT | 1 | 0 | 60 | 1,0 |
| 32 | Radio Base Station TAIT | 1 | 1 | 90 | 1,5 |
| 33 | Pusat Kendali (PK) TAIT | 1 | 1 | 60 | 1,0 |
| 34 | Telekomunikasi Di Stasiun | 1 | 0 | 60 | 1,0 |
| 35 | Telekomunikasi Di Luar Stasiun | 1 | 0 | 120 | 2,0 |
| 36 | Telekomunikasi Di Pintu Perlintasan | 1 | 0 | 45 | 0,8 |
| 37 | Serat Optik | 2 | 0 | 6 | 0,1 |
| 38 | Saluran Blok | 2 | 1 | 90 | 1,5 |

---

## Data Mentah

File JSON & Excel ada di vault root:

```json:data_acuan_tenaga_gabungan.json
```
```xlsx:data_acuan_tenaga_gabungan.xlsx
```

---

## Tags

#reference/data #acuan/perawatan #sinyal #telekomunikasi #p3ste #PTKAI
