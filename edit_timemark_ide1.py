import argparse
import os
import sys
from pathlib import Path

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

DEFAULT_EXPORT_DIR_NAME = "Export_Foto"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Batch edit tanggal Timemark pada foto dokumentasi menggunakan Ide 1 (Y-center average)."
    )
    parser.add_argument(
        "--input",
        default=None,
        help="Folder input gambar. Jika kosong, script akan bertanya.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help=f"Folder output gambar. Default: <folder input>/{DEFAULT_EXPORT_DIR_NAME}",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Teks tanggal baru. Jika kosong, script akan bertanya.",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Simpan salinan preview untuk pengecekan cepat.",
    )
    parser.add_argument(
        "--y-override",
        type=int,
        default=None,
        help="Paksa posisi Y tengah watermark (skip OCR). Contoh: --y-override 195",
    )
    return parser.parse_args()


def ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def clean_prompt_value(value: str) -> str:
    return value.strip().strip('"').strip("'")


def ask_existing_folder() -> Path:
    if not sys.stdin.isatty():
        raise RuntimeError("Menjalankan dalam mode non-interaktif tetapi lokasi folder input diperlukan.")
    while True:
        value = clean_prompt_value(input("Masukkan lokasi folder input foto: "))
        folder = Path(value).expanduser()
        if folder.is_dir():
            return folder.resolve()
        print(f"Folder tidak ditemukan: {folder}")


def ask_date_text() -> str:
    if not sys.stdin.isatty():
        raise RuntimeError("Menjalankan dalam mode non-interaktif tetapi tanggal baru diperlukan (tidak ada date.txt).")
    while True:
        value = input("Masukkan tanggal baru: ").strip()
        if value:
            return value
        print("Tanggal baru tidak boleh kosong.")


def list_images(folder: Path, output_dir: Path | None = None) -> list[Path]:
    exts = {".jpg", ".jpeg", ".png"}
    skip_output = output_dir.resolve() if output_dir else None
    images = []

    for path in folder.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in exts:
            continue
        rel_parts = path.relative_to(folder).parts
        if DEFAULT_EXPORT_DIR_NAME.lower() in [part.lower() for part in rel_parts]:
            continue
        if skip_output and path.resolve().is_relative_to(skip_output):
            continue
        images.append(path)

    return sorted(images)


def get_text_box(w: int, h: int) -> tuple[int, int, int, int]:
    """
    Fallback area tanggal Timemark saat anchor watermark tidak terdeteksi.
    """
    x1 = int(w * 0.047)
    y1 = int(h * 0.735)
    x2 = int(w * 0.49)
    y2 = int(h * 0.82)
    return x1, y1, x2, y2


def contiguous_runs(values: np.ndarray) -> list[tuple[int, int]]:
    indexes = np.where(values)[0]
    if len(indexes) == 0:
        return []

    groups = []
    start = prev = int(indexes[0])
    for value in indexes[1:]:
        value = int(value)
        if value > prev + 1:
            groups.append((start, prev))
            start = value
        prev = value
    groups.append((start, prev))
    return groups


def find_red_guide(arr: np.ndarray) -> tuple[int, int, int, int] | None:
    h, w = arr.shape[:2]
    r = arr[:, :, 0].astype(int)
    g = arr[:, :, 1].astype(int)
    b = arr[:, :, 2].astype(int)
    red = (
        (r > 145)
        & (r > g * 1.3)
        & (r > b * 1.3)
        & (g < 195)
        & (b < 155)
    )

    red[: int(h * 0.54), :] = False
    red[:, int(w * 0.16) :] = False

    counts = red.sum(axis=0)
    cols = np.where(counts > max(20, int(h * 0.04)))[0]
    if len(cols) == 0:
        return None

    candidates = []
    for x1, x2 in contiguous_runs(counts > max(20, int(h * 0.04))):
        if x2 - x1 + 1 > int(w * 0.045):
            continue
        row_has_red = red[:, x1 : x2 + 1].sum(axis=1) > 0
        for y1, y2 in contiguous_runs(row_has_red):
            guide_h = y2 - y1 + 1
            if guide_h < max(25, int(h * 0.055)):
                continue
            score = int(red[y1 : y2 + 1, x1 : x2 + 1].sum())
            candidates.append((guide_h, score, x1, y1, x2, y2))

    if not candidates:
        return None

    _, _, x1, y1, x2, y2 = max(candidates)
    return x1, y1, x2, y2


