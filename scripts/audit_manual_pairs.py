from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "03_photos_export"
VALID_ROOT = ROOT / "04_photos_edited"
LOG_ROOT = ROOT / "logs" / "manual_pair_audit"
EXCLUDED = {
    "BTP BD/AXC/ZP 10C MSG/0.jpg",
    "BTP BD/AXC/ZP 10C MSG/50.jpg",
    "BTP BD/AXC/ZP 10C MSG/100.jpg",
}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def image_size(path: Path) -> list[int] | None:
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    return [int(image.shape[1]), int(image.shape[0])] if image is not None else None


def visual_distance(source: Path, valid: Path, x_pos: int, y_pos: int) -> float | None:
    source_image = cv2.imread(str(source), cv2.IMREAD_GRAYSCALE)
    valid_image = cv2.imread(str(valid), cv2.IMREAD_GRAYSCALE)
    if source_image is None or valid_image is None or source_image.shape != valid_image.shape:
        return None
    mask = np.ones(source_image.shape, dtype=bool)
    box_w = max(1, int(source_image.shape[1] * 0.48))
    box_h = max(1, int(source_image.shape[0] * 0.053))
    x1 = max(0, int(x_pos))
    y1 = max(0, int(y_pos))
    mask[y1:min(source_image.shape[0], y1 + box_h), x1:min(source_image.shape[1], x1 + box_w)] = False
    diff = cv2.absdiff(source_image, valid_image)
    values = diff[mask]
    return float(values.mean()) if values.size else None


def main() -> None:
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    source_by_name: dict[str, list[Path]] = defaultdict(list)
    for path in SOURCE_ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            source_by_name[path.parent.name].append(path)

    rows: list[dict] = []
    metadata_count = 0
    manual_count = 0
    for meta_path in sorted(VALID_ROOT.rglob("meta.json")):
        metadata_count += 1
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            rows.append({"status": "invalid_meta", "valid_meta": str(meta_path.relative_to(ROOT)), "error": str(exc)})
            continue
        folder_name = meta_path.parent.name
        source_candidates = source_by_name.get(folder_name, [])
        for frame, record in sorted(metadata.items()):
            if not isinstance(record, dict) or record.get("manualEdit") is not True:
                continue
            manual_count += 1
            valid_rel = meta_path.parent.relative_to(ROOT).as_posix() + "/" + frame
            excluded = valid_rel.split("/Tim_1/", 1)[-1].split("/Tim_2/", 1)[-1].split("/Tim_3/", 1)[-1] in EXCLUDED
            matches = [path for path in source_candidates if path.name.lower() == frame.lower()]
            valid_path = meta_path.parent / frame
            distances = {
                path: visual_distance(path, valid_path, int(record.get("xPos", 0)), int(record.get("yPos", 0)))
                for path in matches
            }
            ranked_matches = sorted(
                ((path, distance) for path, distance in distances.items() if distance is not None),
                key=lambda item: item[1],
            )
            source = ranked_matches[0][0] if ranked_matches else None
            source_distance = ranked_matches[0][1] if ranked_matches else None
            second_distance = ranked_matches[1][1] if len(ranked_matches) > 1 else None
            visual_confidence = (
                "low" if second_distance is not None and second_distance - source_distance < 1.0
                else "high" if source_distance is not None else None
            )
            row = {
                "status": "excluded" if excluded else ("paired" if source else ("ambiguous_source" if matches else "missing_source")),
                "valid_meta": str(meta_path.relative_to(ROOT)),
                "valid_frame": valid_rel,
                "asset_folder": folder_name,
                "frame": frame,
                "manualEdit": True,
                "xPos": record.get("xPos"),
                "yPos": record.get("yPos"),
                "dateText": record.get("dateText"),
                "source": str(source.relative_to(ROOT)) if source else None,
                "source_matches": [str(item.relative_to(ROOT)) for item in matches],
                "source_visual_distance": round(source_distance, 4) if source_distance is not None else None,
                "source_visual_confidence": visual_confidence,
                "valid_size": image_size(meta_path.parent / frame),
                "source_size": image_size(source) if source else None,
            }
            row["same_size"] = row["valid_size"] == row["source_size"] and row["source_size"] is not None
            rows.append(row)

    payload = {
        "source_root": str(SOURCE_ROOT),
        "valid_root": str(VALID_ROOT),
        "excluded": sorted(EXCLUDED),
        "metadata_files": metadata_count,
        "manual_records": manual_count,
        "summary": {status: sum(row.get("status") == status for row in rows) for status in sorted({row.get("status") for row in rows})},
        "rows": rows,
    }
    (LOG_ROOT / "edited_ground_truth_pairs.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = sorted({key for row in rows for key in row})
    with (LOG_ROOT / "edited_ground_truth_pairs.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"metadata_files": metadata_count, "manual_records": manual_count, "summary": payload["summary"], "output": str(LOG_ROOT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
