import os
import sys
import time
import json
import base64
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import urllib.request
import urllib.error

# 5 Sampel foto sesuai pengujian sebelumnya
SAMPLE_PHOTOS = [
    {
        "category": "WESEL",
        "detail": "W81 BOO_02-02 (100.jpg)",
        "path": Path("03_photos_export/BTP JAK/WESEL/W81 BOO_02-02/100.jpg")
    },
    {
        "category": "SINYAL",
        "detail": "J10 BTT (0.jpg)",
        "path": Path("03_photos_export/BTP BD/SINYAL/J10 BTT/0.jpg")
    },
    {
        "category": "PTLS",
        "detail": "BTT (0.jpg)",
        "path": Path("03_photos_export/BTP BD/PTLS/BTT/0.jpg")
    },
    {
        "category": "SINYAL",
        "detail": "B101 BJD-CLT (50.jpg)",
        "path": Path("03_photos_export/BTP JAK/SINYAL/B101 BJD-CLT/50.jpg")
    },
    {
        "category": "AXC",
        "detail": "ZP 101A BTT-MSG (0.jpg)",
        "path": Path("03_photos_export/BTP BD/AXC/ZP 101A BTT-MSG/0.jpg")
    }
]

OUTPUT_DIR = Path("experiments_google_vision/output")
LOGS_DIR = Path("logs/google_vision_experiment")

def get_api_key():
    key_file = Path("experiments_google_vision/api_key.txt")
    if key_file.exists():
        key = key_file.read_text(encoding="utf-8").strip()
        if key:
            return key
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

def call_gemini_vision(image_path, api_key):
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")

    prompt = (
        "You are an expert OCR and document analysis AI. "
        "Analyze this maintenance photo and locate the date/timestamp watermark text (timemark), "
        "which typically contains date and time (e.g., 'Senin, Jan 06 2025', 'DD/MM/YYYY HH:MM', etc.) "
        "usually located at the lower area of the photo, sometimes accompanied by a small red vertical guide bar.\n"
        "Return ONLY a JSON object with this exact structure:\n"
        "{\n"
        '  "timemark_found": true/false,\n'
        '  "detected_text": "the exact string of the timemark",\n'
        '  "box_2d": [ymin, xmin, ymax, xmax],\n'
        '  "notes": "brief observation"\n'
        "}\n"
        "Note: box_2d coordinates must be normalized integers from 0 to 1000 (0=top/left, 1000=bottom/right)."
    )

    models_to_try = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.5-flash-lite", "gemini-3.1-flash-lite"]
    last_err = None

    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
                ]
            }],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1
            }
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text_out = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text_out)
                parsed["model_used"] = model
                return parsed
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            last_err = f"{model} -> HTTP {e.code}: {err_body}"
            # if 404, try next model; if 429/403, raise to let user know
            if e.code in [401, 403, 429]:
                raise RuntimeError(last_err)
        except Exception as e:
            last_err = str(e)

    raise RuntimeError(f"Semua model gagal: {last_err}")

def draw_annotations(image_path, result_data, out_path):
    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    w, h = img.size

    box_2d = result_data.get("box_2d")
    text = result_data.get("detected_text", "")

    if box_2d and len(box_2d) == 4:
        ymin, xmin, ymax, xmax = box_2d
        # Denormalize 0..1000 to pixels
        px_ymin = int((ymin / 1000.0) * h)
        px_xmin = int((xmin / 1000.0) * w)
        px_ymax = int((ymax / 1000.0) * h)
        px_xmax = int((xmax / 1000.0) * w)

        # Draw green bounding box for timemark
        for i in range(2):
            draw.rectangle([px_xmin - i, px_ymin - i, px_xmax + i, px_ymax + i], outline=(0, 255, 0))

        # Draw label banner
        label = f"Timemark: {text[:25]}"
        draw.rectangle([px_xmin, max(0, px_ymin - 16), px_xmin + 180, px_ymin], fill=(0, 180, 0))
        draw.text((px_xmin + 2, max(0, px_ymin - 15)), label, fill=(255, 255, 255))

    img.save(out_path, quality=95)

def main():
    print("=" * 65)
    print("EKSPERIMEN: Google Gemini Vision pada 5 Sampel Foto")
    print("=" * 65)

    api_key = get_api_key()
    if not api_key:
        print("[GAGAL] API Key tidak ditemukan! Silakan simpan key di experiments_google_vision/api_key.txt")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    results = []

    for idx, sample in enumerate(SAMPLE_PHOTOS, start=1):
        cat = sample["category"]
        detail = sample["detail"]
        img_p = sample["path"]

        print(f"\n[{cat}] ({idx}/{len(SAMPLE_PHOTOS)}) Memproses: {img_p} ...")
        if not img_p.exists():
            print(f"  [PERINGATAN] File tidak ditemukan: {img_p}")
            continue

        t_start = time.time()
        try:
            gemini_res = call_gemini_vision(img_p, api_key)
            dur = time.time() - t_start

            found = gemini_res.get("timemark_found", False)
            text = gemini_res.get("detected_text", "")
            box = gemini_res.get("box_2d", [])
            model = gemini_res.get("model_used", "")

            print(f"  [SUKSES] Durasi: {dur:.2f}s | Model: {model}")
            print(f"  - Ditemukan: {found}")
            print(f"  - Teks Timemark: '{text}'")
            print(f"  - Bounding Box (0-1000): {box}")

            # Simpan visualisasi
            out_name = f"sample_{idx}_{cat}_{img_p.stem}_gemini.jpg"
            out_file = OUTPUT_DIR / out_name
            draw_annotations(img_p, gemini_res, out_file)

            # Copy ke logs sesuai aturan project safety
            log_copy = LOGS_DIR / out_name
            shutil.copy2(out_file, log_copy)

            results.append({
                "sample_index": idx,
                "category": cat,
                "detail": detail,
                "image_path": str(img_p),
                "duration_seconds": round(dur, 2),
                "model": model,
                "success": True,
                "data": gemini_res,
                "annotated_output": str(out_file),
                "log_output": str(log_copy)
            })

        except Exception as e:
            dur = time.time() - t_start
            print(f"  [GAGAL] Error Gemini: {e}")
            results.append({
                "sample_index": idx,
                "category": cat,
                "detail": detail,
                "image_path": str(img_p),
                "duration_seconds": round(dur, 2),
                "success": False,
                "error": str(e)
            })

    # Simpan hasil JSON
    json_out = OUTPUT_DIR / "gemini_vision_results.json"
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 65)
    print(f"Hasil lengkap tersimpan di: {json_out}")
    print(f"Foto hasil anotasi tersimpan di: {OUTPUT_DIR}")
    print(f"Salinan log tersimpan di: {LOGS_DIR}")
    print("=" * 65)

if __name__ == "__main__":
    main()
