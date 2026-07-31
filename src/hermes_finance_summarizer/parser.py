# src/hermes_finance_summarizer/parser.py
import re
import pandas as pd
import pdfplumber
from typing import List, Dict, Optional
import sys

def _detect_column(headers: List[str], patterns: List[str]) -> Optional[str]:
    """Finds the first header column matching any of the given regex patterns."""
    for col in headers:
        for pat in patterns:
            if re.search(pat, str(col), re.IGNORECASE):
                return col
    return None

def standardize_dataframe(df: pd.DataFrame) -> List[Dict]:
    """
    Auto-detects date, description, and amount columns in a DataFrame,
    cleans the values, and returns a list of standardized transaction dicts.
    """
    # Clean column headers
    df.columns = [str(c).strip() for c in df.columns]
    headers = list(df.columns)

    # Regex patterns for bank header variations
    date_col = _detect_column(headers, [r"date", r"time", r"posted"])
    desc_col = _detect_column(headers, [r"desc", r"narration", r"merchant", r"particulars", r"details"])
    
    # Check for single amount column OR separate Debit/Credit columns
    amount_col = _detect_column(headers, [r"amount", r"amt", r"value"])
    debit_col = _detect_column(headers, [r"debit", r"withdrawal", r"dr"])
    credit_col = _detect_column(headers, [r"credit", r"deposit", r"cr"])

    if not date_col or not desc_col or not (amount_col or debit_col):
        if not sys.stdin.isatty():
            raise ValueError(
                f"Unknown bank format detected in headless mode! Headers: {headers}. "
                "Please run parser interactively once to map this bank."
            )
        print("--- Manual Column Mapping Required ---")

    transactions = []

    for _, row in df.iterrows():
        date_str = str(row[date_col]).strip()
        desc_str = str(row[desc_col]).strip()
        
        # Skip empty rows or summary rows
        if not date_str or not desc_str or date_str.lower() == "nan":
            continue

        amount = 0.0
        try:
            if amount_col and pd.notna(row[amount_col]):
                val_str = re.sub(r"[^\d.-]", "", str(row[amount_col]))
                amount = float(val_str) if val_str else 0.0
            elif debit_col and pd.notna(row[debit_col]):
                val_str = re.sub(r"[^\d.-]", "", str(row[debit_col]))
                amount = float(val_str) if val_str else 0.0
            elif credit_col and pd.notna(row[credit_col]):
                # If you want to track income differently, you can handle credits here.
                # For spending analysis, we primarily look at debits.
                val_str = re.sub(r"[^\d.-]", "", str(row[credit_col]))
                amount = -float(val_str) if val_str else 0.0
        except ValueError:
            amount = 0.0

        # We only care about spending (positive debit amounts) for the expenditure summary
        if amount > 0:
            transactions.append({
                "txn_date": date_str,
                "raw_merchant": desc_str,
                "amount": amount
            })

    return transactions

def parse_csv(filepath: str) -> List[Dict]:
    """Parses a CSV statement export."""
    df = pd.read_csv(filepath)
    return standardize_dataframe(df)

def parse_pdf(filepath: str) -> List[Dict]:
    """
    Parses a PDF statement using pdfplumber table extraction.
    Combines tables across all pages into a single DataFrame.
    """
    all_rows = []
    headers = None

    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table and len(table) > 1:
                if not headers:
                    headers = [str(c).strip() if c else f"col_{i}" for i, c in enumerate(table[0])]
                # Append rows excluding header
                all_rows.extend(table[1:])

    if not all_rows or not headers:
        raise ValueError("Could not extract tabular data from PDF. Make sure it is not a scanned image.")

    df = pd.DataFrame(all_rows, columns=headers)
    return standardize_dataframe(df)

def parse_statement(filepath: str) -> List[Dict]:
    """Dispatcher that routes to CSV or PDF parser based on extension."""
    if filepath.lower().endswith(".csv"):
        return parse_csv(filepath)
    elif filepath.lower().endswith(".pdf"):
        return parse_pdf(filepath)
    else:
        raise ValueError("Unsupported file format. Please upload a .csv or .pdf file.")

if __name__ == "__main__":
    # Test CSV Parsing with Synthetic Bank Statement Data
    import os
    test_csv_path = "test_statement.csv"
    
    synthetic_data = """Date,Narration,Debit Amount,Credit Amount
01-07-2026,UPI/P2A/3892/SWIGGY BANGALORE,450.00,0
02-07-2026,POS *ZEPTO INSTAMART PUNE,320.50,0
05-07-2026,NETFLIX.COM #8928374,649.00,0
10-07-2026,SALARY CREDIT JULY,0,85000.00
12-07-2026,UBER *TRIP 8392019 IN,210.00,0
"""
    with open(test_csv_path, "w") as f:
        f.write(synthetic_data)

    print("Testing CSV Statement Parser...")
    txns = parse_statement(test_csv_path)
    for t in txns:
        print(f"  {t['txn_date']} | {t['raw_merchant'][:25]:<25} | Rs. {t['amount']}")

    # Clean up test file
    if os.path.exists(test_csv_path):
        os.remove(test_csv_path)