import argparse
import csv
import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import pdfplumber
from pypdf import PdfReader


# ── Constants ───────────────────────────────────────────────────

STATION_TO_BTP = {
    "BOO": "BTP JAK", "CLT": "BTP JAK",
    "BJD": "BTP JAK",
    "BNR": "BTP BD",
    "BOP": "BTP BD", "BTT": "BTP BD", "CGB": "BTP BD",
    "COS": "BTP BD", "MSG": "BTP BD",
    "BOP-BTT": "BTP BD",
}

# Words to skip when scanning filename for station code
STATION_SKIP_WORDS = {
    'CDA', 'PDSE', 'OTB', 'PTLS', 'PTDS', 'PTPP', 'TLKM', 'GENTANIK',
    'CATU', 'DAYA', 'SERAT', 'OPTIK', 'RADIO', 'JPL', 'BNR', 'TLK',
    'PERAWATAN', 'BULANAN',
    'ELEKTRIK', 'TELEKOM', 'TELEKOMUNIKASI', 'PERSINYALAN', 'MULTIPLEX',
    'DATA', 'LOGGER', 'BANGUNAN', 'PANEL', 'DISPLAY', 'DALWAS', 'PERKA',
    'PESAWAT', 'TELEPON', 'SENTRAL', 'ANTAR', 'STASIUN', 'WARTA',
}

DEFAULT_INPUT_DIR = "./01_pdf_source"
DEFAULT_OUTPUT_DIR = "./03_photos_export"

def original_images_by_name(reader: PdfReader, page_index: int) -> dict[str, tuple[str, bytes]]:
    """Return mapping of image name stem -> (suffix, raw_bytes) from pypdf XObjects."""
    result = {}
    try:
        page = reader.pages[page_index]
        for img_name, img in (page.images or {}).items():
            # img_name might include extension, stem removes it for matching
            stem = Path(img_name).stem
            suffix = Path(img_name).suffix or ".jpg"
            if suffix.lower() not in (".jpg", ".jpeg", ".png"):
                suffix = ".jpg"
            result[stem] = (suffix, img.data)
    except Exception:
        pass
    return result


def _render_page_and_crop(page: pdfplumber.page.Page, placement: dict,
                          resolution: int = 600) -> bytes:
    """Render a pdfplumber page and crop an image region. Returns JPEG bytes.

    Used as fallback when pypdf can't find original (inline images).
    """
    from PIL import Image
    from io import BytesIO

    page_img = page.to_image(resolution=resolution)
    # placement has x0, top, x1, bottom in PDF points
    scale = resolution / 72.0
    crop_box = (
        float(placement['x0']) * scale,
        float(placement['top']) * scale,
        float(placement['x1']) * scale if 'x1' in placement else (float(placement['x0']) + float(placement.get('width', 0))) * scale,
        float(placement['bottom']) * scale,
    )
    # Recompute x1, y1 from width/height if not present
    if 'x1' not in placement:
        crop_box = (
            float(placement['x0']) * scale,
            float(placement['top']) * scale,
            (float(placement['x0']) + float(placement.get('width', 0))) * scale,
            (float(placement['top']) + float(placement.get('height', 0))) * scale,
        )

    cropped = page_img.original.crop([int(v) for v in crop_box])
    buf = BytesIO()
    cropped.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


# ── Station name → code ───────────────────────────────────────────
DEFAULT_LOG_DIR = "./logs"
DEFAULT_START_PAGE = 2
DEFAULT_RESOLUTION = 220
SAP_MAPPING_PATH = "./sap_station_mapping.json"

# ── Station name → code (for matching 2025 PDF location to 2026 PDF folder) ──
STATION_NAME_TO_CODE = {
    "BOGOR": "BOO",
    "CILEBUT": "CLT",
    "BOGORPALEDANG": "BOP",
    "BATUTULIS": "BTT",
    "BOJONGGEDE": "BJD",
    "CIGOMBONG": "CGB",
    "CIOMAS": "COS",
    "MASENG": "MSG",
    "CICURUG": "CCR",
    "DEPOK": "BOO",  # PTLS Depok is actually Bogor (wrong placement by pusat)
}


@dataclass
class AssetRow:
    page_number: int
    code: str
    title: str
    asset_type: str
    detail: str
    top: float
    station: str = "UNKNOWN"
    funcloc: str = ""


# ── Category Detection from Filename ────────────────────────────

