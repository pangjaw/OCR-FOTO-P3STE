"""extract_pdf_dates.py — Ekstrak tanggal dari filename PDF 2025 (02_pdf_target)
dan tulis date.txt ke folder foto 03_photos_export.

v3 (2026-07-15): Filename-based matching. Parse date/category/identifier
langsung dari nama file. Pdfplumber fallback untuk format lama.
"""
import argparse
import datetime
import os
import re
from pathlib import Path
from collections import defaultdict

DEFAULT_PDF_DIR = "./02_pdf_target"
DEFAULT_OUTPUT_ROOT = "./03_photos_export"

INDONESIAN_DAYS = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
INDONESIAN_MONTHS = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "Mei", 6: "Jun",
    7: "Jul", 8: "Agt", 9: "Sep", 10: "Okt", 11: "Nov", 12: "Des"
}

# ── Filename category keyword → Export folder category name ──
FILENAME_TO_CATEGORY = {
    "AXLE COUNTER": "AXC",
    "CATU DAYA": "CATUDAYA",
    "PINTU PERLINTASAN": "PINTU_PERLINTASAN",
    "SERAT OPTIK": "SERAT OPTIK",
    "SINYAL": "SINYAL",
    "WESEL": "WESEL",
    "PTPP": "PTPP",
    "CTS": "CTS",
    "PDSE": "PDSE",
    "PTDS": "PTDS",
    "PTLS": "PTLS",
    "TELEKOMUNIKASI": "TELEKOMUNIKASI",
}
# Ordered longest-first for greedy matching
_CATEGORY_KEYWORDS = sorted(FILENAME_TO_CATEGORY.keys(), key=len, reverse=True)

# ── Identifier exceptions (target filename → export folder) ──
IDENTIFIER_EXCEPTIONS = {
    "ZP 41B": "ZP 41",  # Typo in original PDF target
}

