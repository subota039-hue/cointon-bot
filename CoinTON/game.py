import telebot
from telebot import types
import json
import time
import os

# ========= CONFIG =========
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)
ADMIN_ID = 8420528030
DATA_FILE = "users.json"

# ========= FANS =========
FANS = {
    "basic": {"name": "⚪ Обычный", "income": 0.00005, "price": 0},
    "red": {"name": "🔴 Красный", "income": 0.00007, "price": 50},
    "green": {"name": "🟢 Зелёный", "income": 0.00008, "price": 75},
    "blue": {"name": "🔵 Синий", "income": 0.00009, "price": 100},
    "purple": {"name": "🟣 Фиолетовый", "income": 0.00011, "price": 200},
    "orange": {"name": "🟠 Оранжевый", "income": 0.00012, "price": 300},
    "rainbow": {"name": "🌈 Радужный", "income": 0.005, "price": 1000}
}

FAKE_LEADERS = [
    ("CryptoKing", 12540),
    ("FanMaster", 9842),
    ("NeonRich", 8104),
    ("TON_Lord", 6500),
    ("BlockFan", 5420),
]

# ========= STORAGE =========
users = {}
if os.path.exists(DATA_FILE):
    users = json.load(open(DATA_FILE, "r", encoding="utf-8"))

