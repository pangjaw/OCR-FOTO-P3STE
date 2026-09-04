#!/usr/bin/env python3
"""scheduler.py — Generate schedule.json: urutan PDF → Tim + jam.

Pipeline: export_pdf_foto → extract_pdf_dates → scheduler.py → edit_timemark → merge_pdf_foto

Schedule records are grouped by PDF; each child asset keeps per-photo timestamps.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime, date, timedelta

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

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
    "juli": 7, "jul": 7, "agustus": 8, "agt": 8, "aug": 8, "agu": 8,
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
    """Parse date string from date.txt format 'Senin, Jan 06 2025', '14 Agu 2025', or ISO."""
    if not text:
        return None
    cleaned = re.sub(r'^[A-Za-z]+,\s*', '', text).strip().lower()

    # 1. Month DD YYYY (e.g. 'jan 06 2025', 'agu 14 2025')
    m1 = re.match(r"([a-z]+)\s+(\d{1,2})\s+(\d{4})", cleaned)
    if m1:
        mon_str, day_str, yr_str = m1.groups()
        if mon_str in MONTH_MAP:
            try:
                return date(int(yr_str), MONTH_MAP[mon_str], int(day_str))
            except ValueError:
                pass

    # 2. DD Month YYYY (e.g. '14 agu 2025', '14 agustus 2025')
    m2 = re.match(r"(\d{1,2})\s+([a-z]+)\s+(\d{4})", cleaned)
    if m2:
        day_str, mon_str, yr_str = m2.groups()
        if mon_str in MONTH_MAP:
            try:
                return date(int(yr_str), MONTH_MAP[mon_str], int(day_str))
            except ValueError:
                pass

    # 3. YYYY-MM-DD
    m3 = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", cleaned)
    if m3:
        try:
            return date(int(m3.group(1)), int(m3.group(2)), int(m3.group(3)))
        except ValueError:
            pass

    # 4. DD-MM-YYYY
    m4 = re.match(r"(\d{1,2})-(\d{1,2})-(\d{4})", cleaned)
    if m4:
        try:
            return date(int(m4.group(3)), int(m4.group(2)), int(m4.group(1)))
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
    rem_m = m % (24 * 60)
    return f"{rem_m // 60:02d}:{rem_m % 60:02d}"


def m2iso(d: date, m: int) -> str:
    rem_m = m % (24 * 60)
    return datetime(d.year, d.month, d.day, rem_m // 60, rem_m % 60).isoformat()


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
    upper_identifier = identifier.upper()
    if identifier.startswith("JPL "):
        # BOO-BOP is a cross-station JPL route; it belongs to BTP BD,
        # not the generic BOO route (BTP JAK).
        if re.search(r'\bBOO\s*-\s*BOP\b', upper_identifier):
            return "BTP BD"
        codes = re.findall(r'\b(BOO|CLT|BJD|BOP|BTT|CGB|CS|COS|MSG|CCR)\b', upper_identifier)
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

    print(f"[*] Pass 1: Extracting asset items from {len(files)} PDF files...")

    from extract_pdf_dates import parse_target_filename, parse_date_from_filename, parse_date_indonesian
    import fitz

    # ── PASS 1: Extract all items and group by target date ──
    files_by_date: dict[date, list[dict]] = {}

    for idx, pdf_path in enumerate(files, 1):
        # 1. Parse date and basic info
        target_info = parse_target_filename(pdf_path.name)
        category = None
        identifier = None
        pdf_date: date | None = None
        date_str = None

        if target_info:
            category, identifier, dt_raw = target_info
            pdf_date = parse_date_from_filename(dt_raw)
            if pdf_date:
                date_str = format_date_target(pdf_date)

        # Read page 1 text using fitz
        page1_text = ""
        try:
            with fitz.open(str(pdf_path)) as doc:
                if len(doc) > 0:
                    page1_text = doc[0].get_text() or ""
        except Exception:
            pass

        if not category:
            category = detect_category_from_filename(pdf_path.name)

        if not pdf_date and page1_text:
            pdf_date = parse_date_indonesian(page1_text)
            if pdf_date:
                date_str = format_date_target(pdf_date)

        if not pdf_date:
            print(f"  [SKIP] cannot resolve date for {pdf_path.name}")
            continue

        # Extract funclocs on page 1 (in order from top to bottom)
        all_funclocs = extract_all_funclocs(page1_text) if page1_text else []
        is_multi = category in MULTI_ROW_CATEGORIES
        asset_items = []

        if is_multi and all_funclocs:
            seen = set()
            for funcloc_line in all_funclocs:
                ident = extract_identifier(funcloc_line, category)
                if ident and ident not in seen:
                    seen.add(ident)
                    w = get_waktu(category, mapping, acuan)
                    btp = _determine_btp(ident, pdf_path)
                    asset_items.append({
                        "identifier": ident,
                        "btp": btp,
                        "waktu_menit": w,
                        "funcloc": funcloc_line.strip()
                    })

        if not asset_items:
            # Single-row or fallback
            if not identifier and all_funclocs:
                identifier = extract_identifier(all_funclocs[0], category)
            if not identifier:
                station = extract_station_from_filename(pdf_path.name)
                identifier = station if station else sanitize_segment(pdf_path.stem)

            # Core count check for SERAT OPTIK
            w = get_waktu(category, mapping, acuan)
            if is_serat_optik_pdf(pdf_path):
                m = re.search(r'Jumlah Core[^\d]*(\d+)', page1_text, re.IGNORECASE)
                if m:
                    w = int(m.group(1)) * 6

            btp = _determine_btp(identifier, pdf_path)
            asset_items.append({
                "identifier": identifier,
                "btp": btp,
                "waktu_menit": w,
                "funcloc": ""
            })

        total_pdf_waktu = sum(a["waktu_menit"] for a in asset_items)

        pdf_entry = {
            "file": pdf_path.name,
            "category": category,
            "pdf_stem": pdf_path.stem,
            "date_str": date_str or format_date_target(pdf_date),
            "pdf_date": pdf_date,
            "is_multi": is_multi,
            "asset_items": asset_items,
            "total_pdf_waktu": total_pdf_waktu,
        }

        if pdf_date not in files_by_date:
            files_by_date[pdf_date] = []
        files_by_date[pdf_date].append(pdf_entry)

        if idx % 50 == 0 or idx == 1:
            print(f"  [{idx:3d}/{len(files)}] {pdf_path.name[:50]}...")

    total_extracted_assets = sum(sum(len(p["asset_items"]) for p in pdf_list) for pdf_list in files_by_date.values())
    print(f"[*] Pass 1 complete: {len(files)} PDFs ({total_extracted_assets} total asset entries) grouped into {len(files_by_date)} unique dates.")
    print(f"[*] Pass 2: Generating chronological multi-team schedule per date...")

    # ── PASS 2: Sequential scheduling per chronological date ──
    schedules = []
    sorted_dates = sorted(files_by_date.keys())

    for cur_date in sorted_dates:
        pdf_list = files_by_date[cur_date]
        tim = 1
        clock = jam_mulai
        scheduled_assets_on_date = {}  # (category, identifier) -> slot_info

        for pdf_info in pdf_list:
            for a in pdf_info["asset_items"]:
                asset_key = (pdf_info["category"], a["identifier"])

                if asset_key in scheduled_assets_on_date:
                    # Aset ini sudah dijadwalkan pada tanggal ini -> pakai jam & tim yang sama persis
                    slot = scheduled_assets_on_date[asset_key]
                    entry = {
                        "file": pdf_info["file"],
                        "btp": a["btp"],
                        "category": pdf_info["category"],
                        "pdf_stem": pdf_info["pdf_stem"],
                        "identifier": a["identifier"],
                        "date": pdf_info["date_str"],
                        "iso_date": cur_date.isoformat(),
                        "tim": slot["tim"],
                        "waktu_menit": slot["waktu_menit"],
                        "photos": slot["photos"],
                    }
                    schedules.append(entry)
                else:
                    # Aset baru pada tanggal ini -> alokasikan slot jam berikutnya
                    if clock > jam_selesai:
                        tim += 1
                        clock = jam_mulai

                    w = a["waktu_menit"]
                    t0 = clock
                    t50 = round(clock + w / 2)
                    t100 = clock + w

                    photos = {
                        "0.jpg":  m2iso(cur_date, t0),
                        "50.jpg": m2iso(cur_date, t50),
                        "100.jpg": m2iso(cur_date, t100),
                    }

                    slot = {
                        "tim": tim,
                        "waktu_menit": w,
                        "t0": t0,
                        "t50": t50,
                        "t100": t100,
                        "photos": photos
                    }
                    scheduled_assets_on_date[asset_key] = slot

                    entry = {
                        "file": pdf_info["file"],
                        "btp": a["btp"],
                        "category": pdf_info["category"],
                        "pdf_stem": pdf_info["pdf_stem"],
                        "identifier": a["identifier"],
                        "date": pdf_info["date_str"],
                        "iso_date": cur_date.isoformat(),
                        "tim": tim,
                        "waktu_menit": w,
                        "photos": photos,
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
    if not mapping_path.exists() and (Path("config") / args.mapping).exists():
        mapping_path = Path("config") / args.mapping

    data_acuan_path = Path(args.data_acuan)
    if not data_acuan_path.exists() and (Path("config") / args.data_acuan).exists():
        data_acuan_path = Path("config") / args.data_acuan

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

    print(f"\n✅ Penjadwalan Berhasil! Disimpan ke -> {out}", flush=True)
    print(f"  • Total Jadwal Aset: {len(sched['schedules'])} entri\n", flush=True)

    from collections import OrderedDict
    tree = OrderedDict()
    for s in sched["schedules"]:
        d = s.get("iso_date", s.get("date", "UNKNOWN"))
        t = s.get("tim", 1)
        tree.setdefault(d, {}).setdefault(t, []).append(s)

    for d_idx, (d_str, tims) in enumerate(tree.items(), 1):
        print(f"[{d_idx}/{len(tree)}] 📅 Tanggal: {d_str}", flush=True)
        tim_keys = sorted(tims.keys())
        for t_idx, t_num in enumerate(tim_keys):
            is_last_tim = (t_idx == len(tim_keys) - 1)
            t_branch = "└──" if is_last_tim else "├──"
            t_pipe = "   " if is_last_tim else "│  "
            assets = tims[t_num]
            print(f"  {t_branch} 👥 Tim {t_num} ({len(assets)} aset):", flush=True)
            for a_idx, a in enumerate(assets):
                is_last_asset = (a_idx == len(assets) - 1)
                a_branch = "└──" if is_last_asset else "├──"
                start_iso = a.get("photos", {}).get("0.jpg", "")
                time_str = start_iso.split("T")[1][:5] if "T" in start_iso else "08:00"
                print(f"  {t_pipe}  {a_branch} [{time_str}] {a['category']}/{a['identifier']} ({a['waktu_menit']}m)", flush=True)
        print("", flush=True)

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
