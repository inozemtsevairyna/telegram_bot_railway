print("🔥 FILE LOADED: bot_railway.py")
import os
import json
import random
import time
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ============================
#  CONFIG
# ============================

HOST = os.getenv("RAILWAY_STATIC_URL")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://{HOST}{WEBHOOK_PATH}" if HOST else None

TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN missing")

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)
dp = Dispatcher()

# ============================
#  LOAD VERBS
# ============================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VERBS_PATH = os.path.join(BASE_DIR, "verbs.json")

with open(VERBS_PATH, "r", encoding="utf-8") as f:
    verbs = json.load(f)

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

    "*Формы глагола и времена:*\n"
    "• *Past Simple* → используется *вторая форма* глагола (V2).\n"
    "• *Present Perfect* → используется *третья форма* глагола (V3, Participle).\n\n"

    "*Главное различие:*\n"
    "Past Simple — действие завершено и относится к конкретному моменту в прошлом.\n"
    "Present Perfect — действие связано с настоящим, время не указано.\n\n"

    "*Типичные ошибки:*\n"
    "• Нельзя использовать Present Perfect с указанием точного времени (*yesterday, last year*).\n"
    "• Нельзя использовать Past Simple, если важен результат сейчас.\n"
)

# ============================
#  USER STORAGE
# ============================

user_state = {}
user_stats = {}
user_settings = {}
user_errors = {}

def ensure_user_settings(uid):
    if uid not in user_settings:
        user_settings[uid] = {"daily_enabled": False, "level": 1}

def init_user(uid):
    ensure_user_settings(uid)
    user_stats.setdefault(uid, {"correct": 0, "wrong": 0, "best": 0, "streak": 0, "last_training": 0})
    user_errors.setdefault(uid, [])
    user_state.setdefault(uid, {})

def get_user_level(uid):
    return user_settings[uid]["level"]

def get_random_verb(level):
    available = [v for v in verbs if v.get("level", 1) <= level]
    verb = random.choice(available)
    print("DEBUG LEVEL REQUESTED:", level)
    print("DEBUG VERB SELECTED:", verb["inf"], "LEVEL:", verb["level"])
    return verb

def add_error(uid, error):
    if not any(e["verb"]["inf"] == error["verb"]["inf"] and e["mode"] == error["mode"] for e in user_errors[uid]):
        user_errors[uid].append(error)

# ============================
#  KEYBOARDS
# ============================

def main_menu(uid):
    daily = user_settings[uid]["daily_enabled"]
    daily_text = "🔔 Daily reminder: ON" if daily else "🔕 Daily reminder: OFF"

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📘 Verb Forms", callback_data="menu_forms"),
            InlineKeyboardButton(text="🌐 Translation", callback_data="menu_translation"),
        ],
        [
            InlineKeyboardButton(text="🎲 Mix", callback_data="menu_mix"),
            InlineKeyboardButton(text="⚡ Speed", callback_data="menu_speed"),
        ],
        [InlineKeyboardButton(text="🔁 Repeat Mistakes", callback_data="menu_repeat")],
        [
            InlineKeyboardButton(text="📊 My Stats", callback_data="menu_stats"),
            InlineKeyboardButton(text="⚙️ Settings", callback_data="menu_settings"),
        ],
        [InlineKeyboardButton(text=daily_text, callback_data="toggle_daily")],
        [InlineKeyboardButton(text="ℹ️ Help", callback_data="menu_help")],
    ])


def forms_kb(prefix="forms"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Next", callback_data=f"{prefix}_next")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="back")]
    ])


def translation_kb(prefix="translation"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Next", callback_data=f"{prefix}_next")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="back")]
    ])


def speed_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏹ Stop", callback_data="speed_stop")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="back")]
    ])


def difficulty_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1️⃣ Level 1", callback_data="difficulty_1"),
            InlineKeyboardButton(text="2️⃣ Level 2", callback_data="difficulty_2"),
            InlineKeyboardButton(text="3️⃣ Level 3", callback_data="difficulty_3"),
        ],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="menu_settings")]
    ])