def determine_template(image_path: Path, arr: np.ndarray) -> int:
    path_str = image_path.as_posix().lower()
    if "wesel" in path_str:
        return 1
    if "axc" in path_str or "sinyal" in path_str:
        return 2

    h, w = arr.shape[:2]
    guide = find_red_guide(arr)
    if guide:
        _, _, _, guide_y2 = guide
        if guide_y2 > int(h * 0.94):
            return 1
        else:
            return 2

    # Fallback by white pixel density
    w_start = int(w * 0.05)
    w_end = int(w * 0.45)
    t1_whites = 0
    t2_whites = 0
    for y in range(int(h * 0.60), int(h * 0.65)):
        t1_whites += sum(1 for x in range(w_start, w_end) if arr[y, x, 0] > 180 and arr[y, x, 1] > 180 and arr[y, x, 2] > 180)
    for y in range(int(h * 0.66), int(h * 0.69)):
        t2_whites += sum(1 for x in range(w_start, w_end) if arr[y, x, 0] > 180 and arr[y, x, 1] > 180 and arr[y, x, 2] > 180)

    if t1_whites > t2_whites:
        return 1
    else:
        return 2


def detect_date_y_center(arr: np.ndarray, h: int, w: int) -> float | None:
    img = Image.fromarray(arr)
    x1_crop = int(w * 0.01)
    x2_crop = int(w * 0.48)
    y1_crop = int(h * 0.50)
    y2_crop = int(h * 0.90)

    crop = img.crop((x1_crop, y1_crop, x2_crop, y2_crop))
    crop_large = crop.resize((crop.width * 4, crop.height * 4), Image.Resampling.LANCZOS)
    gray = ImageOps.grayscale(crop_large)

    days = {"SENIN", "SELASA", "RABU", "KAMIS", "JUMAT", "JUM'AT", "SABTU", "MINGGU"}
    months = {
        "JANUARI", "FEBRUARI", "MARET", "APRIL", "MEI", "JUNI", "JULI", "AGUSTUS", "SEPTEMBER", "OKTOBER", "NOVEMBER", "DESEMBER",
        "JAN", "FEB", "MAR", "APR", "MEI", "JUN", "JUL", "AGU", "AGS", "SEP", "OKT", "NOV", "DES"
    }
    markers = {"AM", "PM", "WIB", "WITA", "WIT"}

    import re

    y_centers = []
    for thresh in [180, 160, 200, 215, "adaptive"]:
        if thresh == "adaptive":
            sharp = crop_large.filter(ImageFilter.SHARPEN)
            gray_img = ImageOps.grayscale(sharp)
            gray_arr = np.array(gray_img).astype(float)
            local_mean = np.array(gray_img.filter(ImageFilter.BoxBlur(8))).astype(float)
            bin_arr = np.where(gray_arr > (local_mean + 10), 255, 0).astype(np.uint8)
            bin_img = Image.fromarray(bin_arr)
        else:
            gray_arr = np.array(gray)
            bin_arr = np.where(gray_arr > thresh, 255, 0).astype(np.uint8)
            bin_img = Image.fromarray(bin_arr)

        try:
            data = pytesseract.image_to_data(bin_img, config='--psm 6', output_type=pytesseract.Output.DICT)
            n_boxes = len(data["text"])
            curr_y_centers = []
            for i in range(n_boxes):
                text = data["text"][i].strip().upper()
                if not text:
                    continue
                clean_word = "".join(c for c in text if c.isalnum())
                is_year = False
                year_match = re.search(r"20\d{2}", clean_word)
                if year_match:
                    val = int(year_match.group(0))
                    if 2001 <= val <= 2999:
                        is_year = True
                is_primary = clean_word in months or is_year or clean_word in markers
                if not is_primary and len(clean_word) >= 5:
                    for m in markers:
                        if clean_word.endswith(m):
                            is_primary = True
                            break
                    prefix3 = clean_word[:3]
                    suffix = clean_word[3:]
                    if prefix3 in months and suffix.isdigit():
                        is_primary = True
                if is_primary:
                    conf = int(data["conf"][i])
                    # Gunakan threshold dinamis berdasarkan kekuatan kata kunci
                    if clean_word in months:
                        min_conf = 0    # Nama bulan: sangat spesifik, izinkan confidence rendah
                    elif clean_word in markers:
                        min_conf = 15   # Penunjuk waktu (AM/PM): longgar
                    else:
                        min_conf = 20   # Tahun (20xx): agak longgar
                        
                    if conf < min_conf:
                        continue
                    top = int(data["top"][i] / 4) + y1_crop
                    height = int(data["height"][i] / 4)
                    if int(h * 0.50) <= top <= int(h * 0.78):
                        curr_y_centers.append(top + height / 2.0)

            if not curr_y_centers:
                for i in range(n_boxes):
                    text = data["text"][i].strip().upper()
                    if not text:
                        continue
                    clean_word = "".join(c for c in text if c.isalnum())
                    if clean_word in days:
                        conf = int(data["conf"][i])
                        # Hari campuran (Senin/Rabu dll)
                        min_conf = 15 if clean_word in days else 30
                        if conf < min_conf:
                            continue
                        top = int(data["top"][i] / 4) + y1_crop
                        height = int(data["height"][i] / 4)
                        if int(h * 0.50) <= top <= int(h * 0.78):
                            curr_y_centers.append(top + height / 2.0)

            if curr_y_centers:
                ref_cy = sum(curr_y_centers) / len(curr_y_centers)
                expanded = []
                for i in range(n_boxes):
                    text = data["text"][i].strip()
                    if not text:
                        continue
                    top = int(data["top"][i] / 4) + y1_crop
                    height = int(data["height"][i] / 4)
                    cy = top + height / 2
                    if abs(cy - ref_cy) < 8:
                        expanded.append(cy)
                if len(expanded) > len(y_centers):
                    y_centers = expanded
        except Exception:
            pass

    return sum(y_centers) / len(y_centers) if y_centers else None


