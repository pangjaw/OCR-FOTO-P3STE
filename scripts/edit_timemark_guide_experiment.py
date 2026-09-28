#!/usr/bin/env python3
"""
edit_timemark_ide1.py — Versi baru: HSV Orange Isolation + Fixed-offset Stage 1c
- Hapus Stage 1, 1b, 2, 3, 4, consensus pre-scan
- Hanya: HSV isolate -> find_red_guide -> fixed offset dari guide top-right
- Fallback: get_text_box() jika tidak ada guide
"""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

import pytesseract

import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# Fixed offset parameters (dari test script)
X_OFFSET_FROM_GUIDE = 6      # px right of guide right edge
Y_CENTER_OFFSET = 0          # textbox center = guide top (gy1)
BOX_HEIGHT_RATIO = 0.053     # 5.3% of image height
BOX_WIDTH_RATIO = 0.48       # 48% of image width

# Default paths
DEFAULT_INPUT = Path("03_photos_export")
DEFAULT_OUTPUT = Path("04_photos_edited")
DEFAULT_SCHEDULE = Path("schedule.json")

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
    candidates = [
        DEFAULT_INPUT / btp / category / identifier / "date.txt",
        DEFAULT_INPUT.resolve() / btp / category / identifier / "date.txt",
        input_dir / "date.txt",
        input_dir / btp / category / identifier / "date.txt",
    ]
    for date_path in candidates:
        if date_path.exists():
            return date_path.read_text(encoding="utf-8").strip().removesuffix("\n")
    return None


def normalize_manual_date_text(text: str) -> str:
    """Remove a duplicated trailing HH:MM produced by the manual UI."""
    text = (text or "").strip()
    match = re.match(r"^(.*?\s\d{2}:\d{2})(?:\s+\d{2}:\d{2})+$", text)
    return match.group(1) if match else text


def _read_manual_meta(asset_dir: Path, photo_name: str) -> dict:
    """Read manual UI correction for one photo from the destination asset folder."""
    meta_path = asset_dir / "meta.json"
    if not meta_path.exists():
        return {}
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        item = data.get(photo_name, {})
        if not item.get("manualEdit"):
            return {}
        return item
    except (OSError, json.JSONDecodeError):
        return {}


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
    "BNR": "BTP BD",
    "BOP": "BTP BD", "BTT": "BTP BD", "CGB": "BTP BD",
    "COS": "BTP BD", "MSG": "BTP BD", "CCR": "BTP BD",
}


# ─── HSV Orange Isolation ───
def preprocess_for_guide(img: Image.Image) -> np.ndarray:
    """Grayscale all colors EXCEPT pure red guide (Hue 0-15° or 350-360°, S>60%, V 30-80%)."""
    arr = np.array(img).astype(np.float32) / 255.0
    r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]

    maxc = np.maximum(np.maximum(r, g), b)
    minc = np.minimum(np.minimum(r, g), b)
    val = maxc
    delta = maxc - minc
    # Suppress divide-by-zero warning; np.where handles maxc==0 case
    with np.errstate(invalid='ignore', divide='ignore'):
        sat = np.where(maxc > 0, delta / maxc, 0)

    hue = np.zeros_like(r)
    m = delta > 0
    rm = m & (maxc == r)
    hue[rm] = (60 * ((g[rm] - b[rm]) / delta[rm])) % 360
    gm = m & (maxc == g)
    hue[gm] = 60 * ((b[gm] - r[gm]) / delta[gm]) + 120
    bm = m & (maxc == b)
    hue[bm] = 60 * ((r[bm] - g[bm]) / delta[bm]) + 240

    # Pure red mask: Hue 0-10° or 350-360°, Sat>65%, Val 25-85%
    # Excludes orange (15-35°) that appears behind red guide
    is_red = (
        ((hue <= 10) | (hue >= 350))
        & (sat >= 0.65)
        & (val >= 0.25)
        & (val <= 0.85)
    )

    gray = 0.299*r + 0.587*g + 0.114*b

    out = np.stack([
        np.where(is_red, r, gray),
        np.where(is_red, g, gray),
        np.where(is_red, b, gray),
    ], axis=2)

    return (np.clip(out, 0, 1) * 255).astype(np.uint8)


# ─── Red Guide Detection ───
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


def find_red_guide(arr: np.ndarray, y_start: int | None = None):
    """Deteksi garis merah/kuning/oranye vertikal (Red/Yellow Guide) di area kiri foto.

    Mendukung Red, Orange, dan Yellow guide (Hue 0°-52°, Saturation >= 50%).
    Menggunakan algoritma Local Column Peak Prominence, clean vertical line check,
    dan filter lebar maksimal (<= 8-10px) tanpa Top Crop (y=0 hingga y=h).
    """
    h, w = arr.shape[:2]
    if y_start is None:
        y_start = 0

    r = arr[:,:,0].astype(float)
    g = arr[:,:,1].astype(float)
    b = arr[:,:,2].astype(float)

    # Combined Red & Yellow guide filter (r > 172)
    red_yellow = (
        (r > 172)
        & (r > g * 1.10)
        & (r > b * 1.35)
        & (g < 215)
        & (b < 160)
    )

    # HSV filter: Red, Orange, Yellow (Hue <= 52° or >= 330°) + Sat >= 63%
    delta = r - np.minimum(g, b)
    safe_delta = np.where(delta > 0, delta, 1.0)
    hue = (g - b) / safe_delta * 60
    hue = np.where(hue < 0, hue + 360, hue)
    max_c = np.maximum(np.maximum(r, g), b)
    sat = np.where(max_c > 0, delta / max_c * 100, 0.0)

    ry_mask = red_yellow & ((hue <= 52.0) | (hue >= 330.0)) & (sat >= 63.0)

    if y_start > 0:
        ry_mask[:y_start, :] = False
    
    # Restrict search to X <= 35% of width (max 105px)
    max_x_search = int(max(48, w * 0.35))
    ry_mask[:, max_x_search:] = False

    counts = ry_mask.astype(int).sum(axis=0)

    # Local column peak prominence + Clean vertical line check (gap check)
    prominent_mask = np.zeros(w, dtype=bool)
    min_h = max(20, int(h * 0.065))

    for x in range(max_x_search):
        if counts[x] < min_h:
            continue
        w_start = max(0, x - 6)
        w_end = min(max_x_search, x + 7)
        neighbor_vals = [counts[nx] for nx in range(w_start, w_end) if abs(nx - x) >= 3 and counts[nx] > 0]
        local_bg = np.median(neighbor_vals) if neighbor_vals else 0
        if counts[x] >= local_bg + 20 or counts[x] >= local_bg * 1.35:
            left_bg = np.min([counts[nx] for nx in range(max(0, x-4), max(0, x-1))] or [0])
            right_bg = np.min([counts[nx] for nx in range(min(max_x_search, x+2), min(max_x_search, x+5))] or [0])
            if left_bg <= counts[x] * 0.60 or right_bg <= counts[x] * 0.60:
                prominent_mask[x] = True

    max_allowed_width = 2  # Strict 1-2px guide width requirement for standard photos

    # Split wide runs at drop-off (count < peak * 0.35)
    def _split_wide_run(x1, x2, cnt_array=None):
        if cnt_array is None:
            cnt_array = counts
        run_cols = list(range(x1, x2 + 1))
        if len(run_cols) <= max_allowed_width:
            return [(x1, x2)]
        peak_count = max(cnt_array[x] for x in run_cols)
        threshold = peak_count * 0.35
        sub_runs = []
        sub_start = run_cols[0]
        for x in run_cols[1:]:
            if cnt_array[x] < threshold:
                sub_runs.append((sub_start, x - 1))
                sub_start = x
        sub_runs.append((sub_start, run_cols[-1]))
        return sub_runs

    candidates = []
    for x1, x2 in contiguous_runs(prominent_mask):
        run_width = x2 - x1 + 1
        if run_width > max_allowed_width:
            raw_sub = _split_wide_run(x1, x2)
            sub_runs = []
            for sx1, sx2 in raw_sub:
                if sx2 - sx1 + 1 <= max_allowed_width:
                    sub_runs.append((sx1, sx2))
                else:
                    # Enumerate sliding windows for sub-runs still too wide
                    for w in range(sx1, sx2 + 1):
                        sub_runs.append((w, w))
                    for w in range(sx1, sx2):
                        sub_runs.append((w, w + 1))
            if not sub_runs:
                # Fallback: enumerate all windows in original run
                for w in range(x1, x2 + 1):
                    sub_runs.append((w, w))
                for w in range(x1, x2):
                    sub_runs.append((w, w + 1))
        else:
            sub_runs = [(x1, x2)]

        for sx1, sx2 in sub_runs:
            row_has = ry_mask[:, sx1:sx2+1].sum(axis=1) > 0
            raw_runs = contiguous_runs(row_has)
            if not raw_runs:
                continue
            # Merge runs separated by small vertical gaps (<= 5 px)
            merged_runs = [list(raw_runs[0])]
            for ry1, ry2 in raw_runs[1:]:
                if ry1 - merged_runs[-1][1] <= 5:
                    merged_runs[-1][1] = ry2
                else:
                    merged_runs.append([ry1, ry2])

            for y1, y2 in merged_runs:
                guide_h = y2 - y1 + 1
                if guide_h < max(20, int(h * 0.045)):
                    continue
                score = int(ry_mask[y1:y2+1, sx1:sx2+1].sum())
                candidates.append((guide_h, score, sx1, y1, sx2, y2))

    if not candidates:
        return None
    # Sort by highest score first, then leftmost X (highest score = most pixels = true guide)
    candidates.sort(key=lambda c: (-c[1], c[2]))
    _, _, x1, y1, x2, y2 = candidates[0]
    return x1, y1, x2, y2


