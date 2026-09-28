import os
import sys
import time
import json
import base64
import shutil
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import requests

def parse_args():
    parser = argparse.ArgumentParser(description="Google Cloud Vision OCR Experiment")
    parser.add_argument("--api-key", type=str, default="", help="Google Cloud API Key")
    parser.add_argument("--credentials", type=str, default="", help="Path to Google Cloud service account JSON file")
    return parser.parse_args()

def get_api_key_or_creds(args):
    # 1. Check CLI args
    if args.api_key:
        return ("api_key", args.api_key)
    if args.credentials and Path(args.credentials).exists():
        return ("service_account", str(Path(args.credentials).resolve()))

    # 2. Check local files in experiments_google_vision
    local_key_file = Path("experiments_google_vision/api_key.txt")
    if local_key_file.exists():
        key = local_key_file.read_text(encoding="utf-8").strip()
        if key:
            return ("api_key", key)

    local_creds_json = Path("experiments_google_vision/credentials.json")
    if local_creds_json.exists():
        return ("service_account", str(local_creds_json.resolve()))

    # 3. Check environment variables
    env_key = os.environ.get("GOOGLE_VISION_API_KEY") or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if env_key:
        return ("api_key", env_key)

    env_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if env_creds and Path(env_creds).exists():
        return ("service_account", env_creds)

    return (None, None)

