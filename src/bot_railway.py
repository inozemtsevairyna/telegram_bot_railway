# ============================
#  AIOGRAM VERSION OF YOUR BOT
#  PART 1/5 — CORE SETUP
# ============================

import json
import os
import random
import time
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import F
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

print("🚀 Aiogram bot starting...")

# === ШАГ 1: Render hostname для вебхуков ===
HOST = os.getenv("RENDER_EXTERNAL_HOSTNAME")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://{HOST}{WEBHOOK_PATH}"

if HOST is None:
    print("⚠️ Render hostname not available yet — webhook will be set on next restart")

# === TOKEN ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("❌ TELEGRAM_TOKEN is not set")

TELEGRAM_TOKEN = TELEGRAM_TOKEN.strip()
if len(TELEGRAM_TOKEN) < 30:
    raise RuntimeError("❌ TELEGRAM_TOKEN looks too short")

from aiogram.client.default import DefaultBotProperties

bot = Bot(
    token=TELEGRAM_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.MARKDOWN
    )
)

dp = Dispatcher()

# === LOAD VERBS ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VERBS_PATH = os.path.join(BASE_DIR, "verbs.json")

try:
    with open(VERBS_PATH, "r", encoding="utf-8") as f:
        VERBS = json.load(f)
except FileNotFoundError:
    raise RuntimeError(f"❌ verbs.json not found at {VERBS_PATH}")

# === USER STORAGE ===
user_state = {}
user_stats = {}
user_settings = {}
user_errors = {}

def init_user(user_id: int):
    if user_id not in user_settings:
        user_settings[user_id] = {"daily_enabled": False, "level": 1}

    if user_id not in user_stats:
        user_stats[user_id] = {
            "correct": 0, "wrong": 0, "best": 0,
            "streak": 0, "last_training": 0
        }

    if user_id not in user_errors:
        user_errors[user_id] = []

    if user_id not in user_state:
        user_state[user_id] = {}

def get_user_level(user_id: int) -> int:
    return user_settings[user_id]["level"]

def get_random_verb(level: int):
    if level == 1 and len(VERBS) > 100:
        return random.choice(VERBS[:100])
    return random.choice(VERBS)

def add_error(user_id: int, error: dict):
    if not any(
        e["verb"]["inf"] == error["verb"]["inf"] and e["mode"] == error["mode"]
        for e in user_errors[user_id]
    ):
        user_errors[user_id].append(error)

# ============================
#  LEVEL SYSTEM FOR VERBS
# ============================

LEVEL_1_INF = [
    "be","have","do","say","go","get","make","know","think","take",
    "see","come","give","find","tell","leave","feel","put","bring",
    "begin","keep","let","show","hear","write","sit","stand","lose",
    "pay","meet","run","speak","read","grow","spend","build","fall",
    "send","cut","learn","understand","draw","break","drive","buy",
    "wear","choose","eat","drink","sleep","win","hold","sell","teach",
    "forget","forgive","fly","lead","rise","shake","become","fight",
    "feed","ride","ring","sing","sink","swim","throw","tear","steal",
    "stick","strike","sweep","swing","wake","wind","withdraw",
    "withstand","arise","awake","bite","bleed","blow","breed","burst",
    "cast","catch","cling","creep"
]

LEVEL_2_INF = LEVEL_1_INF + [
    "backslide","befall","beget","behold","bend","bereave","beseech",
    "beset","bespeak","bestride","bet","betake","bid","bind","bless",
    "broadcast","browbeat","burn","bust","can","chide","cleave",
    "clothe","cost","crow","deal","dig","dive","dream","dwell","flee",
    "fling","floodlight","forbear","forbid","forecast","foresee",
    "foretell","forsake","forego","grind","hang","mishear","mislay",
    "mislead","misread","misspell","misspend","mistake","misunderstand",
    "miswrite","mow","offset","outbid","outdo","outfight","outgrow",
    "output","outrun","outsell","outshine","overcome","overdo",
    "overeat","overfly","overhang","overhear","overlay","overpay",
    "override","overrun","oversee","overshoot","oversleep","overspend",
    "overtake","overthrow","partake","plead","preset","prove","quit",
    "rebind","rebuild","recast","redo","rehear","remake","rend","repay",
    "rerun","resell","reset","retake","reteach","retell","rewind",
    "rewrite","rid","roughcast","saw","seek","sew","shave","shear",
    "shed","shine","shoe","shrink","shut","sight-read","slay","slide",
    "sling","slink","slit","smell","smite","sneak","sow","speed","spell",
    "spill","spin","spit","split","spoil","spread","spring","sting",
    "stink","stride","string","strive","sublet","swell","thrive","thrust",
    "tread","typecast","typeset","typewrite","unbend","unbind","unclothe",
    "underbid","undercut","undergo","underlie","underpay","undersell",
    "undertake","underwrite","undo","unfreeze","unhang","unhide","unhold",
    "unknit","unlearn","unmake","unreeve","unsay","unsling","unspin",
    "unstick","unstring","unweave","unwind","uphold","upset","waylay",
    "weave","wed","weep","wet","withhold","wring"
]

def filter_by_level(all_verbs, level):
    if level == 1:
        allowed = set(LEVEL_1_INF)
    elif level == 2:
        allowed = set(LEVEL_2_INF)
    else:
        return all_verbs  # LEVEL 3 = весь список

    return [v for v in all_verbs if v["inf"] in allowed]

 # ============================
