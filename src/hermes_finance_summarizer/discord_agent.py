# src/hermes_finance_summarizer/discord_agent.py
import os
import json
import asyncio
import discord
from dotenv import load_dotenv
from openai import OpenAI

# 1. IMPORT ALL 6 TOOLS FROM tools.py
from hermes_finance_summarizer.tools import (
    tool_process_statement,
    tool_query_category_spend,
    tool_search_transactions,
    tool_compare_months,
    tool_get_anomalies,
    tool_get_transactions_by_category
)

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_NAME = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")

# 2. ADD JSON SCHEMAS SO OPENROUTER KNOWS WHEN TO CALL THEM
FINANCE_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "tool_query_category_spend",
            "description": "Get spending totals by category for a specific month.",
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {"type": "string", "description": "Month in YYYY-MM format, e.g. '2026-07'"},
                    "category": {"type": "string", "description": "Optional category name like 'Dining', 'Shopping'"}
                },
                "required": ["month"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_search_transactions",
            "description": "Search individual transactions by merchant name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "merchant_query": {"type": "string", "description": "Name of merchant like 'SWIGGY' or 'UBER'"},
                    "month": {"type": "string", "description": "Optional month in YYYY-MM format"}
                },
                "required": ["merchant_query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_compare_months",
            "description": "Compare spending between two different months.",
            "parameters": {
                "type": "object",
                "properties": {
                    "month_a": {"type": "string", "description": "First month YYYY-MM"},
                    "month_b": {"type": "string", "description": "Second month YYYY-MM"}
                },
                "required": ["month_a", "month_b"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_get_anomalies",
            "description": "Get detected anomalies like subscription price hikes, duplicate charges, or category spending spikes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {"type": "string", "description": "Optional month in YYYY-MM format to check anomalies for"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_get_transactions_by_category",
            "description": "Get all individual transaction line items under a specific category like 'Income', 'Housing', or 'Dining'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Category name to filter by (e.g., 'Income', 'Housing')"},
                    "month": {"type": "string", "description": "Optional month in YYYY-MM format"}
                },
                "required": ["category"]
            }
        }
    }
]

# 3. MAP JSON NAMES TO ACTUAL PYTHON FUNCTIONS
TOOL_MAP = {
    "tool_query_category_spend": tool_query_category_spend,
    "tool_search_transactions": tool_search_transactions,
    "tool_compare_months": tool_compare_months,
    "tool_get_anomalies": tool_get_anomalies,
    "tool_get_transactions_by_category": tool_get_transactions_by_category
}

class HermesFinanceBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # Required to read user text
        super().__init__(intents=intents)
        self.llm_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )

    async def on_ready(self):
        print("="*65)
        print(f" [+] 🤖 HERMES AGENT DISCORD BOT ONLINE AS: {self.user}")
        print(" [+] Ready to process statements and answer financial Q&A!")
        print("="*65)

    async def on_message(self, message: discord.Message):
        # Ignore messages sent by the bot itself
        if message.author == self.user:
            return

        # Optional: restrict to #finance-reports channel
        if message.channel.name != "finance-reports":
            return

        # -------------------------------------------------------------
        # PATH 1: USER UPLOADED A STATEMENT FILE (.CSV OR .PDF)
        # -------------------------------------------------------------
        if message.attachments:
            for attachment in message.attachments:
                if attachment.filename.lower().endswith((".csv", ".pdf")):
                    await message.add_reaction("⏳")
                    async with message.channel.typing():
                        save_dir = os.path.abspath("data/statements")
                        os.makedirs(save_dir, exist_ok=True)
                        local_path = os.path.join(save_dir, attachment.filename)
                        
                        # Download attachment from Discord
                        await attachment.save(local_path)
                        
                        # Run tool_process_statement
                        month_tag = attachment.filename.split("_")[0] if "_" in attachment.filename else "2026-07"
                        report_md = tool_process_statement(local_path, month_tag)
                        
                        # Check for generated chart
                        chart_path = os.path.join("data", "reports", f"spend_summary_{month_tag}.png")
                        
                        if len(report_md) > 1950:
                            report_md = report_md[:1950] + "\n..."
                            
                        if os.path.exists(chart_path):
                            await message.channel.send(content=report_md, file=discord.File(chart_path))
                        else:
                            await message.channel.send(content=report_md)
                            
                    await message.add_reaction("✅")
                    return

        # -------------------------------------------------------------
        # PATH 2: USER ASKED A CONVERSATIONAL FINANCIAL QUESTION
        # -------------------------------------------------------------
        if message.content.strip():
            async with message.channel.typing():
                try:
                    reply_text = await self.ask_hermes_agent(message.content)
                    await message.reply(reply_text)
                except Exception as e:
                    await message.reply(f"⚠️ **Agent Error:** `{str(e)}`")

    async def ask_hermes_agent(self, user_question: str) -> str:
        """
        Sends the user question to OpenRouter with tool schemas.
        If the model calls a tool, executes it against SQLite and sends the data back for a final answer.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are Hermes, a witty, precise personal finance AI agent. "
                    "You have access to SQLite tools to inspect the user's spending ledger. "
                    "Always query the database tools before answering factual spending questions. "
                    "Format currency in Indian Rupees (₹ or Rs.)."
                )
            },
            {"role": "user", "content": user_question}
        ]

        # Call OpenRouter with tools
        response = self.llm_client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=FINANCE_TOOLS_SCHEMA,
            tool_choice="auto",
            temperature=0.2
        )

        msg = response.choices[0].message
        
        # Check if the LLM decided to call one of our SQLite tools
        if msg.tool_calls:
            messages.append(msg) # Append assistant tool request
            
            for tool_call in msg.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)
                print(f"[*] Hermes Agent executing Tool: `{fn_name}` with args: {fn_args}")
                
                # Execute Python function against local SQLite DB
                tool_func = TOOL_MAP.get(fn_name)
                if tool_func:
                    tool_output = tool_func(**fn_args)
                else:
                    tool_output = "Error: Tool not found."
                    
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": fn_name,
                    "content": str(tool_output)
                })

            # Get final natural language synthesis from OpenRouter
            final_response = self.llm_client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.3
            )
            return final_response.choices[0].message.content.strip()
        else:
            # Model answered directly without calling a tool
            return msg.content.strip()

if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN:
        print("[-] Error: DISCORD_BOT_TOKEN is missing from your .env file!")
    else:
        bot = HermesFinanceBot()
        bot.run(DISCORD_BOT_TOKEN)