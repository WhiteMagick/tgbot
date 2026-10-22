import requests
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bs4 import BeautifulSoup
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
# --- настройки ---
TOKEN = ""
CHAT_ID = ""
RUTUBE_PLAYLIST_URL = "https://rutube.ru/api/playlist/custom/709312/videos"

# --- логирование ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

last_video_id = None  # для Rutube

# --- получаем случайный стих (русский перевод НРП) ---
def get_random_bible_verse_ru():
    url = "https://www.bible.com/ru/verse-of-the-day"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(resp.text, "html.parser")
    a_tag = soup.find('div', class_='border rounded-1 border-l-large border-black mbe-3 mbs-2 plb-1 pli-1 pis-2 dark:border-white') 

    if a_tag:
        text = a_tag.get_text(strip=True)
        print("Найденный текст:", text)
        return f"{text}"
    else:
        #logger.error(f"Ошибка при получении стиха: {e}")
        return "⚠️ Не удалось получить стих."

# --- отправка стиха ---
async def send_daily_verse(app: Application):
    verse = get_random_bible_verse_ru()
    await app.bot.send_message(chat_id=CHAT_ID, text=f"📖 Сегодняшний стих:\n\n{verse}")

async def verse_of_the_day(app: Application):
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Без окна
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)

    url = "https://www.bible.com/ru/verse-of-the-day"
    driver.get(url)
    # --- 2. Ждём появления контента ---
    wait = WebDriverWait(driver, 15)
    # --- 3. Извлекаем HTML и парсим ---
    html = driver.page_source
    driver.quit()
    soup = BeautifulSoup(html, "html.parser")
    eta_desc = soup.find("meta", property="og:image")
    print(eta_desc["content"])
    if eta_desc:
        await app.bot.send_photo(chat_id=CHAT_ID,photo=eta_desc["content"])
    meta_desc = soup.find("meta", property="og:description")
    print(meta_desc["content"])
    verse = meta_desc["content"]
    if meta_desc:
        await app.bot.send_message(chat_id=CHAT_ID, text=f"📖 Сегодняшний стих:\n\n{verse}")


# --- проверка Rutube ---
async def check_rutube(app: Application):
    global last_video_id
    try:
        resp = requests.get(RUTUBE_PLAYLIST_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).json()
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

    async def on_startup(app: Application):
        #scheduler.add_job(send_daily_verse, "cron", hour=2, minute=0, args=[app])
        scheduler.add_job(verse_of_the_day, "cron", hour=2, minute=0, args=[app])
        scheduler.add_job(check_rutube, "interval", minutes=5, args=[app])
        scheduler.start()

    app.post_init = on_startup

    app.run_polling()
    
if __name__ == "__main__":
    main()