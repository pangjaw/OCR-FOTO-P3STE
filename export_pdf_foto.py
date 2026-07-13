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


DEFAULT_INPUT_DIR = "./01_pdf_source"
DEFAULT_OUTPUT_DIR = "./03_photos_export"
DEFAULT_LOG_DIR = "./logs"
DEFAULT_START_PAGE = 2
DEFAULT_RESOLUTION = 220
SAP_MAPPING_PATH = "./sap_station_mapping.json"


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export foto dokumentasi dari PDF berdasarkan aset dan label persen."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="PDF yang diproses. Jika kosong, script akan ambil semua PDF dari --input.",
    )
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT_DIR,
        help=f"Folder PDF input jika paths kosong. Default: {DEFAULT_INPUT_DIR}",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Folder output utama. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--log-dir",
        default=DEFAULT_LOG_DIR,
        help=f"Folder log. Default: {DEFAULT_LOG_DIR}",
    )
    parser.add_argument(
        "--start-page",
        type=int,
        default=DEFAULT_START_PAGE,
        help="Nomor halaman awal scan aset. Default: 2",
    )
    parser.add_argument(
        "--resolution",
        type=int,
        default=DEFAULT_RESOLUTION,
        help="Diabaikan saat export original image; tetap diterima untuk kompatibilitas perintah lama.",
    )
    parser.add_argument(
        "--sap-mapping",
        default=SAP_MAPPING_PATH,
        help=f"Path ke file mapping SAP Functional Location -> Station. Default: {SAP_MAPPING_PATH}",
    )
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
    """Load SAP Functional Location -> Station mapping from JSON file."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        # Create mapping: functional_loc -> station
        mapping = {}
        for floc, info in data.items():
            mapping[floc] = info.get("station", "UNKNOWN")
        return mapping
    except FileNotFoundError:
        print(f"[WARNING] SAP mapping file not found at {path}. Using description-based station extraction.")
        return {}
    except json.JSONDecodeError as e:
        print(f"[WARNING] Invalid JSON in SAP mapping file: {e}")
        return {}


def detect_asset_type(code: str, title: str) -> str:
    upper = f"{code} {title}".upper()
    # Check code prefixes FIRST (more specific) before title keywords
    if code.startswith("AXL"):
        return "AXC"
    if code.startswith("WSL"):
        return "WESEL"
    if code.startswith("CDA"):  # CDA = CATU DAYA - check before SINYAL
        return "CATU_DAYA"
    if code.startswith("SIN"):
        return "SINYAL"
    if code.startswith("JPL"):
        return "PINTU_PERLINTASAN"
    if code.startswith("TLK") or code.startswith("TWR"):
        return "TELEKOMUNIKASI"
    if code.startswith("INB") or code.startswith("TRA"):
        return "PERSINYALAN_ELEKTRIK"
    # Fallback to title keywords
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
    if "TELEKOMUNIKASI" in upper or "RADIO" in upper or "SERAT OPTIK" in upper:
        return "TELEKOMUNIKASI"
    if "PERSINYALAN ELEKTRIK" in upper:
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
        detail = after("CATU DAYA") or after("UPS") or after("BATTERE") or after("GENSET")
    elif asset_type == "PINTU_PERLINTASAN":
        detail = after("PINTU PERLINTASAN") or after("JPL")
    elif asset_type == "TELEKOMUNIKASI":
        detail = after("TELEKOMUNIKASI") or after("RADIO") or after("WAYSTATION") or after("SERAT OPTIK")
    elif asset_type == "PERSINYALAN_ELEKTRIK":
        detail = after("PERSINYALAN ELEKTRIK") or after("INTERMEDIATE BLOK") or after("TRACK CIRCUIT")

    if not detail:
        detail = original

    res = sanitize_segment(detail)
    if res == "ZP 41B BOO":
        res = "ZP 41 BOO"
    return res


def extract_station_from_description(desc: str, sap_mapping: dict, funcloc: str) -> str:
    """Extract station code from description or SAP mapping."""
    # First try SAP mapping using Functional Location code
    if funcloc and funcloc in sap_mapping:
        return sap_mapping[funcloc]

    # Fallback: extract from description (last word if it's a known station code)
    station_codes = {"BOO", "BOP", "BTT", "CLT", "MSG", "CGB", "BJD", "CCR", "COS", "CS", "BNR"}
    words = normalize_spaces(desc).split()
    for word in reversed(words):
        if word in station_codes:
            return word

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

        title = normalize_spaces(" ".join(word["text"] for word in words[code_index + 1 :])).lstrip(": -")
        if not title:
            continue

        asset_type = detect_asset_type(code, title)
        detail = extract_detail(title, asset_type)

        # Extract station using SAP mapping or description fallback
        station = extract_station_from_description(title, sap_mapping, code)

        rows.append(
            AssetRow(
                page_number=page.page_number,
                code=code,
                title=title,
                asset_type=asset_type,
                detail=detail,
                top=top,
                station=station,
                funcloc=code,
            )
        )

    return rows


def pick_image_placements(page: pdfplumber.page.Page, row_start: float, row_end: float) -> list[dict]:
    placements = []
    for image in page.images:
        center_y = (float(image["top"]) + float(image["bottom"])) / 2
        if row_start <= center_y < row_end:
            placements.append(image)
    placements.sort(key=lambda item: float(item["x0"]))
    return placements


def original_images_by_name(reader: PdfReader, page_index: int) -> dict[str, tuple[str, bytes]]:
    images = {}
    for image in reader.pages[page_index].images:
        suffix = Path(image.name).suffix.lower() or ".jpg"
        images[Path(image.name).stem] = (suffix, image.data)
    return images


def asset_output_dir(root: Path, station: str, asset_type: str, detail: str) -> Path:
    """Return output directory with station in path: root/station/asset_type/detail"""
    return root / sanitize_segment(station) / sanitize_segment(asset_type) / sanitize_segment(detail)


def export_pdf(pdf_path: Path, output_root: Path, log_dir: Path, start_page: int, _resolution: int, input_root: Path = None, sap_mapping: dict = None) -> int:
    exported = 0
    log_path = log_dir / "pdf_photo_export_log.csv"
    log_exists = log_path.exists()

    reader = PdfReader(str(pdf_path))
    with pdfplumber.open(str(pdf_path)) as pdf, log_path.open("a", newline="", encoding="utf-8") as log_file:
        writer = csv.DictWriter(
            log_file,
            fieldnames=["pdf", "page", "asset_code", "asset_name", "label", "image_name", "output_file", "status"],
        )
        if not log_exists:
            writer.writeheader()

        # Ekstrak global assets dari Halaman 1 sebagai fallback (Case B)
        global_assets = extract_asset_rows(pdf.pages[0], sap_mapping or {})

        for page_index in range(start_page - 1, len(pdf.pages)):
            page = pdf.pages[page_index]
            rows = extract_asset_rows(page, sap_mapping or {})

            page_height = float(page.height)
            originals = original_images_by_name(reader, page_index)

            if rows:
                # Case A: Ada baris aset di halaman foto (Format 2026 / Per-Asset Photos)
                for idx, row in enumerate(rows):
                    next_top = rows[idx + 1].top if idx + 1 < len(rows) else page_height
                    row_start = max(0.0, row.top - 2.0)
                    row_end = min(page_height, next_top - 2.0)
                    placements = pick_image_placements(page, row_start, row_end)

                    if len(placements) < 3:
                        writer.writerow(
                            {
                                "pdf": pdf_path.name,
                                "page": page.page_number,
                                "asset_code": row.code,
                                "asset_name": row.title,
                                "label": "",
                                "image_name": "",
                                "output_file": "",
                                "status": f"skipped: found {len(placements)} placements",
                            }
                        )
                        continue

                    labels = ["0%", "50%", "100%"]
                    out_dir = asset_output_dir(output_root, row.station, row.asset_type, row.detail)
                    ensure_dir(out_dir)

                    for placement, label, stem in zip(placements[:3], labels, ["0", "50", "100"]):
                        original = originals.get(str(placement.get("name", "")))
                        if not original:
                            writer.writerow(
                                {
                                    "pdf": pdf_path.name,
                                    "page": page.page_number,
                                    "asset_code": row.code,
                                    "asset_name": row.title,
                                    "label": label,
                                    "image_name": str(placement.get("name", "")),
                                    "output_file": "",
                                    "status": "failed: original image not found",
                                }
                            )
                            continue

                        suffix, data = original
                        filename = f"{stem}{suffix}"
                        out_file = out_dir / filename
                        if os.environ.get("OVERWRITE", "1") == "0" and out_file.exists():
                            continue
                        status = "ok"
                        try:
                            out_file.write_bytes(data)
                            exported += 1
                        except OSError as exc:
                            status = f"failed: {exc}"
                        writer.writerow(
                            {
                                "pdf": pdf_path.name,
                                "page": page.page_number,
                                "asset_code": row.code,
                                "asset_name": row.title,
                                "label": label,
                                "image_name": filename,
                                "output_file": str(out_file),
                                "status": status,
                            }
                        )
            else:
                # Case B: Tidak ada baris aset di halaman ini (Format Lama / Shared Photos Page)
                # Ambil semua penempatan gambar di halaman ini
                placements = sorted(page.images, key=lambda item: float(item["x0"]))
                if len(placements) >= 3 and global_assets:
                    for row in global_assets:
                        # Lewati jika tipe aset tidak dikenal
                        if row.asset_type == "UNKNOWN":
                            continue

                        labels = ["0%", "50%", "100%"]
                        out_dir = asset_output_dir(output_root, row.station, row.asset_type, row.detail)
                        ensure_dir(out_dir)

                        for placement, label, stem in zip(placements[:3], labels, ["0", "50", "100"]):
                            original = originals.get(str(placement.get("name", "")))
                            if not original:
                                writer.writerow(
                                    {
                                        "pdf": pdf_path.name,
                                        "page": page.page_number,
                                        "asset_code": row.code,
                                        "asset_name": row.title,
                                        "label": label,
                                        "image_name": str(placement.get("name", "")),
                                        "output_file": "",
                                        "status": "failed: original image not found",
                                    }
                                )
                                continue

                            suffix, data = original
                            filename = f"{stem}{suffix}"
                            out_file = out_dir / filename
                            if os.environ.get("OVERWRITE", "1") == "0" and out_file.exists():
                                continue
                            status = "ok"
                            try:
                                out_file.write_bytes(data)
                                exported += 1
                            except OSError as exc:
                                status = f"failed: {exc}"
                            writer.writerow(
                                {
                                    "pdf": pdf_path.name,
                                    "page": page.page_number,
                                    "asset_code": row.code,
                                    "asset_name": row.title,
                                    "label": label,
                                    "image_name": filename,
                                    "output_file": str(out_file),
                                    "status": status,
                                }
                            )

    return exported


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

    # Load SAP mapping
    sap_mapping = load_sap_mapping(args.sap_mapping)
    if sap_mapping:
        print(f"[INFO] Loaded SAP mapping: {len(sap_mapping)} Functional Locations")
    else:
        print("[WARNING] No SAP mapping loaded, using description-based station extraction")

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
        exported = export_pdf(pdf_path, output_root, log_dir, args.start_page, args.resolution, input_root, sap_mapping)
        total += exported
        print(f"[OK] {pdf_path.name}: {exported} foto diekspor")

    print(f"Selesai. Total foto diekspor: {total}")
    return 0 if total > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
