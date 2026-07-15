#!/usr/bin/env python3
"""scheduler.py — Generate schedule.json: urutan PDF → Tim + jam.

Pipeline: export_pdf_foto → extract_pdf_dates → scheduler.py → edit_timemark → merge_pdf_foto

Schedule key: (btp, category, pdf_stem, photo) — flat structure.
"""

import argparse
import json
import os
import re
from pathlib import Path
from datetime import datetime, date, timedelta

import pdfplumber

from export_pdf_foto import (
    sanitize_segment, ensure_dir, load_sap_mapping, SAP_MAPPING_PATH,
    detect_category_from_filename, extract_station_from_filename, STATION_TO_BTP,
    extract_identifier, extract_funcloc_from_text, extract_all_funclocs,
)
from extract_pdf_dates import extract_date_from_pdf, format_date_target

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

MONTH_MAP = {
    "januari": 1, "jan": 1, "februari": 2, "feb": 2,
    "maret": 3, "mar": 3, "april": 4, "apr": 4,
    "mei": 5, "may": 5, "juni": 6, "jun": 6,
    "juli": 7, "jul": 7, "agustus": 8, "agt": 8, "aug": 8,
    "september": 9, "sep": 9, "oktober": 10, "okt": 10,
    "november": 11, "nov": 11, "desember": 12, "des": 12,
}

# Default waktu (minutes) per category
CATEGORY_DEFAULT_WAKTU = {
    "AXC": 45,
    "CATUDAYA": 45,
    "CTS": 45,
    "JPL": 45,
    "PDSE": 420,
    "PTDS": 45,
    "PTLS": 45,
    "PTPP": 45,
    "SERAT OPTIK": 60,
    "SINYAL": 30,
    "WESEL": 30,
}


def _parse_date(text: str) -> date | None:
    """Parse date string from date.txt format 'Senin, Jan 06 2025' or ISO."""
    text = re.sub(r'^[A-Za-z]+,\s*', '', text).strip()
    m = re.match(
        r"(jan|feb|mar|apr|mei|jun|jul|agt|aug|sep|okt|nov|des|"
        r"januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)"
        r"\s+(\d{1,2})\s+(\d{4})",
        text, re.IGNORECASE,
    )
    if m:
        month = MONTH_MAP.get(m.group(1).lower())
        day = int(m.group(2))
        year = int(m.group(3))
        if month:
            try:
                return date(year, month, day)
            except ValueError:
                pass
    # ISO: YYYY-MM-DD
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    return None


