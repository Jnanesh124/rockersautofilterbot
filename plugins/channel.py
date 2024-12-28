from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import CHANNELS, MOVIE_UPDATE_CHANNEL, ADMINS
from database.ia_filterdb import save_file, unpack_new_file_id
from utils import get_poster, temp, formate_file_name
from urllib.parse import quote  # Correctly import 'quote'
import re
from Script import script
from database.users_chats_db import db

processed_movies = set()
media_filter = filters.document | filters.video

@Client.on_message(filters.chat(CHANNELS) & media_filter)
async def media(bot, message):
    media = getattr(message, message.media.value, None)
    if media.mime_type in ['video/mp4', 'video/x-matroska']:
        media.file_type = message.media.value
        media.caption = message.caption
        success_sts = await save_file(media)
        post_mode = await db.update_post_mode_handle()
        file_id, file_ref = unpack_new_file_id(media.file_id)
        if post_mode.get('all_files_post_mode', False) or success_sts == 'suc':
            await send_movie_updates(bot, file_name=media.file_name, file_id=file_id, post_mode=post_mode)

def name_format(file_name: str):
    file_name = file_name.lower()
    file_name = re.sub(r'http\S+', '', re.sub(r'@\w+|#\w+', '', file_name).replace('_', ' ').replace('[', '').replace(']', '')).strip()
    file_name = re.split(r's\d+|season\s*\d+|chapter\s*\d+', file_name, flags=re.IGNORECASE)[0]
    file_name = file_name.strip()
    words = file_name.split()[:4]
    imdb_file_name = ' '.join(words)
    return imdb_file_name

def clean_movie_name(file_name: str) -> str:
    season_episode_match = re.search(r'\b(S\d{1,2}E\d{1,2}|E\d{1,2})\b', file_name, flags=re.IGNORECASE)
    year_match = re.search(r'\b(19|20)\d{2}\b', file_name)

    if year_match and not season_episode_match:
        year_index = year_match.start()
        file_name = file_name[:year_index]
    elif season_episode_match:
        season_index = season_episode_match.start()
        file_name = file_name[:season_index]

    file_name = re.sub(r'[\[\(\{].*?[\]\)\}]|@\w+', '', file_name)
    file_name = re.sub(
        r'\b(\d{3,4}p|Ultra HD-\d+p|4K|10bit|HDRip|WEBRip|BluRay|REMUX|HS|BDRip|HEVC|mkvCinemas|[Telly]|WebRip|x264|x265|H\.\d+|6CH|AAC|DTS|DDP\d+\.\d+|Ssub|Esub|MB|GB|part\d+)\b',
        '',
        file_name,
        flags=re.IGNORECASE
    )
    file_name = re.sub(r'\b(HQ|HD|Full HD|Web-DL|Spa|Eng|Tam|Tel|Hin|Malayalam|Dual Audio|Eng Sub|Eng Subs|Sub|Ssub|Esub|5.1|mkv|.mkv|1080p|720p)\b', '', file_name, flags=re.IGNORECASE)
    file_name = re.sub(r'[._-]', ' ', file_name)
    file_name = re.sub(r'\s+', ' ', file_name).strip()
    file_name = re.sub(r'[^a-zA-Z0-9\s]', '', file_name)
    file_name = re.sub(r'\s+', ' ', file_name).strip()

    return file_name

async def get_imdb(file_name, post_mode):
    cleaned_name = clean_movie_name(file_name)
    imdb_file_name = name_format(cleaned_name)
    imdb = await get_poster(imdb_file_name)
    file_name_display = f'File Name : <code>{formate_file_name(cleaned_name)}</code>' if post_mode.get('singel_post_mode', True) else ''
    if imdb:
        # Ensure all keys are present in the IMDb dictionary
        title = imdb.get('title', 'Unknown Title')
        rating = imdb.get('rating', 'N/A')
        genres = imdb.get('genres', 'N/A')
        description = imdb.get('plot', 'No description available.')
        year = imdb.get('year', 'Unknown Year')  # Add default for 'year'

        caption = script.MOVIES_UPDATE_TXT.format(
            title=cleaned_name,  # Add cleaned name to the title
            rating=rating,
            genres=genres,
            description=description,
            year=year,  # Include the year key
            file_name=file_name_display
        )
        return title, imdb.get('poster'), caption
    return None, None, None

async def send_movie_updates(bot, file_name, file_id, post_mode):
    imdb_title, poster_url, caption = await get_imdb(file_name, post_mode)
    if not post_mode.get('singel_post_mode', True):
        if imdb_title in processed_movies:
            return
        processed_movies.add(imdb_title)
    if not poster_url or not caption:
        return

    formatted_name = quote(str(clean_movie_name(file_name)) if file_name else 'Unknown')
    btn = [
        [InlineKeyboardButton(
            '📥 𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝 𝐅𝐢𝐥𝐞 📥', 
            url=f'tg://resolve?domain=Theater_Print_Movies_Search_bot&text={formatted_name}'
        )],
    ]
    reply_markup = InlineKeyboardMarkup(btn)
    movie_update_channel = await db.movies_update_channel_id()
    try:
        await bot.send_photo(movie_update_channel if movie_update_channel else MOVIE_UPDATE_CHANNEL, photo=poster_url, caption=caption, reply_markup=reply_markup)
    except Exception as e:
        print('Error in send_movie_updates', e)
        pass
