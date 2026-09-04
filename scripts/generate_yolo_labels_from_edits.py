"""Generate YOLO guideline labels from edited photos and metadata."""
from __future__ import annotations

import json
from pathlib import Path

import cv2

DIR_RAW = Path("03_photos_export")
DIR_CROPPED = Path("03_photos_cropped_temp")
DIR_EDITED = Path("04_photos_edited")
DIR_LABELS = Path("yolo_labels")
AUDIT_PATH = Path("logs/yolo_dataset_source_audit.json")

CLASS_ID = 0
DIFF_THRESHOLD = 30
GUIDE_WIDTH_PX = 5
X_OFFSET_FROM_GUIDE = 6
TEXTBOX_Y_OFFSET_RATIO = 0.018
MIN_CONTOUR_AREA = 4.0


def relative_without_team(path: Path) -> Path:
    """Remove the Tim_N prefix used only by edited/output folders."""
    parts = path.parts
    if parts and parts[0].lower().startswith("tim_"):
        return Path(*parts[1:])
    return path


def estimate_guideline_bbox(meta_record, width, height):
    """Reverse-engineer guideline xyxy from textbox top-left metadata."""
    tb_x = int(meta_record["xPos"])
    tb_y = int(meta_record["yPos"])
    tb_w = int(width * 0.48)
    tb_h = int(height * 0.053)
    gx2 = tb_x - X_OFFSET_FROM_GUIDE
    gx1 = gx2 - GUIDE_WIDTH_PX
    gy1 = tb_y + tb_h // 2 - int(height * TEXTBOX_Y_OFFSET_RATIO)
    gy2 = gy1 + tb_h
    gx1 = max(0, min(gx1, width - 1))
    gx2 = max(gx1 + 1, min(gx2, width))
    gy1 = max(0, min(gy1, height - 1))
    gy2 = max(gy1 + 1, min(gy2, height))
    return (gx1, gy1, gx2, gy2), (tb_x, tb_y, tb_w, tb_h)


def to_yolo(bbox, width, height):
    """Convert pixel xyxy coordinates to one normalized YOLO label line."""
    gx1, gy1, gx2, gy2 = bbox
    xc = ((gx1 + gx2) / 2.0) / width
    yc = ((gy1 + gy2) / 2.0) / height
    bw = (gx2 - gx1) / width
    bh = (gy2 - gy1) / height
    return f"{CLASS_ID} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}"


def resolve_source(meta_path: Path, image_name: str):
    """Use cropped source for collages, raw export for non-collage photos."""
    edited_relative = meta_path.parent.relative_to(DIR_EDITED)
    relative = relative_without_team(edited_relative / image_name)
    cropped = DIR_CROPPED / relative
    if cropped.is_file():
        return cropped, "cropped"
    return DIR_RAW / relative, "raw_non_collage"


def process_record(meta_path: Path, image_name: str, meta_record: dict):
    """Generate one guideline label from metadata textbox coordinates."""
    edited_path = meta_path.parent / image_name
    label_relative = meta_path.parent.relative_to(DIR_EDITED) / Path(image_name).with_suffix(".txt")
    label_path = DIR_LABELS / label_relative
    source_path, source_mode = resolve_source(meta_path, image_name)
    result = {
        "metadata": str(meta_path),
        "edited": str(edited_path),
        "source": str(source_path),
        "source_mode": source_mode,
        "label": str(label_path),
        "status": "skip",
    }

    if source_path is None:
        result["reason"] = "user-cropped source not found"
        return result
    if not source_path.is_file():
        result["reason"] = "missing cropped source image"
        return result

    source = cv2.imread(str(source_path), cv2.IMREAD_COLOR)
    if source is None:
        result["reason"] = "unreadable source image"
        return result
    height, width = source.shape[:2]
    try:
        guideline, textbox = estimate_guideline_bbox(meta_record, width, height)
    except (KeyError, TypeError, ValueError) as exc:
        result["reason"] = f"invalid xPos/yPos metadata: {exc}"
        return result
    label_path.parent.mkdir(parents=True, exist_ok=True)
    label_path.write_text(to_yolo(guideline, width, height) + "\n", encoding="utf-8")
    result.update({
        "status": "ok",
        "image_size": [width, height],
        "textbox_bbox": list(textbox),
        "guideline_bbox": list(guideline),
        "metadata_position": {"xPos": meta_record["xPos"], "yPos": meta_record["yPos"]},
    })
    return result


def main():
    if not DIR_EDITED.is_dir():
        raise SystemExit(f"Edited directory not found: {DIR_EDITED}")
    meta_files = sorted(
        p for p in DIR_EDITED.rglob("meta.json")
        if "backup" not in {part.lower() for part in p.parts}
    )
    if not meta_files:
        raise SystemExit(f"No active meta.json files found in {DIR_EDITED}")

    results = []
    for meta_path in meta_files:
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            results.append({"metadata": str(meta_path), "status": "skip", "reason": f"invalid metadata: {exc}"})
            continue
        for image_name in sorted(metadata):
            if Path(image_name).suffix.lower() not in {".jpg", ".jpeg"}:
                continue
            result = process_record(meta_path, image_name, metadata[image_name])
            results.append(result)
            prefix = "OK" if result["status"] == "ok" else "SKIP"
            print(f"{prefix} {result.get('edited', meta_path)} -> {result.get('reason', result['source_mode'])}")

    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(r["status"] == "ok" for r in results)
    skipped = len(results) - ok
    cropped = sum(
        r.get("source_mode") == "cropped" and r["status"] == "ok"
        for r in results
    )
    raw_non_collage = sum(
        r.get("source_mode") == "raw_non_collage" and r["status"] == "ok"
        for r in results
    )
    print(f"Done: {ok} labels generated, {skipped} skipped, {len(results)} metadata records scanned.")
    print(f"Sources: {cropped} cropped, {raw_non_collage} raw non-collage.")
    print(f"Audit: {AUDIT_PATH}")


if __name__ == "__main__":
    main()
