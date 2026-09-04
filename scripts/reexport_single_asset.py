"""
reexport_single_asset.py — Helper to re-export original photos for a specific asset from source PDF.
Usage:
    python scripts/reexport_single_asset.py --rel "BTP BD/PDSE/MSG/0.jpg"
"""
import os
import sys
import re
import json
import shutil
import argparse
from pathlib import Path

import pypdf
import pdfplumber

# Ensure project root is in path
APP_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(APP_DIR / 'scripts'))

from export_pdf_foto import original_images_by_name


CATEGORY_ALIASES = {
    'AXC': ['AXC', 'AXLE COUNTER', 'AXLE'],
    'WESEL': ['WESEL'],
    'SINYAL': ['SINYAL', 'PERSINYALAN'],
    'PDSE': ['PDSE', 'PTDS', 'PERSINYALAN ELEKTRIK'],
    'PTDS': ['PTDS', 'PDSE'],
    'CATUDAYA': ['CATU DAYA', 'CATUDAYA', 'CDA'],
    'CATU_DAYA': ['CATU DAYA', 'CATUDAYA', 'CDA'],
    'TELEKOMUNIKASI': ['TELEKOMUNIKASI', 'TELEKOM', 'RADIO'],
    'SERAT OPTIK': ['SERAT OPTIK', 'OPTIC'],
    'JPL': ['JPL', 'PINTU PERLINTASAN', 'PTPP'],
    'PTPP': ['PTPP', 'PINTU PERLINTASAN', 'JPL'],
    'PTLS': ['PTLS', 'WAYSTATION', 'BASESTATION']
}


STATION_ALIASES = {
    'BTT': ['BATU TULIS', 'BATUTULIS'],
    'BOO': ['BOGOR'],
    'BOP': ['BOGOR PALEDANG'],
    'CLT': ['CILEBUT'],
    'MSG': ['MASENG'],
    'CGB': ['CIGOMBONG'],
    'COS': ['CIOMAS'],
    'BNR': ['BOGOR NIAGA RAYA'],
}


def _expand_station_tokens(tokens: list[str]) -> list[str]:
    """Return all tokens with station codes expanded to full names."""
    result = []
    for tok in tokens:
        aliases = STATION_ALIASES.get(tok, [])
        if aliases:
            result.extend(aliases)
        result.append(tok)
    return result


def find_matching_source_pdfs(rel: str, source_dir: str = "01_pdf_source") -> list[Path]:
    """Find source PDFs in 01_pdf_source that contain photos for the specified rel path."""
    rel_path = Path(rel)
    parts = rel_path.parts
    if len(parts) < 3:
        return []

    category = parts[1].upper()    # e.g. PDSE, WESEL, AXC
    identifier = parts[2].upper()  # e.g. MSG, ZP 72 BOO, W13 BOO_03-08

    clean_id = re.sub(r'_\d{2}-\d{2}$', '', identifier)
    id_tokens = [tok for tok in clean_id.split() if tok not in ['BTP', 'JAK', 'BD']]

    source_root = Path(source_dir)
    pdf_files = sorted(source_root.glob("*.pdf"))
    aliases = CATEGORY_ALIASES.get(category, [category])

    matches = []
    # Pass 0: Exact phrase match, trying both original and with stations expanded
    if len(clean_id) >= 3:
        candidate_phrases = [clean_id]
        # If last token is a station code, also try without it
        station_aliases_for_filter = []
        if len(id_tokens) >= 2 and id_tokens[-1] in STATION_ALIASES:
            base_without_station = ' '.join(id_tokens[:-1])
            if len(base_without_station) >= 3:
                candidate_phrases.append(base_without_station)
            station_aliases_for_filter = STATION_ALIASES[id_tokens[-1]]

        for phrase in candidate_phrases:
            for pdf_file in pdf_files:
                name_upper = pdf_file.name.upper()
                if phrase in name_upper:
                    # If we're using the fallback (without station), require station alias too
                    if phrase != clean_id and station_aliases_for_filter:
                        if not any(sa in name_upper for sa in station_aliases_for_filter):
                            continue
                    matches.append(pdf_file)
            if matches:
                break

    if matches:
        # Filter: keep only matches where category alias is present
        filtered = [m for m in matches if any(alias in m.name.upper() for alias in aliases)]
        if filtered:
            return filtered
        matches = []

    # Pass 1: Category alias + station token match
    # The station code (last ID token) is the most distinguishing element
    station_key = id_tokens[-1] if id_tokens else ''
    station_candidates = _expand_station_tokens([station_key]) if station_key else []
    for pdf_file in pdf_files:
        name_upper = pdf_file.name.upper()
        if not any(alias in name_upper for alias in aliases):
            continue
        # Must match station (code or expanded name) in filename
        if station_candidates and not any(sc in name_upper for sc in station_candidates):
            continue
        matches.append(pdf_file)

    if matches:
        return matches

    # Pass 2: ID token match fallback (in case category is slightly different in filename)
    if id_tokens:
        for pdf_file in pdf_files:
            name_upper = pdf_file.name.upper()
            if all(tok in name_upper for tok in id_tokens):
                matches.append(pdf_file)

    if matches:
        return matches

    # Pass 3: Content check fallback (slow)
    for pdf_file in pdf_files:
        try:
            reader = pypdf.PdfReader(pdf_file)
            full_text = " ".join([pg.extract_text() or "" for pg in reader.pages]).upper()
            if any(alias in full_text for alias in aliases) and all(tok in full_text for tok in id_tokens if len(tok) >= 2):
                matches.append(pdf_file)
        except Exception:
            pass

    return matches


