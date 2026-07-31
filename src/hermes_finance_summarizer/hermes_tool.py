# src/hermes_finance_summarizer/hermes_tool.py
import os
from typing import Dict, Any
from hermes_finance_summarizer.main import process_monthly_statement

def hermes_summarize_statement(file_path: str, statement_month: str) -> Dict[str, Any]:
    """
    Hermes Agent Tool: Runs the Personal Finance Summarizer on a CSV or PDF.
    Returns the report markdown and visual chart path for Discord/Telegram delivery.
    """
    if not os.path.exists(file_path):
        return {"status": "error", "message": f"File not found: {file_path}"}
        
    try:
        report_markdown = process_monthly_statement(file_path, statement_month)
        chart_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data", "reports", f"spend_summary_{statement_month}.png"
        )
        
        return {
            "status": "success",
            "statement_month": statement_month,
            "report_text": report_markdown,
            "chart_image_path": chart_path if os.path.exists(chart_path) else None
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}