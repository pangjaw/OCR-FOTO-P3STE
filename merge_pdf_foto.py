def log(msg):
    print(msg, flush=True)
import json
import os
import re
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass
import pdfplumber
import fitz  # PyMuPDF
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from datetime import datetime
import argparse

DEFAULT_INPUT_DIR = "./02_pdf_target"
DEFAULT_PHOTOS_DIR = "./04_photos_edited"
DEFAULT_OUTPUT_DIR = "./05_pdf_merged"
CHECKLIST_CONFIG_PATH = "./checklist_types.json"

@dataclass
class AssetRow:
    page_number: int
    code: str
    title: str
    asset_type: str
    detail: str
    top: float
    station: str = "UNKNOWN"

def load_checklist_config(path: str = CHECKLIST_CONFIG_PATH) -> dict:
    """Load checklist types configuration from JSON file."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        log(f"[WARNING] Checklist config not found at {path}, using defaults")
        return {
            "search_keyword": "PERAWATAN",
            "types": {}
        }

def parse_args():
    parser = argparse.ArgumentParser(
        description="Gabungkan foto hasil edit (format 2026) ke dalam PDF format 2025 asli dengan menghapus kolase lama."
    )
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT_DIR,
        help=f"Folder PDF input 2025. Default: {DEFAULT_INPUT_DIR}",
    )
    parser.add_argument(
        "--photos",
        default=DEFAULT_PHOTOS_DIR,
        help=f"Folder foto hasil edit (Export_Foto). Default: {DEFAULT_PHOTOS_DIR}",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Folder PDF hasil gabung. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--schedule",
        default=None,
        help="Path ke schedule.json untuk lookup Tim folder foto.",
    )
    return parser.parse_args()

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def sanitize_segment(text: str) -> str:
    text = normalize_spaces(text)
    text = "".join("_" if ord(char) < 32 else char for char in text)
    text = re.sub(r'[<>:\\"/\\|?*]', "_", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text or "UNKNOWN"

def detect_asset_type(code: str, title: str) -> str:
    upper = f"{code} {title}".upper()
    if code.startswith("AXL") or "AXLE COUNTER" in upper:
        return "AXC"
    if code.startswith("WSL") or "WESEL" in upper:
        return "WESEL"
    if code.startswith("SIN") or "SINYAL" in upper:
        return "SINYAL"
    if code.startswith("CDA") or "CATU DAYA" in upper:
        return "CATU_DAYA"
    if code.startswith("JPL") or "PINTU PERLINTASAN" in upper:
        return "PINTU_PERLINTASAN"
    if code.startswith("TLK") or code.startswith("TWR") or "TELEKOMUNIKASI" in upper or "RADIO" in upper or "SERAT OPTIK" in upper:
        return "TELEKOMUNIKASI"
    if code.startswith("INB") or code.startswith("TRA") or "PERSINYALAN ELEKTRIK" in upper:
        return "PERSINYALAN_ELEKTRIK"
    return "UNKNOWN"

def extract_detail(title: str, asset_type: str) -> str:
    original = normalize_spaces(title)

    def after(marker: str) -> str | None:
        match = re.search(re.escape(marker), original, flags=re.IGNORECASE)
        if not match:
            return None
        return normalize_spaces(original[match.end() :]).lstrip(": -")

    detail = None
    if asset_type == "AXC":
        detail = after("COUNTER")
    elif asset_type == "WESEL":
        detail = after("ELEKTRIK")
    elif asset_type == "SINYAL":
        detail = after("ELEKTRIK") or after("SINYAL MUKA") or after("SINYAL")
    elif asset_type == "CATU_DAYA":
        detail = after("CATU DAYA") or after("GENSET") or after("UPS") or after("BATTERE") or after("BATT")
    elif asset_type == "PINTU_PERLINTASAN":
        detail = after("PINTU PERLINTASAN") or after("JPL") or after("JPLE") or after("GENTANIK")
    elif asset_type == "TELEKOMUNIKASI":
        detail = after("TELEKOMUNIKASI") or after("TELEPON") or after("RADIO") or after("SERAT OPTIK") or after("OTB")
    elif asset_type == "PERSINYALAN_ELEKTRIK":
        detail = after("PERSINYALAN ELEKTRIK") or after("DALAM PERSINYALAN") or after("OTB") or after("BANGUNAN")

    if not detail:
        detail = original

    sanitized = sanitize_segment(detail)
    # Workaround: ZP 41B -> ZP 41 (karena typo di PDF 2025 asli)
    if "ZP 41B" in sanitized.upper() or "ZP41B" in sanitized.upper():
        sanitized = re.sub(r'ZP\s*41B', 'ZP 41', sanitized, flags=re.IGNORECASE)
    return sanitized

def extract_station_from_detail(detail: str) -> str:
    """Extract station code from detail string (e.g., 'ZP 60 BOO' -> 'BOO')."""
    station_codes = {"BOO", "BOP", "BTT", "CLT", "MSG", "CGB", "BJD", "CCR", "COS", "CS", "BNR"}
    words = normalize_spaces(detail).split()
    for word in reversed(words):
        if word in station_codes:
            return word
    return "UNKNOWN"

def is_valid_asset_title(title: str) -> bool:
    words = title.split()
    code_pattern = re.compile(r"^[A-Z]{2,4}\d{4,}$")
    if all(code_pattern.match(w) for w in words):
        return False
    upper = title.upper()
    valid_keywords = ["AXLE", "COUNTER", "WESEL", "SINYAL", "CATU DAYA", "PINTU PERLINTASAN", "TELEKOMUNIKASI", "PERSINYALAN ELEKTRIK", "JPL", "GENTANIK", "RADIO", "SERAT OPTIK", "OTB", "BANGUNAN", "GENSET", "UPS", "BATTERE", "PANEL", "RECTIFIER", "MESIN", "MOTOR", "TOWER", "ANTENA", "INTERLOCKING", "INPUT"]
    if any(kw in upper for kw in valid_keywords):
        return True
    return False

def extract_asset_rows(page: pdfplumber.page.Page) -> list[AssetRow]:
    lines = defaultdict(list)
    for word in page.extract_words(use_text_flow=True):
        lines[round(float(word["top"]), 1)].append(word)

    rows = []
    code_pattern = re.compile(r"^[A-Z]{2,4}\d{4,}$")

    for top in sorted(lines):
        words = sorted(lines[top], key=lambda w: float(w["x0"]))
        code_index = None
        code = None
        for idx, word in enumerate(words):
            if code_pattern.match(word["text"]):
                code_index = idx
                code = word["text"]
                break
        if code_index is None or not code:
            continue

        title = normalize_spaces(" ".join(word["text"] for word in words[code_index + 1 :])).lstrip(": -")
        if not title:
            continue

        if not is_valid_asset_title(title):
            continue

        asset_type = detect_asset_type(code, title)
        detail = extract_detail(title, asset_type)
        station = extract_station_from_detail(detail)
        rows.append(
            AssetRow(
                page_number=page.page_number,
                code=code,
                title=title,
                asset_type=asset_type,
                detail=detail,
                top=top,
                station=station,
            )
        )

    return rows

def extract_location_from_filename(filename: str) -> str:
    name_without_ext = filename.rsplit('.', 1)[0]
    parts = name_without_ext.split('_')
    if len(parts) >= 3:
        location_part = parts[2].strip()
        location_part = re.sub(r'\s*\(\d+\)\s*$', '', location_part)
        return location_part.upper()
    return "BOGOR"

def extract_date_from_page1(page: pdfplumber.page.Page) -> str:
    text = page.extract_text() or ""
    date_pattern = re.compile(r"Tanggal\s*:\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE)
    match = date_pattern.search(text)

    months_id = {
        1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
        5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
        9: "September", 10: "Oktober", 11: "November", 12: "Desember"
    }

    if match:
        date_str = match.group(1)
        y, m, d = map(int, date_str.split('-'))
        return f"{d:02d} {months_id[m]} {y}"

    return "06 Januari 2025" # default fallback

def extract_checklist_title(page: pdfplumber.page.Page, filename: str, config: dict | None = None) -> str:
    """
    Ekstrak judul ceklis dari halaman 1 PDF.
    Prioritas: 1) OCR halaman 1 dengan keyword dari config
               2) Validasi hasil terhadap known types di config
               3) Fallback ke parsing filename
               4) Default hardcoded
    """
    if config is None:
        config = load_checklist_config()

    search_keyword = config.get("search_keyword", "PERAWATAN")
    known_types = config.get("types", {})

    text = page.extract_text() or ""
    for line in text.split('\n'):
        line_clean = normalize_spaces(line)
        if search_keyword in line_clean.upper():
            if line_clean.upper().startswith("STE"):
                line_clean = line_clean[3:].strip()
            extracted = line_clean.upper()

            # Validasi: cek apakah hasil ekstraksi cocok dengan known type
            for known_type in known_types:
                if known_type in extracted or extracted in known_type:
                    return known_type

            # Jika tidak cocok tapi mengandung keyword, return hasil OCR
            return extracted

    # Fallback: parse dari filename
    name_without_ext = filename.rsplit('.', 1)[0]
    parts = name_without_ext.split('_')
    if len(parts) >= 2:
        filename_type = parts[1].strip().upper()

        # Validasi filename type against known types
        for known_type in known_types:
            if known_type in filename_type or filename_type in known_type:
                return known_type

        return filename_type

    return "PERAWATAN AXLE COUNTER SIEMENS 1 BULANAN"

def get_text_width(text: str, fontname: str, fontsize: float) -> float:
    return fitz.get_text_length(text, fontname=fontname, fontsize=fontsize)

def draw_centered_text(page, text: str, y_baseline: float, fontname: str, fontsize: float):
    w = get_text_width(text, fontname, fontsize)
    x = (page.rect.width - w) / 2
    page.insert_text((x, y_baseline), text, fontname=fontname, fontsize=fontsize, color=(0, 0, 0))

def draw_centered_label(page, text: str, img_x0: float, img_x1: float, y_baseline: float, fontname: str, fontsize: float):
    w = get_text_width(text, fontname, fontsize)
    center_img = (img_x0 + img_x1) / 2
    x = center_img - w / 2
    page.insert_text((x, y_baseline), text, fontname=fontname, fontsize=fontsize, color=(0, 0, 0))

def draw_header(page, location: str, date_str: str, checklist_title: str):
    draw_centered_text(page, "FOTO DOKUMENTASI", 38.9, "hebo", 7.2)
    draw_centered_text(page, f"{checklist_title} {location}", 53.3, "hebo", 7.2)
    draw_centered_text(page, date_str, 67.7, "hebo", 7.2)

def process_pdf(pdf_path: Path, photos_dir: Path, output_dir: Path,
                 input_root: Path | None = None, schedule_lookup: dict | None = None,
                 asset_tim: dict | None = None, config: dict | None = None) -> str:
    """
    Gabungkan foto-foto baru ke dalam PDF lama.
    Args:
        schedule_lookup: {pdf_name: tim} from schedule.json (PDF-level Tim)
        asset_tim: {(asset_type, detail): tim} from tim_mapping.json fallback (asset-level Tim)
    """
    if config is None:
        config = load_checklist_config()

    # 1. Buka dengan pdfplumber untuk mencari daftar aset
    with pdfplumber.open(str(pdf_path)) as plumber_pdf:
        if len(plumber_pdf.pages) == 0:
            return "failed: PDF has 0 pages"
        page1 = plumber_pdf.pages[0]
        assets = extract_asset_rows(page1)
        date_str = extract_date_from_page1(page1)
        checklist_title = extract_checklist_title(page1, pdf_path.name, config)

    if not assets:
        return "failed: no assets found on page 1"

    location = extract_location_from_filename(pdf_path.name)

    # 2. Periksa apakah foto lengkap
    missing_assets = []
    asset_photo_paths = {}

    # Dukungan subfolder aset
    subfolder = Path()
    if input_root and pdf_path.is_relative_to(input_root):
        subfolder = pdf_path.parent.relative_to(input_root)

    # Determine photo lookup base directory
    # Priority: schedule_lookup (PDF-level) > asset_tim (asset-level) > default
    pdf_tim = None
    use_asset_tim = False
    if schedule_lookup is not None:
        pdf_tim = schedule_lookup.get(pdf_path.name)
        if pdf_tim:
            log(f"    [SCHEDULE] PDF {pdf_path.name}] Tim {pdf_tim}")
    if pdf_tim is None and asset_tim is not None:
        use_asset_tim = True
        log(f"    [FALLBACK] Using asset-level Tim mapping for {pdf_path.name}")

    for r in assets:
        asset_key = (r.asset_type, r.detail)

        # Determine Tim for this specific asset
        if use_asset_tim:
            # Use asset-level Tim mapping
            tim = asset_tim.get(asset_key, 1)
            photo_lookup_dir = photos_dir / f"Tim_{tim}"
        elif pdf_tim:
            # Use PDF-level Tim from schedule
            photo_lookup_dir = photos_dir / f"Tim_{pdf_tim}"
        else:
            # Default: no Tim subfolder
            photo_lookup_dir = photos_dir

        # Build folder path: photos_dir/Tim_N/station/asset_type/detail/ or photos_dir/subfolder/station/asset_type/detail/
        # New structure: station/asset_type/detail/
        if pdf_tim or use_asset_tim:
            folder_detail = photo_lookup_dir / sanitize_segment(r.station) / sanitize_segment(r.asset_type) / r.detail
        else:
            folder_detail = photo_lookup_dir / subfolder / sanitize_segment(r.station) / sanitize_segment(r.asset_type) / r.detail

        # Validasi 3 foto
        f0 = folder_detail / "0.jpg"
        f50 = folder_detail / "50.jpg"
        f100 = folder_detail / "100.jpg"

        if not (f0.is_file() and f50.is_file() and f100.is_file()):
            missing_assets.append(r.detail)
        else:
            asset_photo_paths[r.detail] = (f0, f50, f100)

    if missing_assets:
        return f"skipped: missing photos for assets: {', '.join(missing_assets)}"

    # 3. Lakukan modifikasi menggunakan PyMuPDF
    doc = fitz.open(str(pdf_path))

    # Hapus halaman terakhir (halaman kolase lama)
    if len(doc) > 0:
        doc.delete_page(-1)

    # Buat halaman-halaman foto baru
    assets_per_page = 4
    for i, r in enumerate(assets):
        page_idx = i // assets_per_page
        asset_idx_on_page = i % assets_per_page

        # Jika baris pertama pada halaman, buat halaman baru
        if asset_idx_on_page == 0:
            page = doc.new_page(width=595, height=842)
            draw_header(page, location, date_str, checklist_title)

        # Dapatkan referensi halaman aktif
        page = doc[-1]

        # Gambar baris aset
        y_title_base = 82.1 + asset_idx_on_page * 183
        title_text = f"{r.code} : {r.title}"
        page.insert_text((31.5, y_title_base), title_text, fontname="helv", fontsize=7.2, color=(0, 0, 0))

        # Tempel foto
        y_img_top = 89.1 + asset_idx_on_page * 183
        y_img_bottom = y_img_top + 148.8

        f0_path, f50_path, f100_path = asset_photo_paths[r.detail]

        # Kolom 1 (0%)
        rect_col0 = fitz.Rect(31.5, y_img_top, 180.3, y_img_bottom)
        page.insert_image(rect_col0, filename=str(f0_path))

        # Kolom 2 (50%)
        rect_col1 = fitz.Rect(210.4, y_img_top, 359.2, y_img_bottom)
        page.insert_image(rect_col1, filename=str(f50_path))

        # Kolom 3 (100%)
        rect_col2 = fitz.Rect(389.8, y_img_top, 538.6, y_img_bottom)
        page.insert_image(rect_col2, filename=str(f100_path))

        # Gambar label di bawah foto
        y_label_base = 251.3 + asset_idx_on_page * 183
        draw_centered_label(page, "Foto 0%", 31.5, 180.3, y_label_base, "helv", 7.2)
        draw_centered_label(page, "Foto 50%", 210.4, 359.2, y_label_base, "helv", 7.2)
        draw_centered_label(page, "Foto 100%", 389.8, 538.6, y_label_base, "helv", 7.2)

    # Simpan berkas hasil gabung
    # Determine output subfolder: if using Tim mapping, save to Tim_N/
    if pdf_tim or use_asset_tim:
        # For fallback with asset_tim, determine the majority Tim for this PDF
        if use_asset_tim:
            # Collect tims for all assets in this PDF
            pdf_tims = []
            for r in assets:
                asset_key = (r.asset_type, r.detail)
                t = asset_tim.get(asset_key, 1)
                pdf_tims.append(t)
            if pdf_tims:
                # Use most common tim
                out_tim = max(set(pdf_tims), key=pdf_tims.count)
            else:
                out_tim = 1
        else:
            out_tim = pdf_tim
        out_pdf_path = output_dir / f"Tim_{out_tim}" / subfolder / pdf_path.name
    else:
        out_pdf_path = output_dir / subfolder / pdf_path.name

    ensure_dir(out_pdf_path.parent)

    if os.environ.get("OVERWRITE", "1") == "0" and out_pdf_path.exists():
        doc.close()
        return f"skipped: {out_pdf_path.name} sudah ada (overwrite=off)"

    doc.save(str(out_pdf_path))
    doc.close()

    return "ok"


def aggregate_photo_to_pdf(tim_mapping: dict, photos_dir: Path) -> dict:
    """
    Aggregate photo->Tim mapping to PDF->Tim mapping.

    For each PDF in input_dir, determine which assets it contains,
    then check the Tim of their photos via tim_mapping.
    If all photos for a PDF have the same Tim, use that Tim.
    """
    from collections import defaultdict

    # Build reverse index: asset_type/detail -> list of photo relative paths
    asset_photos = defaultdict(list)
    for rel_path, tim_n in tim_mapping.items():
        # rel_path format: "station/AXC/ZP 60 BOO/0.jpg"
        parts = rel_path.split("/")
        if len(parts) >= 4:
            station, asset_type, detail, photo_name = parts[0], parts[1], parts[2], parts[3]
            asset_photos[(asset_type, detail)].append((rel_path, tim_n))

    # Build asset_key -> tim mapping (most common tim for that asset)
    asset_tim = {}
    for (asset_type, detail), photos in asset_photos.items():
        if photos:
            # Get most common tim for this asset
            tims = [tim for _, tim in photos]
            most_common_tim = max(set(tims), key=tims.count)
            asset_tim[(asset_type, detail)] = most_common_tim

    return asset_tim


def main():
    args = parse_args()
    input_dir = Path(args.input).resolve()
    photos_dir = Path(args.photos).resolve()
    output_dir = Path(args.output).resolve()

    if not input_dir.is_dir():
        print(f"Folder input tidak ditemukan: {input_dir}")
        return 1
    if not photos_dir.is_dir():
        print(f"Folder foto hasil edit tidak ditemukan: {photos_dir}")
        return 1

    ensure_dir(output_dir)

    pdf_files = sorted([p for p in input_dir.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf"])
    if not pdf_files:
        print(f"Tidak ada berkas PDF di: {input_dir}")
        return 0

    # Load schedule if provided
    schedule_lookup = None
    tim_mapping = None
    if args.schedule:
        sched_path = Path(args.schedule)
        if not sched_path.exists():
            print(f"[ERROR] Schedule file not found: {sched_path}")
            return 1
        with open(sched_path, encoding="utf-8") as f:
            sched_data = json.load(f)
        schedule_lookup = {e["file"]: e["tim"] for e in sched_data.get("schedules", [])}
        print(f"[SCHEDULE] Loaded {len(schedule_lookup)} file->Tim mappings.")
    else:
        # Fallback: try to load tim_mapping.json from logs/
        tim_mapping_path = Path("logs/tim_mapping.json")
        if tim_mapping_path.exists():
            with open(tim_mapping_path, encoding="utf-8") as f:
                tim_mapping_data = json.load(f)
            tim_mapping = tim_mapping_data.get("mapping", {})
            print(f"[FALLBACK] Loaded tim_mapping.json with {len(tim_mapping)} photo->Tim mappings.")
            # Aggregate photo->Tim to PDF->Tim
            schedule_lookup = aggregate_photo_to_pdf(tim_mapping, photos_dir)
            print(f"[FALLBACK] Aggregated to {len(schedule_lookup)} PDF->Tim mappings.")
        else:
            print("[ERROR] No --schedule provided and logs/tim_mapping.json not found.")
            print("         Run edit_timemark with --schedule first, or provide --schedule to merge_pdf_foto.")
            return 1

    log(f"Mulai pemrosesan {len(pdf_files)} berkas PDF...")
    log(f"Input:  {input_dir}")
    log(f"Photos: {photos_dir}")
    log(f"Output: {output_dir}\n")

    success = 0
    skipped = 0
    failed = 0
    failed_files = []
    skipped_files = []

    # Determine which mapping to pass to process_pdf
    # If using schedule directly: schedule_lookup = {pdf: tim}, asset_tim = None
    # If using fallback: schedule_lookup = {pdf: tim} (aggregated), asset_tim = {asset_key: tim}
    asset_tim_for_fallback = tim_mapping if not args.schedule else None

    for pdf_path in pdf_files:
        status = process_pdf(pdf_path, photos_dir, output_dir, input_dir, schedule_lookup, asset_tim_for_fallback)
        if status == "ok":
            success += 1
            log(f"[OK] {pdf_path.name}")
        elif status.startswith("skipped"):
            skipped += 1
            skipped_files.append({
                "file": pdf_path.name,
                "reason": status,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            log(f"[SKIP] {pdf_path.name} - {status}")
        else:
            failed += 1
            failed_files.append({
                "file": pdf_path.name,
                "reason": status,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            log(f"[FAIL] {pdf_path.name} - {status}")

    # Export Excel files
    logs_dir = Path("logs")
    ensure_dir(logs_dir)

    if failed_files:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Failed Files"
        headers = ["File PDF", "Alasan", "Timestamp"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="FF4444", end_color="FF4444", fill_type="solid")
            cell.font = Font(bold=True, color="FFFFFF")
        for row_idx, item in enumerate(failed_files, 2):
            ws.cell(row=row_idx, column=1, value=item["file"])
            ws.cell(row=row_idx, column=2, value=item["reason"])
            ws.cell(row=row_idx, column=3, value=item["timestamp"])
        # Auto-fit columns
        for col in ws.columns:
            max_length = max(len(str(cell.value)) if cell.value else 0 for cell in col)
            ws.column_dimensions[col[0].column_letter].width = max_length + 2
        wb.save(logs_dir / "merge_failed.xlsx")
        log(f"[EXPORT] Failed files saved to logs/merge_failed.xlsx ({len(failed_files)} items)")

    if skipped_files:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Skipped Files"
        headers = ["File PDF", "Alasan", "Timestamp"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="FFA500", end_color="FFA500", fill_type="solid")
            cell.font = Font(bold=True, color="FFFFFF")
        for row_idx, item in enumerate(skipped_files, 2):
            ws.cell(row=row_idx, column=1, value=item["file"])
            ws.cell(row=row_idx, column=2, value=item["reason"])
            ws.cell(row=row_idx, column=3, value=item["timestamp"])
        for col in ws.columns:
            max_length = max(len(str(cell.value)) if cell.value else 0 for cell in col)
            ws.column_dimensions[col[0].column_letter].width = max_length + 2
        wb.save(logs_dir / "merge_skipped.xlsx")
        log(f"[EXPORT] Skipped files saved to logs/merge_skipped.xlsx ({len(skipped_files)} items)")

    # Print summary JSON for app.py to capture
    import sys
    summary = {
        "step": "merge",
        "success": success,
        "failed": failed,
        "skipped": skipped,
        "failed_file": "logs/merge_failed.xlsx" if failed_files else None,
        "skipped_file": "logs/merge_skipped.xlsx" if skipped_files else None
    }
    print(f"__SUMMARY__:{json.dumps(summary)}", flush=True)

    log(f"\nSelesai. Sukses: {success}, Dilewati: {skipped}, Gagal: {failed}.")
    return 0 if success > 0 or skipped > 0 else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
