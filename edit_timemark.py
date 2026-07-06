import argparse
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


DEFAULT_INPUT_DIR = "./input_foto"
DEFAULT_OUTPUT_DIR = "./output_foto"
DEFAULT_DATE_TEXT = "Jumat, Jul 03, 2026"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Batch edit tanggal Timemark pada foto dokumentasi."
    )
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT_DIR,
        help=f"Folder input gambar. Default: {DEFAULT_INPUT_DIR}",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Folder output gambar. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--date",
        default=DEFAULT_DATE_TEXT,
        help=f"Teks tanggal baru. Default: {DEFAULT_DATE_TEXT}",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Simpan salinan preview untuk pengecekan cepat.",
    )
    return parser.parse_args()


def ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def list_images(folder: Path) -> list[Path]:
    exts = {".jpg", ".jpeg", ".png"}
    return sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in exts])


def get_text_box(w: int, h: int) -> tuple[int, int, int, int]:
    """
    Fallback area tanggal Timemark saat anchor watermark tidak terdeteksi.
    """
    x1 = int(w * 0.047)
    y1 = int(h * 0.745)
    x2 = int(w * 0.49)
    y2 = int(h * 0.83)
    return x1, y1, x2, y2


def find_red_guide(arr: np.ndarray) -> tuple[int, int, int, int] | None:
    h, w = arr.shape[:2]
    red = (
        (arr[:, :, 0] > 180)
        & (arr[:, :, 1] < 100)
        & (arr[:, :, 2] < 80)
    )

    red[: int(h * 0.68), :] = False
    red[:, int(w * 0.12) :] = False

    counts = red.sum(axis=0)
    cols = np.where(counts > max(80, int(h * 0.12)))[0]
    if len(cols) == 0:
        return None

    groups = []
    start = prev = int(cols[0])
    for col in cols[1:]:
        col = int(col)
        if col > prev + 1:
            groups.append((start, prev))
            start = col
        prev = col
    groups.append((start, prev))

    x1, x2 = max(groups, key=lambda group: counts[group[0] : group[1] + 1].sum())
    ys, _ = np.where(red[:, x1 : x2 + 1])
    if len(ys) == 0:
        return None
    return x1, int(ys.min()), x2, int(ys.max())


def locate_date_box(arr: np.ndarray) -> tuple[int, int, int, int]:
    h, w = arr.shape[:2]
    guide = find_red_guide(arr)
    if not guide:
        return get_text_box(w, h)

    _, guide_y1, guide_x2, _ = guide
    x1 = guide_x2 + int(w * 0.018)
    y1 = guide_y1 - int(h * 0.03)
    x2 = x1 + int(w * 0.42)
    y2 = guide_y1 + int(h * 0.055)

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

    pad_x = max(12, int(img.width * 0.008))
    pad_y = max(6, int(img.height * 0.004))

    font_size = max(42, min(160, int(img.width * 0.038)))
    while font_size > 24:
        font = locate_font(font_size)
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=2)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        if text_w <= w - (pad_x * 2) and text_h <= h - (pad_y * 2):
            break
        font_size -= 2
    else:
        font = locate_font(font_size)
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=1)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

    text_x = x1 + pad_x
    text_y = y1 + ((h - text_h) // 2) - bbox[1]

    shape_pad_x = max(14, int(img.width * 0.008))
    shape_pad_y = max(8, int(img.height * 0.004))
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
        radius=max(8, int(img.width * 0.006)),
        fill=(0, 0, 0, 140),
    )
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))
    draw = ImageDraw.Draw(img)

    # Shadow dan stroke kecil menjaga gaya watermark Timemark tetap terbaca.
    draw.text(
        (text_x + 3, text_y + 3),
        text,
        font=font,
        fill=(35, 35, 35),
        stroke_width=1,
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
    x1, y1, x2, y2 = locate_date_box(arr)

    # Sedikit perluasan area supaya sisa huruf lama ikut terangkat.
    pad = max(10, int(w * 0.004))
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
    input_dir = Path(args.input)
    output_dir = Path(args.output)
    preview_dir = Path("preview")

    if not input_dir.exists():
        fallback_dir = Path(".")
        print(f"Folder input tidak ditemukan: {input_dir}")
        print(f"Pakai folder kerja saat ini sebagai fallback: {fallback_dir.resolve()}")
        input_dir = fallback_dir

    ensure_dir(str(output_dir))
    if args.preview:
        ensure_dir(str(preview_dir))

    images = list_images(input_dir)
    if not images:
        print(f"Tidak ada file gambar di: {input_dir}")
        return 0

    success = 0
    for image_path in images:
        out_path = output_dir / image_path.name
        ok = process_image(image_path, out_path, args.date)
        if ok:
            success += 1
            print(f"[OK] {image_path.name}")
            if args.preview:
                preview_path = preview_dir / f"preview_{image_path.name}"
                preview_path.write_bytes(out_path.read_bytes())
        else:
            print(f"[FAIL] {image_path.name}")

    print(f"Selesai. {success}/{len(images)} gambar berhasil diproses.")
    return 0 if success > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
