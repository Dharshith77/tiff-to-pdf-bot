import os
import threading
import logging
import asyncio
import uuid
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

BOT_TOKEN = "7877725710:AAFiMMS9u56P911eODywMaVPRNIkL26_Jrk"  # Replace with your actual bot token

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
def handle_conversion(tiff_path, pdf_path, chat_id, bot, loop, display_name):
    try:
        convert_tiff_to_pdf(tiff_path, pdf_path)
        logging.info(f"✅ PDF created: {pdf_path}")

        with open(pdf_path, 'rb') as f:
            asyncio.run_coroutine_threadsafe(
                bot.send_document(chat_id=chat_id, document=f, filename=display_name),
                loop
            )
        logging.info("✅ PDF sent to user.")
    except Exception as e:
        logging.error(f"❌ Conversion error: {e}")
        asyncio.run_coroutine_threadsafe(
            bot.send_message(chat_id=chat_id, text=f"⚠️ Conversion failed: {e}"),
            loop
        )
    finally:
        for path in [tiff_path, pdf_path]:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    logging.info(f"🧹 Removed: {path}")
            except Exception as e:
                logging.warning(f"⚠️ Could not delete {path}: {e}")

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Just send me a `.tiff` file and I’ll reply with a PDF!")

# Handle TIFF uploads
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document or not update.message.document.file_name.lower().endswith(".tiff"):
        return  # silently ignore non-TIFF files

    original_filename = update.message.document.file_name
    base_filename = os.path.splitext(original_filename)[0]
    unique_suffix = uuid.uuid4().hex[:6]

    tiff_path = f"{base_filename}_{unique_suffix}.tiff"
    pdf_path = f"{base_filename}_{unique_suffix}.pdf"
    display_name = f"{base_filename}.pdf"

    file = await context.bot.get_file(update.message.document.file_id)
    await file.download_to_drive(tiff_path)
    logging.info(f"✅ TIFF downloaded: {tiff_path}")

    loop = asyncio.get_running_loop()  # ✅ Correct way to get the active loop

    # Run conversion in a new thread
    threading.Thread(target=handle_conversion, args=(
        tiff_path, pdf_path, update.effective_chat.id, context.bot, loop, display_name
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
