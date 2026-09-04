from __future__ import annotations

import csv
import json
from pathlib import Path

import cv2
import numpy as np

from edit_timemark_canny_temp import find_orange_guide, find_red_guide

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    ROOT / "03_photos_export/BTP JAK/AXC/ZP 205 BOO-CLT/0.jpg",
    ROOT / "03_photos_export/BTP JAK/AXC/ZP 205 BOO-CLT/50.jpg",
    ROOT / "03_photos_export/BTP JAK/AXC/ZP 205 BOO-CLT/100.jpg",
    ROOT / "03_photos_export/BTP BD/WESEL/W11 MSG_19-09/0.jpg",
    ROOT / "03_photos_export/BTP BD/WESEL/W11 MSG_19-09/50.jpg",
    ROOT / "03_photos_export/BTP BD/WESEL/W11 MSG_19-09/100.jpg",
]


def describe(values: np.ndarray) -> dict:
    values = values.astype(float).ravel()
    if not values.size:
        return {"count": 0}
    return {"count": int(values.size), **{f"p{p}": round(float(np.percentile(values, p)), 2) for p in (1, 5, 25, 50, 75, 95, 99)}}


def row(path: Path) -> dict:
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        return {"file": str(path), "status": "unreadable"}
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    red = find_red_guide(rgb, 0)
    orange = find_orange_guide(rgb, 0)
    guide = red or orange
    source = "red_native" if red else ("orange_native" if orange else None)
    result = {"file": str(path.relative_to(ROOT)), "size": [int(rgb.shape[1]), int(rgb.shape[0])], "red_guide": red, "orange_guide": orange, "selected_source": source, "selected_guide": guide}
    if guide is None:
        return result
    x1, y1, x2, y2 = guide
    roi = hsv[max(0, y1):min(rgb.shape[0], y2 + 1), max(0, x1):min(rgb.shape[1], x2 + 1)]
    pixels = roi.reshape(-1, 3)
    result["hue"] = describe(pixels[:, 0])
    result["saturation"] = describe(pixels[:, 1])
    result["value"] = describe(pixels[:, 2])
    # Measure a narrow background ring beside the guide to estimate color contrast.
    bx1 = max(0, x1 - 4)
    bx2 = min(rgb.shape[1], x2 + 5)
    band = hsv[max(0, y1):min(rgb.shape[0], y2 + 1), bx1:bx2]
    result["roi_pixels"] = int(pixels.shape[0])
    result["mean_rgb"] = [round(float(v), 2) for v in rgb[max(0, y1):min(rgb.shape[0], y2 + 1), max(0, x1):min(rgb.shape[1], x2 + 1)].reshape(-1, 3).mean(axis=0)]
    result["mask_saturation_ge_25_fraction"] = round(float((pixels[:, 1] >= 25).mean()), 4)
    result["mask_saturation_ge_35_fraction"] = round(float((pixels[:, 1] >= 35).mean()), 4)
    result["mask_value_ge_55_fraction"] = round(float((pixels[:, 2] >= 55).mean()), 4)
    result["ring_hue"] = describe(band[:, :, 0])
    return result


if __name__ == "__main__":
    output = ROOT / "logs/guide_target_hsv_measurements.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = [row(path) for path in TARGETS]
    output.write_text(json.dumps({"method": "native detector guide ROI", "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = sorted({key for item in rows for key in item})
    with (ROOT / "logs/guide_target_hsv_measurements.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(rows, ensure_ascii=False, indent=2))
