# src/hermes_finance_summarizer/categorizer.py
from typing import Optional, Tuple
from hermes_finance_summarizer.normalizer import clean_merchant_name
from hermes_finance_summarizer.db import get_cached_category, cache_merchant

# 1. High-Priority Semantic Keywords (Evaluated FIRST)
# Ensures specific expense types and merchant names beat generic payment methods.
SEMANTIC_KEYWORDS = {
    # Housing
    "RENT": "Housing",
    "LANDLORD": "Housing",
    "MAINTENANCE": "Housing",
    "ELECTRICITY": "Housing",
    "BROADBAND": "Housing",
    "AIRTEL": "Housing",
    "JIO": "Housing",

    # Subscriptions
    "NETFLIX": "Subscriptions",
    "SPOTIFY": "Subscriptions",
    "APPLE ICLOUD": "Subscriptions",
    "ICLOUD": "Subscriptions",
    "CHATGPT": "Subscriptions",
    "OPENAI": "Subscriptions",
    "PRIME VIDEO": "Subscriptions",
    "DISNEY": "Subscriptions",
    "HOTSTAR": "Subscriptions",

    # Income
    "SALARY": "Income",
    "DIVIDEND": "Income",
    "INTEREST": "Income",

    # Dining
    "SWIGGY": "Dining",
    "ZOMATO": "Dining",
    "STARBUCKS": "Dining",
    "BLUE TOKAI": "Dining",
    "THIRD WAVE": "Dining",
    "MCDONALDS": "Dining",
    "DOMINOS": "Dining",

    # Groceries
    "ZEPTO": "Groceries",
    "BLINKIT": "Groceries",
    "BIGBASKET": "Groceries",
    "INSTAMART": "Groceries",
    "DMART": "Groceries",
    "RELIANCE FRESH": "Groceries",

    # Transport
    "UBER": "Transport",
    "OLA": "Transport",
    "METRO": "Transport",
    "RAPIDO": "Transport",
    "IRCTC": "Transport",
    "FUEL": "Transport",
    "PETROL": "Transport",

    # Entertainment
    "BOOKMYSHOW": "Entertainment",
    "PVR": "Entertainment",
    "INOX": "Entertainment",
    "STEAM": "Entertainment",
    "PLAYSTATION": "Entertainment",

    # Health
    "APOLLO": "Health",
    "PHARMEASY": "Health",
    "1MG": "Health",
    "CULT.FIT": "Health",
    "GYM": "Health",
    "CLINIC": "Health",
    "HOSPITAL": "Health",

    # Shopping
    "AMAZON": "Shopping",
    "FLIPKART": "Shopping",
    "MYNTRA": "Shopping",
    "NYKAA": "Shopping",
    "UNIQLO": "Shopping",
    "APPLE STORE": "Shopping",
    "ZARA": "Shopping",
    "H&M": "Shopping",
}

# 2. Low-Priority Fallback Keywords (Evaluated LAST)
# Only triggers if no semantic keyword matches.
FALLBACK_KEYWORDS = {
    "NEFT": "Transfers",
    "IMPS": "Transfers",
    "RTGS": "Transfers",
    "UPI": "Transfers",
    "ZERODHA": "Transfers",
    "GROWW": "Transfers",
    "UPSTOX": "Transfers",
    "ATM WITHDRAWAL": "Transfers",
    "CASH WITHDRAWAL": "Transfers",
}


def seed_default_cache():
    """
    Populates the SQLite merchant cache with seed rules on first run.
    Seeds both semantic and fallback mappings so common lookups are O(1).
    """
    for merchant, category in SEMANTIC_KEYWORDS.items():
        cache_merchant(merchant, category, confidence=1.0)
    for merchant, category in FALLBACK_KEYWORDS.items():
        cache_merchant(merchant, category, confidence=0.80)


def get_category_fast(raw_description: str) -> Tuple[str, Optional[str]]:
    """
    Attempts to categorize a transaction locally without calling an LLM.
    
    Priority Order:
    1. Local SQLite Merchant Cache (O(1) exact/normalized match)
    2. High-priority Semantic Keywords (Housing, Subscriptions, Dining, etc.)
    3. Low-priority Fallback Keywords (Payment methods, Transfers)
    4. Returns None if unmatched (routes to LLM batch fallback)
    
    Returns:
        Tuple[str, Optional[str]]: (normalized_merchant, category_or_None)
    """
    normalized = clean_merchant_name(raw_description)

    # Step 1: Check SQLite Merchant Cache
    cached_cat = get_cached_category(normalized)
    if cached_cat:
        return normalized, cached_cat

    # Step 2: Check High-Priority Semantic Keywords
    # Check against both normalized string and raw description (for embedded terms like "RENT")
    upper_raw = raw_description.upper()
    for keyword, category in SEMANTIC_KEYWORDS.items():
        if keyword in normalized or keyword in upper_raw:
            # Auto-save to SQLite cache so future lookups are instant
            cache_merchant(normalized, category, confidence=0.95)
            return normalized, category

    # Step 3: Check Low-Priority Fallback Keywords
    for keyword, category in FALLBACK_KEYWORDS.items():
        if keyword in normalized or keyword in upper_raw:
            cache_merchant(normalized, category, confidence=0.80)
            return normalized, category

    # Step 4: No local rule matched — requires OpenRouter/Cohere LLM fallback
    return normalized, None


if __name__ == "__main__":
    from hermes_finance_summarizer.db import init_db

    init_db()
    seed_default_cache()

    test_cases = [
        "NEFT-4455667788-IFSC-SBIN0011223-RENT",
        "UPI/P2A/4019283749/SWIGGY/BANGALORE",
        "NETFLIX.COM SUBSCRIPTION #928374",
        "NEFT FUND TRANSFER TO JOHN DOE",
        "POS *BLUE TOKAI COFFEE PUNE IN",
    ]

    print("=" * 65)
    print(" TESTING TWO-STAGE KEYWORD CATEGORIZER PRIORITY")
    print("=" * 65)

    for desc in test_cases:
        merchant, cat = get_category_fast(desc)
        print(f"Raw: {desc[:38]:<38} -> Normalized: {merchant:<16} | Category: {cat}")