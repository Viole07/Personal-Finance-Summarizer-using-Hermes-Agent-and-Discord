# src/hermes_finance_summarizer/test_suite.py
import os
from hermes_finance_summarizer.db import init_db, get_connection
from hermes_finance_summarizer.categorizer import seed_default_cache
from hermes_finance_summarizer.main import process_monthly_statement

def seed_historical_baseline():
    """
    Seeds 3 months of normal, baseline spending into monthly_summary
    so our MAD Z-Score spike detector has enough historical variance to work with.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Normal monthly baseline (~Rs. 2,000 on Shopping, ~Rs. 4,000 on Dining)
    history_data = [
        ("2026-05", "Shopping", 2100.0, 3),
        ("2026-05", "Dining", 4200.0, 8),
        ("2026-06", "Shopping", 1900.0, 2),
        ("2026-06", "Dining", 3800.0, 7),
        ("2026-07", "Shopping", 2200.0, 4),
        ("2026-07", "Dining", 4500.0, 9),
    ]
    
    for month, cat, total, count in history_data:
        cursor.execute("""
            INSERT OR REPLACE INTO monthly_summary (month, category, total_spend, txn_count)
            VALUES (?, ?, ?, ?)
        """, (month, cat, total, count))
        
    conn.commit()
    conn.close()
    print("[+] Seeded 3 months of historical baseline spend (May, June, July 2026).")

def create_hdfc_style_csv() -> str:
    """Simulates an HDFC/ICICI bank export with different column headers and a refund row."""
    filepath = "test_hdfc_statement.csv"
    content = """Txn Date,Particulars,Withdrawal Amt,Deposit Amt
03-08-2026,UPI/P2M/91827364/BOOKMYSHOW/PUNE,850.00,0
05-08-2026,POS *CULT.FIT HEALTH BANGALORE,4500.00,0
11-08-2026,AMAZON INDIA REFUND,0,1200.00
15-08-2026,UPI/P2A/019283/BLUE TOKAI COFFEE/PUNE,420.00,0
"""
    with open(filepath, "w") as f:
        f.write(content)
    return filepath

def create_spike_csv() -> str:
    """Simulates a statement with a massive shopping splurge to trigger the Z-Score alert."""
    filepath = "test_august_spike.csv"
    content = """Date,Narration,Debit,Credit
02-08-2026,APPLE STORE INDIA MUMBAI,24900.00,0
04-08-2026,ZOMATO FOOD ORDER,480.00,0
08-08-2026,AMAZON ONLINE SHOPPING,3500.00,0
12-08-2026,UBER RIDE PUNE,240.00,0
"""
    with open(filepath, "w") as f:
        f.write(content)
    return filepath

def run_suite():
    init_db()
    seed_default_cache()
    
    print("\n" + "="*70)
    print(" TEST 1: HDFC/ICICI FORMAT & UNSEEN MERCHANTS (LLM LEARNING) ")
    print("="*70)
    hdfc_file = create_hdfc_style_csv()
    report_1 = process_monthly_statement(hdfc_file, "2026-08-A")
    print("\n" + report_1)
    if os.path.exists(hdfc_file):
        os.remove(hdfc_file)

    print("\n" + "="*70)
    print(" TEST 2: STATISTICAL SPIKE DETECTION (MAD Z-SCORE ALERT) ")
    print("="*70)
    seed_historical_baseline()
    spike_file = create_spike_csv()
    report_2 = process_monthly_statement(spike_file, "2026-08")
    print("\n" + report_2)
    if os.path.exists(spike_file):
        os.remove(spike_file)

if __name__ == "__main__":
    run_suite()