# ============================
#  TRAINING START FUNCTIONS
# ============================

async def start_forms(uid, cid):
    ensure_user_settings(uid)

    verb = get_random_verb(get_user_level(uid))
    print("DEBUG FORMS:", verb["inf"], "LEVEL:", verb["level"])

    user_state[uid] = {"mode": "forms", "verb": verb}

    await bot.send_message(
        cid,
        f"📘 *Verb Forms*\n\n"
        f"Infinitive: *{verb['inf']}*\n"
        f"Translation: *{verb['ru']}*\n\n"
        f"Write the 2nd and 3rd forms of the verb.\n"
        f"Example: go → went, gone",
        reply_markup=forms_kb("forms")
    )


async def start_translation(uid, cid):
    ensure_user_settings(uid)

    verb = get_random_verb(get_user_level(uid))
    print("DEBUG TRANSLATION:", verb["inf"], "LEVEL:", verb["level"])

    user_state[uid] = {"mode": "translation", "verb": verb}

    await bot.send_message(
        cid,
        f"🌐 *Translation*\n\nTranslate:\n*{verb['inf']}*",
        reply_markup=translation_kb("translation")
    )


async def start_mix(uid, cid):
    ensure_user_settings(uid)

    sub = random.choice(["forms", "translation"])
    verb = get_random_verb(get_user_level(uid))
    print("DEBUG MIX:", verb["inf"], "LEVEL:", verb["level"], "SUB:", sub)

    user_state[uid] = {"mode": "mix", "sub": sub, "verb": verb}

    if sub == "forms":
        await bot.send_message(
            cid,
            f"🎲 *Mix — Forms*\n\n"
            f"Infinitive: *{verb['inf']}*\n"
            f"Translation: *{verb['ru']}*\n\n"
            f"Write the 2nd and 3rd forms of the verb.\n"
            f"Example: go → went, gone",
            reply_markup=forms_kb("mix")
        )
    else:
        await bot.send_message(
            cid,
            f"🎲 *Mix — Translation*\n\nTranslate:\n*{verb['inf']}*",
            reply_markup=translation_kb("mix")
        )


async def start_speed(uid, cid):
    ensure_user_settings(uid)

    verb = get_random_verb(get_user_level(uid))
    print("DEBUG SPEED:", verb["inf"], "LEVEL:", verb["level"])

    user_state[uid] = {
        "mode": "speed",
        "verb": verb,
        "correct": 0,
        "total": 0,
        "end": time.time() + 60,
        "wrong": []
    }

    await bot.send_message(
        cid,
        f"⚡ *Speed Mode — 60 sec*\n\nInfinitive: *{verb['inf']}*",
        reply_markup=speed_kb()
    )
# ============================
#  ANSWER PROCESSING
# ============================

def norm(text):
    return [p.strip().lower() for p in text.replace(",", " ").split() if p.strip()]


# ============================
#  TRANSLATION PROCESSING
# ============================

async def process_translation(uid, text, msg, mode=None):
    init_user(uid)
    st = user_state.get(uid, {})

    if "verb" not in st:
        await msg.answer("Session expired. Choose a mode 👇", reply_markup=main_menu(uid))
        return

    verb = st["verb"]
    expected = [p.strip() for p in verb["ru"].lower().replace(",", "/").split("/")]

    ok = any(text.lower() == e or text.lower() in e for e in expected)

    if ok:
        user_stats[uid]["correct"] += 1
        reply = f"✅ Correct!\n\n*{verb['inf']}* — *{verb['ru']}*"
    else:
        user_stats[uid]["wrong"] += 1
        add_error(uid, {"verb": verb, "mode": "translation"})
        reply = f"❌ Wrong!\n\nCorrect: *{verb['inf']}* — *{verb['ru']}*"

    # send reply
    if st["mode"] == "mix":
        await msg.answer(reply, reply_markup=translation_kb("mix"))
    else:
        await msg.answer(reply, reply_markup=translation_kb("translation"))

    # NEW VERB (LEVEL-BASED)
    st["verb"] = get_random_verb(get_user_level(uid))



