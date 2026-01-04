#!/usr/bin/env python3

print("🚀 0. bot.py ЗАПУЩЕН")

import json
import os
import random
import time

print("🚀 1. TOKEN...")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or "8562030951:AAGwJdaYCKK-T0K9gxW5o_Xn7n7140llz2w"
print(f"🚀 2. ТОКЕН: '{TELEGRAM_TOKEN[:10]}...'")

if not TELEGRAM_TOKEN or len(TELEGRAM_TOKEN) < 30:
    raise RuntimeError(f"❌ ТОКЕН ОШИБКА: {TELEGRAM_TOKEN}")
print("🚀 3. ТОКЕН OK")

print("🚀 4. verbs.json...")
try:
    with open("verbs.json", "r", encoding="utf-8") as f:
        VERBS = json.load(f)
    print("🚀 5. verbs.json OK")
except Exception as e:
    print(f"❌ verbs.json: {e}")
    raise

print("🚀 6. Импорты Telegram...")
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from telegram.error import BadRequest, Forbidden

print("🚀 7. Готово!")

# === HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎯 Verbs Bot! /learn")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start /learn /help")

# === MAIN ===
async def main():
    print("🚀 main() started")
    # Фикс Python 3.13 + telegram-bot 20.7
    import telegram.ext
    app = telegram.ext.Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("🚀 Bot starting...")
    await app.run_polling(drop_pending_updates=True)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    print("🚀 Bot starting...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

# === TOKEN ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
print(f"🔍 ТОКЕН: '{TELEGRAM_TOKEN}'")
print(f"🔍 ДЛИНА: {len(TELEGRAM_TOKEN) if TELEGRAM_TOKEN else 0}")
print(f"🔍 ПЕРВЫЕ 10 символов: {TELEGRAM_TOKEN[:10] if TELEGRAM_TOKEN else 'ПУСТО'}")

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN ПУСТ!")
if len(TELEGRAM_TOKEN) < 30:
    raise RuntimeError(f"ТОКЕН НЕВЕРНЫЙ! Длина: {len(TELEGRAM_TOKEN)}")

# === LOAD VERBS ===
with open("verbs.json", "r", encoding="utf-8") as f:
    VERBS = json.load(f)

# === USER STATE STORAGE ===
user_state: dict[int, dict] = {}
user_stats: dict[int, dict] = {}
user_settings: dict[int, dict] = {}
user_errors: dict[int, list] = {}

# === INIT USER ===
def init_user(user_id: int):
    if user_id not in user_settings:
        user_settings[user_id] = {
            "daily_enabled": False,
            "level": 1,
        }

    if user_id not in user_stats:
        user_stats[user_id] = {
            "correct": 0,
            "wrong": 0,
            "best": 0,
            "streak": 0,
            "last_training": 0,
        }

    if user_id not in user_errors:
        user_errors[user_id] = []

    if user_id not in user_state:
        user_state[user_id] = {}

def get_user_level(user_id: int) -> int:
    return user_settings[user_id]["level"]

# === VERB SELECTION ===
def get_random_verb(level: int):
    if level == 1 and len(VERBS) > 100:
        return random.choice(VERBS[:100])
    return random.choice(VERBS)

def add_error(user_id: int, error: dict):
    """error = {"verb": verb_dict, "mode": "forms"/"translation"/"mix"}"""
    if not any(
        e["verb"]["inf"] == error["verb"]["inf"] and e["mode"] == error["mode"]
        for e in user_errors[user_id]
    ):
        user_errors[user_id].append(error)
        # === KEYBOARDS ===
def main_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    init_user(user_id)

    daily_enabled = user_settings[user_id]["daily_enabled"]
    daily_text = "🔔 Daily reminder: ON" if daily_enabled else "🔕 Daily reminder: OFF"

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📘 Verb Forms", callback_data="menu_train_forms"),
            InlineKeyboardButton("🌐 Translation", callback_data="menu_train_translation"),
        ],
        [
            InlineKeyboardButton("🎲 Mix", callback_data="menu_mix"),
            InlineKeyboardButton("⚡ Speed", callback_data="menu_speed"),
        ],
        [InlineKeyboardButton("🔁 Repeat Mistakes", callback_data="menu_repeat_errors")],
        [
            InlineKeyboardButton("📊 My Stats", callback_data="menu_stats"),
            InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"),
        ],
        [InlineKeyboardButton(daily_text, callback_data="toggle_daily_main")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="menu_help")],
    ])


