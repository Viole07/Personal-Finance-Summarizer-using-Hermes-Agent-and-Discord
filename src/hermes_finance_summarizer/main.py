import sys
import os
import uuid
from typing import Dict, List
from hermes_finance_summarizer.db import (
    init_db, 
    get_connection, 
    TAXONOMY
)
from hermes_finance_summarizer.categorizer import (
    seed_default_cache, 
    get_category_fast
)
from hermes_finance_summarizer.llm_fallback import categorize_batch_with_llm
from hermes_finance_summarizer.parser import parse_statement
from hermes_finance_summarizer.analyzer import (
    detect_duplicates, 
    detect_spending_spikes,
    detect_subscription_hikes
)
from hermes_finance_summarizer.reporter import (
    generate_spend_chart, 
    generate_markdown_report
)

def process_monthly_statement(filepath: str, statement_month: str) -> str:
    """
    Executes the full pipeline:
    1. Parse CSV/PDF
    2. Categorize (Fast Rule/SQLite Cache -> LLM Fallback)
    3. Save to SQLite transactions & monthly_summary
    4. Run anomaly detection
    5. Generate Markdown report and PNG chart
    """
    print(f"[*] Initializing database and processing: {filepath}")
    init_db()
    seed_default_cache()
    
    # Step 1: Parse
    raw_txns = parse_statement(filepath)
    print(f"[*] Parsed {len(raw_txns)} transactions.")
    
    # Step 2: Categorize Fast & Identify LLM Unmatched Batch
    processed_txns = []
    unmatched_merchants = []
    
    for t in raw_txns:
        norm_merchant, category = get_category_fast(t["raw_merchant"])
        t["normalized_merchant"] = norm_merchant
        
        if category:
            t["category"] = category
        else:
            unmatched_merchants.append(norm_merchant)
            t["category"] = None
        processed_txns.append(t)
        
    # Step 3: LLM Batch Categorization for Unmatched
    if unmatched_merchants:
        print(f"[*] Sending {len(set(unmatched_merchants))} unmatched merchants to Cohere/OpenRouter LLM...")
        llm_map = categorize_batch_with_llm(unmatched_merchants)
        for t in processed_txns:
            if t["category"] is None:
                t["category"] = llm_map.get(t["normalized_merchant"], "Other")
    else:
        print("[*] 100% Cache hit! No LLM calls required.")
        
    # Step 4: Persist to SQLite & Aggregate Totals
    conn = get_connection()
    cursor = conn.cursor()
    
    category_totals: Dict[str, float] = {cat: 0.0 for cat in TAXONOMY}
    
    for t in processed_txns:
        category_totals[t["category"]] = category_totals.get(t["category"], 0.0) + t["amount"]
        txn_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT OR IGNORE INTO transactions 
            (id, txn_date, raw_merchant, normalized_merchant, amount, category, statement_month)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            txn_id, t["txn_date"], t["raw_merchant"], 
            t["normalized_merchant"], t["amount"], 
            t["category"], statement_month
        ))
        
    # Update monthly_summary table
    for cat, total in category_totals.items():
        if total > 0:
            cursor.execute("""
                INSERT OR REPLACE INTO monthly_summary (month, category, total_spend, txn_count)
                VALUES (?, ?, ?, (
                    SELECT COUNT(*) FROM transactions 
                    WHERE statement_month = ? AND category = ?
                ))
            """, (statement_month, cat, total, statement_month, cat))
            
    conn.commit()
    conn.close()
    
    # Step 5: Run Anomaly Detection
    print("[*] Checking for duplicate charges and spending spikes...")
    duplicates = detect_duplicates(processed_txns)
    spikes = detect_spending_spikes(statement_month, category_totals)
    hikes = detect_subscription_hikes(processed_txns)
    
    # Step 6: Generate Visuals and Report
    print("[*] Generating spend chart and Markdown summary...")
    
    # Exclude Income from total expenditure calculation
    total_spend = sum(
        amt for cat, amt in category_totals.items() 
        if cat.lower() != "income"
    )
    
    chart_path = generate_spend_chart(statement_month, category_totals)
    
    # Pass ALL 7 arguments including hikes and chart_path
    report = generate_markdown_report(
        statement_month, total_spend, category_totals, 
        duplicates, spikes, hikes, chart_path
    )
    
    return report

if __name__ == "__main__":
    # Create synthetic test statement if no arguments passed
    test_file = "sample_statement.csv"
    sample_csv = """Date,Narration,Debit Amount,Credit Amount
01-07-2026,UPI/P2A/3892/SWIGGY BANGALORE,450.00,0
02-07-2026,UPI/P2A/3892/SWIGGY BANGALORE,450.00,0
05-07-2026,POS *ZEPTO INSTAMART PUNE,1200.00,0
10-07-2026,NETFLIX.COM #8928374,649.00,0
14-07-2026,UBER *TRIP 8392019 IN,310.00,0
20-07-2026,STEAM GAMES ONLINE,2100.00,0
25-07-2026,SALARY CREDIT JULY,0,85000.00
"""
    with open(test_file, "w") as f:
        f.write(sample_csv)
        
    print("="*60)
    print(" RUNNING HERMES PERSONAL FINANCE SUMMARIZER PIPELINE ")
    print("="*60)
    
    report_output = process_monthly_statement(test_file, "2026-07")
    print("\n" + report_output)
    
    # Clean up temporary test file
    if os.path.exists(test_file):
        os.remove(test_file)