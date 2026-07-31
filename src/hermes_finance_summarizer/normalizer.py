# src/normalizer.py
import re

import re

def mask_pii(text: str) -> str:
    """
    Hard-masks UPI IDs, IFSC codes, card numbers, and bank accounts
    before transaction descriptions can be processed or sent to an LLM.
    """
    # 1. Mask UPI IDs containing phone numbers FIRST (e.g., 9876543210@okaxis)
    text = re.sub(r'\b\d{10}@[a-zA-Z0-9.-]+\b', '[UPI_PHONE_MASKED]', text)
    
    # 2. Mask Indian IFSC codes (e.g., HDFC0000123) and SWIFT codes
    text = re.sub(r'\b[A-Z]{4}0[A-Z0-9]{6}\b', '[IFSC_MASKED]', text)
    
    # 3. Mask 13-16 digit Credit/Debit Card Numbers
    text = re.sub(r'\b(?:\d[ -]*?){13,16}\b', '[CARD_MASKED]', text)
    
    # 4. Mask Indian Bank Account Numbers & 10+ digit numeric sequences LAST
    text = re.sub(r'\b\d{10,18}\b', '[ACCT_MASKED]', text)
    
    return text

def clean_merchant_name(raw_merchant: str) -> str:
    """
    Standardizes merchant names by masking PII, stripping generic banking prefixes,
    and removing whitespace/special characters without over-trimming brand words.
    """
    # Step 1: ALWAYS mask PII first!
    safe_name = mask_pii(raw_merchant)
    
    # Step 2: Strip common banking prefixes (UPI/POS/NEFT/IMPS/RTGS/CARD)
    safe_name = re.sub(r'^(UPI/P2A/|UPI/P2M/|POS \*|NEFT-|IMPS-|RTGS-|CARD )', '', safe_name, flags=re.IGNORECASE)
    
    # Step 3: Remove leading/trailing non-alphanumeric noise and extra spaces
    safe_name = safe_name.strip('*/#- ')
    safe_name = ' '.join(safe_name.split())
    
    return safe_name if safe_name else "UNKNOWN_MERCHANT"

if __name__ == "__main__":
    # Test cases
    samples = [
        "UPI/P2A/402938493029/ZOMATO LIMITED/PUNE",
        "POS *SWIGGY INSTAMART Bangalore IN",
        "NETFLIX.COM #9283746",
        "UBER *TRIP 8392019"
    ]
    for s in samples:
        print(f"{s} --> {clean_merchant_name(s)}")