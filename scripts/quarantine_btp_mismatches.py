#!/usr/bin/env python3
"""Quarantine photo output folders whose station code maps to another BTP."""
import json
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPORT = ROOT / "03_photos_export"
EDITED = ROOT / "04_photos_edited"
LOGS = ROOT / "logs"
MAPPING = {
    "BOO": "BTP JAK", "CLT": "BTP JAK", "BJD": "BTP JAK",
    "BNR": "BTP BD", "BOP": "BTP BD", "BTT": "BTP BD",
    "CGB": "BTP BD", "COS": "BTP BD", "MSG": "BTP BD",
    "CCR": "BTP BD", "BOP-BTT": "BTP BD",
}
CANDIDATES = [
    "BTP JAK/PTLS/RADIO_CGB",
    "BTP JAK/SERAT OPTIK/ER SINYAL BOP",
    "BTP JAK/SERAT OPTIK/ER SINYAL BTT",
    "BTP JAK/SERAT OPTIK/JPL BNR BOO-BOP",
]

def move_tree(src, dst, manifest, kind):
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    files = [p for p in dst.rglob("*") if p.is_file()]
    manifest.append({
        "kind": kind,
        "source": str(src.relative_to(ROOT)).replace("\\", "/"),
        "quarantine": str(dst.relative_to(ROOT)).replace("\\", "/"),
        "fileCount": len(files),
        "bytes": sum(p.stat().st_size for p in files),
    })

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
quarantine = LOGS / f"btp_quarantine_{stamp}"
manifest = []
for rel in CANDIDATES:
    source = EXPORT / Path(rel)
    move_tree(source, quarantine / "03_photos_export" / Path(rel), manifest, "export")
    for tim in sorted(EDITED.glob("Tim_*")):
        source = tim / Path(rel)
        if source.exists():
            move_tree(source, quarantine / "04_photos_edited" / tim.name / Path(rel), manifest, "edited")

report = {
    "schemaVersion": 1,
    "createdAt": datetime.now().isoformat(timespec="seconds"),
    "mapping": MAPPING,
    "candidates": CANDIDATES,
    "quarantineRoot": str(quarantine.relative_to(ROOT)).replace("\\", "/"),
    "moves": manifest,
}
manifest_path = LOGS / f"btp_cleanup_manifest_{stamp}.json"
manifest_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"manifest": str(manifest_path), "quarantine": str(quarantine), "moves": manifest}, indent=2))
