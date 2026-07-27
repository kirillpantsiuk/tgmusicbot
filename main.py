import os
import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
import yt_dlp

logging.basicConfig(level=logging.INFO)

# Твої актуальні дані бота
BOT_TOKEN = "8915515037:AAEXAqq_WuZSv0wVuLzlmscXpbV-jzeCkr4"
BOT_USERNAME = "Mus1cassistant_bot"
LOGO_URL = "https://drive.google.com/uc?id=1NaUW0Q0bMp8rYniDN3gYpTGfGNSteMwS"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Локальна база даних в пам'яті
user_xp = {}
user_names = {}
creator_data = {"creator_xp": 750}
active_quizzes = {}

i18n = {
    "uk": {
        "menu": "🎛 <b>Головне меню</b>\nОбери дію нижче:",
        "btn_quiz": "🎮 Вгадай мелодію",
        "btn_xp": "🌟 Мій досвід",
        "btn_creator": "👑 Досвід творця",
        "btn_leaderboard": "🏆 Топ гравців",
        "xp_zero": "У тебе поки 0 XP 😢. Тисни «Вгадай мелодію», щоб заробити бали!",
        "xp_amount": "Твій музичний досвід: <b>{xp} XP</b> 🌟",
        "creator_xp": "Опыт создателя: <b>{xp} XP</b> 👑\nПроєкт розроблено на Python + yt-dlp!",
        "quiz_start": "🎧 <b>Слухай уривок (30 сек)!</b> Що це за пісня?",
        "quiz_win": "🎉 <b>Правильно!</b> {name} отримує +50 XP!\n🎵 Пісня: {track}",
        "quiz_lose": "❌ Неправильно!",
        "quiz_late": "⏳ Халепа! Хтось вже вгадав цю пісню.",
        "welcome": (
            "👋 <b>Привіт! Я твій музичний бот-помічник.</b>\n"
            "Працюю як в <b>особистих повідомленнях</b>, так і в <b>групових чатах</b>!\n\n"
            "📖 <b>ЯК КОРИСТУВАТИСЯ:</b>\n"
            "🎵 <b>Пошук повних треків (MP3):</b>\n"
            "• Напиши: <code>/search [назва]</code> або у чаті: <i>«знайди пісню metallica»</i>\n\n"
            "🎮 <b>Музична вікторина:</b>\n"
            "• Напиши у чаті: <i>«запусти музичну гру»</i> або <i>«вгадай мелодію»</i>"
        )
    }
}

def download_audio(query: str):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'default_search': 'ytsearch1',
        'noplaylist': True,
        'quiet': True,
    }
    os.makedirs('downloads', exist_ok=True)
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)
            if 'entries' in info:
                info = info['entries'][0]
            file_path = ydl.prepare_filename(info)
            base, _ = os.path.splitext(file_path)
            return {
                'path': base + ".mp3",
                'title': info.get('title', 'Unknown Title'),
                'uploader': info.get('uploader', 'Unknown Artist')
            }
    except Exception as e:
        logging.error(f"Download error: {e}")
        return None

async def process_music_search(message: Message, query: str):
    status_msg = await message.answer(f"🔍 Шукаю повну версію за запитом: <b>{query}</b>...", parse_mode="HTML")
    loop = asyncio.get_event_loop()
    track_info = await loop.run_in_executor(None, download_audio, query)
    
    if track_info and os.path.exists(track_info['path']):
        try:
            audio_file = FSInputFile(track_info['path'])
            await message.answer_audio(
                audio=audio_file,
                title=track_info['title'],
                performer=track_info['uploader'],
                caption=f"🎵 <b>{track_info['title']}</b>\n👤 <b>Виконавець:</b> {track_info['uploader']}",
                parse_mode="HTML"
            )
            await status_msg.delete()
        except Exception as e:
            logging.error(f"Send audio error: {e}")
            await status_msg.edit_text("❌ Сталася помилка при відправці аудіофайлу.")
        finally:
            if os.path.exists(track_info['path']):
                os.remove(track_info['path'])
    else:
        await status_msg.edit_text(f"❌ За запитом «<b>{query}</b>» нічого не знайдено.", parse_mode="HTML")

def get_menu_keyboard():
    t = i18n["uk"]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["btn_quiz"], callback_data="start_quiz")],
        [InlineKeyboardButton(text=t["btn_xp"], callback_data="show_my_xp"),
         InlineKeyboardButton(text=t["btn_creator"], callback_data="show_creator_xp")],
        [InlineKeyboardButton(text=t["btn_leaderboard"], callback_data="show_leaderboard")]
    ])

@dp.message(Command("start", "help"))
async def cmd_start(message: Message):
    add_url = f"https://t.me/{BOT_USERNAME}?startgroup=true&admin=change_info+delete_messages"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Додати бота в групу", url=add_url)],
        [InlineKeyboardButton(text="🎮 Меню та рейтинг", callback_data="open_menu")]
    ])
    await message.answer_photo(
        photo=LOGO_URL,
        caption=i18n["uk"]["welcome"],
        parse_mode="HTML",
        reply_markup=keyboard
    )

@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    await message.answer(i18n["uk"]["menu"], parse_mode="HTML", reply_markup=get_menu_keyboard())

@dp.message(Command("quiz"))
async def cmd_quiz(message: Message):
    await start_quiz(message.chat.id)

