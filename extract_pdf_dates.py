"""extract_pdf_dates.py — Ekstrak tanggal dari PDF 2025 (02_pdf_target) dan tulis date.txt
ke folder foto 2026 yang sudah ada di 03_photos_export.

Matching: nama lokasi 2025 → kode stasiun 2026 via STATION_NAME_TO_CODE.
"""
import argparse
import datetime
import os
import re
from pathlib import Path
from collections import defaultdict
import pdfplumber

from export_pdf_foto import (
    ensure_dir, sanitize_segment,
    detect_category_from_filename,
    extract_identifier, extract_funcloc_from_text, extract_all_funclocs,
    STATION_TO_BTP, STATION_NAME_TO_CODE,
)

DEFAULT_PDF_DIR = "./02_pdf_target"
DEFAULT_OUTPUT_ROOT = "./03_photos_export"

INDONESIAN_DAYS = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
INDONESIAN_MONTHS = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "Mei", 6: "Jun",
    7: "Jul", 8: "Agt", 9: "Sep", 10: "Okt", 11: "Nov", 12: "Des"
}

MONTH_MAP = {
    "januari": 1, "jan": 1, "februari": 2, "feb": 2,
    "maret": 3, "mar": 3, "april": 4, "apr": 4,
    "mei": 5, "may": 5, "juni": 6, "jun": 6,
    "juli": 7, "jul": 7, "agustus": 8, "agt": 8, "aug": 8,
    "september": 9, "sep": 9, "oktober": 10, "okt": 10,
    "november": 11, "nov": 11, "desember": 12, "des": 12
}


def parse_date_indonesian(text: str) -> datetime.date | None:
    # 1. DD Bulan YYYY
    pattern = re.compile(
        r"(\d{1,2})\s+(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember|jan|feb|mar|apr|jun|jul|agt|aug|sep|okt|nov|des)\s+(\d{4})",
        re.IGNORECASE
    )
    match = pattern.search(text)
    if match:
        day = int(match.group(1))
        month_str = match.group(2).lower()
        year = int(match.group(3))
        month = MONTH_MAP.get(month_str)
        if month:
            try:
                return datetime.date(year, month, day)
            except ValueError:
                pass

    # 2. YYYY-MM-DD
    iso_pattern = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
    match = iso_pattern.search(text)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        try:
            return datetime.date(year, month, day)
        except ValueError:
            pass

    # 3. DD-MM-YYYY
    dd_pattern = re.compile(r"(\d{2})-(\d{2})-(\d{4})")
    match = dd_pattern.search(text)
    if match:
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3))
        try:
            return datetime.date(year, month, day)
        except ValueError:
            pass

    return None


def format_date_target(dt: datetime.date) -> str:
    day_name = INDONESIAN_DAYS[dt.weekday()]
    month_name = INDONESIAN_MONTHS[dt.month]
    return f"{day_name}, {month_name} {dt.day:02d} {dt.year}"


def extract_date_from_pdf(pdf_path: Path) -> datetime.date | None:
    print(f"Menganalisis tanggal di PDF: {pdf_path.name}...")
    with pdfplumber.open(str(pdf_path)) as pdf:
        if not pdf.pages:
            return None

        first_page = pdf.pages[0]
        text_first = first_page.extract_text() or ""
        dt = parse_date_indonesian(text_first)
        if dt:
            print(f"  [FOUND] Tanggal ditemukan di Halaman 1: {dt} ({format_date_target(dt)})")
            return dt

        for page_idx in range(1, len(pdf.pages)):
            page = pdf.pages[page_idx]
            text = page.extract_text() or ""
            dt = parse_date_indonesian(text)
            if dt:
                print(f"  [FOUND] Tanggal ditemukan di Halaman {page_idx + 1}: {dt} ({format_date_target(dt)})")
                return dt

    return None


def extract_location_from_2025_filename(filename: str) -> str:
    """Extract location name from 2025 PDF filename.
    
    Pattern: DD-MM-YYYY_PERAWATAN_..._Location.pdf
    Location is last underscore-separated segment (minus .pdf).
    Also handles compound locations like BOGOR-BATUTULIS, CIGOMBONG-CICURUG.
    """
    stem = filename.rsplit('.', 1)[0].upper()
    # Remove date prefix: DD-MM-YYYY_
    stem = re.sub(r'^\d{2}-\d{2}-\d{4}_', '', stem)
    # Get last part after final underscore
    parts = stem.rsplit('_', 1)
    if len(parts) == 2:
        loc = parts[1].strip()
        # Remove trailing numbers in parens like (2)
        loc = re.sub(r'\s*\(\d+\)\s*$', '', loc)
        return loc
    return stem


