# 🖼️ TIFF to PDF Converter Telegram Bot

This project is a **Telegram bot** that automatically converts `.tiff` or `.tif` image files to PDF format. Simply upload a TIFF file to the bot, and it will instantly return a downloadable PDF—no extra steps, no delays.

## 🚀 Features

- Accepts `.tiff` and `.tif` file formats
- Converts to high-quality `.pdf` files
- Instant response with the converted file
- Minimalistic and user-friendly
- Runs 24/7 using Railway free tier

## 🛠️ Tech Stack

- **Python**
- **pyrogram** for Telegram Bot API
- **Pillow** for image processing
- **Railway** for deployment

## 📦 How It Works

1. User sends a `.tiff` file to the bot
2. Bot downloads the file and converts it to a PDF using Pillow
3. The PDF is sent back to the user immediately—no waiting messages or fluff

## 🧾 Example
- User: 📤 uploads image.tiff
- Bot: 📥 responds instantly with image.pdf

## 📡 Deployment

The bot is deployed on [Railway](https://railway.app/), ensuring it's always up and running on the free plan.
