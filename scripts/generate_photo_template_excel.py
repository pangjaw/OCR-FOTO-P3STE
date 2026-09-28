import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.worksheet.pagebreak import Break
from pathlib import Path

def create_photo_template():
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    # Styles
    font_title = Font(name="Arial", size=11, bold=True, color="1E293B")
    font_subtitle = Font(name="Arial", size=9.5, bold=True, color="334155")
    font_date = Font(name="Arial", size=9.5, bold=True, color="475569")
    
    font_asset_title = Font(name="Arial", size=9, bold=True, color="0F172A")
    font_photo_box = Font(name="Arial", size=8.5, italic=True, color="94A3B8")
    font_label = Font(name="Arial", size=9, bold=True, color="1E293B")
    
    fill_header_box = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    fill_asset_title = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    fill_photo_box = PatternFill(start_color="FAFAFA", end_color="FAFAFA", fill_type="solid")
    
    border_thin_gray = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1")
    )
    border_title_row = Border(
        left=Side(style="medium", color="3B82F6"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1")
    )
    border_double_bottom = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="double", color="94A3B8")
    )

    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center")
    
    def setup_page(ws, num_pages=1):
        ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
        ws.page_setup.paperSize = ws.PAPERSIZE_A4
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = num_pages
        ws.page_margins.left = 0.4
        ws.page_margins.right = 0.4
        ws.page_margins.top = 0.4
        ws.page_margins.bottom = 0.4
        ws.page_margins.header = 0.2
        ws.page_margins.footer = 0.2
        
        # Column widths
        ws.column_dimensions['A'].width = 2.5
        ws.column_dimensions['B'].width = 27.5
        ws.column_dimensions['C'].width = 3.0
        ws.column_dimensions['D'].width = 27.5
        ws.column_dimensions['E'].width = 3.0
        ws.column_dimensions['F'].width = 27.5
        ws.column_dimensions['G'].width = 2.5

    def draw_header(ws, start_row, doc_title, checklist_loc, date_str):
        ws.row_dimensions[start_row].height = 8
        
        # Row 1: FOTO DOKUMENTASI
        r1 = start_row + 1
        ws.row_dimensions[r1].height = 19
        ws.merge_cells(start_row=r1, start_column=2, end_row=r1, end_column=6)
        c1 = ws.cell(row=r1, column=2, value=doc_title)
        c1.font = font_title
        c1.alignment = align_center
        
        # Row 2: PERAWATAN ...
        r2 = start_row + 2
        ws.row_dimensions[r2].height = 17
        ws.merge_cells(start_row=r2, start_column=2, end_row=r2, end_column=6)
        c2 = ws.cell(row=r2, column=2, value=checklist_loc)
        c2.font = font_subtitle
        c2.alignment = align_center
        
        # Row 3: Tanggal
        r3 = start_row + 3
        ws.row_dimensions[r3].height = 17
        ws.merge_cells(start_row=r3, start_column=2, end_row=r3, end_column=6)
        c3 = ws.cell(row=r3, column=2, value=date_str)
        c3.font = font_date
        c3.alignment = align_center
        
        ws.row_dimensions[start_row + 4].height = 8
        return start_row + 5

    def draw_asset_row(ws, start_row, asset_idx, asset_text, is_last=False):
        # 1. Asset Title Bar
        r_title = start_row
        ws.row_dimensions[r_title].height = 19
        ws.merge_cells(start_row=r_title, start_column=2, end_row=r_title, end_column=6)
        for col in range(2, 7):
            cell = ws.cell(row=r_title, column=col)
            cell.fill = fill_asset_title
            cell.border = border_thin_gray
        
        c_title = ws.cell(row=r_title, column=2, value=f"{asset_idx}. {asset_text}")
        c_title.font = font_asset_title
        c_title.alignment = align_left
        c_title.border = border_title_row

        # 2. Photo Boxes Row (Height 125 pt)
        r_box = start_row + 1
        ws.row_dimensions[r_box].height = 125
        
        # Col B: Foto 0%
        cB = ws.cell(row=r_box, column=2, value="[ Sisipkan Foto 0% di sini ]\n(Klik Insert > Pictures)")
        cB.font = font_photo_box
        cB.alignment = align_center
        cB.fill = fill_photo_box
        cB.border = border_thin_gray
        
        # Col D: Foto 50%
        cD = ws.cell(row=r_box, column=4, value="[ Sisipkan Foto 50% di sini ]\n(Klik Insert > Pictures)")
        cD.font = font_photo_box
        cD.alignment = align_center
        cD.fill = fill_photo_box
        cD.border = border_thin_gray
        
        # Col F: Foto 100%
        cF = ws.cell(row=r_box, column=6, value="[ Sisipkan Foto 100% di sini ]\n(Klik Insert > Pictures)")
        cF.font = font_photo_box
        cF.alignment = align_center
        cF.fill = fill_photo_box
        cF.border = border_thin_gray
        
        # 3. Label Row (Height 17 pt)
        r_lbl = start_row + 2
        ws.row_dimensions[r_lbl].height = 17
        
        lB = ws.cell(row=r_lbl, column=2, value="Foto 0%")
        lB.font = font_label
        lB.alignment = align_center
        lB.border = border_thin_gray
        
        lD = ws.cell(row=r_lbl, column=4, value="Foto 50%")
        lD.font = font_label
        lD.alignment = align_center
        lD.border = border_thin_gray
        
        lF = ws.cell(row=r_lbl, column=6, value="Foto 100%")
        lF.font = font_label
        lF.alignment = align_center
        lF.border = border_thin_gray
        
        # Spacer
        r_sp = start_row + 3
        ws.row_dimensions[r_sp].height = 8 if not is_last else 4
        return r_sp + 1

    # -------------------------------------------------------------
    # SHEET 1: Model 4 Aset (1 Halaman A4)
    # -------------------------------------------------------------
    ws1 = wb.create_sheet(title="Model 4 Aset (1 Hlm)")
    setup_page(ws1, num_pages=1)
    
    curr = draw_header(ws1, 1, 
                       doc_title="FOTO DOKUMENTASI", 
                       checklist_loc="PERAWATAN PERAGA SINYAL ELEKTRIK 1 BULANAN CILEBUT", 
                       date_str="14 Juni 2025")
    
    sample_assets_4 = [
        "SIN11781 : SINYAL MASUK J20 CLT",
        "SIN11783 : SINYAL MASUK J14 CLT",
        "SIN11861 : SINYAL MASUK J10 CLT",
        "SIN11862 : SINYAL KELUAR J12A CLT"
    ]
    for i, a_text in enumerate(sample_assets_4, 1):
        curr = draw_asset_row(ws1, curr, i, a_text, is_last=(i==4))

    # -------------------------------------------------------------
    # SHEET 2: Model 5 Aset (2 Halaman A4)
    # -------------------------------------------------------------
    ws2 = wb.create_sheet(title="Model 5 Aset (2 Hlm)")
    setup_page(ws2, num_pages=2)
    
    # Halaman 1
    curr2 = draw_header(ws2, 1, 
                        doc_title="FOTO DOKUMENTASI", 
                        checklist_loc="PERAWATAN AXLE COUNTER SIEMENS 1 BULANAN CILEBUT", 
                        date_str="14 Juni 2025")
    
    sample_assets_5 = [
        "AXL11625 : AXLE COUNTER ZP 12A CLT",
        "AXL11633 : AXLE COUNTER ZP 22A CLT",
        "AXL11626 : AXLE COUNTER ZP 12B CLT",
        "AXL11632 : AXLE COUNTER ZP 22B CLT",
        "AXL11627 : AXLE COUNTER ZP 13 CLT"
    ]
    
    for i in range(1, 5):
        curr2 = draw_asset_row(ws2, curr2, i, sample_assets_5[i-1], is_last=(i==4))
        
    # Page break after row 20
    break_row = curr2 - 1
    ws2.row_breaks.append(Break(id=break_row))
    
    # Halaman 2 (Lanjutan untuk aset ke-5)
    curr2 = draw_header(ws2, curr2, 
                        doc_title="FOTO DOKUMENTASI (LANJUTAN)", 
                        checklist_loc="PERAWATAN AXLE COUNTER SIEMENS 1 BULANAN CILEBUT", 
                        date_str="14 Juni 2025")
    
    curr2 = draw_asset_row(ws2, curr2, 5, sample_assets_5[4], is_last=True)

    # -------------------------------------------------------------
    # SHEET 3: Model 1 Aset (1 Halaman A4)
    # -------------------------------------------------------------
    ws3 = wb.create_sheet(title="Model 1 Aset (1 Hlm)")
    setup_page(ws3, num_pages=1)
    
    curr3 = draw_header(ws3, 1, 
                        doc_title="FOTO DOKUMENTASI", 
                        checklist_loc="PERAWATAN CATU DAYA BOGOR", 
                        date_str="26 Februari 2025")
    
    curr3 = draw_asset_row(ws3, curr3, 1, "CDA10020 : CATU DAYA SENTRAL TELEKOMUNIKASI BOO", is_last=True)

    # -------------------------------------------------------------
    # SHEET 4: Petunjuk Penggunaan
    # -------------------------------------------------------------
    ws_guide = wb.create_sheet(title="Petunjuk Pakai", index=0)
    ws_guide.column_dimensions['A'].width = 3
    ws_guide.column_dimensions['B'].width = 85
    
    guide_lines = [
        ("PETUNJUK PENGGUNAAN TEMPLATE HALAMAN FOTO DOKUMENTASI", True, 13, "1E3A8A"),
        ("", False, 10, "000000"),
        ("Template ini dirancang presisi sesuai ukuran kertas A4 Portrait untuk diekspor menjadi PDF.", False, 10, "334155"),
        ("Tersedia 3 model pilihan sheet pada tab di bawah:", False, 10, "334155"),
        ("  1. 'Model 4 Aset (1 Hlm)' : Standar 4 aset (4 baris x 3 foto) pas 1 lembar A4.", True, 10, "0F172A"),
        ("  2. 'Model 5 Aset (2 Hlm)' : 4 aset di Halaman 1, dan aset ke-5 otomatis di Halaman 2.", True, 10, "0F172A"),
        ("  3. 'Model 1 Aset (1 Hlm)' : Untuk perawatan yang hanya berisi 1 aset tunggal.", True, 10, "0F172A"),
        ("", False, 10, "000000"),
        ("CARA MENGEDIT TEKS & MENEMPELKAN FOTO:", True, 11, "1E3A8A"),
        ("  1. Klik pada sel judul, nama perawatan, lokasi, atau tanggal di bagian atas untuk mengedit teks.", False, 10, "334155"),
        ("  2. Klik pada baris nama aset untuk mengubah kode dan nama aset yang dirawat.", False, 10, "334155"),
        ("  3. Untuk memasukkan foto ke kotak:", True, 10, "334155"),
        ("     - Klik menu 'Insert' (Sisipkan) > 'Pictures' (Gambar) > 'This Device'.", False, 10, "334155"),
        ("     - Pilih file foto 0%, 50%, atau 100%.", False, 10, "334155"),
        ("     - Tips: Tahan tombol [ALT] pada keyboard saat menggeser atau memperkecil sudut foto,", True, 10, "0284C7"),
        ("       maka foto akan otomatis MENEMPEL RAPI (Snap to Grid) persis di bingkai kotak kotak!", True, 10, "0284C7"),
        ("", False, 10, "000000"),
        ("CARA MENGEKSPOR MENJADI PDF:", True, 11, "1E3A8A"),
        ("  1. Buka sheet yang ingin diekspor (misal: 'Model 4 Aset').", False, 10, "334155"),
        ("  2. Klik menu 'File' > 'Export' > 'Create PDF/XPS' (atau 'Save As' > pilih jenis file 'PDF (*.pdf)').", False, 10, "334155"),
        ("  3. Klik Publish/Save. Halaman PDF yang dihasilkan akan rapi, presisi, dan siap digabung ke PDF lama.", False, 10, "334155"),
    ]
    
    for r_idx, (text, is_bold, sz, col) in enumerate(guide_lines, 2):
        ws_guide.row_dimensions[r_idx].height = 20 if text else 10
        cell = ws_guide.cell(row=r_idx, column=2, value=text)
        cell.font = Font(name="Arial", size=sz, bold=is_bold, color=col)
        cell.alignment = Alignment(vertical="center")

    out_file1 = Path("templates/TEMPLATE_HALAMAN_FOTO_DOKUMENTASI.xlsx")
    out_file1.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(out_file1))
    
    # Also save to root for convenient access
    out_file2 = Path("TEMPLATE_HALAMAN_FOTO_DOKUMENTASI.xlsx")
    wb.save(str(out_file2))
    
    print(f"[OK] Successfully created template Excel:")
    print(f"  - {out_file1.resolve()}")
    print(f"  - {out_file2.resolve()}")

if __name__ == "__main__":
    create_photo_template()
