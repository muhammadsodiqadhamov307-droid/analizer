import logging
import os
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, JobQueue
from engine.gemini_brain import GeminiAnalyzer

# Load env variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Initialize Gemini Brain
try:
    brain = GeminiAnalyzer()
except Exception as e:
    logging.error(f"Failed to initialize Gemini Brain: {e}")
    brain = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "🚀 **Aether-Quant Bot Online**\n\n"
            "I see what the institutions are doing.\n\n"
            "Commands:\n"
            "/analyze <symbol> - Quick Server Decode\n"
            "/deep_dive <symbol> - Full 5550-style Institutional Report\n"
            "/monitor - Toggle Alert Mode (Background Scan)"
        ),
        parse_mode='Markdown'
    )

async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not brain:
        await update.message.reply_text("❌ System Error: Brain not active.")
        return

    args = context.args
    symbol = args[0] if args else os.getenv("TRADING_SYMBOL", "BTC/USDT")
    
    await update.message.reply_text(f"🔍 Scanning Institutional Flow for {symbol}...")
    
    try:
        # For quick analyze, maybe we just get the technicals or a short summary?
        # User requested: "/analyze: Fetches last 1 hour of data and generates a 'server decoded' report"
        # We can re-use the same brain function but maybe modify prompt slightly or just use the same.
        report = brain.analyze_symbol(symbol)
        await update.message.reply_text(report)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {e}")

async def deep_dive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not brain:
        await update.message.reply_text("❌ System Error: Brain not active.")
        return

    args = context.args
    symbol = args[0] if args else os.getenv("TRADING_SYMBOL", "BTC/USDT")
    
    await update.message.reply_text(f"🕵️‍♂️ **Initiating Deep Dive for {symbol}**...\nChecking Dark Pools & Iceberg Orders...")
    
    try:
        # Prompt explicitly for deep dive
        # We can implement a specific method in brain for this, or just append to prompt
        # For now, analyze_symbol does the job as configured with "Aether-Quant" persona
        report = brain.analyze_symbol(symbol)
        await update.message.reply_text(report)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {e}")

async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    
    if current_jobs:
        for job in current_jobs:
            job.schedule_removal()
        await update.message.reply_text("🛑 Monitor Mode Deactivated.")
    else:
        context.job_queue.run_repeating(monitor_callback, interval=300, first=10, chat_id=chat_id, name=str(chat_id))
        await update.message.reply_text("✅ Monitor Mode Activated. Scanning every 5 minutes...")

async def monitor_callback(context: ContextTypes.DEFAULT_TYPE):
    symbol = os.getenv("TRADING_SYMBOL", "BTC/USDT")
    chat_id = context.job.chat_id
    
    # In a real monitor, we might only send message if a signal is found.
    # For "Aether-Quant", we check imbalance.
    try:
        # We need a way to check *without* generating full text if we want to be quiet 
        # unless there is a signal.
        # But for now, let's just generate a short check.
        # Or better: use the tools directly to check imbalance?
        # Accessing brain's tools directly:
        technicals = brain.get_technical_analysis(symbol)
        
        if "error" in technicals:
            return # Silent fail on error
            
        ratio = technicals.get("volume_imbalance_ratio", 1.0)
        ofi = technicals.get("order_flow_imbalance", 0.0)
        
        # Signal Logic
        msg = ""
        if ratio > 3.0:
            msg = f"🚨 **SELL WALL DETECTED** on {symbol}!\nImbalance Ratio: {ratio:.2f}"
        elif ratio < 0.33:
            msg = f"🚀 **BUY WALL DETECTED** on {symbol}!\nImbalance Ratio: {ratio:.2f}"
            
        if msg:
            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
            
    except Exception as e:
        logging.error(f"Monitor error: {e}")

if __name__ == '__main__':
    if not TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found.")
        exit(1)
        
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('analyze', analyze))
    application.add_handler(CommandHandler('deep_dive', deep_dive))
    application.add_handler(CommandHandler('monitor', monitor))
    
    print("Bot is running...")
    application.run_polling()

