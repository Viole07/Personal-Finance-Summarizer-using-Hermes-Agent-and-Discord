# tests/test_normalizer.py
import pytest
from hermes_finance_summarizer.normalizer import mask_pii, clean_merchant_name

def test_mask_upi_phone_number():
    """Verifies that 10-digit phone numbers in UPI handles are redacted."""
    raw = "PAYMENT REF 9876543210@okaxis TO VENDOR"
    masked = mask_pii(raw)
    assert "[UPI_PHONE_MASKED]" in masked
    assert "9876543210" not in masked
    assert masked == "PAYMENT REF [UPI_PHONE_MASKED] TO VENDOR"

def test_mask_credit_card_number():
    """Verifies 16-digit credit/debit card redaction."""
    raw = "POS *SHARMA APPAREL STORE 4532-8901-2831-9012"
    masked = mask_pii(raw)
    assert "[CARD_MASKED]" in masked
    assert "4532-8901-2831-9012" not in masked

def test_mask_ifsc_and_account_number():
    """Verifies Indian bank IFSC codes and account number sequences are redacted."""
    raw = "NEFT TO 00001928374810 IFSC HDFC0001234 TECH SOLUTIONS PVT"
    masked = mask_pii(raw)
    assert "[IFSC_MASKED]" in masked
    assert "HDFC0001234" not in masked
    assert "00001928374810" not in masked

def test_clean_merchant_name_preserves_brand_tokens():
    """Verifies that clean_merchant_name strips prefixes/PII while keeping brand names intact."""
    raw = "UPI/P2A/9876543210@okaxis/UNKNOWN BAKERY XYZ PUNE"
    cleaned = clean_merchant_name(raw)
    
    assert "UNKNOWN BAKERY XYZ PUNE" in cleaned
    assert "UPI/P2A" not in cleaned      # Check that the banking prefix was removed
    assert "9876543210" not in cleaned    # Check that the phone number was redacted
    assert "[UPI_PHONE_MASKED]" in cleaned  # Check that the mask tag is present