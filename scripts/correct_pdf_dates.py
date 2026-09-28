#!/usr/bin/env python3
"""Audit dan koreksi tanggal halaman pertama PDF mengikuti tanggal filename."""
import argparse
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

import fitz

FILENAME_DATE = re.compile(r"(?<!\d)(\d{2})-(\d{2})-(\d{4})(?!\d)")
PDF_DATE = re.compile(r"(?<!\d)(\d{4}-\d{2}-\d{2}|\d{2}-\d{2}-\d{4})(?!\d)")
INDONESIAN_MONTHS = (
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
)
PHOTO_DATE = re.compile(
    rf"(?<!\d)(\d{{1,2}})\s+({'|'.join(INDONESIAN_MONTHS)})\s+(\d{{4}})(?!\d)", re.I
)


def filename_date(name: str) -> tuple[str, str] | None:
    matches = list(FILENAME_DATE.finditer(name))
    if not matches:
        return None
    day, month, year = matches[-1].groups()
    return f"{day}-{month}-{year}", f"{year}-{month}-{day}"


def find_page_date(page) -> dict | None:
    """Temukan nilai tanggal pada baris visual berlabel Tanggal."""
    spans = [
        span
        for block in page.get_text("dict").get("blocks", [])
        for line in block.get("lines", [])
        for span in line.get("spans", [])
        if span.get("text", "").strip()
    ]
    labels = [span for span in spans if re.search(r"\bTanggal\b", span["text"], re.I)]

    # Format sederhana: label dan nilai berada dalam span yang sama.
    for label in labels:
        match = PDF_DATE.search(label["text"])
        if match:
            return {"value": match.group(1), "span": label}

    # Layout tabel: label, titik dua, dan nilai tersimpan sebagai span/blok terpisah.
    candidates = []
    for label in labels:
        label_box = fitz.Rect(label["bbox"])
        label_y = (label_box.y0 + label_box.y1) / 2
        for span in spans:
            match = PDF_DATE.search(span["text"])
            if not match:
                continue
            box = fitz.Rect(span["bbox"])
            span_y = (box.y0 + box.y1) / 2
            gap = box.x0 - label_box.x1
            if abs(span_y - label_y) <= 8 and -2 <= gap <= 250:
                candidates.append((abs(span_y - label_y) * 10 + max(gap, 0), match.group(1), span))
    if candidates:
        _, value, span = min(candidates, key=lambda item: item[0])
        return {"value": value, "span": span}

    # PDF tertentu memecah tanggal menjadi "2025-07-" dan "15" pada dua baris.
    for label in labels:
        label_box = fitz.Rect(label["bbox"])
        label_y = (label_box.y0 + label_box.y1) / 2
        prefixes = [span for span in spans if re.fullmatch(r"\d{4}-\d{2}-", span["text"].strip())]
        days = [span for span in spans if re.fullmatch(r"\d{2}", span["text"].strip())]
        for prefix in prefixes:
            prefix_box = fitz.Rect(prefix["bbox"])
            if prefix_box.x0 < label_box.x1 or abs(((prefix_box.y0 + prefix_box.y1) / 2) - label_y) > 12:
                continue
            for day in days:
                day_box = fitz.Rect(day["bbox"])
                if abs(day_box.x0 - prefix_box.x0) > 40 or abs(day_box.y0 - prefix_box.y0) > 18:
                    continue
                value = prefix["text"].strip() + day["text"].strip()
                if not PDF_DATE.fullmatch(value):
                    continue
                combined = dict(prefix)
                combined["bbox"] = tuple(prefix_box | day_box)
                combined["origin"] = (prefix["origin"][0], label["origin"][1])
                combined["text"] = value
                return {"value": value, "span": combined}
    return None


