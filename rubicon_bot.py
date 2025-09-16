import os
import os as _os
import logging
from datetime import datetime
from typing import Dict, Any

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# 1) Токен берём из переменной окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Переменная окружения BOT_TOKEN не задана.")

ADMIN_FILE = "admin_id.txt"
ADMIN_ID: int | None = None

user_lang: Dict[int, str] = {}
forms: Dict[int, Dict[str, Any]] = {}

EXCEL_FILE = "requests.xlsx"  # на Render файл не постоянный; годится для /export здесь и сейчас

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("rubicon")

T = {
    "ru": {
        "welcome": "👋 <b>Rubicon Production</b>\nВыберите язык и нажмите «Заполнить заявку».",
        "choose_lang": "🌐 Выберите язык:",
        "btn_ru": "Русский 🇷🇺", "btn_uz": "Oʻzbekcha 🇺🇿", "btn_en": "English 🇬🇧",
        "lang_set": "✅ Язык переключён на русский. Нажмите «📝 Заполнить заявку».",
        "btn_form": "📝 Заполнить заявку", "btn_lang": "🌐 Сменить язык",
        "form_started": "📝 Начинаем заявку.\n<b>Шаг 1/6</b>\nВведите <b>ФИО</b> и <b>название компании</b> (одной строкой).",
        "ask_phone": "📞 <b>Шаг 2/6</b>\nВведите номер телефона (с кодом страны).",
        "ask_tg": "📨 <b>Шаг 3/6</b>\nВаш Telegram-ник (с @ или без).",
        "ask_task": "🎯 <b>Шаг 4/6</b>\nКратко опишите задачу/проект.",
        "ask_email": "✉️ <b>Шаг 5/6</b>\nВаш e-mail.",
        "ask_confirm": "🔎 <b>Шаг 6/6</b>\nПроверьте данные и нажмите «Подтвердить»:",
        "btn_confirm": "✅ Подтвердить и отправить", "btn_cancel": "✖️ Отмена",
        "sent_user": "✅ Заявка отправлена! Мы свяжемся с вами.",
        "sent_admin": "📩 Новая заявка:",
        "not_admin": "Админ не назначен. Выполните /admin с админ-аккаунта.",
        "admin_set": "✅ Вы назначены администратором и будете получать заявки.",
        "cancelled": "❌ Отменено. Для новой заявки нажмите «📝 Заполнить заявку».",
        "export_ok": "📎 Отправляю текущий Excel с заявками.",
        "export_none": "🗂 Файл ещё не создан (нет заявок).",
        "cleared": "🧹 Готово: локальный Excel удалён. Новые заявки начнут файл с чистого листа.",
        "no_rights": "Только администратор может использовать эту команду.",
    },
    "uz": {
        "welcome": "👋 <b>Rubicon Production</b>\nTilni tanlang va «Ariza yuborish» tugmasini bosing.",
        "choose_lang": "🌐 Tilni tanlang:",
        "btn_ru": "Ruscha 🇷🇺", "btn_uz": "Oʻzbekcha 🇺🇿", "btn_en": "Inglizcha 🇬🇧",
        "lang_set": "✅ Til oʻzbekchaga oʻzgartirildi. «📝 Ariza yuborish» ni bosing.",
        "btn_form": "📝 Ariza yuborish", "btn_lang": "🌐 Tilni almashtirish",
        "form_started": "📝 Ariza boshlandi.\n<b>1/6</b>\nF.I.Sh. va kompaniya nomi (bir qatorda).",
        "ask_phone": "📞 <b>2/6</b>\nTelefon raqamingiz (mamlakat kodi bilan).",
        "ask_tg": "📨 <b>3/6</b>\nTelegram nick (@ bilan yoki bo‘lmasligi mumkin).",
        "ask_task": "🎯 <b>4/6</b>\nVazifa/proyektni qisqa yozing.",
        "ask_email": "✉️ <b>5/6</b>\nE-mail.",
        "ask_confirm": "🔎 <b>6/6</b>\nTekshirib «Tasdiqlash» tugmasini bosing:",
        "btn_confirm": "✅ Tasdiqlash", "btn_cancel": "✖️ Bekor qilish",
        "sent_user": "✅ Arizangiz yuborildi! Tez orada bog‘lanamiz.",
        "sent_admin": "📩 Yangi ariza:",
        "not_admin": "Admin belgilanmagan. /admin yuboring.",
        "admin_set": "✅ Admin sifatida belgilandingiz.",
        "cancelled": "❌ Bekor qilindi.",
        "export_ok": "📎 Joriy Excel faylini yuboraman.",
        "export_none": "🗂 Fayl hali yaratilmagan (arizalar yo‘q).",
        "cleared": "🧹 Tayyor: Excel tozalandi.",
        "no_rights": "Bu buyruqni faqat admin ishlatishi mumkin.",
    },
    "en": {
        "welcome": "👋 <b>Rubicon Production</b>\nChoose language and tap “Submit request”.",
        "choose_lang": "🌐 Choose language:",
        "btn_ru": "Russian 🇷🇺", "btn_uz": "Uzbek 🇺🇿", "btn_en": "English 🇬🇧",
        "lang_set": "✅ Language set to English. Tap “📝 Submit request”.",
        "btn_form": "📝 Submit request", "btn_lang": "🌐 Change language",
        "form_started": "📝 Let’s start.\n<b>Step 1/6</b>\nFull name + company (one line).",
        "ask_phone": "📞 <b>Step 2/6</b>\nPhone number (with country code).",
        "ask_tg": "📨 <b>Step 3/6</b>\nTelegram handle (with or without @).",
        "ask_task": "🎯 <b>Step 4/6</b>\nShort description of your task/project.",
        "ask_email": "✉️ <b>Step 5/6</b>\nYour e-mail.",
        "ask_confirm": "🔎 <b>Step 6/6</b>\nCheck details and press “Confirm”:",
        "btn_confirm": "✅ Confirm & send", "btn_cancel": "✖️ Cancel",
        "sent_user": "✅ Request sent! We will contact you shortly.",
        "sent_admin": "📩 New request:",
        "not_admin": "Admin not set. Use /admin from admin account.",
        "admin_set": "✅ You are set as admin. You will receive requests.",
        "cancelled": "❌ Cancelled. Tap “📝 Submit request” to start again.",
        "export_ok": "📎 Sending current Excel file.",
        "export_none": "🗂 File not created yet (no requests).",
        "cleared": "🧹 Done: Excel removed.",
        "no_rights": "Only the admin can use this command.",
    }
}

