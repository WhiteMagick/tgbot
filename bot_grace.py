import requests
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# --- настройки ---
TOKEN = ""
CHAT_ID = ""
RUTUBE_PLAYLIST_URL = "https://rutube.ru/api/playlist/custom/709312/videos"

# --- логирование ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

last_video_id = None  # для Rutube

# --- получаем случайный стих (русский перевод РСТ) ---
def get_random_bible_verse_ru():
    try:
        resp = requests.get("https://justbible.ru/api/random?translation=rst", timeout=10).json()
        #book = resp.get("book")
        #chapter = resp.get("chapter")
        verse = resp.get("verse")
        info = resp.get("info")
        return f"{verse} — {info}"
    except Exception as e:
        logger.error(f"Ошибка при получении стиха: {e}")
        return "⚠️ Не удалось получить стих."

# --- отправка стиха ---
async def send_daily_verse(app: Application):
    verse = get_random_bible_verse_ru()
    await app.bot.send_message(chat_id=CHAT_ID, text=f"📖 Сегодняшний стих:\n\n{verse}")

# --- проверка Rutube ---
async def check_rutube(app: Application):
    global last_video_id
    try:
        resp = requests.get(RUTUBE_PLAYLIST_URL, timeout=10).json()
        results = resp.get("results", [])
        if not results:
            return
        latest = results[0]
        video_id = latest["id"]
        title = latest["title"]
        url = f"https://rutube.ru/video/{video_id}/"
        print(last_video_id)
        if last_video_id is None:
            last_video_id = video_id
            print(last_video_id+"было 0")
        elif video_id != last_video_id:
            last_video_id = video_id
            print(last_video_id)
            await app.bot.send_message(
                chat_id=CHAT_ID,
                text=f"🎬 Новое видео!\n\n{title}\n{url}"
            )
    except Exception as e:
        logger.error(f"Ошибка при проверке Rutube: {e}")

# --- команда /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"Твой chat_id: {chat_id}")
    await update.message.reply_text("Привет! Я буду присылать случайный стих из Библии и уведомлять о новых видео.")

# --- запуск ---
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(send_daily_verse, "cron", hour=2, minute=00, args=[app])  # каждый день в 9:00
    scheduler.add_job(check_rutube, "interval", minutes=5, args=[app])        # проверка каждые 10 мин
    scheduler.start()

    app.run_polling()

if __name__ == "__main__":
    main()