@dp.message(Command("trends"))
async def cmd_trends(message: Message):
    trends_text = (
        "🔥 <b>Популярні музичні напрямки та категорії:</b>\n\n"
        "1. 🎸 <b>Rock / Metal</b> (Metallica, Linkin Park, AC/DC)\n"
        "2. ⚡ <b>Pop / Hits</b> (The Weeknd, Dua Lipa, Billie Eilish)\n"
        "3. 🎧 <b>Electronic / Dance</b> (Daft Punk, Avicii, David Guetta)\n"
        "4. 🎤 <b>Ukrainian Pop & Rock</b> (Океан Ельзи, Бумбокс, SKOFKA)"
    )
    await message.answer(trends_text, parse_mode="HTML")

@dp.message(F.text.regexp(r"^/(search|шукай)(@\w+)?\s+(.+)"))
async def cmd_search(message: Message):
    text_parts = message.text.split(maxsplit=1)
    if len(text_parts) > 1:
        await process_music_search(message, text_parts[1].strip())

@dp.message(F.text)
async def text_triggers(message: Message):
    if not message.text:
        return
    text = message.text.strip()
    lower_text = text.lower()
    
    quiz_triggers = ["запусти музичну гру", "вгадай мелодію", "грати у вікторину", "запусти игру", "угадай мелодию"]
    if any(qt in lower_text for qt in quiz_triggers):
        await start_quiz(message.chat.id)
        return

    search_triggers = ["хочу знайти пісню", "знайди пісню", "хочу найти песню", "найди песню"]
    found = next((t for t in search_triggers if t in lower_text), None)
    if found:
        query = text[lower_text.index(found) + len(found):].strip()
        if query:
            await process_music_search(message, query)

@dp.callback_query(F.data == "start_quiz")
async def cb_start_quiz(callback: CallbackQuery):
    await start_quiz(callback.message.chat.id)
    await callback.answer("Запускаю гру...")

@dp.callback_query(F.data == "open_menu")
async def cb_open_menu(callback: CallbackQuery):
    await callback.message.answer(i18n["uk"]["menu"], parse_mode="HTML", reply_markup=get_menu_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "show_my_xp")
async def cb_my_xp(callback: CallbackQuery):
    uid = callback.from_user.id
    xp = user_xp.get(uid, 0)
    text = i18n["uk"]["xp_zero"] if xp == 0 else i18n["uk"]["xp_amount"].replace("{xp}", str(xp))
    await callback.answer(text, show_alert=True)

@dp.callback_query(F.data == "show_creator_xp")
async def cb_creator_xp(callback: CallbackQuery):
    cXp = creator_data.get("creator_xp", 500)
    text = i18n["uk"]["creator_xp"].replace("{xp}", str(cXp))
    await callback.answer(text, show_alert=True)

@dp.callback_query(F.data == "show_leaderboard")
async def cb_leaderboard(callback: CallbackQuery):
    if not user_xp:
        await callback.answer("У рейтингу поки немає гравців. Зіграйте у вікторину!", show_alert=True)
        return
    
    sorted_users = sorted(user_xp.items(), key=lambda x: x[1], reverse=True)[:5]
    lb_text = "🏆 <b>Топ музичних знавців:</b>\n\n"
    for idx, (uid, xp) in enumerate(sorted_users, 1):
        name = user_names.get(uid, f"Гравець {uid}")
        lb_text += f"{idx}. <b>{name}</b> — {xp} XP 🌟\n"
    
    await callback.answer(lb_text, show_alert=True)

@dp.callback_query(F.data.startswith("qz_"))
async def cb_quiz_answer(callback: CallbackQuery):
    msg_id = callback.message.message_id
    if msg_id not in active_quizzes:
        await callback.answer(i18n["uk"]["quiz_late"], show_alert=True)
        return
    
    action = callback.data.split("_")[1]
    if action == "correct":
        correct_track = active_quizzes.pop(msg_id)
        uid = callback.from_user.id
        name = callback.from_user.first_name
        
        user_names[uid] = name
        user_xp[uid] = user_xp.get(uid, 0) + 50
        creator_data["creator_xp"] += 10
        
        win_text = i18n["uk"]["quiz_win"].replace("{name}", name).replace("{track}", correct_track)
        await callback.message.edit_caption(caption=win_text, parse_mode="HTML")
    else:
        await callback.answer(i18n["uk"]["quiz_lose"], show_alert=False)

async def start_quiz(chat_id: int):
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.deezer.com/search?q=rock&limit=15") as resp:
                data = await resp.json()
                if "data" not in data or len(data["data"]) < 4:
                    return
                
                tracks = random.sample(data["data"], 4)
                correct = tracks[0]
                random.shuffle(tracks)
                
                keyboard_rows = []
                for tr in tracks:
                    is_corr = (tr["id"] == correct["id"])
                    keyboard_rows.append([
                        InlineKeyboardButton(
                            text=f"{tr['artist']['name']} - {tr['title']}",
                            callback_data=f"qz_{'correct' if is_corr else 'wrong'}"
                        )
                    ])
                
                msg = await bot.send_audio(
                    chat_id=chat_id,
                    audio=correct["preview"],
                    title="???",
                    performer="???",
                    caption=i18n["uk"]["quiz_start"],
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
                )
                active_quizzes[msg.message_id] = f"{correct['artist']['name']} - {correct['title']}"
    except Exception as e:
        logging.error(f"Quiz start error: {e}")

async def main():
    print("Python Bot started successfully with token configuration...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())