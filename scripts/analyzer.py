import os
import sys
import json
from pathlib import Path
from PIL import Image
import numpy as np

sys.path.append(str(Path(__file__).parent))
from crop_collage_photos import is_collage_photo_adaptive

def run_misposition_analyzer(photos_edited_dir="04_photos_edited", photos_export_dir="03_photos_export", logs_dir="logs"):
    app_dir = Path(__file__).parent.parent
    edited_root = app_dir / photos_edited_dir
    export_root = app_dir / photos_export_dir
    logs_root = app_dir / logs_dir

    if not edited_root.exists():
        return {"total": 0, "results": []}

    all_edited_jpgs = sorted(list(edited_root.glob("**/*.jpg")))
    
    # Group photos by folder key
    folders_map = {}
    for p in all_edited_jpgs:
        rel = p.relative_to(edited_root)
        parts = rel.parts
        if len(parts) >= 2:
            group = parts[0]
            rel_folder = Path(*parts[1:-1])
            fname = parts[-1]
            key = (group, str(rel_folder))
            if key not in folders_map:
                folders_map[key] = []
            folders_map[key].append((p, fname, rel))

    # Read meta.json files
    meta_cache = {}
    for key, items in folders_map.items():
        group, rel_folder_str = key
        meta_file = edited_root / group / rel_folder_str / "meta.json"
        if meta_file.exists():
            try:
                meta_cache[key] = json.loads(meta_file.read_text(encoding="utf-8"))
            except Exception:
                meta_cache[key] = {}
        else:
            meta_cache[key] = {}

    # Load cropped collages manifest
    cropped_manifest = set()
    manifest_file = logs_root / "cropped_collages.json"
    if manifest_file.exists():
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                cropped_manifest = {m.replace("\\", "/").lower() for m in json.load(f)}
        except Exception:
            pass

    results = []

    for key, items in folders_map.items():
        group, rel_folder_str = key
        meta_data = meta_cache.get(key, {})

        # Collect Y positions for folder median calculation
        folder_y_list = []
        for p, fname, rel in items:
            m = meta_data.get(fname, {})
            y_val = m.get("yPos")
            if y_val is not None:
                folder_y_list.append(int(y_val))

        folder_median_y = int(np.median(folder_y_list)) if len(folder_y_list) > 0 else 220

        for p, fname, rel in items:
            raw_export_path = export_root / rel_folder_str / fname
            rel_photo_str = str(Path(rel_folder_str) / fname).replace("\\", "/").lower()
            m = meta_data.get(fname, {})
            y_val = m.get("yPos", 220)
            x_val = m.get("xPos", 14)
            date_text = m.get("dateText", "")

            # Risk calculation factors
            risk_score = 0
            reasons = []

            # Check 0: Uncropped Collage Detection (raw_export_path)
            is_manual = m.get("manualEdit", False)
            is_already_cropped = rel_photo_str in cropped_manifest
            if raw_export_path.exists() and not is_manual and not is_already_cropped:
                try:
                    img_raw = Image.open(raw_export_path)
                    is_coll, _, _, _ = is_collage_photo_adaptive(img_raw)
                    if is_coll:
                        risk_score += 80
                        reasons.append("Foto Masih Berupa Kolase 2x2 (Perlu Di-crop Manual / Otomatis)")
                except Exception:
                    pass

            # Check 1: Fallback indicator
            is_fallback = False
            flag_unedited = p.with_suffix(p.suffix + ".unedited")
            if flag_unedited.exists() and not is_manual:
                is_fallback = True
                risk_score += 60
                reasons.append("Stage Fallback Skipped (No Red Guide Found)")

            # Check 2: Outlier Y position
            y_dev = abs(y_val - folder_median_y)
            if not is_manual:
                if y_dev > 25:
                    risk_score += 40
                    reasons.append(f"Y-Position Outlier (Dev: {y_dev}px from folder median {folder_median_y}px)")
                elif y_dev > 15:
                    risk_score += 20
                    reasons.append(f"Y-Position Variance ({y_dev}px delta)")

                # Check 3: Abnormal absolute Y range
                if y_val < 130:
                    risk_score += 35
                    reasons.append(f"Abnormally High Y-Position ({y_val}px < 130px)")
                elif y_val > 255:
                    risk_score += 35
                    reasons.append(f"Abnormally Low Y-Position ({y_val}px > 255px)")
            else:
                risk_score = 0
                reasons.append("Koreksi Manual User (Presisi Terverifikasi)")

            # Determine Risk Category
            if risk_score >= 50:
                category = "HIGH"
            elif risk_score >= 20:
                category = "MEDIUM"
            else:
                category = "LOW"

            results.append({
                "rel": str(Path(rel_folder_str) / fname).replace("\\", "/"),
                "group": group,
                "folder": rel_folder_str.replace("\\", "/"),
                "filename": fname,
                "yPos": y_val,
                "xPos": x_val,
                "dateText": date_text,
                "folderMedianY": folder_median_y,
                "isFallback": is_fallback,
                "riskScore": risk_score,
                "riskCategory": category,
                "reasons": reasons
            })

    # Sort results by highest risk score first
    results.sort(key=lambda x: x["riskScore"], reverse=True)

    summary = {
        "total": len(results),
        "highRisk": len([r for r in results if r["riskCategory"] == "HIGH"]),
        "mediumRisk": len([r for r in results if r["riskCategory"] == "MEDIUM"]),
        "lowRisk": len([r for r in results if r["riskCategory"] == "LOW"]),
        "results": results
    }

    logs_root.mkdir(parents=True, exist_ok=True)
    report_json = logs_root / "misposition_audit_report.json"
    report_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return summary

if __name__ == "__main__":
    summary = run_misposition_analyzer()
    print("=== MISPOSITION ANALYZER COMPLETE ===")
    print(f"Total Photos Audited: {summary['total']}")
    print(f"  HIGH RISK (Mispositioned / Fallback): {summary['highRisk']}")
    print(f"  MEDIUM RISK (Variance): {summary['mediumRisk']}")
    print(f"  LOW RISK (Presisi Tinggi): {summary['lowRisk']}")
