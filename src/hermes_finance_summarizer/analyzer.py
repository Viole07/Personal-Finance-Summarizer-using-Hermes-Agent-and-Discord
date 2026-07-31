# src/hermes_finance_summarizer/analyzer.py
from typing import List, Dict
import pandas as pd
import numpy as np
from hermes_finance_summarizer.db import get_connection
import re

def detect_duplicates(transactions: List[Dict]) -> List[Dict]:
    """
    Flags transactions with the same normalized merchant and exact same amount
    occurring within 72 hours of each other.
    """
    if not transactions:
        return []
    
    df = pd.DataFrame(transactions)
    # Parse dates flexibly
    df["dt"] = pd.to_datetime(df["txn_date"], dayfirst=True, errors="coerce")
    df = df.sort_values(by=["normalized_merchant", "amount", "dt"])
    
    duplicates = []
    
    for i in range(len(df) - 1):
        row_a = df.iloc[i]
        row_b = df.iloc[i + 1]
        
        # Check if same merchant and amount
        if (row_a["normalized_merchant"] == row_b["normalized_merchant"] and
            abs(row_a["amount"] - row_b["amount"]) < 0.01):
            
            # Check time diff (within 3 days / 72 hours)
            if pd.notna(row_a["dt"]) and pd.notna(row_b["dt"]):
                diff_hours = abs((row_b["dt"] - row_a["dt"]).total_seconds()) / 3600.0
                if diff_hours <= 72:
                    duplicates.append({
                        "merchant": row_a["normalized_merchant"],
                        "amount": row_a["amount"],
                        "date_1": str(row_a["txn_date"]),
                        "date_2": str(row_b["txn_date"]),
                        "reason": f"Identical charge within {int(diff_hours)} hours"
                    })
                    
    return duplicates

def detect_subscription_hikes(current_txns: List[Dict]) -> List[Dict]:
    """
    Detects price increases for recurring subscriptions across billing cycles
    by matching on the primary brand token (first alphanumeric word).
    """
    conn = get_connection()
    cursor = conn.cursor()
    hikes = []
    
    for t in current_txns:
        if t.get("category") != "Subscriptions":
            continue
            
        merchant = t["normalized_merchant"]
        current_amt = t["amount"]
        current_month = t.get("statement_month", "")
        
        # Extract the primary brand keyword (e.g., "NETFLIX" from "NETFLIX.COM SUBSCRIPTION")
        tokens = re.findall(r'[A-Z0-9]+', merchant.upper())
        if not tokens:
            continue
        brand_token = tokens[0]
        
        # Match any historical subscription containing the same brand token
        cursor.execute("""
            SELECT amount, statement_month, normalized_merchant FROM transactions
            WHERE category = 'Subscriptions'
              AND normalized_merchant LIKE ?
              AND statement_month != ?
            ORDER BY statement_month DESC LIMIT 1
        """, (f"%{brand_token}%", current_month))
        
        row = cursor.fetchone()
        if row:
            past_amt = row["amount"]
            past_month = row["statement_month"]
            delta = current_amt - past_amt
            pct_change = (delta / past_amt) * 100 if past_amt > 0 else 0
            
            # Require >= Rs. 20 OR >= 5% increase to ignore currency/rounding noise
            if delta >= 20.0 or pct_change >= 5.0:
                hikes.append({
                    "merchant": merchant,
                    "current_amount": current_amt,
                    "previous_amount": past_amt,
                    "previous_month": past_month,
                    "hike_percentage": round(pct_change, 1)
                })
                
    conn.close()
    return hikes
    conn = get_connection()
    cursor = conn.cursor()
    hikes = []
    
    for t in current_txns:
        merchant = t["normalized_merchant"]
        current_amt = t["amount"]
        
        # Use LIKE for fuzzy substring matching against historical subscriptions
        cursor.execute("""
            SELECT amount, statement_month, normalized_merchant FROM transactions
            WHERE (normalized_merchant LIKE ? OR ? LIKE '%' || normalized_merchant || '%')
              AND statement_month != ?
            ORDER BY statement_month DESC LIMIT 1
        """, (f"%{merchant}%", merchant, t.get("statement_month", "")))
        
        row = cursor.fetchone()
        if row:
            past_amt = row["amount"]
            past_month = row["statement_month"]
            delta = current_amt - past_amt
            pct_change = (delta / past_amt) * 100 if past_amt > 0 else 0
            
            # Must increase by at least Rs. 20 OR > 5% to avoid currency/rounding noise
            if delta >= 20.0 or pct_change >= 5.0:
                hikes.append({
                    "merchant": merchant,
                    "current_amount": current_amt,
                    "previous_amount": past_amt,
                    "previous_month": past_month,
                    "hike_percentage": round(pct_change, 1)
                })
                
    conn.close()
    return hikes


def detect_spending_spikes(current_month: str, current_totals: Dict[str, float]) -> List[Dict]:
    """
    Compares current month category totals against historical rolling averages
    using Modified Z-Score based on Median Absolute Deviation (MAD).
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT category, total_spend FROM monthly_summary
        WHERE month != ?
    """, (current_month,))
    rows = cursor.fetchall()
    conn.close()
    
    # Organize historical data by category
    history: Dict[str, List[float]] = {}
    for r in rows:
        history.setdefault(r["category"], []).append(r["total_spend"])
        
    spikes = []
    
    for cat, current_spend in current_totals.items():
        past_spends = history.get(cat, [])
        if not past_spends or len(past_spends) < 2:
            continue # Not enough history to calculate deviation
            
        median = float(np.median(past_spends))
        mad = float(np.median(np.abs(np.array(past_spends) - median)))
        
        if mad < 1.0:
            mad = 1.0 # Prevent division by zero for stable categories
            
        mod_z = 0.6745 * abs(current_spend - median) / mad
        
        # Flag if Modified Z-Score > 3.0 and spend is higher than median
        if mod_z > 3.0 and current_spend > median:
            pct_increase = ((current_spend - median) / median) * 100 if median > 0 else 100
            spikes.append({
                "category": cat,
                "current_spend": current_spend,
                "historical_median": median,
                "spike_percentage": round(pct_increase, 1),
                "z_score": round(mod_z, 2)
            })
            
    return spikes

if __name__ == "__main__":
    print("Testing Anomaly Engine (Duplicate Detection)...")
    sample_txns = [
        {"txn_date": "01-07-2026", "normalized_merchant": "SWIGGY", "amount": 450.0},
        {"txn_date": "02-07-2026", "normalized_merchant": "SWIGGY", "amount": 450.0},
        {"txn_date": "15-07-2026", "normalized_merchant": "SWIGGY", "amount": 450.0},
    ]
    dups = detect_duplicates(sample_txns)
    for d in dups:
        print(f"  Flagged: {d['merchant']} | Rs. {d['amount']} on {d['date_1']} & {d['date_2']}")