#  PART 2/5 — KEYBOARDS & HELP
# ============================

# === MAIN MENU KEYBOARD ===
def main_menu_keyboard(user_id: int):
    init_user(user_id)
    daily = user_settings[user_id]["daily_enabled"]
    daily_text = "🔔 Daily reminder: ON" if daily else "🔕 Daily reminder: OFF"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📘 Verb Forms", callback_data="menu_train_forms"),
            InlineKeyboardButton(text="🌐 Translation", callback_data="menu_train_translation"),
        ],
        [
            InlineKeyboardButton(text="🎲 Mix", callback_data="menu_mix"),
            InlineKeyboardButton(text="⚡ Speed", callback_data="menu_speed"),
        ],
        [InlineKeyboardButton(text="🔁 Repeat Mistakes", callback_data="menu_repeat_errors")],
        [
            InlineKeyboardButton(text="📊 My Stats", callback_data="menu_stats"),
            InlineKeyboardButton(text="⚙️ Settings", callback_data="menu_settings"),
        ],
        [InlineKeyboardButton(text=daily_text, callback_data="toggle_daily_main")],
        [InlineKeyboardButton(text="ℹ️ Help", callback_data="menu_help")],
    ])
    return kb


# === TRAINING CONTROL KEYBOARDS ===
def forms_controls_keyboard(prefix="forms"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Next", callback_data=f"{prefix}_next")],
        [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_main_menu")],
    ])


def translation_controls_keyboard(prefix="translation"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Next", callback_data=f"{prefix}_next")],
        [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_main_menu")],
    ])


def speed_controls_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏹ Stop", callback_data="speed_stop")],
        [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_main_menu")],
    ])


def settings_keyboard(user_id: int):
    daily = user_settings[user_id]["daily_enabled"]
    daily_text = "🔔 Daily reminder: ON" if daily else "🔕 Daily reminder: OFF"

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1️⃣ Easy", callback_data="level_1"),
            InlineKeyboardButton(text="2️⃣ Medium", callback_data="level_2"),
            InlineKeyboardButton(text="3️⃣ Hard", callback_data="level_3"),
        ],
        [InlineKeyboardButton(text=daily_text, callback_data="toggle_daily")],
        [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_main_menu")],
    ])


def mix_controls_keyboard(prefix):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="▶️ Next", callback_data=f"{prefix}_next"),
            InlineKeyboardButton(text="⏹ Stop", callback_data="speed_stop"),
        ],
        [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_main_menu")],
    ])


# === HELP TEXT ===
EXPLANATION = (
    "*Past Simple vs Present Perfect*\n\n"
    "*Past Simple* — действие завершено в прошлом.\n"
    "Сигнальные слова: yesterday, last week, in 2010.\n\n"
    "*Present Perfect* — результат важен сейчас.\n"
    "Сигнальные слова: already, just, yet, ever.\n\n"
    "Главное различие:\n"
    "Past Simple — важно *когда* произошло.\n"
    "Present Perfect — важен *результат сейчас*."
)       
# ============================
#  PART 3/5 — TRAINING MODES
# ============================

# === START FORMS TRAINING ===
async def start_forms_training(user_id: int, chat_id: int):
    init_user(user_id)

    level = get_user_level(user_id)
    verbs = filter_by_level(VERBS, level)
    verb = random.choice(verbs)

    user_state[user_id] = {"mode": "forms", "verb": verb}

    text = (
        "📘 *Verb Forms Training*\n\n"
        f"Infinitive: *{verb['inf']}*\n"
        f"Translation: *{verb['ru']}*\n\n"
        "Type the 2nd and 3rd verb forms.\n"
        "Example: *went gone*"
    )

    await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=forms_controls_keyboard("forms"),
    )


# === START TRANSLATION TRAINING ===
async def start_translation_training(user_id: int, chat_id: int):
    init_user(user_id)
    verb = get_random_verb(get_user_level(user_id))
    user_state[user_id] = {"mode": "translation", "verb": verb}

    text = (
        "🌐 *Translation Training*\n\n"
        f"Translate:\n\n*{verb['inf']}*"
    )

    await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=translation_controls_keyboard("translation"),
    )


# === START MIX TRAINING ===
async def start_mix_training(user_id: int, chat_id: int):
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

    await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=kb,
    )


# === START REPEAT ERRORS ===
async def start_repeat_errors(user_id: int, chat_id: int):
    init_user(user_id)
    errors = user_errors[user_id]

    if not errors:
        await bot.send_message(
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

    else:
        text = (
            "🔁 *Mistake review — Verb Forms*\n\n"
            f"Infinitive: *{verb['inf']}*\n"
            f"Translation: *{verb['ru']}*\n\n"
            "Type the 2nd and 3rd verb forms."
        )
        kb = forms_controls_keyboard("repeat")

    await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=kb,
    )


# === START SPEED MODE ===
async def start_speed_mode(user_id: int, chat_id: int):
    init_user(user_id)

    verb = get_random_verb(get_user_level(user_id))
    end_time = time.time() + 60  # 60 seconds

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

    await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=speed_controls_keyboard(),
    )


