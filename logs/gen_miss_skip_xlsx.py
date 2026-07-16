"""Parse extract_pdf_dates.py output → Excel log."""
import re, openpyxl, sys

text = open("debug_dates_output.txt", encoding="utf-8").read()

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "MISS + SKIP"
ws.append(["Type", "Filename", "Category", "Identifier", "Date", "Notes"])

for line in text.splitlines():
    line = line.strip()
    if not line:
        continue
    m = re.match(r"\[MISS\] (.+?) -> cat=(\S+) id=(.+) date=(.+?) -- (.+)", line)
    if m:
        ws.append(["MISS", m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)])
        continue
    m = re.match(r"\[SKIP\] (.+?) — (.+)", line)
    if m:
        ws.append(["SKIP", m.group(1), "", "", "", m.group(2)])
        continue

wb.save("logs/step2_miss_skip.xlsx")
print(f"Written {ws.max_row-1} entries to logs/step2_miss_skip.xlsx")
