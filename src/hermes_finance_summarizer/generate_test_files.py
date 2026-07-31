# src/hermes_finance_summarizer/generate_test_files.py
import os
import pandas as pd
import matplotlib.pyplot as plt

OUTPUT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "statements")
)

# Comprehensive 35-row realistic Indian bank statement for August 2026
TEST_TRANSACTIONS = [
    # --- INCOME & REFUNDS (Should be ignored by spend totals) ---
    {"Date": "01-08-2026", "Narration": "NEFT/SALARY CREDIT AUGUST 2026 ACCT# 00001928374810", "Debit": 0.0, "Credit": 95000.00},
    {"Date": "04-08-2026", "Narration": "AMAZON INDIA REFUND ORDER #89283", "Debit": 0.0, "Credit": 1499.00},
    
    # --- SUBSCRIPTIONS (Testing recurring & price hikes) ---
    {"Date": "02-08-2026", "Narration": "NETFLIX.COM SUBSCRIPTION 4532-8901-2831-9012", "Debit": 799.00, "Credit": 0.0},
    {"Date": "03-08-2026", "Narration": "SPOTIFY INDIA PREM MUMBAI", "Debit": 119.00, "Credit": 0.0},
    {"Date": "05-08-2026", "Narration": "APPLE ICLOUD STORAGE 50GB", "Debit": 75.00, "Credit": 0.0},
    {"Date": "08-08-2026", "Narration": "CHATGPT PLUS OPENAI", "Debit": 1950.00, "Credit": 0.0},

    # --- DINING & COFFEE (Testing seed keywords + LLM unseen brands) ---
    {"Date": "02-08-2026", "Narration": "UPI/P2A/3892/SWIGGY BANGALORE", "Debit": 380.00, "Credit": 0.0},
    {"Date": "06-08-2026", "Narration": "POS *BLUE TOKAI COFFEE PUNE IN", "Debit": 340.00, "Credit": 0.0},
    {"Date": "09-08-2026", "Narration": "UPI/P2M/01928/ZOMATO FOOD ORDER", "Debit": 520.00, "Credit": 0.0},
    {"Date": "10-08-2026", "Narration": "UPI/P2A/11029/SWIGGY BANGALORE", "Debit": 450.00, "Credit": 0.0},  # Duplicate Pair A
    {"Date": "11-08-2026", "Narration": "UPI/P2A/99381/SWIGGY BANGALORE", "Debit": 450.00, "Credit": 0.0},  # Duplicate Pair B (24 hours later)
    {"Date": "15-08-2026", "Narration": "THIRD WAVE COFFEE ROASTERS PUNE", "Debit": 410.00, "Credit": 0.0},
    {"Date": "18-08-2026", "Narration": "STARBUCKS INDIA KALYANI NAGAR", "Debit": 550.00, "Credit": 0.0},
    {"Date": "22-08-2026", "Narration": "UPI/P2M/ZOMATO LIMITED", "Debit": 290.00, "Credit": 0.0},

    # --- GROCERIES (Testing Zepto, Blinkit, BigBasket) ---
    {"Date": "03-08-2026", "Narration": "POS *ZEPTO INSTAMART PUNE IN", "Debit": 840.00, "Credit": 0.0},
    {"Date": "07-08-2026", "Narration": "BLINKIT COMMERCE BANGALORE", "Debit": 1150.00, "Credit": 0.0},
    {"Date": "12-08-2026", "Narration": "BIGBASKET DAILY PUNE", "Debit": 620.00, "Credit": 0.0},
    {"Date": "19-08-2026", "Narration": "POS *ZEPTO INSTAMART PUNE IN", "Debit": 430.00, "Credit": 0.0},
    {"Date": "26-08-2026", "Narration": "BLINKIT GROCERY DELIVERY", "Debit": 890.00, "Credit": 0.0},

    # --- TRANSPORT (Uber, Ola, Metro) ---
    {"Date": "04-08-2026", "Narration": "UBER *TRIP 8392019 IN", "Debit": 240.00, "Credit": 0.0},
    {"Date": "11-08-2026", "Narration": "OLA CABS PUNE RIDE", "Debit": 190.00, "Credit": 0.0},
    {"Date": "17-08-2026", "Narration": "PUNE METRO RECHARGE UPI", "Debit": 200.00, "Credit": 0.0},
    {"Date": "24-08-2026", "Narration": "UBER *TRIP 9918230 IN", "Debit": 310.00, "Credit": 0.0},

    # --- ENTERTAINMENT & HEALTH (Unseen LLM mappings) ---
    {"Date": "05-08-2026", "Narration": "UPI/P2M/BOOKMYSHOW CINEMAS PUNE", "Debit": 920.00, "Credit": 0.0},
    {"Date": "13-08-2026", "Narration": "STEAM GAMES ONLINE PURCHASE", "Debit": 3499.00, "Credit": 0.0},
    {"Date": "14-08-2026", "Narration": "POS *CULT.FIT HEALTH BANGALORE", "Debit": 4500.00, "Credit": 0.0},
    {"Date": "21-08-2026", "Narration": "APOLLO PHARMACY PUNE IN", "Debit": 780.00, "Credit": 0.0},

    # --- SHOPPING (Testing MAD Z-Score Spike Alert) ---
    {"Date": "07-08-2026", "Narration": "AMAZON INDIA ONLINE SHOPPING", "Debit": 1499.00, "Credit": 0.0},
    {"Date": "14-08-2026", "Narration": "APPLE STORE BKC MUMBAI 4532-8901-2831-9012", "Debit": 89900.00, "Credit": 0.0},  # Massive Spike!
    {"Date": "20-08-2026", "Narration": "FLIPKART INTERNET PVT LTD", "Debit": 2199.00, "Credit": 0.0},
    {"Date": "25-08-2026", "Narration": "NYKAA E-RETAIL MUMBAI", "Debit": 1250.00, "Credit": 0.0},
    {"Date": "28-08-2026", "Narration": "UNIQLO INDIA APPAREL PUNE", "Debit": 3990.00, "Credit": 0.0},

    # --- TRANSFERS & UTILITIES ---
    {"Date": "10-08-2026", "Narration": "ZERODHA BROKING LTD FUND TRANSFER", "Debit": 5000.00, "Credit": 0.0},
    {"Date": "16-08-2026", "Narration": "AIRTEL BROADBAND BILL PUNE", "Debit": 1179.00, "Credit": 0.0},
    {"Date": "27-08-2026", "Narration": "GROWW INVESTMENTS MUTUAL FUND", "Debit": 3000.00, "Credit": 0.0},
]