def forms_controls_keyboard(prefix: str = "forms") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Next", callback_data=f"{prefix}_next")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_main_menu")],
    ])


def translation_controls_keyboard(prefix: str = "translation") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Next", callback_data=f"{prefix}_next")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_main_menu")],
    ])


def speed_controls_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏹ Stop", callback_data="speed_stop")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_main_menu")],
    ])


def settings_keyboard(user_id: int) -> InlineKeyboardMarkup:
    daily = user_settings[user_id]["daily_enabled"]
    daily_text = "🔔 Daily reminder: ON" if daily else "🔕 Daily reminder: OFF"

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("1️⃣ Easy", callback_data="level_1"),
            InlineKeyboardButton("2️⃣ Medium", callback_data="level_2"),
            InlineKeyboardButton("3️⃣ Hard", callback_data="level_3"),
        ],
        [InlineKeyboardButton(daily_text, callback_data="toggle_daily")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_main_menu")],
    ])


def mix_controls_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("▶️ Next", callback_data=f"{prefix}_next"),
            InlineKeyboardButton("⏹ Stop", callback_data="speed_stop"),
        ],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_main_menu")],
    ])


# === HELP TEXT ===
EXPLANATION = (
    "*Past Simple vs Present Perfect*\n\n"
    "*Past Simple* — действие завершено в прошлом, время указано или понятно из контекста.\n"
    "Примеры:\n"
    "- I visited London last year.\n"
    "- She finished the project yesterday.\n\n"
    "Сигнальные слова:\n"
    "yesterday, last week, in 2010, two days ago, when I was a child\n\n"
    "*Present Perfect* — действие связано с настоящим, важен результат или опыт.\n"
    "Примеры:\n"
    "- I have visited London many times.\n"
    "- She has just finished the project.\n\n"
    "Сигнальные слова:\n"
    "already, just, yet, ever, never, recently, lately, so far\n\n"
    "*Главное различие:*\n"
    "Past Simple — важно, когда произошло действие.\n"
    "Present Perfect — важно, что результат актуален сейчас.\n\n"
    "*Помни:*  \n"
    "В Past Simple используется **2‑я форма глагола** (went, saw, did).  \n"
    "В Present Perfect — **3‑я форма** (gone, seen, done).  \n\n"
    "Всё обучение в приложении построено на том, чтобы ты уверенно различал и использовал эти формы."
)


# === TRAINING MODES START ===
async def start_forms_training(user_id: int, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    init_user(user_id)
    verb = get_random_verb(get_user_level(user_id))
    user_state[user_id] = {"mode": "forms", "verb": verb}

    text = (
        "📘 *Verb Forms Training*\n\n"
        f"Infinitive: *{verb['inf']}*\n"
        f"Translation: *{verb['ru']}*\n\n"
        "Type the 2nd and 3rd verb forms.\n"
        "Example: *went gone*"
    )

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="Markdown",
        reply_markup=forms_controls_keyboard("forms"),
    )


async def start_translation_training(user_id: int, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    init_user(user_id)
    verb = get_random_verb(get_user_level(user_id))
    user_state[user_id] = {"mode": "translation", "verb": verb}

    text = (
        "🌐 *Translation Training*\n\n"
        f"Translate:\n\n*{verb['inf']}*"
    )

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="Markdown",
        reply_markup=translation_controls_keyboard("translation"),
    )


