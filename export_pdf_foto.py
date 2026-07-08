import argparse
import csv
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import pdfplumber
from pypdf import PdfReader


DEFAULT_INPUT_DIR = "./input_pdf"
DEFAULT_OUTPUT_DIR = "./output_pdf_foto"
DEFAULT_LOG_DIR = "./logs"
DEFAULT_START_PAGE = 2
DEFAULT_RESOLUTION = 220


@dataclass
class AssetRow:
    page_number: int
    code: str
    title: str
    asset_type: str
    detail: str
    top: float


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
    return parser.parse_args()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def list_pdf_files(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(
        [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"]
    )


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def sanitize_segment(text: str) -> str:
    text = normalize_spaces(text)
    text = "".join("_" if ord(char) < 32 else char for char in text)
    text = re.sub(r'[<>:"/\\|?*]', "_", text)
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

    if not detail:
        detail = original

    return sanitize_segment(detail)


def extract_asset_rows(page: pdfplumber.page.Page) -> list[AssetRow]:
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
        rows.append(
            AssetRow(
                page_number=page.page_number,
                code=code,
                title=title,
                asset_type=asset_type,
                detail=detail,
                top=top,
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


def asset_output_dir(root: Path, asset_type: str, detail: str) -> Path:
    return root / sanitize_segment(asset_type) / sanitize_segment(detail)


def export_pdf(pdf_path: Path, output_root: Path, log_dir: Path, start_page: int, _resolution: int) -> int:
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

        for page_index in range(start_page - 1, len(pdf.pages)):
            page = pdf.pages[page_index]
            rows = extract_asset_rows(page)
            if not rows:
                continue

            page_height = float(page.height)
            originals = original_images_by_name(reader, page_index)

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
                out_dir = asset_output_dir(output_root, row.asset_type, row.detail)
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

    output_root = Path(args.output)
    log_dir = Path(args.log_dir)
    ensure_dir(output_root)
    ensure_dir(log_dir)

    total = 0
    for pdf_path in pdf_paths:
        if not pdf_path.exists():
            print(f"[SKIP] Tidak ditemukan: {pdf_path}")
            continue
        exported = export_pdf(pdf_path, output_root, log_dir, args.start_page, args.resolution)
        total += exported
        print(f"[OK] {pdf_path.name}: {exported} foto diekspor")

    print(f"Selesai. Total foto diekspor: {total}")
    return 0 if total > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
