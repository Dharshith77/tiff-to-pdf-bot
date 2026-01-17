import os
import logging
import asyncio
from io import BytesIO
from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from flask import Flask, request, Response
import nest_asyncio

nest_asyncio.apply()

BOT_TOKEN = os.environ['BOT_TOKEN']
WEBHOOK_URL = os.environ['WEBHOOK_URL']

app = Flask(__name__)

@app.route('/')
def home():
    return "TIFF to PDF bot is alive!"

# Telegram handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Send me a TIFF file and I'll convert it to PDF!")

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document.file_name.lower().endswith('.tiff'):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Please send a TIFF file only.")
        return

    file_id = document.file_id
    file_name = document.file_name
    display_name = os.path.splitext(file_name)[0]
    tiff_path = f"{file_id}.tiff"
    pdf_path = f"{file_id}.pdf"

    new_file = await context.bot.get_file(file_id)
    await new_file.download_to_drive(tiff_path)
    logging.info(f"✅ TIFF downloaded: {tiff_path}")

    try:
        image = Image.open(tiff_path)
        frames = []
        try:
            while True:
                frames.append(image.copy())
                image.seek(len(frames))
        except EOFError:
            pass

        frames[0].save(pdf_path, save_all=True, append_images=frames[1:], resolution=100.0)
        logging.info(f"📄 PDF created: {pdf_path}")

        with open(pdf_path, 'rb') as f:
            file_data = BytesIO(f.read())
            file_data.name = f"{display_name}.pdf"
            await context.bot.send_document(chat_id=update.effective_chat.id, document=file_data, caption="Here is your PDF 📄")
    except Exception as e:
        logging.error(f"❌ Error: {e}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Something went wrong while converting the file.")
    finally:
        for file in [tiff_path, pdf_path]:
            if os.path.exists(file):
                os.remove(file)

# Initialize bot
application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.Document.ALL, handle_file))

# Flask webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.get_event_loop().create_task(application.process_update(update))
    return Response("ok", status=200)

# Set webhook on startup
async def setup_webhook():
    await application.bot.delete_webhook()
    await application.bot.set_webhook(WEBHOOK_URL)
    logging.info(f"🚀 Webhook set to {WEBHOOK_URL}")

asyncio.run(setup_webhook())