def find_page_date_ocr(page) -> dict | None:
    """Baca tanggal dari render halaman hanya jika text layer tidak tersedia."""
    try:
        import pytesseract
        from PIL import Image

        tesseract = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if tesseract.is_file():
            pytesseract.pytesseract.tesseract_cmd = str(tesseract)
        pix = page.get_pixmap(dpi=300, alpha=False)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        rough = pytesseract.image_to_data(
            image, config="--psm 12 -l eng", output_type=pytesseract.Output.DICT
        )
        scale = 72 / 300
        candidates = []
        for i, text in enumerate(rough["text"]):
            if text.strip().lower() != "tanggal" or float(rough["conf"][i]) < 50:
                continue
            left, top = rough["left"][i], rough["top"][i]
            height = rough["height"][i]
            crop_left = max(0, left - 30)
            crop_top = max(0, top - 15)
            crop_right = min(image.width, left + int(image.width * 0.4))
            crop_bottom = min(image.height, top + height + 20)
            crop = image.crop((crop_left, crop_top, crop_right, crop_bottom))
            data = pytesseract.image_to_data(
                crop, config="--psm 7 -l eng", output_type=pytesseract.Output.DICT
            )
            for j, token in enumerate(data["text"]):
                match = PDF_DATE.fullmatch(token.strip())
                if not match or float(data["conf"][j]) < 70:
                    continue
                value = match.group(1)
                fmt = "%Y-%m-%d" if value[:4].isdigit() else "%d-%m-%Y"
                try:
                    datetime.strptime(value, fmt)
                except ValueError:
                    continue
                x0 = crop_left + data["left"][j]
                y0 = crop_top + data["top"][j]
                x1 = x0 + data["width"][j]
                y1 = y0 + data["height"][j]
                candidates.append({
                    "value": value,
                    "confidence": float(data["conf"][j]),
                    "span": {
                        "text": value,
                        "bbox": (x0 * scale, y0 * scale, x1 * scale, y1 * scale),
                        "origin": (x0 * scale, y1 * scale),
                        "size": max(6.0, data["height"][j] * scale * 1.3),
                        "font": "",
                    },
                })
        unique = {item["value"] for item in candidates}
        if len(unique) == 1:
            return max(candidates, key=lambda item: item["confidence"])
    except Exception:
        return None
    return None


def find_photo_dates(page) -> list[dict]:
    """Temukan tanggal Indonesia pada header halaman FOTO DOKUMENTASI."""
    if "FOTO DOKUMENTASI" not in page.get_text().upper():
        return []
    found = []
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                match = PHOTO_DATE.search(span.get("text", ""))
                if not match:
                    continue
                day, month_name, year = match.groups()
                month = next((i for i, name in enumerate(INDONESIAN_MONTHS, 1)
                              if name.lower() == month_name.lower()), None)
                if month:
                    found.append({
                        "value": match.group(0),
                        "iso": f"{year}-{month:02d}-{int(day):02d}",
                        "span": span,
                    })
    return found


def find_photo_dates_ocr(page) -> list[dict]:
    """Baca tanggal header FOTO DOKUMENTASI, bukan watermark di dalam foto."""
    try:
        import pytesseract
        from PIL import Image

        tesseract = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if tesseract.is_file():
            pytesseract.pytesseract.tesseract_cmd = str(tesseract)
        pix = page.get_pixmap(dpi=300, alpha=False)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        data = pytesseract.image_to_data(
            image, config="--psm 12 -l eng", output_type=pytesseract.Output.DICT
        )
        words = [
            {
                "text": text.strip(),
                "conf": float(data["conf"][i]),
                "left": data["left"][i],
                "top": data["top"][i],
                "width": data["width"][i],
                "height": data["height"][i],
                "line": (data["block_num"][i], data["par_num"][i], data["line_num"][i]),
            }
            for i, text in enumerate(data["text"])
            if text.strip() and float(data["conf"][i]) >= 50
        ]
        title_y = next(
            (word["top"] for word in words if word["text"].upper() == "DOKUMENTASI"), None
        )
        if title_y is None:
            return []
        scale = 72 / 300
        lines = {}
        for word in words:
            if title_y < word["top"] < title_y + 400:
                lines.setdefault(word["line"], []).append(word)
        found = []
        for line_words in lines.values():
            line_words.sort(key=lambda word: word["left"])
            text = " ".join(word["text"] for word in line_words)
            match = PHOTO_DATE.search(text)
            if not match:
                continue
            day, month_name, year = match.groups()
            month = next((i for i, name in enumerate(INDONESIAN_MONTHS, 1)
                          if name.lower() == month_name.lower()), None)
            if not month:
                continue
            matched = [word for word in line_words if any(part in word["text"] for part in match.groups())]
            if not matched:
                continue
            x0 = min(word["left"] for word in matched)
            y0 = min(word["top"] for word in matched)
            x1 = max(word["left"] + word["width"] for word in matched)
            y1 = max(word["top"] + word["height"] for word in matched)
            found.append({
                "value": match.group(0),
                "iso": f"{year}-{month:02d}-{int(day):02d}",
                "span": {
                    "text": match.group(0),
                    "bbox": (x0 * scale, y0 * scale, x1 * scale, y1 * scale),
                    "origin": (x0 * scale, y1 * scale),
                    "size": max(6.0, (y1 - y0) * scale * 1.3),
                    "font": "",
                },
            })
        return found
    except Exception:
        return []


