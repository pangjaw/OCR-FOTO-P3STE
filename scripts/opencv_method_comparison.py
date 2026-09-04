#!/usr/bin/env python3
"""Compare four independent OpenCV guide detectors on manually edited photos."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import cv2
import numpy as np


METHODS = ("hsv_components", "canny_hough", "hough_lines", "contours")

def records(edited: Path, export: Path):
    for meta in sorted(edited.rglob("meta.json")):
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        rel = meta.parent.relative_to(edited)
        src_rel = Path(*rel.parts[1:]) if rel.parts and rel.parts[0].startswith("Tim_") else rel
        for name, label in data.items():
            if isinstance(label, dict) and label.get("manualEdit"):
                yield {
                    "rel": (rel / name).as_posix(), "source": export / src_rel / name,
                    "x_manual": int(label.get("xPos", 0)), "y_manual": int(label.get("yPos", 0)),
                }

def candidate(x, y, w, h, score, method):
    return {"x": int(x), "y": int(y), "w": int(w), "h": int(h), "score": float(score), "method": method}

def hsv_components(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([0, 35, 25]), np.array([179, 255, 255]))
    mask[:, int(img.shape[1] * .35):] = 0
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 9), np.uint8))
    n, _, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    out = []
    for x, y, w, h, area in stats[1:]:
        if h >= max(18, int(img.shape[0] * .035)) and area >= 10 and h / max(w, 1) >= 2.5:
            out.append(candidate(x, y, w, h, h * 2 + area, "hsv_components"))
    return out

def canny_hough(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 35, 110)
    edges[:, int(img.shape[1] * .35):] = 0
    lines = cv2.HoughLinesP(edges, 1, np.pi / 1800, threshold=16,
                            minLineLength=max(18, int(img.shape[0] * .035)), maxLineGap=12)
    out = []
    if lines is not None:
        for x1, y1, x2, y2 in lines.reshape(-1, 4):
            angle = abs(np.degrees(np.arctan2(y2-y1, x2-x1)))
            length = float(np.hypot(x2-x1, y2-y1))
            if angle >= 82 or angle <= 8:
                out.append(candidate(min(x1, x2), min(y1, y2), abs(x2-x1)+1, abs(y2-y1)+1,
                                      length + (abs(y2-y1) * 2), "canny_hough"))
    return out

def hough_lines(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edges[:, int(img.shape[1] * .35):] = 0
    lines = cv2.HoughLines(edges, 1, np.pi / 180, max(18, int(img.shape[0] * .04)))
    out = []
    if lines is not None:
        for rho, theta in lines[:, 0]:
            deg = abs(np.degrees(theta))
            if deg < 8 or abs(deg - 180) < 8:
                x = int(rho / max(np.cos(theta), .01))
                out.append(candidate(max(0, x-1), int(img.shape[0]*.1), 3, int(img.shape[0]*.8),
                                      img.shape[0], "hough_lines"))
    return out

def contours(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mask = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY_INV, 31, 7)
    mask[:, int(img.shape[1] * .35):] = 0
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 11), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)
        if h >= max(18, int(img.shape[0] * .035)) and h / max(w, 1) >= 2.5 and area >= 10:
            out.append(candidate(x, y, w, h, h * 2 + area, "contours"))
    return out

DETECTORS = {"hsv_components": hsv_components, "canny_hough": canny_hough,
            "hough_lines": hough_lines, "contours": contours}

def main():
    root = Path(__file__).resolve().parents[1]
    edited, export, logs = root / "04_photos_edited", root.parent / "03_photos_export", root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    all_rows = []
    for rec in records(edited, export):
        img = cv2.imread(str(rec["source"]))
        for method in METHODS:
            row = {**rec, "source": str(rec["source"]), "method": method}
            if img is None:
                row["status"] = "missing_or_unreadable"
                all_rows.append(row)
                continue
            h = img.shape[0]
            expected_x = rec["x_manual"] - 6
            expected_y = rec["y_manual"] + int(h * .053) // 2 - int(h * .018)
            candidates = DETECTORS[method](img)
            best = min(candidates, key=lambda c: abs(c["x"]-expected_x) + abs(c["y"]-expected_y)) if candidates else None
            row.update({"expected_x": expected_x, "expected_y": expected_y, "candidate_count": len(candidates)})
            if best is None:
                row["status"] = "no_detection"
            else:
                row.update(best)
                row["dx"], row["dy"] = best["x"]-expected_x, best["y"]-expected_y
                row["distance"] = float(np.hypot(row["dx"], row["dy"]))
                row["status"] = "match" if abs(row["dx"]) <= 10 and abs(row["dy"]) <= 10 else "mismatch"
            all_rows.append(row)
    summary = {"opencv_version": cv2.__version__, "total_manual": len(all_rows)//4, "methods": {}}
    for method in METHODS:
        subset = [r for r in all_rows if r["method"] == method]
        distances = [r["distance"] for r in subset if "distance" in r]
        counts = {s: sum(r.get("status") == s for r in subset) for s in ("match", "mismatch", "no_detection", "missing_or_unreadable")}
        summary["methods"][method] = {"counts": counts, "median_distance": float(np.median(distances)) if distances else None,
                                       "p95_distance": float(np.percentile(distances, 95)) if distances else None}
    (logs / "opencv_method_comparison.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    fields = sorted({k for row in all_rows for k in row})
    with (logs / "opencv_method_comparison.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(all_rows)
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
