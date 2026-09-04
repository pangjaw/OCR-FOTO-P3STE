#!/usr/bin/env python3
"""
scripts/export_dinasan_excel.py
--------------------------------
Generates official KAI-standard "DAFTAR DINASAN PEGAWAI" Excel spreadsheet.
Features:
- Automatic month & day-of-week generation (Senin..Minggu)
- Official KAI logo insertion
- Clean grid styling matching KAI Resor Sintelisp format
- Resor set to "P" for all days
- Tim 1 & Tim 2 personnel set to "P" on active maintenance days
- Non-scheduled cells left blank for user's manual customization
- Automatic Excel COUNTIF formulas for row & column totals
- Real-time Excel Conditional Formatting for P, S, M, L, CT codes
- Official signature block
"""

import sys
import os
import re
import json
import calendar
from datetime import datetime
from pathlib import Path
import argparse

import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as OpenpyxlImage
from openpyxl.formatting.rule import CellIsRule

# Try importing employee_manager helpers
try:
    from employee_manager import (
        load_pegawai_config,
        extract_page1_tim1_personnel,
        get_tim2_roster_for_date
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from employee_manager import (
        load_pegawai_config,
        extract_page1_tim1_personnel,
        get_tim2_roster_for_date
    )

import fitz

MONTH_NAMES_ID = {
    1: "JANUARI", 2: "FEBRUARI", 3: "MARET", 4: "APRIL",
    5: "MEI", 6: "JUNI", 7: "JULI", 8: "AGUSTUS",
    9: "SEPTEMBER", 10: "OKTOBER", 11: "NOVEMBER", 12: "DESEMBER"
}

DAY_NAMES_ID = {
    0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis",
    4: "Jumat", 5: "Sabtu", 6: "Minggu"
}


def build_dinasan_workbook(year: int, month: int, schedule_path: Path, config_path: Path, output_path: Path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Dinasan {MONTH_NAMES_ID[month]} {year}"
    ws.views.sheetView[0].showGridLines = True

    # ── 1. Load Configurations ──
    cfg = load_pegawai_config(config_path)
    resor = cfg.get("resor", {
        "nama": "FURQON SUSILO WARDOYO",
        "nipp": "64465",
        "jabatan": "KUPT RESOR STL 1.21 BOGOR"
    })
    kaur_list = cfg.get("kaur", [])
    pnc_list = cfg.get("pnc", [])

    # ── 2. Read Schedule & Determine Active Duties ──
    schedules = []
    if schedule_path.exists():
        try:
            with open(schedule_path, "r", encoding="utf-8") as f:
                s_data = json.load(f)
                schedules = s_data.get("schedules", [])
        except Exception as e:
            print(f"[WARN] Could not load schedule.json: {e}")

    # Map: day_number (1..num_days) -> {"tim1_files": [], "tim2_files": []}
    num_days = calendar.monthrange(year, month)[1]
    days_activity = {d: {"tim1": [], "tim2": []} for d in range(1, num_days + 1)}

    for item in schedules:
        iso = item.get("iso_date")
        if not iso:
            continue
        try:
            dt = datetime.strptime(iso, "%Y-%m-%d")
            if dt.year == year and dt.month == month:
                t = item.get("tim", 1)
                f_name = item.get("file")
                if t == 2:
                    days_activity[dt.day]["tim2"].append(f_name)
                else:
                    days_activity[dt.day]["tim1"].append(f_name)
        except Exception:
            continue

    # Pre-scan Tim 1 personnel from 01_pdf_source
    src_dir = Path("01_pdf_source")
    pdf_by_date = {}
    if src_dir.exists():
        for pdf_file in src_dir.glob("*.pdf"):
            m = re.search(r'(\d{2})-(\d{2})-(\d{4})', pdf_file.name)
            if m:
                d_str = m.group(0)
                if d_str not in pdf_by_date:
                    pdf_by_date[d_str] = pdf_file

    # Build duty roster per day: day -> set of UPPERCASE names on duty
    daily_duties = {}
    for day in range(1, num_days + 1):
        duty_set = set()
        # Resor is always on duty
        duty_set.add(resor.get("nama", "").strip().upper())

        act = days_activity[day]
        has_tim1 = len(act["tim1"]) > 0
        has_tim2 = len(act["tim2"]) > 0

        d_str = f"{day:02d}-{month:02d}-{year}"
        t1_tokens = set()

        if (has_tim1 or has_tim2) and d_str in pdf_by_date:
            try:
                doc = fitz.open(pdf_by_date[d_str])
                t1_tokens = extract_page1_tim1_personnel(doc)
                doc.close()
            except Exception:
                pass

        if has_tim1:
            for k in kaur_list:
                k_name = k.get("nama", "").strip().upper()
                if k_name in t1_tokens or any(part in t1_tokens for part in k_name.split() if len(part) > 3):
                    duty_set.add(k_name)
            for p in pnc_list:
                p_name = p.get("nama", "").strip().upper()
                if p_name in t1_tokens or any(part in t1_tokens for part in p_name.split() if len(part) > 3):
                    duty_set.add(p_name)

        if has_tim2:
            roster_tim2 = get_tim2_roster_for_date(d_str, t1_tokens, cfg)
            for r in roster_tim2:
                duty_set.add(r.get("nama", "").strip().upper())

        daily_duties[day] = duty_set

    # ── 3. Formatting & Styles ──
    font_family = "Arial"
    thin_border = Side(border_style="thin", color="000000")
    medium_border = Side(border_style="medium", color="000000")
    double_bottom = Side(border_style="double", color="000000")

    border_all_thin = Border(left=thin_border, right=thin_border, top=thin_border, bottom=thin_border)
    border_header_outer = Border(left=thin_border, right=thin_border, top=medium_border, bottom=thin_border)

    fill_header_gray = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    fill_sunday_red = PatternFill(start_color="FFE6E6", end_color="FFE6E6", fill_type="solid")
    fill_red_solid = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")
    fill_blue_solid = PatternFill(start_color="00B0F0", end_color="00B0F0", fill_type="solid")

    font_title = Font(name=font_family, size=13, bold=True)
    font_subtitle = Font(name=font_family, size=11, bold=True)
    font_bold = Font(name=font_family, size=9, bold=True)
    font_bold_white = Font(name=font_family, size=9, bold=True, color="FFFFFF")
    font_regular = Font(name=font_family, size=9)
    font_small = Font(name=font_family, size=8)

    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_center_vert = Alignment(horizontal="center", vertical="center", text_rotation=90)
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)

    # ── 4. Insert Header & Titles ──
    # Logo KAI
    logo_path = Path("config/kai_logo.png")
    if logo_path.exists():
        try:
            img = OpenpyxlImage(str(logo_path))
            img.width = 110
            img.height = 42
            ws.add_image(img, "A1")
        except Exception as e:
            print(f"[WARN] Failed to add KAI logo image: {e}")

    # Title lines
    end_col_idx = 2 + num_days + 3  # NO, NAMA + num_days + L, P, CT
    end_col_letter = get_column_letter(end_col_idx)

    ws.merge_cells(f"A1:{end_col_letter}1")
    title_cell = ws["A1"]
    title_cell.value = "DAFTAR DINASAN PEGAWAI"
    title_cell.font = font_title
    title_cell.alignment = align_center

    ws.merge_cells(f"A2:{end_col_letter}2")
    sub_cell = ws["A2"]
    sub_cell.value = resor.get("jabatan", "RESOR SINTELIS 1.21 BOGOR")
    sub_cell.font = font_subtitle
    sub_cell.alignment = align_center

    ws.row_dimensions[1].height = 24
    ws.row_dimensions[2].height = 20

    # ── 5. Build Table Headers (Rows 3, 4, 5) ──
    # Row 3: Month spanning columns C..end of days
    first_day_col = "C"
    last_day_col = get_column_letter(2 + num_days)

    ws.merge_cells(f"A3:A5")
    ws["A3"].value = "NO"
    ws["A3"].font = font_bold
    ws["A3"].alignment = align_center

    ws.merge_cells(f"B3:B5")
    ws["B3"].value = "NAMA"
    ws["B3"].font = font_bold
    ws["B3"].alignment = align_center

    ws.merge_cells(f"{first_day_col}3:{last_day_col}3")
    month_cell = ws[f"{first_day_col}3"]
    month_cell.value = MONTH_NAMES_ID[month]
    month_cell.font = font_bold
    month_cell.alignment = align_center
    month_cell.fill = fill_header_gray

    # Total columns header
    tot_l_col = get_column_letter(2 + num_days + 1)
    tot_p_col = get_column_letter(2 + num_days + 2)
    tot_ct_col = get_column_letter(2 + num_days + 3)

    ws.merge_cells(f"{tot_l_col}3:{tot_ct_col}3")
    ws[f"{tot_l_col}3"].value = "TOTAL"
    ws[f"{tot_l_col}3"].font = font_bold
    ws[f"{tot_l_col}3"].alignment = align_center

    # Row 4: Day of Week Name
    ws.row_dimensions[4].height = 55
    ws.row_dimensions[5].height = 20

    for d in range(1, num_days + 1):
        col_let = get_column_letter(2 + d)
        dt = datetime(year, month, d)
        day_name = DAY_NAMES_ID[dt.weekday()]
        is_sunday = dt.weekday() == 6

        cell_day = ws[f"{col_let}4"]
        cell_day.value = day_name
        cell_day.font = font_small
        cell_day.alignment = align_center_vert
        if is_sunday:
            cell_day.fill = fill_sunday_red

        cell_num = ws[f"{col_let}5"]
        cell_num.value = d
        cell_num.font = font_bold
        cell_num.alignment = align_center
        if is_sunday:
            cell_num.fill = fill_sunday_red

    # Sub-headers for TOTAL
    ws.merge_cells(f"{tot_l_col}4:{tot_l_col}5")
    ws[f"{tot_l_col}4"].value = "L"
    ws[f"{tot_l_col}4"].font = font_bold_white
    ws[f"{tot_l_col}4"].alignment = align_center
    ws[f"{tot_l_col}4"].fill = fill_red_solid

    ws.merge_cells(f"{tot_p_col}4:{tot_p_col}5")
    ws[f"{tot_p_col}4"].value = "P"
    ws[f"{tot_p_col}4"].font = font_bold
    ws[f"{tot_p_col}4"].alignment = align_center

    ws.merge_cells(f"{tot_ct_col}4:{tot_ct_col}5")
    ws[f"{tot_ct_col}4"].value = "CT"
    ws[f"{tot_ct_col}4"].font = font_bold_white
    ws[f"{tot_ct_col}4"].alignment = align_center
    ws[f"{tot_ct_col}4"].fill = fill_blue_solid

    # Apply borders to header cells
    for r in range(3, 6):
        for c in range(1, end_col_idx + 1):
            ws.cell(row=r, column=c).border = border_all_thin

    # ── 6. Assemble Employee Rows ──
    # Row list: Resor first, then KAURs, then PNCs
    all_employees = []
    # Resor
    all_employees.append({
        "role": "RESOR",
        "nama": resor.get("nama", "FURQON SUSILO WARDOYO"),
        "nipp": resor.get("nipp", "64465")
    })
    for k in kaur_list:
        all_employees.append({
            "role": "KAUR",
            "nama": k.get("nama", ""),
            "nipp": k.get("nipp", "")
        })
    for p in pnc_list:
        all_employees.append({
            "role": "PNC",
            "nama": p.get("nama", ""),
            "nipp": p.get("nipp", "")
        })

    start_data_row = 6
    curr_row = start_data_row
    pnc_start_row = None
    pnc_end_row = None

    for idx, emp in enumerate(all_employees, start=1):
        ws.row_dimensions[curr_row].height = 28
        emp_role = emp["role"]
        emp_name = emp["nama"].strip().upper()
        emp_nipp = emp["nipp"].strip()

        if emp_role == "PNC" and pnc_start_row is None:
            pnc_start_row = curr_row
        if emp_role == "PNC":
            pnc_end_row = curr_row

        # Col A: NO
        c_no = ws.cell(row=curr_row, column=1, value=idx)
        c_no.font = font_bold
        c_no.alignment = align_center
        c_no.border = border_all_thin

        # Col B: NAMA \n NIPP : xxxxx
        disp_text = emp_name
        if emp_nipp:
            disp_text += f"\nNIPP : {emp_nipp}"
        c_nama = ws.cell(row=curr_row, column=2, value=disp_text)
        c_nama.font = font_bold
        c_nama.alignment = align_left
        c_nama.border = border_all_thin

        # Days 1..num_days
        for d in range(1, num_days + 1):
            c_day = ws.cell(row=curr_row, column=2 + d)
            c_day.alignment = align_center
            c_day.border = border_all_thin

            # Resor always gets P
            if emp_role == "RESOR":
                c_day.value = "P"
                c_day.font = font_bold
            else:
                if emp_name in daily_duties.get(d, set()):
                    c_day.value = "P"
                    c_day.font = font_bold
                else:
                    c_day.value = None

        # Formulas for TOTAL
        # L
        cL = ws.cell(row=curr_row, column=2 + num_days + 1)
        cL.value = f'=COUNTIF({first_day_col}{curr_row}:{last_day_col}{curr_row}, "L")'
        cL.font = font_bold
        cL.alignment = align_center
        cL.border = border_all_thin

        # P
        cP = ws.cell(row=curr_row, column=2 + num_days + 2)
        cP.value = f'=COUNTIF({first_day_col}{curr_row}:{last_day_col}{curr_row}, "P")'
        cP.font = font_bold
        cP.alignment = align_center
        cP.border = border_all_thin

        # CT
        cCT = ws.cell(row=curr_row, column=2 + num_days + 3)
        cCT.value = f'=COUNTIF({first_day_col}{curr_row}:{last_day_col}{curr_row}, "CT")'
        cCT.font = font_bold
        cCT.alignment = align_center
        cCT.border = border_all_thin

        curr_row += 1

    end_data_row = curr_row - 1

    # ── 7. Summary Rows below Data ──
    # S, M, L, P(PNC), P(ALL)
    summary_rows = [
        ("S", "S"),
        ("M", "M"),
        ("L", "L"),
        ("P(PNC)", "P_PNC"),
        ("P(ALL)", "P_ALL"),
    ]

    ws.row_dimensions[curr_row].height = 10  # blank spacer row
    curr_row += 1

    sum_start_row = curr_row
    for label, code in summary_rows:
        ws.row_dimensions[curr_row].height = 18
        lbl_cell = ws.cell(row=curr_row, column=2, value=label)
        lbl_cell.font = font_bold
        lbl_cell.alignment = Alignment(horizontal="center", vertical="center")
        lbl_cell.border = border_all_thin

        for d in range(1, num_days + 1):
            col_let = get_column_letter(2 + d)
            s_cell = ws.cell(row=curr_row, column=2 + d)
            s_cell.font = font_regular
            s_cell.alignment = align_center
            s_cell.border = border_all_thin

            if code == "P_PNC":
                if pnc_start_row and pnc_end_row:
                    s_cell.value = f'=COUNTIF({col_let}{pnc_start_row}:{col_let}{pnc_end_row}, "P")'
                else:
                    s_cell.value = 0
            elif code == "P_ALL":
                s_cell.value = f'=COUNTIF({col_let}{start_data_row}:{col_let}{end_data_row}, "P")'
            else:
                s_cell.value = f'=COUNTIF({col_let}{start_data_row}:{col_let}{end_data_row}, "{code}")'

        # Total on the right
        if code in ["S", "M", "L"]:
            tot_cell = ws.cell(row=curr_row, column=2 + num_days + 1)
            tot_cell.value = f'=SUM({first_day_col}{curr_row}:{last_day_col}{curr_row})'
            tot_cell.font = font_bold
            tot_cell.alignment = align_center
            tot_cell.border = border_all_thin
            if code == "L":
                tot_cell.fill = fill_red_solid
                tot_cell.font = font_bold_white

        curr_row += 1

    # ── 8. Conditional Formatting for Shift Cells ──
    # Data range: C6..[last_day_col][end_data_row]
    data_range = f"{first_day_col}{start_data_row}:{last_day_col}{end_data_row}"

    # L = Red
    ws.conditional_formatting.add(data_range, CellIsRule(
        operator='equal', formula=['"L"'], stopIfTrue=True,
        fill=fill_red_solid, font=font_bold_white
    ))
    # S = Green
    ws.conditional_formatting.add(data_range, CellIsRule(
        operator='equal', formula=['"S"'], stopIfTrue=True,
        fill=PatternFill(start_color="00B050", end_color="00B050", fill_type="solid"),
        font=font_bold_white
    ))
    # M = Yellow
    ws.conditional_formatting.add(data_range, CellIsRule(
        operator='equal', formula=['"M"'], stopIfTrue=True,
        fill=PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid"),
        font=font_bold
    ))
    # CT = Blue
    ws.conditional_formatting.add(data_range, CellIsRule(
        operator='equal', formula=['"CT"'], stopIfTrue=True,
        fill=fill_blue_solid, font=font_bold_white
    ))
    # P = Bold
    ws.conditional_formatting.add(data_range, CellIsRule(
        operator='equal', formula=['"P"'], stopIfTrue=True,
        font=font_bold
    ))

    # ── 9. Legend & Signature Block ──
    curr_row += 2
    legend_start = curr_row

    ws.cell(row=curr_row, column=2, value="KETERANGAN :").font = font_bold
    curr_row += 1
    ws.cell(row=curr_row, column=2, value="P :  Dinas Pagi mulai jam 08:00 s.d jam 16:00 (Pemeliharaan dan Perbaikan gangguan)").font = font_small
    curr_row += 1
    ws.cell(row=curr_row, column=2, value="S :  Dinas Siang mulai jam 16:00 s.d jam 24:00 (Piket dan Perbaikan gangguan)").font = font_small
    curr_row += 1
    ws.cell(row=curr_row, column=2, value="M :  Dinas Malam mulai jam 24:00 s.d jam 08:00 (Piket dan Perbaikan gangguan)").font = font_small
    curr_row += 1
    ws.cell(row=curr_row, column=2, value="L :  Libur dinas").font = font_small
    curr_row += 1
    ws.cell(row=curr_row, column=2, value="CT : Cuti Tahunan").font = font_small

    # Signature on the right side
    sig_col = 2 + num_days - 6
    sig_col_let = get_column_letter(sig_col)

    ws.cell(row=legend_start, column=sig_col, value=resor.get("jabatan", "KUPT RESOR STL 1.21 BOGOR")).font = font_bold
    ws.cell(row=legend_start + 4, column=sig_col, value=resor.get("nama", "FURQON SUSILO WARDOYO")).font = font_bold
    ws.cell(row=legend_start + 5, column=sig_col, value=f"NIPP : {resor.get('nipp', '64465')}").font = font_bold

    # ── 10. Column Widths ──
    ws.column_dimensions["A"].width = 5
    ws.column_dimensions["B"].width = 24
    for d in range(1, num_days + 1):
        ws.column_dimensions[get_column_letter(2 + d)].width = 3.6
    ws.column_dimensions[tot_l_col].width = 4.2
    ws.column_dimensions[tot_p_col].width = 4.2
    ws.column_dimensions[tot_ct_col].width = 4.2

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    wb.close()
    print(f"[OK] Dinasan Excel exported successfully -> {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Export KAI Daftar Dinasan Pegawai to Excel")
    parser.add_argument("--month", type=str, default=None, help="Month in YYYY-MM format, e.g. 2026-08")
    parser.add_argument("--schedule", type=str, default="schedule.json", help="Path to schedule.json")
    parser.add_argument("--config", type=str, default="config/daftar_pegawai.json", help="Path to daftar_pegawai.json")
    parser.add_argument("--output", type=str, default=None, help="Output path for .xlsx")
    args = parser.parse_args()

    sch_path = Path(args.schedule)
    cfg_path = Path(args.config)

    # Determine year & month
    year = None
    month = None

    if args.month:
        parts = args.month.split("-")
        year = int(parts[0])
        month = int(parts[1])
    else:
        # Detect from schedule.json
        if sch_path.exists():
            try:
                with open(sch_path, "r", encoding="utf-8") as f:
                    s_data = json.load(f)
                    for item in s_data.get("schedules", []):
                        iso = item.get("iso_date")
                        if iso:
                            dt = datetime.strptime(iso, "%Y-%m-%d")
                            year = dt.year
                            month = dt.month
                            break
            except Exception:
                pass

    if not year or not month:
        now = datetime.now()
        year = now.year
        month = now.month

    m_name = MONTH_NAMES_ID[month]
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = Path(f"logs/DAFTAR_DINASAN_PEGAWAI_{m_name}_{year}.xlsx")

    build_dinasan_workbook(year, month, sch_path, cfg_path, out_path)


if __name__ == "__main__":
    main()