# === NORMALIZE ANSWER ===
def normalize_answer(text: str):
    return [p.strip().lower() for p in text.replace(",", " ").split() if p.strip()]
# ============================
#  PART 4/5 — ANSWER PROCESSING
# ============================

# === PROCESS TRANSLATION ANSWER ===
async def process_translation_answer(user_id: int, text: str, message: types.Message, mode_override=None):
    init_user(user_id)
    user_stats[user_id]["last_training"] = time.time()

    state = user_state.get(user_id, {})
    if not state:
        await message.answer("Choose a training mode 👇", reply_markup=main_menu_keyboard(user_id))
        return

    mode = mode_override or state.get("mode", "translation")
    verb = state["verb"]

    expected = [
        p.strip()
        for p in verb["ru"].lower().replace(",", "/").split("/")
        if p.strip()
    ]

    user_ans = text.strip().lower()

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

# === REPEAT MODE (translation) ===
    if mode == "repeat":
        await process_answer(message, user_id, verb, correct)
        return

# NORMAL TRANSLATION MODE
    if mode == "translation":
        await message.answer(reply, reply_markup=translation_controls_keyboard("translation"))
        return

# MIX MODE
    if mode == "mix":
        await message.answer(reply, reply_markup=translation_controls_keyboard("mix"))
        return


# === REPEAT MODE ===

async def process_answer(message: types.Message, user_id: int, verb: dict, correct: bool):
    mode = user_state[user_id].get("mode")

    if mode == "repeat":

        if correct:
            user_errors[user_id].pop(0)
        else:
            wrong = user_errors[user_id].pop(0)
            user_errors[user_id].append(wrong)

        if not user_errors[user_id]:
            await message.answer(
                "🎉 Great job! You have no more mistakes left.",
                reply_markup=main_menu_keyboard(user_id),
            )
            user_state[user_id] = {}
            return

        next_error = user_errors[user_id][0]
        next_verb = next_error["verb"]

        user_state[user_id] = {
            "mode": "repeat",
            "verb": next_verb,
            "repeat_mode": "translation",
        }

        await message.answer(
            f"Next:\n*{next_verb['inf']}*",
            reply_markup=translation_controls_keyboard("repeat"),
        )
        return


