import json
import os
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# Font caching
_FONT_CACHE = {}

def get_font(size: int):
    if size in _FONT_CACHE:
        return _FONT_CACHE[size]
    candidates = [
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arial.ttf",
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "segoeui.ttf",
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "calibri.ttf",
    ]
    for fp in candidates:
        if fp.exists():
            font = ImageFont.truetype(str(fp), size=size)
            _FONT_CACHE[size] = font
            return font
    return ImageFont.load_default()

def diffuse_fill(arr: np.ndarray, mask: np.ndarray, steps: int = 20) -> np.ndarray:
    filled = arr.copy().astype(np.float32)
    mask3 = mask[:, :, None]
    for _ in range(steps):
        up = np.vstack([filled[:1], filled[:-1]])
        down = np.vstack([filled[1:], filled[-1:]])
        left = np.hstack([filled[:, :1], filled[:, :-1]])
        right = np.hstack([filled[:, 1:], filled[:, -1:]])
        avg = (up + down + left + right) * 0.25
        filled = np.where(mask3, avg, filled)
    return np.clip(filled, 0, 255).astype(np.uint8)

def draw_textbox(img: Image.Image, box: tuple[int, int, int, int], text: str) -> Image.Image:
    x1, y1, x2, y2 = box
    w, h = img.size
    box_h = y2 - y1
    font_size = max(9, min(160, int(w * 0.038)))
    font = get_font(font_size)

    dummy = ImageDraw.Draw(Image.new("L", (1, 1)))
    fit_stroke = 1 if font_size >= 28 else 0
    bbox = dummy.textbbox((0, 0), text, font=font, stroke_width=fit_stroke)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad_x = max(2, int(w * 0.008))
    pad_y = max(1, int(h * 0.004))
    tx = x1 + pad_x
    ty = y1 + ((box_h - th) // 2) - bbox[1]

    sx1 = max(0, x1)
    sy1 = max(0, y1)
    sx2 = min(w, x2)
    sy2 = min(h, y2)
    shape_box = (sx1, sy1, sx2, sy2)

    out = img.copy()

    # Dark rounded semi-transparent pill overlay matching production timemark
    radius = max(2, int(box_h * 0.25))
    overlay = Image.new("RGBA", out.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    odraw.rounded_rectangle(shape_box, radius=radius, fill=(0, 0, 0, 150))
    out = Image.alpha_composite(out.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(out)
    so = max(1, int(font_size * 0.02))
    # Shadow text
    draw.text((tx + so, ty + so), text, font=font, fill=(35, 35, 35), stroke_width=fit_stroke, stroke_fill=(35, 35, 35))
    # Crisp white text
    draw.text((tx, ty), text, font=font, fill=(248, 248, 248))

    return out

def main():
    json_path = Path("experiments_google_vision/output/google_vision_results.json")
    if not json_path.exists():
        print("[ERROR] google_vision_results.json tidak ditemukan!")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    out_dir = Path("experiments_google_vision/output")
    logs_dir = Path("logs/google_vision_experiment")
    out_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Contoh tanggal target pengganti (Tahun 2025)
    sample_target_dates = [
        "Senin, Jan 06 2025 08:30",
        "Rabu, Jan 08 2025 09:15",
        "Kamis, Jan 09 2025 10:00",
        "Jumat, Jan 10 2025 11:30",
        "Senin, Jan 13 2025 14:00"
    ]

    print("=" * 65)
    print("DEMO: Menimpa Tanggal Lama dengan Tanggal Baru via Google Vision")
    print("=" * 65)

    for idx, item in enumerate(results):
        photo_path = Path(item["path"])
        name = item["name"]
        cat = item["category"]
        w, h = item["image_size"]

        if not photo_path.exists():
            continue

        date_cands = item.get("date_candidates", [])
        # Cari kata anchor (tahun 2026/2025 atau bulan) di area kiri
        anchor_box = None
        for dc in date_cands:
            txt = dc["text"].lower()
            if any(yr in txt for yr in ["2024", "2025", "2026"]) and dc["bbox"][0] < 150:
                anchor_box = dc["bbox"]
                break
        if not anchor_box:
            for dc in date_cands:
                txt = dc["text"].lower()
                if any(m in txt for m in ["jan", "feb", "mar", "apr", "mei", "jun", "jul", "agu", "sep", "okt", "nov", "des"]) and dc["bbox"][0] < 150:
                    anchor_box = dc["bbox"]
                    break

        if not anchor_box:
            print(f"[{cat}] {name}: Tidak ada koordinat tanggal yang cocok.")
            continue

        anchor_cy = (anchor_box[1] + anchor_box[3]) // 2

        # HANYA ambil kata tanggal yang berada di satu baris yang sama dengan anchor (selisih Y <= 8 px)
        # Ini mencegah kata 'Sel.' pada 'Bogor Sel.' (alamat di bawah) ikut terhapus!
        same_line_boxes = [
            dc["bbox"] for dc in date_cands
            if dc["bbox"][0] < 150 and dc["text"] != "Timemark" and abs(((dc["bbox"][1] + dc["bbox"][3]) // 2) - anchor_cy) <= 8
        ]

        min_x = min(b[0] for b in same_line_boxes)
        min_y = min(b[1] for b in same_line_boxes)
        max_x = max(b[2] for b in same_line_boxes)
        max_y = max(b[3] for b in same_line_boxes)

        new_date_text = sample_target_dates[idx % len(sample_target_dates)]

        # Hitung ukuran text dan padding agar box pas dengan tanggal & jam
        font_size = max(9, min(160, int(w * 0.038)))
        font = get_font(font_size)
        dummy = ImageDraw.Draw(Image.new("L", (1, 1)))
        fit_stroke = 1 if font_size >= 28 else 0
        bbox = dummy.textbbox((0, 0), new_date_text, font=font, stroke_width=fit_stroke)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        pad_x = max(4, int(w * 0.010))
        fit_w = tw + (2 * pad_x)

        # Ukuran box tinggi & koordinat posisi
        box_h = max(16, int(h * 0.053))
        y_center = (min_y + max_y) // 2
        y1 = max(0, y_center - box_h // 2)
        y2 = min(h, y1 + box_h)
        x1 = max(0, min_x - 3)

        # Pastikan box menutupi seluruh teks lama jika teks lama lebih panjang
        cover_w = max(fit_w, (max_x - x1) + 4)
        x2 = min(w, x1 + cover_w)
        target_box = (x1, y1, x2, y2)

        # Buka foto dan proses
        img = Image.open(photo_path).convert("RGB")
        arr = np.array(img)

        # Bersihkan/diffuse teks lama HANYA di area yang akan ditutup textbox
        mask = np.zeros((h, w), dtype=bool)
        mask[y1:y2, x1:x2] = True

        diffused_arr = diffuse_fill(arr, mask, steps=25)
        diffused_img = Image.fromarray(diffused_arr)

        # Tempel textbox tanggal baru tepat di posisi yang dihitung
        final_img = draw_textbox(diffused_img, target_box, new_date_text)

        # Simpan hasil
        out_name = f"demo_replaced_{name}.jpg"
        out_file = out_dir / out_name
        final_img.save(out_file, quality=95)

        log_file = logs_dir / out_name
        shutil.copy2(out_file, log_file)

        print(f"[{cat}] {name}:")
        print(f"  - Tanggal Asli Terdeteksi di: X={min_x}..{max_x}, Y={min_y}..{max_y}")
        print(f"  - Box Tanggal Baru Dipasang: {target_box}")
        print(f"  - Teks Baru Dituliskan: '{new_date_text}'")
        print(f"  - File Hasil: {log_file}\n")

    print("=" * 65)
    print(f"Semua demo gambar penggantian tanggal tersimpan di:\n{logs_dir.resolve()}")
    print("=" * 65)

if __name__ == "__main__":
    main()