def find_amber_guide_initial(arr: np.ndarray, y_start: int | None = None):
    """Original amber detector: longest thin continuous 1-3 px run."""
    h, w = arr.shape[:2]
    y_start = int(h * 0.54) if y_start is None else y_start

    rgb = arr.astype(float) / 255.0
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    max_c = np.max(rgb, axis=2)
    min_c = np.min(rgb, axis=2)
    delta = max_c - min_c
    hue = np.zeros_like(max_c)
    nonzero = delta > 0
    red_max = (max_c == r) & nonzero
    green_max = (max_c == g) & nonzero
    blue_max = (max_c == b) & nonzero
    hue[red_max] = (60 * ((g[red_max] - b[red_max]) / delta[red_max]) + 360) % 360
    hue[green_max] = 60 * ((b[green_max] - r[green_max]) / delta[green_max] + 2)
    hue[blue_max] = 60 * ((r[blue_max] - g[blue_max]) / delta[blue_max] + 4)
    sat = np.divide(delta, max_c, out=np.zeros_like(delta), where=max_c > 0) * 100
    mask = (hue >= 14) & (hue <= 35) & (sat >= 55) & (max_c * 100 >= 45)
    mask[:y_start, :] = False
    max_x = int(w * 0.16)
    mask[:, max_x:] = False

    min_height = max(25, int(h * 0.20))
    candidates = []
    for x1 in range(max_x):
        for width in (1, 2, 3):
            x2 = x1 + width - 1
            if x2 >= max_x:
                continue
            row_has = mask[:, x1:x2 + 1].any(axis=1)
            for gy1, gy2 in contiguous_runs(row_has):
                guide_h = gy2 - gy1 + 1
                if guide_h < min_height:
                    continue
                pixels = int(mask[gy1:gy2 + 1, x1:x2 + 1].sum())
                density = pixels / (guide_h * width)
                if density >= 0.80:
                    candidates.append((guide_h, density, pixels, width, -x1, x1, gy1, x2, gy2))
    if not candidates:
        return None
    *_, x1, gy1, x2, gy2 = max(candidates)
    return x1, gy1, x2, gy2


def find_amber_guide_v4(arr: np.ndarray, y_start: int | None = None):
    """V4 amber candidate with local geometry and white-run correction."""
    h, w = arr.shape[:2]
    y_start = int(h * 0.54) if y_start is None else y_start

    rgb = arr.astype(float) / 255.0
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    max_c = np.max(rgb, axis=2)
    min_c = np.min(rgb, axis=2)
    delta = max_c - min_c

    hue = np.zeros_like(max_c)
    nonzero = delta > 0
    red_max = (max_c == r) & nonzero
    green_max = (max_c == g) & nonzero
    blue_max = (max_c == b) & nonzero
    hue[red_max] = (60 * ((g[red_max] - b[red_max]) / delta[red_max]) + 360) % 360
    hue[green_max] = 60 * ((b[green_max] - r[green_max]) / delta[green_max] + 2)
    hue[blue_max] = 60 * ((r[blue_max] - g[blue_max]) / delta[blue_max] + 4)
    sat = np.divide(delta, max_c, out=np.zeros_like(delta), where=max_c > 0) * 100
    value = max_c * 100

    mask = (hue >= 14) & (hue <= 35) & (sat >= 55) & (value >= 45)
    mask[:y_start, :] = False
    max_x = int(w * 0.16)
    mask[:, max_x:] = False

    min_height = max(25, int(h * 0.20))
    stable_rows = max(8, int(h * 0.04))
    candidates = []
    for x1 in range(max_x):
        for width in (1, 2, 3):
            x2 = x1 + width - 1
            if x2 >= max_x:
                continue
            row_has = mask[:, x1:x2 + 1].any(axis=1)
            local_x1 = max(0, x1 - 3)
            local_x2 = min(max_x, x2 + 4)
            local_amber_count = mask[:, local_x1:local_x2].sum(axis=1)
            for raw_y1, gy2 in contiguous_runs(row_has):
                gy1 = raw_y1
                for y in range(raw_y1, gy2 - stable_rows + 2):
                    if np.all(row_has[y:y + stable_rows]) and np.all(
                        local_amber_count[y:y + stable_rows] <= width + 2
                    ):
                        gy1 = y
                        break
                guide_h = gy2 - gy1 + 1
                if guide_h < min_height:
                    continue
                pixels = int(mask[gy1:gy2 + 1, x1:x2 + 1].sum())
                density = pixels / (guide_h * width)
                if density >= 0.80:
                    candidates.append((guide_h, density, pixels, width, -x1, x1, gy1, x2, gy2))

    if not candidates:
        return None
    *_, x1, gy1, x2, gy2 = max(candidates)

    initial_box = place_textbox_fixed_offset((x1, gy1, x2, gy2), w, h)
    rgb_255 = arr.astype(int)
    channel_max = rgb_255.max(axis=2)
    channel_min = rgb_255.min(axis=2)
    white_text = (channel_min >= 165) & ((channel_max - channel_min) <= 45)
    text_counts = white_text[:, x2 + 8:int(w * 0.55)].sum(axis=1)
    active_rows = text_counts >= 8
    for text_y1, text_y2 in contiguous_runs(active_rows):
        if text_y2 - text_y1 + 1 >= 3 and text_y1 <= initial_box[1] <= text_y2:
            gy1 = text_y1 + (gy1 - initial_box[1])
            break
    return x1, gy1, x2, gy2