def detect_text_via_rest(image_path, api_key):
    url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "requests": [
            {
                "image": {"content": img_b64},
                "features": [{"type": "TEXT_DETECTION"}]
            }
        ]
    }

    resp = requests.post(url, json=payload, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")

    data = resp.json()
    responses = data.get("responses", [{}])[0]
    if "error" in responses:
        raise RuntimeError(f"Google Vision API Error: {responses['error']}")

    text_annotations = responses.get("textAnnotations", [])
    return text_annotations

def detect_text_via_sdk(image_path, creds_path):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
    from google.cloud import vision

    client = vision.ImageAnnotatorClient()
    with open(image_path, "rb") as f:
        content = f.read()

    image = vision.Image(content=content)
    response = client.text_detection(image=image)

    if response.error.message:
        raise RuntimeError(f"Google Vision SDK Error: {response.error.message}")

    # Convert SDK response to standard dict format
    annotations = []
    for annotation in response.text_annotations:
        vertices = [{"x": v.x, "y": v.y} for v in annotation.bounding_poly.vertices]
        annotations.append({
            "description": annotation.description,
            "boundingPoly": {"vertices": vertices}
        })

    return annotations

def main():
    args = parse_args()

    print("=" * 65)
    print("EXPERIMENT: Google Cloud Vision API on 5 Sample Photos")
    print("=" * 65)

    exp_dir = Path("experiments_google_vision")
    out_dir = exp_dir / "output"
    logs_dir = Path("logs/google_vision_experiment")
    out_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    auth_type, auth_val = get_api_key_or_creds(args)

    if not auth_type:
        print("\n[PERINGATAN] Kredensial Google Vision API belum ditemukan.")
        print("-" * 65)
        print("Silakan sediakan kunci dengan salah satu cara berikut:")
        print("1. Salin file Service Account JSON Anda ke:")
        print(f"   {exp_dir.resolve() / 'credentials.json'}")
        print("2. ATAU simpan API Key Anda di file teks:")
        print(f"   {exp_dir.resolve() / 'api_key.txt'}")
        print("3. ATAU jalankan perintah dengan argumen:")
        print("   python experiments_google_vision/run_google_vision_test.py --api-key AIzaSy...")
        print("-" * 65)
        sys.exit(2)

    print(f"Autentikasi terdeteksi: {auth_type.upper()}")

    # 5 Test Photos
    sample_photos = [
        {"category": "WESEL", "path": Path("03_photos_export/BTP JAK/WESEL/W81 BOO_02-02/100.jpg"), "name": "01_wesel_w81"},
        {"category": "SINYAL", "path": Path("03_photos_export/BTP BD/SINYAL/J10 BTT/0.jpg"), "name": "02_sinyal_j10"},
        {"category": "PTLS", "path": Path("03_photos_export/BTP BD/PTLS/BTT/0.jpg"), "name": "03_ptls_btt"},
        {"category": "SINYAL", "path": Path("03_photos_export/BTP JAK/SINYAL/B101 BJD-CLT/50.jpg"), "name": "04_sinyal_b101"},
        {"category": "AXC", "path": Path("03_photos_export/BTP BD/AXC/ZP 101A BTT-MSG/0.jpg"), "name": "05_axc_zp101a"}
    ]

    date_keywords = [
        "2024", "2025", "2026", "jan", "feb", "mar", "apr", "mei", "jun",
        "jul", "agt", "agu", "sep", "okt", "nov", "des", "sen", "sel",
        "rab", "kam", "jum", "sab", "min", "wib", "gmt", "utc"
    ]

    results_summary = []

    for item in sample_photos:
        photo_path = item["path"]
        cat = item["category"]
        base_name = item["name"]

        print(f"[{cat}] Processing: {photo_path} ...")
        if not photo_path.exists():
            print(f"  [ERROR] File not found: {photo_path}")
            continue

        img = Image.open(photo_path).convert("RGB")
        w, h = img.size

        t0 = time.time()
        try:
            if auth_type == "api_key":
                text_annotations = detect_text_via_rest(photo_path, auth_val)
            else:
                text_annotations = detect_text_via_sdk(photo_path, auth_val)
        except Exception as e:
            print(f"  [GAGAL] Error pemanggilan Google Vision: {e}")
            continue

        elapsed = time.time() - t0

        # First item in text_annotations is the entire concatenated text block
        full_text = text_annotations[0]["description"] if text_annotations else ""
        word_annotations = text_annotations[1:] if len(text_annotations) > 1 else []

        print(f"  -> Selesai dalam {elapsed:.2f} detik.")
        print(f"  -> Total kata terdeteksi: {len(word_annotations)}")
        print(f"  -> Teks penuh: {repr(full_text.strip()[:100])}...")

        # Find bounding boxes
        detected_words = []
        date_candidates = []

        annotated_img = img.copy()
        draw = ImageDraw.Draw(annotated_img)
        try:
            font = ImageFont.truetype("arial.ttf", 14)
            font_small = ImageFont.truetype("arial.ttf", 11)
        except Exception:
            font = ImageFont.load_default()
            font_small = font

        for ann in word_annotations:
            txt = ann.get("description", "")
            verts = ann.get("boundingPoly", {}).get("vertices", [])
            if not verts:
                continue

            xs = [v.get("x", 0) for v in verts]
            ys = [v.get("y", 0) for v in verts]
            x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)

            is_date = any(k in txt.lower() for k in date_keywords) or (any(c.isdigit() for c in txt) and (":" in txt or "-" in txt or "/" in txt))

            word_entry = {
                "text": txt,
                "bbox": [x1, y1, x2, y2],
                "is_date": is_date
            }
            detected_words.append(word_entry)

            if is_date:
                date_candidates.append(word_entry)
                # Draw thick RED box for date candidate
                draw.rectangle([x1, y1, x2, y2], outline="red", width=2)
                draw.rectangle([x1, max(0, y1 - 15), x1 + len(txt) * 8 + 4, y1], fill="red")
                draw.text((x1 + 2, max(0, y1 - 14)), txt, fill="white", font=font_small)
            else:
                # Draw CYAN box for normal text
                draw.rectangle([x1, y1, x2, y2], outline="cyan", width=1)

        # Save output images
        out_img_path = out_dir / f"{base_name}_gvision_annotated.jpg"
        annotated_img.save(out_img_path, quality=95)
        log_img_path = logs_dir / f"{base_name}_gvision_annotated.jpg"
        shutil.copy(out_img_path, log_img_path)

        entry_summary = {
            "name": base_name,
            "category": cat,
            "path": str(photo_path),
            "image_size": [w, h],
            "inference_time_sec": round(elapsed, 3),
            "full_text": full_text.strip(),
            "total_words": len(word_annotations),
            "date_candidates": date_candidates,
            "output_image": str(out_img_path),
            "log_image": str(log_img_path)
        }
        results_summary.append(entry_summary)

        for dc in date_candidates:
            print(f"     [TANGGAL TERDETEKSI] '{dc['text']}' @ bbox={dc['bbox']}")
        print()

    # Save summary JSON
    report_path = out_dir / "google_vision_results.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results_summary, f, indent=2, ensure_ascii=False)

    print("=" * 65)
    print(f"Hasil lengkap tersimpan di: {report_path}")
    print(f"Foto hasil anotasi tersimpan di: {out_dir}")
    print(f"Salinan log tersimpan di: {logs_dir}")
    print("=" * 65)

if __name__ == "__main__":
    main()
