import os
import json
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv
from hermes_finance_summarizer.db import TAXONOMY, cache_merchant

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_NAME = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")

def get_openrouter_client() -> OpenAI:
    """Initializes OpenAI client configured for OpenRouter endpoint."""
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is missing from your .env file!")
    
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

def categorize_batch_with_llm(unmatched_merchants: List[str]) -> Dict[str, str]:
    """
    Takes a list of unique unmatched merchant names, calls OpenRouter,
    and returns a mapping of {merchant: category}.
    Auto-saves learned mappings directly into SQLite cache.
    """
    if not unmatched_merchants:
        return {}
    
    # Deduplicate while preserving list structure
    unique_merchants = list(set(unmatched_merchants))
    client = get_openrouter_client()

    # ---------------------------------------------------------
    # 🛡️ PRIVACY AUDIT: PRINT THE EXACT PAYLOAD LEAVING THE MACHINE
    # ---------------------------------------------------------
    print("\n" + "🛡️ "*20)
    print(" PRIVACY AUDIT: PAYLOAD BOUND FOR LLM (OPENROUTER)")
    print("🛡️ "*20)
    print(json.dumps(unique_merchants, indent=2))
    print("🛡️ "*20 + "\n")
    # ---------------------------------------------------------

    prompt = f"""
You are an expert personal finance transaction classifier.
Categorize the following list of merchants into EXACTLY one of these allowed categories:
{json.dumps(TAXONOMY)}

Strict Guidelines:
1. Return ONLY a valid JSON object mapping each merchant to its single category.
2. Do not include markdown code blocks, explanation, or conversational text.
3. If uncertain, select "Other".

Merchants to categorize:
{json.dumps(unique_merchants, indent=2)}
"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a financial transaction classification engine that outputs raw JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1, # Low temperature for consistent classification
        )

        content = response.choices[0].message.content.strip()
        
        # Clean potential markdown wrapping if the model adds ```json ... ```
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:].strip()

        categorized_map: Dict[str, str] = json.loads(content)

        # Validate categories & persist newly learned mappings to SQLite
        results = {}
        for merchant, cat in categorized_map.items():
            final_cat = cat if cat in TAXONOMY else "Other"
            cache_merchant(merchant, final_cat, confidence=0.85)
            results[merchant] = final_cat

        return results

    except Exception as e:
        print(f"Error during LLM categorization fallback: {e}")
        # Fallback to 'Other' for unhandled failures, using the correct variable name
        return {m: "Other" for m in unique_merchants}


if __name__ == "__main__":
    from hermes_finance_summarizer.db import init_db
    init_db()
    
    print("Testing LLM Fallback Categorization...")
    test_batch = ["STEAM GAMES", "BLUE TOKAI COFFEE", "FITNESS FIRST GYM", "UPI/P2A/9876543210@ybl"]
    
    # Make sure OPENROUTER_API_KEY is in .env before testing
    if os.getenv("OPENROUTER_API_KEY"):
        classified = categorize_batch_with_llm(test_batch)
        print("\nResults:")
        for merchant, category in classified.items():
            print(f"  {merchant} -> {category}")
    else:
        print("Please add your OPENROUTER_API_KEY to .env to run this test!")