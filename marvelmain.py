import sqlite3
import logging

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =========================================================
# SOZLAMALAR
# =========================================================

BOT_TOKEN = ""
ADMIN_ID = 6299950641  # BU YERGA O'Z TELEGRAM IDINGIZNI YOZING

# =========================================================
# LOG
# =========================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

# =========================================================
# DATABASE
# =========================================================

DB_NAME = "marvel_bot.db"

db = sqlite3.connect(DB_NAME, check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    file_id TEXT NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL
)
""")

db.commit()

# =========================================================
# ADMIN HOLATLARI
# =========================================================

admin_states = {}

# =========================================================
# YORDAMCHI FUNKSIYALAR
# =========================================================

def is_admin(user_id):
    return user_id == ADMIN_ID


def save_user(user_id):
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
        (user_id,)
    )
    db.commit()


async def check_subscription(user_id, context):
    cursor.execute("SELECT username FROM channels")
    channels = cursor.fetchall()

    if not channels:
        return True

    for (username,) in channels:
        try:
            member = await context.bot.get_chat_member(
                chat_id=username,
                user_id=user_id
            )

            if member.status in ["left", "kicked"]:
                return False

        except Exception as e:
            logger.error(f"Kanal tekshirish xatosi: {username} - {e}")
            return False

    return True


def subscription_keyboard():
    cursor.execute("SELECT username FROM channels")
    channels = cursor.fetchall()

    buttons = []

    for (username,) in channels:
        name = username.replace("@", "")
        buttons.append([
            InlineKeyboardButton(
                f"📢 {name}",
                url=f"https://t.me/{name}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "✅ Obunani tekshirish",
            callback_data="check_subscription"
        )
    ])

    return InlineKeyboardMarkup(buttons)


def main_menu():
    keyboard = [
        [
            InlineKeyboardButton(
                "🎬 Kino kodini yuborish",
                callback_data="movie_code"
            )
        ],
        [
            InlineKeyboardButton(
                "ℹ️ Bot haqida",
                callback_data="about"
            )
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    save_user(user.id)

    subscribed = await check_subscription(user.id, context)

    if not subscribed:
        await update.message.reply_text(
            "🔐 Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:\n\n"
            "Obuna bo‘lgandan keyin «Obunani tekshirish» tugmasini bosing.",
            reply_markup=subscription_keyboard()
        )
        return

    await update.message.reply_text(
        f"👋 Salom, {user.first_name}!\n\n"
        "🎬 Marvel Kino Botiga xush kelibsiz!\n\n"
        "Kino kodini yuboring.\n"
        "Masalan: 101",
        reply_markup=main_menu()
    )


# =========================================================
# CALLBACK
# =========================================================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data == "check_subscription":

        subscribed = await check_subscription(user_id, context)

        if not subscribed:
            await query.message.reply_text(
                "❌ Siz hali barcha kanallarga obuna bo‘lmagansiz.",
                reply_markup=subscription_keyboard()
            )
            return

        await query.message.reply_text(
            "✅ Obuna tasdiqlandi!\n\n"
            "🎬 Endi kino kodini yuboring.",
            reply_markup=main_menu()
        )

    elif query.data == "movie_code":

        subscribed = await check_subscription(user_id, context)

        if not subscribed:
            await query.message.reply_text(
                "🔐 Avval kanallarga obuna bo‘ling.",
                reply_markup=subscription_keyboard()
            )
            return

        await query.message.reply_text(
            "🎬 Kino kodini yuboring.\n\n"
            "Masalan:\n"
            "101"
        )

    elif query.data == "about":

        await query.message.reply_text(
            "🎬 MARVEL KINO BOT\n\n"
            "Bu bot orqali kino kodini yuborib "
            "kerakli kinoni topishingiz mumkin.\n\n"
            "📌 Kino kodini yuboring va bot sizga kinoni chiqarib beradi."
        )


# =========================================================
# ADMIN PANEL
# =========================================================

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text(
            "❌ Siz admin emassiz."
        )
        return

    keyboard = [
        [
            InlineKeyboardButton(
                "➕ Kino qo‘shish",
                callback_data="admin_add_movie"
            )
        ],
        [
            InlineKeyboardButton(
                "🗑 Kino o‘chirish",
                callback_data="admin_delete_movie"
            )
        ],
        [
            InlineKeyboardButton(
                "📋 Kinolar",
                callback_data="admin_movies"
            )
        ],
        [
            InlineKeyboardButton(
                "➕ Kanal qo‘shish",
                callback_data="admin_add_channel"
            )
        ],
        [
            InlineKeyboardButton(
                "🗑 Kanal o‘chirish",
                callback_data="admin_delete_channel"
            )
        ],
        [
            InlineKeyboardButton(
                "📢 Kanallar",
                callback_data="admin_channels"
            )
        ],
        [
            InlineKeyboardButton(
                "📊 Statistika",
                callback_data="admin_stats"
            )
        ],
    ]

    await update.message.reply_text(
        "⚙️ ADMIN PANEL\n\n"
        "Kerakli bo‘limni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================================================
# ADMIN CALLBACK
# =========================================================

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.message.reply_text(
            "❌ Ruxsat yo‘q."
        )
        return

    data = query.data

    # -----------------------------
    # KINO QO'SHISH
    # -----------------------------

    if data == "admin_add_movie":

        admin_states[user_id] = {
            "state": "movie_code"
        }

        await query.message.reply_text(
            "➕ KINO QO‘SHISH\n\n"
            "1️⃣ Kino kodini yuboring.\n\n"
            "Masalan: 101"
        )

    # -----------------------------
    # KINO O'CHIRISH
    # -----------------------------

    elif data == "admin_delete_movie":

        admin_states[user_id] = {
            "state": "delete_movie"
        }

        await query.message.reply_text(
            "🗑 O‘chiriladigan kino kodini yuboring."
        )

    # -----------------------------
    # KINOLAR
    # -----------------------------

    elif data == "admin_movies":

        cursor.execute(
            "SELECT code, title FROM movies ORDER BY id DESC"
        )

        movies = cursor.fetchall()

        if not movies:
            await query.message.reply_text(
                "📭 Hozircha kinolar yo‘q."
            )
            return

        text = "🎬 KINOLAR RO‘YXATI\n\n"

        for code, title in movies:
            text += f"🔹 {code} — {title}\n"

        await query.message.reply_text(text)

    # -----------------------------
    # KANAL QO'SHISH
    # -----------------------------

    elif data == "admin_add_channel":

        admin_states[user_id] = {
            "state": "add_channel"
        }

        await query.message.reply_text(
            "➕ KANAL QO‘SHISH\n\n"
            "Kanal username'ini yuboring.\n\n"
            "Masalan:\n"
            "@MarvelKino"
        )

    # -----------------------------
    # KANAL O'CHIRISH
    # -----------------------------

    elif data == "admin_delete_channel":

        admin_states[user_id] = {
            "state": "delete_channel"
        }

        await query.message.reply_text(
            "🗑 O‘chiriladigan kanal username'ini yuboring.\n\n"
            "Masalan:\n"
            "@MarvelKino"
        )

    # -----------------------------
    # KANALLAR
    # -----------------------------

    elif data == "admin_channels":

        cursor.execute(
            "SELECT username FROM channels"
        )

        channels = cursor.fetchall()

        if not channels:
            await query.message.reply_text(
                "📭 Majburiy kanallar yo‘q."
            )
            return

        text = "📢 MAJBURIY KANALLAR\n\n"

        for (username,) in channels:
            text += f"🔹 {username}\n"

        await query.message.reply_text(text)

    # -----------------------------
    # STATISTIKA
    # -----------------------------

    elif data == "admin_stats":

        cursor.execute(
            "SELECT COUNT(*) FROM users"
        )
        users = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM movies"
        )
        movies = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM channels"
        )
        channels = cursor.fetchone()[0]

        await query.message.reply_text(
            "📊 BOT STATISTIKASI\n\n"
            f"👥 Foydalanuvchilar: {users}\n"
            f"🎬 Kinolar: {movies}\n"
            f"📢 Kanallar: {channels}"
        )


# =========================================================
# ADMIN MATN VA VIDEO
# =========================================================

async def admin_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    if not is_admin(user_id):
        return False

    if user_id not in admin_states:
        return False

    state = admin_states[user_id]["state"]

    # =====================================================
    # KINO KODI
    # =====================================================

    if state == "movie_code":

        if not update.message.text:
            return True

        code = update.message.text.strip()

        cursor.execute(
            "SELECT id FROM movies WHERE code = ?",
            (code,)
        )

        if cursor.fetchone():
            await update.message.reply_text(
                "❌ Bu kod allaqachon mavjud.\n"
                "Boshqa kod yuboring."
            )
            return True

        admin_states[user_id] = {
            "state": "movie_title",
            "code": code
        }

        await update.message.reply_text(
            "✅ Kod qabul qilindi.\n\n"
            "2️⃣ Kino nomini yuboring."
        )

        return True

    # =====================================================
    # KINO NOMI
    # =====================================================

    if state == "movie_title":

        title = update.message.text.strip()

        admin_states[user_id]["title"] = title
        admin_states[user_id]["state"] = "movie_description"

        await update.message.reply_text(
            "✅ Kino nomi saqlandi.\n\n"
            "3️⃣ Kino haqida qisqacha ma’lumot yuboring.\n\n"
            "Agar kerak bo‘lmasa, '-' yuboring."
        )

        return True

    # =====================================================
    # KINO TAVSIFI
    # =====================================================

    if state == "movie_description":

        description = update.message.text.strip()

        if description == "-":
            description = ""

        admin_states[user_id]["description"] = description
        admin_states[user_id]["state"] = "movie_video"

        await update.message.reply_text(
            "✅ Ma’lumot saqlandi.\n\n"
            "4️⃣ Endi kinoni VIDEO ko‘rinishida shu yerga yuboring."
        )

        return True

    # =====================================================
    # KINO VIDEOSI
    # =====================================================

    if state == "movie_video":

        if not update.message.video:

            await update.message.reply_text(
                "❌ Iltimos, kino faylini VIDEO sifatida yuboring."
            )

            return True

        video = update.message.video

        code = admin_states[user_id]["code"]
        title = admin_states[user_id]["title"]
        description = admin_states[user_id]["description"]

        cursor.execute(
            """
            INSERT INTO movies
            (code, title, description, file_id)
            VALUES (?, ?, ?, ?)
            """,
            (
                code,
                title,
                description,
                video.file_id
            )
        )

        db.commit()

        del admin_states[user_id]

        await update.message.reply_text(
            "🎉 KINO MUVAFFAQIYATLI QO‘SHILDI!\n\n"
            f"🔢 Kod: {code}\n"
            f"🎬 Nomi: {title}"
        )

        return True

    # =====================================================
    # KINO O'CHIRISH
    # =====================================================

    if state == "delete_movie":

        code = update.message.text.strip()

        cursor.execute(
            "SELECT title FROM movies WHERE code = ?",
            (code,)
        )

        movie = cursor.fetchone()

        if not movie:

            await update.message.reply_text(
                "❌ Bunday koddagi kino topilmadi."
            )

            return True

        cursor.execute(
            "DELETE FROM movies WHERE code = ?",
            (code,)
        )

        db.commit()

        del admin_states[user_id]

        await update.message.reply_text(
            "✅ Kino o‘chirildi.\n\n"
            f"🔢 Kod: {code}\n"
            f"🎬 Nomi: {movie[0]}"
        )

        return True

    # =====================================================
    # KANAL QO'SHISH
    # =====================================================

    if state == "add_channel":

        username = update.message.text.strip()

        if not username.startswith("@"):
            username = "@" + username

        try:

            cursor.execute(
                "INSERT INTO channels (username) VALUES (?)",
                (username,)
            )

            db.commit()

            del admin_states[user_id]

            await update.message.reply_text(
                "✅ Kanal qo‘shildi.\n\n"
                f"📢 {username}\n\n"
                "⚠️ Bot ushbu kanalga ADMIN qilib qo‘yilgan bo‘lishi kerak."
            )

        except sqlite3.IntegrityError:

            await update.message.reply_text(
                "❌ Bu kanal allaqachon mavjud."
            )

        return True

    # =====================================================
    # KANAL O'CHIRISH
    # =====================================================

    if state == "delete_channel":

        username = update.message.text.strip()

        if not username.startswith("@"):
            username = "@" + username

        cursor.execute(
            "SELECT id FROM channels WHERE username = ?",
            (username,)
        )

        if not cursor.fetchone():

            await update.message.reply_text(
                "❌ Bunday kanal topilmadi."
            )

            return True

        cursor.execute(
            "DELETE FROM channels WHERE username = ?",
            (username,)
        )

        db.commit()

        del admin_states[user_id]

        await update.message.reply_text(
            f"✅ Kanal o‘chirildi:\n{username}"
        )

        return True

    return False


# =========================================================
# KINO KODINI QIDIRISH
# =========================================================

async def movie_code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    # Admin hozir ma'lumot kiritayotgan bo'lsa
    if is_admin(user_id) and user_id in admin_states:
        return

    if not update.message.text:
        return

    code = update.message.text.strip()

    # Faqat raqamli kod
    if not code.isdigit():
        return

    save_user(user_id)

    subscribed = await check_subscription(user_id, context)

    if not subscribed:

        await update.message.reply_text(
            "🔐 Kino olish uchun avval kanallarga obuna bo‘ling.",
            reply_markup=subscription_keyboard()
        )

        return

    cursor.execute(
        """
        SELECT title, description, file_id
        FROM movies
        WHERE code = ?
        """,
        (code,)
    )

    movie = cursor.fetchone()

    if not movie:

        await update.message.reply_text(
            "❌ Bunday koddagi kino topilmadi.\n\n"
            "Kino kodini tekshirib qayta yuboring."
        )

        return

    title, description, file_id = movie

    caption = f"🎬 {title}"

    if description:
        caption += f"\n\n📝 {description}"

    try:

        await update.message.reply_video(
            video=file_id,
            caption=caption
        )

    except Exception as e:

        logger.error(f"Video yuborish xatosi: {e}")

        await update.message.reply_text(
            "❌ Kinoni yuborishda xatolik yuz berdi."
        )


# =========================================================
# UMUMIY MATN HANDLER
# =========================================================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    if is_admin(user_id) and user_id in admin_states:

        handled = await admin_message_handler(
            update,
            context
        )

        if handled:
            return

    await movie_code_handler(
        update,
        context
    )


# =========================================================
# XATOLAR
# =========================================================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):

    logger.error(
        "Xatolik:",
        exc_info=context.error
    )


# =========================================================
# MAIN
# =========================================================

def main():

    if BOT_TOKEN == "BU_YERGA_BOT_TOKENINGIZNI_QOYING":

        print("❌ BOT TOKEN KIRITILMAGAN!")
        print("marvelmain.py faylini ochib BOT_TOKEN ni yozing.")
        return

    if ADMIN_ID == 123456789:

        print("❌ ADMIN_ID KIRITILMAGAN!")
        print("marvelmain.py faylini ochib ADMIN_ID ni yozing.")
        return

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # Commands
    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("admin", admin_command)
    )

    # Callback
    application.add_handler(
        CallbackQueryHandler(
            callback_handler,
            pattern="^(check_subscription|movie_code|about)$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern="^admin_"
        )
    )

    # Video va matn
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler
        )
    )

    application.add_handler(
        MessageHandler(
            filters.VIDEO,
            text_handler
        )
    )

    application.add_error_handler(
        error_handler
    )

    print("====================================")
    print("🎬 MARVEL KINO BOT ISHGA TUSHDI!")
    print("====================================")

    application.run_polling(
        drop_pending_updates=True
    )


# =========================================================
# START PROGRAM
# =========================================================

if __name__ == "__main__":
    main()
