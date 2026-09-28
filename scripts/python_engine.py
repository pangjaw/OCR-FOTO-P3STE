"""
python_engine.py — Unified Dispatcher for OCR-FOTO-P3STE Core Scripts
Bundled by PyInstaller to provide a fully standalone Python execution engine for non-Python PCs.
"""

import sys
import os
from pathlib import Path

# Ensure scripts and root directories are in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

ROOT_DIR = SCRIPT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Direct imports of all script modules to ensure PyInstaller bundles all dependencies
import export_pdf_foto
import auto_crop_collages
import extract_pdf_dates
import scheduler
import audit_and_correct_personnel
import extract_file_personnel
import edit_timemark_ide1
import merge_pdf_foto
import correct_serat_optik_cores
import edit_photo_time_only
import export_tablo_excel
import export_dinasan_excel
import export_asset_data_excel
import correct_pdf_dates

MODULE_MAP = {
    "export_pdf_foto": export_pdf_foto,
    "auto_crop_collages": auto_crop_collages,
    "extract_pdf_dates": extract_pdf_dates,
    "scheduler": scheduler,
    "audit_and_correct_personnel": audit_and_correct_personnel,
    "extract_file_personnel": extract_file_personnel,
    "edit_timemark_ide1": edit_timemark_ide1,
    "merge_pdf_foto": merge_pdf_foto,
    "correct_serat_optik_cores": correct_serat_optik_cores,
    "edit_photo_time_only": edit_photo_time_only,
    "export_tablo_excel": export_tablo_excel,
    "export_dinasan_excel": export_dinasan_excel,
    "export_asset_data_excel": export_asset_data_excel,
    "correct_pdf_dates": correct_pdf_dates,
}

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print("=== OCR-FOTO-P3STE Standalone Python Engine ===")
        print("Usage: python_engine.exe <script_name> [arguments...]")
        print("\nAvailable modules:")
        for name in sorted(MODULE_MAP.keys()):
            print(f"  • {name}")
        return 0

    target_name = sys.argv[1].replace(".py", "").strip()
    if target_name not in MODULE_MAP:
        print(f"[ERROR] Module '{target_name}' tidak dikenal.")
        print("Modules yang tersedia:", ", ".join(sorted(MODULE_MAP.keys())))
        return 1

    mod = MODULE_MAP[target_name]
    # Reconstruct sys.argv so argparse in the target module receives target module name as argv[0]
    sys.argv = [f"{target_name}.py"] + sys.argv[2:]

    if hasattr(mod, "main"):
        res = mod.main()
        return res if isinstance(res, int) else 0
    else:
        print(f"[ERROR] Module '{target_name}' tidak memiliki fungsi main().")
        return 1

if __name__ == "__main__":
    sys.exit(main())