def detect_address_y_top(arr: np.ndarray, h: int, w: int) -> float | None:
    img = Image.fromarray(arr)
    x1_fb = int(w * 0.01)
    x2_fb = int(w * 0.38)
    y1_fb = int(h * 0.55)
    y2_fb = int(h * 0.88)
    crop_fb = img.crop((x1_fb, y1_fb, x2_fb, y2_fb))
    crop_fb_large = crop_fb.resize((crop_fb.width * 4, crop_fb.height * 4), Image.Resampling.LANCZOS)
    gray_fb = ImageOps.grayscale(crop_fb_large)
    gray_fb_arr = np.array(gray_fb)
    bin_fb_arr = np.where(gray_fb_arr > 150, 255, 0).astype(np.uint8)
    bin_fb = Image.fromarray(bin_fb_arr)

    try:
        data = pytesseract.image_to_data(bin_fb, config='--psm 4', output_type=pytesseract.Output.DICT)
        n_boxes = len(data["text"])
        text_lines = {}

        for i in range(n_boxes):
            text = data["text"][i].strip()
            if not text or len(text) < 3:
                continue
            if len([c for c in text if c.isalpha()]) < 2 and len(text) < 4:
                continue
            conf = int(data["conf"][i])
            if conf < 20:
                continue
            top = int(data["top"][i] / 4) + y1_fb
            left = int(data["left"][i] / 4) + x1_fb
            height = int(data["height"][i] / 4)
            cy = top + height / 2
            found = False
            for key in text_lines:
                if abs(text_lines[key]["avg_y"] - cy) < 10:
                    text_lines[key]["count"] += 1
                    found = True
                    break
            if not found:
                text_lines[len(text_lines)] = {"avg_y": cy, "count": 1, "top": top, "left": left}

        if text_lines:
            address_lines = {k: v for k, v in text_lines.items() if v["left"] < 30}
            if address_lines:
                best = min(address_lines.values(), key=lambda x: x["top"])
                return best["top"]
            else:
                best = min(text_lines.values(), key=lambda x: x["top"])
                return best["top"]
    except Exception:
        pass
    return None


