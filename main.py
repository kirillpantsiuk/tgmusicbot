import os
import asyncio
import logging
import random
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
import yt_dlp
from dotenv import load_dotenv

# Завантажуємо локальний .env файл (якщо він є)
load_dotenv()

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME", "Mus1cassistant_bot")
LOGO_URL = "https://drive.google.com/uc?id=1NaUW0Q0bMp8rYniDN3gYpTGfGNSteMwS"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Локальна база даних в пам'яті
user_xp = {}
user_names = {}
creator_data = {"creator_xp": 750}
active_text_quizzes = {}

i18n = {
    "uk": {
        "menu": "🎛 <b>Головне меню</b>\nОбери дію нижче:",
        "btn_quiz": "🎮 Вгадай мелодію",
        "btn_xp": "🌟 Мій досвід",
        "btn_creator": "👑 Досвід творця",
        "btn_leaderboard": "🏆 Топ гравців",
        "xp_zero": "У тебе поки 0 XP 😢. Тисни «Вгадай мелодію», щоб заробити бали!",
        "xp_amount": "Твій музичний досвід: <b>{xp} XP</b> 🌟",
        "creator_xp": "Досвід творця: <b>{xp} XP</b> 👑\nПроєкт розроблено на Python + yt-dlp!",
        "quiz_choose": "🎮 <b>Вибери категорію для вікторини «Вгадай мелодію»:</b>",
        "quiz_start": (
            "🎧 <b>Музична вікторина «Вгадай мелодію»!</b>\n"
            "Слухай уривок вище та <b>напиши в чат виконавця та назву треку</b>.\n"
            "Хто перший вгадає — отримує +50 XP!"
        ),
        "quiz_win": "🎉 <b>Браво, {name}!</b> Ти першим вгадав мелодію (+50 XP)!\n🎵 <b>Трек:</b> {track}",
        "quiz_error": "❌ Не вдалося завантажити треки для цієї категорії. Спробуй іншу!",
        "thanks_creator": "❤️ Дякуємо! Твоя подяка зарахована, досвід творця збільшено!",
        "thanks_alert": "Дякуємо за підтримку автора! 🚀",
        "welcome_photo": "👋 <b>Привіт! Я твій музичний бот-помічник.</b>\nПрацюю в особистих повідомленнях та групових чатах!",
        "welcome_text": (
            "📖 <b>ПОВНА ІНСТРУКЦІЯ ТА МОЇ МОЖЛИВОСТІ:</b>\n\n"
            "🎵 <b>1. Швидкий пошук треків (MP3):</b>\n"
            "• Через команду: <code>/search [назва]</code> або <code>/шукай [назва]</code>\n"
            "• Або просто напиши у чаті слово <b>«знайди»</b> разом із назвою (наприклад: <i>«знайди metallica»</i> або <i>«ЗНАЙДИ imagine dragons»</i> — регістр не має значення)\n\n"
            "🎮 <b>2. Музична вікторина «Вгадай мелодію»:</b>\n"
            "• Запусти гру командою: <code>/quiz</code>\n"
            "• Або використай розмовні тригер-фрази у чаті: <i>«запусти музичну гру»</i>, <i>«вгадай мелодію»</i>, <i>«грати у вікторину»</i>\n"
            "• За кожну правильну відповідь ти отримуєш <b>+50 XP</b> до свого музичного рейтингу!\n\n"
            "🏆 <b>3. Система прокачування та рейтинги:</b>\n"
            "• 🌟 <b>Мій досвід:</b> перевіряй свої заролені бали (XP) та ставай найкращим музичним знавцем.\n"
            "• 👑 <b>Досвід творця:</b> слідкуй за розвитком та очками творця нашого проєкту (Python + yt-dlp).\n"
            "• 🏆 <b>Топ гравців:</b> змагайся з друзями та потрапляй у п'ятірку найкращих лідерів чату.\n\n"
            "🎛 <b>4. Додаткові команди:</b>\n"
            "• <code>/menu</code> — відкрити інтерактивне головне меню з усіма кнопками\n"
            "• <code>/trends</code> — популярні музичні жанри та напрямки\n"
            "• <code>/help</code> — показати цю довідку"
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
        'default_search': 'auto',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }
    os.makedirs('downloads', exist_ok=True)
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Використовуємо універсальний пошук без жорсткої прив'язки до платформи
            search_query = f"auto:{query}"
            info = ydl.extract_info(search_query, download=True)
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
        logging.error(f"Download error for query '{query}': {e}")
        return None

async def process_music_search(message: Message, query: str):
    status_msg = await message.answer(f"🔍 Шукаю повну версію за запитом: <b>{query}</b>...", parse_mode="HTML")
    loop = asyncio.get_event_loop()
    track_info = await loop.run_in_executor(None, download_audio, query)
    
    if track_info and os.path.exists(track_info['path']):
        try:
            audio_file = FSInputFile(track_info['path'])
            thanks_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❤️ Віддячити творцю (+20 XP)", callback_data="thank_creator")]
            ])
            await message.answer_audio(
                audio=audio_file,
                title=track_info['title'],
                performer=track_info['uploader'],
                caption=f"🎵 <b>{track_info['title']}</b>\n👤 <b>Виконавець:</b> {track_info['uploader']}",
                parse_mode="HTML",
                reply_markup=thanks_keyboard
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

def get_quiz_categories_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎸 Rock / Metal", callback_data="quiz_cat_rock")],
        [InlineKeyboardButton(text="⚡ Pop / Hits", callback_data="quiz_cat_pop")],
        [InlineKeyboardButton(text="🎧 Electronic", callback_data="quiz_cat_electronic")],
        [InlineKeyboardButton(text="🇺🇦 Ukrainian Music", callback_data="quiz_cat_ukrainian")],
        [InlineKeyboardButton(text="📼 80-ті (80s)", callback_data="quiz_cat_80s")],
        [InlineKeyboardButton(text="💿 90-ті (90s)", callback_data="quiz_cat_90s")],
        [InlineKeyboardButton(text="🎲 Випадковий жанр", callback_data="quiz_cat_random")]
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
        caption=i18n["uk"]["welcome_photo"],
        parse_mode="HTML"
    )
    await message.answer(
        text=i18n["uk"]["welcome_text"],
        parse_mode="HTML",
        reply_markup=keyboard
    )

