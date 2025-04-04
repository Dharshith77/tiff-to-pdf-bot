import os
import threading
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from PIL import Image
from keep_alive import keep_alive  # Keeps Railway service alive

# ✅ Enable detailed logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# 🤖 Your Telegram Bot Token
BOT_TOKEN = "7877725710:AAFiMMS9u56P911eODywMaVPRNIkL26_Jrk"  # 🔁 Replace with your actual token

# 📄 Function to convert TIFF to PDF
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

# 🔁 Background handler for conversion and response
def handle_conversion(tiff_path, pdf_path, chat_id, context: ContextTypes.DEFAULT_TYPE):
    try:
        convert_tiff_to_pdf(tiff_path, pdf_path)
        context.bot.send_document(chat_id=chat_id, document=open(pdf_path, 'rb'))
        logging.info("✅ PDF sent.")
    except Exception as e:
        logging.error(f"❌ Conversion error: {e}")
        context.bot.send_message(chat_id=chat_id, text="⚠️ Something went wrong during conversion.")
    finally:
        for path in [tiff_path, pdf_path]:
            if os.path.exists(path):
                os.remove(path)
        logging.info("🧹 Temp files cleaned up.")

# 🧃 Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me a `.tiff` file and I’ll convert it to PDF!")

# 📎 Handler for document uploads
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document or not document.file_name.lower().endswith(".tiff"):
        await update.message.reply_text("⚠️ Please send a valid `.tiff` file.")
        return

    await update.message.reply_text("📥 Downloading your TIFF file...")
    file = await context.bot.get_file(document.file_id)

    tiff_path = f"{document.file_unique_id}.tiff"
    pdf_path = f"{document.file_unique_id}.pdf"
    await file.download_to_drive(tiff_path)

    logging.info(f"✅ Downloaded: {tiff_path}")
    await update.message.reply_text("⏳ Converting TIFF to PDF...")

    # Start conversion in background
    threading.Thread(target=handle_conversion, args=(tiff_path, pdf_path, update.effective_chat.id, context)).start()

# 🚀 Main bot runner
async def main():
    keep_alive()  # 🔁 Keeps Railway service alive
    logging.info("🔄 Starting bot...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    await app.run_polling()

# 🏁 Start bot
if __name__ == "__main__":
    import asyncio
    import nest_asyncio
    nest_asyncio.apply()  # ✅ Fix: allows nested event loops

    keep_alive()

    asyncio.get_event_loop().run_until_complete(main())
