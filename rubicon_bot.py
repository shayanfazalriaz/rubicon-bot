# rubicon_bot.py — Rubicon Production (RU/UZ/EN) + Excel + webhook для Render
# Требует: python-telegram-bot[webhooks]==20.7, openpyxl

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, User
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# ── КОНФИГ ─────────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Переменная окружения BOT_TOKEN не задана.")

# стабильные источники для администратора (persist на Render):
ADMIN_ID_ENV = os.getenv("ADMIN_ID")  # строка -> int
ADMIN_USERNAME_ENV = (os.getenv("ADMIN_USERNAME") or "").strip().lstrip("@").lower()

ADMIN_FILE = "admin_id.txt"            # вспомогательный локальный кэш (может пропадать на free)
EXCEL_FILE = "requests.xlsx"           # локальный Excel для /export (на free Render не постоянен)

# память процесса
ADMIN_ID: Optional[int] = None
user_lang: Dict[int, str] = {}
forms: Dict[int, Dict[str, Any]] = {}

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("rubicon")

# ── ТЕКСТЫ ─────────────────────────────────────────────────────────────────────
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
        "not_admin": "Админ не назначен. Напишите админу или используйте /whoami чтобы занести ADMIN_ID в Render.",
        "admin_set": "✅ Вы назначены администратором и будете получать заявки.",
        "cancelled": "❌ Отменено. Для новой заявки нажмите «📝 Заполнить заявку».",
        "export_ok": "📎 Отправляю текущий Excel с заявками.",
        "export_none": "🗂 Файл ещё не создан (нет заявок).",
        "cleared": "🧹 Готово: локальный Excel удалён.",
        "no_rights": "Только администратор может использовать эту команду.",
        "whoami": "🆔 Ваш chat_id: <code>{}</code>\nСовет: добавьте его в Render → Environment переменной <code>ADMIN_ID</code>.",
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
        "not_admin": "Admin belgilanmagan. /whoami ni yuboring va ADMIN_ID ni Render ga qo‘shing.",
        "admin_set": "✅ Admin sifatida belgilandingiz.",
        "cancelled": "❌ Bekor qilindi.",
        "export_ok": "📎 Joriy Excel faylini yuboraman.",
        "export_none": "🗂 Fayl hali yaratilmagan (arizalar yo‘q).",
        "cleared": "🧹 Tayyor: Excel tozalandi.",
        "no_rights": "Bu buyruqni faqat admin ishlatishi mumkin.",
        "whoami": "🆔 Sizning chat_id: <code>{}</code>\nMaslahat: Render → Environment ga <code>ADMIN_ID</code> sifatida qo‘shing.",
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
        "not_admin": "Admin not set. Use /whoami and set ADMIN_ID in Render.",
        "admin_set": "✅ You are set as admin.",
        "cancelled": "❌ Cancelled.",
        "export_ok": "📎 Sending current Excel file.",
        "export_none": "🗂 File not created yet (no requests).",
        "cleared": "🧹 Done: Excel removed.",
        "no_rights": "Only the admin can use this command.",
        "whoami": "🆔 Your chat_id: <code>{}</code>\nTip: add it to Render → Environment as <code>ADMIN_ID</code>.",
    }
}

# ── Хелперы ───────────────────────────────────────────────────────────────────
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

def load_admin_id_from_file() -> Optional[int]:
    if os.path.exists(ADMIN_FILE):
        try:
            return int(open(ADMIN_FILE, "r", encoding="utf-8").read().strip())
        except Exception:
            return None
    return None

def save_admin_id_to_file(admin_id: int):
    try:
        with open(ADMIN_FILE, "w", encoding="utf-8") as f:
            f.write(str(admin_id))
    except Exception as e:
        log.warning("Не удалось сохранить admin_id.txt: %s", e)