def find_cyan_guide_inverted(arr_orig: np.ndarray, y_start: int | None = None):
    """Deteksi red guide via invert (255 - RGB): red(200,30,30) -> cyan(55,225,225).
    
    Cyan mask formula: r_inv < 51, g_inv > 108, b_inv > 140, g_inv > r_inv * 1.40, b_inv > r_inv * 1.40.
    Menggunakan algoritma Local Column Peak Prominence (sama dengan red guide) dan NO TOP CROP.
    """
    h, w = arr_orig.shape[:2]
    if y_start is None:
        y_start = 0

    arr_inv = 255 - arr_orig.astype(np.int16)
    arr_inv = np.clip(arr_inv, 0, 255).astype(np.uint8)

    r_inv = arr_inv[:,:,0].astype(float)
    g_inv = arr_inv[:,:,1].astype(float)
    b_inv = arr_inv[:,:,2].astype(float)

    cyan_mask = (
        (r_inv < 51) & (g_inv > 108) & (b_inv > 140)
        & (g_inv > r_inv * 1.40) & (b_inv > r_inv * 1.40)
    )
    if y_start > 0:
        cyan_mask[:y_start, :] = False

    max_x_search = int(max(48, w * 0.35))
    cyan_mask[:, max_x_search:] = False

    counts = cyan_mask.astype(int).sum(axis=0)

    # ── SAME prominent check as red guide (gap check included) ──
    prominent_mask = np.zeros(w, dtype=bool)
    min_h = max(20, int(h * 0.065))

    for x in range(max_x_search):
        if counts[x] < min_h:
            continue
        w_start = max(0, x - 6)
        w_end = min(max_x_search, x + 7)
        neighbor_vals = [counts[nx] for nx in range(w_start, w_end) if abs(nx - x) >= 3 and counts[nx] > 0]
        local_bg = np.median(neighbor_vals) if neighbor_vals else 0
        if counts[x] >= local_bg + 20 or counts[x] >= local_bg * 1.35:
            left_bg = np.min([counts[nx] for nx in range(max(0, x-4), max(0, x-1))] or [0])
            right_bg = np.min([counts[nx] for nx in range(min(max_x_search, x+2), min(max_x_search, x+5))] or [0])
            if left_bg <= counts[x] * 0.60 or right_bg <= counts[x] * 0.60:
                prominent_mask[x] = True

    max_allowed_width = 2  # Strict 1-2px guide width requirement

    # Split wide runs at drop-off (count < peak * 0.35)
    def _split_wide_run(x1, x2):
        run_cols = list(range(x1, x2 + 1))
        if len(run_cols) <= max_allowed_width:
            return [(x1, x2)]
        peak_count = max(counts[x] for x in run_cols)
        threshold = peak_count * 0.35
        sub_runs = []
        sub_start = run_cols[0]
        for x in run_cols[1:]:
            if counts[x] < threshold:
                sub_runs.append((sub_start, x - 1))
                sub_start = x
        sub_runs.append((sub_start, run_cols[-1]))
        return [(sx1, sx2) for sx1, sx2 in sub_runs if sx2 - sx1 + 1 <= max_allowed_width]

    candidates = []
    for x1, x2 in contiguous_runs(prominent_mask):
        run_width = x2 - x1 + 1
        if run_width > max_allowed_width:
            sub_runs = _split_wide_run(x1, x2)
        else:
            sub_runs = [(x1, x2)]

        for sx1, sx2 in sub_runs:
            row_has = cyan_mask[:, sx1:sx2+1].sum(axis=1) > 0
            raw_runs = contiguous_runs(row_has)
            if not raw_runs:
                continue
            # Merge runs separated by small vertical gaps (<= 5 px) — same as red guide
            merged_runs = [list(raw_runs[0])]
            for ry1, ry2 in raw_runs[1:]:
                if ry1 - merged_runs[-1][1] <= 5:
                    merged_runs[-1][1] = ry2
                else:
                    merged_runs.append([ry1, ry2])

            for y1, y2 in merged_runs:
                guide_h = y2 - y1 + 1
                if guide_h < max(20, int(h * 0.045)):
                    continue
                score = int(cyan_mask[y1:y2+1, sx1:sx2+1].sum())
                candidates.append((guide_h, score, sx1, y1, sx2, y2))

    if not candidates:
        return None

    candidates.sort(key=lambda c: (c[2], -c[0], -c[1]))
    _, _, x1, y1, x2, y2 = candidates[0]
    return x1, y1, x2, y2


def find_custom1_hsv_guide(arr_orig: np.ndarray, y_start: int | None = None):
    """Custom1 HSV mask — target hue ~353° (red edge), high saturation & value.
    
    Formula: |hue - 353| ≤ 26°, sat ∈ [84,100], val ∈ [67,100].
    Uses same column peak prominence algorithm as red/cyan guides.
    """
    h, w = arr_orig.shape[:2]
    if y_start is None:
        y_start = 0

    img = Image.fromarray(arr_orig)
    hsv = img.convert('HSV')
    arr_hsv = np.array(hsv).astype(float)

    # PIL HSV is 0-255 for all channels — convert to standard ranges
    hue = (arr_hsv[:, :, 0] * 360.0 / 255.0)
    sat = (arr_hsv[:, :, 1] * 100.0 / 255.0)
    val = (arr_hsv[:, :, 2] * 100.0 / 255.0)

    # Circular hue distance from 353° (red edge)
    hue_diff = np.abs(hue - 353.0)
    hue_diff = np.where(hue_diff > 180.0, 360.0 - hue_diff, hue_diff)

    custom1_mask = (
        (hue_diff <= 26.0)
        & (sat >= 84.0) & (sat <= 100.0)
        & (val >= 67.0) & (val <= 100.0)
    )
    if y_start > 0:
        custom1_mask[:y_start, :] = False

    max_x_search = int(max(48, w * 0.35))
    custom1_mask[:, max_x_search:] = False

    counts = custom1_mask.astype(int).sum(axis=0)

    # Same prominent check as red/cyan guide
    prominent_mask = np.zeros(w, dtype=bool)
    min_h = max(20, int(h * 0.065))

    for x in range(max_x_search):
        if counts[x] < min_h:
            continue
        w_start = max(0, x - 6)
        w_end = min(max_x_search, x + 7)
        neighbor_vals = [counts[nx] for nx in range(w_start, w_end) if abs(nx - x) >= 3 and counts[nx] > 0]
        local_bg = np.median(neighbor_vals) if neighbor_vals else 0
        if counts[x] >= local_bg + 20 or counts[x] >= local_bg * 1.35:
            left_bg = np.min([counts[nx] for nx in range(max(0, x-4), max(0, x-1))] or [0])
            right_bg = np.min([counts[nx] for nx in range(min(max_x_search, x+2), min(max_x_search, x+5))] or [0])
            if left_bg <= counts[x] * 0.60 or right_bg <= counts[x] * 0.60:
                prominent_mask[x] = True

    # Custom1 detects colored AREAS (orange header), not thin lines — wider width allowed
    max_allowed_width = max(8, int(w * 0.035))

    def _split_wide_run(x1, x2):
        run_cols = list(range(x1, x2 + 1))
        if len(run_cols) <= max_allowed_width:
            return [(x1, x2)]
        peak_count = max(counts[x] for x in run_cols)
        threshold = peak_count * 0.35
        sub_runs = []
        sub_start = run_cols[0]
        for x in run_cols[1:]:
            if counts[x] < threshold:
                sub_runs.append((sub_start, x - 1))
                sub_start = x
        sub_runs.append((sub_start, run_cols[-1]))
        return [(sx1, sx2) for sx1, sx2 in sub_runs if sx2 - sx1 + 1 <= max_allowed_width]

    candidates = []
    for x1, x2 in contiguous_runs(prominent_mask):
        # Custom1 detects colored AREAS — no width limit, just group columns
        row_has = custom1_mask[:, x1:x2+1].sum(axis=1) > 0
        raw_runs = contiguous_runs(row_has)
        if not raw_runs:
            continue
        merged_runs = [list(raw_runs[0])]
        for ry1, ry2 in raw_runs[1:]:
            if ry1 - merged_runs[-1][1] <= 5:
                merged_runs[-1][1] = ry2
            else:
                merged_runs.append([ry1, ry2])

        for y1, y2 in merged_runs:
            guide_h = y2 - y1 + 1
            if guide_h < max(20, int(h * 0.045)):
                continue
            score = int(custom1_mask[y1:y2+1, x1:x2+1].sum())
            candidates.append((guide_h, score, x1, y1, x2, y2))

    if not candidates:
        return None

    candidates.sort(key=lambda c: (c[2], -c[0], -c[1]))
    _, _, x1, y1, x2, y2 = candidates[0]
    return x1, y1, x2, y2


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


