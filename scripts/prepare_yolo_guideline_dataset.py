"""Prepare a reproducible YOLO dataset from the generated source audit."""
from __future__ import annotations

import json
import random
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "logs" / "yolo_dataset_source_audit.json"
OUTPUT = ROOT / "yolo_guideline_dataset"
SEED = 20260811
VAL_RATIO = 0.2


def main() -> None:
    records = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    valid = [r for r in records if r.get("status") == "ok"]
    if not valid:
        raise SystemExit("No valid records in source audit")

    random.Random(SEED).shuffle(valid)
    val_count = max(1, round(len(valid) * VAL_RATIO))
    splits = {"val": valid[:val_count], "train": valid[val_count:]}

    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    for split in splits:
        (OUTPUT / "images" / split).mkdir(parents=True, exist_ok=True)
        (OUTPUT / "labels" / split).mkdir(parents=True, exist_ok=True)

    manifest = {"seed": SEED, "val_ratio": VAL_RATIO, "records": []}
    for split, split_records in splits.items():
        for index, record in enumerate(split_records):
            source = ROOT / record["source"]
            label = ROOT / record["label"]
            if not source.is_file() or not label.is_file():
                raise FileNotFoundError(f"Missing pair: {source} / {label}")
            stem = f"{index:04d}_{source.stem}"
            image_target = OUTPUT / "images" / split / f"{stem}{source.suffix.lower()}"
            label_target = OUTPUT / "labels" / split / f"{stem}.txt"
            shutil.copy2(source, image_target)
            shutil.copy2(label, label_target)
            manifest["records"].append({
                "split": split,
                "image": str(image_target.relative_to(ROOT)),
                "label": str(label_target.relative_to(ROOT)),
                "source": record["source"],
                "source_mode": record["source_mode"],
                "metadata": record["metadata"],
            })

    dataset_path = OUTPUT.as_posix()
    (OUTPUT / "dataset.yaml").write_text(
        f"path: {dataset_path}\ntrain: images/train\nval: images/val\nnames:\n  0: guideline\n",
        encoding="utf-8",
    )
    (ROOT / "logs" / "yolo_training_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Prepared {len(valid)} pairs: train={len(splits['train'])}, val={len(splits['val'])}")
    print(f"Dataset: {OUTPUT}")


if __name__ == "__main__":
    main()