async def start_mix_training(user_id: int, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    init_user(user_id)

    prev_state = user_state.get(user_id, {})
    prev_submode = prev_state.get("submode")

    if prev_submode == "forms":
        submode = "translation"
    elif prev_submode == "translation":
        submode = "forms"
    else:
        submode = random.choice(["forms", "translation"])

    verb = get_random_verb(get_user_level(user_id))

    user_state[user_id] = {
        "mode": "mix",
        "submode": submode,
        "verb": verb,
    }

    if submode == "forms":
        text = (
            "🎲 *Mix Mode — Verb Forms*\n\n"
            f"Infinitive: *{verb['inf']}*\n"
            f"Translation: *{verb['ru']}*\n\n"
            "Type the 2nd and 3rd verb forms."
        )
        kb = forms_controls_keyboard("mix")
    else:
        text = (
            "🎲 *Mix Mode — Translation*\n\n"
            f"Translate:\n\n*{verb['inf']}*"
        )
        kb = translation_controls_keyboard("mix")

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="Markdown",
        reply_markup=kb,
    )

    # === REPEAT ERRORS ===
async def start_repeat_errors(user_id: int, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    init_user(user_id)
    errors = user_errors[user_id]

    if not errors:
        await context.bot.send_message(
            chat_id=chat_id,
            text="🎉 You don’t have any saved mistakes!",
            reply_markup=main_menu_keyboard(user_id),
        )
        return

    error = errors[0]
    verb = error["verb"]
    mode = error["mode"]

    user_state[user_id] = {
        "mode": "repeat",
        "verb": verb,
        "repeat_mode": mode,
    }

    if mode == "translation":
        text = (
            "🔁 *Mistake review — Translation*\n\n"
            f"Infinitive: *{verb['inf']}*\n\n"
            "Type the translation:"
        )
        kb = translation_controls_keyboard("repeat")

    elif mode == "forms":
        text = (
            "🔁 *Mistake review — Verb Forms*\n\n"
            f"Infinitive: *{verb['inf']}*\n"
            f"Translation: *{verb['ru']}*\n\n"
            "Type the 2nd and 3rd verb forms."
        )
        kb = forms_controls_keyboard("repeat")

    else:  # mix (на будущее, если захочешь расширить)
        text = (
            "🔁 *Mistake review — Mix Mode*\n\n"
            f"Infinitive: *{verb['inf']}*\n"
            f"Translation: *{verb['ru']}*\n\n"
            "Answer the question:"
        )
        kb = mix_controls_keyboard("repeat")

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="Markdown",
        reply_markup=kb,
    )

 # === SPEED MODE START ===
async def start_speed_mode(user_id: int, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    init_user(user_id)

    verb = get_random_verb(get_user_level(user_id))
    end_time = time.time() + 60  # 60 seconds timer

    user_state[user_id] = {
        "mode": "speed",
        "verb": verb,
        "correct": 0,
        "total": 0,
        "end_time": end_time,
        "wrong_answers": [],
    }

    text = (
        "⚡ *Speed Mode — 60 seconds!*\n\n"
        f"Infinitive: *{verb['inf']}*\n"
        f"Translation: *{verb['ru']}*\n\n"
        "Type the 2nd and 3rd verb forms."
    )

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="Markdown",
        reply_markup=speed_controls_keyboard(),
    )

    # === ANSWER NORMALIZATION ===
def normalize_answer(text: str):
    return [p.strip().lower() for p in text.replace(",", " ").split() if p.strip()]


