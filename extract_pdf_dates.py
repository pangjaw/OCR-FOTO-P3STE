import argparse
import datetime
import os
import re
from pathlib import Path
import pdfplumber

from export_pdf_foto import (
    extract_asset_rows,
    asset_output_dir,
    ensure_dir,
    sanitize_segment,
    load_sap_mapping,
    SAP_MAPPING_PATH
)

DEFAULT_PDF_IMO_DIR = "./02_pdf_target"
DEFAULT_OUTPUT_ROOT = "./03_photos_export"

INDONESIAN_DAYS = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
INDONESIAN_MONTHS = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "Mei", 6: "Jun",
    7: "Jul", 8: "Agt", 9: "Sep", 10: "Okt", 11: "Nov", 12: "Des"
}

MONTH_MAP = {
    "januari": 1, "jan": 1,
    "februari": 2, "feb": 2,
    "maret": 3, "mar": 3,
    "april": 4, "apr": 4,
    "mei": 5, "may": 5,
    "juni": 6, "jun": 6,
    "juli": 7, "jul": 7,
    "agustus": 8, "agt": 8, "aug": 8,
    "september": 9, "sep": 9,
    "oktober": 10, "okt": 10,
    "november": 11, "nov": 11,
    "desember": 12, "des": 12
}


def parse_date_indonesian(text: str) -> datetime.date | None:
    # 1. Cari pola: DD [Bulan] YYYY (misal: 17 Juni 2026 atau 01 Mei 2026)
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

    # 2. Cari pola ISO: YYYY-MM-DD (misal: 2026-06-17)
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

    # 3. Cari pola: DD-MM-YYYY (misal: 17-06-2026)
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
            
        # Prioritas Utama: Halaman Pertama (halaman 1)
        first_page = pdf.pages[0]
        text_first = first_page.extract_text() or ""
        dt = parse_date_indonesian(text_first)
        if dt:
            print(f"  [FOUND] Tanggal ditemukan di Halaman 1: {dt} ({format_date_target(dt)})")
            return dt
            
        # Fallback: Cari di halaman-halaman berikutnya dari depan ke belakang
        for page_idx in range(1, len(pdf.pages)):
            page = pdf.pages[page_idx]
            text = page.extract_text() or ""
            dt = parse_date_indonesian(text)
            if dt:
                print(f"  [FOUND] Tanggal ditemukan di Halaman {page_idx + 1}: {dt} ({format_date_target(dt)})")
                return dt

    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ekstrak tanggal dari halaman foto PDF di folder 02_pdf_target dan simpan ke date.txt di subfolder 03_photos_export/."
    )
    parser.add_argument(
        "--pdf-dir",
        default=DEFAULT_PDF_IMO_DIR,
        help=f"Folder berisi PDF target. Default: {DEFAULT_PDF_IMO_DIR}"
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_ROOT,
        help=f"Folder root tempat penyimpanan foto hasil ekspor. Default: {DEFAULT_OUTPUT_ROOT}"
    )
    args = parser.parse_args()

    pdf_dir = Path(args.pdf_dir).resolve()
    output_root = Path(args.output_dir).resolve()

    if not pdf_dir.is_dir():
        print(f"[ERROR] Folder PDF '{pdf_dir}' tidak ditemukan.")
        return 1

    pdf_files = sorted([p for p in pdf_dir.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf"])
    if not pdf_files:
        print(f"Tidak ada file PDF di '{pdf_dir}'.")
        return 0

    print(f"Ditemukan {len(pdf_files)} file PDF di '{pdf_dir.name}'.")
    
    updated_folders = 0

    for pdf_path in pdf_files:
        dt = extract_date_from_pdf(pdf_path)
        if not dt:
            print(f"  [WARNING] Gagal mengekstrak tanggal dari PDF: {pdf_path.name}")
            continue

        formatted_date = format_date_target(dt)

        # Load SAP mapping for station lookup
        sap_mapping = load_sap_mapping(SAP_MAPPING_PATH)

        # Cari seluruh aset di PDF ini untuk memperbarui date.txt di foldernya
        with pdfplumber.open(str(pdf_path)) as pdf:
            pdf_assets = []

            for page in pdf.pages:
                rows = extract_asset_rows(page, sap_mapping)
                for r in rows:
                    # New signature: asset_output_dir(root, station, asset_type, detail)
                    out_dir = asset_output_dir(output_root, r.station, r.asset_type, r.detail)
                    ensure_dir(out_dir)
                    pdf_assets.append((r.code, r.detail, out_dir))

            if not pdf_assets:
                print(f"  [WARNING] Tidak ada aset yang ditemukan di PDF ini.")
                continue

            # Tulis date.txt ke folder aset yang ditemukan
            # Gunakan set untuk menghindari duplikasi folder jika satu aset memiliki beberapa baris
            unique_dirs = set(d for _, _, d in pdf_assets)
            for out_dir in unique_dirs:
                date_file = out_dir / "date.txt"
                try:
                    if os.environ.get("OVERWRITE", "1") == "0" and date_file.exists():
                        print(f"  [SKIP] {out_dir.relative_to(output_root)}/date.txt sudah ada (overwrite=off)")
                        continue
                    date_file.write_text(formatted_date, encoding="utf-8")
                    print(f"  [UPDATE] {out_dir.relative_to(output_root)}/date.txt -> '{formatted_date}'")
                    updated_folders += 1
                except Exception as e:
                    print(f"  [ERROR] Gagal menulis ke {date_file}: {e}")

    print(f"\nSelesai. Berhasil memperbarui {updated_folders} file date.txt di folder aset.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
