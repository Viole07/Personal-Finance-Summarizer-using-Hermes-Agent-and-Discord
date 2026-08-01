# 📊 Hermes Personal Finance Summarizer & Discord AI Agent

An enterprise-grade, privacy-first personal finance intelligence system that processes bank statements (PDF & CSV), automatically categorizes transactions, detects anomalies, and exposes an interactive bi-directional tool-calling agent on Discord.

Powered by a **two-stage local/cloud categorization pipeline**, a **local PII privacy firewall**, and **OpenRouter function calling**, Hermes turns raw financial ledgers into actionable spending breakdowns, interactive chat insights, and visual chart reports.

---

## 🌟 Key Features

* **📄 Multi-Format Statement Ingestion:** Parses complex multi-page PDF bank statements (`pdfplumber`) and CSV exports (`pandas`) with resilient error handling for malformed rows.
* **🛡️ Local Privacy Firewall (PII Redaction):** Hard-masks 10-digit UPI phone handles (`[UPI_PHONE_MASKED]`), 16-digit card numbers (`[CARD_MASKED]`), IFSC codes (`[IFSC_MASKED]`), and bank account numbers **before** any transaction string reaches third-party LLMs.
* **⚡ Two-Stage Categorization Hierarchy:**
  1. **Stage 1 (Local O(1) Rules & Cache):** Priority-based keyword engine (`SEMANTIC_KEYWORDS` > `FALLBACK_KEYWORDS`) backed by an O(1) local SQLite cache (`merchant_cache`). Standard UPI/NEFT transfers are resolved 100% locally on-device.
  2. **Stage 2 (LLM Fallback):** Unmatched merchant strings are scrubbed of PII and batched to OpenRouter/Cohere for classification.
* **💰 Income & Expenditure Decoupling:** Strictly isolates incoming credits/salary deposits (`Income`) from outflow metrics to prevent skewed spending calculations and charts.
* **🚨 Tri-Factor Anomaly Engine:**
  * **Duplicate Charge Detector:** Flags identical charges within a rolling 24–72 hour window.
  * **Category Spending Spikes:** Uses Median Absolute Deviation (MAD) against historical baselines.
  * **Subscription Price Hikes:** Employs fuzzy **Brand-Token Matching** (e.g., matching `NETFLIX.COM SUBSCRIPTION` with `NETFLIX INDIA`) to detect price increases above $\ge 5\%$ or $\ge ₹20$.
* **🤖 Bi-Directional Discord Agent with Tool Surface:**
  * Interactive Discord bot using `discord.py` and OpenRouter tool schemas (`FINANCE_TOOLS_SCHEMA` & `TOOL_MAP`).
  * Supports direct PDF/CSV file drops into channel.
  * Answers conversational Q&A by dynamically executing local SQLite introspection tools (`tool_query_category_spend`, `tool_compare_months`, `tool_get_anomalies`, `tool_get_transactions_by_category`).
* **🧪 Automated Test Suite:** Integrated `pytest` suite validating PII regex redaction and merchant normalization rules.

---

## 🏗️ System Architecture

```text
  [ Bank Statement ] (PDF / CSV)
          │
          ▼
   [ parser.py ] ──► (Extract Raw Rows & Amounts)
          │
          ▼
 [ normalizer.py ] ──► [ mask_pii() ]  ◄── (Local Privacy Firewall)
          │
          ▼
[ categorizer.py ] ──► (Semantic Priority Rules + SQLite Cache)
          │
          ├── (100% Cache/Rule Hit) ──┐
          │                          │
          └── (Unmatched Fallback) ──┼──► [ llm_fallback.py ] ──► (OpenRouter API)
                                     │
                                     ▼
                            [ SQLite Database ] (finance.db)
                                     │
         ┌───────────────────────────┴───────────────────────────┐
         ▼                                                       ▼
 [ analyzer.py ] ──► (Anomalies)                        [ discord_agent.py ]
         │                                                       │
         ▼                                                       ▼
 [ reporter.py ] ──► (Markdown & PNG Charts)             [ OpenRouter Tool Map ] 
                                                                 │
                                                                 ▼
                                                        [ Interactive Discord ]

```

---

## 🛠️ Tech Stack