def place_textbox_above_guide(guide: tuple[int, int, int, int], anchor_x: int,
                              w: int, h: int) -> tuple[int, int, int, int]:
    """Keep the standard box size, 2 px above the guide, aligned to OCR date X."""
    _, gy1, _, _ = guide
    box_h = int(h * BOX_HEIGHT_RATIO)
    box_w = int(w * BOX_WIDTH_RATIO)
    x1 = max(0, min(anchor_x, w - box_w))
    y2 = max(box_h, gy1 - 2)
    return x1, y2 - box_h, min(w, x1 + box_w), y2



def find_collage_custom_guide(arr: np.ndarray, y_start: int | None = None):
    """Deteksi guide khusus foto kolase menggunakan HSV Eyedropper mask.
    
    Formula mask:
    - hue_diff = |hue - 32.0| (dengan 360 wrap-around) <= 25.0°
    - sat in [26.0%, 86.0%]
    - val in [38.0%, 98.0%]
    """
    h, w = arr.shape[:2]
    if y_start is None:
        y_start = 0

    r = arr[:,:,0].astype(float)
    g = arr[:,:,1].astype(float)
    b = arr[:,:,2].astype(float)

    delta = r - np.minimum(g, b)
    safe_delta = np.where(delta > 0, delta, 1.0)
    max_c = np.maximum(np.maximum(r, g), b)
    
    # Calculate Hue
    hue = np.zeros_like(r)
    mask_r = (max_c == r) & (delta > 0)
    mask_g = (max_c == g) & (delta > 0)
    mask_b = (max_c == b) & (delta > 0)
    
    hue[mask_r] = ((g[mask_r] - b[mask_r]) / safe_delta[mask_r]) % 6
    hue[mask_g] = (b[mask_g] - r[mask_g]) / safe_delta[mask_g] + 2
    hue[mask_b] = (r[mask_b] - g[mask_b]) / safe_delta[mask_b] + 4
    hue = hue * 60.0
    hue = np.where(hue < 0, hue + 360.0, hue)
    
    sat = np.where(max_c > 0, (delta / max_c) * 100.0, 0.0)
    val = (max_c / 255.0) * 100.0
    
    hue_diff = np.abs(hue - 32.0)
    hue_diff = np.where(hue_diff > 180.0, 360.0 - hue_diff, hue_diff)
    
    custom_mask = (
        (hue_diff <= 25.0) &
        (sat >= 26.0) & (sat <= 86.0) &
        (val >= 38.0) & (val <= 98.0)
    )

    if y_start > 0:
        custom_mask[:y_start, :] = False

    max_x_search = int(max(48, w * 0.35))
    custom_mask[:, max_x_search:] = False

    counts = custom_mask.astype(int).sum(axis=0)

    prominent_mask = np.zeros(w, dtype=bool)
    min_h = max(20, int(h * 0.065))

    for x in range(max_x_search):
        if counts[x] < min_h:
            continue
        w_start = max(0, x - 6)
        w_end = min(max_x_search, x + 7)
        neighbor_vals = [counts[nx] for nx in range(w_start, w_end) if abs(nx - x) >= 3 and counts[nx] > 0]
        local_bg = np.median(neighbor_vals) if neighbor_vals else 0
        if counts[x] >= local_bg + 20 or counts[x] >= local_bg * 1.35:
            prominent_mask[x] = True

    max_allowed_width = max(8, int(w * 0.035))

    candidates = []
    for x1, x2 in contiguous_runs(prominent_mask):
        if x2 - x1 + 1 > max_allowed_width:
            continue
        row_has = custom_mask[:, x1:x2+1].sum(axis=1) > 0
        raw_runs = contiguous_runs(row_has)
        if not raw_runs:
            continue
        merged_runs = [list(raw_runs[0])]
        for ry1, ry2 in raw_runs[1:]:
            if ry1 - merged_runs[-1][1] <= 5:
                merged_runs[-1][1] = ry2
            else:
                merged_runs.append([ry1, ry2])

        for y1, y2 in merged_runs:
            guide_h = y2 - y1 + 1
            if guide_h < max(20, int(h * 0.045)):
                continue
            score = int(custom_mask[y1:y2+1, x1:x2+1].sum())
            candidates.append((guide_h, score, x1, y1, x2, y2))

    if not candidates:
        return None
    candidates.sort(key=lambda c: (c[2], -c[0], -c[1]))
    _, _, x1, y1, x2, y2 = candidates[0]
    return x1, y1, x2, y2


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