# ============================
#  FORMS PROCESSING
# ============================

def normalize_forms(value):
    # Convert correct forms into a list of lowercase strings
    if isinstance(value, list):
        return [v.lower().strip() for v in value]
    if isinstance(value, str):
        # Split variants like "burned/burnt"
        return [v.lower().strip() for v in value.split("/")]
    return []


async def process_forms(uid, text, msg, mode=None):
    ensure_user_settings(uid)
    st = user_state.get(uid, {})

    if "verb" not in st:
        await msg.answer("Session expired. Choose a mode 👇", reply_markup=main_menu(uid))
        return

    verb = st["verb"]
    ans = norm(text)  # user input split into words

    # Normalize correct forms
    past_forms = normalize_forms(verb["past"])
    part_forms = normalize_forms(verb["part"])

    # Normalize user input
    # Example: "was were been" → ["was", "were", "been"]
    user_past = []
    user_part = ""

    if len(ans) >= 2:
        # First part = past forms
        user_past = [x.strip().lower() for x in ans[0].replace(",", " ").split()]
        # Second part = participle
        user_part = " ".join(ans[1:]).strip().lower()

    # Check correctness
    ok = (
        len(user_past) > 0
        and set(user_past) == set(past_forms)
        and user_part in part_forms
    )

    if ok:
        user_stats[uid]["correct"] += 1
        reply = f"✅ Correct!\n\n{verb['inf']} — {verb['past']}, {verb['part']}"
    else:
        user_stats[uid]["wrong"] += 1
        add_error(uid, {"verb": verb, "mode": "forms"})
        reply = f"❌ Wrong!\n\nCorrect: {verb['inf']} — {verb['past']}, {verb['part']}"

    # Send reply
    if st["mode"] == "mix":
        await msg.answer(reply, reply_markup=forms_kb("mix"))
    else:
        await msg.answer(reply, reply_markup=forms_kb("forms"))

    # New verb (level-based)
    st["verb"] = get_random_verb(get_user_level(uid))

# ============================
#  SPEED MODE
# ============================

async def process_speed(uid, text, msg):
    init_user(uid)
    st = user_state.get(uid)

    if not st or st.get("mode") != "speed":
        await msg.answer("Choose a mode 👇", reply_markup=main_menu(uid))
        return

    # TIME IS UP
    if time.time() >= st["end"]:
        wrong_list = st.get("wrong", [])

        wrong_text = (
            "\n".join(
                f"• *{w['inf']}* — {w['past']}, {w['part']} ({w['ru']})"
                for w in wrong_list
            )
            if wrong_list else "No mistakes — great job!"
        )

        result = (
            f"⏰ *Time is up!*\n\n"
            f"Correct: {st['correct']}\n"
            f"Total: {st['total']}\n\n"
            f"❗ Mistakes:\n{wrong_text}"
        )

        user_state[uid] = {}
        await msg.answer(result, reply_markup=main_menu(uid))
        return

    # NORMAL PROCESSING
    if "verb" not in st:
        await msg.answer("Session expired. Choose a mode 👇", reply_markup=main_menu(uid))
        return

    verb = st["verb"]
    ans = norm(text)

    past_forms = normalize_forms(verb["past"])
    part_forms = normalize_forms(verb["part"])

    ok = (
        len(ans) >= 2 and
        ans[0] in past_forms and
        ans[1] in part_forms
    )

    st["total"] += 1

    if ok:
        st["correct"] += 1
        reply = f"✅ Correct!\n\n{verb['inf']} — {verb['past']}, {verb['part']}"
    else:
        st["wrong"].append({
            "inf": verb["inf"],
            "past": verb["past"],
            "part": verb["part"],
            "ru": verb["ru"],
        })
        reply = f"❌ Wrong!\n\nCorrect: {verb['inf']} — {verb['past']}, {verb['part']}"

    await msg.answer(reply)

    # NEW VERB (LEVEL-BASED)
    st["verb"] = get_random_verb(get_user_level(uid))

