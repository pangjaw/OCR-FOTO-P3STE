#!/usr/bin/env python3
"""
edit_timemark_YOLO.py — YOLO-only guide detection + fixed-offset timemark editing
- YOLO is the only automatic guide detector
- Photos without detection are copied unchanged and marked .unedited
"""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

from ultralytics import YOLO

import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
# Fixed offset parameters (dari test script)
X_OFFSET_FROM_GUIDE = 6      # px right of guide right edge
Y_CENTER_OFFSET = 0          # textbox center = guide top (gy1)
BOX_HEIGHT_RATIO = 0.053     # 5.3% of image height
BOX_WIDTH_RATIO = 0.48       # 48% of image width

# Default paths
DEFAULT_INPUT = Path("03_photos_export")
DEFAULT_OUTPUT = Path("04_photos_edited")
DEFAULT_SCHEDULE = Path("schedule.json")
YOLO_MODEL_PATH = Path(__file__).with_name("best.pt")
YOLO_DATASET_DIR = Path("logs/yolo_dataset")
YOLO_LABEL_CLASS = 0
_YOLO_MODEL: YOLO | None = None

# ── Fallback durations (minutes) when schedule.json is not available ──
CATEGORY_DURATIONS = {
    "SINYAL": 30,
    "PERSINYALAN_ELEKTRIK": 420,
    "TELEKOMUNIKASI": 60,
    "SERAT OPTIK": 60,
    "PDSE": 420,
}
DEFAULT_DURATION = 45  # AXC, WESEL, CATU_DAYA, PINTU_PERLINTASAN, CTS, PTDS, PTLS, PTPP, JPL

MONTHS_ABBR = ["", "Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
DAYS_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def _read_date_txt(input_dir: Path, btp: str, category: str, identifier: str) -> str | None:
    """Read date.txt from 03_photos_export for the given asset."""
    date_path = input_dir / btp / category / identifier / "date.txt"
    if date_path.exists():
        return date_path.read_text(encoding="utf-8").strip()
    return None


def parse_date_text(text: str) -> datetime:
    """Parse Indonesian date text like 'Kamis, Jan 09 2025' or 'Kamis, Jan 09 2025 07:00'."""
    m = re.match(r'\w+, (\w+) (\d{2}) (\d{4})(?: (\d{2}):(\d{2}))?', text)
    if m:
        month = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"Mei":5,"Jun":6,
                  "Jul":7,"Agu":8,"Agt":8,"Aug":8,"Sep":9,"Okt":10,"Nov":11,"Des":12}.get(m.group(1), 1)
        return datetime(int(m.group(3)), month, int(m.group(2)),
                        int(m.group(4)) if m.group(4) else 7,
                        int(m.group(5)) if m.group(5) else 0)
    return None


def format_timemark(dt: datetime) -> str:
    return f"{DAYS_ID[dt.weekday()]}, {MONTHS_ABBR[dt.month]} {dt.day:02d} {dt.year} {dt.hour:02d}:{dt.minute:02d}"

# Station → BTP mapping (must match export_pdf_foto.py)
STATION_TO_BTP = {
    "BOO": "BTP JAK", "CLT": "BTP JAK",
    "BJD": "BTP JAK",
    "BNR": "BOP-BTT",
    "BOP": "BTP BD", "BTT": "BTP BD", "CGB": "BTP BD",
    "COS": "BTP BD", "MSG": "BTP BD", "CCR": "BTP BD",
}


def find_guide_yolo_details(arr_orig: np.ndarray, conf_threshold: float = 0.4) -> dict | None:
    """Return the highest-confidence guideline detection and training metadata."""
    global _YOLO_MODEL
    if _YOLO_MODEL is None:
        _YOLO_MODEL = YOLO(str(YOLO_MODEL_PATH))
    results = _YOLO_MODEL.predict(source=arr_orig, conf=conf_threshold, verbose=False)
    if not results or results[0].boxes is None or len(results[0].boxes) == 0:
        return None
    boxes = results[0].boxes
    best_index = int(boxes.conf.argmax().item())
    x1, y1, x2, y2 = boxes.xyxy[best_index].tolist()
    class_id = int(boxes.cls[best_index].item()) if boxes.cls is not None else YOLO_LABEL_CLASS
    confidence = float(boxes.conf[best_index].item())
    return {
        "bbox": (int(x1), int(y1), int(x2), int(y2)),
        "class_id": class_id,
        "confidence": confidence,
    }


