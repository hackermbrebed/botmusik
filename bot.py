import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from yt_dlp import YoutubeDL
from pytgcalls import PyTgCalls, idle
from pytgcalls.types import AudioPiped, AudioVideoPiped
from pytgcalls.exceptions import No
import traceback # Untuk menampilkan error lebih detail

# Muat variabel dari .env
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
FORCE_SUB_CHANNEL_ID = int(os.getenv("FORCE_SUB_CHANNEL_ID"))

# Inisialisasi bot Pyrogram
app = Client(
    "music_bot_session", # Nama sesi Anda
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Inisialisasi PyTgCalls
# Nama sesi userbot ini harus unik dan berbeda dari sesi bot utama
# Pastikan API_ID dan API_HASH sama dengan yang digunakan di Client utama
call_py = PyTgCalls(app)

# Dictionary untuk menyimpan antrean musik per grup/chat
# Ini adalah implementasi antrean yang sangat sederhana.
# Untuk bot produksi, disarankan menggunakan database atau struktur data yang lebih kompleks.
music_queue = {}

async def is_subscribed(client, user_id):
    """
    Fungsi untuk memeriksa apakah pengguna sudah subscribe channel atau belum.
    """
    try:
        member = await client.get_chat_member(FORCE_SUB_CHANNEL_ID, user_id)
        if member.status in ["member", "creator", "administrator"]:
            return True
        else:
            return False
    except Exception as e:
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
        "Selamat datang di Bot Musik Voice Chat! Gunakan:\n"
        "`/search <judul_lagu>`: Untuk mencari musik.\n"
        "`/join`: Untuk bot bergabung ke obrolan suara.\n"
        "`/play <url_musik>`: Untuk memutar musik dari URL (setelah bot bergabung).\n"
        "`/leave`: Untuk bot meninggalkan obrolan suara.\n"
        "`/stop`: Untuk menghentikan pemutaran dan meninggalkan obrolan suara."
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
            title = video_info['title']
            webpage_url = video_info['webpage_url']
            duration_sec = video_info.get('duration', 0)
            minutes, seconds = divmod(duration_sec, 60)
            duration_str = f"{minutes:02}:{seconds:02}"

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Play Voice Chat 🎵", callback_data=f"playvc_{webpage_url}"),
                 InlineKeyboardButton("Unduh 💾", callback_data=f"download_{webpage_url}")]
            ])
            await msg.edit_text(
                f"**Judul:** `{title}`\n**Durasi:** `{duration_str}`\n\nKlik 'Play Voice Chat' untuk memutar di VC atau 'Unduh' untuk mendapatkan file.",
                reply_markup=keyboard
            )

    except Exception as e:
        await msg.edit_text(f"Terjadi kesalahan saat mencari musik: `{e}`")