# ============================
#  CALLBACK HANDLER
# ============================

@dp.callback_query()
async def cb(q: types.CallbackQuery):
    await q.answer()   # подтверждаем callback сразу
    uid = q.from_user.id
    cid = q.message.chat.id
    data = q.data
    init_user(uid)

    # ============================
    # BACK
    # ============================
    if data == "back":
        user_state[uid] = {}
        await q.message.edit_text("Choose a mode 👇", reply_markup=main_menu(uid))
        return

    # ============================
    # MAIN MENU ACTIONS
    # ============================
    if data == "menu_help":
        await q.message.edit_text(EXPLANATION, reply_markup=main_menu(uid))
        return

    if data == "menu_forms":
        await start_forms(uid, cid)
        return

    if data == "menu_translation":
        await start_translation(uid, cid)
        return

    if data == "menu_mix":
        await start_mix(uid, cid)
        return

    if data == "menu_speed":
        await start_speed(uid, cid)
        return

    if data == "menu_repeat":
        if not user_errors[uid]:
            await q.message.edit_text("🎉 No mistakes!", reply_markup=main_menu(uid))
            return

        err = user_errors[uid][0]
        verb = err["verb"]
        mode = err["mode"]

        user_state[uid] = {"mode": "repeat", "verb": verb, "repeat_mode": mode}

        if mode == "translation":
            await q.message.edit_text(
                f"🔁 Repeat — Translation\n\n*{verb['inf']}*",
                reply_markup=translation_kb("repeat")
            )
        else:
            await q.message.edit_text(
                f"🔁 Repeat — Forms\n\n{verb['inf']} — {verb['ru']}",
                reply_markup=forms_kb("repeat")
            )
        return

    if data == "menu_stats":
        s = user_stats[uid]
        await q.message.edit_text(
            f"📊 Stats:\n"
            f"Correct: {s['correct']}\n"
            f"Wrong: {s['wrong']}\n"
            f"Best streak: {s['best']}",
            reply_markup=main_menu(uid)
        )
        return

    # ============================
    #  SETTINGS
    # ============================

    def ensure_user_settings(uid):
        user_settings.setdefault(uid, {})
        user_settings[uid].setdefault("daily_enabled", False)
        user_settings[uid].setdefault("level", 1)


    if data == "menu_settings":
        ensure_user_settings(uid)

        lvl = user_settings[uid]["level"]
        daily = user_settings[uid]["daily_enabled"]

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎚 Difficulty", callback_data="menu_difficulty")],
            [InlineKeyboardButton(text="🔔 Daily reminder", callback_data="toggle_daily")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="back")]
        ])

        await q.message.edit_text(
            f"⚙️ Settings\n\n"
            f"Difficulty level: {lvl}\n"
            f"Daily: {'ON' if daily else 'OFF'}",
            reply_markup=kb
        )
        return


    if data == "toggle_daily":
        ensure_user_settings(uid)

        user_settings[uid]["daily_enabled"] = not user_settings[uid]["daily_enabled"]

        await q.message.edit_text("Choose a mode 👇", reply_markup=main_menu(uid))
        return


    if data == "menu_difficulty":
        ensure_user_settings(uid)

        lvl = user_settings[uid]["level"]

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=("✅ Level 1" if lvl == 1 else "Level 1"), callback_data="set_level_1")],
            [InlineKeyboardButton(text=("✅ Level 2" if lvl == 2 else "Level 2"), callback_data="set_level_2")],
            [InlineKeyboardButton(text=("✅ Level 3" if lvl == 3 else "Level 3"), callback_data="set_level_3")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="menu_settings")]
        ])

        await q.message.edit_text(
            f"🎚 Difficulty\n\n"
            f"Current level: {lvl}",
            reply_markup=kb
        )
        return


    if data == "set_level_1":
        ensure_user_settings(uid)
        user_settings[uid]["level"] = 1

        await q.message.edit_text("Level set to 1️⃣", reply_markup=main_menu(uid))
        return


    if data == "set_level_2":
        ensure_user_settings(uid)
        user_settings[uid]["level"] = 2

        await q.message.edit_text("Level set to 2️⃣", reply_markup=main_menu(uid))
        return


    if data == "set_level_3":
        ensure_user_settings(uid)
        user_settings[uid]["level"] = 3

        await q.message.edit_text("Level set to 3️⃣", reply_markup=main_menu(uid))
        return
    
    # ============================
    # DIFFICULTY
    # ============================
    if data == "menu_difficulty":
        await q.message.edit_text(
            "Choose difficulty level:",
            reply_markup=difficulty_kb()
        )
        return

    if data.startswith("difficulty_"):
        level = int(data.split("_")[1])
        user_settings[uid]["level"] = level

        await q.message.edit_text(
            f"Difficulty level set to {level}.",
            reply_markup=main_menu(uid)
        )
        return

    # ============================
    # NEXT BUTTONS
    # ============================
    if data.endswith("_next"):
        mode = data.split("_")[0]

        if mode == "forms":
            await start_forms(uid, cid)
        elif mode == "translation":
            await start_translation(uid, cid)
        elif mode == "mix":
            await start_mix(uid, cid)
        elif mode == "repeat":
            await start_mix(uid, cid)

        return

    # ============================
    # SPEED STOP
    # ============================
    if data == "speed_stop":
        st = user_state.get(uid, {})
        await q.message.edit_text(
            f"⏹ Stopped.\nCorrect: {st.get('correct', 0)}\nTotal: {st.get('total', 0)}",
            reply_markup=main_menu(uid)
        )
        user_state[uid] = {}
        return

