import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from yt_dlp import YoutubeDL
import asyncio # Penting untuk operasi asinkron

# Muat variabel dari .env
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
FORCE_SUB_CHANNEL_ID = int(os.getenv("FORCE_SUB_CHANNEL_ID"))

# Inisialisasi bot Pyrogram
app = Client(
    "music_bot_session", # Nama sesi Anda, bisa apa saja
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

async def is_subscribed(client, user_id):
    """
    Fungsi untuk memeriksa apakah pengguna sudah subscribe channel.
    """
    try:
        member = await client.get_chat_member(FORCE_SUB_CHANNEL_ID, user_id)
        if member.status in ["member", "creator", "administrator"]:
            return True
        else:
            return False
    except Exception as e:
        # Penting: Jika bot bukan admin di channel atau channel ID salah,
        # maka get_chat_member akan gagal. Tangani error ini.
        print(f"Error checking subscription for user {user_id}: {e}")
        return False

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    user_id = message.from_user.id
    if not await is_subscribed(client, user_id):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Gabung Channel", url=f"https://t.me/c/{str(FORCE_SUB_CHANNEL_ID)[4:]}")]
        ])
        await message.reply_text(
            "Halo! 👋 Untuk menggunakan bot ini, Anda harus bergabung ke channel ini terlebih dahulu:",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        return

    await message.reply_text(
        "Selamat datang di Bot Musik! Gunakan /search <judul_lagu> untuk mencari musik."
    )

@app.on_message(filters.command("search") & filters.private)
async def search_music(client, message):
    user_id = message.from_user.id
    if not await is_subscribed(client, user_id):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Gabung Channel", url=f"https://t.me/c/{str(FORCE_SUB_CHANNEL_ID)[4:]}")]
        ])
        await message.reply_text(
            "Mohon maaf, Anda harus bergabung ke channel kami untuk mencari musik.",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        return

    if len(message.command) < 2:
        await message.reply_text("Penggunaan: `/search <judul_lagu>`")
        return

    query = " ".join(message.command[1:])
    msg = await message.reply_text(f"Mencari `{query}`... Mohon tunggu.")

    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': 'downloads/%(title)s.%(ext)s', # File akan disimpan di folder downloads
            'quiet': True,
            'noplaylist': True,
            'max_downloads': 1
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)
            if not info or not info['entries']:
                await msg.edit_text("Musik tidak ditemukan.")
                return

            video_info = info['entries'][0]
            title = video_info.get('title', 'Tidak diketahui')
            webpage_url = video_info.get('webpage_url')
            duration_sec = video_info.get('duration', 0)
            minutes, seconds = divmod(duration_sec, 60)
            duration_str = f"{minutes:02}:{seconds:02}"

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Unduh 🎵", callback_data=f"download_{webpage_url}")]
            ])
            await msg.edit_text(
                f"**Judul:** `{title}`\n**Durasi:** `{duration_str}`\n\nKlik Unduh untuk mendapatkan musik.",
                reply_markup=keyboard
            )

    except Exception as e:
        await msg.edit_text(f"Terjadi kesalahan saat mencari musik: `{e}`")


@app.on_callback_query()
async def callback_handler(client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id

    # Periksa langganan setiap kali ada callback query
    if not await is_subscribed(client, user_id):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Gabung Channel", url=f"https://t.me/c/{str(FORCE_SUB_CHANNEL_ID)[4:]}")]
        ])
        await callback_query.message.reply_text(
            "Mohon maaf, Anda harus bergabung ke channel kami untuk mengunduh musik.",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        await callback_query.answer("Anda belum subscribe channel kami!")
        return

    if data.startswith("download_"):
        url = data.replace("download_", "")

        # Hapus tombol dan beritahu pengguna sedang mengunduh
        await callback_query.edit_message_reply_markup(reply_markup=None) 
        status_msg = await callback_query.message.reply_text("Mengunduh musik, mohon tunggu...")

        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': 'downloads/%(title)s.%(ext)s',
                'quiet': True,
                'noplaylist': True,
                'max_downloads': 1
            }

            # Pastikan folder downloads ada (meskipun tidak di-upload ke GitHub)
            if not os.path.exists('downloads'):
                os.makedirs('downloads')

            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)

                await status_msg.edit_text(f"Mengunggah `{info.get('title', 'musik')}`...")
                await client.send_audio(
                    chat_id=callback_query.message.chat.id,
                    audio=file_path,
                    caption=f"🎵 **{info.get('title', 'Musik Anda')}**\n\nDiunduh untuk Anda!"
                )
                await status_msg.delete() # Hapus pesan status
                os.remove(file_path) # Hapus file lokal setelah dikirim
        except Exception as e:
            await status_msg.edit_text(f"Gagal mengunduh musik: `{e}`")

        await callback_query.answer("Unduhan selesai!")


# Jalankan bot
print("Bot sedang berjalan...")
app.run()