def find_date_box_by_ocr(arr: np.ndarray, template: int = 2, y_override: int | None = None) -> tuple[int, int, int, int] | None:
    h, w = arr.shape[:2]
    box_h = int(h * 0.046)

    # 0. Override Manual
    if y_override is not None:
        y1 = y_override - int(box_h / 2) if int(box_h / 2) < y_override else 0
        y2 = y1 + box_h
        x1 = int(w * 0.047)
        x2 = int(w * 0.49)
        print(f"  STAGE 0 (Override): TextBox Y={y1}-{y2}")
        return max(0, x1), max(0, y1), min(w, x2), min(h, y2)

    # 1. Coba deteksi tanggal (Stage 1)
    avg_yc = detect_date_y_center(arr, h, w)
    if avg_yc is not None:
        y1 = int(avg_yc - box_h / 2)
        y2 = y1 + box_h
        x1 = int(w * 0.047)
        x2 = int(w * 0.49)
        print(f"  STAGE 1 (OCR Tanggal): TextBox Y={y1}-{y2}")
        return max(0, x1), max(0, y1), min(w, x2), min(h, y2)

    # 2. Fallback deteksi alamat (Stage 2)
    y_top = detect_address_y_top(arr, h, w)
    if y_top is not None:
        box_h = int(h * 0.046)
        y_ratio = y_top / h
        if y_ratio < 0.70:
            gap = 0
        elif y_ratio < 0.76:
            gap = int(h * 0.083)
        else:
            gap = int(h * 0.133)

        y1 = y_top - box_h - gap
        if template == 1:
            min_y = int(h * 0.70)
            max_y = int(h * 0.82)
        else:
            min_y = int(h * 0.60)
            max_y = int(h * 0.68)

        y1 = max(min_y, min(max_y, y1))
        y2 = y1 + box_h
        x1 = int(w * 0.047)
        x2 = int(w * 0.49)
        return max(0, x1), y1, min(w, x2), min(h, y2)

    return None


