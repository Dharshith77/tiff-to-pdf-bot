import os
import logging
import threading
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from PIL import Image
from flask import Flask
import asyncio
import nest_asyncio
import time

nest_asyncio.apply()

BOT_TOKEN = '7877725710:AAFiMMS9u56P911eODywMaVPRNIkL26_Jrk'  # replace with your bot token
app_flask = Flask('')


@app_flask.route('/')
def home():
    return "TIFF to PDF bot is alive!"


def keep_alive():
    app_flask.run(host='0.0.0.0', port=8081)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Send me a TIFF file and I'll convert it to PDF!")


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document

    if not document.file_name.lower().endswith('.tiff'):
        return  # Not a TIFF file, ignore

    # File paths
    file_id = document.file_id
    file_name = document.file_name
    display_name = os.path.splitext(file_name)[0]
    tiff_path = f"{file_id}.tiff"
    pdf_path = f"{file_id}.pdf"
    flag_path = f"{file_id}.flag"

    # Download the file
    new_file = await context.bot.get_file(file_id)
    await new_file.download_to_drive(tiff_path)
    logging.info(f"✅ TIFF downloaded: {tiff_path}")

    # Create a flag to track processing
    with open(flag_path, "w") as f:
        f.write(str(update.effective_chat.id))

    # Run conversion in background
    loop = asyncio.get_running_loop()
    threading.Thread(target=handle_conversion, args=(
        tiff_path, pdf_path, update.effective_chat.id, context.bot, loop, display_name, flag_path
    )).start()


def handle_conversion(tiff_path, pdf_path, chat_id, bot, loop, display_name, flag_path):
    try:
        image = Image.open(tiff_path)

        # Load all frames
        frames = []
        try:
            while True:
                frames.append(image.copy())
                image.seek(len(frames))
        except EOFError:
            pass

        # Save as multi-page PDF
        if frames:
            frames[0].save(
                pdf_path,
                save_all=True,
                append_images=frames[1:],
                resolution=100.0
            )
            logging.info(f"📄 PDF created: {pdf_path}")

            # Send PDF to user
            asyncio.run_coroutine_threadsafe(
                bot.send_document(chat_id=chat_id, document=open(pdf_path, 'rb'), filename=f"{display_name}.pdf", caption="Sunil, Here is your PDF 📄"),
                loop
            ).result()
        else:
            raise Exception("TIFF file has no readable frames.")

    except Exception as e:
        logging.error(f"❌ Error during conversion: {e}")
        asyncio.run_coroutine_threadsafe(
            bot.send_message(chat_id=chat_id, text="Something went wrong while converting the file."),
            loop
        ).result()

    finally:
        for file in [tiff_path, pdf_path, flag_path]:
            if os.path.exists(file):
                os.remove(file)

def check_crash_recovery():
    """If there's any leftover flag file, notify the user that the process was interrupted."""
    for file in os.listdir():
        if file.endswith('.flag'):
            try:
                with open(file, 'r') as f:
                    chat_id = int(f.read().strip())
                logging.warning(f"⚠️ Detected interrupted session for chat_id {chat_id}")
                os.remove(file)
                asyncio.run(application.bot.send_message(chat_id=chat_id,
                                                         text="Sorry, something went wrong before I could send your PDF. Please try again."))
            except Exception as e:
                logging.error(f"Error handling crash recovery: {e}")


def main():
    global application
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    # Start Flask keep-alive in background
    threading.Thread(target=keep_alive, daemon=True).start()

    # Handle crash recovery
    check_crash_recovery()

    logging.info("🔄 Starting bot...")
    application.run_polling()


if __name__ == '__main__':
    main()
