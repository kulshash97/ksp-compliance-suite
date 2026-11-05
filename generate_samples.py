import pandas as pd

books_data = {
    "invoice_number": ["INV/2026/101", "INV/2026/102", "INV/2026/103"],
    "supplier_gstin": ["36AAAAA0000A1Z5", "36AAAAA0000A1Z5", "36BBBBB1111B2Z3"],
    "taxable_value": [50000, 30000, 20000],
    "cgst": [4500, 2700, 1800],
    "sgst": [4500, 2700, 1800],
    "total_tax": [9000, 5400, 3600],
    "total_value": [59000, 35400, 23600]
}

gstr2b_data = {
    "invoice_number": ["INV2026101", "INV/2026/102"],  # 101 has stripped slashes, 103 is missing in 2B
    "supplier_gstin": ["36AAAAA0000A1Z5", "36AAAAA0000A1Z5"],
    "taxable_value": [50000, 30000],
    "cgst": [4500, 2700],
    "sgst": [4500, 2700],
    "total_tax": [9000, 5400],
    "total_value": [59000, 35400]
}

pd.DataFrame(books_data).to_excel("sample_books.xlsx", index=False)
pd.DataFrame(gstr2b_data).to_excel("sample_gstr2b.xlsx", index=False)
print("Generated sample_books.xlsx and sample_gstr2b.xlsx!")