def get_lang(uid: int) -> str:
    return user_lang.get(uid, "ru")

def main_menu(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(T[lang]["btn_form"], callback_data="form:start"),
    ], [
        InlineKeyboardButton(T[lang]["btn_lang"], callback_data="lang:open"),
    ]])

def lang_menu(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(T[lang]["btn_ru"], callback_data="set_lang:ru"),
        InlineKeyboardButton(T[lang]["btn_uz"], callback_data="set_lang:uz"),
        InlineKeyboardButton(T[lang]["btn_en"], callback_data="set_lang:en"),
    ]])

def render_card(d: Dict[str, str]) -> str:
    return (
        f"<b>ФИО+компания:</b> {d.get('fio_company','—')}\n"
        f"<b>Телефон:</b> {d.get('phone','—')}\n"
        f"<b>Telegram:</b> @{d.get('tg','—').lstrip('@')}\n"
        f"<b>Задача:</b> {d.get('task','—')}\n"
        f"<b>Email:</b> {d.get('email','—')}"
    )

def load_admin_id():
    global ADMIN_ID
    if _os.path.exists(ADMIN_FILE):
        try:
            ADMIN_ID = int(open(ADMIN_FILE, "r", encoding="utf-8").read().strip())
        except Exception:
            ADMIN_ID = None

def save_admin_id(admin_id: int):
    with open(ADMIN_FILE, "w", encoding="utf-8") as f:
        f.write(str(admin_id))

def excel_append(lang: str, data: Dict[str, str], user):
    # лёгкая локальная запись — на Render может «сбрасываться» после рестарта
    try:
        from openpyxl import Workbook, load_workbook
        from openpyxl.utils import get_column_letter
    except Exception as e:
        log.warning("openpyxl не установлен: %s", e)
        return

    headers = ["Timestamp(UTC)", "Lang", "FIO+Company", "Phone", "Telegram",
               "Task", "Email", "UserID", "Username"]

    if not _os.path.exists(EXCEL_FILE):
        wb = Workbook()
        ws = wb.active
        ws.title = "Requests"
        ws.append(headers)
        wb.save(EXCEL_FILE)

    wb = load_workbook(EXCEL_FILE)
    ws = wb.active

    row = [
        datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        lang.upper(),
        data.get("fio_company", ""),
        data.get("phone", ""),
        f"@{data.get('tg','').lstrip('@')}",
        data.get("task", ""),
        data.get("email", ""),
        getattr(user, "id", ""),
        f"@{getattr(user, 'username', '')}" if getattr(user, "username", None) else "",
    ]
    ws.append(row)
    if ws.max_row == 2:
        for col in range(1, ws.max_column + 1):
            col_letter = get_column_letter(col)
            max_len = max(len(str(cell.value)) if cell.value else 0 for cell in ws[col_letter])
            ws.column_dimensions[col_letter].width = min(max(12, max_len + 2), 60)
    wb.save(EXCEL_FILE)