# === PROCESS TRANSLATION ANSWER ===
async def process_translation_answer(
    user_id: int,
    text: str,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    mode_override: str | None = None,
):
    init_user(user_id)
    user_stats[user_id]["last_training"] = time.time()

    state = user_state.get(user_id, {})
    if not state:
        await update.message.reply_text(
            "Choose a training mode 👇",
            reply_markup=main_menu_keyboard(user_id),
        )
        return

    mode = mode_override or state.get("mode", "translation")
    verb = state["verb"]

    expected = [
        p.strip()
        for p in verb["ru"].lower().replace(",", "/").split("/")
        if p.strip()
    ]

    user_ans = text.strip().lower()

    # More accurate comparison
    correct = any(
        user_ans == exp or user_ans in exp or exp in user_ans
        for exp in expected
    )

    s = user_stats[user_id]

    if correct:
        s["correct"] += 1
        s["streak"] += 1
        s["best"] = max(s["best"], s["streak"])
        reply = f"✅ Correct!\n\n*{verb['inf']}* — *{verb['ru']}*"
    else:
        s["wrong"] += 1
        s["streak"] = 0
        add_error(user_id, {"verb": verb, "mode": mode})
        reply = f"❌ Wrong!\n\nCorrect: *{verb['inf']}* — *{verb['ru']}*"

    # === NORMAL TRANSLATION MODE ===
    if mode == "translation":
        await update.message.reply_text(
            reply,
            parse_mode="Markdown",
            reply_markup=translation_controls_keyboard("translation"),
        )
        return

    # === MIX MODE ===
    if mode == "mix":
        await update.message.reply_text(
            reply,
            parse_mode="Markdown",
            reply_markup=translation_controls_keyboard("mix"),
        )
        return

    # === REPEAT MODE ===
    if mode == "repeat":
        # Remove error if correct
        if correct:
            user_errors[user_id] = [
                e for e in user_errors[user_id]
                if not (e["verb"]["inf"] == verb["inf"] and e["mode"] == "translation")
            ]
        else:
            # Move wrong error to end
            wrong = user_errors[user_id].pop(0)
            user_errors[user_id].append(wrong)

        # No more errors
        if not user_errors[user_id]:
            await update.message.reply_text(
                "🎉 Great job! You have no more mistakes left.",
                reply_markup=main_menu_keyboard(user_id),
                parse_mode="Markdown",
            )
            user_state[user_id] = {}
            return

        # Next error
        next_error = user_errors[user_id][0]
        next_verb = next_error["verb"]

        user_state[user_id] = {
            "mode": "repeat",
            "verb": next_verb,
            "repeat_mode": "translation",
        }

        await update.message.reply_text(
            reply + f"\n\nNext:\n*{next_verb['inf']}*",
            parse_mode="Markdown",
            reply_markup=translation_controls_keyboard("repeat"),
        )
        return


# === PROCESS FORMS ANSWER ===
async def process_forms_answer(
    user_id: int,
    text: str,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    mode_override: str | None = None,
):
    init_user(user_id)
    user_stats[user_id]["last_training"] = time.time()

    state = user_state.get(user_id, {})
    if not state:
        await update.message.reply_text(
            "Choose a training mode 👇",
            reply_markup=main_menu_keyboard(user_id),
        )
        return

    mode = mode_override or state.get("mode", "forms")
    verb = state["verb"]

    answer = normalize_answer(text)

