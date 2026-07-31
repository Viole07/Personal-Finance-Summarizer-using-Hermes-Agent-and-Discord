# src/hermes_finance_summarizer/db.py
import sqlite3
import os
from typing import Optional, Dict, List, Tuple

# Path goes up 3 levels: db.py -> hermes_finance_summarizer -> src -> project root
DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
    "data", 
    "finance.db"
)

TAXONOMY = [
    "Housing", "Groceries", "Dining", "Transport", "Subscriptions", 
    "Entertainment", "Health", "Shopping", "Income", "Transfers", "Other"
]

def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Creates the necessary SQLite tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Merchant Cache Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS merchant_cache (
            normalized_merchant TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            confidence_score REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 2. Transactions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            txn_date TEXT NOT NULL,
            raw_merchant TEXT NOT NULL,
            normalized_merchant TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            statement_month TEXT NOT NULL,
            is_recurring BOOLEAN DEFAULT 0,
            FOREIGN KEY (normalized_merchant) REFERENCES merchant_cache(normalized_merchant)
        )
    """)
    
    # 3. Monthly Summary Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monthly_summary (
            month TEXT NOT NULL,
            category TEXT NOT NULL,
            total_spend REAL NOT NULL,
            txn_count INTEGER NOT NULL,
            PRIMARY KEY (month, category)
        )
    """)

    # Add this table inside init_db() in src/hermes_finance_summarizer/db.py
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bank_header_mappings (
            bank_name TEXT PRIMARY KEY,
            date_col TEXT NOT NULL,
            desc_col TEXT NOT NULL,
            amount_col TEXT,
            debit_col TEXT,
            credit_col TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def get_cached_category(normalized_merchant: str) -> Optional[str]:
    """Returns the cached category for a merchant if it exists."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT category FROM merchant_cache WHERE normalized_merchant = ?",
        (normalized_merchant,)
    )
    row = cursor.fetchone()
    conn.close()
    return row["category"] if row else None

def cache_merchant(normalized_merchant: str, category: str, confidence: float = 1.0):
    """Saves a learned merchant -> category mapping."""
    if category not in TAXONOMY:
        category = "Other"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO merchant_cache (normalized_merchant, category, confidence_score)
        VALUES (?, ?, ?)
    """, (normalized_merchant, category, confidence))
    conn.commit()
    conn.close()


def get_bank_mapping(bank_name: str) -> Optional[Dict[str, str]]:
    """Retrieves a saved column mapping for a known bank."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM bank_header_mappings WHERE LOWER(bank_name) = LOWER(?)",
        (bank_name.strip(),)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def save_bank_mapping(
    bank_name: str, 
    date_col: str, 
    desc_col: str, 
    amount_col: Optional[str] = None,
    debit_col: Optional[str] = None, 
    credit_col: Optional[str] = None
):
    """Saves a user-defined column mapping for a bank into SQLite."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO bank_header_mappings 
        (bank_name, date_col, desc_col, amount_col, debit_col, credit_col)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (bank_name.strip(), date_col, desc_col, amount_col, debit_col, credit_col))
    conn.commit()
    conn.close()
    print(f"[+] Saved permanent column mapping for bank: '{bank_name}'")

    # Add to src/hermes_finance_summarizer/db.py
def reset_db():
    """Wipes all transaction and summary tables for clean test runs."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions")
    cursor.execute("DELETE FROM monthly_summary")
    cursor.execute("DELETE FROM merchant_cache")
    conn.commit()
    conn.close()
    print("[+] Clean slate: All database tables have been wiped.")

if __name__ == "__main__":
    init_db()
    print(f"Database successfully initialized at {DB_PATH}")