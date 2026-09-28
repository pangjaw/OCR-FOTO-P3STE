#!/usr/bin/env python3
"""generate_asset_koordinat_mapping.py — Ekstrak dan normalisasi data koordinat dari Excel ke JSON.

Sumber: C:\\Users\\dikarm\\Documents\\Server\\Copy of Timemark_F.xlsx (Sheet Aset)
Output: config/asset_koordinat_mapping.json
"""

import re
import json
from pathlib import Path
import openpyxl

EXCEL_SOURCE = Path(r"C:\Users\dikarm\Documents\Server\Copy of Timemark_F.xlsx")
OUTPUT_JSON = Path("config/asset_koordinat_mapping.json")


def normalize_coord_str(raw: any) -> str | None:
    """Normalizes various GPS coordinate formats into standard '-6.xxxxxx, 106.xxxxxx'."""
    if not raw:
        return None
    s = str(raw).strip()
    if not s or s.lower() in ("none", "0", "-", "null"):
        return None

    # Fix known typos in source Excel
    # Typo 1: '706.' -> '106.' (wrong key press for longitude)
    s = re.sub(r'\b706\.', '106.', s)
    # Typo 2: '+' artifact
    s = s.replace('+', '')
    # Typo 3: apostrophe instead of period in decimal (e.g. 106'799485)
    s = re.sub(r'(\d{1,3})\'(\d{4,})', r'\1.\2', s)

    # 1. Decimal with S/E (or even typo E/E): e.g. "6.525087'S, 106.801578'E" or "6.583438'E, 106.793363'E"
    m1 = re.search(r'([0-9.]+)\s*[\'°]?\s*[A-Za-z]?\s*[,/ ]+\s*([0-9.]+)\s*[\'°]?\s*[A-Za-z]?', s)
    if m1:
        v1 = float(m1.group(1))
        v2 = float(m1.group(2))
        lat_val = min(v1, v2)
        lon_val = max(v1, v2)
        # In Java/Bogor area, Lat is approx 6.4 - 6.8 S, Lon is approx 106.7 - 107.0 E
        if 5.0 <= lat_val <= 8.0 and 105.0 <= lon_val <= 109.0:
            return f"-{lat_val:.6f}, {lon_val:.6f}"

    # 2. Signed decimal: e.g. "-6.569635397216756, 106.79901688504974"
    m2 = re.search(r'(-?[0-9.]+)\s*[,/ ]+\s*(-?[0-9.]+)', s)
    if m2:
        v1 = float(m2.group(1))
        v2 = float(m2.group(2))
        lat_val = min(v1, v2)
        lon_val = max(v1, v2)
        if -8.0 <= lat_val <= -5.0 and 105.0 <= lon_val <= 109.0:
            return f"{lat_val:.6f}, {lon_val:.6f}"

    # 3. DMS format: e.g. 6°33'53.5"S 106°48'08.6"E
    m3 = re.search(r'(\d+)\D+(\d+)\D+([0-9.]+)\D*[Ss]?\D+(\d+)\D+(\d+)\D+([0-9.]+)\D*[Ee]?', s)
    if m3:
        d1, min1, s1 = float(m3.group(1)), float(m3.group(2)), float(m3.group(3))
        d2, min2, s2 = float(m3.group(4)), float(m3.group(5)), float(m3.group(6))
        lat_dec = -(d1 + min1 / 60.0 + s1 / 3600.0)
        lon_dec = d2 + min2 / 60.0 + s2 / 3600.0
        return f"{lat_dec:.6f}, {lon_dec:.6f}"

    return None


def extract_core_identifier(desc: str) -> str:
    """Extracts short identifier from SAP description.
    e.g. 'AXLE COUNTER ZP 207 CLT-BJD' -> 'ZP 207 CLT-BJD'
         'PENGGERAK WESEL W21A BOO' -> 'W21A BOO'
         'SINYAL MASUK J10 BOO' -> 'J10 BOO'
    """
    s = desc.strip()
    # Strip prefix
    prefixes = [
        r"^AXLE\s+COUNTER\s+",
        r"^PENGGERAK\s+WESEL\s+",
        r"^WESEL\s+",
        r"^SINYAL\s+(?:MASUK|KELUAR|BLOK|ULANG\s+BLOK|MUKA\s+BLOK|MUKA|LANGSIR)\s+",
        r"^SINYAL\s+",
        r"^PESAWAT\s+TELEPON\s+",
        r"^GENTANIK\s+",
        r"^OTB\s+FO\s+",
        r"^PINTU\s+PERLINTASAN\s+",
        r"^INTERMEDIATE\s+BLOK\s+",
        r"^BANGUNAN\s+",
        r"^UPS\s+",
        r"^BATTERE\s+",
        r"^GENSET\s+",
        r"^RECTIFIER\s+",
    ]
    for p in prefixes:
        s = re.sub(p, "", s, flags=re.IGNORECASE)
    return s.strip()