def bootstrap_admin_from_env():
    global ADMIN_ID
    # 1) Жёстко заданный chat_id
    if ADMIN_ID_ENV:
        try:
            ADMIN_ID = int(ADMIN_ID_ENV)
            log.info("ADMIN_ID задан из ENV: %s", ADMIN_ID)
            return
        except ValueError:
            log.warning("ADMIN_ID в ENV не число: %r", ADMIN_ID_ENV)
    # 2) Попытка прочитать кэш-файл (если Render не перезапускал контейнер)
    file_id = load_admin_id_from_file()
    if file_id:
        ADMIN_ID = file_id
        log.info("ADMIN_ID восстановлен из файла: %s", ADMIN_ID)

def maybe_auto_claim_admin(user: User):
    """Если ADMIN_ID ещё не установлен, а username совпал с ADMIN_USERNAME_ENV— назначаем."""
    global ADMIN_ID
    if ADMIN_ID is None and ADMIN_USERNAME_ENV:
        uname = (user.username or "").lower()
        if uname == ADMIN_USERNAME_ENV:
            ADMIN_ID = user.id
            save_admin_id_to_file(ADMIN_ID)
            log.info("ADMIN_ID автоматически назначен по username=%s: %s", uname, ADMIN_ID)
            return True
    return False

# ── Excel ─────────────────────────────────────────────────────────────────────
def excel_append(lang: str, data: Dict[str, str], user: User):
    try:
        from openpyxl import Workbook, load_workbook
        from openpyxl.utils import get_column_letter
    except Exception as e:
        log.warning("openpyxl недоступен: %s", e)
        return

    headers = ["Timestamp(UTC)", "Lang", "FIO+Company", "Phone", "Telegram",
               "Task", "Email", "UserID", "Username"]

    if not os.path.exists(EXCEL_FILE):
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
        user.id,
        f"@{user.username}" if user.username else "",
    ]
    ws.append(row)

    if ws.max_row == 2:
        for col in range(1, ws.max_column + 1):
            from openpyxl.utils import get_column_letter
            col_letter = get_column_letter(col)
            max_len = max(len(str(cell.value)) if cell.value else 0 for cell in ws[col_letter])
            ws.column_dimensions[col_letter].width = min(max(12, max_len + 2), 60)

    wb.save(EXCEL_FILE)

# ── Обработчики ───────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    maybe_auto_claim_admin(user)
    lang = get_lang(user.id)
    await update.message.reply_text(
        f"{T[lang]['welcome']}\n\n{T[lang]['choose_lang']}",
        parse_mode="HTML",
        reply_markup=lang_menu(lang)
    )

# ЗАПРЕЩАЕМ /admin всем, кроме действующего админа.
# Если админ ещё не зафиксирован (ADMIN_ID = None), разрешаем только:
#  - пользователю с username == ADMIN_USERNAME (если задан)
#  - ИЛИ по секретному ключу ADMIN_KEY через: /admin <ключ>  (опционально)
async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ADMIN_ID
    user = update.effective_user
    lang = get_lang(user.id)

    ADMIN_KEY = os.getenv("ADMIN_KEY", "").strip()

    def is_username_allowed(u: User) -> bool:
        return bool(ADMIN_USERNAME_ENV) and (u.username or "").lower() == ADMIN_USERNAME_ENV

    def key_matches() -> bool:
        return bool(ADMIN_KEY) and len(context.args) >= 1 and context.args[0] == ADMIN_KEY

    allowed = False

    if ADMIN_ID is not None:
        # Админ уже назначен — только он может выполнять /admin
        allowed = (user.id == ADMIN_ID)
    else:
        # Админ ещё не назначен — разрешаем только «хозяину» по нику или по ключу
        allowed = is_username_allowed(user) or key_matches()

    if not allowed:
        await update.message.reply_text(T[lang]["no_rights"])
        return

    # Назначаем/переназначаем админа (разрешено только действующему)
    ADMIN_ID = user.id
    save_admin_id_to_file(ADMIN_ID)
    await update.message.reply_text(T[lang]["admin_set"])


async def cmd_whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_lang(uid)
    await update.message.reply_text(T[lang]["whoami"].format(uid), parse_mode="HTML")