# ─── Handlers ───
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_lang(uid)
    await update.message.reply_text(
        f"{T[lang]['welcome']}\n\n{T[lang]['choose_lang']}",
        parse_mode="HTML",
        reply_markup=lang_menu(lang)
    )

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ADMIN_ID
    ADMIN_ID = update.effective_user.id
    save_admin_id(ADMIN_ID)
    lang = get_lang(ADMIN_ID)
    await update.message.reply_text(T[lang]["admin_set"])

async def cmd_pingadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_ID:
        await context.bot.send_message(chat_id=ADMIN_ID, text="✅ Test to admin OK")
        await update.message.reply_text("Пробная отправка админу отправлена.")
    else:
        await update.message.reply_text(T[get_lang(update.effective_user.id)]["not_admin"])

async def cmd_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_user.id)
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(T[lang]["no_rights"]); return
    if not _os.path.exists(EXCEL_FILE):
        await update.message.reply_text(T[lang]["export_none"]); return
    await update.message.reply_text(T[lang]["export_ok"])
    try:
        with open(EXCEL_FILE, "rb") as f:
            await context.bot.send_document(chat_id=update.effective_chat.id, document=f, filename=EXCEL_FILE)
    except Exception as e:
        log.error("Export send failed: %s", e)

async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_user.id)
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(T[lang]["no_rights"]); return
    try:
        if _os.path.exists(EXCEL_FILE):
            _os.remove(EXCEL_FILE)
        await update.message.reply_text(T[lang]["cleared"])
    except Exception as e:
        log.error("Clear failed: %s", e)

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    lang = get_lang(uid)
    data = q.data or ""

    if data.startswith("set_lang:"):
        new_lang = data.split(":", 1)[1]
        if new_lang in ("ru", "uz", "en"):
            user_lang[uid] = new_lang
            lang = new_lang
        await q.edit_message_text(
            T[lang]["lang_set"], parse_mode="HTML", reply_markup=main_menu(lang)
        ); return

    if data == "lang:open":
        await q.edit_message_text(
            T[lang]["choose_lang"], parse_mode="HTML", reply_markup=lang_menu(lang)
        ); return

    if data == "form:start":
        forms[uid] = {"step": 1, "data": {}}
        await q.edit_message_text(T[lang]["form_started"], parse_mode="HTML"); return

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_lang(uid)
    txt = (update.message.text or "").strip()
    if uid not in forms: return
    st = forms[uid]["step"]; d = forms[uid]["data"]

    if st == 1:
        d["fio_company"] = txt; forms[uid]["step"] = 2
        await update.message.reply_text(T[lang]["ask_phone"], parse_mode="HTML"); return
    if st == 2:
        d["phone"] = txt; forms[uid]["step"] = 3
        await update.message.reply_text(T[lang]["ask_tg"], parse_mode="HTML"); return
    if st == 3:
        d["tg"] = txt.lstrip("@"); forms[uid]["step"] = 4
        await update.message.reply_text(T[lang]["ask_task"], parse_mode="HTML"); return
    if st == 4:
        d["task"] = txt; forms[uid]["step"] = 5
        await update.message.reply_text(T[lang]["ask_email"], parse_mode="HTML"); return
    if st == 5:
        d["email"] = txt; forms[uid]["step"] = 6
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(T[lang]["btn_confirm"], callback_data="form:confirm"),
            InlineKeyboardButton(T[lang]["btn_cancel"], callback_data="form:cancel"),
        ]])
        await update.message.reply_text(
            f"{T[lang]['ask_confirm']}\n\n{render_card(d)}",
            parse_mode="HTML", reply_markup=kb
        ); return

async def on_form_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    lang = get_lang(uid)
    d = forms.get(uid, {}).get("data", {})

    if q.data == "form:cancel":
        forms.pop(uid, None)
        await q.edit_message_text(T[lang]["cancelled"], parse_mode="HTML", reply_markup=main_menu(lang)); return

    if q.data == "form:confirm":
        if ADMIN_ID:
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID, text=f"{T[lang]['sent_admin']}\n\n{render_card(d)}", parse_mode="HTML"
                )
            except Exception as e:
                log.error("Send to admin failed: %s", e)
        else:
            await q.message.reply_text(T[lang]["not_admin"])
        try:
            excel_append(lang, d, q.from_user)
        except Exception as e:
            log.error("Excel append failed: %s", e)
        await q.edit_message_text(T[lang]["sent_user"], parse_mode="HTML", reply_markup=main_menu(lang))
        forms.pop(uid, None); return

def main():
    load_admin_id()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("pingadmin", cmd_pingadmin))
    app.add_handler(CommandHandler("export", cmd_export))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CallbackQueryHandler(on_callback, pattern="^(set_lang:(ru|uz|en)|lang:open|form:start)$"))
    app.add_handler(CallbackQueryHandler(on_form_control, pattern="^form:(confirm|cancel)$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    print(">>> Rubicon bot booting…")
    main()
