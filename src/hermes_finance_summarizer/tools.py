# src/hermes_finance_summarizer/tools.py
import os
import json
from typing import Optional, List, Dict, Any
from hermes_finance_summarizer.db import get_connection
from hermes_finance_summarizer.main import process_monthly_statement

def tool_process_statement(filepath: str, statement_month: str) -> str:
    """
    TOOL: Ingests, parses, and categorizes a bank statement (CSV or PDF).
    Returns the narrative Markdown summary of spending and anomalies.
    Use this when the user uploads a new bank statement file.
    """
    if not os.path.exists(filepath):
        return f"Error: File '{filepath}' does not exist on disk."
    try:
        report = process_monthly_statement(filepath, statement_month)
        return report
    except Exception as e:
        return f"Pipeline execution failed: {str(e)}"

def tool_query_category_spend(month: str, category: Optional[str] = None) -> str:
    """
    TOOL: Retrieves spending totals by category for a given month (e.g., '2026-07').
    If category is None, returns all category breakdowns for that month.
    Use this to answer questions like 'How much did I spend on Dining in July?'
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if category:
        cursor.execute("""
            SELECT category, total_spend, txn_count FROM monthly_summary
            WHERE month = ? AND LOWER(category) = LOWER(?)
        """, (month, category))
    else:
        cursor.execute("""
            SELECT category, total_spend, txn_count FROM monthly_summary
            WHERE month = ? ORDER BY total_spend DESC
        """, (month,))
        
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    if not rows:
        return f"No spending data found for month '{month}'" + (f" in category '{category}'." if category else ".")
    return json.dumps(rows, indent=2)

def tool_search_transactions(merchant_query: str, month: Optional[str] = None) -> str:
    """
    TOOL: Searches individual transactions by merchant name (e.g., 'SWIGGY', 'UBER', 'NETFLIX').
    Optionally filters by statement_month (YYYY-MM).
    Use this to answer questions like 'Show me all my Swiggy orders' or 'How much went to Amazon?'
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    sql = """
        SELECT txn_date, raw_merchant, normalized_merchant, amount, category, statement_month
        FROM transactions
        WHERE (normalized_merchant LIKE ? OR raw_merchant LIKE ?)
    """
    params = [f"%{merchant_query}%", f"%{merchant_query}%"]
    
    if month:
        sql += " AND statement_month = ?"
        params.append(month)
        
    sql += " ORDER BY txn_date DESC LIMIT 15"
    
    cursor.execute(sql, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    if not rows:
        return f"No transactions found matching merchant '{merchant_query}'."
    return json.dumps(rows, indent=2)

def tool_compare_months(month_a: str, month_b: str) -> str:
    """
    TOOL: Compares total spend and category differences between two statement months.
    Use this to answer 'Why did I spend more in August than July?' or trend questions.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT month, category, total_spend FROM monthly_summary
        WHERE month IN (?, ?)
    """, (month_a, month_b))
    rows = cursor.fetchall()
    conn.close()
    
    data: Dict[str, Dict[str, float]] = {month_a: {}, month_b: {}}
    for r in rows:
        data[r["month"]][r["category"]] = r["total_spend"]
        
    all_cats = set(data[month_a].keys()).union(set(data[month_b].keys()))
    comparison = []
    
    for cat in all_cats:
        amt_a = data[month_a].get(cat, 0.0)
        amt_b = data[month_b].get(cat, 0.0)
        diff = amt_b - amt_a
        comparison.append({
            "category": cat,
            f"spend_{month_a}": amt_a,
            f"spend_{month_b}": amt_b,
            "difference": round(diff, 2)
        })
        
    return json.dumps(comparison, indent=2)



def tool_get_transactions_by_category(category: str, month: Optional[str] = None) -> str:
    """
    TOOL: Retrieves individual transaction line items for a specific category
    (e.g., 'Income', 'Housing', 'Subscriptions', 'Dining').
    Use this when the user asks to see all transactions under a certain category.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    sql = """
        SELECT txn_date, raw_merchant, normalized_merchant, amount, category, statement_month
        FROM transactions
        WHERE LOWER(category) = LOWER(?)
    """
    params = [category.strip()]
    
    if month:
        sql += " AND statement_month = ?"
        params.append(month)
        
    sql += " ORDER BY txn_date DESC LIMIT 20"
    
    cursor.execute(sql, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    if not rows:
        return f"No transactions found in category '{category}'" + (f" for month '{month}'." if month else ".")
    return json.dumps(rows, indent=2)


# Append to src/hermes_finance_summarizer/tools.py
from hermes_finance_summarizer.analyzer import (
    detect_duplicates,
    detect_spending_spikes,
    detect_subscription_hikes
)

def tool_get_anomalies(month: Optional[str] = None) -> str:
    """
    TOOL: Retrieves detected anomalies including duplicate charges, unusual category spikes,
    and recurring subscription price hikes.
    Use this when the user asks about price increases, weird charges, or duplicates.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if not month:
        cursor.execute("SELECT MAX(statement_month) as latest FROM transactions")
        row = cursor.fetchone()
        month = row["latest"] if row and row["latest"] else "2026-09"
        
    cursor.execute("SELECT * FROM transactions WHERE statement_month = ?", (month,))
    txns = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    if not txns:
        return f"No transactions found for month '{month}' to analyze."
        
    duplicates = detect_duplicates(txns)
    hikes = detect_subscription_hikes(txns)
    
    totals = {}
    for t in txns:
        cat = t["category"]
        totals[cat] = totals.get(cat, 0.0) + t["amount"]
    spikes = detect_spending_spikes(month, totals)
    
    return json.dumps({
        "analyzed_month": month,
        "subscription_price_hikes": hikes,
        "duplicate_charges": duplicates,
        "category_spending_spikes": spikes
    }, indent=2)

def tool_get_transactions_by_category(category: str, month: Optional[str] = None) -> str:
    """
    TOOL: Retrieves individual transaction line items for a specific category
    (e.g., 'Income', 'Housing', 'Subscriptions', 'Dining').
    Use this when the user asks to see all transactions under a certain category.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    sql = """
        SELECT txn_date, raw_merchant, normalized_merchant, amount, category, statement_month
        FROM transactions
        WHERE LOWER(category) = LOWER(?)
    """
    params = [category.strip()]
    
    if month:
        sql += " AND statement_month = ?"
        params.append(month)
        
    sql += " ORDER BY txn_date DESC LIMIT 20"
    
    cursor.execute(sql, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    if not rows:
        return f"No transactions found in category '{category}'" + (f" for month '{month}'." if month else ".")
    return json.dumps(rows, indent=2)