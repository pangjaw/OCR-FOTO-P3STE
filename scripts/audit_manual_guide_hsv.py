from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PAIR_FILE = ROOT / "logs/manual_pair_audit/edited_ground_truth_pairs.json"
OUT = ROOT / "logs/manual_guide_hsv_audit"
BOX_H_RATIO = 0.053
X_OFFSET = 6
Y_OFFSET = 0.018


def stats(values: np.ndarray) -> dict:
    values = values.astype(float).ravel()
    return {"count": int(values.size), **{f"p{p}": round(float(np.percentile(values, p)), 2) for p in (5, 25, 50, 75, 95)}} if values.size else {"count": 0}


def color_label(hue: np.ndarray, sat: np.ndarray, val: np.ndarray) -> str:
    h, s, v = float(np.median(hue)), float(np.median(sat)), float(np.median(val))
    if s < 35 and v > 150:
        return "white"
    if h >= 170 or h < 5:
        return "red"
    if h < 18:
        return "orange"
    return "yellow"


def extract(row: dict) -> dict | None:
    source = ROOT / row["source"]
    image = cv2.imread(str(source), cv2.IMREAD_COLOR)
    if image is None:
        return None
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, w = hsv.shape[:2]
    box_h = max(1, int(round(h * BOX_H_RATIO)))
    x_text = int(row["xPos"])
    y_text = int(row["yPos"])
    expected_x2 = x_text - X_OFFSET
    expected_y1 = int(round(y_text + box_h / 2 - h * Y_OFFSET))
    x1 = max(0, expected_x2 - 3)
    x2 = min(w - 1, expected_x2 + 3)
    y1 = max(0, expected_y1 - 12)
    y2 = min(h - 1, expected_y1 + 24)
    roi = hsv[y1:y2 + 1, x1:x2 + 1]
    pixels = roi.reshape(-1, 3)
    warm = (((pixels[:, 0] <= 45) | (pixels[:, 0] >= 170)) & (pixels[:, 1] >= 25) & (pixels[:, 2] >= 35))
    guide_pixels = pixels[warm]
    if guide_pixels.size == 0:
        guide_pixels = pixels
    return {
        "status": "measured",
        "source": row["source"],
        "valid_frame": row["valid_frame"],
        "asset_folder": row["asset_folder"],
        "frame": row["frame"],
        "xPos": x_text,
        "yPos": y_text,
        "estimated_guide_bbox": [x1, y1, x2, y2],
        "estimated_guide_x": expected_x2,
        "estimated_guide_y": expected_y1,
        "color": color_label(guide_pixels[:, 0], guide_pixels[:, 1], guide_pixels[:, 2]),
        "hue": stats(guide_pixels[:, 0]),
        "saturation": stats(guide_pixels[:, 1]),
        "value": stats(guide_pixels[:, 2]),
        "warm_fraction": round(float(warm.mean()), 4),
        "mean_rgb": [round(float(v), 2) for v in cv2.cvtColor(roi, cv2.COLOR_HSV2RGB).reshape(-1, 3).mean(axis=0)],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    payload = json.loads(PAIR_FILE.read_text(encoding="utf-8"))
    rows = [row for row in payload["rows"] if row.get("status") == "paired" and row.get("same_size")]
    measured = [item for row in rows if (item := extract(row)) is not None]
    color_counts = Counter(item["color"] for item in measured)
    by_color = defaultdict(list)
    for item in measured:
        by_color[item["color"]].append(item)
    summary = {
        color: {"count": len(items), "hue_p5_p50_p95": [round(float(np.median([x["hue"][f"p{p}"] for x in items])), 2) for p in (5, 50, 95)], "sat_p5_p50_p95": [round(float(np.median([x["saturation"][f"p{p}"] for x in items])), 2) for p in (5, 50, 95)], "value_p5_p50_p95": [round(float(np.median([x["value"][f"p{p}"] for x in items])), 2) for p in (5, 50, 95)]} for color, items in sorted(by_color.items())
    }
    result = {"pair_input": str(PAIR_FILE), "measured_count": len(measured), "color_counts": dict(color_counts), "summary": summary, "rows": measured}
    (OUT / "manual_guide_hsv.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = sorted({key for item in measured for key in item})
    with (OUT / "manual_guide_hsv.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(measured)
    print(json.dumps({"measured_count": len(measured), "color_counts": dict(color_counts), "summary": summary, "output": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