# === PROCESS FORMS ANSWER ===
async def process_forms_answer(user_id: int, text: str, message: types.Message, mode_override=None):
    init_user(user_id)
    user_stats[user_id]["last_training"] = time.time()

    state = user_state.get(user_id, {})
    if not state:
        await message.answer("Choose a training mode 👇", reply_markup=main_menu_keyboard(user_id))
        return

    mode = mode_override or state.get("mode", "forms")
    verb = state["verb"]

    answer = normalize_answer(text)

    expected_past = [p.strip().lower() for p in verb["past"].split("/")]
    expected_part = [p.strip().lower() for p in verb["part"].split("/")]

    # Special case for "can"
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

    # === REPEAT MODE (forms) ===
    if mode == "repeat":
        await process_answer(message, user_id, verb, correct)
        return

    # NORMAL FORMS MODE
    if mode == "forms":
        await message.answer(reply, reply_markup=forms_controls_keyboard("forms"))
        return

    # MIX MODE
    if mode == "mix":
        await message.answer(reply, reply_markup=forms_controls_keyboard("mix"))
        return

    # REPEAT MODE
    if mode == "repeat":
        if correct:
            user_errors[user_id] = [
                e for e in user_errors[user_id]
                if not (e["verb"]["inf"] == verb["inf"] and e["mode"] == "forms")
            ]

        if not user_errors[user_id]:
            await message.answer(
                "🎉 Great job! You have no more mistakes left.",
                reply_markup=main_menu_keyboard(user_id),
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

        await message.answer(
            reply + f"\n\nNext:\n*{next_verb['inf']}* — {next_verb['ru']}",
            reply_markup=forms_controls_keyboard("repeat"),
        )
        return


# === PROCESS SPEED ANSWER ===
async def process_speed_answer(user_id: int, text: str, message: types.Message):
    init_user(user_id)
    user_stats[user_id]["last_training"] = time.time()

    state = user_state.get(user_id)
    if not state or state.get("mode") != "speed":
        await message.answer("Choose a training mode 👇", reply_markup=main_menu_keyboard(user_id))
        return

    # TIME IS UP
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

        await message.answer(result, reply_markup=main_menu_keyboard(user_id))
        return

    # NORMAL PROCESSING
    verb = state["verb"]
    answer = normalize_answer(text)

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
        await message.answer(msg, reply_markup=speed_controls_keyboard())
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

    await message.answer(reply)

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

    await message.answer(msg, reply_markup=speed_controls_keyboard())
    # ============================
#  PART 5/5 — CALLBACKS, COMMANDS, STARTUP
# ============================

# === CALLBACK HANDLER ===
@dp.callback_query()
async def callback_handler(query: types.CallbackQuery):
    try:
        user_id = query.from_user.id
        chat_id = query.message.chat.id if query.message else user_id
        data = query.data

        init_user(user_id)
        await query.answer()

        # BACK TO MENU
        if data == "back_main_menu":
            user_state[user_id] = {}
            await query.message.edit_text(
                "Choose a training mode 👇",
                reply_markup=main_menu_keyboard(user_id),
            )
            return

        # MAIN MENU ACTIONS
        if data == "menu_stats":
            s = user_stats[user_id]
            text = (
                f"📊 *Your Stats:*\n\n"
                f"Correct: {s['correct']}\n"
                f"Wrong: {s['wrong']}\n"
                f"Best streak: {s['best']}\n"
                f"Errors saved: {len(user_errors[user_id])}"
            )
            await query.message.edit_text(text, reply_markup=main_menu_keyboard(user_id))
            return

        if data == "menu_help":
            await query.message.edit_text(
                EXPLANATION,
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
            await query.message.edit_text(
                text,
                reply_markup=settings_keyboard(user_id),
            )
            return

        # TOGGLE DAILY (settings)
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
            await query.message.edit_text(
                text,
                reply_markup=settings_keyboard(user_id),
            )
            return

        # TOGGLE DAILY (main menu)
        if data == "toggle_daily_main":
            user_settings[user_id]["daily_enabled"] = not user_settings[user_id]["daily_enabled"]
            await query.message.edit_text(
                "Choose a training mode 👇",
                reply_markup=main_menu_keyboard(user_id),
            )
            return

        # DIFFICULTY LEVEL
        if data.startswith("level_"):
            level = int(data.split("_")[1])
            user_settings[user_id]["level"] = level

            await bot.send_message(
                chat_id=chat_id,
                text="Choose a training mode👇",
                reply_markup=main_menu_keyboard(user_id),
            )
            return

        # NEXT BUTTONS
        if data.endswith("_next"):
            mode = data.split("_")[0]

            if mode == "translation":
                await start_translation_training(user_id, chat_id)
            elif mode == "forms":
                await start_forms_training(user_id, chat_id)
            elif mode == "mix":
                await start_mix_training(user_id, chat_id)
            elif mode == "repeat":
                await start_repeat_errors(user_id, chat_id)
            return

        # SPEED MODE STOP
        if data == "speed_stop":
            state = user_state.get(user_id, {})
            if state.get("mode") == "speed":
                result = (
                    f"⏹ Speed Mode stopped.\n\n"
                    f"Correct answers: {state.get('correct', 0)}\n"
                    f"Total questions: {state.get('total', 0)}"
                )
                user_state[user_id] = {}

                await query.message.edit_text(
                    result,
                    reply_markup=main_menu_keyboard(user_id),
                )
            else:
                await query.message.edit_text(
                    "Choose a training mode 👇",
                    reply_markup=main_menu_keyboard(user_id),
                )
            return

        # MENU TRAININGS
        if data == "menu_train_forms":
            await start_forms_training(user_id, chat_id)
            return

        if data == "menu_train_translation":
            await start_translation_training(user_id, chat_id)
            return

        if data == "menu_mix":
            await start_mix_training(user_id, chat_id)
            return

        if data == "menu_speed":
            await start_speed_mode(user_id, chat_id)
            return

        if data == "menu_repeat_errors":
            await start_repeat_errors(user_id, chat_id)
            return

        # FALLBACK
        await query.message.edit_text(
            "Choose a training mode 👇",
            reply_markup=main_menu_keyboard(user_id),
        )

    except Exception as e:
        print(f"Error in callback_handler: {e}")
        try:
            await bot.send_message(
                chat_id=query.from_user.id,
                text="⚠️ Something went wrong. Please try again.",
                reply_markup=main_menu_keyboard(query.from_user.id),
            )
        except:
            pass


# === DAILY REMINDER JOBS ===
async def daily_reminder_job(user_id: int):
    await bot.send_message(
        chat_id=user_id,
        text="⏰ Daily practice time! Train irregular verbs 👌",
        reply_markup=main_menu_keyboard(user_id),
    )


async def smart_daily_check(user_id: int):
    init_user(user_id)
    last = user_stats[user_id].get("last_training", 0)
    now = time.time()

    if now - last >= 86400:
        await bot.send_message(
            chat_id=user_id,
            text="⏰ You haven’t trained for 24 hours! Time to practice irregular verbs. 💪",
            reply_markup=main_menu_keyboard(user_id),
        )
        user_stats[user_id]["last_training"] = now


# === COMMANDS ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
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

    await message.answer(intro_text, reply_markup=main_menu_keyboard(user_id))


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(EXPLANATION, reply_markup=main_menu_keyboard(message.from_user.id))


@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    user_id = message.from_user.id
    init_user(user_id)

    s = user_stats[user_id]
    text = (
        f"📊 *Your Stats:*\n\n"
        f"Correct: {s['correct']}\n"
        f"Wrong: {s['wrong']}\n"
        f"Best streak: {s['best']}\n"
        f"Errors saved: {len(user_errors[user_id])}"
    )

    await message.answer(text, reply_markup=main_menu_keyboard(user_id))


@dp.message(Command("daily_on"))
async def daily_on(message: types.Message):
    user_id = message.from_user.id
    init_user(user_id)

    user_settings[user_id]["daily_enabled"] = True
    await message.answer(
        "✅ Daily reminder is now ON.\n"
        "You will get a notification if you don’t train for 24 hours.",
        reply_markup=main_menu_keyboard(user_id),
    )


@dp.message(Command("daily_off"))
async def daily_off(message: types.Message):
    user_id = message.from_user.id
    init_user(user_id)

    user_settings[user_id]["daily_enabled"] = False
    await message.answer(
        "❌ Daily reminder is now OFF.",
        reply_markup=main_menu_keyboard(user_id),
    )


# === TEXT HANDLER ===
@dp.message(F.text)
async def process_text_answer_handler(message: types.Message):
    user_id = message.from_user.id
    init_user(user_id)

    text = message.text.strip()
    state = user_state.get(user_id)

    if not state or "mode" not in state:
        await message.answer(
            "Ready to practise? Choose a training mode 👇",
            reply_markup=main_menu_keyboard(user_id),
        )
        return

    mode = state["mode"]

    # FORMS + REPEAT(FORMS)
    if mode in ("forms", "repeat"):
        repeat_mode = state.get("repeat_mode")
        if mode == "repeat" and repeat_mode == "translation":
            await process_translation_answer(user_id, text, message, mode_override="repeat")
        else:
            await process_forms_answer(
                user_id,
                text,
                message,
                mode_override="repeat" if mode == "repeat" else None,
            )
        return

    # TRANSLATION
    if mode == "translation":
        await process_translation_answer(user_id, text, message)
        return

    # MIX
    if mode == "mix":
        submode = state.get("submode", "forms")
        if submode == "forms":
            await process_forms_answer(user_id, text, message, mode_override="mix")
        else:
            await process_translation_answer(user_id, text, message, mode_override="mix")
        return

    # SPEED
    if mode == "speed":
        await process_speed_answer(user_id, text, message)
        return

    # FALLBACK
    await message.answer(
        "Ready to practise? Choose a training mode 👇",
        reply_markup=main_menu_keyboard(user_id),
    )
# ============================
#  AIOGRAM VERSION OF YOUR BOT
#  RAILWAY EDITION — PART 1/4
# ============================

import json
import os
import random
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from aiogram.client.default import DefaultBotProperties

print("🚀 Aiogram bot starting on Railway...")

# === HOSTNAME FOR WEBHOOK (RAILWAY) ===
# Railway создаёт переменную RAILWAY_PUBLIC_DOMAIN, например:
# my-bot.up.railway.app
HOST = os.getenv("RAILWAY_PUBLIC_DOMAIN")
WEBHOOK_PATH = "/webhook"

if HOST:
    WEBHOOK_URL = f"https://{HOST}{WEBHOOK_PATH}"
else:
    WEBHOOK_URL = None
    print("⚠️ Railway domain not available yet — webhook will be set later")

# === TOKEN ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("❌ TELEGRAM_TOKEN is not set")

TELEGRAM_TOKEN = TELEGRAM_TOKEN.strip()
if len(TELEGRAM_TOKEN) < 30:
    raise RuntimeError("❌ TELEGRAM_TOKEN looks too short")

from aiogram.client.default import DefaultBotProperties

bot = Bot(
    token=TELEGRAM_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.MARKDOWN
    )
)

dp = Dispatcher()

# === LOAD VERBS ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VERBS_PATH = os.path.join(BASE_DIR, "verbs.json")

try:
    with open(VERBS_PATH, "r", encoding="utf-8") as f:
        VERBS = json.load(f)
except FileNotFoundError:
    raise RuntimeError(f"❌ verbs.json not found at {VERBS_PATH}")

# === USER STORAGE ===
user_state = {}
user_stats = {}
user_settings = {}
user_errors = {}


def init_user(user_id: int):
    if user_id not in user_settings:
        user_settings[user_id] = {"daily_enabled": False, "level": 1}

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


def get_random_verb(level: int):
    if level == 1 and len(VERBS) > 100:
        return random.choice(VERBS[:100])
    return random.choice(VERBS)


def add_error(user_id: int, error: dict):
    if not any(
        e["verb"]["inf"] == error["verb"]["inf"] and e["mode"] == error["mode"]
        for e in user_errors[user_id]
    ):
        user_errors[user_id].append(error)


# ============================
#  PART 2/4 — KEYBOARDS & TRAINING START
# ============================

# === MAIN MENU KEYBOARD ===
def main_menu_keyboard(user_id: int):
    init_user(user_id)
    daily = user_settings[user_id]["daily_enabled"]
    daily_text = "🔔 Daily reminder: ON" if daily else "🔕 Daily reminder: OFF"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📘 Verb Forms", callback_data="menu_train_forms"
                ),
                InlineKeyboardButton(
                    text="🌐 Translation", callback_data="menu_train_translation"
                ),
            ],
            [
                InlineKeyboardButton(text="🎲 Mix", callback_data="menu_mix"),
                InlineKeyboardButton(text="⚡ Speed", callback_data="menu_speed"),
            ],
            [
                InlineKeyboardButton(
                    text="🔁 Repeat Mistakes", callback_data="menu_repeat_errors"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 My Stats", callback_data="menu_stats"
                ),
                InlineKeyboardButton(
                    text="⚙️ Settings", callback_data="menu_settings"
                ),
            ],
            [InlineKeyboardButton(text=daily_text, callback_data="toggle_daily_main")],
            [InlineKeyboardButton(text="ℹ️ Help", callback_data="menu_help")],
        ]
    )
    return kb


