import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from PIL import Image

# Replace with your bot token
BOT_TOKEN = "7877725710:AAFiMMS9u56P911eODywMaVPRNIkL26_Jrk"

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Hello! Send me a TIFF file, and I'll convert it to a PDF for you.")

async def handle_tiff(update: Update, context: CallbackContext) -> None:
    file = update.message.document

    if not file.mime_type.startswith("image/tiff"):
        await update.message.reply_text("Please send a valid TIFF file.")
        return

    original_filename = os.path.splitext(file.file_name)[0]
    tiff_path = f"{original_filename}.tiff"
    pdf_path = f"{original_filename}.pdf"

    new_file = await context.bot.get_file(file.file_id)
    await new_file.download_to_drive(tiff_path)

    try:
        # Open TIFF in a separate process to avoid file locks
        with Image.open(tiff_path) as image:
            if hasattr(image, "n_frames") and image.n_frames > 1:
                image_list = [image.convert("RGB") for i in range(image.n_frames)]
                image_list[0].save(pdf_path, save_all=True, append_images=image_list[1:])
            else:
                image.convert("RGB").save(pdf_path, "PDF", resolution=100.0)

        # Send the PDF with increased timeout
        with open(pdf_path, "rb") as pdf_file:
            await context.bot.send_document(
                chat_id=update.message.chat_id,
                document=pdf_file,
                filename=f"{original_filename}.pdf",
                caption="Here is your converted PDF!"
)

            

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

    finally:
        # Ensure file is closed before deleting
        if os.path.exists(tiff_path):
            os.remove(tiff_path)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

def main():
    app = Application.builder().token(BOT_TOKEN).read_timeout(120).write_timeout(120).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.MimeType("image/tiff"), handle_tiff))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
