import requests
import tempfile
import os
import re

def format_date(date):
    if not date or not date.get('year'):
        return "?"
    year = date.get('year')
    month = str(date.get('month', '??')).zfill(2) if date.get('month') else "??"
    day = str(date.get('day', '??')).zfill(2) if date.get('day') else "??"
    return f"{year}-{month}-{day}"

def format_status(status):
    status_map = {
        'FINISHED': 'Finished',
        'RELEASING': 'Ongoing',
        'NOT_YET_RELEASED': 'Not Yet Released',
        'CANCELLED': 'Cancelled',
        'HIATUS': 'Hiatus'
    }
    return status_map.get(status, status)

def format_type(type_):
    type_map = {
        'TV': 'TV Series',
        'TV_SHORT': 'TV Short',
        'MOVIE': 'Movie',
        'SPECIAL': 'Special',
        'OVA': 'OVA',
        'ONA': 'ONA',
        'MUSIC': 'Music'
    }
    return type_map.get(type_, type_)

def format_source(source):
    source_map = {
        'ORIGINAL': 'Original',
        'MANGA': 'Manga',
        'LIGHT_NOVEL': 'Light Novel',
        'VISUAL_NOVEL': 'Visual Novel',
        'VIDEO_GAME': 'Video Game',
        'NOVEL': 'Novel',
        'DOUJINSHI': 'Doujinshi',
        'ANIME': 'Anime'
    }
    return source_map.get(source, source)

def format_season(season):
    season_map = {
        'WINTER': 'Winter',
        'SPRING': 'Spring',
        'SUMMER': 'Summer',
        'FALL': 'Fall'
    }
    return season_map.get(season, season)

def clean_description(description):
    if not description:
        return "No description available"
    desc = re.sub(r'<[^>]*>', '', description)
    return desc[:700] + ("..." if len(desc) > 700 else "")

