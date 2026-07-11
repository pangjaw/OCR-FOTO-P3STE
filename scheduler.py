#!/usr/bin/env python3
"""scheduler.py — Generate schedule.json: urutan aset dari PDF → Tim + jam.

Pipeline: export_pdf_foto → extract_pdf_dates → scheduler.py → edit_timemark → merge_pdf_foto
"""
import argparse
import json
import os
import re
from pathlib import Path
from datetime import datetime, date, timedelta

import pdfplumber

from export_pdf_foto import extract_asset_rows, sanitize_segment, ensure_dir
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


def _parse_date(text: str) -> date | None:
    """Parse date string from date.txt format 'Rabu, Jul 08 2026' or ISO."""
    # Remove day name prefix: "Rabu, Jul 08 2026" -> "Jul 08 2026"
    text = re.sub(r'^[A-Za-z]+,\s*', '', text).strip()
    # Pattern: Month DD YYYY
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


def get_waktu(asset_type: str, detail: str, mapping: dict, acuan: dict) -> int:
    key = (asset_type, detail)
    asset_id = mapping.get(key)
    if asset_id and asset_id in acuan:
        return acuan[asset_id]["waktu_menit"]
    defaults = {"AXC": 45, "WESEL": 45, "SINYAL": 30, "PDSE": 420}
    return defaults.get(asset_type, 45)


def read_date_from_photos(photos_dir: Path, asset_type: str, detail: str) -> str | None:
    fp = photos_dir / sanitize_segment(asset_type) / sanitize_segment(detail) / "date.txt"
    if fp.exists():
        return fp.read_text(encoding="utf-8").strip()
    return None


def m2hhmm(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def m2iso(d: date, m: int) -> str:
    return datetime(d.year, d.month, d.day, m // 60, m % 60).isoformat()


# ---------------------------------------------------------------------------
# core
# ---------------------------------------------------------------------------

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
        with pdfplumber.open(str(pdf_path)) as doc:
            if not doc.pages:
                continue
            page1 = doc.pages[0]
            assets = extract_asset_rows(page1)

        if not assets:
            continue

        # --- determine date ---
        date_str = None
        pdf_date: date | None = None

        # 1) from date.txt of first asset
        if assets:
            date_str = read_date_from_photos(photos_dir, assets[0].asset_type, assets[0].detail)

        # 2) fallback: scan PDF
        if not date_str:
            d = extract_date_from_pdf(pdf_path)
            if d:
                pdf_date = d
                date_str = format_date_target(d)

        if not date_str:
            print(f"  [SKIP] no date found for {pdf_path.name}")
            continue

        # parse date
        if pdf_date is None:
            pdf_date = _parse_date(date_str)
        if pdf_date is None:
            print(f"  [SKIP] cannot parse date '{date_str}' for {pdf_path.name}")
            continue

        # --- date boundary → reset ---
        if pdf_date != cur_date:
            cur_date = pdf_date
            tim = 1
            clock = jam_mulai

        # --- check if file fits in current Tim ---
        total_waktu = sum(get_waktu(a.asset_type, a.detail, mapping, acuan)
                          for a in assets)

        # Overflow rule: file is the first in its tim, always fits.
        # Only switch if clock already past end OR file doesn't fit AND not first file.
        if clock >= jam_selesai or (clock + total_waktu > jam_selesai and clock != jam_mulai):
            tim += 1
            if tim > tim_max:
                tim = 1
                # Move to next working day
                cur_date = pdf_date + timedelta(days=1)
                date_str = format_date_target(cur_date)
            clock = jam_mulai

        # --- assign times ---
        entry = {"file": pdf_path.name, "date": date_str, "tim": tim, "assets": []}

        for a in assets:
            w = get_waktu(a.asset_type, a.detail, mapping, acuan)
            t0 = clock
            t50 = round(clock + w / 2)
            t100 = clock + w

            entry["assets"].append({
                "type": a.asset_type,
                "detail": a.detail,
                "code": a.code,
                "waktu_menit": w,
                "photos": {
                    "0.jpg":  m2iso(cur_date, t0),
                    "50.jpg": m2iso(cur_date, t50),
                    "100.jpg": m2iso(cur_date, t100),
                },
            })
            clock = t100

        schedules.append(entry)

    return {"version": 1, "schedules": schedules}


def main() -> int:
    p = argparse.ArgumentParser(description="Generate schedule.json for per-asset timing + team.")
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

    mapping = load_mapping(Path(args.mapping))
    acuan = load_data_acuan(Path(args.data_acuan))

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
        print(f"  Tim {s['tim']} | {s['date']} | {s['file']} ({len(s['assets'])} aset)")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