<<<<<<< HEAD
    expected_past = [p.strip().lower() for p in verb["past"].split("/")]
    expected_part = [p.strip().lower() for p in verb["part"].split("/")]

    # ФИКС ДЛЯ MODALНЫХ ГЛАГОЛОВ (can)
    answer_str = " ".join(answer).strip()
    if verb["inf"] == "can":
        correct = any(x in answer_str for x in ["could be able", "be able to", "been able to", "be able"])
    else:
        correct = (
            len(answer) >= 2
            and answer[0] in expected_past
            and answer[1] in expected_part
        )

    s = user_stats[user_id]

    if correct:
        s["correct"] += 1
        s["streak"] += 1
        s["best"] = max(s["best"], s["streak"])
        reply = f"✅ Correct!\n\n{verb['inf']} — {verb['past']}, {verb['part']}"
    else:
        s["wrong"] += 1
        s["streak"] = 0
        add_error(user_id, {"verb": verb, "mode": mode})
        reply = (
            f"❌ Wrong.\n\nCorrect forms:\n"
            f"{verb['inf']} — {verb['past']}, {verb['part']}"
        )

    # === NORMAL FORMS MODE ===
    if mode == "forms":
        await update.message.reply_text(
            reply,
            parse_mode="Markdown",
            reply_markup=forms_controls_keyboard("forms"),
        )
        return

    # === MIX MODE ===
    if mode == "mix":
        await update.message.reply_text(
            reply,
            parse_mode="Markdown",
            reply_markup=forms_controls_keyboard("mix"),
        )
        return

    # === REPEAT MODE ===
    if mode == "repeat":
        if correct:
            user_errors[user_id] = [
                e for e in user_errors[user_id]
                if not (e["verb"]["inf"] == verb["inf"] and e["mode"] == "forms")
            ]

        if not user_errors[user_id]:
            await update.message.reply_text(
                "🎉 Great job! You have no more mistakes left.",
                reply_markup=main_menu_keyboard(user_id),
                parse_mode="Markdown",
            )
            user_state[user_id] = {}
            return

        next_error = user_errors[user_id][0]
        next_verb = next_error["verb"]

        user_state[user_id] = {
            "mode": "repeat",
            "verb": next_verb,
            "repeat_mode": "forms",
        }

        await update.message.reply_text(
            reply + f"\n\nNext:\n*{next_verb['inf']}* — {next_verb['ru']}",
            parse_mode="Markdown",
            reply_markup=forms_controls_keyboard("repeat"),
        )
        return