@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    await message.answer(i18n["uk"]["menu"], parse_mode="HTML", reply_markup=get_menu_keyboard())

@dp.message(Command("quiz"))
async def cmd_quiz(message: Message):
    await message.answer(i18n["uk"]["quiz_choose"], parse_mode="HTML", reply_markup=get_quiz_categories_keyboard())

@dp.message(Command("trends"))
async def cmd_trends(message: Message):
    trends_text = (
        "🔥 <b>Популярні музичні напрямки та категорії:</b>\n\n"
        "1. 🎸 <b>Rock / Metal</b> (Metallica, Linkin Park, AC/DC)\n"
        "2. ⚡ <b>Pop / Hits</b> (The Weeknd, Dua Lipa, Billie Eilish)\n"
        "3. 🎧 <b>Electronic / Dance</b> (Daft Punk, Avicii, David Guetta)\n"
        "4. 🎤 <b>Ukrainian Pop & Rock</b> (Океан Ельзи, Бумбокс, SKOFKA)\n"
        "5. 📼 <b>80-ті та 💿 90-ті класика</b>"
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
    chat_id = message.chat.id

    if chat_id in active_text_quizzes:
        correct_answer = active_text_quizzes[chat_id].lower()
        keywords = [w for w in correct_answer.split() if len(w) > 2]
        if keywords and all(kw in lower_text for kw in keywords[:2]):
            track_name = active_text_quizzes.pop(chat_id)
            uid = message.from_user.id
            name = message.from_user.first_name
            
            user_names[uid] = name
            user_xp[uid] = user_xp.get(uid, 0) + 50
            creator_data["creator_xp"] += 15
            
            win_msg = i18n["uk"]["quiz_win"].replace("{name}", name).replace("{track}", track_name)
            await message.answer(win_msg, parse_mode="HTML")
            return

    quiz_triggers = ["запусти музичну гру", "вгадай мелодію", "грати у вікторину", "запусти игру", "угадай мелодию"]
    if any(qt in lower_text for qt in quiz_triggers):
        await message.answer(i18n["uk"]["quiz_choose"], parse_mode="HTML", reply_markup=get_quiz_categories_keyboard())
        return

    if "знайди" in lower_text:
        parts = text.split("знайди", 1)
        if len(parts) > 1:
            query = parts[1].strip()
            if query:
                await process_music_search(message, query)
                return

@dp.callback_query(F.data == "start_quiz")
async def cb_start_quiz(callback: CallbackQuery):
    await callback.message.answer(i18n["uk"]["quiz_choose"], parse_mode="HTML", reply_markup=get_quiz_categories_keyboard())
    await callback.answer()

@dp.callback_query(F.data.startswith("quiz_cat_"))
async def cb_quiz_category(callback: CallbackQuery):
    cat = callback.data.split("_")[2]
    genre_map = {
        "rock": "rock",
        "pop": "pop",
        "electronic": "dance",
        "ukrainian": "ukrainian",
        "80s": "80s hits",
        "90s": "90s hits",
        "random": random.choice(["rock", "pop", "dance", "80s hits", "90s hits"])
    }
    genre = genre_map.get(cat, "rock")
    
    success = await start_quiz(callback.message.chat.id, genre)
    if success:
        await callback.answer("Гра розпочинається! 🎧")
    else:
        await callback.answer(i18n["uk"]["quiz_error"], show_alert=True)
        
    try:
        await callback.message.delete()
    except Exception:
        pass

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
    cXp = creator_data.get("creator_xp", 750)
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

@dp.callback_query(F.data == "thank_creator")
async def cb_thank_creator(callback: CallbackQuery):
    creator_data["creator_xp"] += 20
    await callback.answer(i18n["uk"]["thanks_alert"], show_alert=True)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(i18n["uk"]["thanks_creator"])

async def start_quiz(chat_id: int, genre: str = "rock") -> bool:
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            query_url = f"https://api.deezer.com/search?q={genre}&limit=30"
            async with session.get(query_url) as resp:
                data = await resp.json()
                if "data" not in data or len(data["data"]) == 0:
                    return False
                
                valid_tracks = [t for t in data["data"] if t.get("preview")]
                if not valid_tracks:
                    valid_tracks = data["data"]
                
                track = random.choice(valid_tracks)
                preview_url = track.get("preview")
                artist_name = track["artist"]["name"]
                track_title = track["title"]
                
                active_text_quizzes[chat_id] = f"{artist_name} - {track_title}"
                
                if preview_url:
                    await bot.send_audio(
                        chat_id=chat_id,
                        audio=preview_url,
                        title="Вгадай мелодію",
                        performer="Музична вікторина",
                        caption=i18n["uk"]["quiz_start"],
                        parse_mode="HTML"
                    )
                    return True
                else:
                    return False
    except Exception as e:
        logging.error(f"Quiz start error: {e}")
        return False

async def handle_ping(request):
    return web.Response(text="Music Assistant Bot is running and active!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Web server started on port {port}")

async def main():
    await start_web_server()
    print("Python Bot started successfully with web server & full features...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())