def find_old_date_by_ocr(arr: np.ndarray, w: int, h: int) -> tuple[int, int, int, int] | None:
    """Deteksi watermark tanggal putih dari PDF sumber 2026 via OCR.
    
    Format: 'Senin, Mei 25,2026:' atau 'Rabu, Nov 05 2025 07:00'
    Scan area: y > 35%, x < 70% gambar (area watermark di kiri-bawah).
    Mencoba 3 threshold (180/200/220) untuk menangani variasi kecerahan teks.
    Returns: (x1, y1, x2, y2) atau None jika tidak ditemukan.
    """
    from PIL import Image
    
    cy1 = int(h * 0.35)
    cx2 = int(w * 0.70)
    crop = arr[cy1:, :cx2]
    crop_img = Image.fromarray(crop).convert("L")
    
    # Regex: "Senin, Mei 25,2026:" atau "Senin, Nov 22 2025"
    DAY_PAT   = r"(?:Senin|Selasa|Rabu|Kamis|Jumat|Sabtu|Minggu)"
    MONTH_PAT = r"(?:Jan|Feb|Mar|Apr|Mei|Jun|Jul|Agu|Sep|Okt|Nov|Des)"
    DATE_RE   = re.compile(
        rf"({DAY_PAT})[,.]?\s*({MONTH_PAT})\s+\d{{1,2}}",
        re.IGNORECASE
    )
    
    cfg = "--psm 6 -l eng"
    all_candidates = []
    
    for threshold in [180, 200, 220]:
        th = crop_img.point(lambda p, t=threshold: 255 if p > t else 0)
        # Skip if almost no white pixels
        white_px = np.array(th).sum() // 255
        if white_px < 200:
            continue
        th_inv = th.point(lambda p: 255 - p)
        
        try:
            data = pytesseract.image_to_data(th_inv, config=cfg, output_type=pytesseract.Output.DICT)
        except Exception:
            continue
        
        n = len(data["text"])
        lines = {}
        for i in range(n):
            conf = int(data["conf"][i])
            if conf < 30:
                continue
            line_key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            if line_key not in lines:
                lines[line_key] = []
            lines[line_key].append(i)
        
        for line_key, indices in lines.items():
            line_text = " ".join(str(data["text"][i]) for i in indices if str(data["text"][i]).strip())
            m = DATE_RE.search(line_text)
            if not m:
                continue
            
            valid = [i for i in indices if str(data["text"][i]).strip()]
            if not valid:
                continue
            xs = [data["left"][i] for i in valid]
            ys = [data["top"][i] for i in valid]
            ws = [data["width"][i] for i in valid]
            hs = [data["height"][i] for i in valid]
            confs = [int(data["conf"][i]) for i in valid]
            avg_conf = sum(confs) / len(confs)
            
            x1 = min(xs)
            y1 = min(ys) + cy1
            x2 = max(x + wi for x, wi in zip(xs, ws))
            y2 = max(y + hi for y, hi in zip(ys, hs)) + cy1
            
            all_candidates.append((avg_conf, x1, y1, x2, y2))
    
    if not all_candidates:
        return None
    
    # Pilih candidate dengan confidence tertinggi
    all_candidates.sort(key=lambda c: c[0], reverse=True)
    best_conf, x1, y1, x2, y2 = all_candidates[0]

    box_h = y2 - y1
    pad_y = max(1, int(box_h * 0.3))
    return (x1, y1 - pad_y, x2, y2 + pad_y)


def find_old_date_anchor(arr: np.ndarray) -> tuple[int, int, int, int] | None:
    """Find one Indonesian day/month word, then expand it to its white date row."""
    h, w = arr.shape[:2]
    crop_y1, crop_x2, scale = int(h * 0.35), int(w * 0.70), 4
    gray = Image.fromarray(arr[crop_y1:, :crop_x2]).convert("L")
    scaled = gray.resize((crop_x2 * scale, (h - crop_y1) * scale))
    keywords = re.compile(
        r"^(senin|selasa|rabu|kamis|jumat|sabtu|minggu|jan|feb|mar|apr|mei|jun|jul|agu|sep|okt|nov|des)[,.:]*$",
        re.IGNORECASE,
    )
    matches = []
    for threshold in (180, 200):
        binary = scaled.point(lambda value, limit=threshold: 0 if value > limit else 255)
        try:
            data = pytesseract.image_to_data(
                binary, config="--psm 11 -l eng", output_type=pytesseract.Output.DICT
            )
        except Exception:
            continue
        for i, text in enumerate(data["text"]):
            confidence = float(data["conf"][i])
            if confidence < 30 or not keywords.match(str(text).strip()):
                continue
            x1 = int(data["left"][i] / scale)
            y1 = int(data["top"][i] / scale) + crop_y1
            x2 = int((data["left"][i] + data["width"][i]) / scale)
            y2 = int((data["top"][i] + data["height"][i]) / scale) + crop_y1
            matches.append((confidence, x1, y1, x2, y2))
    if not matches:
        return None

    _, x1, y1, x2, y2 = max(matches)
    rgb = arr.astype(int)
    channel_max = rgb.max(axis=2)
    channel_min = rgb.min(axis=2)
    white = (channel_min >= 165) & ((channel_max - channel_min) <= 45)
    local_x1 = max(0, x1 - 3)
    local_x2 = min(w, x2 + 4)
    row_counts = white[:, local_x1:local_x2].sum(axis=1)
    local_y1 = max(0, y1 - 4)
    local_y2 = min(h, y2 + 5)
    for local_run_y1, local_run_y2 in contiguous_runs(row_counts[local_y1:local_y2] >= 3):
        run_y1 = local_y1 + local_run_y1
        run_y2 = local_y1 + local_run_y2
        if run_y2 - run_y1 + 1 >= 3 and run_y1 <= y2 and run_y2 >= y1:
            return max(0, x1 - 3), run_y1, int(w * 0.55), run_y2 + 1
    return x1, y1, x2, y2


def find_old_date_anchor_near_box(arr: np.ndarray, box: tuple[int, int, int, int]):
    """Read a small date strip near one guide candidate when global OCR fails."""
    h, w = arr.shape[:2]
    crop_x1 = max(0, box[0] - 5)
    crop_x2 = min(w, int(w * 0.63))
    crop_y1 = max(0, box[1] - 8)
    crop_y2 = min(h, box[3] + 8)
    scale = 8
    gray = Image.fromarray(arr[crop_y1:crop_y2, crop_x1:crop_x2]).convert("L")
    binary = gray.resize((gray.width * scale, gray.height * scale)).point(
        lambda value: 255 if value >= 180 else 0
    )
    keywords = re.compile(
        r"(senin|selasa|rabu|kamis|jumat|sabtu|minggu|jan|feb|mar|apr|mei|jun|jul|agu|sep|okt|nov|des|20\d{2})",
        re.IGNORECASE,
    )
    try:
        data = pytesseract.image_to_data(
            binary, config="--psm 13 -l eng", output_type=pytesseract.Output.DICT
        )
    except Exception:
        return None
    matches = []
    for i, text in enumerate(data["text"]):
        confidence = float(data["conf"][i])
        if confidence < 40 or not keywords.search(str(text)):
            continue
        x1 = int(data["left"][i] / scale) + crop_x1
        y1 = int(data["top"][i] / scale) + crop_y1
        x2 = int((data["left"][i] + data["width"][i]) / scale) + crop_x1
        y2 = int((data["top"][i] + data["height"][i]) / scale) + crop_y1
        matches.append((confidence, x1, y1, x2, y2))
    if not matches:
        return None
    _, x1, y1, x2, y2 = max(matches)
    return x1, y1, x2, y2


def find_old_date_anchor_near_guide(arr: np.ndarray,
                                    guide: tuple[int, int, int, int]):
    """Find an abbreviated day token within 42 px above the same photo's guide."""
    h, w = arr.shape[:2]
    _, gy1, _, _ = guide
    crop_x1, crop_x2 = 0, min(w, int(w * 0.70))
    crop_y1, crop_y2 = max(0, gy1 - 42), min(h, gy1 + 2)
    scale = 10
    gray = Image.fromarray(arr[crop_y1:crop_y2, crop_x1:crop_x2]).convert("L")
    binary = gray.resize(
        (gray.width * scale, gray.height * scale), Image.Resampling.LANCZOS
    ).point(lambda value: 255 if value >= 140 else 0)
    try:
        data = pytesseract.image_to_data(
            binary, config="--psm 6 -l eng", output_type=pytesseract.Output.DICT
        )
    except Exception:
        return None

    day_token = re.compile(
        r"^(sen(?:in)?|sel(?:asa)?|rab(?:u)?|kam(?:is)?|jum(?:at)?|sab(?:tu)?|min(?:ggu)?)[,.:]*$",
        re.IGNORECASE,
    )
    matches = []
    for i, text in enumerate(data["text"]):
        confidence = float(data["conf"][i])
        if confidence < 40 or not day_token.match(str(text).strip()):
            continue
        x1 = int(data["left"][i] / scale) + crop_x1
        y1 = int(data["top"][i] / scale) + crop_y1
        x2 = int((data["left"][i] + data["width"][i]) / scale) + crop_x1
        y2 = int((data["top"][i] + data["height"][i]) / scale) + crop_y1
        if y2 <= gy1 + 2:
            matches.append((confidence, x1, y1, x2, y2))
    if not matches:
        return None
    _, x1, y1, x2, y2 = max(matches)
    return x1, y1, x2, y2


