import os
import sys
import time
import json
import re
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import torch
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info

def main():
    print("=" * 65)
    print("EXPERIMENT: Qwen2.5-VL-3B-Instruct for Date & Watermark Detection")
    print("Target PC Specs: Core i5-9300H (4C/8T), 16GB RAM, GTX 1050 3GB")
    print("Optimization: CPU execution, bfloat16, constrained vision patch tokens")
    print("=" * 65)

    # Directories
    exp_dir = Path("experiments_qwen25_vl")
    out_dir = exp_dir / "output"
    logs_dir = Path("logs/qwen25_vl_experiment")
    out_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    # 5 Sample photos
    sample_photos = [
        {"category": "WESEL", "path": Path("03_photos_export/BTP JAK/WESEL/W81 BOO_02-02/100.jpg"), "name": "01_wesel_w81"},
        {"category": "SINYAL", "path": Path("03_photos_export/BTP BD/SINYAL/J10 BTT/0.jpg"), "name": "02_sinyal_j10"},
        {"category": "PTLS", "path": Path("03_photos_export/BTP BD/PTLS/BTT/0.jpg"), "name": "03_ptls_btt"},
        {"category": "SINYAL", "path": Path("03_photos_export/BTP JAK/SINYAL/B101 BJD-CLT/50.jpg"), "name": "04_sinyal_b101"},
        {"category": "AXC", "path": Path("03_photos_export/BTP BD/AXC/ZP 101A BTT-MSG/0.jpg"), "name": "05_axc_zp101a"}
    ]

    model_id = "Qwen/Qwen2.5-VL-3B-Instruct"
    print(f"\nLoading {model_id}...")
    t0_load = time.time()

    # Hardware-adjusted parameters:
    # 3GB VRAM is too tight for 3B model, so CPU with 16GB RAM + bfloat16 is optimal & stable
    device = "cpu"
    dtype = torch.bfloat16

    # Constrain resolution tokens for 300x300 photos to maximize CPU speed
    min_pixels = 256 * 28 * 28
    max_pixels = 512 * 28 * 28

    print(f"Loading processor (min_pixels={min_pixels}, max_pixels={max_pixels})...")
    processor = AutoProcessor.from_pretrained(
        model_id,
        min_pixels=min_pixels,
        max_pixels=max_pixels
    )

    print(f"Loading model weights into CPU (dtype={dtype})...")
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        model_id,
        torch_dtype=dtype,
        device_map=device
    )
    model.eval()
    print(f"Model loaded successfully in {time.time() - t0_load:.2f}s\n")

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

        # Formulate instruction prompt requesting both text and bounding box
        prompt_text = (
            "Read the timestamp, date, time, and camera watermark text on this photo. "
            "Output each detected text and its bounding box in JSON format: "
            "[{\"text\": \"...\", \"bbox_2d\": [ymin, xmin, ymax, xmax]}]. "
            "Coordinates must be normalized from 0 to 1000. "
            "If no date/watermark is present, output []."
        )

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": img},
                    {"type": "text", "text": prompt_text}
                ]
            }
        ]

        t0_inf = time.time()
        text_input = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)

        inputs = processor(
            text=[text_input],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt"
        ).to(device)

        with torch.no_grad():
            generated_ids = model.generate(
                **inputs,
                max_new_tokens=256,
                do_sample=False
            )

        # Trim prompt tokens from generated output
        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        response_text = processor.batch_decode(
            generated_ids_trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False
        )[0]

        elapsed = time.time() - t0_inf
        print(f"  -> Generated in {elapsed:.2f}s")
        print(f"  -> Raw response: {response_text.strip()}")

        # Parse detected boxes from response
        detected_boxes = []
        try:
            # Try to extract JSON block if wrapped in markdown
            json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
            if json_match:
                parsed_json = json.loads(json_match.group(0))
                for entry in parsed_json:
                    txt = entry.get("text", "")
                    bbox_norm = entry.get("bbox_2d", [])
                    if len(bbox_norm) == 4:
                        ymin, xmin, ymax, xmax = bbox_norm
                        x1 = int(xmin / 1000.0 * w)
                        y1 = int(ymin / 1000.0 * h)
                        x2 = int(xmax / 1000.0 * w)
                        y2 = int(ymax / 1000.0 * h)
                        detected_boxes.append({
                            "text": txt,
                            "bbox_normalized": bbox_norm,
                            "bbox_pixels": [x1, y1, x2, y2]
                        })
        except Exception as e:
            print(f"  [WARN] JSON parse error: {e}")

        # Draw annotations on image copy
        annotated_img = img.copy()
        draw = ImageDraw.Draw(annotated_img)
        try:
            font = ImageFont.truetype("arial.ttf", 14)
            font_small = ImageFont.truetype("arial.ttf", 11)
        except Exception:
            font = ImageFont.load_default()
            font_small = font

        for box_item in detected_boxes:
            x1, y1, x2, y2 = box_item["bbox_pixels"]
            txt = box_item["text"]
            # Draw thick green box with label
            draw.rectangle([x1, y1, x2, y2], outline="#00FF00", width=3)
            draw.rectangle([x1, max(0, y1 - 18), x1 + len(txt) * 8 + 6, y1], fill="#00FF00")
            draw.text((x1 + 3, max(0, y1 - 16)), txt, fill="black", font=font_small)

        out_img_path = out_dir / f"{base_name}_qwen_annotated.jpg"
        annotated_img.save(out_img_path, quality=95)
        log_img_path = logs_dir / f"{base_name}_qwen_annotated.jpg"
        shutil.copy(out_img_path, log_img_path)

        entry_summary = {
            "name": base_name,
            "category": cat,
            "path": str(photo_path),
            "image_size": [w, h],
            "inference_time_sec": round(elapsed, 3),
            "response_text": response_text.strip(),
            "detected_boxes": detected_boxes,
            "output_image": str(out_img_path),
            "log_image": str(log_img_path)
        }
        results_summary.append(entry_summary)
        print(f"  -> Total boxes found: {len(detected_boxes)}\n")

    # Save summary JSON
    report_path = out_dir / "qwen25_vl_test_results.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results_summary, f, indent=2, ensure_ascii=False)

    print("=" * 65)
    print(f"Results saved to: {report_path}")
    print(f"Annotated images saved to: {out_dir}")
    print(f"Log images copied to: {logs_dir}")
    print("=" * 65)

if __name__ == "__main__":
    main()