def fetch_anime_info(anime_name, send_message_func):
    # send_message_func(msg, attachment_path=None)
    query = '''
    query ($search: String) {
        Media(search: $search, type: ANIME) {
            title { romaji english native }
            description(asHtml: false)
            coverImage { extraLarge large color }
            bannerImage
            episodes
            duration
            status
            averageScore
            meanScore
            popularity
            favourites
            genres
            studios(isMain: true) { nodes { name } }
            startDate { year month day }
            endDate { year month day }
            season
            seasonYear
            format
            source
            countryOfOrigin
            hashtag
            trailer { id site thumbnail }
            nextAiringEpisode { airingAt timeUntilAiring episode }
            relations { edges { relationType node { title { romaji english } siteUrl } } }
            recommendations { nodes { mediaRecommendation { title { romaji } siteUrl } } }
            siteUrl
        }
    }
    '''
    variables = {"search": anime_name}
    send_message_func("🔍 Searching anime info...")
    try:
        response = requests.post('https://graphql.anilist.co', json={"query": query, "variables": variables})
        response.raise_for_status()
        anime = response.json()['data']['Media']
        if not anime:
            send_message_func(f"❌ No results found for \"{anime_name}\". Please check the name and try again.")
            return
        description = clean_description(anime.get('description'))
        relations = anime.get('relations', {}).get('edges', [])
        relations_text = ""
        if relations:
            relations_text = '\n'.join([
                f"{edge.get('relationType')}: {edge.get('node', {}).get('title', {}).get('romaji')}" for edge in relations[:3]
            ])
        recommendations = anime.get('recommendations', {}).get('nodes', [])
        recommendations_text = ""
        if recommendations:
            recommendations_text = '\n'.join([
                f"- {node.get('mediaRecommendation', {}).get('title', {}).get('romaji')}" for node in recommendations[:3]
            ])
        next_ep = anime.get('nextAiringEpisode')
        next_episode_text = ""
        if next_ep:
            time_until = next_ep.get('timeUntilAiring', 0)
            days = time_until // (24 * 60 * 60)
            hours = (time_until % (24 * 60 * 60)) // (60 * 60)
            next_episode_text = f"\n⏳ Next Episode: #{next_ep.get('episode')} in {days}d {hours}h"
        studio = anime.get('studios', {}).get('nodes', [{}])[0].get('name', 'Unknown')
        title = anime['title']
        info_msg = f"🎌 𝗧𝗶𝘁𝗹𝗲: {title.get('romaji') or title.get('english')}\n"
        if title.get('english'):
            info_msg += f"🏴 𝗘𝗻𝗴𝗹𝗶𝘀𝗵: {title['english']}\n"
        if title.get('native'):
            info_msg += f"🗾 𝗡𝗮𝘁𝗶𝘃𝗲: {title['native']}\n\n"
        info_msg += f"📌 𝗦𝘁𝗮𝘁𝘂𝘀: {format_status(anime.get('status'))}\n"
        info_msg += f"📺 𝗘𝗽𝗶𝘀𝗼𝗱𝗲𝘀: {anime.get('episodes', 'Unknown')} ({anime.get('duration', '?')} min/ep)\n"
        info_msg += f"⭐ 𝗥𝗮𝘁𝗶𝗻𝗴: {anime.get('averageScore', '?')}/100 ({anime.get('meanScore', '?')} mean)\n"
        info_msg += f"❤️ 𝗙𝗮𝘃𝗼𝗿𝗶𝘁𝗲𝘀: {anime.get('favourites', 0):,}\n"
        info_msg += f"🔥 𝗣𝗼𝗽𝘂𝗹𝗮𝗿𝗶𝘁𝘆: #{anime.get('popularity', '?')}\n\n"
        info_msg += f"🎬 𝗙𝗼𝗿𝗺𝗮𝘁: {format_type(anime.get('format'))}\n"
        info_msg += f"🎥 𝗦𝗼𝘂𝗿𝗰𝗲: {format_source(anime.get('source'))}\n"
        info_msg += f"🏢 𝗦𝘁𝘂𝗱𝗶𝗼: {studio}\n"
        info_msg += f"🌐 𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {anime.get('countryOfOrigin', 'Japan')}\n\n"
        info_msg += f"🗓️ 𝗔𝗶𝗿𝗲𝗱: {format_date(anime.get('startDate'))} to {format_date(anime.get('endDate'))}\n"
        if anime.get('season'):
            info_msg += f"🍂 𝗦𝗲𝗮𝘀𝗼𝗻: {format_season(anime['season'])} {anime.get('seasonYear', '')}\n"
        info_msg += next_episode_text
        info_msg += f"\n🏷️ 𝗚𝗲𝗻𝗿𝗲𝘀: {', '.join(anime.get('genres', []))}\n\n"
        # info_msg += f"📝 𝗗𝗲𝘀𝗰𝗿𝗶𝗽𝘁𝗶𝗼𝗻:\n{description}\n\n"  # Description turned off as requested
        if relations_text:
            info_msg += f"🔗 𝗥𝗲𝗹𝗮𝘁𝗶𝗼𝗻𝘀:\n{relations_text}\n\n"
        if recommendations_text:
            info_msg += f"💡 𝗥𝗲𝗰𝗼𝗺𝗺𝗲𝗻𝗱𝗲𝗱:\n{recommendations_text}\n\n"
        info_msg += f"🔗 𝗠𝗼𝗿𝗲 𝗜𝗻𝗳𝗼: {anime.get('siteUrl')}"
        trailer = anime.get('trailer')
        if trailer and trailer.get('id'):
            info_msg += f"\n🎬 𝗧𝗿𝗮𝗶𝗹𝗲𝗿: https://youtube.com/watch?v={trailer['id']}"
        image_url = anime.get('coverImage', {}).get('extraLarge') or anime.get('coverImage', {}).get('large')
        if image_url:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as img_file:
                img_resp = requests.get(image_url)
                img_file.write(img_resp.content)
                img_path = img_file.name
            # Telegram caption limit is 1024 chars
            if len(info_msg) > 1024:
                short_caption = title.get('romaji') or title.get('english') or 'Anime Info'
                send_message_func(short_caption, attachment_path=img_path)
                # Send the rest as a text message
                send_message_func(info_msg)
            else:
                send_message_func(info_msg, attachment_path=img_path)
            os.unlink(img_path)
        else:
            send_message_func(info_msg)
    except Exception as e:
        send_message_func("❌ Error fetching anime info. Please try again later.")
        print(f"❌ Anime Error: {str(e)}")

