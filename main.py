import logging
import os
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, JobQueue

# ... (Previous imports and setup remain)

# Load env variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = os.getenv("TRADING_SYMBOL", "BTC/USDT")
    keyboard = [
        [InlineKeyboardButton(f"📡 Tahlil: {symbol}", callback_data=f"analyze_{symbol}")],
        [InlineKeyboardButton(f"🕵️‍♂️ Chuqur Tahlil: {symbol}", callback_data=f"deep_{symbol}")],
        [InlineKeyboardButton("🔔 Monitor (Ogohlantirish)", callback_data="monitor_toggle")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "🚀 <b>Aether-Quant Bot Ishga Tushdi</b>\n\n"
            "Men institutsional oqimlarni ko'ra olaman.\n"
            "Harakatni tanlang:"
        ),
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # Acknowledge interaction
    
    data = query.data
    
    # Route based on callback data
    if data.startswith("analyze_"):
        symbol = data.split("_")[1]
        # Context args are not available in callback, so we manually call logic or helper
        await execute_analyze(update, context, symbol)
        
    elif data.startswith("deep_"):
        symbol = data.split("_")[1]
        await execute_deep_dive(update, context, symbol)
        
    elif data == "monitor_toggle":
        await monitor(update, context)

async def execute_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str):
    if not brain:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Tizim Xatosi: Miyya faol emas.")
        return

    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"🔍 {symbol} uchun Institutsional Oqimlar Tekshirilmoqda...", parse_mode='HTML')
    
    try:
        report = brain.analyze_symbol(symbol)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=report, parse_mode='HTML') 
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"⚠️ Xatolik: {e}")

async def execute_deep_dive(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str):
    if not brain:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Tizim Xatosi: Miyya faol emas.")
        return

    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"🕵️‍♂️ <b>{symbol} bo'yicha Chuqur Tahlil Boshlandi</b>...\nDark Pool va Iceberg orderlar tekshirilmoqda...", parse_mode='HTML')
    
    try:
        report = brain.analyze_symbol(symbol)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=report, parse_mode='HTML')
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"⚠️ Xatolik: {e}")

# Keep legacy text commands compatible by wrapping them if needed, 
# but for now we basically map them to the new functions.

# ... (Monitor function remains mostly same, just ensure context.bot.send_message is used if update.message is ambiguous in callbacks, 
# although update.effective_chat.id works for both)

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    symbol = args[0] if args else os.getenv("TRADING_SYMBOL", "BTC/USDT")
    await execute_analyze(update, context, symbol)

async def deep_dive_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    symbol = args[0] if args else os.getenv("TRADING_SYMBOL", "BTC/USDT")
    await execute_deep_dive(update, context, symbol)
    
# ... (Monitor function) ...


async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    
    if current_jobs:
        for job in current_jobs:
            job.schedule_removal()
        await update.message.reply_text("🛑 Monitor Rejimi O'chirildi.")
    else:
        context.job_queue.run_repeating(monitor_callback, interval=300, first=10, chat_id=chat_id, name=str(chat_id))
        await update.message.reply_text("✅ Monitor Rejimi Yoqildi. Har 5 daqiqada skanerlanadi...")

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
        if not brain:
             return

        technicals = brain.get_technical_analysis(symbol)
        
        if "error" in technicals:
            return # Silent fail on error
            
        ratio = technicals.get("volume_imbalance_ratio", 1.0)
        ofi = technicals.get("order_flow_imbalance", 0.0)
        
        # Signal Logic
        msg = ""
        if ratio > 3.0:
            msg = f"🚨 <b>SELL WALL DETECTED</b> on {symbol}!\nImbalance Ratio: {ratio:.2f}"
        elif ratio < 0.33:
            msg = f"🚀 <b>BUY WALL DETECTED</b> on {symbol}!\nImbalance Ratio: {ratio:.2f}"
            
        if msg:
            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='HTML')
            
    except Exception as e:
        logging.error(f"Monitor error: {e}")

if __name__ == '__main__':
    if not TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found.")
        exit(1)
        
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('analyze', analyze_command))
    application.add_handler(CommandHandler('deep_dive', deep_dive_command))
    application.add_handler(CommandHandler('monitor', monitor))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("Bot is running...")
    application.run_polling()

