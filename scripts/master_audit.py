"""master_audit.py — Master Asset Completeness & Over-target Audit Engine (2026).

Audits target asset outputs against official 398 Master Target Whitelist.
Checks 03_photos_export, 04_photos_edited, and 05_pdf_merged.
Generates logs/master_audit_report.json and logs/AUDIT_KELENGKAPAN_MASTER_2026.xlsx.
"""
import json
import os
import re
from pathlib import Path
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill

APP_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = APP_DIR / "logs"
EXPORT_DIR = APP_DIR / "03_photos_export"
EDITED_DIR = APP_DIR / "04_photos_edited"
MERGED_DIR = APP_DIR / "05_pdf_merged"

# Master targets baseline by Category (2026 Master Data)
MASTER_CATEGORY_TARGETS = {
    "WESEL": 62,
    "AXC": 139,
    "SINYAL": 125,
    "SERAT OPTIK": 22,
    "PTPP": 11,
    "JPL": 10,
    "CATUDAYA": 9,
    "PTLS": 5,
    "PDSE": 7,
    "PTDS": 7,
    "POINT LOCK": 2,
    "CTS": 2
}

TOTAL_MASTER_TARGET = 395

def normalize_text(text):
    return re.sub(r'[\s_\-]+', ' ', text).lower().strip()

def match_detail_to_pdf(detail, merged_pdfs):
    norm_detail = normalize_text(detail)
    core_detail = re.sub(r'\s*\d{2}[-_ ]\d{2}.*$', '', norm_detail)
    
    for pdf in merged_pdfs:
        norm_pdf = normalize_text(pdf)
        if core_detail in norm_pdf or norm_detail in norm_pdf:
            return pdf
    return ""

def detect_category(rel_folder, detail, pdf_name=""):
    full_str = f"{rel_folder} {detail} {pdf_name}".upper()
    parts = rel_folder.split('/')
    cat_folder = parts[1].upper() if len(parts) > 1 else ""
    
    # POINT LOCK override (special case under WESEL folder)
    if "POINT LOCK" in full_str or "POINT_LOCK" in full_str:
        return "POINT LOCK"
        
    # Primary check: exact category folder in 03_photos_export (rel_folder)
    for k in MASTER_CATEGORY_TARGETS:
        if k == "SERAT OPTIK" and ("SERAT OPTIK" in cat_folder or "SERAT_OPTIK" in cat_folder):
            return "SERAT OPTIK"
        if k == cat_folder or k in cat_folder:
            return k
            
    # Secondary check: text matching for unmapped folders
    if "SERAT OPTIK" in full_str or "SERAT_OPTIK" in full_str:
        return "SERAT OPTIK"
    if "CATUDAYA" in full_str or "CATU DAYA" in full_str or "RADIO_COS" in full_str or "RADIO BASESTATION" in full_str:
        return "CATUDAYA"
    if "PTPP" in full_str:
        return "PTPP"
    if "PTLS" in full_str:
        return "PTLS"
    if "PTDS" in full_str:
        return "PTDS"
    if "PDSE" in full_str:
        return "PDSE"
    if "JPL" in full_str or "PINTU PERLINTASAN" in full_str:
        return "JPL"
    if "CTS" in full_str or "CTC" in full_str:
        return "CTS"
    if "AXC" in full_str or "AXLE COUNTER" in full_str or "ZP " in full_str or "ZP_" in full_str:
        return "AXC"
    if "SINYAL" in full_str or "SIGNAL" in full_str or re.search(r'\bJ\d+\b', full_str) or re.search(r'\bJL\d+\b', full_str):
        return "SINYAL"
    if "WESEL" in full_str or re.search(r'\bW\d+\b', full_str):
        return "WESEL"

    return "UNKNOWN"