def find_guide_yolo(arr_orig: np.ndarray, conf_threshold: float = 0.4) -> tuple[int, int, int, int] | None:
    """Return highest-confidence guide box from cached YOLO model."""
    details = find_guide_yolo_details(arr_orig, conf_threshold)
    return details["bbox"] if details else None


def _dataset_rel_path(image_path: Path) -> Path:
    """Return a stable relative path for labels without colliding on frame names."""
    try:
        return image_path.relative_to(DEFAULT_INPUT)
    except ValueError:
        return Path(image_path.name)


def _write_yolo_capture(image_path: Path, image_size: tuple[int, int],
                        detection: dict | None, stage: str) -> None:
    """Write one YOLO label and one manifest record for the current photo."""
    rel = _dataset_rel_path(image_path)
    label_path = YOLO_DATASET_DIR / "labels" / rel.with_suffix(".txt")
    label_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = image_size
    record = {
        "image": str(rel).replace("\\", "/"),
        "image_size": [width, height],
        "stage": stage,
        "status": "detected" if detection else "no_detection",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    if detection:
        x1, y1, x2, y2 = detection["bbox"]
        x1, y1 = max(0, min(x1, width)), max(0, min(y1, height))
        x2, y2 = max(x1, min(x2, width)), max(y1, min(y2, height))
        box_w, box_h = x2 - x1, y2 - y1
        xc, yc = (x1 + x2) / 2 / width, (y1 + y2) / 2 / height
        nw, nh = box_w / width, box_h / height
        label = f"{YOLO_LABEL_CLASS} {xc:.6f} {yc:.6f} {nw:.6f} {nh:.6f}"
        label_path.write_text(label + "\n", encoding="utf-8")
        record.update({"class_id": YOLO_LABEL_CLASS, "confidence": detection["confidence"],
                       "bbox": [x1, y1, x2, y2], "label": label})
    elif label_path.exists():
        label_path.unlink()
    with (YOLO_DATASET_DIR / "manifest.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


# ─── Guide Utilities ───
def contiguous_runs(values: np.ndarray):
    idx = np.where(values)[0]
    if len(idx) == 0:
        return []
    groups = []
    s = p = int(idx[0])
    for v in idx[1:]:
        v = int(v)
        if v > p + 1:
            groups.append((s, p))
            s = v
        p = v
    groups.append((s, p))
    return groups








def place_textbox_fixed_offset(guide: tuple[int,int,int,int], w: int, h: int) -> tuple[int,int,int,int]:
    """Place textbox at fixed offset from guide top-right."""
    _, gy1, gx2, _ = guide
    
    box_h = int(h * BOX_HEIGHT_RATIO)
    box_w = int(w * BOX_WIDTH_RATIO)
    
    new_x1 = gx2 + X_OFFSET_FROM_GUIDE
    new_y1 = gy1 + Y_CENTER_OFFSET - box_h // 2 + int(h * 0.018)  # shifted down
    new_x2 = min(w, new_x1 + box_w)
    new_y2 = new_y1 + box_h
    
    # Clamp
    new_y1 = max(0, new_y1)
    new_y2 = min(h, new_y2)
    new_x1 = max(0, min(new_x1, w - 1))
    new_x2 = min(w, new_x2)
    
    return new_x1, new_y1, new_x2, new_y2





def load_cropped_collages_manifest(logs_dir: str = "logs") -> set[str]:
    """Reads logs/cropped_collages.json and returns a set of normalized relative paths."""
    manifest_file = Path(logs_dir) / "cropped_collages.json"
    if not manifest_file.exists():
        return set()
    try:
        with open(manifest_file, 'r', encoding='utf-8') as f:
            paths = json.load(f)
            return set(p.replace('\\', '/').lower() for p in paths)
    except Exception as e:
        print(f"Warning: Could not read collage manifest {manifest_file}: {e}")
        return set()




def get_text_box(w: int, h: int) -> tuple[int, int, int, int]:
    """Fallback area when no guide detected (bottom-left watermark position)."""
    x1 = int(w * 0.047)
    y1 = int(h * 0.735)
    x2 = int(w * 0.49)
    y2 = int(h * 0.82)
    return x1, y1, x2, y2


# ─── Diffuse Fill (inpainting) ───
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


# ─── Font ───
# Cache font at module level to avoid repeated disk reads
_FONT_CACHE = {}

def get_font(size: int):
    if size in _FONT_CACHE:
        return _FONT_CACHE[size]
    candidates = [
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arial.ttf",
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "segoeui.ttf",
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "calibri.ttf",
        "DejaVuSans.ttf",
        "DejaVuSans-Bold.ttf",
    ]
    for fp in candidates:
        if isinstance(fp, str):
            try:
                font = ImageFont.truetype(fp, size=size)
                _FONT_CACHE[size] = font
                return font
            except:
                continue
        if fp.exists():
            font = ImageFont.truetype(str(fp), size=size)
            _FONT_CACHE[size] = font
            return font
    return ImageFont.load_default()


# ─── Draw Textbox ───
def draw_textbox(img: Image.Image, box: tuple[int,int,int,int], text: str) -> Image.Image:
    x1, y1, x2, y2 = box
    w, h = img.size
    box_h = y2 - y1
    font_size = max(9, min(160, int(w * 0.038)))
    font = get_font(font_size)

    dummy = ImageDraw.Draw(Image.new("L", (1,1)))
    fit_stroke = 1 if font_size >= 28 else 0
    bbox = dummy.textbbox((0,0), text, font=font, stroke_width=fit_stroke)
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
    draw = ImageDraw.Draw(out)

    radius = max(2, int(box_h * 0.25))
    overlay = Image.new("RGBA", out.size, (0,0,0,0))
    odraw = ImageDraw.Draw(overlay)
    odraw.rounded_rectangle(shape_box, radius=radius, fill=(0,0,0,140))
    out = Image.alpha_composite(out.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(out)

    so = max(1, int(font_size * 0.02))
    draw.text((tx+so, ty+so), text, font=font, fill=(35,35,35), stroke_width=fit_stroke, stroke_fill=(35,35,35))
    draw.text((tx, ty), text, font=font, fill=(248,248,248))

    return out


# (duplicate defs removed - see live versions below)


# ─── Main ───
def sanitize_segment(text: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', '_', text).strip()


def asset_output_dir(root: Path, btp: str, category: str, identifier: str) -> Path:
    return root / sanitize_segment(btp) / category / sanitize_segment(identifier)


def _folder_key_from_path(rel: Path, input_dir: Path | None = None) -> tuple[str, str, str] | None:
    """Extract (btp, category, identifier) from relative path for flat structure.

    Structure: [BTP/]category/identifier/photo.jpg
    Returns: (btp, category, identifier) or None
    """
    parts = rel.parts
    btp_shift = 1 if parts and parts[0].startswith("BTP") else 0
    if len(parts) >= 3 + btp_shift:
        btp = parts[0] if btp_shift else "BTP JAK"
        return btp, parts[0 + btp_shift], parts[1 + btp_shift]
    return None






def locate_date_box(arr_orig: np.ndarray, w: int, h: int,
                    y_override: int | None = None, consensus_gy1: int | None = None,
                    is_collage: bool = False):
    """Return YOLO textbox coordinates, or a no-detection stage."""
    if y_override is not None:
        box_h = int(h * BOX_HEIGHT_RATIO)
        y1 = max(0, y_override - box_h // 2)
        y2 = min(h, y1 + box_h)
        x1 = int(w * 0.047)
        x2 = int(w * 0.49)
        return (x1, y1, x2, y2), "stage_0_override"
    guide = find_guide_yolo(arr_orig)
    if guide is None:
        return None, "stage_yolo_no_detection"
    return place_textbox_fixed_offset(guide, w, h), "stage_1_yolo_detection"

# ─── Schedule Support ───
def load_schedule(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def iso_to_timemark(iso_str: str) -> str:
    """2026-07-11T09:30:00 -> Rabu, Jul 11 2026 09:30"""
    dt = datetime.fromisoformat(iso_str)
    days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    months = ["", "Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
    return f"{days[dt.weekday()]}, {months[dt.month]} {dt.day:02d} {dt.year} {dt.hour:02d}:{dt.minute:02d}"


def normalize_schedule_identifier(identifier: str) -> str:
    """Map legacy 2025 identifier to current 2026 photo folder."""
    return "ZP 41 BOO" if identifier.strip().upper() == "ZP 41B BOO" else identifier


def build_schedule_lookup(schedule_data: dict, tim_filter: int | None = None):
    """Build {(btp, category, identifier, photo): (timemark_text, tim_n)}."""
    lookup = {}
    for sched in schedule_data.get("schedules", []):
        tim_n = sched.get("tim", 1)
        if tim_filter is not None and tim_n != tim_filter:
            continue
        btp = sched.get("btp", "BTP JAK")
        category = sched.get("category", "UNKNOWN")
        identifier = normalize_schedule_identifier(sched.get("identifier") or sched.get("pdf_stem", ""))
        for pname, iso_ts in sched.get("photos", {}).items():
            key = (btp, category, identifier, pname)
            new_val = (iso_to_timemark(iso_ts), tim_n)
            existing = lookup.get(key)
            if existing is None or tim_n > existing[1]:
                lookup[key] = new_val
    return lookup






# ─── Process Single Image ───
def process_image(image_path: Path, output_path: Path, timemark_text: str, y_override: int | None = None, x_override: int | None = None, schedule_lookup=None, asset_key=None) -> str:
    actual_input_path = image_path
    if "03_photos_export" in str(image_path):
        try:
            parts = Path(image_path).parts
            if "03_photos_export" in parts:
                idx = parts.index("03_photos_export")
                rel_p = Path(*parts[idx+1:])
                cand_temp = Path("03_photos_cropped_temp") / rel_p
                if cand_temp.exists():
                    actual_input_path = cand_temp
        except Exception:
            pass

    img_orig = Image.open(actual_input_path).convert("RGB")
    w, h = img_orig.size
    arr_orig = np.array(img_orig)

    detection = None
    if y_override is not None:
        box_w = int(w * BOX_WIDTH_RATIO)
        box_h = int(h * BOX_HEIGHT_RATIO)
        if y_override <= 300 and h > 300:
            y1 = int((y_override / 300.0) * h)
        else:
            y1 = y_override

        if x_override is not None:
            if x_override <= 300 and w > 300:
                x1 = int((x_override / 300.0) * w)
            else:
                x1 = x_override
        else:
            x1 = int(w * 0.047)

        x2 = min(w, x1 + box_w)
        y2 = min(h, y1 + box_h)
        box = (x1, y1, x2, y2)
        stage = "stage_0_override"
    else:
        detection = find_guide_yolo_details(arr_orig)
        if detection is None:
            box, stage = None, "stage_yolo_no_detection"
        else:
            box = place_textbox_fixed_offset(detection["bbox"], w, h)
            stage = "stage_1_yolo_detection"

    _write_yolo_capture(image_path, (w, h), detection, stage)

    # ── No YOLO detection → copy as-is, no edit ──
    if stage == "stage_yolo_no_detection":
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(image_path, output_path)
        # Flag file: per-photo marker for merge step
        flag_path = output_path.with_suffix(output_path.suffix + ".unedited")
        flag_path.write_text("")
        return stage

    x1, y1, x2, y2 = box

    # Blur: fill box area with diffuse inpainting (full rectangle, matches textbox)
    crop = arr_orig[y1:y2, x1:x2]
    box_h_px = y2 - y1
    radius = max(2, int(box_h_px * 0.25))

    mask_img = Image.new("L", (x2 - x1, y2 - y1), 255)  # full mask = entire box blurred

    arr_work = arr_orig.copy()
    arr_work[y1:y2, x1:x2] = diffuse_fill(crop, np.array(mask_img) > 0, steps=60)

    img_erased = Image.fromarray(arr_work)

    # Draw textbox
    img_out = draw_textbox(img_erased, box, timemark_text)

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img_out.save(output_path, quality=95, subsampling=0)

    return stage


def main():
    parser = argparse.ArgumentParser(description="Edit timemark on photos (Fixed-offset + Folder Consensus)")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Input photos folder")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output photos folder")
    parser.add_argument("--date", type=str, help="Global date text (e.g. 'Sabtu, Apr 29 2026 08:00')")
    parser.add_argument("--schedule", type=Path, help="schedule.json for per-photo timestamps")
    parser.add_argument("--y-override", type=int, help="Force Y position for textbox")
    parser.add_argument("--x-override", type=int, help="Force X position for textbox")
    parser.add_argument("--single-out", type=Path, help="Force specific single output file path")
    parser.add_argument("--clear-output", action="store_true", help="Clear output folder first")
    parser.add_argument("--tim-filter", type=int, help="Process only schedule entries for this Tim number")
    args = parser.parse_args()

    input_dir = args.input
    output_dir = args.output

    if args.clear_output and output_dir.exists():
        shutil.rmtree(output_dir, ignore_errors=True)

    schedule_lookup = None
    if args.schedule and args.schedule.exists():
        schedule_data = load_schedule(args.schedule)
        schedule_lookup = build_schedule_lookup(schedule_data, args.tim_filter)

    date_text = args.date or ""  # empty if not provided; schedule_lookup handles dates

    if input_dir.is_file():
        all_jpgs = [input_dir]
    else:
        all_jpgs = list(input_dir.rglob("*.jpg"))

    ok = 0
    failed = 0
    skipped = 0
    stage_counts = {
        "stage_0_override": 0,
        "stage_1_yolo_detection": 0,
        "stage_yolo_no_detection": 0
    }
    stage_details = []
    failed_files = []
    missing_dates = []
    unedited_files = []  # Track unedited photos for Excel
    tim_mapping = {}  # photo_rel_path -> tim_n

    for src in all_jpgs:
        try:
            rel = src.relative_to(DEFAULT_INPUT)
        except ValueError:
            rel = src.relative_to(input_dir) if input_dir.is_dir() else Path(src.name)
        parts = rel.parts
        # Flat structure: [BTP/]category/identifier/photo.jpg
        btp_shift = 1 if parts and parts[0].startswith("BTP") else 0
        if len(parts) < 3 + btp_shift:
            failed_files.append({"file": str(rel), "reason": "invalid_asset_path", "expected": "BTP/category/identifier/photo.jpg"})
            continue
        btp = parts[0] if btp_shift else "BTP JAK"
        category = parts[0 + btp_shift]
        identifier = normalize_schedule_identifier(parts[1 + btp_shift])
        photo_name = parts[2 + btp_shift]
        asset_key = (btp, category, identifier, photo_name)
        if args.tim_filter is not None and (not schedule_lookup or asset_key not in schedule_lookup):
            continue

        tim_n = 1
        if args.date:
            timemark_text = args.date
            dst_dir = output_dir / f"Tim_{tim_n}"
        elif schedule_lookup and asset_key:
            result = schedule_lookup.get(asset_key)
            if result:
                timemark_text, tim_n = result
                dst_dir = output_dir / f"Tim_{tim_n}" / asset_output_dir(Path(""), btp, category, identifier)
            else:
                # Schedule exists but this photo not in it — try date.txt fallback
                folder_date = _read_date_txt(input_dir, btp, category, identifier)
                if folder_date:
                    dt = parse_date_text(folder_date)
                    if dt:
                        pct = 0
                        name_stem = Path(photo_name).stem
                        if name_stem == "50": pct = 50
                        elif name_stem == "100": pct = 100
                        duration = CATEGORY_DURATIONS.get(category.upper(), DEFAULT_DURATION)
                        offset_minutes = int(pct * duration / 100)
                        photo_dt = dt + timedelta(minutes=offset_minutes)
                        timemark_text = format_timemark(photo_dt)
                        dst_dir = output_dir / f"Tim_{tim_n}" / asset_output_dir(Path(""), btp, category, identifier)
                    else:
                        missing_dates.append({"folder": str(rel.parent), "btp": btp, "category": category, "identifier": identifier, "reason": "date.txt unreadable"})
                        skipped += 1
                        continue
                else:
                    # Fallback date if not in schedule & no date.txt
                    timemark_text = date_text or format_timemark(datetime.now())
                    dst_dir = output_dir / f"Tim_{tim_n}" / asset_output_dir(Path(""), btp, category, identifier)
        else:
            # No schedule — try date.txt
            folder_date = _read_date_txt(input_dir, btp, category, identifier)
            if folder_date:
                dt = parse_date_text(folder_date)
                if dt:
                    pct = 0
                    name_stem = Path(photo_name).stem
                    if name_stem == "50": pct = 50
                    elif name_stem == "100": pct = 100
                    duration = CATEGORY_DURATIONS.get(category.upper(), DEFAULT_DURATION)
                    offset_minutes = int(pct * duration / 100)
                    photo_dt = dt + timedelta(minutes=offset_minutes)
                    timemark_text = format_timemark(photo_dt)
                    dst_dir = output_dir / f"Tim_{tim_n}" / asset_output_dir(Path(""), btp, category, identifier)
                else:
                    timemark_text = date_text or format_timemark(datetime.now())
                    dst_dir = output_dir / f"Tim_{tim_n}" / asset_output_dir(Path(""), btp, category, identifier)
            else:
                timemark_text = date_text or format_timemark(datetime.now())
                dst_dir = output_dir / f"Tim_{tim_n}" / asset_output_dir(Path(""), btp, category, identifier)
        tim_mapping[str(rel)] = tim_n
        dst = args.single_out if args.single_out else (dst_dir / src.name)

        try:
            stage = process_image(src, dst, timemark_text, args.y_override, args.x_override, schedule_lookup, asset_key)
            ok += 1
            if stage in stage_counts:
                stage_counts[stage] += 1
            stage_details.append({
                "file": str(rel),
                "stage": stage,
                "asset_type": category,
                "detail": identifier,
                "photo": photo_name,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            # Track unedited fallbacks for Excel log
            if stage == "stage_yolo_no_detection":
                unedited_files.append({
                    "btp": btp,
                    "category": category,
                    "identifier": identifier,
                    "photo": photo_name,
                    "source": str(src),
                    "output": str(dst),
                    "stage": stage,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            print(json.dumps({
                "type": "stage",
                "file": str(rel),
                "stage": stage,
                "asset_type": category,
                "detail": identifier,
                "photo": photo_name
            }), flush=True)
        except Exception as e:
            print(f"[ERROR] process_image failed: {e}", sys.stderr)
            failed += 1
            failed_files.append({
                "file": str(rel),
                "asset_type": category,
                "detail": identifier,
                "photo": photo_name,
                "reason": str(e),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })



    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Write tim_mapping.json if schedule was used
    if args.schedule and tim_mapping:
        tim_mapping_data = {
            "version": 1,
            "generated_at": datetime.now().isoformat(),
            "mapping": tim_mapping,
            "tims_used": sorted(set(tim_mapping.values()))
        }
        with open(logs_dir / "tim_mapping.json", "w", encoding="utf-8") as f:
            json.dump(tim_mapping_data, f, indent=2, ensure_ascii=False)

    if stage_details:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Stage Details"
        headers = ["File", "Stage", "Asset Type", "Detail Aset", "Photo", "Timestamp"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            cell.font = Font(bold=True, color="FFFFFF")
        for row_idx, item in enumerate(stage_details, 2):
            ws.cell(row=row_idx, column=1, value=item["file"])
            ws.cell(row=row_idx, column=2, value=item["stage"])
            ws.cell(row=row_idx, column=3, value=item["asset_type"])
            ws.cell(row=row_idx, column=4, value=item["detail"])
            ws.cell(row=row_idx, column=5, value=item["photo"])
            ws.cell(row=row_idx, column=6, value=item["timestamp"])
        for col in ws.columns:
            max_length = max(len(str(cell.value)) if cell.value else 0 for cell in col)
            ws.column_dimensions[col[0].column_letter].width = max_length + 2
        wb.save(logs_dir / "edit_stages.xlsx")

    if failed_files:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Failed Files"
        headers = ["File", "Asset Type", "Detail Aset", "Photo", "Alasan", "Timestamp"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="FF4444", end_color="FF4444", fill_type="solid")
            cell.font = Font(bold=True, color="FFFFFF")
        for row_idx, item in enumerate(failed_files, 2):
            ws.cell(row=row_idx, column=1, value=item["file"])
            ws.cell(row=row_idx, column=2, value=item["asset_type"])
            ws.cell(row=row_idx, column=3, value=item["detail"])
            ws.cell(row=row_idx, column=4, value=item["photo"])
            ws.cell(row=row_idx, column=5, value=item["reason"])
            ws.cell(row=row_idx, column=6, value=item["timestamp"])
        for col in ws.columns:
            max_length = max(len(str(cell.value)) if cell.value else 0 for cell in col)
            ws.column_dimensions[col[0].column_letter].width = max_length + 2
        wb.save(logs_dir / "edit_failed.xlsx")

    if missing_dates:
        # Deduplicate by folder
        seen_folders = set()
        unique_missing = []
        for item in missing_dates:
            if item["folder"] not in seen_folders:
                seen_folders.add(item["folder"])
                unique_missing.append(item)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Missing Dates"
        headers = ["Folder", "BTP", "Category", "Identifier", "Alasan"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="FF8800", end_color="FF8800", fill_type="solid")
            cell.font = Font(bold=True, color="FFFFFF")
        for row_idx, item in enumerate(unique_missing, 2):
            ws.cell(row=row_idx, column=1, value=item["folder"])
            ws.cell(row=row_idx, column=2, value=item["btp"])
            ws.cell(row=row_idx, column=3, value=item["category"])
            ws.cell(row=row_idx, column=4, value=item["identifier"])
            ws.cell(row=row_idx, column=5, value=item["reason"])
        for col in ws.columns:
            max_length = max(len(str(cell.value)) if cell.value else 0 for cell in col)
            ws.column_dimensions[col[0].column_letter].width = max_length + 2
        wb.save(logs_dir / "missing_dates.xlsx")

    if unedited_files:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Unedited Photos"
        headers = ["BTP", "Category", "Identifier/Aset", "Foto", "Stage", "Source Path", "Output Path", "Timestamp"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="FF8800", end_color="FF8800", fill_type="solid")
            cell.font = Font(bold=True, color="FFFFFF")
        for row_idx, item in enumerate(unedited_files, 2):
            ws.cell(row=row_idx, column=1, value=item["btp"])
            ws.cell(row=row_idx, column=2, value=item["category"])
            ws.cell(row=row_idx, column=3, value=item["identifier"])
            ws.cell(row=row_idx, column=4, value=item["photo"])
            ws.cell(row=row_idx, column=5, value=item.get("stage", "stage_yolo_no_detection"))
            ws.cell(row=row_idx, column=6, value=item["source"])
            ws.cell(row=row_idx, column=7, value=item["output"])
            ws.cell(row=row_idx, column=8, value=item["timestamp"])
        for col in ws.columns:
            max_length = max(len(str(cell.value)) if cell.value else 0 for cell in col)
            ws.column_dimensions[col[0].column_letter].width = max_length + 2
        wb.save(logs_dir / "unedited_photos.xlsx")

    summary = {
        "step": "edit",
        "success": ok,
        "failed": failed,
        "skipped": skipped,
        "missing_dates": len(unique_missing) if missing_dates else 0,
        "stage_counts": stage_counts,
        "failed_file": "logs/edit_failed.xlsx" if failed_files else None,
        "stages_file": "logs/edit_stages.xlsx" if stage_details else None,
        "missing_dates_file": "logs/missing_dates.xlsx" if missing_dates else None
    }
    print(f"__SUMMARY__:{json.dumps(summary)}", flush=True)


if __name__ == "__main__":
    main()