def locate_date_box(
    arr: np.ndarray,
    image_path: Path,
    y_override: int | None = None,
    folder_address_consensus: float | None = None,
    folder_date_consensus: float | None = None,
) -> tuple[int, int, int, int] | None:
    h, w = arr.shape[:2]
    template = determine_template(image_path, arr)
    box_h = int(h * 0.046)  # Tinggi standar 13px untuk h=300

    # 0. Jika y_override diset, skip semua deteksi dan pakai posisi manual
    if y_override is not None:
        box_h_manual = int(h * 0.053)
        y1 = max(0, y_override - box_h_manual // 2)
        y2 = min(h, y_override + box_h_manual // 2)
        x1 = int(w * 0.047)
        x2 = int(w * 0.49)
        print(f"  STAGE 0 (Override): TextBox Y={y1}-{y2}")
        return x1, y1, x2, y2

    # STAGE 1: Tanggal Lokal (OCR Mandiri File) - Prioritas Pertama
    y_date_local = detect_date_y_center(arr, h, w)

    # Stage 1a: Validasi Red Guide — Stage 1 hanya valid jika Y-date sejajar (±10px) dengan Red Guide
    # KECUALI jika didukung oleh konsensus tanggal tingkat folder
    if y_date_local is not None:
        is_valid = False
        if folder_date_consensus is not None and abs(y_date_local - folder_date_consensus) <= 10:
            is_valid = True
        else:
            guide = find_red_guide(arr)
            if not guide or abs(y_date_local - guide[1]) <= 10:
                is_valid = True
                
        if not is_valid:
            y_date_local = None

    if y_date_local is not None:
        y1 = int(y_date_local - box_h / 2)
        y2 = y1 + box_h
        x1 = int(w * 0.047)
        x2 = int(w * 0.49)
        print(f"  STAGE 1 (Tanggal): Y_date={y_date_local:.1f} TextBox Y={y1}-{y2}")
        return max(0, x1), max(0, y1), min(w, x2), min(h, y2)

    # STAGE 1b: Konsensus Tanggal Folder (jika OCR lokal gagal tapi folder punya voting tanggal)
    if y_date_local is None and folder_date_consensus is not None:
        y1 = int(folder_date_consensus - box_h / 2)
        y2 = y1 + box_h
        x1 = int(w * 0.047)
        x2 = int(w * 0.49)
        print(f"  STAGE 1b (Konsensus Tanggal Folder): Y_date={folder_date_consensus:.1f} TextBox Y={y1}-{y2}")
        return max(0, x1), max(0, y1), min(w, x2), min(h, y2)

    # STAGE 2: Alamat Konsensus (OCR) - Fallback Kedua
    if folder_address_consensus is not None:
        y_ratio = folder_address_consensus / h
        if y_ratio < 0.70:
            gap = 0
        elif y_ratio < 0.76:
            gap = int(h * 0.083)
        else:
            gap = int(h * 0.133)

        y1 = int(folder_address_consensus - box_h - gap)
        if template == 1:
            min_y = int(h * 0.70)
            max_y = int(h * 0.82)
        else:
            min_y = int(h * 0.60)
            max_y = int(h * 0.68)

        y1 = max(min_y, min(max_y, y1))
        y2 = int(y1 + box_h)
        x1 = int(w * 0.047)
        x2 = int(w * 0.49)
        print(f"  STAGE 2 (Alamat): addr_y={folder_address_consensus:.1f} gap={gap} TextBox Y={y1}-{y2}")
        return max(0, x1), y1, min(w, x2), min(h, y2)

    # STAGE 3: Red Guide Lokal (Pola 1) - Fallback Terakhir
    guide = find_red_guide(arr)
    if guide:
        _, guide_y1, guide_x2, guide_y2 = guide
        x1 = guide_x2 + int(w * 0.018)
        x2 = x1 + int(w * 0.42)

        if template == 1:
            y1 = guide_y2 - int(h * 0.088)
            y2 = guide_y2
        else:
            y1 = guide_y1
            y2 = y1 + box_h
        print(f"  STAGE 3 (Red Guide): guide_y1={guide_y1} TextBox Y={y1}-{y2}")
        return max(0, x1), max(0, y1), min(w, x2), min(h, y2)

    # Gagal deteksi
    print(f"  STAGE 4 (GAGAL): tidak ada deteksi")
    return None




def diffuse_fill_region(arr: np.ndarray, mask: np.ndarray, steps: int = 120) -> np.ndarray:
    """
    Fill ringan berbasis difusi dari piksel tetangga.
    """
    filled = arr.copy().astype(np.float32)
    mask3 = mask[:, :, None]

    for _ in range(steps):
        up = np.vstack([filled[:1, :, :], filled[:-1, :, :]])
        down = np.vstack([filled[1:, :, :], filled[-1:, :, :]])
        left = np.hstack([filled[:, :1, :], filled[:, :-1, :]])
        right = np.hstack([filled[:, 1:, :], filled[:, -1:, :]])
        avg = (up + down + left + right) * 0.25
        filled = np.where(mask3, avg, filled)

    return np.clip(filled, 0, 255).astype(np.uint8)


def locate_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arial.ttf",
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "segoeui.ttf",
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "calibri.ttf",
        "DejaVuSans.ttf",
        "DejaVuSans-Bold.ttf",
    ]
    for font_path in candidates:
        if isinstance(font_path, str):
            try:
                return ImageFont.truetype(font_path, size=size)
            except Exception:
                continue
        if font_path.exists():
            return ImageFont.truetype(str(font_path), size=size)
    return ImageFont.load_default()


def get_shape_box(
    img_w: int, img_h: int, text: str, box: tuple[int, int, int, int]
) -> tuple[
    tuple[int, int, int, int], ImageFont.FreeTypeFont | ImageFont.ImageFont, int, int, int
]:
    x1, y1, x2, y2 = box
    w = x2 - x1
    h = y2 - y1

    pad_x = max(2, int(img_w * 0.008))
    pad_y = max(1, int(img_h * 0.004))

    font_size = max(9, min(160, int(img_w * 0.038)))
    dummy_draw = ImageDraw.Draw(Image.new("L", (1, 1)))

    while font_size > 8:
        font = locate_font(font_size)
        fit_stroke = 1 if font_size >= 28 else 0
        bbox = dummy_draw.textbbox((0, 0), text, font=font, stroke_width=fit_stroke)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        if text_w <= w - (pad_x * 2) and text_h <= h - (pad_y * 2):
            break
        font_size -= 1
    else:
        font = locate_font(font_size)
        fit_stroke = 1 if font_size >= 28 else 0
        bbox = dummy_draw.textbbox((0, 0), text, font=font, stroke_width=fit_stroke)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

    text_x = x1 + pad_x
    text_y = y1 + ((h - text_h) // 2) - bbox[1]

    shape_pad_x = max(3, int(font_size * 0.28))
    shape_pad_y = max(2, int(font_size * 0.22))
    shape_box = (
        max(0, text_x + bbox[0] - shape_pad_x),
        max(0, text_y + bbox[1] - shape_pad_y),
        min(img_w, text_x + bbox[2] + shape_pad_x),
        min(img_h, text_y + bbox[3] + shape_pad_y),
    )
    return shape_box, font, text_x, text_y, font_size


def draw_text(
    img: Image.Image,
    text: str,
    shape_box: tuple[int, int, int, int],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    text_x: int,
    text_y: int,
    font_size: int,
) -> None:
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    
    box_h = shape_box[3] - shape_box[1]
    radius = max(2, int(box_h * 0.25))
    overlay_draw.rounded_rectangle(
        shape_box,
        radius=radius,
        fill=(0, 0, 0, 140),
    )
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))
    draw = ImageDraw.Draw(img)

    shadow_offset = max(1, int(font_size * 0.02))
    stroke_width = 1 if font_size >= 28 else 0

    # Shadow dan stroke kecil menjaga gaya watermark Timemark tetap terbaca.
    draw.text(
        (text_x + shadow_offset, text_y + shadow_offset),
        text,
        font=font,
        fill=(35, 35, 35),
        stroke_width=stroke_width,
        stroke_fill=(35, 35, 35),
    )
    draw.text(
        (text_x, text_y),
        text,
        font=font,
        fill=(248, 248, 248),
    )