# === PROCESS SPEED ANSWER ===
async def process_speed_answer(
    user_id: int,
    text: str,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    init_user(user_id)
    user_stats[user_id]["last_training"] = time.time()

    state = user_state.get(user_id)
    if not state or state.get("mode") != "speed":
        await update.message.reply_text(
            "Choose a training mode 👇",
            reply_markup=main_menu_keyboard(user_id),
        )
        return

    # === TIME IS UP ===
    if time.time() >= state["end_time"]:
        wrong_list = state.get("wrong_answers", [])

        wrong_text = (
            "\n".join(
                f"• *{w['inf']}* — {w['past']}, {w['part']} ({w['ru']})"
                for w in wrong_list
            )
            if wrong_list
            else "No mistakes — great job!"
        )

        result = (
            f"⏰ *Time is up!*\n\n"
            f"Correct answers: {state['correct']}\n"
            f"Total questions: {state['total']}\n\n"
            f"❗ *Mistakes to review:*\n{wrong_text}"
        )

        user_state[user_id] = {}

        await update.message.reply_text(
            result,
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(user_id),
        )
        return

    # === NORMAL PROCESSING ===
    verb = state["verb"]
    answer = normalize_answer(text)

    # Empty input
    if not answer:
        remaining = max(0, int(state["end_time"] - time.time()))
        msg = (
            f"⚡ *Speed Mode*\n"
            f"Left: {remaining} sec\n"
            f"Correct: {state['correct']} / {state['total']}\n\n"
            f"Infinitive: *{verb['inf']}*\n"
            f"Translation: *{verb['ru']}*\n\n"
            "Type the 2nd and 3rd verb forms."
        )
        await update.message.reply_text(
            msg,
            parse_mode="Markdown",
            reply_markup=speed_controls_keyboard(),
        )
        return

    expected_past = verb["past"].lower().split("/")
    expected_part = verb["part"].lower().split("/")

    correct = (
        len(answer) >= 2
        and answer[0] in expected_past
        and answer[1] in expected_part
    )

    state["total"] += 1

    if correct:
        state["correct"] += 1
        reply = f"✅ Correct!\n\n{verb['inf']} — {verb['past']}, {verb['part']}"
    else:
        state["wrong_answers"].append({
            "inf": verb["inf"],
            "past": verb["past"],
            "part": verb["part"],
            "ru": verb["ru"],
        })
        reply = f"❌ Wrong!\n\nCorrect: {verb['inf']} — {verb['past']}, {verb['part']}"

    await update.message.reply_text(reply, parse_mode="Markdown")

    # NEW QUESTION
    new_verb = get_random_verb(get_user_level(user_id))
    state["verb"] = new_verb

    remaining = max(0, int(state["end_time"] - time.time()))

    msg = (
        f"⚡ *Speed Mode*\n"
        f"Left: {remaining} sec\n"
        f"Correct: {state['correct']} / {state['total']}\n\n"
        f"Infinitive: *{new_verb['inf']}*\n"
        f"Translation: *{new_verb['ru']}*\n\n"
        "Type the 2nd and 3rd verb forms."
    )

    await update.message.reply_text(
        msg,
        parse_mode="Markdown",
        reply_markup=speed_controls_keyboard(),
    )
    # === SAFE EDIT (защита от ошибок Telegram) ===
async def safe_edit(query, text, **kwargs):
    try:
        # Если сообщение текстовое и текст отличается — редактируем
        if query.message.text and query.message.text != text:
            await query.message.edit_text(text, **kwargs)
        else:
            # Если текст тот же — обновляем только клавиатуру
            if "reply_markup" in kwargs:
                await query.message.edit_reply_markup(kwargs["reply_markup"])
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise


# === CALLBACK HANDLER ===
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return

    data = query.data
    user_id = query.from_user.id
    chat_id = query.message.chat.id

    await query.answer()
    init_user(user_id)

    # === BACK TO MENU ===
    if data == "back_main_menu":
        user_state[user_id] = {}
        await safe_edit(
            query,
            "Choose a training mode 👇",
            reply_markup=main_menu_keyboard(user_id),
        )
        return

    # === MAIN MENU ACTIONS ===
    if data == "menu_stats":
        s = user_stats[user_id]
        text = (
            f"📊 *Your Stats:*\n\n"
            f"Correct: {s['correct']}\n"
            f"Wrong: {s['wrong']}\n"
            f"Best streak: {s['best']}\n"
            f"Errors saved: {len(user_errors[user_id])}"
        )
        await safe_edit(
            query,
            text,
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(user_id),
        )
        return

    if data == "menu_help":
        await safe_edit(
            query,
            EXPLANATION,
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(user_id),
        )
        return

    if data == "menu_settings":
        level = get_user_level(user_id)
        daily = user_settings[user_id]["daily_enabled"]
        text = (
            f"⚙️ *Settings*\n\n"
            f"Difficulty level: {level}\n"
            f"Daily reminder: {'ON' if daily else 'OFF'}\n\n"
            f"Choose an option:"
        )
        await safe_edit(
            query,
            text,
            parse_mode="Markdown",
            reply_markup=settings_keyboard(user_id),
        )
        return

    # === TOGGLE DAILY (settings) ===
    if data == "toggle_daily":
        user_settings[user_id]["daily_enabled"] = not user_settings[user_id]["daily_enabled"]

        level = get_user_level(user_id)
        daily = user_settings[user_id]["daily_enabled"]

        text = (
            f"⚙️ *Settings*\n\n"
            f"Difficulty level: {level}\n"
            f"Daily reminder: {'ON' if daily else 'OFF'}\n\n"
            f"Choose an option:"
        )

        await safe_edit(
            query,
            text,
            parse_mode="Markdown",
            reply_markup=settings_keyboard(user_id),
        )
        return

    # === TOGGLE DAILY (main menu) ===
    if data == "toggle_daily_main":
        user_settings[user_id]["daily_enabled"] = not user_settings[user_id]["daily_enabled"]

        await safe_edit(
            query,
            "Choose a training mode 👇",
            reply_markup=main_menu_keyboard(user_id),
        )
        return

    # === DIFFICULTY LEVEL ===
    if data.startswith("level_"):
        level = int(data.split("_")[1])
        user_settings[user_id]["level"] = level

        await context.bot.send_message(
            chat_id=chat_id,
            text="Choose a training mode👇",
            reply_markup=main_menu_keyboard(user_id),
        )
        return

    # === NEXT BUTTONS ===
    if data.endswith("_next"):
        mode = data.split("_")[0]

        if mode == "translation":
            await start_translation_training(user_id, context, chat_id)
        elif mode == "forms":
            await start_forms_training(user_id, context, chat_id)
        elif mode == "mix":
            await start_mix_training(user_id, context, chat_id)
        elif mode == "repeat":
            await start_repeat_errors(user_id, context, chat_id)
        return

    # === SPEED MODE STOP ===
    if data == "speed_stop":
        state = user_state.get(user_id, {})

        if state.get("mode") == "speed":
            result = (
                f"⏹ Speed Mode stopped.\n\n"
                f"Correct answers: {state.get('correct', 0)}\n"
                f"Total questions: {state.get('total', 0)}"
            )
            user_state[user_id] = {}

            await safe_edit(
                query,
                result,
                reply_markup=main_menu_keyboard(user_id),
            )
        else:
            await safe_edit(
                query,
                "Choose a training mode 👇",
                reply_markup=main_menu_keyboard(user_id),
            )
        return

    # === MENU TRAININGS ===
    if data == "menu_train_forms":
        await start_forms_training(user_id, context, chat_id)
        return

    if data == "menu_train_translation":
        await start_translation_training(user_id, context, chat_id)
        return

    if data == "menu_mix":
        await start_mix_training(user_id, context, chat_id)
        return

    if data == "menu_speed":
        await start_speed_mode(user_id, context, chat_id)
        return

    if data == "menu_repeat_errors":
        await start_repeat_errors(user_id, context, chat_id)
        return


# === COMMANDS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    init_user(user_id)

    intro_text = (
        "👋 *Welcome!*\n\n"
        "This bot helps you practise English irregular verbs.\n\n"
        "*Training modes:*\n"
        "- Forms — practise V1, V2, V3.\n"
        "- Translation — translate verbs.\n"
        "- Mix — both forms and translation.\n"
        "- Speed mode — answer as many as possible.\n"
        "- Repeat mistakes — verbs you answered incorrectly.\n\n"
        "Ready to practise? Choose a training mode! 👇"
    )

    try:
        await update.message.reply_text(
            intro_text,
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(user_id),
        )
    except Forbidden:
        print(f"User {user_id} blocked the bot")


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    init_user(user.id)

    s = user_stats[user.id]

    text = (
        f"📊 *Your Stats:*\n\n"
        f"Correct: {s['correct']}\n"
        f"Wrong: {s['wrong']}\n"
        f"Best streak: {s['best']}\n"
        f"Errors saved: {len(user_errors[user.id])}"
    )

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(user.id),
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        EXPLANATION,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(update.effective_user.id),
    )