def build_mapping():
    if not EXCEL_SOURCE.exists():
        raise FileNotFoundError(f"Source Excel not found at: {EXCEL_SOURCE}")

    print(f"Reading {EXCEL_SOURCE}...")
    wb = openpyxl.load_workbook(EXCEL_SOURCE, data_only=True)
    if "Aset" not in wb.sheetnames:
        raise ValueError("Sheet 'Aset' not found in Excel workbook!")

    ws = wb["Aset"]
    rows = list(ws.iter_rows(values_only=True))[1:]

    by_funcloc = {}
    by_identifier = {}
    by_nokai = {}
    
    total_rows = 0
    valid_coords = 0
    skipped_coords = 0

    for r in rows:
        floc = str(r[1] or "").strip()
        no_kai = str(r[2] or "").strip()
        desc = str(r[3] or "").strip()
        catalog = str(r[4] or "").strip()
        jenis = str(r[5] or "").strip()
        lokasi = str(r[6] or "").strip()
        raw_coord = r[8]
        alamat = str(r[9] or "").strip()

        if not floc and not desc:
            continue
        total_rows += 1
        # User-provided coordinate for Sinyal Muka MJ20 CLT (SIN11782)
        if (floc == "SIN11782" or "MJ20.CLT" in no_kai.upper() or ("MJ20" in desc.upper() and "CLT" in desc.upper())) and not raw_coord:
            raw_coord = "6.527237'S, 106.800950'E"
            if not alamat:
                alamat = "Jl. Raya Cilebut No. 46, Cilebut Tim, Kec. Sukaraja, Kabupaten Bogor, Jawa Barat 16710"

        norm_coord = normalize_coord_str(raw_coord)
        if not norm_coord:
            skipped_coords += 1
            continue
        
        valid_coords += 1
        entry = {
            "funcloc": floc,
            "no_kai": no_kai,
            "description": desc,
            "catalog": catalog,
            "jenis": jenis,
            "lokasi": lokasi,
            "coordinate": norm_coord,
            "address": alamat
        }

        # 1. Map by Funcloc
        if floc:
            by_funcloc[floc.upper()] = entry

        # 2. Map by No KAI
        if no_kai:
            by_nokai[no_kai.upper()] = entry
            # Also clean dots: AXC.ZP207.CLT-BJD -> ZP207 CLT-BJD
            clean_no_kai = no_kai.replace(".", " ").strip().upper()
            by_nokai[clean_no_kai] = entry

        # 3. Map by Core Identifier
        ident = extract_core_identifier(desc)
        if ident:
            by_identifier[ident.upper()] = entry
            # Add alias without leading zeros: JPL 02 BOO -> JPL 2 BOO
            jpl_zero = re.sub(r'\bJPL\s+0+(\d+)', r'JPL \1', ident, flags=re.IGNORECASE)
            if jpl_zero != ident:
                by_identifier[jpl_zero.upper()] = entry
            # Add alias with leading zero: JPL 2 BOO -> JPL 02 BOO
            jpl_add_zero = re.sub(r'\bJPL\s+(\d)\b', r'JPL 0\1', ident, flags=re.IGNORECASE)
            if jpl_add_zero != ident:
                by_identifier[jpl_add_zero.upper()] = entry

            # Handle ZP 41B -> ZP 41 alias
            if "ZP 41B" in ident.upper():
                zp41_alias = ident.upper().replace("ZP 41B", "ZP 41")
                by_identifier[zp41_alias] = entry

        # Handle Catu Daya station alias (e.g. folder BTP JAK/CATUDAYA/CLT -> identifier "CLT")
        if jenis == "Catu Daya" and lokasi:
            by_identifier[f"CATUDAYA {lokasi.upper()}"] = entry
            by_identifier[f"CDA {lokasi.upper()}"] = entry
            if lokasi.upper() == "CLT":
                by_identifier["CLT"] = entry

    data = {
        "_metadata": {
            "source_file": str(EXCEL_SOURCE),
            "total_assets": total_rows,
            "assets_with_coordinate": valid_coords,
            "assets_without_coordinate": skipped_coords,
            "format": "-6.xxxxxx, 106.xxxxxx"
        },
        "by_funcloc": by_funcloc,
        "by_identifier": by_identifier,
        "by_nokai": by_nokai
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Generated {OUTPUT_JSON} successfully!")
    print(f"  - Total rows: {total_rows}")
    print(f"  - Valid coordinates: {valid_coords}")
    print(f"  - Skipped (empty): {skipped_coords}")
    print(f"  - Indexed Funclocs: {len(by_funcloc)}")
    print(f"  - Indexed Identifiers: {len(by_identifier)}")


if __name__ == "__main__":
    build_mapping()
