"""
Employee Manager Module for OCR-FOTO-P3STE.

Handles:
1. Loading personnel configuration (KAUR & PNC) from config/daftar_pegawai.json.
2. Detecting personnel assigned to Tim 1 on a given date.
3. Determining consistent Tim 2 roster (1 KAUR on top + 2 PNC below) per date.
4. Clean PDF redaction and insertion of replacement personnel on Page 1.
"""

import re
import json
import random
from pathlib import Path
import fitz

# Default fallback config path
CONFIG_PATH = Path("config/daftar_pegawai.json")


def load_pegawai_config(config_path: Path | str = None) -> dict:
    """Loads KAUR and PNC master data from config/daftar_pegawai.json."""
    p = Path(config_path) if config_path else CONFIG_PATH
    if not p.exists():
        # Fallback search
        alt_p = Path(__file__).parent.parent / "config" / "daftar_pegawai.json"
        if alt_p.exists():
            p = alt_p

    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    "resor": data.get("resor", {
                        "nama": "FURQON SUSILO WARDOYO",
                        "nipp": "64465",
                        "jabatan": "KUPT RESOR STL 1.21 BOGOR"
                    }),
                    "kaur": data.get("kaur", []),
                    "pnc": data.get("pnc", [])
                }
        except Exception as e:
            print(f"[WARN] Failed to read {p}: {e}")

    # Default fallback personnel if file is missing
    return {
        "resor": {
            "nama": "FURQON SUSILO WARDOYO",
            "nipp": "64465",
            "jabatan": "KUPT RESOR STL 1.21 BOGOR"
        },
        "kaur": [
            {"nama": "SUTISNA", "nipp": "45677", "no_sc": "PRP.080175.126093"},
            {"nama": "YATIYO", "nipp": "49957", "no_sc": "PRP.260287.39992"}
        ],
        "pnc": [
            {"nama": "RAIHAN HERPIAN", "nipp": "75276", "no_sc": "PRP.170204.72256"},
            {"nama": "IWAN SETIAWAN", "nipp": "69810", "no_sc": "PRP.03071990.36476"},
            {"nama": "JUJUN JUNAEDI", "nipp": "69699", "no_sc": "PRP.02021990.36540"},
            {"nama": "DIKA ARMANSYAH", "nipp": "72347", "no_sc": "PRP.020899.122293"}
        ]
    }


def extract_page1_tim1_personnel(doc: fitz.Document) -> set[str]:
    """Extracts personnel names and SC numbers from Page 1 of a Tim 1 PDF."""
    if len(doc) == 0:
        return set()

    page = doc[0]
    blocks = page.get_text("dict")["blocks"]

    dila_span = None
    sc_span = None

    for b in blocks:
        if "lines" not in b:
            continue
        for l in b["lines"]:
            for s in l["spans"]:
                txt = s["text"].strip().upper()
                if "DILAKSANAKAN" in txt:
                    dila_span = s
                elif "NO. SC." in txt and dila_span and abs(s["bbox"][1] - dila_span["bbox"][1]) < 30:
                    sc_span = s

    if not dila_span:
        return set()

    y_mid = (dila_span["bbox"][1] + dila_span["bbox"][3]) / 2

    # Extract all text in the horizontal band of "Dilaksanakan oleh:" row
    found_tokens = set()
    for b in blocks:
        if "lines" not in b:
            continue
        for l in b["lines"]:
            for s in l["spans"]:
                txt = s["text"].strip().upper()
                # If within vertical band of the personnel row
                if abs(s["bbox"][1] - y_mid) < 35 and s["bbox"][0] > dila_span["bbox"][2]:
                    if txt and txt not in (":", "NO. SC.", "-", "PRP.", "NO.", "SC."):
                        found_tokens.add(txt)
                        # Also add individual words / SC numbers
                        for w in txt.split():
                            if len(w) > 2:
                                found_tokens.add(w)

    return found_tokens


