#!/usr/bin/env python3
"""Export manual crop and textbox-position audit data without processing photos."""

import argparse
import csv
import json
from pathlib import Path


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def iter_json_files(root: Path, filename: str):
    return root.rglob(filename) if root.exists() else ()


def collect(export_root: Path, edited_root: Path):
    rows = []
    crop_count = 0
    for crop_file in iter_json_files(export_root, "collage_crop.json"):
        data = read_json(crop_file, {})
        for photo_name, crop in (data.get("photos") or {}).items():
            crop_count += 1
            rows.append({
                "rel": crop.get("rel", f"{crop_file.parent.name}/{photo_name}"),
                "sourcePath": crop.get("sourcePath"),
                "cropBox": crop.get("cropBox"),
                "cropBoxPct": crop.get("cropBoxPct"),
                "imageSize": crop.get("imageSize"),
                "cropUpdatedAt": crop.get("updatedAt"),
                "initial": None,
                "latestUserCorrection": None,
            })

    by_rel = {row["rel"]: row for row in rows}
    for meta_file in iter_json_files(edited_root, "meta.json"):
        meta_data = read_json(meta_file, {})
        for photo_name, meta in meta_data.items():
            if not isinstance(meta, dict):
                continue
            rel = meta.get("rel", f"{meta_file.parent.name}/{photo_name}").replace("\\", "/")
            row = by_rel.setdefault(rel, {
                "rel": rel,
                "sourcePath": None,
                "cropBox": None,
                "cropBoxPct": None,
                "imageSize": None,
                "cropUpdatedAt": None,
                "initial": None,
                "latestUserCorrection": None,
            })
            row["initial"] = meta.get("initial")
            row["latestUserCorrection"] = meta.get("latestUserCorrection")

    for row in by_rel.values():
        initial = row.get("initial") or {}
        latest = row.get("latestUserCorrection") or {}
        row["deltaX"] = latest.get("xPos", initial.get("xPos")) - initial.get("xPos") if latest.get("xPos") is not None and initial.get("xPos") is not None else None
        row["deltaY"] = latest.get("yPos", initial.get("yPos")) - initial.get("yPos") if latest.get("yPos") is not None and initial.get("yPos") is not None else None

    return list(by_rel.values()), crop_count


def main():
    parser = argparse.ArgumentParser(description="Export manual crop/edit metadata audit")
    parser.add_argument("--export-root", type=Path, default=Path("03_photos_export"))
    parser.add_argument("--edited-root", type=Path, default=Path("04_photos_edited"))
    parser.add_argument("--output", type=Path, default=Path("logs/manual_edit_audit.json"))
    args = parser.parse_args()

    rows, crop_count = collect(args.export_root, args.edited_root)
    report = {
        "schemaVersion": 1,
        "photoCount": len(rows),
        "manualCropCount": crop_count,
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    csv_path = args.output.with_suffix(".csv")
    fields = ["rel", "sourcePath", "cropBox", "cropBoxPct", "imageSize", "cropUpdatedAt", "initial", "latestUserCorrection", "deltaX", "deltaY"]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: json.dumps(row[field], ensure_ascii=False) if isinstance(row[field], (dict, list)) else row[field] for field in fields} for row in rows)

    print(f"Wrote {args.output} and {csv_path} ({len(rows)} photos, {crop_count} manual crops)")


if __name__ == "__main__":
    main()