def generate_csv(filepath: str):
    """Generates a comprehensive 35-row CSV bank statement."""
    df = pd.DataFrame(TEST_TRANSACTIONS)
    df.to_csv(filepath, index=False)
    print(f"[+] Successfully generated CSV statement ({len(df)} rows): {filepath}")

def generate_pdf(filepath: str):
    """
    Generates a clean, 2-page tabular PDF statement using matplotlib
    so pdfplumber can extract borders and text accurately.
    """
    df = pd.DataFrame(TEST_TRANSACTIONS)
    
    # Format currency columns for visual cleanliness
    df_formatted = df.copy()
    df_formatted["Debit"] = df_formatted["Debit"].apply(lambda x: f"{x:,.2f}" if x > 0 else "0.00")
    df_formatted["Credit"] = df_formatted["Credit"].apply(lambda x: f"{x:,.2f}" if x > 0 else "0.00")
    
    # Split into two pages (18 rows per page) so table rows don't get squished
    page_size = 18
    num_pages = (len(df_formatted) + page_size - 1) // page_size

    from matplotlib.backends.backend_pdf import PdfPages
    with PdfPages(filepath) as pdf:
        for i in range(num_pages):
            chunk = df_formatted.iloc[i * page_size : (i + 1) * page_size]
            
            fig, ax = plt.subplots(figsize=(10, 7.5))
            ax.axis("tight")
            ax.axis("off")
            
            # Title header for each page
            ax.set_title(f"HDFC/ICICI Statement of Account — August 2026 (Page {i+1} of {num_pages})", 
                         fontsize=12, fontweight="bold", pad=15)

            table = ax.table(
                cellText=chunk.values,
                colLabels=chunk.columns,
                cellLoc="left",
                loc="center",
                colWidths=[0.15, 0.55, 0.15, 0.15]
            )
            
            table.auto_set_font_size(False)
            table.set_fontsize(9)
            table.scale(1.0, 1.8)
            
            # Style table header row
            for col_idx in range(len(chunk.columns)):
                cell = table[0, col_idx]
                cell.set_facecolor("#E5E7EB")
                cell.set_text_props(weight="bold")
                
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

    print(f"[+] Successfully generated PDF statement ({num_pages} pages, {len(df)} rows): {filepath}")

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    csv_path = os.path.join(OUTPUT_DIR, "test_statement_detailed.csv")
    pdf_path = os.path.join(OUTPUT_DIR, "test_statement_detailed.pdf")
    
    print("="*65)
    print(" 🛠️ GENERATING COMPREHENSIVE TEST DATASETS FOR HERMES BOT")
    print("="*65)
    
    generate_csv(csv_path)
    generate_pdf(pdf_path)
    
    print("\n[✓] Both test files are ready inside 'data/statements/'!")
    print("    -> Drag and drop either file into Discord to test the Bot!")