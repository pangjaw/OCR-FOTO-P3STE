import re

def extract_detect_func(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    match = re.search(r'def detect_asset_type\(.*?\) -> str:.*?(?=\ndef |\nclass |\n\S|\Z)', content, re.DOTALL)
    return match.group(0) if match else ''

exp = extract_detect_func('c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/export_pdf_foto.py')
mrg = extract_detect_func('c:/Users/LAPTOPBOO/Documents/Server/OCR-FOTO-P3STE/merge_pdf_foto.py')

exp_returns = re.findall(r'return "(\w+)"', exp)
mrg_returns = re.findall(r'return "(\w+)"', mrg)

print('export_pdf_foto.py returns:', exp_returns)
print('merge_pdf_foto.py returns:', mrg_returns)
print('Match:', exp_returns == mrg_returns)