def detect_category_from_filename(pdf_name: str) -> str:
    """Detect asset category folder name from PDF filename.

    Priority order (more specific first — check substrings in this order):
    1. PTPP/PTDS/PTLS/PDSE/CDA explicit codes in filename
    2. "DI PINTU PERLINTASAN" / "DI LUAR STASIUN" / "DI STASIUN"
    3. "TLKM JPL" / "GENTANIK" → PTPP
    4. "JPL" standalone → JPL
    5. "CDA" / "CATU DAYA" → CATUDAYA
    6. "PDSE" / "PERSINYALAN ELEKTRIK" → PDSE
    7. "CTC-CTS" → CTS
    8. "SERAT OPTIK" / "OTB" / "FIBER OPTIK" → SERAT OPTIK
    9. "MULTIPLEX" / "MUX" / "TOWER TLK" → PTLS
    10. "BANGUNAN" / "DATA LOGGER" → PDSE
    """
    name = pdf_name.upper()

    # ── Explicit code in filename (most reliable) ──
    if "PTPP" in name:
        return "PTPP"
    if "PTDS" in name:
        return "PTDS"
    if "PTLS" in name:
        return "PTLS"

    # ── Long-form Telekomunikasi phrases ──
    if "DI PINTU PERLINTASAN" in name or "PERALATAN TELEKOMUNIKASI DI PINTU PERLINTASAN" in name:
        return "PTPP"
    if "DI LUAR STASIUN" in name:
        return "PTLS"
    if "DI STASIUN" in name:
        return "PTDS"

    # ── TLKM + JPL / Gentanik → PTPP ──
    if ("TLKM" in name and "JPL" in name) or "GENTANIK" in name:
        return "PTPP"

    # ── Serat Optik / OTB ── (before JPL: SERAT OPTIK files may mention JPL locations)
    if "SERAT OPTIK" in name or "FIBER OPTIK" in name or "OTB" in name:
        return "SERAT OPTIK"

    # ── Standalone JPL / PINTU PERLINTASAN ──
    if "PINTU PERLINTASAN" in name or re.search(r'(?<![A-Z])JPL(?![A-Z])', name) or "_JPL_" in name:
        return "JPL"

    # ── Catu Daya ──
    if "CDA" in name or "CATU DAYA" in name or "CATUDAYA" in name:
        return "CATUDAYA"

    # ── WESEL ── (before PDSE: WESEL filenames may contain "elektrik" but are not PDSE)
    if ("WESEL" in name or "POINT LOCK" in name or "PERINTANG" in name or "PELALAU" in name) and "PERSINYALAN" not in name:
        return "WESEL"

    # ── SINYAL / PERAGA SINYAL ── (before PDSE to avoid "elektrik" clash)
    if "PERAGA SINYAL" in name:
        return "SINYAL"
    if "SINYAL" in name and "PERSINYALAN" not in name:
        return "SINYAL"

    # ── AXLE COUNTER ──
    if "AXLE COUNTER" in name or " AXC " in name:
        return "AXC"

    # ── PDSE ──
    if "PDSE" in name or "PERSINYALAN ELEKTRIK" in name:
        return "PDSE"

    # ── CTC-CTS ──
    if "CTC-CTS" in name or ("CTC" in name and "CTS" in name):
        return "CTS"

    # ── Serat Optik / OTB ──
    if "SERAT OPTIK" in name or "FIBER OPTIK" in name or "OTB" in name:
        return "SERAT OPTIK"

    # ── PTLS fallbacks ──
    if "MULTIPLEX" in name or "MUX" in name or "TOWER TLK" in name:
        return "PTLS"

    # ── PDSE fallbacks ──
    if "BANGUNAN" in name or "DATA LOGGER" in name:
        return "PDSE"

    # ── PTLS extra: RADIO BASESTATION / WAYSTATION ──
    if "RADIO" in name and ("BASESTATION" in name or "WAY" in name or "WAYSTATION" in name):
        return "PTLS"

    return "UNKNOWN"


