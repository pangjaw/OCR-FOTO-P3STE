from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import cv2
import numpy as np

EXTS = {".jpg", ".jpeg", ".png", ".webp"}
EXCLUDED_FILES = {
    "BTP BD/AXC/ZP 10C MSG/0.jpg",
    "BTP BD/AXC/ZP 10C MSG/50.jpg",
    "BTP BD/AXC/ZP 10C MSG/100.jpg",
}


def stats(values: np.ndarray) -> dict:
    values = values.astype(float).ravel()
    if not values.size:
        return {"count": 0}
    return {"count": int(values.size), **{f"p{p}": round(float(np.percentile(values, p)), 3) for p in (5, 25, 50, 75, 95)}}


def classify_color(hue: np.ndarray, saturation: np.ndarray, value: np.ndarray) -> str:
    h = float(np.median(hue))
    s = float(np.median(saturation))
    v = float(np.median(value))
    if s < 35 and v > 150:
        return "white"
    if h >= 170 or h < 4:
        return "red"
    if h < 18:
        return "orange"
    return "yellow"


def find_candidates(rgb: np.ndarray) -> list[dict]:
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    h, w = hsv.shape[:2]
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    warm = (((hue <= 45) | (hue >= 170)) & (sat >= 25) & (val >= 40)).astype(np.uint8) * 255
    warm = cv2.morphologyEx(warm, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 7)))
    count, _, component_stats, _ = cv2.connectedComponentsWithStats(warm, 8)
    minimum_height = max(20, int(h * 0.045))
    candidates = []
    for i in range(1, count):
        x, y, width, height, area = map(int, component_stats[i])
        if height < minimum_height or width > max(20, int(w * 0.12)) or area < 12:
            continue
        ratio = height / max(width, 1)
        if ratio < 2.0:
            continue
        density = area / max(1, width * height)
        score = min(1.0, height / max(1, h * 0.35)) * 0.55 + min(1.0, 3 / max(1, width)) * 0.25 + density * 0.20
        pixels = hsv[y:y + height, x:x + width].reshape(-1, 3)
        candidates.append({
            "bbox": [x, y, x + width - 1, y + height - 1],
            "score": round(float(score), 5),
            "color": classify_color(pixels[:, 0], pixels[:, 1], pixels[:, 2]),
            "hue": stats(pixels[:, 0]),
            "saturation": stats(pixels[:, 1]),
            "value": stats(pixels[:, 2]),
            "height": height,
            "width": width,
            "density": round(float(density), 5),
        })
    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates[:3]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("03_photos_export"))
    parser.add_argument("--logs", type=Path, default=Path("logs"))
    parser.add_argument("--max-contact", type=int, default=48)
    args = parser.parse_args()
    root = args.input.resolve()
    logs = args.logs.resolve()
    logs.mkdir(parents=True, exist_ok=True)
    rows = []
    contact = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if relative in EXCLUDED_FILES or path.suffix.lower() not in EXTS:
            continue
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            continue
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        candidates = find_candidates(rgb)
        for rank, candidate in enumerate(candidates, 1):
            row = {"file": relative, "rank": rank, **candidate}
            if rank == 1:
                next_score = candidates[1]["score"] if len(candidates) > 1 else 0.0
                row["selection_status"] = "uncertain" if candidate["score"] - next_score < 0.08 else "selected"
            else:
                row["selection_status"] = "alternative"
            rows.append(row)
            if len(contact) < args.max_contact and rank == 1:
                x1, y1, x2, y2 = candidate["bbox"]
                preview = cv2.resize(image, (180, 180), interpolation=cv2.INTER_AREA)
                cv2.rectangle(preview, (int(x1 * 180 / image.shape[1]), int(y1 * 180 / image.shape[0])), (int(x2 * 180 / image.shape[1]), int(y2 * 180 / image.shape[0])), (0, 255, 0), 2)
                cv2.putText(preview, f"{len(contact)+1}: {candidate['color']} {path.stem}", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA)
                contact.append(preview)
    color_counts = {}
    for item in rows:
        color_counts[item["color"]] = color_counts.get(item["color"], 0) + 1
    payload = {"input": str(root), "excluded_files": sorted(EXCLUDED_FILES), "candidate_count": len(rows), "photo_count": len({row['file'] for row in rows}), "color_counts": color_counts, "rows": rows}
    (logs / "guide_hsv_audit.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = ["file", "rank", "bbox", "score", "color", "selection_status", "height", "width", "density", "hue", "saturation", "value"]
    with (logs / "guide_hsv_audit.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    if contact:
        cols = 6
        rows_count = (len(contact) + cols - 1) // cols
        sheet = np.full((rows_count * 180, cols * 180, 3), 32, dtype=np.uint8)
        for index, preview in enumerate(contact):
            y, x = divmod(index, cols)
            sheet[y * 180:(y + 1) * 180, x * 180:(x + 1) * 180] = preview
        cv2.imwrite(str(logs / "guide_hsv_contact_sheet.jpg"), sheet)
    print(json.dumps({"photos_with_candidates": payload["photo_count"], "candidate_count": payload["candidate_count"], "color_counts": color_counts, "excluded": sorted(EXCLUDED_FILES), "contact_sheet": str(logs / "guide_hsv_contact_sheet.jpg")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
