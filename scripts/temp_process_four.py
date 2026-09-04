from pathlib import Path
import importlib.util
import cv2
import numpy as np

ROOT = Path(r"C:\Users\dikarm\Documents\Server\OCR-FOTO-P3STE")
MAIN = ROOT / "edit_timemark_ide1.py"
OUT = ROOT / "OCR_Foto_Timemark_App/logs/temp_four_hsv_canny.jpg"
INPUTS = [
    ROOT / "03_photos_export/BTP BD/SINYAL/L47A BOP/100.jpg",
    ROOT / "03_photos_export/BTP BD/SINYAL/JL26A BOP/50.jpg",
    ROOT / "03_photos_export/BTP BD/SINYAL/J28 BOP/0.jpg",
    ROOT / "03_photos_export/BTP BD/SINYAL/MB101 MSG-CCR/100.jpg",
]

spec = importlib.util.spec_from_file_location("main_detector", MAIN)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def panel(im, title):
    h, w = im.shape[:2]
    out = im.copy()
    cv2.rectangle(out, (0, 0), (w, 26), (25, 25, 25), -1)
    cv2.putText(out, title[:48], (5, 18), cv2.FONT_HERSHEY_SIMPLEX, .38,
                (0, 255, 255), 1, cv2.LINE_AA)
    return out

def process(source):
    img = cv2.imread(str(source))
    if img is None:
        return [np.zeros((300, 300, 3), np.uint8)] * 5, f"MISSING: {source.name}"
    h, w = img.shape[:2]
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    red = module.find_red_guide(rgb, y_start=0)
    cyan = module.find_cyan_guide_inverted(rgb, y_start=0)
    custom = module.find_custom1_hsv_guide(rgb, y_start=0)
    selected = red or cyan or custom
    roi_mask = np.zeros((h, w), np.uint8)
    if selected:
        x1, y1, x2, y2 = selected
        roi_mask[y1:y2 + 1, x1:x2 + 1] = 255
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.bitwise_and(gray, gray, mask=roi_mask), 35, 110)
    view = img.copy()
    count = 0
    lines = cv2.HoughLinesP(edges, 1, np.pi / 1800, threshold=8,
                            minLineLength=max(12, int(h * .035)), maxLineGap=8)
    if lines is not None:
        for a, b, c, d in lines.reshape(-1, 4):
            angle = abs(np.degrees(np.arctan2(d - b, c - a)))
            if 87 <= angle <= 93:
                cv2.line(view, (a, b), (c, d), (0, 0, 255), 2)
                count += 1
    if selected:
        cv2.rectangle(view, (x1, y1), (x2, y2), (0, 255, 0), 1)
    result = [
        panel(img, source.parent.name + "/" + source.name),
        panel(cv2.cvtColor(roi_mask, cv2.COLOR_GRAY2BGR), f"Main guide: {selected}"),
        panel(cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR), "Canny inside guide ROI"),
        panel(view, f"HLP vertical={count}; red=HLP green=main"),
    ]
    # Keep 4 panels per photo; repeat metadata in first panel.
    return result, f"{source.name}: red={red}, cyan={cyan}, custom={custom}, HLP={count}"

rows = []
for source in INPUTS:
    panels, summary = process(source)
    print(summary)
    rows.append(panels)

# Four photos x four panels, each panel 300x300.
cell = 300
canvas = np.full((len(rows) * cell, 4 * cell, 3), 35, np.uint8)
for row_i, panels in enumerate(rows):
    for col_i, p in enumerate(panels):
        canvas[row_i * cell:(row_i + 1) * cell,
               col_i * cell:(col_i + 1) * cell] = cv2.resize(p, (cell, cell))
OUT.parent.mkdir(parents=True, exist_ok=True)
cv2.imwrite(str(OUT), canvas)
print(f"output={OUT}")