# ── Helpers ─────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export foto dokumentasi dari PDF berdasarkan aset dan label persen."
    )
    parser.add_argument(
        "paths", nargs="*",
        help="PDF yang diproses. Jika kosong, script akan ambil semua PDF dari --input.",
    )
    parser.add_argument("--input", default=DEFAULT_INPUT_DIR,
                        help=f"Folder PDF input. Default: {DEFAULT_INPUT_DIR}")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR,
                        help=f"Folder output. Default: {DEFAULT_OUTPUT_DIR}")
    parser.add_argument("--log-dir", default=DEFAULT_LOG_DIR,
                        help=f"Folder log. Default: {DEFAULT_LOG_DIR}")
    parser.add_argument("--start-page", type=int, default=DEFAULT_START_PAGE,
                        help="Nomor halaman awal scan aset. Default: 2")
    parser.add_argument("--resolution", type=int, default=DEFAULT_RESOLUTION,
                        help="Diabaikan saat export original image.")
    parser.add_argument("--sap-mapping", default=SAP_MAPPING_PATH,
                        help=f"Path ke file mapping SAP. Default: {SAP_MAPPING_PATH}")
    return parser.parse_args()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def list_pdf_files(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(
        [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf"]
    )


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def sanitize_segment(text: str) -> str:
    text = normalize_spaces(text)
    text = "".join("_" if ord(char) < 32 else char for char in text)
    text = re.sub(r'[<>:"\/\\|?*]', "_", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text or "UNKNOWN"


def load_sap_mapping(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        mapping = {}
        for floc, info in data.items():
            mapping[floc] = info.get("station", "UNKNOWN")
        return mapping
    except FileNotFoundError:
        print(f"[WARNING] SAP mapping not found at {path}.")
        return {}
    except json.JSONDecodeError as e:
        print(f"[WARNING] Invalid JSON in SAP mapping: {e}")
        return {}


def detect_asset_type(code: str, title: str) -> str:
    upper = f"{code} {title}".upper()
    if code.startswith("AXL"):
        return "AXC"
    if code.startswith("WSL"):
        return "WESEL"
    if code.startswith("CDA"):
        return "CATU_DAYA"
    if code.startswith("SIN"):
        return "SINYAL"
    if code.startswith("JPL"):
        return "PINTU_PERLINTASAN"
    if code.startswith("TLK") or code.startswith("TWR") or code.startswith("OTB"):
        if "BANGUNAN" in upper or "DATA LOGGER" in upper:
            return "PDSE"
        return "TELEKOMUNIKASI"
    if code.startswith("CTC") or "CTC" in upper or "CTS" in upper or "DALWAS" in upper:
        return "CTS"
    if code.startswith("INB"):
        return "PDSE"  # INB = interlocking/blok equipment → PDSE
    if code.startswith("TRA"):
        if "BANGUNAN" in upper or "DATA LOGGER" in upper:
            return "PDSE"
        if "MULTIPLEX" in upper or "MUX" in upper:
            return "PTLS"
        if "OTB" in upper:
            return "SERAT OPTIK"
        return "UNKNOWN"
    if "AXLE COUNTER" in upper:
        return "AXC"
    if "WESEL" in upper:
        return "WESEL"
    if "CATU DAYA" in upper:
        return "CATU_DAYA"
    if "SINYAL" in upper:
        return "SINYAL"
    if "PINTU PERLINTASAN" in upper:
        return "PINTU_PERLINTASAN"
    if "TELEKOMUNIKASI" in upper or "RADIO" in upper or "SERAT OPTIK" in upper or "OTB" in upper:
        return "TELEKOMUNIKASI"
    if "BANGUNAN" in upper or "DATA LOGGER" in upper:
        return "PDSE"
    if "MULTIPLEX" in upper:
        return "PTLS"
    return "UNKNOWN"


def extract_detail(title: str, asset_type: str) -> str:
    original = normalize_spaces(title)

    def after(marker: str) -> str | None:
        match = re.search(re.escape(marker), original, flags=re.IGNORECASE)
        if not match:
            return None
        return normalize_spaces(original[match.end():]).lstrip(": -")

    detail = None
    if asset_type == "AXC":
        detail = after("COUNTER")
    elif asset_type == "WESEL":
        detail = after("ELEKTRIK")
    elif asset_type == "SINYAL":
        detail = after("ELEKTRIK") or after("SINYAL MUKA") or after("SINYAL")
    elif asset_type == "CATU_DAYA":
        detail = after("CATU DAYA") or after("UPS") or after("BATTERE") or after("GENSET")
    elif asset_type == "PINTU_PERLINTASAN":
        detail = after("PINTU PERLINTASAN") or after("JPL")
    elif asset_type == "TELEKOMUNIKASI":
        detail = after("TELEKOMUNIKASI") or after("RADIO") or after("WAYSTATION") or after("SERAT OPTIK")
    elif asset_type == "CTS":
        detail = after("CTC") or after("PERALATAN") or original

    if not detail:
        detail = original

    res = sanitize_segment(detail)
    if res == "ZP 41B BOO":
        res = "ZP 41 BOO"
    return res


def extract_station_from_description(desc: str, sap_mapping: dict, funcloc: str) -> str:
    if funcloc and funcloc in sap_mapping:
        station = sap_mapping[funcloc]
        if '-' in station:
            for part in station.split('-'):
                if part in STATION_TO_BTP:
                    return part
        return station

    STATION_NAME_MAP = {
        "BATU TULIS": "BTT", "BOGOR PALEDANG": "BOP", "BOGOR": "BOO",
        "CILEBUT": "CLT", "CIGOMBONG": "CGB", "CIOMAS": "COS", "MASENG": "MSG",
    }
    CODE_ALIASES = {"CS": "COS"}
    station_codes = {"BOO", "BOP", "BTT", "CLT", "MSG", "CGB", "BJD", "CCR", "COS", "CS", "BNR"}

    words = normalize_spaces(desc).split()
    for word in words:
        if word in station_codes:
            return CODE_ALIASES.get(word, word)
    for word in words:
        for part in word.split("-"):
            if part in station_codes:
                return CODE_ALIASES.get(part, part)
    for full_name, code in STATION_NAME_MAP.items():
        if full_name in desc.upper():
            return code
    return "UNKNOWN"


def extract_asset_rows(page: pdfplumber.page.Page, sap_mapping: dict) -> list[AssetRow]:
    lines: defaultdict[float, list[dict]] = defaultdict(list)
    for word in page.extract_words(use_text_flow=True):
        lines[round(float(word["top"]), 1)].append(word)

    rows: list[AssetRow] = []
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

        title = normalize_spaces(" ".join(word["text"] for word in words[code_index + 1:])).lstrip(": -")
        if not title:
            continue

        asset_type = detect_asset_type(code, title)
        detail = extract_detail(title, asset_type)
        station = extract_station_from_description(title, sap_mapping, code)

        rows.append(AssetRow(
            page_number=page.page_number, code=code, title=title,
            asset_type=asset_type, detail=detail, top=top,
            station=station, funcloc=code,
        ))
    return rows


def original_images_by_name(reader: PdfReader, page_index: int) -> dict[str, tuple[str, bytes]]:
    images = {}
    for image in reader.pages[page_index].images:
        suffix = Path(image.name).suffix.lower() or ".jpg"
        images[Path(image.name).stem] = (suffix, image.data)
    return images


# ── Station from Filename ───────────────────────────────────────

def extract_station_from_filename(pdf_name: str) -> str | None:
    """Cari kode station dari nama file PDF setelah kata PERAWATAN.

    Contoh:
      '2026-1_Boo_PERAWATAN_CDA_BOP_11-01-2026.pdf' → 'BOP'
      'Perawatan CDA RADIO BOO 08-01-2026.pdf' → 'BOO'
      '08-03-2026_PERAWATAN CATU DAYA 1 BULANAN_Bogor.pdf' → 'BOO'
    """
    name = pdf_name.replace('.pdf', '').strip()
    m = re.search(r'PERAWATAN[^A-Za-z]*', name, re.IGNORECASE)
    if not m:
        return None
    after = name[m.end():]
    tokens = re.split(r'[_\s]+', after)
    for t in tokens:
        t = t.strip('( ).,;-')
        if not t or len(t) <= 1:
            continue
        if re.match(r'^\d+$', t):
            continue
        upper = t.upper()
        if upper in STATION_SKIP_WORDS:
            continue

        # Check if this is a full station name (e.g. "BOGOR")
        STATION_NAME_MAP = {
            "BATU TULIS": "BTT", "BATUTULIS": "BTT",
            "BOGOR PALEDANG": "BOP", "BOGORPALEDANG": "BOP",
            "BOGOR": "BOO", "CILEBUT": "CLT", "CIGOMBONG": "CGB",
            "CIOMAS": "COS", "MASENG": "MSG",
        }
        if upper in STATION_NAME_MAP:
            return STATION_NAME_MAP[upper]

        if upper in STATION_TO_BTP:
            if '-' in upper:
                for part in upper.split('-'):
                    if part in STATION_TO_BTP:
                        return part
            return upper
    return None


def normalize_jpl_identifier(ident: str) -> str:
    """Normalize JPL identifier: convert full station names to codes, sort multi-station order.
    
    Examples:
        'JPL 15 MASENG' -> 'JPL 15 MSG'
        'JPL 28 CLT-BOO' -> 'JPL 28 BOO-CLT'  (alphabetical sort)
        'JPL BNR BOP - BTT' -> 'JPL BNR BOP-BTT'  (joined + sorted)
        'JPL 27 BOO-CLT' -> 'JPL 27 BOO-CLT'  (already sorted)
    """
    NAME_TO_CODE = {k: v for k, v in STATION_NAME_TO_CODE.items()}
    for code in STATION_TO_BTP:
        if '-' not in code:
            NAME_TO_CODE[code] = code
    
    parts = ident.split()
    if len(parts) < 3:
        return ident
    
    # Second part may be a number (JPL 28) or a name (JPL BNR)
    prefix = ' '.join(parts[:2])  # "JPL NN" or "JPL BNR"
    station_raw = ' '.join(parts[2:])  # "BOP - BTT" or "CLT-BOO" or "MASENG"
    
    # Normalize spaced dashes: "BOP - BTT" -> "BOP-BTT"
    station_raw = re.sub(r'\s*-\s*', '-', station_raw)
    
    # Split multi-station
    stations = station_raw.split('-')
    normalized = []
    for s in stations:
        upper = s.upper().strip()
        mapped = NAME_TO_CODE.get(upper, upper)
        if mapped == 'CS':
            mapped = 'COS'
        normalized.append(mapped)
    
    normalized.sort()
    return f"{prefix} {'-'.join(normalized)}"


def extract_identifier(funcloc_text: str, category: str) -> str | None:
    """Extract folder identifier from Funcloc/asset description line."""

    # ── Auto-detect category from funcloc prefix if UNKNOWN ──
    if category == "UNKNOWN":
        txt = funcloc_text.strip().upper()
        if txt.startswith("WSL"): category = "WESEL"
        elif txt.startswith("SIN"): category = "SINYAL"
        elif txt.startswith("AXL"): category = "AXC"
        elif "ER " in txt and ("BOGOR" in txt or "CILEBUT" in txt or "BATU TULIS" in txt):
            category = "SERAT OPTIK"
        elif "JPL" in txt:
            category = "JPL"
    
    # ── 2026 (nama lokasi) → 2025 (kode stasiun) mapping for SERAT OPTIK ──
    SERAT_OPTIK_IDENT_MAP_2026_TO_2025 = {
        "ER BOGOR":              "ER SINYAL BOO",
        "ER CILEBUT":            "ER SINYAL CLT",
        "ER BATU TULIS":         "ER SINYAL BTT",
        "ER BOGOR PALEDANG":     "ER SINYAL BOP",
        "ER TELKOM BATU TULIS":  "ER TELKOM BTT",
        "ER CIOMAS":             "ER SINYAL IB COS",
        "ER CIGOMBONG":          "ER SINYAL IB CGB",
        "ER MASENG":             "ER SINYAL MSG",
        "ER TELKOM MASENG":      "ER TELKOM MSG",
        "ER TELKOM CIGOMBONG":   "ER TELKOM CGB",
        "ER TELKOM BOGOR":       "RUANG RADIO BOO",
    }
    
    if category in ("JPL", "PTPP"):
        # First try: named JPL (e.g. "JPL BNR BOP - BTT" from "JPL10489 : PESAWAT TELEPON JPL BNR BOP - BTT")
        desc_part = funcloc_text.split(":", 1)[1].strip() if ":" in funcloc_text else funcloc_text
        STATION_RE = r'(?:BOO|CLT|BJD|BOP|BTT|CGB|COS|CS|MSG|CCR)'
        STATIONS_RE = STATION_RE + r'(?:\s*-\s*' + STATION_RE + r')*'
        # Match: JPL <2-3 letter name> <station codes>
        m = re.search(r'\bJPL\s+([A-Z]{2,3})\s+(' + STATIONS_RE + r')\b', desc_part, re.I)
        if m:
            jpl_name = m.group(1).upper()
            stations_raw = m.group(2).strip()
            if jpl_name not in ("NO", "ELE", "OPT", "FO", "IB"):
                # Named JPL: "BNR BOP - BTT" → normalize to "JPL BNR BOP-BTT"
                raw = f"JPL {jpl_name} {stations_raw}"
                return normalize_jpl_identifier(raw)
        # Second try: "NO 28 CLT-BOO" pattern
        m = re.search(r'(?:NO|JPL)\s*(\d{1,3}[A-Z]?\s+[A-Za-z]{2,3}(?:-[A-Za-z]{2,3})?)', funcloc_text, re.I)
        if m:
            raw = f"JPL {m.group(1).strip()}"
            return normalize_jpl_identifier(raw)
        # Fallback: look for standalone JPL number in code field
        m2 = re.search(r'JPL\s*(\d{1,3}[A-Z]?)', funcloc_text, re.I)
        if m2:
            return f"JPL {m2.group(1)}"
        return None
    
    if category == "SERAT OPTIK":
        m = re.search(r'OTB\s+(?:FO\s+)?(?:\d+\s+)?(.+)', funcloc_text, re.I)
        if m:
            raw = m.group(1).strip()
            return SERAT_OPTIK_IDENT_MAP_2026_TO_2025.get(raw, raw)
        return None
    
    if category == "WESEL":
        # "WSL11086 : PENGGERAK WESEL W31D BOO" → "W31D BOO"
        desc = re.sub(r'^WSL\d+\s*:\s*', '', funcloc_text).strip()
        m = re.search(r'\b(W\d+[A-Z]?\d*)\b', desc, re.I)
        if m:
            w_code = m.group(1)
            codes = re.findall(r'\b(BOO|CLT|BJD|BOP|BTT|CGB|CS|COS|MSG|CCR)\b', desc, re.I)
            station = codes[-1].upper() if codes else "UNKNOWN"
            if station == "CS": station = "COS"
            return f"{w_code} {station}"
        return None

    if category == "AXC":
        # "AXL11584 : AXLE COUNTER ZP 201B CCR - MSG" → "ZP 201B MSG"
        desc = re.sub(r'^AXL\d+\s*:\s*', '', funcloc_text).strip()
        m = re.search(r'\bZP\s*(\d+[A-Z]?)\b', desc, re.I)
        if m:
            zp = f"ZP {m.group(1)}"
            codes = re.findall(r'\b(BOO|CLT|BJD|BOP|BTT|CGB|CS|COS|MSG|CCR)\b', desc, re.I)
            station = codes[-1].upper() if codes else "UNKNOWN"
            if station == "CS": station = "COS"
            return f"{zp} {station}"
        return None

    if category == "SINYAL":
        # "SIN11704 : SINYAL MASUK J10 BOO" → "J10 BOO"
        desc = re.sub(r'^SIN\d+\s*:\s*', '', funcloc_text).strip()
        m = re.search(
            r'\b(JL\s*\d+[A-Z]?|J\d+[A-Z]?|L\d+[A-Z]?|MJ\d+[A-Z]?|'
            r'B\d+[A-Z]?|UB\d+[A-Z]?|MB\d+[A-Z]?|UJ\d+[A-Z]?)\b',
            desc, re.I
        )
        if m:
            sig_code = m.group(1).replace(' ', '')
            codes = re.findall(r'\b(BOO|CLT|BJD|BOP|BTT|CGB|CS|COS|MSG|CCR)\b', desc, re.I)
            station = codes[-1].upper() if codes else "UNKNOWN"
            if station == "CS": station = "COS"
            return f"{sig_code} {station}"
        return None

    # All others: extract station code + RADIO prefix
    codes = re.findall(r'\b(BOO|CLT|BJD|BOP|BTT|CGB|CS|COS|MSG|CCR)\b', funcloc_text, re.I)
    if not codes:
        return None
    
    has_radio = bool(re.search(r'\bRADIO\b', funcloc_text, re.I))
    code = codes[0].upper()
    if code == "CS": code = "COS"
    return f"RADIO_{code}" if has_radio else code


def extract_funcloc_from_text(text: str) -> str | None:
    """Find Funcloc line in page text: prefix like TRA12345, CDA12345, INB12345, etc."""
    FCL_PREFIX = r'(?:TRA|TLK|TWR|INB|CDA|JPL|CTC|OTB|GEN|BNR|SIN|WSL|AXL)\d{4,}'
    for line in text.split('\n'):
        line = line.strip()
        if re.search(FCL_PREFIX + r'\s*:', line, re.I):
            return line
    return None


# ── Output Path ─────────────────────────────────────────────────

def identifier_output_dir(root: Path, btp: str, category: str, identifier: str) -> Path:
    """Return: root/btp/category/identifier/  (flat, no pdf_stem)"""
    return root / sanitize_segment(btp) / category / sanitize_segment(identifier)



# ── Helper: extract all funclocs ──────────────────────────────────

def extract_all_funclocs(page_text: str) -> list[str]:
    """Extract ALL Funcloc lines from page 1 text (for multi-funcloc detection)."""
    FCL_PREFIX = r'(?:TRA|TLK|TWR|INB|CDA|JPL|CTC|OTB|GEN|BNR|SIN|WSL|AXL)\d{4,}'
    results = []
    for line in page_text.split('\n'):
        line = line.strip()
        if re.search(FCL_PREFIX + r'\s*:', line, re.I):
            results.append(line)
    return results


def determine_btp(identifier: str) -> str:
    """Determine BTP from identifier string."""
    if not identifier:
        return "BTP JAK"
    if identifier.startswith("JPL "):
        codes = re.findall(r'\b(BOO|CLT|BJD|BOP|BTT|CGB|CS|COS|MSG|CCR)\b', identifier.upper())
        if codes:
            station = codes[0].upper()
            if station == "CS": station = "COS"
            return STATION_TO_BTP.get(station, "BTP JAK")
    elif identifier.startswith("ER ") or identifier.startswith("RUANG "):
        parts = identifier.split()
        code = STATION_NAME_TO_CODE.get(parts[-1]) if parts else None
        if not code: code = "BOO"
        if code == "CS": code = "COS"
        return STATION_TO_BTP.get(code, "BTP JAK")
    else:
        clean = identifier.replace("RADIO_", "")
        if clean == "CS": clean = "COS"
        return STATION_TO_BTP.get(clean, "BTP JAK")
    return "BTP JAK"


# ── Multi-Row Export (WESEL / SINYAL / AXC) ─────────────────────

def export_multi_row(pdf, reader, photo_page_idx: int, category: str,
                     all_funclocs: list[str], output_root: Path,
                     log_path: Path, log_exists: bool,
                     pdf_name: str) -> int:
    """Export photos from multi-row photo page: 3 photos per asset row.

    WESEL/SINYAL/AXC PDFs have a single photo page with multiple rows.
    Each row has a funcloc text above it, followed by 3 images (0%, 50%, 100%).
    """
    page = pdf.pages[photo_page_idx]
    page_height = float(page.height)

    # Extract words to find funcloc positions
    words = page.extract_words(use_text_flow=True)
    FCL_PAT = re.compile(r'(?:SIN|WSL|AXL)\d{4,}\s*:', re.I)
    funcloc_positions: list[tuple[float, str]] = []
    for w in words:
        txt = str(w.get('text', '') or '').strip()
        if FCL_PAT.search(txt):
            funcloc_positions.append((float(w['top']), txt))
    funcloc_positions.sort(key=lambda x: x[0])

    # Get all images and sort by top
    images = sorted(page.images, key=lambda i: float(i['top']))

    # Group images into rows by clustering top positions (tolerance ~15px)
    rows: list[list] = []
    current_row: list = []
    prev_top = None
    for img in images:
        img_top = float(img['top'])
        if prev_top is None or abs(img_top - prev_top) < 15:
            current_row.append(img)
        else:
            if len(current_row) >= 3:
                rows.append(current_row)
            current_row = [img]
        prev_top = img_top
    if len(current_row) >= 3:
        rows.append(current_row)

    # Map each image row to nearest funcloc above it
    exported = 0
    with log_path.open("a", newline="", encoding="utf-8") as log_file:
        writer = csv.DictWriter(log_file,
            fieldnames=["pdf", "page", "asset_code", "asset_name", "label",
                        "image_name", "output_file", "status"])
        if not log_exists:
            writer.writeheader()

        originals = original_images_by_name(reader, photo_page_idx)

        for row_imgs in rows:
            row_top = float(row_imgs[0]['top'])

            # Find nearest funcloc ABOVE this row
            best_fc = None
            best_dist = float('inf')
            for fc_top, fc_text in funcloc_positions:
                dist = row_top - fc_top
                if 0 < dist < best_dist:
                    best_dist = dist
                    best_fc = fc_text

            if not best_fc:
                # Fallback: match funclocs by order if positions don't align
                row_idx = rows.index(row_imgs)
                if row_idx < len(all_funclocs):
                    best_fc = all_funclocs[row_idx]
                else:
                    writer.writerow({
                        "pdf": pdf_name, "page": page.page_number,
                        "asset_code": "", "asset_name": "",
                        "label": "", "image_name": "",
                        "output_file": "",
                        "status": f"skipped: no funcloc for row top={row_top:.0f}",
                    })
                    continue

            identifier = extract_identifier(best_fc, category)
            if not identifier:
                writer.writerow({
                    "pdf": pdf_name, "page": page.page_number,
                    "asset_code": best_fc, "asset_name": "",
                    "label": "", "image_name": "",
                    "output_file": "",
                    "status": "skipped: could not extract identifier",
                })
                continue

            btp = determine_btp(identifier)
            out_dir = identifier_output_dir(output_root, btp, category, identifier)
            ensure_dir(out_dir)

            # Export 3 photos sorted by x0
            sorted_imgs = sorted(row_imgs, key=lambda i: float(i['x0']))[:3]
            if len(sorted_imgs) < 3:
                writer.writerow({
                    "pdf": pdf_name, "page": page.page_number,
                    "asset_code": best_fc, "asset_name": identifier,
                    "label": "", "image_name": "",
                    "output_file": "",
                    "status": f"skipped: only {len(sorted_imgs)} images in row",
                })
                continue

            for placement, stem in zip(sorted_imgs, ['0', '50', '100']):
                img_name = str(placement.get('name', ''))
                original = originals.get(Path(img_name).stem)
                if not original:
                    try:
                        data = _render_page_and_crop(page, placement)
                        suffix = '.jpg'
                    except Exception:
                        writer.writerow({
                            "pdf": pdf_name, "page": page.page_number,
                            "asset_code": best_fc, "asset_name": identifier,
                            "label": stem, "image_name": img_name,
                            "output_file": "",
                            "status": "failed: original image not found",
                        })
                        continue
                else:
                    suffix, data = original

                out_file = out_dir / f"{stem}{suffix}"
                if os.environ.get("OVERWRITE", "1") == "0" and out_file.exists():
                    continue
                try:
                    out_file.write_bytes(data)
                    exported += 1
                except OSError as exc:
                    writer.writerow({
                        "pdf": pdf_name, "page": page.page_number,
                        "asset_code": best_fc, "asset_name": identifier,
                        "label": stem, "image_name": img_name,
                        "output_file": str(out_file), "status": f"failed: {exc}",
                    })
                    continue
                writer.writerow({
                    "pdf": pdf_name, "page": page.page_number,
                    "asset_code": best_fc, "asset_name": identifier,
                    "label": stem, "image_name": img_name,
                    "output_file": str(out_file), "status": "ok",
                })

    return exported


# ── Core Export ─────────────────────────────────────────────────

def export_pdf(pdf_path: Path, output_root: Path, log_dir: Path,
               start_page: int, _resolution: int,
               input_root: Path = None, sap_mapping: dict = None) -> int:
    """Unified export: detect category from filename, find photos, output to flat identifier structure.

    Output: {output_root}/{btp}/{category}/{identifier}/{0,50,100}.jpg
    """
    if sap_mapping is None:
        sap_mapping = {}

    exported = 0
    log_path = log_dir / "pdf_photo_export_log.csv"
    log_exists = log_path.exists()

    # ── Detect category ──
    category = detect_category_from_filename(pdf_path.name)

    reader = PdfReader(str(pdf_path))

    # ── Read ALL funclocs from page 1 ──
    all_funclocs: list[str] = []
    page1_text = ""
    with pdfplumber.open(str(pdf_path)) as pdf:
        if pdf.pages:
            page1_text = pdf.pages[0].extract_text() or ""
            all_funclocs = extract_all_funclocs(page1_text)

    # Multiple funclocs → force per-row export (each asset row gets own folder)
    force_per_row = len(all_funclocs) > 1

    # ── Fallback: detect category from funcloc prefix if filename detection failed ──
    CATEGORY_FROM_FUNCLOC = {"WSL": "WESEL", "SIN": "SINYAL", "AXL": "AXC"}
    if category == "UNKNOWN" and all_funclocs:
        for fc in all_funclocs:
            for prefix, cat in CATEGORY_FROM_FUNCLOC.items():
                if fc.strip().startswith(prefix):
                    category = cat
                    break
            if category != "UNKNOWN":
                break

    # Multi-row photo page categories (1 row = 1 asset, per-row funcloc)
    MULTI_ROW_CATEGORIES = {"SINYAL", "WESEL", "AXC"}

    # ── Primary identifier & BTP from page 1 ──
    identifier = None
    btp = "BTP JAK"
    if all_funclocs:
        identifier = extract_identifier(all_funclocs[0], category)
    if not identifier:
        # Fallback: use station from filename
        station = extract_station_from_filename(pdf_path.name)
        if station:
            identifier = station
            if "RADIO" in page1_text.upper() and identifier == "BOO":
                identifier = "RADIO_BOO"
        else:
            identifier = pdf_path.stem
    btp = determine_btp(identifier)

    # ── Build primary output directory ──
    out_dir = identifier_output_dir(output_root, btp, category, identifier)
    ensure_dir(out_dir)

    # ── Find photo page ──
    photo_page_idx = None
    with pdfplumber.open(str(pdf_path)) as _detect_pdf:
        for i in range(start_page - 1, len(_detect_pdf.pages)):
            if len(_detect_pdf.pages[i].images) >= 3:
                photo_page_idx = i
                break

    # ── Multi-row export (WESEL / SINYAL / AXC): delegate ──
    if category in MULTI_ROW_CATEGORIES and photo_page_idx is not None:
        with pdfplumber.open(str(pdf_path)) as _multi_pdf:
            return export_multi_row(_multi_pdf, reader, photo_page_idx,
                                    category, all_funclocs, output_root,
                                    log_path, log_exists, pdf_path.name)

    with pdfplumber.open(str(pdf_path)) as pdf, \
         log_path.open("a", newline="", encoding="utf-8") as log_file:

        writer = csv.DictWriter(log_file,
            fieldnames=["pdf", "page", "asset_code", "asset_name", "label",
                        "image_name", "output_file", "status"])
        if not log_exists:
            writer.writeheader()

        if photo_page_idx is not None:
            # ── Single photo page found ──
            if not force_per_row:
                # Standard export: 3 photos → one folder
                page = pdf.pages[photo_page_idx]
                placements = sorted(page.images, key=lambda img: float(img['x0']))
                selected = placements[:3]
                originals = original_images_by_name(reader, photo_page_idx)

                for placement, stem in zip(selected, ['0', '50', '100']):
                    img_name = str(placement.get('name', ''))
                    original = originals.get(Path(img_name).stem)
                    if not original:
                        try:
                            data = _render_page_and_crop(page, placement)
                            suffix = '.jpg'
                        except Exception:
                            writer.writerow({
                                "pdf": pdf_path.name, "page": page.page_number,
                                "asset_code": "", "asset_name": "",
                                "label": stem, "image_name": img_name,
                                "output_file": "", "status": "failed: original image not found",
                            })
                            continue
                    else:
                        suffix, data = original

                    out_file = out_dir / f"{stem}{suffix}"
                    if os.environ.get("OVERWRITE", "1") == "0" and out_file.exists():
                        continue
                    try:
                        out_file.write_bytes(data)
                        exported += 1
                    except OSError as exc:
                        writer.writerow({
                            "pdf": pdf_path.name, "page": page.page_number,
                            "asset_code": "", "asset_name": "",
                            "label": stem, "image_name": img_name,
                            "output_file": str(out_file), "status": f"failed: {exc}",
                        })
                        continue
                    writer.writerow({
                        "pdf": pdf_path.name, "page": page.page_number,
                        "asset_code": "", "asset_name": "",
                        "label": stem, "image_name": img_name,
                        "output_file": str(out_file), "status": "ok",
                    })
            else:
                # ── Multi-funcloc with shared photo page ──
                # Extract photos once, then copy to ALL funcloc folders
                page = pdf.pages[photo_page_idx]
                placements = sorted(page.images, key=lambda img: float(img['x0']))
                selected = placements[:3]
                originals = original_images_by_name(reader, photo_page_idx)

                # Gather photo data once
                photo_data: list[tuple[str, str, bytes]] = []
                for placement, stem in zip(selected, ['0', '50', '100']):
                    img_name = str(placement.get('name', ''))
                    original = originals.get(Path(img_name).stem)
                    if not original:
                        try:
                            data = _render_page_and_crop(page, placement)
                            suffix = '.jpg'
                        except Exception:
                            continue
                    else:
                        suffix, data = original
                    photo_data.append((stem, suffix, data))

                if not photo_data:
                    writer.writerow({
                        "pdf": pdf_path.name, "page": page.page_number,
                        "asset_code": "", "asset_name": "",
                        "label": "", "image_name": "",
                        "output_file": "", "status": "failed: no photos extracted",
                    })
                else:
                    # Export to each funcloc's folder (deduplicate by identifier)
                    written_identifiers: set[str] = set()
                    for funcloc_line in all_funclocs:
                        row_id = extract_identifier(funcloc_line, category)
                        if not row_id or row_id in written_identifiers:
                            continue
                        written_identifiers.add(row_id)
                        row_btp = determine_btp(row_id)
                        row_out_dir = identifier_output_dir(output_root, row_btp, category, row_id)
                        ensure_dir(row_out_dir)

                        for stem, suffix, data in photo_data:
                            out_file = row_out_dir / f"{stem}{suffix}"
                            try:
                                out_file.write_bytes(data)
                                exported += 1
                            except OSError as exc:
                                writer.writerow({
                                    "pdf": pdf_path.name, "page": page.page_number,
                                    "asset_code": funcloc_line, "asset_name": "",
                                    "label": stem, "image_name": "",
                                    "output_file": str(out_file), "status": f"failed: {exc}",
                                })
                                continue
                            writer.writerow({
                                "pdf": pdf_path.name, "page": page.page_number,
                                "asset_code": funcloc_line, "asset_name": "",
                                "label": stem, "image_name": "",
                                "output_file": str(out_file), "status": "ok",
                            })
        else:
            # Old-format / multi-funcloc: per-page per-asset export
            # Each asset row gets its own folder with 0.jpg, 50.jpg, 100.jpg
            global_assets = extract_asset_rows(pdf.pages[0], sap_mapping) if pdf.pages else []

            for page_index in range(start_page - 1, len(pdf.pages)):
                page = pdf.pages[page_index]
                rows = extract_asset_rows(page, sap_mapping)
                page_height = float(page.height)
                originals = original_images_by_name(reader, page_index)

                if not rows:
                    continue

                for idx, row in enumerate(rows):
                    # Resolve station from global assets
                    if row.station == "UNKNOWN":
                        for ga in global_assets:
                            if ga.code == row.code and ga.station != "UNKNOWN":
                                row.station = ga.station
                                break

                    # ── Determine identifier for THIS row ──
                    funcloc_line = f"{row.code}: {row.title}"
                    row_identifier = extract_identifier(funcloc_line, category)
                    if not row_identifier:
                        # Fallback: use station > code > detail
                        if row.station != "UNKNOWN":
                            has_radio = bool(re.search(r'\bRADIO\b', row.title, re.I))
                            row_identifier = f"RADIO_{row.station}" if has_radio else row.station
                        else:
                            row_identifier = row.code or row.detail
                    if not row_identifier:
                        row_identifier = identifier  # fallback to primary

                    # ── Determine BTP for this row ──
                    row_btp = determine_btp(row_identifier)

                    # ── Create output folder for this row ──
                    row_out_dir = identifier_output_dir(output_root, row_btp, category, row_identifier)
                    ensure_dir(row_out_dir)

                    # ── Pick images in this row's Y range ──
                    next_top = rows[idx + 1].top if idx + 1 < len(rows) else page_height
                    row_start = max(0.0, row.top - 2.0)
                    row_end = min(page_height, next_top - 2.0)
                    placements = sorted(
                        [img for img in page.images
                         if row_start <= (float(img['top']) + float(img['bottom'])) / 2 < row_end],
                        key=lambda img: float(img['x0'])
                    )

                    if len(placements) < 3:
                        writer.writerow({
                            "pdf": pdf_path.name, "page": page.page_number,
                            "asset_code": row.code, "asset_name": row.title,
                            "label": "", "image_name": "",
                            "output_file": "", "status": f"skipped: {len(placements)} placements",
                        })
                        continue

                    for p_idx, (placement, stem) in enumerate(zip(placements[:3], ['0', '50', '100'])):
                        img_name = str(placement.get('name', ''))
                        original = originals.get(Path(img_name).stem)
                        if not original:
                            try:
                                data = _render_page_and_crop(page, placement)
                                suffix = '.jpg'
                            except Exception:
                                writer.writerow({
                                    "pdf": pdf_path.name, "page": page.page_number,
                                    "asset_code": row.code, "asset_name": row.title,
                                    "label": stem, "image_name": img_name,
                                    "output_file": "", "status": "failed: original image not found",
                                })
                                continue
                        else:
                            suffix, data = original

                        out_file = row_out_dir / f"{stem}{suffix}"
                        if os.environ.get("OVERWRITE", "1") == "0" and out_file.exists():
                            continue
                        try:
                            out_file.write_bytes(data)
                            exported += 1
                        except OSError as exc:
                            writer.writerow({
                                "pdf": pdf_path.name, "page": page.page_number,
                                "asset_code": row.code, "asset_name": row.title,
                                "label": stem, "image_name": img_name,
                                "output_file": str(out_file), "status": f"failed: {exc}",
                            })
                            continue
                        writer.writerow({
                            "pdf": pdf_path.name, "page": page.page_number,
                            "asset_code": row.code, "asset_name": row.title,
                            "label": stem, "image_name": img_name,
                            "output_file": str(out_file), "status": "ok",
                        })

    return exported


# ── Main ────────────────────────────────────────────────────────

def resolve_inputs(args: argparse.Namespace) -> list[Path]:
    if args.paths:
        return [Path(path) for path in args.paths]
    return list_pdf_files(Path(args.input))


def main() -> int:
    args = parse_args()
    pdf_paths = resolve_inputs(args)
    if not pdf_paths:
        print("Tidak ada file PDF untuk diproses.")
        return 1

    sap_mapping = load_sap_mapping(args.sap_mapping)
    if sap_mapping:
        print(f"[INFO] Loaded SAP mapping: {len(sap_mapping)} Functional Locations")
    else:
        print("[WARNING] No SAP mapping loaded")

    input_root = Path(args.input)
    output_root = Path(args.output)
    log_dir = Path(args.log_dir)
    ensure_dir(output_root)
    ensure_dir(log_dir)

    total = 0
    for pdf_path in pdf_paths:
        if not pdf_path.exists():
            print(f"[SKIP] Tidak ditemukan: {pdf_path}")
            continue
        exported = export_pdf(pdf_path, output_root, log_dir,
                              args.start_page, args.resolution, input_root, sap_mapping)
        total += exported
        print(f"[OK] {pdf_path.name}: {exported} foto diekspor")

    print(f"Selesai. Total foto diekspor: {total}")
    return 0 if total > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
