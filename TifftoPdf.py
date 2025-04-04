import os
import threading
import logging
import asyncio
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

BOT_TOKEN = "7877725710:AAFiMMS9u56P911eODywMaVPRNIkL26_Jrk"

# TIFF to PDF conversion
def convert_tiff_to_pdf(tiff_path, pdf_path):
    Image.MAX_IMAGE_PIXELS = None
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

# Threaded conversion and async sending
def handle_conversion(tiff_path, pdf_path, pdf_filename, chat_id, bot, loop):
    try:
        convert_tiff_to_pdf(tiff_path, pdf_path)
        asyncio.run_coroutine_threadsafe(
            bot.send_document(
                chat_id=chat_id,
                document=open(pdf_path, 'rb'),
                filename=pdf_filename  # Send with original name
            ),
            loop
        )
        logging.info("✅ PDF sent.")
    except Exception as e:
        logging.error(f"❌ Conversion error: {e}")
        asyncio.run_coroutine_threadsafe(
            bot.send_message(chat_id=chat_id, text="⚠️ Something went wrong during conversion."),
            loop
        )
    finally:
        if os.path.exists(tiff_path):
            os.remove(tiff_path)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        logging.info("🧹 Cleaned up files.")

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Just send me a `.tiff` file and I’ll reply with a PDF!")

# Handle TIFF uploads
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document or not update.message.document.file_name.lower().endswith(".tiff"):
        return  # silently ignore non-TIFF files

    file = await context.bot.get_file(update.message.document.file_id)

    original_filename = update.message.document.file_name  # e.g., image.tiff
    base_name = os.path.splitext(original_filename)[0]
    tiff_path = f"{base_name}.tiff"
    pdf_path = f"{base_name}.pdf"
    pdf_filename = f"{base_name}.pdf"

    await file.download_to_drive(tiff_path)
    logging.info(f"✅ TIFF downloaded: {tiff_path}")

    # Start conversion in a thread
    threading.Thread(target=handle_conversion, args=(
        tiff_path, pdf_path, pdf_filename, update.effective_chat.id, context.bot, asyncio.get_running_loop()
    )).start()

# Main function
def main():
    keep_alive()  # Keeps Railway container alive

    import nest_asyncio
    nest_asyncio.apply()

    logging.info("🔄 Starting bot...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    import asyncio
    asyncio.run(app.run_polling())

if __name__ == "__main__":
    main()
