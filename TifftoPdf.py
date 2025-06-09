import os
import logging
import asyncio
from io import BytesIO
from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import time

BOT_TOKEN = os.getenv("7877725710:AAFiMMS9u56P911eODywMaVPRNIkL26_Jrk")  # Securely fetched from Render env vars

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Send me a TIFF file and I'll convert it to PDF!")

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document

    if not document.file_name.lower().endswith('.tiff'):
        return

    file_id = document.file_id
    file_name = document.file_name
    display_name = os.path.splitext(file_name)[0]
    tiff_path = f"{file_id}.tiff"
    pdf_path = f"{file_id}.pdf"
    flag_path = f"{file_id}.flag"

    new_file = await context.bot.get_file(file_id)
    await new_file.download_to_drive(tiff_path)
    logging.info(f"✅ TIFF downloaded: {tiff_path}")

    with open(flag_path, "w") as f:
        f.write(str(update.effective_chat.id))

    await handle_conversion_async(tiff_path, pdf_path, update.effective_chat.id, context.bot, display_name, flag_path)

async def handle_conversion_async(tiff_path, pdf_path, chat_id, bot, display_name, flag_path):
    try:
        image = Image.open(tiff_path)

        frames = []
        try:
            while True:
                frames.append(image.copy())
                image.seek(len(frames))
        except EOFError:
            pass

        if frames:
            frames[0].save(
                pdf_path,
                save_all=True,
                append_images=frames[1:],
                resolution=100.0
            )
            logging.info(f"📄 PDF created: {pdf_path}")

            if os.path.exists(pdf_path):
                with open(pdf_path, 'rb') as pdf_file:
                    file_data = BytesIO(pdf_file.read())
                    file_data.name = f"{display_name}.pdf"
                    await bot.send_document(chat_id=chat_id, document=file_data, caption="Here is your PDF 📄")
            else:
                logging.error("PDF file not found")
                await bot.send_message(chat_id=chat_id, text="Something went wrong while converting the file.")
        else:
            raise Exception("TIFF file has no readable frames.")
    except Exception as e:
        logging.error(f"❌ Error during conversion: {e}")
        await bot.send_message(chat_id=chat_id, text="Something went wrong while converting the file.")
    finally:
        for file in [tiff_path, pdf_path, flag_path]:
            if os.path.exists(file):
                os.remove(file)
                logging.info(f"🧹 Removed temporary file: {file}")

def check_crash_recovery(application):
    for file in os.listdir():
        if file.endswith('.flag'):
            try:
                with open(file, 'r') as f:
                    chat_id = int(f.read().strip())
                os.remove(file)
                asyncio.run(application.bot.send_message(chat_id=chat_id, text="Sorry, something went wrong before I could send your PDF. Please try again."))
            except Exception as e:
                logging.error(f"Recovery error: {e}")

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    check_crash_recovery(application)

    logging.info("🤖 Bot running with polling...")
    application.run_polling()

if __name__ == '__main__':
    main()