def process_image(
    image_path: Path,
    output_path: Path,
    date_text: str,
    y_override: int | None = None,
    folder_address_consensus: float | None = None,
    folder_date_consensus: float | None = None,
) -> bool:
    try:
        img = Image.open(image_path)
        img = ImageOps.exif_transpose(img).convert("RGB")
    except Exception:
        return False

    arr = np.array(img)
    h, w = arr.shape[:2]
    template = determine_template(image_path, arr)

    detection = locate_date_box(
        arr, 
        image_path, 
        y_override=y_override, 
        folder_address_consensus=folder_address_consensus,
        folder_date_consensus=folder_date_consensus
    )

    is_fallback = False
    if detection is None:
        # Gagal deteksi, lewati pemrosesan file
        return False

    x1, y1, x2, y2 = detection

    # Hitung shape box
    shape_box, font, text_x, text_y, font_size = get_shape_box(w, h, date_text, (x1, y1, x2, y2))
    sx1, sy1, sx2, sy2 = shape_box

    # Masking & Erase
    pad = 2
    y1p = max(0, sy1 - pad)
    x1p = max(0, sx1 - pad)
    y2p = min(h, sy2 + pad)
    x2p = min(w, sx2 + pad)

    crop = arr[y1p:y2p, x1p:x2p]
    ry1, ry2 = sy1 - y1p, sy2 - y1p
    rx1, rx2 = sx1 - x1p, sx2 - x1p

    # Mask berbentuk rounded rectangle mengikuti shape box secara presisi
    mask_img = Image.new("L", (crop.shape[1], crop.shape[0]), 0)
    mask_draw = ImageDraw.Draw(mask_img)
    box_h = ry2 - ry1
    radius = max(2, int(box_h * 0.25))
    mask_draw.rounded_rectangle((rx1, ry1, rx2, ry2), radius=radius, fill=255)
    crop_mask = np.array(mask_img) > 0

    cleaned = arr.copy()
    cleaned[y1p:y2p, x1p:x2p] = diffuse_fill_region(crop, crop_mask, steps=60)
    
    out_img = Image.fromarray(cleaned)
    draw_text(out_img, date_text, shape_box, font, text_x, text_y, font_size)

    save_kwargs = {"quality": 95, "optimize": True}
    if image_path.suffix.lower() in {".jpg", ".jpeg"}:
        save_kwargs["subsampling"] = 0
    out_img.save(output_path, **save_kwargs)
    return True


