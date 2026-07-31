# src/hermes_finance_summarizer/test_pdf_parser.py
import os
import matplotlib.pyplot as plt
from hermes_finance_summarizer.parser import parse_pdf

def generate_sample_pdf_statement(filepath: str):
    """Generates a clean PDF bank statement with a structured table."""
    data = [
        ["Date", "Narration", "Debit", "Credit"],
        ["01-08-2026", "UPI/P2A/SWIGGY BANGALORE", "450.00", "0.00"],
        ["05-08-2026", "POS *ZEPTO INSTAMART PUNE", "1250.00", "0.00"],
        ["10-08-2026", "NETFLIX.COM SUBSCRIPTION", "649.00", "0.00"],
        ["14-08-2026", "UBER *TRIP 8392 IN", "310.00", "0.00"],
        ["25-08-2026", "SALARY JULY CREDIT", "0.00", "85000.00"]
    ]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.axis("tight")
    ax.axis("off")
    table = ax.table(cellText=data, cellLoc="center", loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.5)

    plt.savefig(filepath, format="pdf", bbox_inches="tight")
    plt.close()
    print(f"[+] Generated sample PDF statement at: {filepath}")

if __name__ == "__main__":
    pdf_path = "test_statement.pdf"
    generate_sample_pdf_statement(pdf_path)

    print("\n[*] Testing pdfplumber extraction on PDF...")
    try:
        txns = parse_pdf(pdf_path)
        print(f"[+] Successfully extracted {len(txns)} transactions from PDF table!")
        for t in txns:
            print(f"  -> {t['txn_date']} | {t['raw_merchant'][:28]:<28} | Rs. {t['amount']}")
    except Exception as e:
        print(f"[-] PDF extraction failed: {e}")
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)