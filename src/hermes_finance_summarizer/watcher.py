# src/hermes_finance_summarizer/watcher.py
import os
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
from hermes_finance_summarizer.hermes_tool import hermes_summarize_statement

load_dotenv()

WATCH_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "statements")
)

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def notify_discord(report_text: str, chart_path: str):
    """
    Sends the narrative Markdown report and uploads the generated
    PNG chart artifact directly to your Discord channel via Webhook.
    """
    if not DISCORD_WEBHOOK_URL:
        print("[!] DISCORD_WEBHOOK_URL missing from .env! Saving report locally only.")
        return

    print("[*] Uploading summary report and spend chart to Discord...")
    
    # Discord webhooks accept 'content' for text messages
    # If report is slightly over Discord's 2000 char limit, truncate safely
    safe_text = report_text[:1950] + "\n..." if len(report_text) > 1950 else report_text
    data_payload = {"content": safe_text}
    
    try:
        # If the Matplotlib chart PNG exists, send it as an image attachment!
        if chart_path and os.path.exists(chart_path):
            with open(chart_path, "rb") as img_file:
                files = {"file": (os.path.basename(chart_path), img_file.read(), "image/png")}
                response = requests.post(
                    DISCORD_WEBHOOK_URL, 
                    data=data_payload, 
                    files=files, 
                    timeout=10
                )
        else:
            response = requests.post(DISCORD_WEBHOOK_URL, json=data_payload, timeout=10)

        # Discord returns 200 OK or 204 No Content on success
        if response.status_code in (200, 204):
            print("[+] 🚀 Report and chart successfully delivered to Discord!")
        else:
            print(f"[-] Discord error ({response.status_code}): {response.text}")
            
    except Exception as e:
        print(f"[-] Failed to deliver to Discord Webhook: {e}")

def start_watching():
    os.makedirs(WATCH_DIR, exist_ok=True)
    print("="*65)
    print(f" [*] HERMES AGENT DISCORD WATCHER ACTIVE ON:")
    print(f"     {WATCH_DIR}")
    print(" [*] Drop a .csv or .pdf statement to trigger instant Discord delivery!")
    print("="*65)
    
    seen_files = set(os.listdir(WATCH_DIR))
    
    try:
        while True:
            time.sleep(3)
            current_files = set(os.listdir(WATCH_DIR))
            new_files = current_files - seen_files
            
            for file in new_files:
                if file.lower().endswith((".csv", ".pdf")):
                    filepath = os.path.join(WATCH_DIR, file)
                    month_tag = datetime.now().strftime("%Y-%m")
                    print(f"\n[!] New statement detected: '{file}'! Running summarizer...")
                    
                    result = hermes_summarize_statement(filepath, month_tag)
                    if result.get("status") == "success":
                        notify_discord(result["report_text"], result.get("chart_image_path"))
                    else:
                        print(f"[-] Processing failed: {result.get('message')}")
                        
                    seen_files.add(file)
    except KeyboardInterrupt:
        print("\n[*] Watcher stopped.")

if __name__ == "__main__":
    start_watching()