def _select_source_pdf(rel: str, source_dir: str) -> Path | None:
    """Choose a unique source PDF using the full asset identity and station aliases."""
    parts = Path(rel).parts
    if len(parts) < 3:
        return None

    category = parts[1].upper()
    identifier = parts[2].upper().replace('_', ' ').strip()
    tokens = identifier.split()
    if not tokens:
        return None

    station = tokens[-1]
    station_terms = [station, *STATION_ALIASES.get(station, [])]
    specific_code = None
    if len(tokens) >= 2 and tokens[0] == 'ZP':
        specific_code = f'ZP {tokens[1]}'
    elif re.match(r'^[A-Z]+\d', tokens[0]):
        specific_code = tokens[0]

    def has_term(name: str, term: str) -> bool:
        return bool(re.search(rf'(?<![A-Z0-9]){re.escape(term)}(?![A-Z0-9])', name))

    candidates = []
    for pdf in sorted(Path(source_dir).glob('*.pdf')):
        name = pdf.stem.upper().replace('_', ' ')
        if category == 'PTLS':
            if not has_term(name, 'PTLS'):
                continue
        elif category == 'PTDS':
            if not any(has_term(name, token) for token in ('PTDS', 'PDSE')):
                continue
        elif category == 'PDSE':
            if not any(has_term(name, token) for token in ('PDSE', 'PTDS')):
                continue
        elif category == 'CATUDAYA':
            if not any(term in name for term in ('CATU DAYA', 'CATUDAYA')):
                continue
        elif category in ('TELEKOMUNIKASI', 'RADIO'):
            if not any(term in name for term in ('RADIO', 'TELEKOMUNIKASI')):
                continue
        elif category == 'AXC' and not any(term in name for term in ('AXLE COUNTER', 'AXC')):
            continue

        if specific_code and not has_term(name, specific_code):
            continue
        if not any(has_term(name, term) for term in station_terms):
            continue
        candidates.append(pdf)

    # Never silently choose an unrelated PDF when the identity is ambiguous.
    return candidates[0] if len(candidates) == 1 else None


def _extract_one_frame(pdf_path: Path, frame: str) -> bytes | None:
    """Extract one standard frame using the PDF layout's left-to-right order."""
    index = {'0': 0, '50': 1, '100': 2}.get(Path(frame).stem)
    if index is None:
        return None
    reader = pypdf.PdfReader(str(pdf_path))
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_index in range(1, len(pdf.pages)):
            page = pdf.pages[page_index]
            placements = sorted(page.images, key=lambda image: float(image['x0']))
            if len(placements) < 3:
                continue
            placement = placements[index]
            wanted = Path(str(placement.get('name', ''))).stem
            raw = original_images_by_name(reader, page_index)
            match = raw.get(wanted)
            return match[1] if match else None
    return None


def reexport_asset(rel: str, source_dir: str = "01_pdf_source", photos_dir: str = "03_photos_export", logs_dir: str = "logs"):
    """Re-export only the requested original frame; never run the full PDF exporter."""
    rel_path = Path(rel)
    if len(rel_path.parts) < 3 or rel_path.suffix.lower() not in ('.jpg', '.jpeg', '.png'):
        print(f"[ERROR] Invalid photo rel path: {rel}", file=sys.stderr)
        return False
    pdf_path = _select_source_pdf(rel, source_dir)
    if not pdf_path:
        print(f"[ERROR] No unique source PDF found for {rel}", file=sys.stderr)
        return False
    print(f"[INFO] Targeted source: {pdf_path.name}")
    data = _extract_one_frame(pdf_path, rel_path.name)
    if not data:
        print(f"[ERROR] Photo frame {rel_path.name} not found in {pdf_path.name}", file=sys.stderr)
        return False
    target = Path(photos_dir) / rel_path
    backup = Path(logs_dir) / 'reexport_originals' / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    backup.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not backup.exists():
        shutil.copy2(target, backup)
    target.write_bytes(data)

    rel_folder = str(rel_path.parent).replace('\\', '/')
    edited_root = APP_DIR / '04_photos_edited'
    if edited_root.exists():
        for tim_dir in edited_root.iterdir():
            edited = tim_dir / rel_folder / rel_path.name
            if edited.exists():
                edited.unlink()
    manifest_path = Path(logs_dir) / 'cropped_collages.json'
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            manifest = [item for item in manifest if item != str(rel_path).replace('\\', '/')]
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        except (OSError, json.JSONDecodeError):
            pass
    print(f"[OK] Targeted re-export complete for {rel}; bytes={len(data)}")
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Re-export original asset photos from source PDF")
    parser.add_argument("--rel", required=True, help="Relative photo or folder path (e.g. BTP BD/PDSE/MSG/0.jpg)")
    parser.add_argument("--source-dir", default="01_pdf_source", help="Path to 01_pdf_source")
    parser.add_argument("--photos-dir", default="03_photos_export", help="Path to 03_photos_export")
    parser.add_argument("--logs-dir", default="logs", help="Path to logs")
    args = parser.parse_args()

    ok = reexport_asset(args.rel, args.source_dir, args.photos_dir, args.logs_dir)
    sys.exit(0 if ok else 1)