* **Language & Runtime:** Python 3.11+
* **Package Manager:** [`uv`](https://github.com/astral-sh/uv) (Astral)
* **Agent & Bot Framework:** `discord.py`, `openai` SDK (OpenRouter API)
* **Data Ingestion & Processing:** `pdfplumber`, `pandas`, `matplotlib`
* **Storage & Persistence:** SQLite3
* **Testing:** `pytest`

---

## 📁 Project Structure

hermes-finance-summarizer/
├── src/
│   └── hermes_finance_summarizer/
│       ├── __init__.py
│       ├── main.py              # CLI entry point & main processing pipeline
│       ├── discord_agent.py     # Discord bot daemon & OpenRouter tool-calling agent
│       ├── parser.py            # PDF and CSV bank statement parsing engine
│       ├── normalizer.py        # Local PII masking firewall & merchant cleanup
│       ├── categorizer.py       # Priority rules and local SQLite cache manager
│       ├── llm_fallback.py      # Scrubbed batch LLM categorization via OpenRouter
│       ├── analyzer.py          # Duplicate, spike, and subscription hike detectors
│       ├── reporter.py          # Matplotlib chart generator & Markdown renderer
│       ├── db.py                # SQLite schema init, baseline seeding, and DB resets
│       └── tools.py             # Agent function implementations for Discord Q&A
├── tests/
│   └── test_normalizer.py      # Automated pytest suite for PII firewall
├── data/                        # Local database, report PNGs, & statement storage (Gitignored)
├── pyproject.toml               # Dependency specification & build configuration
├── uv.lock                      # Deterministic dependency lockfile
├── .gitignore                   # Ignore rules for secrets, DBs, & virtualenvs
└── README.md


---

## 🚀 Getting Started

### Prerequisites

* Python **3.11+** installed.
* [uv](https://github.com/astral-sh/uv) installed (`curl -LsSf https://astral.sh/uv/install.sh | sh` or via `pip install uv`).
* An **OpenRouter API Key** ([Get one here](https://openrouter.ai/)).
* A **Discord Bot Token** ([Create a bot on Discord Developer Portal](https://discord.com/developers/applications)).

---

### Installation

1. **Clone the repository:**
```bash
git clone [https://github.com/Viole07/Personal-Finance-Summarizer-using-Hermes-Agent-and-Discord.git](https://github.com/Viole07/Personal-Finance-Summarizer-using-Hermes-Agent-and-Discord.git)
cd Personal-Finance-Summarizer-using-Hermes-Agent-and-Discord

```


2. **Sync dependencies using `uv`:**
```bash
uv sync

```


3. **Configure Environment Variables:**
Create a `.env` file in the root directory:
```env
DISCORD_BOT_TOKEN=your_discord_bot_token_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct:free

```



---

## 💻 Usage

### 1. Running the Discord Agent

Start the agent daemon:

```bash
uv run python -m hermes_finance_summarizer.discord_agent

```

Once online:

* **Upload Statements:** Drop any bank PDF or CSV statement directly into your `#finance-reports` channel. Hermes will process it, store transactions in SQLite, post a structured Markdown summary, and upload a spending bar chart PNG.
* **Conversational Q&A:** Ask questions in channel or thread:
* *"How much did I spend on Subscriptions in September 2026?"*
* *"Did any subscription prices increase this cycle?"*
* *"Show me all Income-category transactions."*
* *"Compare spending between 2026-08 and 2026-09."*



---

### 2. Running CLI Processing (Standalone Pipeline)

To run the pipeline locally on a statement file without Discord:

```bash
uv run python -m hermes_finance_summarizer.main

```

---

### 3. Running Automated Tests

Run the `pytest` suite to verify the local PII masking firewall:

```bash
uv run pytest -v

```

**Expected Test Output:**

```text
tests/test_normalizer.py::test_mask_upi_phone_number PASSED              [ 25%]
tests/test_normalizer.py::test_mask_credit_card_number PASSED            [ 50%]
tests/test_normalizer.py::test_mask_ifsc_and_account_number PASSED       [ 75%]
tests/test_normalizer.py::test_clean_merchant_name_preserves_brand_tokens PASSED [100%]

============================== 4 passed in 0.12s ==============================

```

---

## 🔒 Security & Privacy Features

Hermes is architected from the ground up to protect user privacy:

* **Zero PII Exposure:** Bank account numbers, card PANs, IFSC codes, and UPI handles containing phone numbers are scrubbed locally before cloud LLM classification.
* **Local Transaction Storage:** All financial ledgers and monthly summaries are kept in a local SQLite database (`data/finance.db`).
* **Git Safety:** Secrets (`.env`), databases (`*.db`), and generated PNG charts (`*.png`) are strictly ignored via `.gitignore`.

---

## 📜 License

This project is licensed under the [MIT License](https://www.google.com/search?q=LICENSE).
