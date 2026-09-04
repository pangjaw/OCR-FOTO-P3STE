from pathlib import Path
import importlib.util
import cv2
import numpy as np

ROOT = Path(r"C:\Users\dikarm\Documents\Server\OCR-FOTO-P3STE")
MAIN = ROOT / "edit_timemark_ide1.py"
OUT = ROOT / "OCR_Foto_Timemark_App/logs/temp_compare_main_vs_canny.jpg"
INPUTS = [
    ROOT / "03_photos_export/BTP BD/SINYAL/L47A BOP/100.jpg",
    ROOT / "03_photos_export/BTP BD/SINYAL/JL26A BOP/50.jpg",
    ROOT / "03_photos_export/BTP BD/SINYAL/J28 BOP/0.jpg",
    ROOT / "03_photos_export/BTP BD/SINYAL/MB101 MSG-CCR/100.jpg",
]

spec = importlib.util.spec_from_file_location("main_detector", MAIN)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def detect_hlp(img, guide):
    if not guide:
        return None, 0
    x1, y1, x2, y2 = guide
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    roi_mask = np.zeros(gray.shape, np.uint8)
    roi_mask[y1:y2 + 1, x1:x2 + 1] = 255
    edges = cv2.Canny(cv2.bitwise_and(gray, gray, mask=roi_mask), 35, 110)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 1800, threshold=8,
                            minLineLength=max(12, int(img.shape[0] * .035)), maxLineGap=8)
    segments = []
    if lines is not None:
        for a, b, c, d in lines.reshape(-1, 4):
            angle = abs(np.degrees(np.arctan2(d - b, c - a)))
            if 87 <= angle <= 93:
                segments.append((int(round((a + c) / 2)), min(b, d), max(b, d)))
    if not segments:
        return None, 0

    # Group nearby vertical segments by X, then merge overlapping/nearby Y ranges.
    # This reconstructs one continuous guide instead of returning one HLP fragment.
    groups = []
    for x, y1, y2 in sorted(segments):
        group = next((g for g in groups if abs(x - g[0]) <= 3), None)
        if group is None:
            groups.append([x, [(y1, y2)]])
        else:
            group[1].append((y1, y2))

    merged_groups = []
    for x, ranges in groups:
        merged = []
        for y1, y2 in sorted(ranges):
            if merged and y1 <= merged[-1][1] + 8:
                merged[-1] = (merged[-1][0], max(merged[-1][1], y2))
            else:
                merged.append((y1, y2))
        total = sum(y2 - y1 + 1 for y1, y2 in merged)
        span = merged[-1][1] - merged[0][0] + 1
        merged_groups.append((span, total, x, merged))

    span, total, x, merged = max(merged_groups, key=lambda item: (item[0], item[1]))
    y1, y2 = merged[0][0], merged[-1][1]
    return (x, y1, x, y2), len(segments)


def panel(img, title):
    h, w = img.shape[:2]
    out = img.copy()
    cv2.rectangle(out, (0, 0), (w, 42), (25, 25, 25), -1)
    for i, line in enumerate(title.split("\n")):
        cv2.putText(out, line[:52], (5, 16 + i * 15), cv2.FONT_HERSHEY_SIMPLEX,
                    .35, (0, 255, 255), 1, cv2.LINE_AA)
    return out

rows = []
for source in INPUTS:
    img = cv2.imread(str(source))
    if img is None:
        continue
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    main_box = module.find_red_guide(rgb, y_start=0) or module.find_cyan_guide_inverted(rgb, y_start=0) or module.find_custom1_hsv_guide(rgb, y_start=0)
    hlp_line, count = detect_hlp(img, main_box)

    no_canny = img.copy()
    if main_box:
        x1, y1, x2, y2 = main_box
        cv2.rectangle(no_canny, (x1, y1), (x2, y2), (0, 255, 0), 2)
    no_canny = panel(no_canny, f"NO CANNY: main box\n{source.parent.name}/{source.name}")

    with_canny = img.copy()
    if main_box:
        x1, y1, x2, y2 = main_box
        cv2.rectangle(with_canny, (x1, y1), (x2, y2), (0, 255, 0), 1)
    if hlp_line:
        a, b, c, d = hlp_line
        cv2.line(with_canny, (a, b), (c, d), (0, 0, 255), 2)
    with_canny = panel(with_canny, f"WITH CANNY+HLP: {count} vertical\ngreen=main, red=HLP")
    rows.append((no_canny, with_canny))
    print(f"{source.name}: main={main_box}, hlp={hlp_line}, candidates={count}")

cell = 300
canvas = np.full((len(rows) * cell, 2 * cell, 3), 35, np.uint8)
for i, (left, right) in enumerate(rows):
    canvas[i * cell:(i + 1) * cell, :cell] = cv2.resize(left, (cell, cell))
    canvas[i * cell:(i + 1) * cell, cell:2 * cell] = cv2.resize(right, (cell, cell))
OUT.parent.mkdir(parents=True, exist_ok=True)
cv2.imwrite(str(OUT), canvas)
print(f"output={OUT}")