def get_tim2_roster_for_date(
    date_str: str,
    tim1_personnel_tokens: set[str] = None,
    pegawai_config: dict = None
) -> list[dict]:
    """
    Determines 1 KAUR (top row) and 2 PNC (middle & bottom rows) for Tim 2 on date_str.
    Prioritizes personnel not present in Tim 1 on that date.
    Deterministic PRNG seeded by date_str guarantees identical team on that date.
    """
    if pegawai_config is None:
        pegawai_config = load_pegawai_config()
    if tim1_personnel_tokens is None:
        tim1_personnel_tokens = set()

    all_kaur = list(pegawai_config.get("kaur", []))
    all_pnc = list(pegawai_config.get("pnc", []))

    if not all_kaur:
        all_kaur = [{"nama": "S. SLAMET RIYADI", "no_sc": "PRP.070474.126088"}]
    if len(all_pnc) < 2:
        all_pnc = [
            {"nama": "AGUS PRIYONO", "no_sc": "PRP.030886.126116"},
            {"nama": "IWAN SETIAWAN", "no_sc": "PRP.03071990.36476"}
        ]

    # Normalize date string for stable seeding
    norm_date = re.sub(r'[^0-9]', '', str(date_str))
    seed_str = f"tim2_roster_seed_{norm_date}"
    rng = random.Random(seed_str)

    # Helper to check if person is present in Tim 1 tokens
    def is_in_tim1(person: dict) -> bool:
        nama = person.get("nama", "").strip().upper()
        no_sc = person.get("no_sc", "").strip().upper()
        if nama in tim1_personnel_tokens or no_sc in tim1_personnel_tokens:
            return True
        # Check if full name or substantial part matches
        for tok in tim1_personnel_tokens:
            if tok and (tok in nama or (len(tok) > 5 and tok in no_sc)):
                return True
        return False

    # 1. Select 1 KAUR
    avail_kaur = [k for k in all_kaur if not is_in_tim1(k)]
    if avail_kaur:
        chosen_kaur = rng.choice(avail_kaur)
    else:
        chosen_kaur = rng.choice(all_kaur)

    # 2. Select 2 PNCs
    avail_pnc = [p for p in all_pnc if not is_in_tim1(p)]
    if len(avail_pnc) >= 2:
        chosen_pncs = rng.sample(avail_pnc, 2)
    elif len(avail_pnc) == 1:
        pool = [p for p in all_pnc if p != avail_pnc[0]]
        chosen_pncs = [avail_pnc[0], rng.choice(pool) if pool else avail_pnc[0]]
    else:
        chosen_pncs = rng.sample(all_pnc, min(2, len(all_pnc)))

    return [
        {"role": "KAUR", **chosen_kaur},
        {"role": "PNC", **chosen_pncs[0]},
        {"role": "PNC", **chosen_pncs[1]}
    ]


