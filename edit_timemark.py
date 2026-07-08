import argparse
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


DEFAULT_EXPORT_DIR_NAME = "Export_Foto"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Batch edit tanggal Timemark pada foto dokumentasi."
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
    return parser.parse_args()


def ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def clean_prompt_value(value: str) -> str:
    return value.strip().strip('"').strip("'")


def ask_existing_folder() -> Path:
    while True:
        value = clean_prompt_value(input("Masukkan lokasi folder input foto: "))
        folder = Path(value).expanduser()
        if folder.is_dir():
            return folder.resolve()
        print(f"Folder tidak ditemukan: {folder}")


def ask_date_text() -> str:
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
        & (r > g + 22)
        & (r > b + 45)
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


def locate_date_box(arr: np.ndarray, image_path: Path) -> tuple[int, int, int, int]:
    h, w = arr.shape[:2]
    template = determine_template(image_path, arr)

    guide = find_red_guide(arr)
    if guide:
        _, guide_y1, guide_x2, guide_y2 = guide
        x1 = guide_x2 + int(w * 0.018)
        x2 = x1 + int(w * 0.42)

        if template == 1:
            # Wesel: anchor dari guide_y2 yang selalu terdeteksi benar.
            # guide_y2 ≈ 0.977*h; tanggal berada 0.107*h s.d. 0.190*h di atas guide_y2.
            y2 = guide_y2 - int(h * 0.107)
            y1 = guide_y2 - int(h * 0.190)
        else:
            # AXC/Sinyal: gunakan guide_y1 seperti semula.
            y1 = guide_y1 - int(h * 0.03)
            y2 = guide_y1 + int(h * 0.055)
    else:
        x1 = int(w * 0.047)
        x2 = int(w * 0.49)
        if template == 1:
            y1 = int(h * 0.787)
            y2 = int(h * 0.870)
        else:
            y1 = int(h * 0.633)
            y2 = int(h * 0.717)

    return (
        max(0, x1),
        max(0, y1),
        min(w, x2),
        min(h, y2),
    )


def diffuse_fill_region(arr: np.ndarray, mask: np.ndarray, steps: int = 120) -> np.ndarray:
    """
    Fill ringan berbasis difusi dari piksel tetangga.
    Ini bukan inpainting AI, tapi cukup stabil untuk area teks kecil.
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


def draw_text(img: Image.Image, text: str, box: tuple[int, int, int, int]) -> None:
    draw = ImageDraw.Draw(img)
    x1, y1, x2, y2 = box
    w = x2 - x1
    h = y2 - y1

    pad_x = max(2, int(img.width * 0.008))
    pad_y = max(1, int(img.height * 0.004))

    font_size = max(9, min(160, int(img.width * 0.038)))
    while font_size > 8:
        font = locate_font(font_size)
        fit_stroke = 1 if font_size >= 28 else 0
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=fit_stroke)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        if text_w <= w - (pad_x * 2) and text_h <= h - (pad_y * 2):
            break
        font_size -= 1
    else:
        font = locate_font(font_size)
        fit_stroke = 1 if font_size >= 28 else 0
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=fit_stroke)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

    text_x = x1 + pad_x
    text_y = y1 + ((h - text_h) // 2) - bbox[1]

    shape_pad_x = max(3, int(font_size * 0.28))
    shape_pad_y = max(2, int(font_size * 0.22))
    shape_box = (
        max(0, text_x + bbox[0] - shape_pad_x),
        max(0, text_y + bbox[1] - shape_pad_y),
        min(img.width, text_x + bbox[2] + shape_pad_x),
        min(img.height, text_y + bbox[3] + shape_pad_y),
    )
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle(
        shape_box,
        radius=max(2, int(font_size * 0.25)),
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


def process_image(image_path: Path, output_path: Path, date_text: str) -> bool:
    try:
        img = Image.open(image_path)
        img = ImageOps.exif_transpose(img).convert("RGB")
    except Exception:
        return False

    arr = np.array(img)
    h, w = arr.shape[:2]
    x1, y1, x2, y2 = locate_date_box(arr, image_path)

    # Sedikit perluasan area supaya sisa huruf lama ikut terangkat.
    pad = max(3, int(w * 0.002))
    y1p = max(0, y1 - pad)
    x1p = max(0, x1 - pad)
    y2p = min(h, y2 + pad)
    x2p = min(w, x2 + pad)

    crop = arr[y1p:y2p, x1p:x2p]
    crop_mask = np.zeros((crop.shape[0], crop.shape[1]), dtype=bool)
    crop_mask[y1 - y1p : y2 - y1p, x1 - x1p : x2 - x1p] = True

    cleaned = arr.copy()
    cleaned[y1p:y2p, x1p:x2p] = diffuse_fill_region(crop, crop_mask, steps=160)
    out_img = Image.fromarray(cleaned)
    draw_text(out_img, date_text, (x1, y1, x2, y2))

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

    date_text = args.date.strip() if args.date else ask_date_text()
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

    success = 0
    for image_path in images:
        rel_path = image_path.relative_to(input_dir)
        out_path = output_dir / rel_path
        ensure_dir(str(out_path.parent))

        if out_path.resolve() == image_path.resolve():
            print(f"[FAIL] Output sama dengan file asli, dilewati: {image_path}")
            continue

        ok = process_image(image_path, out_path, date_text)
        if ok:
            success += 1
            print(f"[OK] {rel_path}")
            if args.preview:
                preview_path = preview_dir / rel_path
                ensure_dir(str(preview_path.parent))
                preview_path.write_bytes(out_path.read_bytes())
        else:
            print(f"[FAIL] {rel_path}")

    print(f"Selesai. {success}/{len(images)} gambar berhasil diproses.")
    print(f"Output: {output_dir}")
    return 0 if success > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