# === DAILY REMINDER JOBS ===
async def daily_reminder_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id = job.chat_id
    init_user(user_id)

    await context.bot.send_message(
        chat_id=user_id,
        text="⏰ Daily practice time! Train irregular verbs 👌",
        reply_markup=main_menu_keyboard(user_id),
    )


async def smart_daily_check(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id = job.chat_id

    init_user(user_id)

    last = user_stats[user_id].get("last_training", 0)
    now = time.time()

    if now - last >= 86400:
        await context.bot.send_message(
            chat_id=user_id,
            text="⏰ You haven’t trained for 24 hours! Time to practice irregular verbs. 💪",
            reply_markup=main_menu_keyboard(user_id),
        )
        user_stats[user_id]["last_training"] = now


async def daily_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    init_user(user_id)

    if user_settings[user_id]["daily_enabled"]:
        await update.message.reply_text(
            "Daily reminder is already ON.",
            reply_markup=main_menu_keyboard(user_id),
        )
        return

    user_settings[user_id]["daily_enabled"] = True

    # Remove old jobs
    old_jobs = context.job_queue.get_jobs_by_name(f"smart_daily_{user_id}")
    for j in old_jobs:
        j.schedule_removal()

    # Add new job
    context.job_queue.run_repeating(
        smart_daily_check,
        interval=3600,
        first=10,
        chat_id=user_id,
        name=f"smart_daily_{user_id}",
    )

    await update.message.reply_text(
        "✅ Daily reminder is now ON.\n"
        "You will get a notification if you don’t train for 24 hours.",
        reply_markup=main_menu_keyboard(user_id),
    )


async def daily_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    init_user(user_id)

    jobs = context.job_queue.get_jobs_by_name(f"smart_daily_{user_id}")
    for j in jobs:
        j.schedule_removal()

    user_settings[user_id]["daily_enabled"] = False

    await update.message.reply_text(
        "❌ Daily reminder is now OFF.",
        reply_markup=main_menu_keyboard(user_id),
    )
    # === TEXT HANDLER ===
async def process_text_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    init_user(user_id)

    text = update.message.text.strip()
    state = user_state.get(user_id)

    # No active mode
    if not state or "mode" not in state:
        await update.message.reply_text(
            "Ready to practise? Choose a training mode 👇",
            reply_markup=main_menu_keyboard(user_id),
        )
        return

    mode = state["mode"]

    # FORMS + REPEAT(FORMS)
    if mode in ("forms", "repeat"):
        repeat_mode = state.get("repeat_mode")
        if mode == "repeat" and repeat_mode == "translation":
            await process_translation_answer(
                user_id, text, update, context, mode_override="repeat"
            )
        else:
            await process_forms_answer(
                user_id,
                text,
                update,
                context,
                mode_override="repeat" if mode == "repeat" else None,
            )
        return

    # TRANSLATION
    if mode == "translation":
        await process_translation_answer(user_id, text, update, context)
        return

    # MIX
    if mode == "mix":
        submode = state.get("submode", "forms")
        if submode == "forms":
            await process_forms_answer(user_id, text, update, context, mode_override="mix")
        else:
            await process_translation_answer(user_id, text, update, context, mode_override="mix")
        return

    # SPEED
    if mode == "speed":
        await process_speed_answer(user_id, text, update, context)
        return

    # FALLBACK
    await update.message.reply_text(
        "Ready to practise? Choose a training mode 👇",
        reply_markup=main_menu_keyboard(user_id),
    )


# === MAIN ===
# 1. ДОБАВИТЕ ЭТИ 4 функции (ДО main()):
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎯 Verbs Bot! /learn")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start /learn /help")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔘 OK!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 /learn")

# 2. ЗАМЕНИТЕ main():
async def main():
    print("🚀 main() started")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🚀 Bot starting...")
    await app.run_polling(drop_pending_updates=True)

def main():  # ← СИНХРОННАЯ ФУНКЦИЯ!
    print("🚀 main() started")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Все handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("daily_on", daily_on))
    app.add_handler(CommandHandler("daily_off", daily_off))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_text_answer))
    
    print("🚀 Bot starting...")
    app.run_polling(drop_pending_updates=True)  # ← БЕЗ await!

if __name__ == "__main__":
    main()  # ← БЕЗ asyncio.run!



async def main():
    print("🚀 main() started")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # ВСЕ handlers ОДИН РАЗ
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("daily_on", daily_on))
    app.add_handler(CommandHandler("daily_off", daily_off))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_text_answer))
    
    print("🚀 Bot starting...")
    await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
