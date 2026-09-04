from pathlib import Path
import importlib.util
import cv2
import numpy as np

ROOT = Path(r"C:\Users\dikarm\Documents\Server\OCR-FOTO-P3STE")
SOURCE = ROOT / "03_photos_export/BTP BD/AXC/ZP 101A BTT-MSG/100.jpg"
OUTPUT = ROOT / "OCR_Foto_Timemark_App/logs/temp_main_masks_canny_demo.jpg"
MAIN = ROOT / "edit_timemark_ide1.py"

spec = importlib.util.spec_from_file_location("main_detector", MAIN)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

img_bgr = cv2.imread(str(SOURCE))
if img_bgr is None:
    raise SystemExit(f"Cannot read: {SOURCE}")
img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
h, w = img_bgr.shape[:2]

# Run the exact production detector stages, in production order.
red = module.find_red_guide(img_rgb, y_start=0)
cyan = module.find_cyan_guide_inverted(img_rgb, y_start=0)
custom = module.find_custom1_hsv_guide(img_rgb, y_start=0)
selected = red or cyan or custom

# Visualize the exact selected guide mask approximately from its returned box.
mask_view = np.zeros((h, w), np.uint8)
if selected:
    x1, y1, x2, y2 = selected
    cv2.rectangle(mask_view, (x1, y1), (x2, y2), 255, -1)

# Canny is deliberately applied only inside the production detector's guide box.
# It is an auxiliary edge view, not a replacement for production guide selection.
roi = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
roi_mask = np.zeros_like(roi)
if selected:
    roi_mask[y1:y2 + 1, x1:x2 + 1] = 255
roi_gray = cv2.bitwise_and(roi, roi, mask=roi_mask)
edges = cv2.Canny(roi_gray, 35, 110)

hough_view = img_bgr.copy()
lines = cv2.HoughLinesP(edges, 1, np.pi / 1800, threshold=8,
                        minLineLength=max(12, int(h * .035)), maxLineGap=8)
accepted = 0
if lines is not None:
    for a, b, c, d in lines.reshape(-1, 4):
        angle = abs(np.degrees(np.arctan2(d - b, c - a)))
        if 87 <= angle <= 93:
            cv2.line(hough_view, (a, b), (c, d), (0, 0, 255), 2)
            accepted += 1
if selected:
    cv2.rectangle(hough_view, (x1, y1), (x2, y2), (0, 255, 0), 1)


def panel(im, title):
    out = im.copy()
    cv2.rectangle(out, (0, 0), (w, 28), (25, 25, 25), -1)
    cv2.putText(out, title, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, .44,
                (0, 255, 255), 1, cv2.LINE_AA)
    return out

panels = [
    panel(img_bgr, "1 Original"),
    panel(cv2.cvtColor(mask_view, cv2.COLOR_GRAY2BGR),
          f"2 Main detector: red={red} cyan={cyan} custom={custom}"),
    panel(cv2.cvtColor(roi_mask, cv2.COLOR_GRAY2BGR), "3 Exact selected guide ROI"),
    panel(cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR), "4 Canny inside selected ROI"),
    panel(hough_view, f"5 HLP vertical lines: {accepted}; green=main guide"),
]
canvas = np.full((h * 2, w * 3, 3), 35, np.uint8)
canvas[:h, :w] = panels[0]
canvas[:h, w:2*w] = panels[1]
canvas[:h, 2*w:3*w] = panels[2]
canvas[h:, :w] = panels[3]
canvas[h:, w:2*w] = panels[4]
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
cv2.imwrite(str(OUTPUT), canvas)
print(f"output={OUTPUT}")
print(f"source={SOURCE}")
print(f"red={red} cyan={cyan} custom={custom} selected={selected}")
print(f"accepted_vertical_lines={accepted}")