def fetch_manga_info(manga_name, send_message_func):
    query = '''
    query ($search: String) {
        Media(search: $search, type: MANGA) {
            title { romaji english native }
            description(asHtml: false)
            coverImage { extraLarge large color }
            chapters
            volumes
            status
            averageScore
            meanScore
            popularity
            favourites
            genres
            startDate { year month day }
            endDate { year month day }
            siteUrl
        }
    }
    '''
    variables = {"search": manga_name}
    send_message_func("🔍 Searching manga info...")
    try:
        response = requests.post('https://graphql.anilist.co', json={"query": query, "variables": variables})
        response.raise_for_status()
        manga = response.json()['data']['Media']
        if not manga:
            send_message_func(f"❌ No results found for \"{manga_name}\". Please check the name and try again.")
            return
        title = manga['title']
        info_msg = f"📖 𝗧𝗶𝘁𝗹𝗲: {title.get('romaji') or title.get('english')}\n"
        if title.get('english'):
            info_msg += f"🏴 𝗘𝗻𝗴𝗹𝗶𝘀𝗵: {title['english']}\n"
        if title.get('native'):
            info_msg += f"🗾 𝗡𝗮𝘁𝗶𝘃𝗲: {title['native']}\n\n"
        info_msg += f"📌 𝗦𝘁𝗮𝘁𝘂𝘀: {format_status(manga.get('status'))}\n"
        info_msg += f"📚 𝗖𝗵𝗮𝗽𝘁𝗲𝗿𝘀: {manga.get('chapters', 'Unknown')}\n"
        info_msg += f"📖 𝗩𝗼𝗹𝘂𝗺𝗲𝘀: {manga.get('volumes', 'Unknown')}\n"
        info_msg += f"⭐ 𝗥𝗮𝘁𝗶𝗻𝗴: {manga.get('averageScore', '?')}/100 ({manga.get('meanScore', '?')} mean)\n"
        info_msg += f"❤️ 𝗙𝗮𝘃𝗼𝗿𝗶𝘁𝗲𝘀: {manga.get('favourites', 0):,}\n"
        info_msg += f"🔥 𝗣𝗼𝗽𝘂𝗹𝗮𝗿𝗶𝘁𝘆: #{manga.get('popularity', '?')}\n\n"
        info_msg += f"🗓️ 𝗔𝗶𝗿𝗲𝗱: {format_date(manga.get('startDate'))} to {format_date(manga.get('endDate'))}\n"
        info_msg += f"🏷️ 𝗚𝗲𝗻𝗿𝗲𝘀: {', '.join(manga.get('genres', []))}\n\n"
        # info_msg += f"📝 𝗗𝗲𝘀𝗰𝗿𝗶𝗽𝘁𝗶𝗼𝗻:\n{clean_description(manga.get('description'))}\n\n"  # Description turned off as requested
        info_msg += f"🔗 𝗠𝗼𝗿𝗲 𝗜𝗻𝗳𝗼: {manga.get('siteUrl')}"
        image_url = manga.get('coverImage', {}).get('extraLarge') or manga.get('coverImage', {}).get('large')
        if image_url:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as img_file:
                img_resp = requests.get(image_url)
                img_file.write(img_resp.content)
                img_path = img_file.name
            # Telegram caption limit is 1024 chars
            if len(info_msg) > 1024:
                short_caption = title.get('romaji') or title.get('english') or 'Manga Info'
                send_message_func(short_caption, attachment_path=img_path)
                send_message_func(info_msg)
            else:
                send_message_func(info_msg, attachment_path=img_path)
            os.unlink(img_path)
        else:
            send_message_func(info_msg)
    except Exception as e:
        send_message_func("❌ Error fetching manga info. Please try again later.")
        print(f"❌ Manga Error: {str(e)}")

# Example usage:
# def send_message(msg, attachment_path=None):
#     print(msg)
#     if attachment_path:
#         print(f"[Image at {attachment_path}]")
# fetch_anime_info("Naruto", send_message)