def audit_file(path: Path, root: Path) -> dict:
    result = {
        "file": path.name,
        "relative_path": str(path.relative_to(root)),
        "pdf_path": str(path.resolve()),
        "filename_date": "-",
        "pdf_date": "-",
        "date_source": "-",
        "status": "",
        "error": "",
    }
    target = filename_date(path.name)
    if not target:
        result["status"] = "FILENAME TANPA TANGGAL"
        return result
    result["filename_date"] = target[0]
    try:
        with fitz.open(path) as doc:
            found = find_page_date(doc[0]) if len(doc) else None
            if found:
                result["date_source"] = "TEXT LAYER"
            elif len(doc):
                found = find_page_date_ocr(doc[0])
                if found:
                    result["date_source"] = "OCR"
            photo_dates = []
            for page in doc:
                page_dates = find_photo_dates(page)
                if not page_dates and len(page.get_text("words")) < 10:
                    page_dates = find_photo_dates_ocr(page)
                photo_dates.extend(page_dates)
    except Exception as exc:
        result["status"], result["error"] = "GAGAL DIBACA", str(exc)
        return result
    if not found:
        result["status"] = "TANGGAL TIDAK TERBACA"
        return result
    result["pdf_date"] = found["value"]
    result["photo_dates"] = [item["value"] for item in photo_dates]
    current_ymd = found["value"] if found["value"][:4].isdigit() else "-".join(reversed(found["value"].split("-")))
    dates_match = current_ymd == target[1] and all(item["iso"] == target[1] for item in photo_dates)
    result["status"] = "SESUAI" if dates_match else "BERBEDA"
    return result