async def cmd_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    maybe_auto_claim_admin(user)
    lang = get_lang(user.id)
    if user.id != ADMIN_ID:
        await update.message.reply_text(T[lang]["no_rights"]); return
    if not os.path.exists(EXCEL_FILE):
        await update.message.reply_text(T[lang]["export_none"]); return
    await update.message.reply_text(T[lang]["export_ok"])
    try:
        with open(EXCEL_FILE, "rb") as f:
            await context.bot.send_document(chat_id=update.effective_chat.id, document=f, filename=EXCEL_FILE)
    except Exception as e:
        log.error("Export send failed: %s", e)

async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    maybe_auto_claim_admin(user)
    lang = get_lang(user.id)
    if user.id != ADMIN_ID:
        await update.message.reply_text(T[lang]["no_rights"]); return
    try:
        if os.path.exists(EXCEL_FILE):
            os.remove(EXCEL_FILE)
        await update.message.reply_text(T[lang]["cleared"])
    except Exception as e:
        log.error("Clear failed: %s", e)

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = q.from_user
    maybe_auto_claim_admin(user)
    uid = user.id
    lang = get_lang(uid)
    data = q.data or ""

    if data.startswith("set_lang:"):
        new_lang = data.split(":", 1)[1]
        if new_lang in ("ru", "uz", "en"):
            user_lang[uid] = new_lang
            lang = new_lang
        await q.edit_message_text(T[lang]["lang_set"], parse_mode="HTML", reply_markup=main_menu(lang)); return

    if data == "lang:open":
        await q.edit_message_text(T[lang]["choose_lang"], parse_mode="HTML", reply_markup=lang_menu(lang)); return

    if data == "form:start":
        forms[uid] = {"step": 1, "data": {}}
        await q.edit_message_text(T[lang]["form_started"], parse_mode="HTML"); return

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    maybe_auto_claim_admin(user)
    uid = user.id
    lang = get_lang(uid)
    txt = (update.message.text or "").strip()

    if uid not in forms:
        return

    st = forms[uid]["step"]
    d = forms[uid]["data"]

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
    user = q.from_user
    maybe_auto_claim_admin(user)
    uid = user.id
    lang = get_lang(uid)
    d = forms.get(uid, {}).get("data", {})

    if q.data == "form:cancel":
        forms.pop(uid, None)
        await q.edit_message_text(T[lang]["cancelled"], parse_mode="HTML", reply_markup=main_menu(lang)); return

    if q.data == "form:confirm":
        if ADMIN_ID:
            try:
                await context.bot.send_message(chat_id=ADMIN_ID, text=f"{T[lang]['sent_admin']}\n\n{render_card(d)}", parse_mode="HTML")
            except Exception as e:
                log.error("Send to admin failed: %s", e)
        else:
            await q.message.reply_text(T[lang]["not_admin"])
        try:
            excel_append(lang, d, user)
        except Exception as e:
            log.error("Excel append failed: %s", e)
        await q.edit_message_text(T[lang]["sent_user"], parse_mode="HTML", reply_markup=main_menu(lang))
        forms.pop(uid, None); return

# ── Запуск (webhook на Render, polling локально) ─────────────────────────────
def run(app):
    base_url = os.getenv("RENDER_EXTERNAL_URL")
    port = int(os.getenv("PORT", "10000"))

    if base_url:
        path = f"/webhook/{BOT_TOKEN}"
        webhook_url = f"{base_url}{path}"
        print(f">>> Using webhook on {webhook_url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=path,
            webhook_url=webhook_url,
            allowed_updates=Update.ALL_TYPES,
        )
    else:
        print(">>> Using polling (local run)")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    bootstrap_admin_from_env()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("admin", cmd_admin))     # опционально
    app.add_handler(CommandHandler("whoami", cmd_whoami))
    app.add_handler(CommandHandler("export", cmd_export))
    app.add_handler(CommandHandler("clear", cmd_clear))

    app.add_handler(CallbackQueryHandler(on_callback, pattern="^(set_lang:(ru|uz|en)|lang:open|form:start)$"))
    app.add_handler(CallbackQueryHandler(on_form_control, pattern="^form:(confirm|cancel)$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    run(app)

if __name__ == "__main__":
    print(">>> Rubicon bot booting…")
    main()

