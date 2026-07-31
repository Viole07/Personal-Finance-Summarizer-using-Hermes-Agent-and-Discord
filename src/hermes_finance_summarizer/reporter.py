# src/hermes_finance_summarizer/reporter.py
import os
import matplotlib.pyplot as plt
from typing import Dict, List

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
    "data", 
    "reports"
)

def generate_spend_chart(statement_month: str, category_totals: Dict[str, float]) -> str:
    """
    Generates a horizontal bar chart of EXPENDITURE by category (excluding Income)
    and saves it as a PNG artifact.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Exclude "Income" and 0-spend categories from expenditure charts
    data = {
        k: v for k, v in category_totals.items() 
        if v > 0 and k.lower() != "income"
    }
    if not data:
        return ""
        
    sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)
    categories = [item[0] for item in sorted_items]
    amounts = [item[1] for item in sorted_items]
    
    plt.figure(figsize=(9, 5))
    bars = plt.barh(categories[::-1], amounts[::-1], color="#3B82F6", edgecolor="#1E3A8A")
    
    plt.title(f"Monthly Spend by Category — {statement_month}", fontsize=14, fontweight="bold", pad=15)
    plt.xlabel("Amount (Rs.)", fontsize=11)
    plt.grid(axis="x", linestyle="--", alpha=0.5)
    
    for bar in bars:
        width = bar.get_width()
        plt.text(
            width + max(amounts) * 0.01, 
            bar.get_y() + bar.get_height() / 2, 
            f"Rs. {width:,.2f}", 
            va="center", 
            fontsize=9, 
            color="#1F2937"
        )
    
    plt.tight_layout()
    output_path = os.path.join(OUTPUT_DIR, f"spend_summary_{statement_month}.png")
    plt.savefig(output_path, dpi=200)
    plt.close()
    
    return output_path

def generate_markdown_report(
    statement_month: str,
    total_spend: float,
    category_totals: Dict[str, float],
    duplicates: List[Dict],
    spikes: List[Dict],
    hikes: List[Dict],
    chart_path: str
) -> str:
    """
    Generates a Markdown summary separating Income from Monthly Expenditure.
    """
    total_income = category_totals.get("Income", 0.0)
    
    lines = [
        f"# 📊 Personal Finance Report ({statement_month})",
        "",
        f"**Total Income Received:** `Rs. {total_income:,.2f}`",
        f"**Total Monthly Expenditure:** `Rs. {total_spend:,.2f}`",
        "---",
        "## 💸 Spend Breakdown"
    ]
    
    # Sort expense categories descending (excluding Income)
    for cat, amt in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
        if amt > 0 and cat.lower() != "income":
            pct = (amt / total_spend) * 100 if total_spend > 0 else 0
            lines.append(f"- **{cat}:** Rs. {amt:,.2f} (*{pct:.1f}%*)")
            
    # Add Anomalies Section
    if duplicates or spikes or hikes:
        lines.append("")
        lines.append("---")
        lines.append("## 🚨 Detected Anomalies")
        
        if hikes:
            lines.append("\n### Recurring Subscription Price Hikes")
            for h in hikes:
                lines.append(
                    f"- **{h['merchant']}**: Rs. {h['current_amount']:,.2f} "
                    f"(*+{h['hike_percentage']}%* up from Rs. {h['previous_amount']:,.2f} in `{h['previous_month']}`)"
                )
        
        if duplicates:
            lines.append("\n### Duplicate Charges")
            for d in duplicates:
                lines.append(
                    f"- **{d['merchant']}**: Rs. {d['amount']} charged on "
                    f"`{d['date_1']}` and `{d['date_2']}`"
                )
                
        if spikes:
            lines.append("\n### Unusual Category Spikes")
            for s in spikes:
                lines.append(
                    f"- **{s['category']}**: Rs. {s['current_spend']:,.2f} "
                    f"(*+{s['spike_percentage']}%* above median)"
                )
                
    if chart_path:
        lines.append("")
        lines.append(f"*Chart saved locally to:* `{chart_path}`")
        
    return "\n".join(lines)

if __name__ == "__main__":
    print("Testing Reporter Graph & Markdown Generation...")
    sample_totals = {
        "Dining": 4500.0,
        "Groceries": 3200.0,
        "Subscriptions": 649.0,
        "Transport": 1200.0
    }
    chart = generate_spend_chart("2026-07", sample_totals)
    report = generate_markdown_report("2026-07", 9549.0, sample_totals, [], [], chart)
    print("\n" + report)