def replace_page1_employee_names(
    doc: fitz.Document,
    new_employees: list[dict]
) -> bool:
    """
    Redacts old personnel names & SC numbers on Page 1 and inserts new_employees.
    Row 1: KAUR (top)
    Row 2: PNC 1 (middle)
    Row 3: PNC 2 (bottom)
    Preserves all table borders intact and centers text within cells.
    """
    if len(doc) == 0:
        return False

    page = doc[0]

    # 1. Search for anchor spans
    blocks = page.get_text("dict")["blocks"]
    dila_span = None
    sc_span = None

    for b in blocks:
        if "lines" not in b:
            continue
        for l in b["lines"]:
            for s in l["spans"]:
                txt = s["text"].strip().upper()
                if "DILAKSANAKAN" in txt:
                    dila_span = s
                elif "NO. SC." in txt and dila_span and abs(s["bbox"][1] - dila_span["bbox"][1]) < 30:
                    sc_span = s

    if not dila_span or not sc_span:
        # Fallback: search anywhere on page for "Dilaksanakan"
        for b in blocks:
            if "lines" not in b:
                continue
            for l in b["lines"]:
                for s in l["spans"]:
                    txt = s["text"].strip().upper()
                    if "DILAKSANAKAN" in txt:
                        dila_span = s
                    elif "NO. SC." in txt:
                        sc_span = s
        if not dila_span or not sc_span:
            print("[WARN] Could not find 'Dilaksanakan' or 'NO. SC.' on Page 1; skipping employee replacement.")
            return False

    y_mid = (dila_span["bbox"][1] + dila_span["bbox"][3]) / 2

    # 2. Extract table lines from vector drawings
    drawings = page.get_drawings()
    h_lines = set()
    v_lines = set()

    for d in drawings:
        r = d["rect"]
        if r.width > 20 and r.height < 2 and (y_mid - 60 <= r.y0 <= y_mid + 60):
            h_lines.add(round(r.y0, 2))
        elif r.height > 20 and r.width < 2 and (y_mid - 60 <= (r.y0 + r.y1)/2 <= y_mid + 60):
            v_lines.add(round(r.x0, 2))

    sorted_h = sorted(h_lines)
    sorted_v = sorted(v_lines)

    top_lines = [y for y in sorted_h if y <= y_mid]
    bottom_lines = [y for y in sorted_h if y >= y_mid]

    y_top = max(top_lines) if top_lines else y_mid - 25.0
    y_bottom = min(bottom_lines) if bottom_lines else y_mid + 35.0

    # Vertical boundaries:
    # Names cell: lines between dila_span and sc_span
    v_between = [x for x in sorted_v if dila_span["bbox"][0] <= x <= sc_span["bbox"][2]]
    if len(v_between) >= 4:
        x_name_left = v_between[2]
        x_name_right = v_between[3]
    elif len(v_between) >= 2:
        x_name_left = v_between[-2]
        x_name_right = v_between[-1]
    else:
        x_name_left = dila_span["bbox"][2] + 15.0
        x_name_right = sc_span["bbox"][0] - 15.0

    # SC numbers cell: lines to the right of sc_span
    v_right = [x for x in sorted_v if x >= sc_span["bbox"][0]]
    if len(v_right) >= 4:
        x_sc_left = v_right[2]
        x_sc_right = v_right[3]
    elif len(v_right) >= 2:
        x_sc_left = v_right[-2]
        x_sc_right = v_right[-1]
    else:
        x_sc_left = sc_span["bbox"][2] + 25.0
        x_sc_right = page.rect.width - 29.0

    # 3. Clean redaction strictly inside cell borders
    rect_names = fitz.Rect(x_name_left + 1.0, y_top + 1.0, x_name_right - 1.0, y_bottom - 1.0)
    rect_sc = fitz.Rect(x_sc_left + 1.0, y_top + 1.0, x_sc_right - 1.0, y_bottom - 1.0)

    page.add_redact_annot(rect_names, fill=(1, 1, 1))
    page.add_redact_annot(rect_sc, fill=(1, 1, 1))
    page.apply_redactions()

    # 4. Insert new text vertically and horizontally centered using authentic DejaVuSans-Bold
    num_rows = len(new_employees)
    font_size_name = 7.8
    font_size_sc = 7.0

    # Locate DejaVuSans-Bold.ttf
    ttf_candidates = [
        Path("config/DejaVuSans-Bold.ttf"),
        Path(__file__).parent.parent / "config" / "DejaVuSans-Bold.ttf"
    ]
    font_file = None
    for cand in ttf_candidates:
        if cand.exists():
            font_file = str(cand.resolve())
            break

    custom_font = None
    if font_file:
        try:
            custom_font = fitz.Font(fontfile=font_file)
        except Exception:
            custom_font = None

    font_name = "DejaVuSans-Bold" if custom_font else "hebo"

    avail_h = (y_bottom - 1.0) - (y_top + 1.0)
    row_h = avail_h / (num_rows + 1)

    for idx, emp in enumerate(new_employees):
        nama = emp.get("nama", "").strip().upper()
        no_sc = emp.get("no_sc", "").strip().upper()

        y_row_center = (y_top + 1.0) + (idx + 1) * row_h
        y_base_name = y_row_center + (font_size_name * 0.36)
        y_base_sc = y_row_center + (font_size_sc * 0.36)

        # Name: centered in names cell (7.8pt)
        if custom_font:
            w_name = custom_font.text_length(nama, fontsize=font_size_name)
            x_name_center = (x_name_left + x_name_right) / 2
            x_name_pos = max(x_name_left + 2.0, x_name_center - (w_name / 2))
            page.insert_text((x_name_pos, y_base_name), nama, fontname=font_name, fontfile=font_file, fontsize=font_size_name, color=(0, 0, 0))
        else:
            w_name = fitz.get_text_length(nama, fontname=font_name, fontsize=font_size_name)
            x_name_center = (x_name_left + x_name_right) / 2
            x_name_pos = max(x_name_left + 2.0, x_name_center - (w_name / 2))
            page.insert_text((x_name_pos, y_base_name), nama, fontname=font_name, fontsize=font_size_name, color=(0, 0, 0))

        # No. SC: centered in SC cell (7.0pt)
        if custom_font:
            w_sc = custom_font.text_length(no_sc, fontsize=font_size_sc)
            x_sc_center = (x_sc_left + x_sc_right) / 2
            x_sc_pos = max(x_sc_left + 2.0, x_sc_center - (w_sc / 2))
            page.insert_text((x_sc_pos, y_base_sc), no_sc, fontname=font_name, fontfile=font_file, fontsize=font_size_sc, color=(0, 0, 0))
        else:
            w_sc = fitz.get_text_length(no_sc, fontname=font_name, fontsize=font_size_sc)
            x_sc_center = (x_sc_left + x_sc_right) / 2
            x_sc_pos = max(x_sc_left + 2.0, x_sc_center - (w_sc / 2))
            page.insert_text((x_sc_pos, y_base_sc), no_sc, fontname=font_name, fontsize=font_size_sc, color=(0, 0, 0))

    return True