def find_complete_date_anchor(arr: np.ndarray,
                              guides: list[tuple[int, int, int, int]]):
    """Find a complete Indonesian date row and rank it by OCR and guide proximity."""
    h, w = arr.shape[:2]
    crop_y1, crop_x2, scale = int(h * 0.32), int(w * 0.75), 6
    gray = Image.fromarray(arr[crop_y1:, :crop_x2]).convert("L")
    scaled = gray.resize((gray.width * scale, gray.height * scale), Image.Resampling.LANCZOS)
    day_re = re.compile(r"^(sen(?:in)?|sel(?:asa)?|rab(?:u)?|kam(?:is)?|jum(?:at)?|sab(?:tu)?|min(?:ggu)?)[,.:]*$", re.I)
    month_re = re.compile(r"^(jan|feb|mar|apr|mei|jun|jul|agu|sep|okt|nov|des)[,.:]*$", re.I)
    number_re = re.compile(r"^(?:[0-2]?\d|3[01])[,.:]*$")
    year_re = re.compile(r"^20\d{2}[,.:]*$")
    candidates = {}

    for threshold, psm in ((140, 6), (180, 11)):
        binary = scaled.point(lambda value, limit=threshold: 255 if value >= limit else 0)
        try:
            data = pytesseract.image_to_data(
                binary, config=f"--psm {psm} -l eng", output_type=pytesseract.Output.DICT
            )
        except Exception:
            continue
        lines = {}
        for i, raw in enumerate(data["text"]):
            text = str(raw).strip()
            try:
                confidence = float(data["conf"][i])
            except (TypeError, ValueError):
                continue
            if text and confidence >= 25:
                key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
                lines.setdefault(key, []).append((i, text, confidence))

        for tokens in lines.values():
            days = [token for token in tokens if day_re.match(token[1])]
            months = [token for token in tokens if month_re.match(token[1])]
            numbers = [token for token in tokens if number_re.match(token[1])]
            years = [token for token in tokens if year_re.match(token[1])]
            if not months or not ((days and numbers) or (numbers and years)):
                continue
            relevant = days + months + numbers + years
            anchor_token = min(days or numbers + months, key=lambda token: data["left"][token[0]])
            i = anchor_token[0]
            x1 = int(data["left"][i] / scale)
            y1 = min(int(data["top"][item[0]] / scale) for item in relevant) + crop_y1
            x2 = max(int((data["left"][item[0]] + data["width"][item[0]]) / scale) for item in relevant)
            y2 = max(int((data["top"][item[0]] + data["height"][item[0]]) / scale) for item in relevant) + crop_y1
            confidence = sum(item[2] for item in relevant) / len(relevant)
            evidence = 25 * bool(days) + 25 * bool(months) + 15 * bool(numbers) + 15 * bool(years)
            distance = min((min(abs(y1 - guide[1]), abs(y2 - guide[1])) for guide in guides), default=20)
            score = confidence + evidence - min(distance, 60) * 0.5
            key = (x1 // 3, y1 // 3)
            candidate = (score, (x1, y1, x2, y2))
            if key not in candidates or score > candidates[key][0]:
                candidates[key] = candidate

    ranked = sorted(candidates.values(), reverse=True)
    if not ranked or ranked[0][0] < 75:
        return None, ranked
    if len(ranked) > 1:
        first, second = ranked[0][1], ranked[1][1]
        same_row = abs(first[0] - second[0]) <= 4 and abs(first[1] - second[1]) <= 4
        if not same_row and ranked[0][0] - ranked[1][0] < 8:
            return None, ranked
    return ranked[0][1], ranked


def place_textbox_on_date_anchor(anchor: tuple[int, int, int, int],
                                  w: int, h: int) -> tuple[int, int, int, int]:
    """Place the standard textbox from the detected day token's top-left."""
    x1, y1, _, _ = anchor
    box_w = int(w * BOX_WIDTH_RATIO)
    box_h = int(h * BOX_HEIGHT_RATIO)
    x1 = max(0, min(x1, w - box_w))
    y1 = max(0, min(y1, h - box_h))
    return x1, y1, x1 + box_w, y1 + box_h


def select_amber_textbox(arr: np.ndarray, w: int, h: int,
                           allow_above_layout: bool = False):
    """Select guide and above/side layout from this photo; OCR judges ambiguity."""
    guide_a = find_amber_guide_initial(arr)
    guide_b = find_amber_guide_v4(arr)
    if guide_a is None and guide_b is None:
        return None
    if guide_a is None or guide_b is None:
        guide = guide_a or guide_b
        label = "initial" if guide_a else "v4"
        return place_textbox_fixed_offset(guide, w, h), f"stage_amber_dual_{label}_only"

    box_a = place_textbox_fixed_offset(guide_a, w, h)
    box_b = place_textbox_fixed_offset(guide_b, w, h)
    if allow_above_layout:
        near_guide_anchor = find_old_date_anchor_near_guide(arr, guide_a)
        if near_guide_anchor is not None:
            return (
                place_textbox_on_date_anchor(near_guide_anchor, w, h),
                "stage_amber_date_near_guide_above_initial",
            )

    anchor = find_old_date_anchor(arr)
    if anchor is not None:
        # OCR chooses the per-photo layout; category only enables the above option.
        guide, label = min(
            ((guide_a, "initial"), (guide_b, "v4")),
            key=lambda item: abs(item[0][1] - anchor[3]),
        )
        if allow_above_layout and anchor[1] <= guide[1]:
            return (
                place_textbox_above_guide(guide, anchor[0], w, h),
                f"stage_amber_dual_ocr_above_{label}",
            )

        def distance(box):
            if box[1] <= anchor[1] and box[3] >= anchor[3]:
                return 0
            return max(box[1] - anchor[1], anchor[3] - box[3], 0)

        winner, label = min(((box_a, "initial"), (box_b, "v4")), key=lambda item: distance(item[0]))
        shift = anchor[1] - winner[1] if anchor[1] < winner[1] else max(0, anchor[3] - winner[3])
        if abs(shift) > 10:
            return winner, "stage_amber_manual_review"
        if shift:
            winner = (winner[0], winner[1] + shift, winner[2], winner[3] + shift)
        return winner, f"stage_amber_dual_ocr_side_{label}"

    if abs(guide_a[1] - guide_b[1]) <= 2:
        return box_a, "stage_amber_dual_agree"

    local_anchor_a = find_old_date_anchor_near_box(arr, box_a)
    local_anchor_b = find_old_date_anchor_near_box(arr, box_b)
    if local_anchor_a is not None and local_anchor_b is None:
        return box_a, "stage_amber_dual_local_ocr_side_initial"
    if local_anchor_b is not None and local_anchor_a is None:
        return box_b, "stage_amber_dual_local_ocr_side_v4"
    if local_anchor_a is not None and local_anchor_b is not None:
        def local_distance(item):
            box, local_anchor = item
            return abs((box[1] + box[3]) - (local_anchor[1] + local_anchor[3]))

        winner, label = min(
            ((box_a, local_anchor_a, "initial"), (box_b, local_anchor_b, "v4")),
            key=lambda item: local_distance((item[0], item[1])),
        )[::2]
        return winner, f"stage_amber_dual_local_ocr_side_{label}"

    # No date token means no safe basis for choosing widely different guide endpoints.
    return box_a, "stage_amber_manual_review"


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
                    is_collage: bool = False, allow_above_layout: bool = False):
    """Detect guides from this photo; use folder consensus only to reject outliers."""
    if y_override is not None:
        box_h = int(h * BOX_HEIGHT_RATIO)
        y1 = max(0, y_override - box_h // 2)
        y2 = min(h, y1 + box_h)
        x1 = int(w * 0.047)
        x2 = int(w * 0.49)
        return (x1, y1, x2, y2), "stage_0_override"

    candidates = []
    if is_collage:
        guide = find_collage_custom_guide(arr_orig, y_start=0)
        if guide is not None:
            candidates.append(("stage_1c_guide_original", guide))

    if allow_above_layout:
        ptls_guides = [
            guide for guide in (
                find_amber_guide_initial(arr_orig),
                find_amber_guide_v4(arr_orig),
                find_red_guide(arr_orig, y_start=0),
            ) if guide is not None
        ]
        date_anchor, _ = find_complete_date_anchor(arr_orig, ptls_guides)
        if date_anchor is not None:
            return place_textbox_on_date_anchor(date_anchor, w, h), "stage_ptls_date_complete"

    amber_result = select_amber_textbox(
        arr_orig, w, h, allow_above_layout=allow_above_layout
    )
    if amber_result is not None:
        return amber_result

    if allow_above_layout:
        return get_text_box(w, h), "stage_ptls_manual_review"

    guide = find_red_guide(arr_orig, y_start=0)
    if guide is not None:
        candidates.append(("stage_1c_guide_original", guide))

    y_bot = int(h * 0.54)
    zone_arr = arr_orig[y_bot:, :]

    guide = find_cyan_guide_inverted(zone_arr, y_start=0)
    if guide is not None:
        guide = (guide[0], y_bot + guide[1], guide[2], y_bot + guide[3])
        candidates.append(("stage_2_invert_guide", guide))

    guide = find_custom1_hsv_guide(zone_arr, y_start=0)
    if guide is not None:
        guide = (guide[0], y_bot + guide[1], guide[2], y_bot + guide[3])
        candidates.append(("stage_3_custom1_hsv", guide))

    if candidates:
        # Consensus validates candidates; selected coordinates still come from this photo.
        if consensus_gy1 is not None:
            stage, guide = min(candidates, key=lambda item: abs(item[1][1] - consensus_gy1))
        else:
            stage, guide = candidates[0]
        return place_textbox_fixed_offset(guide, w, h), stage

    ocr_box = find_old_date_by_ocr(zone_arr, w, h)
    if ocr_box is not None:
        return ocr_box, "stage_ocr_old_date"

    return get_text_box(w, h), "stage_fallback"


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




def find_guide_by_mask_direct(arr_orig: np.ndarray, mask_type: str = "red"):
    """Pixel Inspector Direct Mask Guide Finder (No strict bounding box / flank rules)."""
    h, w = arr_orig.shape[:2]
    max_x = int(w * 0.35)

    if mask_type == "cyan":
        arr_inv = np.clip(255 - arr_orig.astype(np.int16), 0, 255).astype(np.uint8)
        r = arr_inv[:, :, 0].astype(float)
        g = arr_inv[:, :, 1].astype(float)
        b = arr_inv[:, :, 2].astype(float)
        mask = (r < 65) & (g > 90) & (b > 120) & (g > r * 1.3) & (b > r * 1.3)
    elif mask_type == "custom":
        r = arr_orig[:, :, 0].astype(float)
        g = arr_orig[:, :, 1].astype(float)
        b = arr_orig[:, :, 2].astype(float)
        mask = (r > 120) & (r > g * 1.3) & (r > b * 1.3) & (g < 210) & (b < 180)
    else:  # red mask
        r = arr_orig[:, :, 0].astype(float)
        g = arr_orig[:, :, 1].astype(float)
        b = arr_orig[:, :, 2].astype(float)
        mask = (r > 140) & (r > g * 1.4) & (r > b * 1.4) & (g < 195) & (b < 165)

    mask[:, max_x:] = False

    counts = mask.astype(int).sum(axis=0)
    if counts.max() < 10:
        return None

    best_x = int(np.argmax(counts))
    col_mask = mask[:, max(0, best_x - 1):min(w, best_x + 2)].any(axis=1)
    y_indices = np.where(col_mask)[0]
    if len(y_indices) < 10:
        return None

    y1, y2 = int(y_indices[0]), int(y_indices[-1])
    return (best_x, y1, best_x, y2)


def _detect_guideline_for_label(arr: np.ndarray, w: int, h: int, is_collage: bool = False):
    """Return the actual pixel guideline used for YOLO capture, if present."""
    if is_collage:
        guide = find_collage_custom_guide(arr, y_start=0)
        if guide is not None:
            return tuple(map(int, guide))
    guide = find_red_guide(arr, y_start=0)
    if guide is not None:
        return tuple(map(int, guide))
    y_bot = int(h * 0.54)
    guide = find_cyan_guide_inverted(arr[y_bot:, :], y_start=0)
    if guide is not None:
        return int(guide[0]), y_bot + int(guide[1]), int(guide[2]), y_bot + int(guide[3])
    guide = find_custom1_hsv_guide(arr[y_bot:, :], y_start=0)
    if guide is not None:
        return int(guide[0]), y_bot + int(guide[1]), int(guide[2]), y_bot + int(guide[3])
    return None


def _write_yolo_label(image_path: Path, image_size: tuple[int, int], guide):
    """Write one class-0 YOLO label beside the source image."""
    label_path = image_path.with_suffix(".txt")
    if guide is None:
        if label_path.exists():
            label_path.unlink()
        return
    width, height = image_size
    x1, y1, x2, y2 = guide
    x1 = max(0, min(int(x1), width))
    y1 = max(0, min(int(y1), height))
    x2 = max(x1, min(int(x2), width))
    y2 = max(y1, min(int(y2), height))
    if x2 <= x1 or y2 <= y1:
        if label_path.exists():
            label_path.unlink()
        return
    label = f"0 {(x1 + x2) / 2 / width:.6f} {(y1 + y2) / 2 / height:.6f} {(x2 - x1) / width:.6f} {(y2 - y1) / height:.6f}\n"
    label_path.write_text(label, encoding="utf-8")


# ─── Process Single Image ───
def process_image(image_path: Path, output_path: Path, timemark_text: str, y_override: int | None = None, x_override: int | None = None, schedule_lookup=None, asset_key=None, consensus_gy1: int | None = None, is_collage: bool = False, mask_mode: str | None = None) -> str:
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
    _write_yolo_label(image_path, (w, h), _detect_guideline_for_label(arr_orig, w, h, is_collage))

    # Always detect the original position first so a user override never replaces it.
    allow_above_layout = bool(asset_key and len(asset_key) > 1 and asset_key[1] == "PTLS")
    initial_box, initial_stage = locate_date_box(
        arr_orig, w, h,
        consensus_gy1=consensus_gy1,
        is_collage=is_collage,
        allow_above_layout=allow_above_layout,
    )

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
    elif mask_mode is not None:
        guide = find_guide_by_mask_direct(arr_orig, mask_mode)
        if guide is not None:
            box = place_textbox_fixed_offset(guide, w, h)
            stage = f"stage_pixel_inspector_{mask_mode}"
        else:
            box, stage = initial_box, initial_stage
    else:
        box, stage = initial_box, initial_stage

    detector_meta = {
        "stage": initial_stage,
        "textboxBox": list(initial_box),
        "imageSize": [w, h],
        "detectedAt": datetime.now().isoformat(timespec="seconds")
    }

    # Ambiguous detection keeps source untouched and emits no output.
    if stage.endswith("manual_review"):
        if output_path.exists():
            output_path.unlink()
        return stage

    # ── Fallback: no date detected → copy as-is, no edit (only for non-cropped photos) ──
    if stage == "stage_fallback" and not is_collage and actual_input_path == image_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(actual_input_path, output_path)
        if y_override is not None or x_override is not None:
            output_path.with_suffix(output_path.suffix + ".detector.json").write_text(json.dumps(detector_meta), encoding="utf-8")
        # Flag file: per-photo marker for merge step
        flag_path = output_path.with_suffix(output_path.suffix + ".unedited")
        flag_path.write_text("")
        return "stage_fallback_skipped"

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
    unedited_flag = output_path.with_suffix(output_path.suffix + ".unedited")
    if unedited_flag.exists():
        unedited_flag.unlink()
    if y_override is not None or x_override is not None:
        output_path.with_suffix(output_path.suffix + ".detector.json").write_text(json.dumps(detector_meta), encoding="utf-8")

    return stage


def _collect_folder_consensus(input_dir: Path, all_jpgs: list[Path]) -> dict[tuple[str, str, str], int]:
    from collections import defaultdict
    folder_guides = defaultdict(list)

    for src in all_jpgs:
        rel = src.relative_to(input_dir)
        fkey = _folder_key_from_path(rel, input_dir)
        if not fkey:
            continue
        try:
            img = Image.open(src).convert('RGB')
            arr = np.array(img)
            guide = find_red_guide(arr)
            if guide:
                gx1, gy1, gx2, gy2 = guide
                folder_guides[fkey].append(gy1)
        except Exception:
            pass

    consensus = {}
    for fkey, gy1s in folder_guides.items():
        if len(gy1s) >= 2:
            gy1s.sort()
            median = gy1s[len(gy1s) // 2]
            inliers = [g for g in gy1s if abs(g - median) <= 10]
            if len(inliers) >= 2:
                consensus[fkey] = inliers[len(inliers) // 2]
    return consensus


def main():
    parser = argparse.ArgumentParser(description="Edit timemark on photos (Fixed-offset + Folder Consensus)")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Input photos folder")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output photos folder")
    parser.add_argument("--date", type=str, help="Global date text (e.g. 'Sabtu, Apr 29 2026 08:00')")
    parser.add_argument("--schedule", type=Path, default=DEFAULT_SCHEDULE, help="schedule.json for per-photo timestamps")
    parser.add_argument("--y-override", type=int, help="Force Y position for textbox")
    parser.add_argument("--x-override", type=int, help="Force X position for textbox")
    parser.add_argument("--single-out", type=Path, help="Force specific single output file path")
    parser.add_argument("--clear-output", action="store_true", help="Clear output folder first")
    parser.add_argument("--tim-filter", type=int, help="Process only schedule entries for this Tim number")
    parser.add_argument("--red-mask", action="store_true", help="Run with Red Mask HSV priority")
    parser.add_argument("--cyan-mask", action="store_true", help="Run with Cyan Mask HSV priority")
    parser.add_argument("--custom-mask", action="store_true", help="Run with Custom Mask HSV priority")
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

    cropped_collages_set = load_cropped_collages_manifest(logs_dir="logs")
    if cropped_collages_set:
        print(f"[INFO] Loaded collage manifest ({len(cropped_collages_set)} cropped collage photos registered)")
    folder_consensus = _collect_folder_consensus(input_dir, all_jpgs) if input_dir.is_dir() else {}

    ok = 0
    failed = 0
    skipped = 0
    stage_counts = {
        "stage_0_override": 0,
        "stage_1c_guide_original": 0,
        "stage_2_invert_guide": 0,
        "stage_3_custom1_hsv": 0,
        "stage_1c_guide_consensus": 0,
        "stage_ocr_old_date": 0,
        "stage_fallback": 0,
        "stage_fallback_skipped": 0
    }
    stage_details = []
    failed_files = []
    missing_dates = []
    unedited_files = []  # Track unedited photos for Excel
    tim_mapping = {}  # photo_rel_path -> tim_n

    current_asset_folder = None
    asset_folder_count = 0

    for src in all_jpgs:
        src_resolved = src.resolve()
        parts = src_resolved.parts
        if "03_photos_export" in parts:
            idx = parts.index("03_photos_export")
            rel = Path(*parts[idx+1:])
        elif "03_photos_cropped_temp" in parts:
            idx = parts.index("03_photos_cropped_temp")
            rel = Path(*parts[idx+1:])
        else:
            try:
                rel = src.relative_to(DEFAULT_INPUT)
            except ValueError:
                try:
                    rel = src.relative_to(DEFAULT_INPUT.resolve())
                except ValueError:
                    rel = src.relative_to(input_dir) if input_dir.is_dir() else Path(src.name)
        parts = rel.parts
        # Flat structure: [BTP/]category/identifier/photo.jpg
        btp_shift = 1 if parts and parts[0].startswith("BTP") else 0
        if len(parts) < 3 + btp_shift:
            failed_files.append({
                "file": str(rel),
                "asset_type": "",
                "detail": "",
                "photo": "",
                "reason": "invalid_asset_path; expected BTP/category/identifier/photo.jpg",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
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
        manual_meta = _read_manual_meta(dst_dir, photo_name)
        photo_y_override = args.y_override
        photo_x_override = args.x_override
        if manual_meta:
            photo_y_override = manual_meta.get("yPos", photo_y_override)
            photo_x_override = manual_meta.get("xPos", photo_x_override)

        fkey = _folder_key_from_path(rel, input_dir)
        consensus_gy1 = folder_consensus.get(fkey) if fkey else None

        asset_folder_key = (btp, category, identifier, tim_n)
        if asset_folder_key != current_asset_folder:
            if current_asset_folder is not None:
                print(f"  └── [OK] Folder selesai diproses\n", flush=True)
            current_asset_folder = asset_folder_key
            asset_folder_count += 1
            print(f"[{asset_folder_count}] 📁 {btp}/{category}/{identifier} (Tim {tim_n})", flush=True)
            print(f"  ├── Target Timemark : {timemark_text}", flush=True)

        is_coll = str(rel).replace('\\', '/').lower() in cropped_collages_set
        try:
            mask_mode = "red" if args.red_mask else "cyan" if args.cyan_mask else "custom" if args.custom_mask else None
            stage = process_image(src, dst, timemark_text, photo_y_override, photo_x_override, schedule_lookup, asset_key, consensus_gy1, is_collage=is_coll, mask_mode=mask_mode)
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
            if stage == "stage_fallback_skipped":
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
            print(f"  │   ├── {photo_name} -> [{stage}] Watermark diaplikasikan", flush=True)
            print(json.dumps({
                "type": "stage",
                "file": str(rel),
                "stage": stage,
                "asset_type": category,
                "detail": identifier,
                "photo": photo_name
            }), flush=True)
        except Exception as e:
            print(f"  │   ├── ❌ [ERROR] {photo_name} gagal: {e}", flush=True)
            failed += 1
            failed_files.append({
                "file": str(rel),
                "asset_type": category,
                "detail": identifier,
                "photo": photo_name,
                "reason": str(e),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

    if current_asset_folder is not None:
        print(f"  └── [OK] Folder selesai diproses\n", flush=True)



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
            ws.cell(row=row_idx, column=5, value=item.get("stage", "stage_fallback_skipped"))
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
