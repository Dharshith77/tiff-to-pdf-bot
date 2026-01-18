import os
import logging
import asyncio
from io import BytesIO
from PIL import Image
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from flask import Flask, request, Response
from concurrent.futures import ThreadPoolExecutor

# ================= CONFIG =================
BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
PORT = int(os.environ.get("PORT", 8080))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TifftoPdf")

# ================= FLASK =================
app = Flask(__name__)

@app.route("/")
def home():
    return "TIFF to PDF bot is alive!"

# ================= TELEGRAM HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send me a TIFF file and I'll convert it to PDF!"
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document

    if not document or not document.file_name.lower().endswith(".tiff"):
        await update.message.reply_text("Please send a TIFF file only.")
        return

    file_id = document.file_id
    display_name = os.path.splitext(document.file_name)[0]
    tiff_path = f"{file_id}.tiff"
    pdf_path = f"{file_id}.pdf"

    try:
        tg_file = await context.bot.get_file(file_id)
        await tg_file.download_to_drive(tiff_path)

        image = Image.open(tiff_path)
        frames = []

        try:
            while True:
                frames.append(image.copy())
                image.seek(len(frames))
        except EOFError:
            pass

        frames[0].save(
            pdf_path,
            save_all=True,
            append_images=frames[1:],
            resolution=100.0,
        )

        with open(pdf_path, "rb") as f:
            bio = BytesIO(f.read())
            bio.name = f"{display_name}.pdf"
            await update.message.reply_document(bio)

    except Exception as e:
        logger.exception("Conversion error")
        await update.message.reply_text(
            "Something went wrong while converting the file."
        )

    finally:
        for f in (tiff_path, pdf_path):
            if os.path.exists(f):
                os.remove(f)

# ================= TELEGRAM APP =================
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

# ================= ASYNCIO LOOP (GLOBAL) =================
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# ================= WEBHOOK =================
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), telegram_app.bot)
        asyncio.run_coroutine_threadsafe(
            telegram_app.process_update(update),
            loop,
        )
        return Response("ok", status=200)
    except Exception as e:
        logger.exception("Webhook error")
        return Response("error", status=500)

# ================= STARTUP =================
async def setup():
    await telegram_app.initialize()
    await telegram_app.bot.delete_webhook(drop_pending_updates=True)
    await telegram_app.bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook set to {WEBHOOK_URL}")

def start_async_loop():
    loop.run_forever()

def main():
    # Start asyncio loop in background thread
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(start_async_loop)

    # Run async setup safely
    asyncio.run_coroutine_threadsafe(setup(), loop).result()

    # Start Flask (foreground process)
    app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