def main() -> int:
    args = parse_args()

    if args.input:
        input_dir = Path(clean_prompt_value(args.input)).expanduser().resolve()
        if not input_dir.is_dir():
            print(f"Folder input tidak ditemukan: {input_dir}")
            return 1
    else:
        input_dir = ask_existing_folder()

    global_date_text = args.date.strip() if args.date else None
    output_dir = (
        Path(clean_prompt_value(args.output)).expanduser().resolve()
        if args.output
        else input_dir / DEFAULT_EXPORT_DIR_NAME
    )
    preview_dir = output_dir / "preview"

    ensure_dir(str(output_dir))
    if args.preview:
        ensure_dir(str(preview_dir))

    images = list_images(input_dir, output_dir)
    if not images:
        print(f"Tidak ada file gambar di: {input_dir}")
        return 0

    # Cek apakah ada file date.txt di folder gambar mana pun
    any_date_txt_exists = any((img_path.parent / "date.txt").exists() for img_path in images)
    if not global_date_text and not any_date_txt_exists:
        global_date_text = ask_date_text()

    # Kelompokkan file berdasarkan parent folder untuk pre-scan tingkat folder
    images_by_folder = {}
    for img_path in images:
        images_by_folder.setdefault(img_path.parent, []).append(img_path)

    folder_address_consensuses = {}
    folder_date_consensuses = {}

    print("Melakukan pra-pemindaian folder untuk mencari panduan posisi...")
    for folder, folder_images in images_by_folder.items():
        valid_addresses = []
        valid_dates = []
        
        for img_path in folder_images:
            try:
                with Image.open(img_path) as tmp_img:
                    arr = np.array(tmp_img.convert("RGB"))
                    h_img, w_img = arr.shape[:2]
                    
                    y_addr = detect_address_y_top(arr, h_img, w_img)
                    if y_addr:
                        valid_addresses.append(y_addr)
                        
                    y_date = detect_date_y_center(arr, h_img, w_img)
                    if y_date:
                        valid_dates.append(y_date)
            except Exception:
                pass

        # Aturan konsensus alamat (minimal 2 file konsisten < 10px)
        if len(valid_addresses) >= 2:
            best_cluster = []
            for ref_y in valid_addresses:
                cluster = [y for y in valid_addresses if abs(y - ref_y) < 10]
                if len(cluster) > len(best_cluster):
                    best_cluster = cluster
            if len(best_cluster) >= 2:
                avg_y = sum(best_cluster) / len(best_cluster)
                folder_address_consensuses[folder] = avg_y
                print(f"[VOTING] Folder '{folder.name}': Konsensus Alamat Y-top={avg_y:.1f}")

        # Aturan konsensus tanggal (minimal 2 file konsisten < 10px)
        if len(valid_dates) >= 2:
            best_date_cluster = []
            for ref_y in valid_dates:
                cluster = [y for y in valid_dates if abs(y - ref_y) < 10]
                if len(cluster) > len(best_date_cluster):
                    best_date_cluster = cluster
            if len(best_date_cluster) >= 2:
                avg_y_date = sum(best_date_cluster) / len(best_date_cluster)
                folder_date_consensuses[folder] = avg_y_date
                print(f"[VOTING] Folder '{folder.name}': Konsensus Tanggal Y-center={avg_y_date:.1f}")

    success = 0
    failed_detections = []

    for image_path in images:
        rel_path = image_path.relative_to(input_dir)
        out_path = output_dir / rel_path
        ensure_dir(str(out_path.parent))

        if out_path.resolve() == image_path.resolve():
            print(f"[FAIL] Output sama dengan file asli, dilewati: {image_path}")
            continue

        addr_consensus = folder_address_consensuses.get(image_path.parent)
        date_consensus = folder_date_consensuses.get(image_path.parent)

        # Ambil tanggal dinamis dari date.txt local jika ada
        date_text = None
        local_date_file = image_path.parent / "date.txt"
        if local_date_file.exists():
            try:
                date_text = local_date_file.read_text(encoding="utf-8").strip()
            except Exception as e:
                print(f"  [WARNING] Gagal membaca {local_date_file.name}: {e}")
        
        if not date_text:
            if not global_date_text:
                if not sys.stdin.isatty():
                    print(f"  [SKIP] File '{rel_path}' dilewati karena tidak memiliki 'date.txt' dan berjalan non-interaktif.")
                    failed_detections.append(rel_path)
                    continue
                print(f"\n[PROMPT] File '{rel_path}' tidak memiliki 'date.txt'.")
                global_date_text = ask_date_text()
            date_text = global_date_text

        ok = process_image(
            image_path, 
            out_path, 
            date_text, 
            y_override=args.y_override, 
            folder_address_consensus=addr_consensus,
            folder_date_consensus=date_consensus
        )
        
        if ok:
            success += 1
            print(f"[OK] {rel_path} (Tanggal: {date_text})")
            if args.preview:
                preview_path = preview_dir / rel_path
                ensure_dir(str(preview_path.parent))
                preview_path.write_bytes(out_path.read_bytes())
        else:
            failed_detections.append(rel_path)
            print(f"[FAIL] {rel_path} - Gagal dideteksi (dilewati, tidak diproses)")

    print(f"\nSelesai. {success}/{len(images)} gambar berhasil diproses.")
    if failed_detections:
        print(f"\n[WARNING] Sebanyak {len(failed_detections)} file GAGAL dideteksi posisinya/tanggalnya (dilewati, tidak diproses):")
        for f_path in failed_detections:
            print(f"  - {f_path}")
            
    print(f"Output: {output_dir}")
    return 0 if success > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