def correct_file(source: Path, destination: Path) -> None:
    target = filename_date(source.name)
    if not target:
        raise ValueError("filename tanpa tanggal")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_suffix(".tmp.pdf")
    temp.unlink(missing_ok=True)
    try:
        with fitz.open(source) as doc:
            if not len(doc):
                raise ValueError("PDF tidak memiliki halaman")
            found = find_page_date(doc[0])
            if not found:
                found = find_page_date_ocr(doc[0])
            if not found:
                raise ValueError("tanggal setelah label Tanggal tidak ditemukan")
            span = found["span"]
            original = found["value"]
            replacement = target[1] if original[:4].isdigit() else target[0]
            fontsize = span.get("size", 7.8)
            page = doc[0]

            # Gunakan bbox hasil pencarian teks, bukan lebar font pengganti.
            # Font berbeda dapat membuat area redaksi terlalu pendek dan menyisakan angka lama.
            span_box = fitz.Rect(span["bbox"])
            matches = [rect for rect in page.search_for(original) if rect.intersects(span_box)]
            date_box = min(matches, key=lambda rect: abs(rect.x0 - span_box.x0)) if matches else span_box
            date_x = date_box.x0

            # Gunakan file font DejaVu Sans utuh. Font subset embedded PDF tidak aman
            # untuk ditulis ulang karena encoding-nya dapat berubah menjadi karakter nol.
            original_font = span.get("font", "")
            fontfile = None
            try:
                import matplotlib
                candidate = Path(matplotlib.get_data_path()) / "fonts" / "ttf" / (
                    "DejaVuSans-Bold.ttf" if "bold" in original_font.lower() else "DejaVuSans.ttf"
                )
                if candidate.is_file():
                    fontfile = candidate
            except Exception:
                pass

            page.add_redact_annot(
                fitz.Rect(date_box.x0 - 1.5, date_box.y0 - 1, date_box.x1 + 1.5, date_box.y1 + 1),
                fill=(1, 1, 1),
            )
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

            if fontfile:
                fontname = "date_original"
                page.insert_font(fontname=fontname, fontfile=str(fontfile))
            else:
                fontname = "hebo" if "bold" in original_font.lower() else "helv"
                fontsize *= 1.18  # Samakan tinggi visual fallback Helvetica dengan DejaVu Sans.
            page.insert_text((date_x, span["origin"][1]), replacement, fontname=fontname,
                             fontsize=fontsize, color=(0, 0, 0))

            # Koreksi hanya teks header halaman FOTO DOKUMENTASI. Isi gambar dan
            # watermark di dalam foto tidak dipindai maupun diubah.
            day, month, year = target[0].split("-")
            photo_replacement = f"{int(day)} {INDONESIAN_MONTHS[int(month) - 1]} {year}"
            for photo_page in doc:
                photo_dates = find_photo_dates(photo_page)
                if not photo_dates and not photo_page.get_text().strip():
                    photo_dates = find_photo_dates_ocr(photo_page)
                if not photo_dates:
                    continue
                for photo_date in photo_dates:
                    photo_span = photo_date["span"]
                    photo_box = fitz.Rect(photo_span["bbox"])
                    photo_page.add_redact_annot(
                        fitz.Rect(photo_box.x0 - 1.5, photo_box.y0 - 1,
                                  photo_box.x1 + 1.5, photo_box.y1 + 1),
                        fill=(1, 1, 1),
                    )
                photo_page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
                for photo_date in photo_dates:
                    photo_span = photo_date["span"]
                    photo_font = photo_span.get("font", "")
                    photo_fontsize = photo_span.get("size", 7.8)
                    photo_fontname = "hebo" if "bold" in photo_font.lower() else "helv"
                    if fontfile:
                        photo_fontname = f"date_photo_{photo_page.number}"
                        photo_page.insert_font(fontname=photo_fontname, fontfile=str(fontfile))
                    photo_page.insert_text(
                        photo_span["origin"], photo_replacement,
                        fontname=photo_fontname, fontsize=photo_fontsize, color=(0, 0, 0),
                    )
            doc.save(temp, garbage=0, deflate=False)
        temp.replace(destination)
    except Exception:
        temp.unlink(missing_ok=True)
        if source.resolve() != destination.resolve():
            destination.unlink(missing_ok=True)
        raise


def run(input_dir: Path, output_dir: Path | None = None) -> dict:
    files = sorted(input_dir.rglob("*.pdf"))
    records = [audit_file(path, input_dir) for path in files]
    corrected, failed = 0, 0
    if output_dir:
        for record in records:
            if record["status"] != "BERBEDA":
                continue
            try:
                destination = output_dir / record["relative_path"]
                correct_file(Path(record["pdf_path"]), destination)
                verified = audit_file(destination, output_dir)
                record.update({key: verified.get(key, record.get(key)) for key in
                               ("pdf_date", "photo_dates", "status", "error")})
                record["correction"] = "BERHASIL"
                corrected += 1
            except Exception as exc:
                record["correction"] = "GAGAL"
                record["error"] = str(exc)
                failed += 1
    counts = {status: sum(r["status"] == status for r in records) for status in (
        "SESUAI", "BERBEDA", "TANGGAL TIDAK TERBACA", "FILENAME TANPA TANGGAL", "GAGAL DIBACA")}
    return {"success": True, "input": str(input_dir), "output": str(output_dir or ""),
            "total": len(records), "counts": counts, "corrected": corrected,
            "failed": failed, "files": records}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output")
    parser.add_argument("--report")
    args = parser.parse_args()
    input_dir = Path(args.input).resolve()
    if not input_dir.is_dir():
        raise SystemExit(f"Folder input tidak ditemukan: {input_dir}")
    output_dir = Path(args.output).resolve() if args.output else None
    if output_dir and output_dir != input_dir and input_dir in output_dir.parents:
        raise SystemExit("Folder output tidak boleh berada di dalam folder input")
    result = run(input_dir, output_dir)
    if args.report:
        report = Path(args.report)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
