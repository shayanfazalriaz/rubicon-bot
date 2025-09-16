import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- /start команда ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("Русский 🇷🇺", callback_data="lang_ru"),
            InlineKeyboardButton("O’zbekcha 🇺🇿", callback_data="lang_uz"),
            InlineKeyboardButton("English 🇬🇧", callback_data="lang_en"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👋 Rubicon Production\nВыберите язык и заполните заявку:", reply_markup=reply_markup)

# --- обработчик кнопок ---
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("lang_"):
        await query.edit_message_text(f"✅ Язык выбран: {query.data}")

# --- fallback ---
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Напиши /start чтобы выбрать язык.")

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан. Добавь его в Environment Variables.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print(">>> Rubicon bot booting…")
    app.run_polling()

if __name__ == "__main__":
    main()