# === TRAINING CONTROL KEYBOARDS ===
def forms_controls_keyboard(prefix="forms"):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Next", callback_data=f"{prefix}_next")],
            [
                InlineKeyboardButton(
                    text="⬅️ Back to Menu", callback_data="back_main_menu"
                )
            ],
        ]
    )


def translation_controls_keyboard(prefix="translation"):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Next", callback_data=f"{prefix}_next")],
            [
                InlineKeyboardButton(
                    text="⬅️ Back to Menu", callback_data="back_main_menu"
                )
            ],
        ]
    )


def speed_controls_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏹ Stop", callback_data="speed_stop")],
            [
                InlineKeyboardButton(
                    text="⬅️ Back to Menu", callback_data="back_main_menu"
                )
            ],
        ]
    )


def settings_keyboard(user_id: int):
    daily = user_settings[user_id]["daily_enabled"]
    daily_text = "🔔 Daily reminder: ON" if daily else "🔕 Daily reminder: OFF"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1️⃣ Easy", callback_data="level_1"),
                InlineKeyboardButton(text="2️⃣ Medium", callback_data="level_2"),
                InlineKeyboardButton(text="3️⃣ Hard", callback_data="level_3"),
            ],
            [InlineKeyboardButton(text=daily_text, callback_data="toggle_daily")],
            [
                InlineKeyboardButton(
                    text="⬅️ Back to Menu", callback_data="back_main_menu"
                )
            ],
        ]
    )


