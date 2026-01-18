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

# ================= CONFIG =================
BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
PORT = int(os.environ.get("PORT", 8080))

logging.basicConfig(level=logging.INFO)

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
        logging.error(e)
        await update.message.reply_text(
            "Something went wrong while converting the file."
        )

    finally:
        for f in (tiff_path, pdf_path):
