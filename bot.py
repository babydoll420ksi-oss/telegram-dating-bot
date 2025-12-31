import json, os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

# ================= CONFIG =================
TOKEN = "8300397418:AAHb4chq4DLBnl2mkBBu2EuxbHy_IqDB3Fw"
ADMIN_ID = 1600167005  # <-- apna Telegram ID
# =========================================

FILES = {
    "users": "users.json",
    "likes": "likes.json",
    "bans": "bans.json",
    "chats": "chats.json",
    "blocks": "blocks.json",
    "reports": "reports.json"
}

for f in FILES.values():
    if not os.path.exists(f):
        with open(f, "w") as x:
            json.dump({}, x)

steps = {}
photo_wait = set()


def load(name):
    with open(FILES[name]) as f:
        return json.load(f)


def save(name, data):
    with open(FILES[name], "w") as f:
        json.dump(data, f, indent=2)


# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if uid in load("bans"):
        await update.message.reply_text("🚫 You are banned.")
        return
    steps[uid] = "name"
    await update.message.reply_text("👋 Welcome!\nYour name?")


# ---------- TEXT ----------
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    text = update.message.text
    users = load("users")

    # Anonymous chat
    if uid not in steps and uid not in photo_wait:
        chats = load("chats")
        if uid in chats:
            await context.bot.send_message(
                chats[uid], f"💬 Anonymous: {text}"
            )
        return

    step = steps.get(uid)

    if step == "name":
        users[uid] = {"name": text}
        steps[uid] = "age"
        await update.message.reply_text("🎂 Age? (18+)")
    elif step == "age":
        if not text.isdigit() or int(text) < 18:
            await update.message.reply_text("❌ 18+ only")
            return
        users[uid]["age"] = int(text)
        steps[uid] = "gender"
        await update.message.reply_text("⚧ Gender?")
    elif step == "gender":
        users[uid]["gender"] = text
        steps[uid] = "city"
        await update.message.reply_text("🏙️ City?")
    elif step == "city":
        users[uid]["city"] = text
        steps.pop(uid)
        photo_wait.add(uid)
        await update.message.reply_text("📸 Send profile photo")

    save("users", users)


# ---------- PHOTO ----------
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if uid not in photo_wait:
        return
    users = load("users")
    users[uid]["photo"] = update.message.photo[-1].file_id
    save("users", users)
    photo_wait.remove(uid)
    await update.message.reply_text("✅ Profile ready! Use /browse")


# ---------- BROWSE ----------
async def browse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    users = load("users")
    likes = load("likes")
    blocks = load("blocks")

    seen = set(likes.get(uid, []))
    blocked = set(blocks.get(uid, []))

    for k, v in users.items():
        if k != uid and k not in seen and k not in blocked:
            context.user_data["current"] = k
            await update.message.reply_photo(
                v["photo"],
                caption=f"{v['name']}, {v['age']}\n{v['gender']} | {v['city']}\n\n❤️ /like ❌ /skip 🚫 /block 🚩 /report"
            )
            return
    await update.message.reply_text("😔 No profiles available")


# ---------- LIKE ----------
async def like(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    t = context.user_data.get("current")
    if not t:
        return

    likes = load("likes")
    likes.setdefault(uid, []).append(t)
    save("likes", likes)

    if uid in likes.get(t, []):
        chats = load("chats")
        chats[uid] = t
        chats[t] = uid
        save("chats", chats)
        await update.message.reply_text("💞 MATCH! Chat started")
        await context.bot.send_message(t, "💞 MATCH! Chat started")
    else:
        await update.message.reply_text("👍 Liked! /browse")


async def skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏭️ Skipped /browse")


# ---------- BLOCK ----------
async def block(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    t = context.user_data.get("current")
    if not t:
        return
    blocks = load("blocks")
    blocks.setdefault(uid, []).append(t)
    save("blocks", blocks)
    await update.message.reply_text("🚫 User blocked")


# ---------- REPORT ----------
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    t = context.user_data.get("current")
    if not t:
        return
    reports = load("reports")
    reports.setdefault(t, []).append(uid)
    save("reports", reports)
    await update.message.reply_text("🚩 User reported")


# ---------- ADMIN ----------
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    users = load("users")
    reports = load("reports")
    await update.message.reply_text(
        f"🛡️ Admin Panel\n"
        f"Users: {len(users)}\n"
        f"Reported: {len(reports)}\n"
        "/ban <id>\n/broadcast <msg>"
    )


async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    bans = load("bans")
    bans[context.args[0]] = True
    save("bans", bans)
    await update.message.reply_text("🚫 User banned")


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    msg = " ".join(context.args)
    users = load("users")
    for u in users:
        try:
            await context.bot.send_message(u, f"📢 {msg}")
        except:
            pass
    await update.message.reply_text("✅ Broadcast sent")


# ---------- APP ----------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("browse", browse))
app.add_handler(CommandHandler("like", like))
app.add_handler(CommandHandler("skip", skip))
app.add_handler(CommandHandler("block", block))
app.add_handler(CommandHandler("report", report))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CommandHandler("ban", ban))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

print("🔥 FULL Dating Bot Running...")
app.run_polling()