def mix_controls_keyboard(prefix):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="▶️ Next", callback_data=f"{prefix}_next"),
                InlineKeyboardButton(text="⏹ Stop", callback_data="speed_stop"),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Back to Menu", callback_data="back_main_menu"
                )
            ],
        ]
    )


# === HELP TEXT ===
EXPLANATION = (
    "*Past Simple vs Present Perfect*\n\n"
    "*Past Simple* — действие завершено в прошлом.\n"
    "Сигнальные слова: *yesterday, last week, in 2010, ago*.\n"
    "Используем, когда важно *когда* произошло действие.\n"
    "Пример: *I visited London in 2020.*\n\n"

    "*Present Perfect* — результат важен сейчас.\n"
    "Сигнальные слова: *already, just, yet, ever, never, recently*.\n"
    "Используем, когда важен *опыт, результат или связь с настоящим*.\n"
    "Пример: *I have visited London twice.*\n\n"

    "*Главное различие:*\n"
    "Past Simple — действие завершено и относится к конкретному моменту в прошлом.\n"
    "Present Perfect — действие связано с настоящим, время не указано.\n\n"

    "*Типичные ошибки:*\n"
    "• Нельзя использовать Present Perfect с указанием точного времени (*yesterday, last year*).\n"
    "• Нельзя использовать Past Simple, если важен результат сейчас.\n\n"

)


# === TRAINING START FUNCTIONS ===
async def start_forms_training(user_id: int, chat_id: int):
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

    await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=forms_controls_keyboard("forms"),
    )
 # ============================
#  PART 3/4 — ANSWER PROCESSING
# ============================

# === NORMALIZE ANSWER ===
def normalize_answer(text: str):
    return [p.strip().lower() for p in text.replace(",", " ").split() if p.strip()]


# === PROCESS TRANSLATION ANSWER ===
async def process_translation_answer(user_id: int, text: str, message: types.Message, mode_override=None):
    init_user(user_id)
    user_stats[user_id]["last_training"] = time.time()

    state = user_state.get(user_id, {})
    if not state:
        await message.answer("Choose a training mode 👇", reply_markup=main_menu_keyboard(user_id))
        return

    mode = mode_override or state.get("mode", "translation")
    verb = state["verb"]

    expected = [
        p.strip()
        for p in verb["ru"].lower().replace(",", "/").split("/")
        if p.strip()
    ]

    user_ans = text.strip().lower()

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

    # NORMAL TRANSLATION MODE
    if mode == "translation":
        await message.answer(reply, reply_markup=translation_controls_keyboard("translation"))
        return

    # MIX MODE
    if mode == "mix":
        await message.answer(reply, reply_markup=translation_controls_keyboard("mix"))
        return

    # REPEAT MODE
    if mode == "repeat":
        if correct:
            # remove this verb from errors completely
            user_errors[user_id] = [
                e for e in user_errors[user_id]
                if e["verb"]["inf"] != verb["inf"]
            ]
        else:
            wrong = user_errors[user_id].pop(0)
            user_errors[user_id].append(wrong)

        if not user_errors[user_id]:
            await message.answer(
                 "🎉 Great job! You have no more mistakes left.",
                reply_markup=main_menu_keyboard(user_id),
            )
            user_state[user_id] = {}
            return

        next_error = user_errors[user_id][0]
        next_verb = next_error["verb"]

        user_state[user_id] = {
            "mode": "repeat",
            "verb": next_verb,
            "repeat_mode": "translation",
        }

        await message.answer(
            reply + f"\n\nNext:\n*{next_verb['inf']}*",
            reply_markup=translation_controls_keyboard("repeat"),
        )
        return