def load_mapping(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    result = {}
    for asset_type, details in data.items():
        if asset_type.startswith("_"):
            continue
        for detail, info in details.items():
            if detail.startswith("_"):
                continue
            result[(asset_type, detail)] = info["asset_id"]
    return result


def load_data_acuan(path: Path) -> dict[int, dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {a["id"]: a for a in data["aset"]}


def get_waktu(category: str, mapping: dict, acuan: dict) -> int:
    """Get waktu in minutes for a category. Try mapping first, then default."""
    # Try lookup via category in mapping
    for (asset_type, detail), asset_id in mapping.items():
        if category in asset_type or category in detail:
            if asset_id in acuan:
                return acuan[asset_id]["waktu_menit"]
    # Default per category
    return CATEGORY_DEFAULT_WAKTU.get(category, 45)


def read_date_from_photos(photos_dir: Path, btp: str, category: str, identifier: str) -> str | None:
    """Read date.txt from flat output structure."""
    fp = photos_dir / sanitize_segment(btp) / category / sanitize_segment(identifier) / "date.txt"
    if fp.exists():
        return fp.read_text(encoding="utf-8").strip()
    return None


def m2hhmm(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def m2iso(d: date, m: int) -> str:
    return datetime(d.year, d.month, d.day, m // 60, m % 60).isoformat()


def is_serat_optik_pdf(pdf_path: Path) -> bool:
    return "SERAT OPTIK" in pdf_path.parts or "OPTIK" in pdf_path.parts


def extract_core_count(doc) -> int | None:
    if not doc.pages:
        return None
    text = doc.pages[0].extract_text() or ""
    m = re.search(r'Jumlah Core[^\d]*(\d+)', text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def _determine_btp(identifier: str, pdf_path: Path) -> str:
    """Determine BTP from identifier or pdf path."""
    if identifier.startswith("JPL "):
        codes = re.findall(r'\b(BOO|CLT|BJD|BOP|BTT|CGB|CS|COS|MSG|CCR)\b', identifier.upper())
        if codes:
            station = codes[0].upper()
            if station == "CS": station = "COS"
            return STATION_TO_BTP.get(station, "BTP JAK")
    elif identifier.startswith("ER ") or identifier.startswith("RUANG "):
        parts = identifier.split()
        code = None
        for kw in ["BOO", "BTT", "CLT", "BOP", "CGB", "COS", "MSG"]:
            if kw in parts:
                code = kw
                break
        if not code: code = "BOO"
        return STATION_TO_BTP.get(code, "BTP JAK")
    else:
        codes = re.findall(r'\b(BOO|CLT|BJD|BOP|BTT|CGB|CS|COS|MSG|CCR)\b', identifier.upper())
        if codes:
            station = codes[-1].upper()
            if station == "CS": station = "COS"
            return STATION_TO_BTP.get(station, "BTP JAK")
        clean = identifier.replace("RADIO_", "")
        return STATION_TO_BTP.get(clean, "BTP JAK")
    return "BTP JAK"


# Categories where each funcloc = separate folder with own 3 photos
MULTI_ROW_CATEGORIES = {"SINYAL", "WESEL", "AXC"}


def build_schedule(pdf_dir: Path, photos_dir: Path,
                   mapping: dict, acuan: dict,
                   jam_mulai: int, jam_selesai: int, tim_max: int) -> dict:
    files = sorted(p for p in pdf_dir.rglob("*")
                   if p.is_file() and p.suffix.lower() == ".pdf")
    if not files:
        return {"version": 1, "schedules": []}

    schedules = []
    tim = 1
    cur_date: date | None = None
    clock = jam_mulai  # minutes from midnight

    for pdf_path in files:
        # ── Detect category ──
        category = detect_category_from_filename(pdf_path.name)
        
        # ── Read ALL funclocs from page 1 ──
        all_funclocs: list[str] = []
        page1_text = ""
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                if pdf.pages:
                    page1_text = pdf.pages[0].extract_text() or ""
                    all_funclocs = extract_all_funclocs(page1_text)
        except Exception:
            pass

        # ── Core count for SERAT OPTIK ──
        core_count = None
        if is_serat_optik_pdf(pdf_path):
            try:
                with pdfplumber.open(str(pdf_path)) as doc:
                    core_count = extract_core_count(doc)
                    if core_count:
                        print(f"  [SERAT OPTIK] {pdf_path.name}: {core_count} core -> {core_count * 6} min")
            except Exception:
                pass

        # ── Build identifier list per category ──
        # KEL1: multi-funcloc → one entry per funcloc
        # KEL2: single identifier → one entry per PDF
        if category in MULTI_ROW_CATEGORIES and len(all_funclocs) > 1:
            identifiers = []
            for fl in all_funclocs:
                ident = extract_identifier(fl, category)
                if ident:
                    identifiers.append(ident)
            # Deduplicate preserving order
            seen = set()
            unique = []
            for ident in identifiers:
                if ident not in seen:
                    seen.add(ident)
                    unique.append(ident)
            identifiers = unique
        else:
            # KEL2: single identifier
            ident = None
            if all_funclocs:
                ident = extract_identifier(all_funclocs[0], category)
            if not ident:
                station = extract_station_from_filename(pdf_path.name)
                if station:
                    ident = station
                    if "RADIO" in page1_text.upper() and ident == "BOO":
                        ident = "RADIO_BOO"
                else:
                    ident = pdf_path.stem
            identifiers = [ident]

        # ── Per-identifier scheduling ──
        for identifier in identifiers:
            btp = _determine_btp(identifier, pdf_path)

            # ── Determine date ──
            date_str = read_date_from_photos(photos_dir, btp, category, identifier)
            pdf_date: date | None = None

            if not date_str:
                d = extract_date_from_pdf(pdf_path)
                if d:
                    pdf_date = d
                    date_str = format_date_target(d)

            if not date_str:
                print(f"  [SKIP] no date found for {pdf_path.name} / {identifier}")
                continue

            if pdf_date is None:
                pdf_date = _parse_date(date_str)
            if pdf_date is None:
                print(f"  [SKIP] cannot parse date '{date_str}' for {pdf_path.name}")
                continue

            # ── Date boundary → reset ──
            if pdf_date != cur_date:
                cur_date = pdf_date
                tim = 1
                clock = jam_mulai

            # ── Waktu per entry ──
            if core_count:
                w = core_count * 6
            else:
                w = get_waktu(category, mapping, acuan)

            # ── Overflow check ──
            if clock >= jam_selesai or (clock + w > jam_selesai and clock != jam_mulai):
                tim += 1
                if tim > tim_max:
                    tim = 1
                    cur_date = pdf_date + timedelta(days=1)
                    date_str = format_date_target(cur_date)
                clock = jam_mulai

            # ── Assign times ──
            t0 = clock
            t50 = round(clock + w / 2)
            t100 = clock + w

            entry = {
                "file": pdf_path.name,
                "btp": btp,
                "category": category,
                "pdf_stem": pdf_path.stem,
                "identifier": identifier,
                "date": date_str,
                "tim": tim,
                "waktu_menit": w,
                "photos": {
                    "0.jpg":  m2iso(cur_date, t0),
                    "50.jpg": m2iso(cur_date, t50),
                    "100.jpg": m2iso(cur_date, t100),
                },
            }
            schedules.append(entry)
            clock = t100

    return {"version": 3, "schedules": schedules}


def main() -> int:
    p = argparse.ArgumentParser(description="Generate schedule.json for flat category structure.")
    p.add_argument("--pdf-dir", default="./02_pdf_target")
    p.add_argument("--photos-dir", default="./03_photos_export")
    p.add_argument("--mapping", default="asset_waktu_mapping.json")
    p.add_argument("--data-acuan", default="data_acuan_tenaga_gabungan.json")
    p.add_argument("--jam-mulai", type=int, default=7, help="jam mulai (0-23)")
    p.add_argument("--jam-selesai", type=int, default=18, help="jam selesai (0-23)")
    p.add_argument("--tim-max", type=int, default=2)
    p.add_argument("--output", default="schedule.json")
    args = p.parse_args()

    pdf_dir = Path(args.pdf_dir).resolve()
    photos_dir = Path(args.photos_dir).resolve()

    mapping_path = Path(args.mapping)
    data_acuan_path = Path(args.data_acuan)

    mapping = {}
    acuan = {}
    if mapping_path.exists():
        mapping = load_mapping(mapping_path)
    else:
        print(f"[WARNING] mapping file not found: {mapping_path}")
    if data_acuan_path.exists():
        acuan = load_data_acuan(data_acuan_path)
    else:
        print(f"[WARNING] data acuan not found: {data_acuan_path}")

    jm = max(0, min(23 * 60, args.jam_mulai * 60))
    js = max(0, min(24 * 60, args.jam_selesai * 60))

    sched = build_schedule(pdf_dir, photos_dir, mapping, acuan, jm, js, max(1, args.tim_max))

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    if os.environ.get("OVERWRITE", "1") == "0" and out.exists():
        print(f"  [SKIP] {out} sudah ada (overwrite=off)")
        return 0

    with open(out, "w", encoding="utf-8") as f:
        json.dump(sched, f, indent=2, ensure_ascii=False)

    print(f"\nSchedule saved -> {out}")
    print(f"Files: {len(sched['schedules'])}")
    for s in sched["schedules"]:
        print(f"  Tim {s['tim']} | {s['date']} | {s['btp']}/{s['category']}/{s['identifier']} ({s['waktu_menit']} menit)")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