def find_matching_2026_folders(location_name: str, category: str, btp: str,
                                output_root: Path) -> list[Path]:
    """Find 2026 folders matching a 2025 location.
    
    Strategy:
    1. Split compound location (e.g. "BOGOR-BATUTULIS" → ["BOGOR","BATUTULIS"])
    2. Convert each part to station code via STATION_NAME_TO_CODE
    3. Scan output_root/btp/category/ for folders whose stem contains those codes
    """
    parts = [p.strip() for p in location_name.split('-')]
    codes = set()
    for part in parts:
        code = STATION_NAME_TO_CODE.get(part)
        if code:
            codes.add(code)
        # Also add the part itself for Resor-format folders that use full names
        codes.add(part)

    if not codes:
        return []

    category_dir = output_root / sanitize_segment(btp) / category
    if not category_dir.exists():
        return []

    matches = []
    for folder in category_dir.iterdir():
        if not folder.is_dir():
            continue
        stem_upper = folder.name.upper()
        # Match if folder stem contains any of the station codes
        # Use (?:^|[^A-Z0-9]) instead of \b because underscore is a word char in Python
        if any(re.search(r'(?:^|[^A-Z0-9])' + c + r'(?:$|[^A-Z0-9])', stem_upper) for c in codes):
            matches.append(folder)

    return matches


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ekstrak tanggal dari halaman 1 PDF dan simpan ke date.txt di folder foto yg sudah ada."
    )
    parser.add_argument("--pdf-dir", default=DEFAULT_PDF_DIR,
                        help=f"Folder berisi PDF target. Default: {DEFAULT_PDF_DIR}")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_ROOT,
                        help=f"Folder root output foto. Default: {DEFAULT_OUTPUT_ROOT}")
    args = parser.parse_args()

    pdf_dir = Path(args.pdf_dir).resolve()
    output_root = Path(args.output_dir).resolve()

    if not pdf_dir.is_dir():
        print(f"[ERROR] Folder PDF '{pdf_dir}' tidak ditemukan.")
        return 1

    pdf_files = sorted([p for p in pdf_dir.rglob("*")
                        if p.is_file() and p.suffix.lower() == ".pdf"])
    if not pdf_files:
        print(f"Tidak ada file PDF di '{pdf_dir}'.")
        return 0

    print(f"Ditemukan {len(pdf_files)} file PDF di '{pdf_dir.name}'.")

    updated_folders = 0
    skipped_no_match = 0

    for pdf_path in pdf_files:
        dt = extract_date_from_pdf(pdf_path)
        if not dt:
            print(f"  [WARNING] Gagal mengekstrak tanggal dari PDF: {pdf_path.name}")
            continue

        formatted_date = format_date_target(dt)

        # ── Detect category from filename ──
        category = detect_category_from_filename(pdf_path.name)
        print(f"  [INFO] Category={category}")

        # ── Read ALL funclocs from page 1 ──
        MULTI_ROW_CATEGORIES = {"SINYAL", "WESEL", "AXC"}
        identifiers = []
        btp = "BTP JAK"
        with pdfplumber.open(str(pdf_path)) as pdf:
            page1_text = pdf.pages[0].extract_text() or ""
            all_funclocs = extract_all_funclocs(page1_text)
            
            if category in MULTI_ROW_CATEGORIES and all_funclocs:
                # KEL1: extract identifier per funcloc
                for fl in all_funclocs:
                    ident = extract_identifier(fl, category)
                    if ident:
                        identifiers.append(ident)
                        print(f"  [INFO] Funcloc: '{fl.strip()}' -> identifier: '{ident}'")
            elif all_funclocs:
                # KEL2: use first funcloc only
                ident = extract_identifier(all_funclocs[0], category)
                if ident:
                    identifiers.append(ident)
                    print(f"  [INFO] Funcloc: '{all_funclocs[0].strip()}' -> identifier: '{ident}'")
        
        if not identifiers:
            print(f"  [SKIP] Tidak dapat mengekstrak identifier dari Funcloc di: {pdf_path.name}")
            skipped_no_match += 1
            continue

        for identifier in identifiers:
            # ── Determine BTP ──
            if identifier.startswith("JPL "):
                codes = re.findall(r'\b(BOO|CLT|BJD|BOP|BTT|CGB|CS|COS|MSG|CCR)\b', identifier.upper())
                if codes:
                    station = codes[0].upper()
                    if station == "CS": station = "COS"
                    btp = STATION_TO_BTP.get(station, "BTP JAK")
            elif identifier.startswith("ER ") or identifier.startswith("RUANG "):
                parts = identifier.split()
                code = STATION_NAME_TO_CODE.get(parts[-1]) if parts else None
                if not code: code = "BOO"
                if code == "CS": code = "COS"
                btp = STATION_TO_BTP.get(code, "BTP JAK")
            else:
                clean = identifier.replace("RADIO_", "")
                btp = STATION_TO_BTP.get(clean, "BTP JAK")

            # ── Find exact output folder (with BTP cross-search) ──
            target_dir = output_root / sanitize_segment(btp) / category / sanitize_segment(identifier)
            if not target_dir.exists():
                # Cross-search: try all BTP folders
                all_btps = sorted(set(STATION_TO_BTP.values()))
                found = False
                for try_btp in all_btps:
                    candidate = output_root / sanitize_segment(try_btp) / category / sanitize_segment(identifier)
                    if candidate.exists():
                        target_dir = candidate
                        found = True
                        break
                if not found:
                    print(f"  [SKIP] Folder target tidak ditemukan: {target_dir}")
                    skipped_no_match += 1
                    continue

            # Write date.txt
            date_file = target_dir / "date.txt"
            try:
                if os.environ.get("OVERWRITE", "1") == "0" and date_file.exists():
                    print(f"  [SKIP] {target_dir.relative_to(output_root)}/date.txt sudah ada (overwrite=off)")
                    continue
                date_file.write_text(formatted_date, encoding="utf-8")
                print(f"  [UPDATE] {target_dir.relative_to(output_root)}/date.txt -> '{formatted_date}'")
                updated_folders += 1
            except Exception as e:
                print(f"  [ERROR] Gagal menulis ke {date_file}: {e}")

    print(f"\nSelesai. Berhasil memperbarui {updated_folders} file date.txt.")
    if skipped_no_match:
        print(f"  Dilewati karena tidak ada folder match: {skipped_no_match}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