# === PROCESS FORMS ANSWER ===
async def process_forms_answer(user_id: int, text: str, message: types.Message, mode_override=None):
    init_user(user_id)
    user_stats[user_id]["last_training"] = time.time()

    state = user_state.get(user_id, {})
    if not state:
        await message.answer("Choose a training mode 👇", reply_markup=main_menu_keyboard(user_id))
        return

    mode = mode_override or state.get("mode", "forms")
    verb = state["verb"]

    answer = normalize_answer(text)

    expected_past = [p.strip().lower() for p in verb["past"].split("/")]
    expected_part = [p.strip().lower() for p in verb["part"].split("/")]

    # Special case for "can"
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

    # NORMAL FORMS MODE
    if mode == "forms":
        await message.answer(reply, reply_markup=forms_controls_keyboard("forms"))
        return

    # MIX MODE
    if mode == "mix":
        await message.answer(reply, reply_markup=forms_controls_keyboard("mix"))
        return

    # REPEAT MODE
    if mode == "repeat":
        if correct:
            user_errors[user_id] = [
                e for e in user_errors[user_id]
                if not (e["verb"]["inf"] == verb["inf"] and e["mode"] == "forms")
            ]

        if not user_errors[user_id]:
            await message.answer(
                "🎉 Great job! You have no more mistakes left.",
                reply_markup=main_menu_keyboard(user_id),
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

        await message.answer(
            reply + f"\n\nNext:\n*{next_verb['inf']}* — {next_verb['ru']}",
            reply_markup=forms_controls_keyboard("repeat"),
        )
        return


# === PROCESS SPEED ANSWER ===
async def process_speed_answer(user_id: int, text: str, message: types.Message):
    init_user(user_id)
    user_stats[user_id]["last_training"] = time.time()

    state = user_state.get(user_id)
    if not state or state.get("mode") != "speed":
        await message.answer("Choose a training mode 👇", reply_markup=main_menu_keyboard(user_id))
        return

    # TIME IS UP
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

        await message.answer(result, reply_markup=main_menu_keyboard(user_id))
        return

    # NORMAL PROCESSING
    verb = state["verb"]
    answer = normalize_answer(text)

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
        await message.answer(msg, reply_markup=speed_controls_keyboard())
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

    await message.answer(reply)

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

    await message.answer(msg, reply_markup=speed_controls_keyboard())
 # ============================
#  PART 4/4 — CALLBACKS, COMMANDS, TEXT HANDLER
# ============================

# === CALLBACK HANDLER ===
@dp.callback_query()
async def callback_handler(query: types.CallbackQuery):
    try:
        user_id = query.from_user.id
        chat_id = query.message.chat.id if query.message else user_id
        data = query.data

        init_user(user_id)
        await query.answer()

        # BACK TO MENU
        if data == "back_to_main":
            user_state[user_id] = {}
            await query.message.edit_text(
                "Choose a training mode 👇",
                  reply_markup=main_menu_keyboard(user_id),
           )
            return

        # MAIN MENU ACTIONS
        if data == "menu_stats":
            s = user_stats[user_id]
            text = (
                f"📊 *Your Stats:*\n\n"
                f"Correct: {s['correct']}\n"
                f"Wrong: {s['wrong']}\n"
                f"Best streak: {s['best']}\n"
                f"Errors saved: {len(user_errors[user_id])}"
            )
            await query.message.edit_text(text, reply_markup=main_menu_keyboard(user_id))
            return

        if data == "menu_help":
            await query.message.edit_text(
                EXPLANATION,
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
            await query.message.edit_text(
                text,
                reply_markup=settings_keyboard(user_id),
            )
            return

        # TOGGLE DAILY (settings)
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
            await query.message.edit_text(
                text,
                reply_markup=settings_keyboard(user_id),
            )
            return

        # TOGGLE DAILY (main menu)
        if data == "toggle_daily_main":
            user_settings[user_id]["daily_enabled"] = not user_settings[user_id]["daily_enabled"]
            await query.message.edit_text(
                "Choose a training mode 👇",
                reply_markup=main_menu_keyboard(user_id),
            )
            return

        # DIFFICULTY LEVEL
        if data.startswith("level_"):
            level = int(data.split("_")[1])
            user_settings[user_id]["level"] = level

            await bot.send_message(
                chat_id=chat_id,
                text="Choose a training mode👇",
                reply_markup=main_menu_keyboard(user_id),
            )
            return

        # NEXT BUTTONS
        if data.endswith("_next"):
            mode = data.split("_")[0]

            if mode == "translation":
                await start_translation_training(user_id, chat_id)
            elif mode == "forms":
                await start_forms_training(user_id, chat_id)
            elif mode == "mix":
                await start_mix_training(user_id, chat_id)
            elif mode == "repeat":
                await start_repeat_errors(user_id, chat_id)
            return

        # SPEED MODE STOP
        if data == "speed_stop":
            state = user_state.get(user_id, {})
            if state.get("mode") == "speed":
                result = (
                    f"⏹ Speed Mode stopped.\n\n"
                    f"Correct answers: {state.get('correct', 0)}\n"
                    f"Total questions: {state.get('total', 0)}"
                )
                user_state[user_id] = {}

                await query.message.edit_text(
                    result,
                    reply_markup=main_menu_keyboard(user_id),
                )
            else:
                await query.message.edit_text(
                    "Choose a training mode 👇",
                    reply_markup=main_menu_keyboard(user_id),
                )
            return

        # MENU TRAININGS
        if data == "menu_train_forms":
            await start_forms_training(user_id, chat_id)
            return

        if data == "menu_train_translation":
            await start_translation_training(user_id, chat_id)
            return

        if data == "menu_mix":
            await start_mix_training(user_id, chat_id)
            return

        if data == "menu_speed":
            await start_speed_mode(user_id, chat_id)
            return

        if data == "menu_repeat_errors":
            await start_repeat_errors(user_id, chat_id)
            return

        # FALLBACK
        await query.message.edit_text(
            "Choose a training mode 👇",
            reply_markup=main_menu_keyboard(user_id),
        )

    except Exception as e:
        print(f"Error in callback_handler: {e}")
        try:
            await bot.send_message(
                chat_id=query.from_user.id,
                text="⚠️ Something went wrong. Please try again.",
                reply_markup=main_menu_keyboard(query.from_user.id),
            )
        except:
            pass


# === DAILY REMINDER JOBS ===
async def daily_reminder_job(user_id: int):
    await bot.send_message(
        chat_id=user_id,
        text="⏰ Daily practice time! Train irregular verbs 👌",
        reply_markup=main_menu_keyboard(user_id),
    )


async def smart_daily_check(user_id: int):
    init_user(user_id)
    last = user_stats[user_id].get("last_training", 0)
    now = time.time()

    if now - last >= 86400:
        await bot.send_message(
            chat_id=user_id,
            text="⏰ You haven’t trained for 24 hours! Time to practice irregular verbs. 💪",
            reply_markup=main_menu_keyboard(user_id),
        )
        user_stats[user_id]["last_training"] = now


# === COMMANDS ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
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

    await message.answer(intro_text, reply_markup=main_menu_keyboard(user_id))


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(EXPLANATION, reply_markup=main_menu_keyboard(message.from_user.id))


@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    user_id = message.from_user.id
    init_user(user_id)

    s = user_stats[user_id]
    text = (
        f"📊 *Your Stats:*\n\n"
        f"Correct: {s['correct']}\n"
        f"Wrong: {s['wrong']}\n"
        f"Best streak: {s['best']}\n"
        f"Errors saved: {len(user_errors[user_id])}"
    )

    await message.answer(text, reply_markup=main_menu_keyboard(user_id))


@dp.message(Command("daily_on"))
async def daily_on(message: types.Message):
    user_id = message.from_user.id
    init_user(user_id)

    user_settings[user_id]["daily_enabled"] = True
    await message.answer(
        "✅ Daily reminder is now ON.\n"
        "You will get a notification if you don’t train for 24 hours.",
        reply_markup=main_menu_keyboard(user_id),
    )


@dp.message(Command("daily_off"))
async def daily_off(message: types.Message):
    user_id = message.from_user.id
    init_user(user_id)

    user_settings[user_id]["daily_enabled"] = False
    await message.answer(
        "❌ Daily reminder is now OFF.",
        reply_markup=main_menu_keyboard(user_id),
    )


# === TEXT HANDLER ===
@dp.message(F.text)
async def process_text_answer_handler(message: types.Message):
    user_id = message.from_user.id
    init_user(user_id)

    text = message.text.strip()
    state = user_state.get(user_id)

    if not state or "mode" not in state:
        await message.answer(
            "Ready to practise? Choose a training mode 👇",
            reply_markup=main_menu_keyboard(user_id),
        )
        return

    mode = state["mode"]

    # FORMS + REPEAT(FORMS)
    if mode in ("forms", "repeat"):
        repeat_mode = state.get("repeat_mode")
        if mode == "repeat" and repeat_mode == "translation":
            await process_translation_answer(user_id, text, message, mode_override="repeat")
        else:
            await process_forms_answer(
                user_id,
                text,
                message,
                mode_override="repeat" if mode == "repeat" else None,
            )
        return

    # TRANSLATION
    if mode == "translation":
        await process_translation_answer(user_id, text, message)
        return

    # MIX
    if mode == "mix":
        submode = state.get("submode", "forms")
        if submode == "forms":
            await process_forms_answer(user_id, text, message, mode_override="mix")
        else:
            await process_translation_answer(user_id, text, message, mode_override="mix")
        return

    # SPEED
    if mode == "speed":
        await process_speed_answer(user_id, text, message)
        return

    # FALLBACK
    await message.answer(
        "Ready to practise? Choose a training mode 👇",
        reply_markup=main_menu_keyboard(user_id),
    )
    # ============================
#  PART 5/5 — WEBHOOK & SERVER (RAILWAY)
# ============================

from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# === AIOHTTP APP MUST BE GLOBAL FOR RAILWAY ===
app = web.Application()

# Webhook path
WEBHOOK_PATH = "/webhook"


async def on_startup():
    """Runs when the server starts."""
    print("🚀 Aiogram bot LIVE on Railway!")

    # Register webhook handler
    SimpleRequestHandler(dp, bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    # Set webhook only if Railway domain is available
    if WEBHOOK_URL:
        await bot.set_webhook(WEBHOOK_URL)
        print(f"🌐 Webhook set to: {WEBHOOK_URL}")
    else:
        print("⏳ Waiting for Railway domain to become available...")


# === HEALTH CHECK (Railway-friendly) ===
async def health(request):
    return web.Response(text="OK")


# Register health endpoints
app.router.add_get("/", health)
app.router.add_get("/health", health)


# === MAIN ENTRY POINT ===
async def main():
    await on_startup()
    return app


if __name__ == "__main__":
    web.run_app(
        main(),
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080))
    )  