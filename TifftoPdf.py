import os
import threading
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from PIL import Image
from keep_alive import keep_alive

# Logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# Your bot token from BotFather
BOT_TOKEN = "7877725710:AAFiMMS9u56P911eODywMaVPRNIkL26_Jrk"  # 🔁 Replace this!

# Function to convert TIFF to PDF
def convert_tiff_to_pdf(tiff_path, pdf_path):
    Image.MAX_IMAGE_PIXELS = None  # Prevents DecompressionBombError
    images = []
    try:
        with Image.open(tiff_path) as img:
            while True:
                images.append(img.copy().convert("RGB"))
                img.seek(img.tell() + 1)
    except EOFError:
        pass

    if images:
        images[0].save(pdf_path, save_all=True, append_images=images[1:])

# Run conversion and send result in background
def handle_conversion(tiff_path, pdf_path, chat_id, context: ContextTypes.DEFAULT_TYPE):
    try:
        convert_tiff_to_pdf(tiff_path, pdf_path)
        context.bot.send_document(chat_id=chat_id, document=open(pdf_path, 'rb'))
        logging.info("✅ PDF sent.")
    except Exception as e:
        logging.error(f"❌ Conversion error: {e}")
        context.bot.send_message(chat_id=chat_id, text="⚠️ Something went wrong during conversion.")
    finally:
        if os.path.exists(tiff_path):
            os.remove(tiff_path)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        logging.info("🧹 Cleaned up temporary files.")

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me a TIFF file and I’ll convert it to PDF!")

# Handle TIFF file upload
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document or not update.message.document.file_name.lower().endswith(".tiff"):
        await update.message.reply_text("⚠️ Please send a `.tiff` file.")
        return

    await update.message.reply_text("📥 Downloading your TIFF file...")
    file = await context.bot.get_file(update.message.document.file_id)

    tiff_path = f"{update.message.document.file_unique_id}.tiff"
    pdf_path = f"{update.message.document.file_unique_id}.pdf"
    await file.download_to_drive(tiff_path)
    logging.info(f"✅ Downloaded TIFF: {tiff_path}")

    await update.message.reply_text("⏳ Converting TIFF to PDF. Please wait...")

    # Run conversion in background
    threading.Thread(target=handle_conversion, args=(tiff_path, pdf_path, update.effective_chat.id, context)).start()

# Main function
def main():
    keep_alive()  # Keeps the bot alive on Railway

    import nest_asyncio
    import asyncio
    nest_asyncio.apply()

    logging.info("🔄 Starting bot...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    asyncio.run(app.run_polling())

if __name__ == "__main__":
    main()