def run_master_audit():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Scan 05_pdf_merged for PDFs
    merged_pdfs = set()
    if MERGED_DIR.is_dir():
        for p in MERGED_DIR.rglob("*.pdf"):
            merged_pdfs.add(p.name)

    # 2. Scan 03_photos_export and 04_photos_edited for folders
    export_folders = set()
    if EXPORT_DIR.is_dir():
        for p in EXPORT_DIR.rglob("*.jpg"):
            rel_folder = str(p.parent.relative_to(EXPORT_DIR)).replace('\\', '/')
            export_folders.add(rel_folder)

    edited_folders = set()
    if EDITED_DIR.is_dir():
        for p in EDITED_DIR.rglob("*.jpg"):
            rel = str(p.parent.relative_to(EDITED_DIR)).replace('\\', '/')
            parts = rel.split('/')
            if len(parts) >= 2:
                edited_folders.add('/'.join(parts[1:]))

    # 3. Categorize outputs
    category_counts = {cat: 0 for cat in MASTER_CATEGORY_TARGETS}
    extra_items = []
    processed_items = []

    # Map processed folders to categories
    for rel_f in export_folders:
        parts = rel_f.split('/')
        btp = parts[0] if len(parts) > 0 else "UNKNOWN"
        detail = '/'.join(parts[2:]) if len(parts) > 2 else rel_f
        
        has_edited = rel_f in edited_folders
        
        # Check matching PDF name with normalized matching
        matched_pdf_name = match_detail_to_pdf(detail, merged_pdfs)
        has_pdf = bool(matched_pdf_name)
        matched_cat = detect_category(rel_f, detail, matched_pdf_name)
        
        status = "LENGKAP" if (has_edited and has_pdf) else ("FOTO_ADA" if (has_edited or rel_f in export_folders) else "BELUM_DIPROSES")
        
        if matched_cat in category_counts:
            category_counts[matched_cat] += 1
            processed_items.append({
                "btp": btp,
                "category": matched_cat,
                "detail": detail,
                "folderKey": rel_f,
                "hasExport": True,
                "hasEdited": has_edited,
                "hasPdf": has_pdf,
                "matchedPdf": matched_pdf_name,
                "status": status
            })
        else:
            extra_items.append({
                "btp": btp,
                "category": matched_cat,
                "detail": detail,
                "folderKey": rel_f,
                "status": "BERLEBIH_EXTRA",
                "reason": "Kategori/Folder di luar Whitelist Master 2026"
            })

    total_completed = sum(category_counts.values())
    completion_pct = round((total_completed / TOTAL_MASTER_TARGET) * 100, 1) if TOTAL_MASTER_TARGET > 0 else 0

    category_summary = []
    for cat, target in MASTER_CATEGORY_TARGETS.items():
        actual = category_counts.get(cat, 0)
        pct = round((actual / target) * 100, 1) if target > 0 else 0
        category_summary.append({
            "category": cat,
            "target": target,
            "actual": actual,
            "percentage": pct,
            "isComplete": actual >= target
        })

    report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "totalMasterTarget": TOTAL_MASTER_TARGET,
        "totalCompleted": total_completed,
        "completionPercentage": completion_pct,
        "totalExtraFiles": len(extra_items),
        "categories": category_summary,
        "processedItems": processed_items,
        "extraItems": extra_items
    }

    # Save JSON report
    report_json_path = LOGS_DIR / "master_audit_report.json"
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Save Excel report
    export_excel_report(report)
    
    return report

def export_excel_report(report):
    wb = openpyxl.Workbook()
    header_font = Font(bold=True, color="FFFFFF", size=11)
    green_fill = PatternFill("solid", fgColor="27AE60")
    orange_fill = PatternFill("solid", fgColor="E67E22")
    blue_fill = PatternFill("solid", fgColor="2980B9")

    # Sheet 1: RINGKASAN
    ws1 = wb.active
    ws1.title = "RINGKASAN_MASTER"
    ws1.append(["Kategori Aset", "Target Master", "Realisasi File", "Pencapaian (%)", "Status"])
    for cell in ws1[1]:
        cell.font = header_font; cell.fill = blue_fill; cell.alignment = Alignment(horizontal="center")

    for cat in report["categories"]:
        status = "LENGKAP ✅" if cat["isComplete"] else f"KURANG ({cat['target'] - cat['actual']} File)"
        ws1.append([cat["category"], cat["target"], cat["actual"], f"{cat['percentage']}%", status])

    ws1.append([])
    ws1.append(["TOTAL TARGET MASTER", report["totalMasterTarget"], report["totalCompleted"], f"{report['completionPercentage']}%", "PERAWATAN 2026"])

    # Sheet 2: DETAIL_PER_ASET
    ws_detail = wb.create_sheet("DETAIL_PER_ASET")
    ws_detail.append(["No", "Wilayah (BTP)", "Kategori Aset", "Detail / Identitas Aset", "Status Kelengkapan", "Foto Export", "Foto Edited", "File PDF Merged"])
    for cell in ws_detail[1]:
        cell.font = header_font; cell.fill = green_fill; cell.alignment = Alignment(horizontal="center")

    for idx, item in enumerate(report["processedItems"], 1):
        export_status = "Ada (03)" if item.get("hasExport") else "Tidak"
        edited_status = "Ada (04)" if item.get("hasEdited") else "Tidak"
        pdf_name = item.get("matchedPdf") or "-"
        ws_detail.append([idx, item.get("btp", ""), item.get("category", ""), item.get("detail", ""), item.get("status", ""), export_status, edited_status, pdf_name])

    # Sheet 3: BERLEBIH_EXTRA
    ws2 = wb.create_sheet("BERLEBIH_EXTRA")
    ws2.append(["No", "BTP", "Category", "Detail Aset", "Folder Key", "Alasan Status"])
    for cell in ws2[1]:
        cell.font = header_font; cell.fill = orange_fill; cell.alignment = Alignment(horizontal="center")

    for idx, item in enumerate(report["extraItems"], 1):
        ws2.append([idx, item["btp"], item["category"], item["detail"], item["folderKey"], item["reason"]])

    excel_path = LOGS_DIR / "AUDIT_KELENGKAPAN_MASTER_2026.xlsx"
    wb.save(excel_path)

if __name__ == "__main__":
    res = run_master_audit()
    print(f"Master Audit Done! Completed: {res['totalCompleted']}/{res['totalMasterTarget']} ({res['completionPercentage']}%). Extra items: {res['totalExtraFiles']}")
