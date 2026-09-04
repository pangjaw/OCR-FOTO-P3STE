#!/usr/bin/env python3
"""Compare OpenCV vertical-guide detection against manual meta.json positions."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import cv2
import numpy as np


IMAGE_EXTS = {".jpg", ".jpeg", ".png"}


def manual_records(edited_root: Path, export_root: Path):
    for meta_path in sorted(edited_root.rglob("meta.json")):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        rel_folder = meta_path.parent.relative_to(edited_root)
        # Edited output has Tim_N prefix; export input does not.
        source_folder = Path(*rel_folder.parts[1:]) if rel_folder.parts and rel_folder.parts[0].startswith("Tim_") else rel_folder
        for filename, label in meta.items():
            if not isinstance(label, dict) or not label.get("manualEdit"):
                continue
            source = export_root / source_folder / filename
            yield {
                "rel": (rel_folder / filename).as_posix(),
                "source": source,
                "x_manual": int(label.get("xPos", 0)),
                "y_manual": int(label.get("yPos", 0)),
            }


def colour_mask(image: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    # Red/orange/yellow guide range, plus the cyan-inverted fallback range.
    warm = cv2.inRange(hsv, np.array([0, 55, 45]), np.array([38, 255, 255]))
    warm |= cv2.inRange(hsv, np.array([165, 55, 45]), np.array([179, 255, 255]))
    cyan = cv2.inRange(hsv, np.array([75, 45, 45]), np.array([115, 255, 255]))
    mask = cv2.bitwise_or(warm, cyan)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 7))
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)


def detect(image: np.ndarray):
    h, w = image.shape[:2]
    mask = colour_mask(image)
    mask[:, int(w * 0.35):] = 0
    components, _, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    candidates = []
    for i in range(1, components):
        x, y, width, height, area = stats[i]
        if height < max(20, int(h * 0.045)) or area < 12:
            continue
        ratio = height / max(width, 1)
        if ratio < 3.0:
            continue
        roi = mask[y:y + height, x:x + width]
        lines = cv2.HoughLinesP(
            roi, 1, np.pi / 180, threshold=max(10, height // 4),
            minLineLength=max(15, int(height * 0.45)), maxLineGap=8,
        )
        vertical = 0
        if lines is not None:
            for line in lines.reshape(-1, 4):
                x1, y1, x2, y2 = map(int, line)
                angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
                if 80 <= angle <= 100:
                    vertical += 1
        score = (height * 2) + area + (vertical * height)
        candidates.append({
            "x": int(x), "y": int(y), "w": int(width), "h": int(height),
            "area": int(area), "vertical_lines": vertical, "score": int(score),
        })
    candidates.sort(key=lambda c: (-c["score"], c["x"]))
    return candidates[0] if candidates else None


def evaluate(record):
    image = cv2.imread(str(record["source"]))
    if image is None:
        return {**record, "status": "missing_or_unreadable", "source": str(record["source"])}
    h, w = image.shape[:2]
    # meta yPos/xPos are textbox coordinates; estimate guide top from fixed-offset layout.
    box_h = int(h * 0.053)
    expected_guide_x = record["x_manual"] - 6
    expected_guide_y = record["y_manual"] + (box_h // 2) - int(h * 0.018)
    candidate = detect(image)
    result = {
        **record,
        "source": str(record["source"]),
        "width": w,
        "height": h,
        "expected_guide_x": expected_guide_x,
        "expected_guide_y": expected_guide_y,
    }
    if candidate is None:
        result["status"] = "no_detection"
        return result
    dx = candidate["x"] - expected_guide_x
    dy = candidate["y"] - expected_guide_y
    result.update(candidate)
    result["dx"] = int(dx)
    result["dy"] = int(dy)
    result["distance"] = float(np.hypot(dx, dy))
    result["status"] = "match" if abs(dx) <= 10 and abs(dy) <= 10 else "mismatch"
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-dir", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--export-dir", type=Path, default=None)
    parser.add_argument("--edited-dir", type=Path, default=None)
    parser.add_argument("--logs-dir", type=Path, default=None)
    args = parser.parse_args()
    app_dir = args.app_dir.resolve()
    edited = (args.edited_dir or app_dir / "04_photos_edited").resolve()
    export = (args.export_dir or app_dir.parent / "03_photos_export").resolve()
    logs = (args.logs_dir or app_dir / "logs").resolve()
    logs.mkdir(parents=True, exist_ok=True)

    records = [evaluate(r) for r in manual_records(edited, export)]
    counts = {}
    for row in records:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    matched = [r for r in records if r.get("status") in {"match", "mismatch"}]
    errors = sorted((r["distance"] for r in matched))
    summary = {
        "opencv_version": cv2.__version__,
        "edited_root": str(edited),
        "export_root": str(export),
        "total_manual": len(records),
        "counts": counts,
        "median_distance": float(np.median(errors)) if errors else None,
        "p95_distance": float(np.percentile(errors, 95)) if errors else None,
        "records": records,
    }
    (logs / "opencv_guide_experiment.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    fields = sorted({key for row in records for key in row})
    with (logs / "opencv_guide_experiment.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    print(json.dumps({k: summary[k] for k in ("opencv_version", "total_manual", "counts", "median_distance", "p95_distance")}, indent=2))


if __name__ == "__main__":
    main()