def save():
    json.dump(users, open(DATA_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def get_user(uid):
    uid = str(uid)
    if uid not in users:
        users[uid] = {
            "nick": None,
            "ct": 0.0,
            "fan": "basic",
            "offline": False,
            "last": time.time(),
            "banned": False,
            "last_click": 0,
            "violations": 0,
            "admin_grant": False,
            "last_msg": None
        }
        save()
    return users[uid]

# ========= ECONOMY =========
def update_income(u):
    now = time.time()
    delta = min(now - u["last"], 3600)
    income = FANS[u["fan"]]["income"] * delta
    if u["offline"]:
        income *= 2
    u["ct"] += income
    u["last"] = now

# ========= MESSAGES =========
def send_clean(uid, text, reply_markup=None):
    u = get_user(uid)
    if u["last_msg"]:
        try:
            bot.delete_message(uid, u["last_msg"])
        except:
            pass
    msg = bot.send_message(uid, text, reply_markup=reply_markup)
    u["last_msg"] = msg.message_id
    save()

# ========= MENUS =========
def main_menu():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💰 Баланс", callback_data="balance"))
    kb.add(types.InlineKeyboardButton("🌀 Вентилятор", callback_data="fan"))
    kb.add(types.InlineKeyboardButton("🏆 Рейтинг", callback_data="rating"))
    return kb

def balance_menu():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("➕ Донат", url="https://t.me/CoinTON_Supp"))
    kb.add(types.InlineKeyboardButton("➖ Вывести", url="https://t.me/CoinTON_Supp"))
    kb.add(types.InlineKeyboardButton("⬅ Назад", callback_data="back"))
    return kb

def fan_menu(uid):
    kb = types.InlineKeyboardMarkup()
    u = get_user(uid)
    for k, f in FANS.items():
        text = f"{f['name']} | {f['price']} CT | {f['income']:.5f}/сек"
        if u["fan"] == k:
            text += " ✅"
            kb.add(types.InlineKeyboardButton(text, callback_data="none"))
        else:
            kb.add(types.InlineKeyboardButton(text, callback_data=f"buy_{k}"))
    kb.add(types.InlineKeyboardButton("⬅ Назад", callback_data="back"))
    return kb

def fake_leaderboard_text():
    txt = "🏆 Топ игроков\n\n"
    for i, (nick, ct) in enumerate(FAKE_LEADERS, 1):
        txt += f"{i}. {nick} — {ct} CT\n"
    return txt

def show_main_menu(uid):
    kb = main_menu()
    try:
        with open("menu.jpg", "rb") as photo:
            msg = bot.send_photo(uid, photo, caption="Главное меню", reply_markup=kb)
    except FileNotFoundError:
        msg = bot.send_message(uid, "Главное меню", reply_markup=kb)
    u = get_user(uid)
    u["last_msg"] = msg.message_id
    save()

# ========= START =========
@bot.message_handler(commands=["start"])
def start(msg):
    u = get_user(msg.from_user.id)
    if u["banned"]:
        send_clean(msg.chat.id, "🚫 Вы заблокированы")
        return
    if not u["nick"]:
        send_clean(msg.chat.id, "Введите уникальный ник:")
        bot.register_next_step_handler(msg, set_nick)
    else:
        update_income(u)
        save()
        show_main_menu(msg.chat.id)

def set_nick(msg):
    if any(u.get("nick") == msg.text for u in users.values()):
        send_clean(msg.chat.id, "❌ Ник занят")
        return
    u = get_user(msg.from_user.id)
    u["nick"] = msg.text
    save()
    show_main_menu(msg.chat.id)

# ========= ADMIN MENU =========
def admin_menu():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🚫 Бан по нику", callback_data="aban"))
    kb.add(types.InlineKeyboardButton("🔓 Разбан по нику", callback_data="aunban"))
    kb.add(types.InlineKeyboardButton("💸 Выдать CT", callback_data="agive"))
    return kb

@bot.message_handler(commands=["Admin"])
def admin_panel(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    send_clean(msg.chat.id, "🧑‍💼 Админ-панель", admin_menu())

# ========= CALLBACK HANDLER =========
@bot.callback_query_handler(func=lambda c: True)
def cb(call):
    uid = call.from_user.id
    u = get_user(uid)
    update_income(u)
    save()

    # Защита от спама
    if time.time() - u["last_click"] < 0.8:
        bot.answer_callback_query(call.id, "⏳ Не так быстро")
        return
    u["last_click"] = time.time()

    if u["banned"]:
        bot.answer_callback_query(call.id, "🚫 Заблокированы")
        return

    # ======== MAIN MENU ========
    if call.data == "balance":
        send_clean(uid, f"💰 Баланс: {u['ct']:.5f} CT", balance_menu())
    elif call.data == "fan":
        send_clean(uid, "🌀 Магазин вентиляторов", fan_menu(uid))
    elif call.data.startswith("buy_"):
        k = call.data[4:]
        f = FANS[k]
        if u["ct"] >= f["price"]:
            u["ct"] -= f["price"]
            u["fan"] = k
            save()
        send_clean(uid, "🌀 Магазин вентиляторов", fan_menu(uid))
    elif call.data == "rating":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅ Назад", callback_data="back"))
        send_clean(uid, fake_leaderboard_text(), kb)
    elif call.data == "back":
        show_main_menu(uid)

    # ======== ADMIN ACTIONS ========
    elif call.data in ["aban", "aunban", "agive"] and uid == ADMIN_ID:
        txt = {"aban": "Введите ник для бана:", "aunban": "Введите ник для разбана:", "agive": "Введите: ник сумма"}[call.data]
        m = bot.send_message(uid, txt)
        bot.register_next_step_handler(m, admin_action, call.data)

def admin_action(msg, action):
    parts = msg.text.strip().split()
    if not parts:
        return
    nick = parts[0]
    target = next((u for u in users.values() if u.get("nick") == nick), None)
    if not target:
        send_clean(msg.chat.id, "❌ Пользователь не найден")
        return
    if action == "aban":
        target["banned"] = True
        send_clean(msg.chat.id, f"🚫 Пользователь {nick} забанен")
    elif action == "aunban":
        target["banned"] = False
        send_clean(msg.chat.id, f"🔓 Пользователь {nick} разбанен")
    elif action == "agive":
        try:
            amount = float(parts[1])
            target["admin_grant"] = True
            target["ct"] += amount
            target["admin_grant"] = False
            send_clean(msg.chat.id, f"💸 Выдано {amount} CT пользователю {nick}")
        except:
            send_clean(msg.chat.id, "❌ Формат: ник сумма")
    save()

# ========= RUN =========
bot.infinity_polling()