# ── Station aliases (filename station → export folder station) ──
STATION_ALIASES = {
    "COS": "CIOMAS",  # Cilebut/Cigombong
    "CIOMAS": "COS",  # reverse
    "ER SINYAL": "ER",  # ER SINYAL CLT -> ER CLT
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
    """Parse date from Indonesian text (fallback for old-format PDFs)."""
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
        try:
            return datetime.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            pass

    # 3. DD-MM-YYYY
    dd_pattern = re.compile(r"(\d{2})-(\d{2})-(\d{4})")
    match = dd_pattern.search(text)
    if match:
        try:
            return datetime.date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
        except ValueError:
            pass

    return None


def format_date_target(dt: datetime.date) -> str:
    day_name = INDONESIAN_DAYS[dt.weekday()]
    month_name = INDONESIAN_MONTHS[dt.month]
    return f"{day_name}, {month_name} {dt.day:02d} {dt.year}"


def parse_date_from_filename(date_str: str) -> datetime.date | None:
    """Parse DD-MM-YYYY string → date object."""
    m = re.match(r'^(\d{2})-(\d{2})-(\d{4})$', date_str)
    if not m:
        return None
    try:
        return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def parse_target_filename(filename: str) -> tuple[str, str, str] | None:
    """Parse 'PERAWATAN TYPE ID STATION DD-MM-YYYY.pdf' → (category, identifier, date_str).
    
    Returns None if filename doesn't match expected format.
    """
    stem = Path(filename).stem  # Remove .pdf
    # Fix double .pdf.pdf
    if stem.lower().endswith('.pdf'):
        stem = stem[:-4]
    # Strip trailing (N) duplicate suffix
    stem = re.sub(r'\s*\(\d+\)\s*$', '', stem)

    # Match: PERAWATAN {asset_part} DD-MM-YYYY
    m = re.match(r'^PERAWATAN\s+(.+?)\s+(\d{2}-\d{2}-\d{4})$', stem)
    if not m:
        return None

    asset_part = m.group(1).strip()
    date_str = m.group(2)

    # Find category keyword (longest match first)
    category = None
    identifier = None
    for kw in _CATEGORY_KEYWORDS:
        if asset_part.startswith(kw + ' '):
            category = FILENAME_TO_CATEGORY[kw]
            identifier = asset_part[len(kw):].strip()
            break

    if not category or not identifier:
        return None

    # Apply identifier exceptions
    for old, new in IDENTIFIER_EXCEPTIONS.items():
        if old in identifier:
            identifier = identifier.replace(old, new)

    return (category, identifier, date_str)


def extract_date_from_pdf(pdf_path) -> datetime.date | None:
    """Fallback: read date from PDF page 1 via pdfplumber."""
    import pdfplumber
    with pdfplumber.open(str(pdf_path)) as pdf:
        if not pdf.pages:
            return None
        for page in pdf.pages:
            text = page.extract_text() or ""
            dt = parse_date_indonesian(text)
            if dt:
                return dt
    return None


def build_folder_lookup(output_root: Path) -> dict[tuple[str, str], list[Path]]:
    """Pre-scan 03_photos_export/ → {(category, identifier): [folder_path]}.
    
    Also adds prefix-based alternate keys for fuzzy matching.
    E.g. folder "JPL 07 BOO-BOP" also gets key "JPL 07 BOO" so filename
    "PERAWATAN SERAT OPTIK JPL 07 BOO ..." can match it.
    """
    lookup = defaultdict(list)
    if not output_root.exists():
        return lookup

    # Station suffixes that funcloc-derived folder names may add
    _STATION_SUFFIXES = ["BOP-BTT", "BOO-BOP", "BJD-CLT", "CLT-BOO", "BOO-CLT",
                         "CCR-MSG", "MSG-BTT", "BTT-MSG", "MSG-CCR", "CLT-BJD"]

    for btp_dir in output_root.iterdir():
        if not btp_dir.is_dir():
            continue
        for cat_dir in btp_dir.iterdir():
            if not cat_dir.is_dir():
                continue
            category = cat_dir.name
            for ident_dir in cat_dir.iterdir():
                if not ident_dir.is_dir():
                    continue
                if any(ident_dir.glob("*.jpg")):
                    key = (category, ident_dir.name)
                    lookup[key].append(ident_dir)

                    # WESEL: strip _DD-MM suffix → also map base identifier
                    # "W13 BOO_02-01" → base "W13 BOO"
                    name = ident_dir.name
                    if category == "WESEL":
                        we_m = re.match(r'^(.+?)_(\d{2}-\d{2})$', name)
                        if we_m:
                            base_name = we_m.group(1)
                            base_key = (category, base_name)
                            if base_key not in lookup:
                                lookup[base_key] = []
                            if ident_dir not in lookup[base_key]:
                                lookup[base_key].append(ident_dir)

                    # Add fuzzy/prefix keys (strip compound station suffixes)
                    # "MJ28 BOP-BTT" -> keys: "MJ28 BOP", "MJ28 BTT", "MJ28"
                    # "JPL 07 BOO-BOP" -> keys: "JPL 07 BOO", "JPL 07 BOP", "JPL 07"
                    for suffix in _STATION_SUFFIXES:
                        if name.endswith(suffix):
                            base = name[:-len(suffix)].strip().rstrip("-").strip()
                            parts = suffix.split("-")
                            if base:
                                # Add each station part as a key
                                for part in parts:
                                    part_key = (category, f"{base} {part}")
                                    if part_key not in lookup:
                                        lookup[part_key] = []
                                    if ident_dir not in lookup[part_key]:
                                        lookup[part_key].append(ident_dir)
                                # Add base-only variant
                                base_key = (category, base)
                                if base_key not in lookup:
                                    lookup[base_key] = []
                                if ident_dir not in lookup[base_key]:
                                    lookup[base_key].append(ident_dir)

                    # Add alias variants (COS <-> CIOMAS etc)
                    for alias_from, alias_to in STATION_ALIASES.items():
                        if alias_from in name:
                            alias_name = name.replace(alias_from, alias_to)
                            alt_key = (category, alias_name)
                            if alt_key not in lookup:
                                lookup[alt_key] = []
                            if ident_dir not in lookup[alt_key]:
                                lookup[alt_key].append(ident_dir)

    return lookup


def _alternate_ids(identifier: str) -> list[str]:
    """Generate alternate identifiers from compound station suffixes.
    
    E.g. 'UB101 BJD-CLT' -> ['UB101 BJD', 'UB101 CLT']
         'JPL 07 BOO-BOP' -> ['JPL 07 BOO', 'JPL 07 BOP']
    """
    alts = []
    parts = identifier.rsplit(" ", 1)
    if len(parts) == 2:
        base, station = parts
        if "-" in station:
            for p in station.split("-"):
                alts.append(f"{base} {p}")
    return alts


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ekstrak tanggal dari filename PDF target → date.txt di folder foto export."
    )
    parser.add_argument("--pdf-dir", default=DEFAULT_PDF_DIR,
                        help=f"Folder PDF target. Default: {DEFAULT_PDF_DIR}")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_ROOT,
                        help=f"Folder root foto export. Default: {DEFAULT_OUTPUT_ROOT}")
    args = parser.parse_args()

    pdf_dir = Path(args.pdf_dir).resolve()
    output_root = Path(args.output_dir).resolve()

    if not pdf_dir.is_dir():
        print(f"[ERROR] Folder PDF '{pdf_dir}' tidak ditemukan.")
        return 1

    # ── Pre-scan folder lookup ──
    print(f"Pre-scan folder lookup dari '{output_root.name}'...")
    folder_lookup = build_folder_lookup(output_root)
    total_folders = sum(len(v) for v in folder_lookup.values())
    print(f"  {len(folder_lookup)} unique identifiers, {total_folders} folder.\n")

    pdf_files = sorted(pdf_dir.rglob("*.pdf"))
    if not pdf_files:
        print(f"Tidak ada PDF di '{pdf_dir}'.")
        return 0

    print(f"Processing {len(pdf_files)} PDF dari '{pdf_dir.name}'...\n")

    updated = 0
    skipped = 0
    fallback_used = 0

    for pdf_path in pdf_files:
        fname = pdf_path.name

        # ── Try filename parsing first ──
        parsed = parse_target_filename(fname)

        if parsed:
            category, identifier, date_str = parsed
            dt = parse_date_from_filename(date_str)
            method = "filename"
        else:
            # ── Fallback: pdfplumber ──
            dt = extract_date_from_pdf(pdf_path)
            category = None
            identifier = None
            method = "pdfplumber"
            fallback_used += 1
            if not dt:
                print(f"  [SKIP] {fname} — tidak bisa parse filename atau PDF")
                skipped += 1
                continue

        formatted = format_date_target(dt)

        if category and identifier:
            # -- Look up folder --
            key = (category, identifier)
            matches = folder_lookup.get(key, [])

            if not matches:
                # -- Try alternate identifiers (compound station) --
                for alt in _alternate_ids(identifier):
                    alt_matches = folder_lookup.get((category, alt), [])
                    if alt_matches:
                        matches = alt_matches
                        break

            if not matches:
                print(f"  [MISS] {fname} -> cat={category} id={identifier} date={formatted} -- folder tidak ditemukan")
                skipped += 1
                continue

            for folder in matches:
                date_file = folder / "date.txt"
                try:
                    if os.environ.get("OVERWRITE", "1") == "0" and date_file.exists():
                        print(f"  [SKIP] {folder.relative_to(output_root)}/date.txt sudah ada")
                        continue
                    date_file.write_text(formatted, encoding="utf-8")
                    rel = folder.relative_to(output_root)
                    print(f"  [OK] {rel}/date.txt -> {formatted} ({method})")
                    updated += 1
                except Exception as e:
                    print(f"  [ERROR] {date_file}: {e}")
        else:
            print(f"  [SKIP] {fname} -- fallback tanpa category/identifier")
            skipped += 1

    print(f"\nSelesai: {updated} date.txt ditulis, {skipped} dilewati, {fallback_used} pakai pdfplumber fallback.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
