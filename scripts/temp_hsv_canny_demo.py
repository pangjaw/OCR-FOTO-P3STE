from pathlib import Path
import cv2
import numpy as np

ROOT = Path(r"C:\Users\dikarm\Documents\Server\OCR-FOTO-P3STE")
SOURCE = ROOT / "03_photos_export/BTP BD/AXC/ZP 101A BTT-MSG/100.jpg"
OUTPUT = ROOT / "OCR_Foto_Timemark_App/logs/temp_hsv_canny_demo.jpg"

img = cv2.imread(str(SOURCE))
if img is None:
    raise SystemExit(f"Cannot read: {SOURCE}")
h, w = img.shape[:2]

# Existing main-script red/yellow HSV logic, converted to OpenCV HSV ranges.
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
b, g, r = cv2.split(img)
red_yellow = (r > 172) & (r > g * 1.5) & (r > b * 1.5) & (g < 195) & (b < 155)
hue = hsv[:, :, 0].astype(float) * 2.0
sat = hsv[:, :, 1].astype(float) * 100.0 / 255.0
mask = red_yellow & ((hue <= 52.0) | (hue >= 330.0)) & (sat >= 63.0)
mask[:, int(w * 0.35):] = False
mask_u8 = (mask.astype(np.uint8) * 255)

# Remove isolated speckles; preserve thin guide lines.
kernel = np.ones((3, 3), np.uint8)
clean = cv2.morphologyEx(mask_u8, cv2.MORPH_OPEN, kernel)
clean = cv2.morphologyEx(clean, cv2.MORPH_CLOSE, np.ones((3, 5), np.uint8))

# Canny only on masked pixels, not on full grayscale image.
masked_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
masked_gray[clean == 0] = 0
edges = cv2.Canny(masked_gray, 35, 110)

# HoughLinesP; red lines show accepted near-vertical candidates only.
hough_view = img.copy()
lines = cv2.HoughLinesP(edges, 1, np.pi / 1800, threshold=8,
                        minLineLength=max(12, int(h * 0.035)), maxLineGap=8)
accepted = 0
if lines is not None:
    for x1, y1, x2, y2 in lines.reshape(-1, 4):
        angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
        if 87 <= angle <= 93:
            cv2.line(hough_view, (x1, y1), (x2, y2), (0, 0, 255), 2)
            accepted += 1

def panel(im, title):
    out = im.copy()
    cv2.rectangle(out, (0, 0), (w, 28), (25, 25, 25), -1)
    cv2.putText(out, title, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, .48,
                (0, 255, 255), 1, cv2.LINE_AA)
    return out

panels = [
    panel(img, "1 Original"),
    panel(cv2.cvtColor(mask_u8, cv2.COLOR_GRAY2BGR), "2 HSV red/yellow mask"),
    panel(cv2.cvtColor(clean, cv2.COLOR_GRAY2BGR), "3 Clean mask"),
    panel(cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR), "4 Canny on mask"),
    panel(hough_view, f"5 HLP vertical candidates: {accepted}"),
]
# 3+2 layout, fixed canvas for Discord preview.
canvas = np.full((h * 2, w * 3, 3), 35, np.uint8)
canvas[:h, :w] = panels[0]
canvas[:h, w:2*w] = panels[1]
canvas[:h, 2*w:3*w] = panels[2]
canvas[h:, :w] = panels[3]
canvas[h:, w:2*w] = panels[4]
cv2.imwrite(str(OUTPUT), canvas)
print(f"output={OUTPUT}")
print(f"source={SOURCE}")
print(f"accepted_vertical_lines={accepted}")
