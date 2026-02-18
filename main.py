import logging
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, JobQueue
from engine.gemini_brain import GeminiAnalyzer

# Load env variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TRADING_SYMBOL = os.getenv("TRADING_SYMBOL", "BTC/USDT")

# ALLOWED USERS CONFIG
allowed_env = os.getenv("ALLOWED_USER_IDS", "")
ALLOWED_IDS = [int(id.strip()) for id in allowed_env.split(",") if id.strip().isdigit()]

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

async def is_authorized(update: Update) -> bool:
    user_id = update.effective_user.id
    if not ALLOWED_IDS:
        return True 
    
    if user_id not in ALLOWED_IDS:
        print(f"⚠️ Unauthorized access attempt from: {user_id} ({update.effective_user.first_name})")
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update):
        return
        
    keyboard = [
        [InlineKeyboardButton(f"📡 Tahlil: {TRADING_SYMBOL}", callback_data=f"analyze_{TRADING_SYMBOL}")],
        [InlineKeyboardButton(f"🕵️‍♂️ Chuqur Tahlil: {TRADING_SYMBOL}", callback_data=f"deep_{TRADING_SYMBOL}")],
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
    
    if not await is_authorized(update):
        await query.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    await query.answer() 
    
    data = query.data
    
    if data.startswith("analyze_"):
        symbol = data.split("_")[1]
        await execute_analyze(update, context, symbol)
        
    elif data.startswith("deep_"):
        symbol = data.split("_")[1]
        await execute_deep_dive(update, context, symbol)
        
    elif data == "monitor_toggle":
        await monitor(update, context)

async def execute_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str):
    chat_id = update.effective_chat.id
    if not brain:
        await context.bot.send_message(chat_id=chat_id, text="❌ Tizim Xatosi: Miyya faol emas.")
        return

    await context.bot.send_message(chat_id=chat_id, text=f"🔍 {symbol} uchun Institutsional Oqimlar Tekshirilmoqda...", parse_mode='HTML')
    
    try:
        # Await the async analysis
        report = await brain.analyze_symbol(symbol)
        await context.bot.send_message(chat_id=chat_id, text=report, parse_mode='HTML') 
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Xatolik: {e}")

async def execute_deep_dive(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str):
    chat_id = update.effective_chat.id
    if not brain:
        await context.bot.send_message(chat_id=chat_id, text="❌ Tizim Xatosi: Miyya faol emas.")
        return

    await context.bot.send_message(chat_id=chat_id, text=f"🕵️‍♂️ <b>{symbol} bo'yicha Chuqur Tahlil Boshlandi</b>...\nDark Pool va Iceberg orderlar tekshirilmoqda...", parse_mode='HTML')
    
    try:
        report = await brain.analyze_symbol(symbol)
        await context.bot.send_message(chat_id=chat_id, text=report, parse_mode='HTML')
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Xatolik: {e}")

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    args = context.args
    symbol = args[0] if args else TRADING_SYMBOL
    await execute_analyze(update, context, symbol)

async def deep_dive_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    args = context.args
    symbol = args[0] if args else TRADING_SYMBOL
    await execute_deep_dive(update, context, symbol)

async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    
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
    symbol = TRADING_SYMBOL
    chat_id = context.job.chat_id
    
    try:
        if not brain:
             return
        
        # Tools are sync, this is fine to run quick check
        # But if we wanted to be fully async we could wrap it.
        # Since get_technical_analysis is just HTTP requests + math, 
        # it might block slightly but likely acceptable for now. 
        # Ideally we'd make get_technical_analysis async too, but let's fix criticals first.
        technicals = brain.get_technical_analysis(symbol)
        
        if "error" in technicals:
            return 
            
        ratio = technicals.get("volume_imbalance_ratio", 1.0)
        
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
