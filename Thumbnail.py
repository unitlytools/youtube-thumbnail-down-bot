import os
import re
import requests
import tempfile
import threading

from PIL import Image
from flask import Flask
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ✅ Your Bot Token
TOKEN = "8300053434:AAFOFKKtCAC-W16MPdaPhcqdjHKnH1Q6YI4"

# ✅ Flask app
app = Flask(__name__)

@app.route("/health")
def health():
    return "OK", 200

# ✅ Detect Shorts
def is_shorts_url(url):
    return "youtube.com/shorts/" in url

# ✅ Extract YouTube video ID (Supports Shorts, Watch, and youtu.be)
def extract_youtube_id(url):
    patterns = [
        r"(?:https?://)?(?:www\.)?youtu\.be/([^\s/?&]+)",
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([^\s&]+)",
        r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([^\s/?&]+)"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

# ✅ /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me a YouTube video link (Shorts or normal), and I'll send a proper thumbnail as a downloadable file.")

# ✅ Main message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    video_id = extract_youtube_id(text)

    if not video_id:
        await update.message.reply_text("❌ Invalid YouTube URL.")
        return

    is_shorts = is_shorts_url(text)

    thumb_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    response = requests.get(thumb_url)

    if response.status_code != 200:
        thumb_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        response = requests.get(thumb_url)

    if response.status_code != 200:
        await update.message.reply_text("❌ Thumbnail not found.")
        return

    # Save image temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        tmp.write(response.content)
        tmp_path = tmp.name

    # ✅ Crop for Shorts (9:16 vertical center)
    if is_shorts:
        try:
            with Image.open(tmp_path) as img:
                width, height = img.size
                new_width = int(height * 9 / 16)
                left = (width - new_width) // 2
                right = left + new_width
                cropped = img.crop((left, 0, right, height))
                cropped.save(tmp_path)
        except Exception as e:
            await update.message.reply_text("⚠️ Failed to crop image to Shorts format.")

    # ✅ Send as downloadable document
    await update.message.reply_document(
        document=open(tmp_path, "rb"),
        filename=f"{video_id}_thumbnail.jpg",
        caption="📥 Here's your thumbnail (adjusted for Shorts if needed)"
    )

    os.remove(tmp_path)

# ✅ Run Flask in background thread
def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

# ✅ Main entry
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()

    app_bot = ApplicationBuilder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app_bot.run_polling()
    
