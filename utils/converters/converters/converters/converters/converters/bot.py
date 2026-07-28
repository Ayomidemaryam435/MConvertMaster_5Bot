import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from config import BOT_TOKEN, MAX_FILE_SIZE_MB
from utils.file_utils import new_job_id, job_path, cleanup
from converters.image_converter import convert_image
from converters.audio_converter import convert_audio
from converters.video_converter import convert_video
from converters.document_converter import convert_document

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# In-memory job store: job_id -> {"path": str, "category": str, "ext": str}
# NOTE: this resets if the bot restarts. Fine for a single-instance polling bot;
# swap for Redis/a DB if you ever run multiple replicas.
JOBS = {}

IMAGE_FORMATS = ["jpg", "png", "webp", "bmp", "pdf"]
AUDIO_FORMATS = ["mp3", "wav", "ogg", "flac", "m4a"]
VIDEO_FORMATS = ["mp4", "avi", "mov", "mkv", "gif", "mp3"]
DOCUMENT_FORMAT_MAP = {
    "pdf": ["docx", "txt"],
    "docx": ["pdf", "txt"],
    "doc": ["pdf"],
    "odt": ["pdf", "docx"],
    "txt": ["pdf", "docx"],
    "pptx": ["pdf"],
    "xlsx": ["pdf"],
    "rtf": ["pdf", "docx"],
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to ConvertMaster_5Bot!\n\n"
        "Send me a document, image, audio, or video file and I'll show you "
        "the formats I can convert it to.\n\n"
        f"Max file size: {MAX_FILE_SIZE_MB}MB\n"
        "Use /help to see supported formats."
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📄 Documents: pdf, docx, doc, odt, txt, pptx, xlsx, rtf\n"
        "🖼 Images: jpg, png, webp, bmp\n"
        "🎵 Audio: mp3, wav, ogg, flac, m4a\n"
        "🎬 Video: mp4, avi, mov, mkv (+ extract gif/mp3)\n\n"
        "Just send the file to get started."
    )


def _build_keyboard(job_id: str, formats: list, current_ext: str) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(f".{f}", callback_data=f"conv:{job_id}:{f}")
        for f in formats
        if f != current_ext
    ]
    rows = [buttons[i : i + 3] for i in range(0, len(buttons), 3)]
    return InlineKeyboardMarkup(rows)


async def _check_size(update: Update, file_size) -> bool:
    if file_size and file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        await update.message.reply_text(f"⚠️ File too large. Max is {MAX_FILE_SIZE_MB}MB.")
        return False
    return True


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not await _check_size(update, doc.file_size):
        return
    ext = doc.file_name.rsplit(".", 1)[-1].lower() if doc.file_name and "." in doc.file_name else ""
    if ext not in DOCUMENT_FORMAT_MAP:
        await update.message.reply_text(f"Sorry, .{ext or 'this'} files aren't supported yet.")
        return

    job_id = new_job_id()
    src_path = job_path(job_id, ext)
    tg_file = await doc.get_file()
    await tg_file.download_to_drive(src_path)

    JOBS[job_id] = {"path": src_path, "category": "document", "ext": ext}
    kb = _build_keyboard(job_id, DOCUMENT_FORMAT_MAP[ext], ext)
    await update.message.reply_text("Convert to:", reply_markup=kb)


async def handle_image_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Images sent as uncompressed files (Telegram "file" attachment, not photo)
    doc = update.message.document
    if not await _check_size(update, doc.file_size):
        return
    ext = doc.file_name.rsplit(".", 1)[-1].lower() if doc.file_name and "." in doc.file_name else "jpg"

    job_id = new_job_id()
    src_path = job_path(job_id, ext)
    tg_file = await doc.get_file()
    await tg_file.download_to_drive(src_path)

    JOBS[job_id] = {"path": src_path, "category": "image", "ext": ext}
    kb = _build_keyboard(job_id, IMAGE_FORMATS, ext)
    await update.message.reply_text("Convert to:", reply_markup=kb)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    if not await _check_size(update, photo.file_size):
        return

    job_id = new_job_id()
    src_path = job_path(job_id, "jpg")
    tg_file = await photo.get_file()
    await tg_file.download_to_drive(src_path)

    JOBS[job_id] = {"path": src_path, "category": "image", "ext": "jpg"}
    kb = _build_keyboard(job_id, IMAGE_FORMATS, "jpg")
    await update.message.reply_text("Convert to:", reply_markup=kb)


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    audio = update.message.audio or update.message.voice
    if not await _check_size(update, audio.file_size):
        return

    ext = "ogg" if update.message.voice else "mp3"
    if update.message.audio and update.message.audio.file_name and "." in update.message.audio.file_name:
        ext = update.message.audio.file_name.rsplit(".", 1)[-1].lower()

    job_id = new_job_id()
    src_path = job_path(job_id, ext)
    tg_file = await audio.get_file()
    await tg_file.download_to_drive(src_path)

    JOBS[job_id] = {"path": src_path, "category": "audio", "ext": ext}
    kb = _build_keyboard(job_id, AUDIO_FORMATS, ext)
    await update.message.reply_text("Convert to:", reply_markup=kb)


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video
    if not await _check_size(update, video.file_size):
        return

    job_id = new_job_id()
    src_path = job_path(job_id, "mp4")
    tg_file = await video.get_file()
    await tg_file.download_to_drive(src_path)

    JOBS[job_id] = {"path": src_path, "category": "video", "ext": "mp4"}
    kb = _build_keyboard(job_id, VIDEO_FORMATS, "mp4")
    await update.message.reply_text("Convert to:", reply_markup=kb)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        _, job_id, target_ext = query.data.split(":")
    except ValueError:
        return

    job = JOBS.get(job_id)
    if not job:
        await query.edit_message_text("⚠️ This file has expired. Please send it again.")
        return

    await query.edit_message_text(f"⏳ Converting to .{target_ext} ...")

    src_path = job["path"]
    category = job["category"]
    dst_path = job_path(job_id + "_out", target_ext)

    try:
        if category == "image":
            convert_image(src_path, dst_path, target_ext)
        elif category == "audio":
            convert_audio(src_path, dst_path, target_ext)
        elif category == "video":
            convert_video(src_path, dst_path, target_ext)
        elif category == "document":
            convert_document(src_path, dst_path, target_ext)
        else:
            raise RuntimeError("Unknown file category")

        with open(dst_path, "rb") as f:
            await query.message.reply_document(f, filename=f"converted.{target_ext}")
        await query.edit_message_text(f"✅ Done! Converted to .{target_ext}")

    except Exception as e:
        logger.exception("Conversion failed for job %s", job_id)
        await query.edit_message_text(f"❌ Conversion failed: {e}")

    finally:
        cleanup(dst_path, src_path)
        JOBS.pop(job_id, None)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Unhandled exception", exc_info=context.error)


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is not set")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.AUDIO | filters.VOICE, handle_audio))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.Document.IMAGE, handle_image_document))
    app.add_handler(MessageHandler(filters.Document.ALL & ~filters.Document.IMAGE, handle_document))
    app.add_handler(CallbackQueryHandler(handle_callback, pattern=r"^conv:"))
    app.add_error_handler(error_handler)

    logger.info("ConvertMaster_5Bot starting (polling mode)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
