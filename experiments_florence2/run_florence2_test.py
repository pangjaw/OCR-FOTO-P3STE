import os
import sys
import time
import json
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import torch
from transformers import AutoProcessor, AutoModelForCausalLM

def main():
    print("=" * 60)
    print("EXPERIMENT: Microsoft Florence-2 OCR & Region Detection")
    print("=" * 60)

    # Folders
    exp_dir = Path("experiments_florence2")
    out_dir = exp_dir / "output"
    logs_dir = Path("logs/florence2_experiment")
    out_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    # 5 Test Photos across categories
    sample_photos = [
        {"category": "AXC", "path": Path("03_photos_export/BTP BD/AXC/ZP 101A BTT-MSG/0.jpg"), "name": "01_axc_zp101a"},
        {"category": "SINYAL", "path": Path("03_photos_export/BTP BD/SINYAL/J10 BTT/0.jpg"), "name": "02_sinyal_j10"},
        {"category": "WESEL", "path": Path("03_photos_export/BTP JAK/WESEL/W81 BOO_02-02/100.jpg"), "name": "03_wesel_w81"},
        {"category": "PTLS", "path": Path("03_photos_export/BTP BD/PTLS/BTT/0.jpg"), "name": "04_ptls_btt"},
        {"category": "SERAT OPTIK", "path": Path("03_photos_export/BTP BD/SERAT OPTIK/ER SINYAL BTT/0.jpg"), "name": "05_serat_optik_er_sinyal"}
    ]

    print("Loading Florence-2 model (microsoft/Florence-2-base)...")
    t0_load = time.time()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    model_id = "microsoft/Florence-2-base"
    processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
    torch_dtype = torch.float32
    model = AutoModelForCausalLM.from_pretrained(model_id, trust_remote_code=True, torch_dtype=torch_dtype).to(device)
    model.eval()
    print(f"Model loaded in {time.time() - t0_load:.2f}s\n")

    results_summary = []

    # Date keywords for detection
    date_keywords = [
        "2024", "2025", "2026", "jan", "feb", "mar", "apr", "mei", "jun",
        "jul", "agt", "agu", "sep", "okt", "nov", "des", "sen", "sel",
        "rab", "kam", "jum", "sab", "min", "wib", "gmt", "utc"
    ]

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

        # Task: OCR_WITH_REGION
        t0_inf = time.time()
        task_prompt = "<OCR_WITH_REGION>"
        inputs = processor(text=task_prompt, images=img, return_tensors="pt")
        inputs = {k: v.to(device, dtype=torch_dtype) if isinstance(v, torch.Tensor) and v.dtype.is_floating_point else v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            generated_ids = model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=1024,
                num_beams=3,
                do_sample=False,
                use_cache=False
            )

        generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
        parsed_answer = processor.post_process_generation(
            generated_text,
            task=task_prompt,
            image_size=(w, h)
        )
        elapsed = time.time() - t0_inf

        ocr_data = parsed_answer.get("<OCR_WITH_REGION>", {})
        quad_boxes = ocr_data.get("quad_boxes", [])
        labels = ocr_data.get("labels", [])

        # Create Annotated Image
        annotated_img = img.copy()
        draw = ImageDraw.Draw(annotated_img)

        try:
            font = ImageFont.truetype("arial.ttf", 14)
            font_small = ImageFont.truetype("arial.ttf", 11)
        except Exception:
            font = ImageFont.load_default()
            font_small = font

        detected_boxes_info = []
        date_candidates = []

        for qb, label in zip(quad_boxes, labels):
            if len(qb) == 8:
                xs = qb[0::2]
                ys = qb[1::2]
                box = [min(xs), min(ys), max(xs), max(ys)]
            elif len(qb) == 4:
                box = qb
            else:
                continue

            x1, y1, x2, y2 = [int(v) for v in box]
            is_date_related = any(k in label.lower() for k in date_keywords) or (any(c.isdigit() for c in label) and (":" in label or "-" in label or "/" in label))

            box_info = {
                "text": label,
                "bbox": [x1, y1, x2, y2],
                "is_date": is_date_related
            }
            detected_boxes_info.append(box_info)

            if is_date_related:
                date_candidates.append(box_info)
                # Draw thick RED box for date candidate
                draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
                draw.rectangle([x1, max(0, y1 - 16), x1 + len(label) * 8 + 6, y1], fill="red")
                draw.text((x1 + 3, max(0, y1 - 15)), label, fill="white", font=font_small)
            else:
                # Draw CYAN box for other text
                draw.rectangle([x1, y1, x2, y2], outline="cyan", width=1)
                draw.text((x1 + 2, max(0, y1 - 13)), label, fill="cyan", font=font_small)

        # Save output images
        out_img_path = out_dir / f"{base_name}_annotated.jpg"
        annotated_img.save(out_img_path, quality=95)
        # Also copy to logs for display compliance
        log_img_path = logs_dir / f"{base_name}_annotated.jpg"
        shutil.copy(out_img_path, log_img_path)

        result_entry = {
            "name": base_name,
            "category": cat,
            "path": str(photo_path),
            "image_size": [w, h],
            "inference_time_sec": round(elapsed, 3),
            "raw_generated_text": generated_text,
            "total_detected_text": len(labels),
            "date_candidates": date_candidates,
            "all_detections": detected_boxes_info,
            "output_image": str(out_img_path),
            "log_image": str(log_img_path)
        }
        results_summary.append(result_entry)

        print(f"  -> Selesai dalam {elapsed:.2f} detik. Total teks terdeteksi: {len(labels)}")
        print(f"     Raw text: {repr(generated_text[:120])}")
        for dc in date_candidates:
            print(f"     [TANGGAL TERDETEKSI] '{dc['text']}' pada koordinat {dc['bbox']}")
        print()

    # Save JSON report
    report_json_path = out_dir / "florence2_test_results.json"
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(results_summary, f, indent=2, ensure_ascii=False)

    print("=" * 60)
    print("HASIL LENGKAP PENGUJIAN")
    print("=" * 60)
    print(f"Hasil JSON tersimpan di: {report_json_path}")
    print(f"Foto hasil anotasi tersimpan di: {out_dir}")
    print(f"Salinan foto untuk log tersimpan di: {logs_dir}")

if __name__ == "__main__":
    main()