@app.on_message(filters.command("join") & filters.group)
async def join_vc(client, message):
    user_id = message.from_user.id
    if not await is_subscribed(client, user_id):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Gabung Channel", url=f"https://t.me/c/{str(FORCE_SUB_CHANNEL_ID)[4:]}")]
        ])
        await message.reply_text(
            "Mohon maaf, Anda harus bergabung ke channel kami untuk menggunakan bot ini.",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        return

    chat_id = message.chat.id
    try:
        await call_py.join_group_call(
            chat_id,
            AudioPiped("input.raw"), # Ini hanya placeholder, akan diganti saat play
        )
        await message.reply_text("Bot telah bergabung ke obrolan suara.")
    except No:
        await message.reply_text("Tidak ada obrolan suara yang aktif di grup ini.")
    except Exception as e:
        await message.reply_text(f"Gagal bergabung ke obrolan suara: `{e}`")
        traceback.print_exc() # Untuk debug

@app.on_message(filters.command("play") & filters.group)
async def play_music(client, message):
    user_id = message.from_user.id
    if not await is_subscribed(client, user_id):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Gabung Channel", url=f"https://t.me/c/{str(FORCE_SUB_CHANNEL_ID)[4:]}")]
        ])
        await message.reply_text(
            "Mohon maaf, Anda harus bergabung ke channel kami untuk memutar musik.",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        return

    chat_id = message.chat.id
    if len(message.command) < 2:
        await message.reply_text("Penggunaan: `/play <url_musik_youtube>`")
        return

    url = message.command[1]

    if chat_id not in music_queue:
        music_queue[chat_id] = []
    
    music_queue[chat_id].append(url)

    if await call_py.get_call(chat_id): # Jika bot sudah di VC
        if call_py.get_call(chat_id).is_playing:
            await message.reply_text(f"Musik ditambahkan ke antrean: `{url}`")
            return
    
    await message.reply_text(f"Mulai memutar musik dari antrean...")
    await start_play_queue(client, chat_id)

async def start_play_queue(client, chat_id):
    if not music_queue[chat_id]:
        await app.send_message(chat_id, "Antrean musik kosong. Meninggalkan obrolan suara...")
        await call_py.leave_group_call(chat_id)
        del music_queue[chat_id]
        return

    url = music_queue[chat_id][0] # Ambil musik pertama di antrean
    
    try:
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio', # Format terbaik untuk streaming ke VC
            'outtmpl': '-', # Mengirim output ke stdout
            'quiet': True,
            'noplaylist': True,
            'max_downloads': 1,
            'default_search': 'ytsearch',
            'cookiefile': None, # Penting jika ada masalah cookie yt-dlp
            'allow_playlist_files': False, # Pastikan tidak mengunduh playlist
            'verbose': False # Mode debug pytgcalls
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            # ydl.download([url]) # Tidak perlu download ke file
            info = ydl.extract_info(url, download=False)
            if not info:
                await app.send_message(chat_id, f"Gagal mendapatkan info musik dari URL: `{url}`. Melewati.")
                music_queue[chat_id].pop(0) # Hapus dari antrean
                await start_play_queue(client, chat_id) # Lanjut ke lagu berikutnya
                return

            title = info.get('title', 'Unknown Title')
            
            # Ini adalah bagian streaming langsung dari yt-dlp ke ffmpeg, lalu ke pytgcalls
            # Menggunakan - sebagai output yt-dlp dan input ffmpeg
            stream_url = info.get('url') # URL stream langsung, bukan webpage_url
            
            await app.send_message(chat_id, f"Memutar: `{title}`")
            
            await call_py.change_stream(
                chat_id,
                AudioPiped(stream_url) # Langsung streaming dari URL
            )
            # await call_py.send_audio_to_group_call(chat_id, AudioPiped(stream_url)) # Alternatif jika change_stream tidak bekerja

    except Exception as e:
        await app.send_message(chat_id, f"Terjadi kesalahan saat memutar musik `{url}`: `{e}`. Melewati.")
        music_queue[chat_id].pop(0) # Hapus dari antrean
        await start_play_queue(client, chat_id) # Lanjut ke lagu berikutnya
        traceback.print_exc()

@call_py.on_stream_end()
async def stream_end_handler(client, update):
    chat_id = update.chat_id
    if chat_id in music_queue:
        music_queue[chat_id].pop(0) # Hapus lagu yang selesai diputar
        await start_play_queue(client, chat_id) # Lanjut ke lagu berikutnya

@app.on_message(filters.command("leave") & filters.group)
async def leave_vc(client, message):
    user_id = message.from_user.id
    if not await is_subscribed(client, user_id):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Gabung Channel", url=f"https://t.me/c/{str(FORCE_SUB_CHANNEL_ID)[4:]}")]
        ])
        await message.reply_text(
            "Mohon maaf, Anda harus bergabung ke channel kami untuk menggunakan bot ini.",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        return

    chat_id = message.chat.id
    try:
        await call_py.leave_group_call(chat_id)
        if chat_id in music_queue:
            del music_queue[chat_id]
        await message.reply_text("Bot telah meninggalkan obrolan suara.")
    except No:
        await message.reply_text("Bot tidak sedang berada di obrolan suara.")
    except Exception as e:
        await message.reply_text(f"Gagal meninggalkan obrolan suara: `{e}`")
        traceback.print_exc()

@app.on_message(filters.command("stop") & filters.group)
async def stop_music(client, message):
    user_id = message.from_user.id
    if not await is_subscribed(client, user_id):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Gabung Channel", url=f"https://t.me/c/{str(FORCE_SUB_CHANNEL_ID)[4:]}")]
        ])
        await message.reply_text(
            "Mohon maaf, Anda harus bergabung ke channel kami untuk menggunakan bot ini.",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        return

    chat_id = message.chat.id
    try:
        await call_py.leave_group_call(chat_id)
        if chat_id in music_queue:
            del music_queue[chat_id]
        await message.reply_text("Pemutaran musik dihentikan dan bot meninggalkan obrolan suara.")
    except No:
        await message.reply_text("Bot tidak sedang memutar musik atau tidak di obrolan suara.")
    except Exception as e:
        await message.reply_text(f"Gagal menghentikan musik: `{e}`")
        traceback.print_exc()

@app.on_callback_query()
async def callback_handler(client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id
    
    # Periksa langganan setiap kali ada callback query
    if not await is_subscribed(client, user_id):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Gabung Channel", url=f"https://t.me/c/{str(FORCE_SUB_CHANNEL_ID)[4:]}")]
        ])
        await callback_query.message.reply_text(
            "Mohon maaf, Anda harus bergabung ke channel kami untuk menggunakan bot ini.",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        await callback_query.answer("Anda belum subscribe channel kami!")
        return

    # Hapus tombol setelah diklik untuk menghindari klik ganda
    await callback_query.edit_message_reply_markup(reply_markup=None) 

    if data.startswith("playvc_"):
        url = data.replace("playvc_", "")
        
        await callback_query.message.reply_text(f"Menyiapkan musik untuk Voice Chat dari `{url}`...")

        if chat_id not in music_queue:
            music_queue[chat_id] = []
        music_queue[chat_id].append(url)

        try:
            # Cek apakah bot sudah di VC, jika belum, gabung dulu
            try:
                await call_py.get_call(chat_id)
            except No: # Jika belum bergabung
                await call_py.join_group_call(chat_id, AudioPiped("input.raw")) # Placeholder
                await callback_query.message.reply_text("Bot bergabung ke obrolan suara.")
            
            # Jika sudah bergabung, atau baru bergabung, langsung play dari antrean
            await start_play_queue(client, chat_id)
            await callback_query.answer("Musik akan diputar di Voice Chat!")

        except Exception as e:
            await callback_query.message.reply_text(f"Gagal memutar di Voice Chat: `{e}`")
            traceback.print_exc()
            await callback_query.answer("Gagal memutar di Voice Chat!")

    elif data.startswith("download_"):
        url = data.replace("download_", "")
        
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
                await status_msg.delete()
                os.remove(file_path) # Hapus file lokal setelah dikirim
        except Exception as e:
            await status_msg.edit_text(f"Gagal mengunduh musik: `{e}`")
            traceback.print_exc()
        
        await callback_query.answer("Unduhan selesai!")

# Jalankan bot
async def main():
    print("Memulai bot...")
    await app.start()
    print("Bot utama berjalan.")
    await call_py.start() # Memulai klien PyTgCalls
    print("PyTgCalls berjalan.")
    await idle() # Biarkan bot berjalan sampai dihentikan secara manual
    print("Bot berhenti.")
    await app.stop()
    await call_py.stop()

if __name__ == "__main__":
    asyncio.run(main())