# ============================
#  COMMANDS
# ============================

@dp.message(Command("start"))
async def cmd_start(msg: types.Message):
    uid = msg.from_user.id
    init_user(uid)
    await msg.answer("👋 Welcome! Choose a mode 👇", reply_markup=main_menu(uid))


@dp.message(Command("help"))
async def cmd_help(msg: types.Message):
    await msg.answer(
        "This bot helps you practise irregular verbs.\nChoose a mode 👇",
        reply_markup=main_menu(msg.from_user.id)
    )


@dp.message(Command("stats"))
async def cmd_stats(msg: types.Message):
    uid = msg.from_user.id
    init_user(uid)
    s = user_stats[uid]
    await msg.answer(
        f"📊 Stats:\n"
        f"Correct: {s['correct']}\n"
        f"Wrong: {s['wrong']}\n"
        f"Best streak: {s['best']}",
        reply_markup=main_menu(uid)
    )


# ============================
#  TEXT HANDLER
# ============================

@dp.message(F.text)
async def text_handler(msg: types.Message):
    uid = msg.from_user.id
    init_user(uid)
    st = user_state.get(uid)

    if not st or "mode" not in st:
        await msg.answer("Choose a mode 👇", reply_markup=main_menu(uid))
        return

    mode = st["mode"]
    text = msg.text.strip()

    if mode == "forms":
        await process_forms(uid, text, msg)
        return

    if mode == "translation":
        await process_translation(uid, text, msg)
        return

    if mode == "mix":
        if st["sub"] == "forms":
            await process_forms(uid, text, msg)
        else:
            await process_translation(uid, text, msg)
        return

    if mode == "speed":
        await process_speed(uid, text, msg)
        return
# ============================
#  WEBHOOK SERVER
# ============================

async def on_startup(app):
    # Устанавливаем вебхук
    if not WEBHOOK_URL:
        print("❗ WEBHOOK_URL is missing — webhook not set")
        return

    await bot.set_webhook(WEBHOOK_URL)
    print(f"🌐 Webhook set: {WEBHOOK_URL}")


async def on_shutdown(app):
    await bot.session.close()


# Создаём aiohttp приложение
app = web.Application()

# Регистрируем обработчик вебхука (ОБЯЗАТЕЛЬНО!)
SimpleRequestHandler(dp, bot).register(app, path=WEBHOOK_PATH)

# Подключаем aiogram к aiohttp
setup_application(app, dp, bot=bot)

# Регистрируем события
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

# Запуск сервера
if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))