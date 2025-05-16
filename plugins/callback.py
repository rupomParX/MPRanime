#..........This Bot Made By [RAHAT](https://t.me/r4h4t_69)..........#
#..........Anyone Can Modify This As He Likes..........#
#..........Just one requests do not remove my credit..........#

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from plugins.queue import add_to_queue, remove_from_queue
from plugins.kwik import extract_kwik_link
from plugins.direct_link import get_dl_link
from plugins.headers import*
from plugins.file import*
from plugins.commands import user_queries
from helper.database import*
from config import DOWNLOAD_DIR
from bs4 import BeautifulSoup
import re


episode_data = {}
episode_urls = {}

@Client.on_callback_query(filters.regex(r"^anime_"))
def anime_details(client, callback_query):
    session_id = callback_query.data.split("anime_")[1]

    # Retrieve the query stored earlier
    query = user_queries.get(callback_query.message.chat.id, "")
    search_url = f"https://animepahe.ru/api?m=search&q={query.replace(' ', '+')}"
    response = session.get(search_url).json()
    
    anime = next(anime for anime in response['data'] if anime['session'] == session_id)
    title = anime['title']
    anime_type = anime['type']
    episodes = anime['episodes']
    status = anime['status']
    season = anime['season']
    year = anime['year']
    score = anime['score']
    poster_url = anime['poster']
    anime_link = f"https://animepahe.ru/anime/{session_id}"

    message_text = (
        f"**Title**: {title}\n"
        f"**Type**: {anime_type}\n"
        f"**Episodes**: {episodes}\n"
        f"**Status**: {status}\n"
        f"**Season**: {season}\n"
        f"**Year**: {year}\n"
        f"**Score**: {score}\n"
        f"[Anime Link]({anime_link})\n\n"
        f"**Bot Made By**\n"
        f"    **[MushrifurParX](NA)**"
    )

    # Store the session_id for episodes
    episode_data[callback_query.message.chat.id] = {
        "session_id": session_id,
        "poster": poster_url,
        "title": title        # Store the poster URL here
    }

    episode_button = InlineKeyboardMarkup([[InlineKeyboardButton("Episodes", callback_data="episodes")]])
    client.send_photo(
        chat_id=callback_query.message.chat.id,
        photo=poster_url,
        caption=message_text,
        reply_markup=episode_button
    )
# Callback for episode list with pagination (send buttons once)
@Client.on_callback_query(filters.regex(r"^episodes$"))
def episode_list(client, callback_query, page=1):
    session_data = episode_data.get(callback_query.message.chat.id)

    if not session_data:
        callback_query.message.reply_text("Session ID not found.")
        return

    session_id = session_data['session_id']
    episodes_url = f"https://animepahe.ru/api?m=release&id={session_id}&sort=episode_asc&page={page}"
    response = session.get(episodes_url).json()

    # Store the total number of pages
    last_page = int(response["last_page"])
    episodes = response['data']

    # Update the current page for the user
    episode_data[callback_query.message.chat.id]['current_page'] = page
    episode_data[callback_query.message.chat.id]['last_page'] = last_page

    # Store episode data for each user
    episode_data[callback_query.message.chat.id]['episodes'] = {ep['episode']: ep['session'] for ep in episodes}

    episode_buttons = [
        [InlineKeyboardButton(f"Episode {ep['episode']}", callback_data=f"ep_{ep['episode']}")]
        for ep in episodes
    ]


    # Add navigation buttons for pagination
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("<", callback_data=f"page_{page - 1}"))
    if page < last_page:
        nav_buttons.append(InlineKeyboardButton(">", callback_data=f"page_{page + 1}"))

    if nav_buttons:
        episode_buttons.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(episode_buttons)

    # If it's the first time, send a message, otherwise edit the existing one
    if callback_query.message.reply_markup is None:
        callback_query.message.reply_text(f"Page {page}/{last_page}: Select an episode:", reply_markup=reply_markup)
    else:
        callback_query.message.edit_reply_markup(reply_markup)

# Callback to handle navigation between pages (edit buttons in place)
@Client.on_callback_query(filters.regex(r"^page_"))
def navigate_pages(client, callback_query):
    new_page = int(callback_query.data.split("_")[1])
    session_data = episode_data.get(callback_query.message.chat.id)

    if not session_data:
        callback_query.message.reply_text("Session ID not found.")
        return

    current_page = session_data.get('current_page', 1)
    last_page = session_data.get('last_page', 1)

    # Check if the user is trying to go beyond the first or last page
    if new_page < 1:
        callback_query.answer("You're already on the first page.", show_alert=True)
    elif new_page > last_page:
        callback_query.answer("You're already on the last page.", show_alert=True)
    else:
        # Call the episode list function with the new page number, but edit the message
        episode_list(client, callback_query, page=new_page)


# Callback for episode link and fetching download links
@Client.on_callback_query(filters.regex(r"^ep_"))
def fetch_download_links(client, callback_query):
    episode_number = int(callback_query.data.split("_")[1])
    user_id = callback_query.message.chat.id  # Unique per user
    
    session_data = episode_data.get(user_id)

    if not session_data or 'episodes' not in session_data:
        callback_query.message.reply_text("Episode not found.")
        return

    session_id = session_data['session_id']
    episodes = session_data['episodes']

    if episode_number not in episodes:
        callback_query.message.reply_text("Episode not found.")
        return

    # Store episode number for the user
    episode_data[user_id]['current_episode'] = episode_number  # Add this line

    episode_session = episodes[episode_number]
    episode_url = f"https://animepahe.ru/play/{session_id}/{episode_session}"

    # Send a request to the episode URL and parse the HTML for download links
    response = session.get(episode_url)
    soup = BeautifulSoup(response.content, "html.parser")

    # Extract all download links and their titles
    download_links = soup.select("#pickDownload a.dropdown-item")

    if not download_links:
        callback_query.message.reply_text("No download links found.")
        return

    # Create buttons for each download link
    download_buttons = [
        [InlineKeyboardButton(link.get_text(strip=True), callback_data=f"dl_{link['href']}")]
        for link in download_links
    ]
    reply_markup = InlineKeyboardMarkup(download_buttons)
    callback_query.message.reply_text("Select a download link:", reply_markup=reply_markup)

@Client.on_callback_query(filters.regex(r"set_method_"))
def change_upload_method(client, callback_query):
    user_id = callback_query.from_user.id
    data = callback_query.data.split("_")[2]  # Extract 'document' or 'video'
    
    # Update the selected method in the database
    save_upload_method(user_id, data)
    
    # Acknowledge the change
    callback_query.answer(f"Upload method set to {data.capitalize()}")
    
    # Update the buttons with the new selection
    document_status = "✅" if data == "document" else "❌"
    video_status = "✅" if data == "video" else "❌"
    
    buttons = [
        [
            InlineKeyboardButton(f"Document ({document_status})", callback_data="set_method_document"),
            InlineKeyboardButton(f"Video ({video_status})", callback_data="set_method_video")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(buttons)
    callback_query.message.edit_reply_markup(reply_markup)


@Client.on_callback_query(filters.regex(r"^dl_"))
def download_and_upload_file(client, callback_query):
    download_url = callback_query.data.split("dl_")[1]
    kwik_link = extract_kwik_link(download_url)

    try:
        direct_link = get_dl_link(kwik_link)
    except Exception as e:
        callback_query.message.reply_text(f"Error generating download link: {str(e)}")
        return
    username = callback_query.from_user.username or "Unknown User"
    user_id = callback_query.from_user.id
    add_to_queue(user_id, username, direct_link)
    # Retrieve episode number from episode_data
    episode_number = episode_data.get(user_id, {}).get('current_episode', 'Unknown')  # Default to 'Unknown Episode'
    title = episode_data.get(user_id, {}).get('title', 'Unknown Title')  # Default to 'Unknown Title'

    # Extract download button title
    download_button_title = next(
        (button.text for row in callback_query.message.reply_markup.inline_keyboard
         for button in row if button.callback_data == f"dl_{download_url}"),
        "Unknown Source"
    )

    # Create the filename
    resolution = re.search(r"\b\d{3,4}p\b", download_button_title)
    resolution = resolution.group() if resolution else download_button_title
    if 'eng' in download_button_title:
	    type = "Dub"
    else:
	    type = "Sub"
    # Create the filename
    title = f"{title}"
    short_name = create_short_name(title)	
    file_name = f"[{type}] [{short_name}] [EP {episode_number}] [{resolution}]"
    file_name = file_name + ".mp4"
    filename = sanitize_filename(file_name)
    file_name = filename
    random_str = random_string(5)

    # Define download path
    user_download_dir = os.path.join(DOWNLOAD_DIR, str(user_id), random_str)
    os.makedirs(user_download_dir, exist_ok=True)
    download_path = os.path.join(user_download_dir, file_name)

    #callback_query.message.reply_text(f"Added to queue: {file_name}. Downloading now...")
    #dl_msg = callback_query.message.reply_text(f"<b>Added to queue:</b>\n <pre language="python">{file_name}</pre>\n<b>Downloading now...</b>")
    dl_msg = callback_query.message.reply_text(f"<b>Added to queue:</b>\n <pre>{file_name}</pre>\n<b>Downloading now...</b>")
    
    try:
        # Download the file
        download_file(direct_link, download_path)
        #callback_query.message.reply_text("File downloaded, uploading...")
        dl_msg.edit("<b>Episode downloaded, uploading...</b>")

        # Fetch thumbnail
        user_thumbnail = get_thumbnail(user_id)
        poster_url = episode_data.get(user_id, {}).get("poster", None)

        if user_thumbnail:
            thumb_path = client.download_media(user_thumbnail)
        elif poster_url:
            response = requests.get(poster_url, stream=True)
            thumb_path = f"{user_download_dir}/thumb_file.jpg"
            with open(thumb_path, 'wb') as thumb_file:
                for chunk in response.iter_content(1024):
                    thumb_file.write(chunk)
        else:
            thumb_path = None

        # Send the file
        user_caption = get_caption(user_id)
        caption_to_use = user_caption if user_caption else file_name        

        send_and_delete_file(client, callback_query.message.chat.id, download_path, thumb_path, caption_to_use, user_id)
        # Remove the thumbnail file if it was downloaded
        remove_from_queue(user_id, direct_link)
        dl_msg.edit(f"<b><pre>Episode Uploaded 🎉</pre></b>")
        if thumb_path and os.path.exists(thumb_path):
            os.remove(thumb_path)
        if user_download_dir and os.path.exists(user_download_dir):
            remove_directory(user_download_dir)        

    except Exception as e:
        callback_query.message.reply_text(f"Error: {str(e)}")

# Callback query handler for Help and Close buttons
@Client.on_callback_query()
def callback_query_handler(client, callback_query):
    if callback_query.data == "help":
        # Send the help message
        callback_query.message.edit_text(
            text=(
                "<b>Here is how to use the bot:</b>\n\n"
                "<b>General Commands:</b>\n"
                "/start - Welcome message and menu buttons.\n"
                "/help - Get assistance with bot commands.\n"
                "/latest - Fetch the latest airing anime.\n"
                "/anime <name> - Search for an anime by name.\n"
                "/anime info <name> or /anime_info <name> - Get detailed anime info.\n"
                "/manga info <name> or /manga_info <name> - Get detailed manga info.\n"
                "/airing - Get a list of currently airing anime.\n"
                "/queue - View active downloads in the queue.\n"
                "/ping - Bot health check.\n\n"
                "<b>Thumbnail Commands:</b>\n"
                "/set_thumb - Set a custom thumbnail (reply to a photo).\n"
                "/see_thumb - See your current custom thumbnail.\n"
                "/del_thumb - Delete your custom thumbnail.\n\n"
                "<b>Caption Commands:</b>\n"
                "/set_caption - Save a custom caption (reply to a text).\n"
                "/see_caption - View your current caption.\n"
                "/del_caption - Delete your custom caption.\n\n"
                "<b>Upload Options:</b>\n"
                "/options - Set upload options (Document or Video).\n\n"
                "<b>Admin Commands:</b>\n"
                "/users - Get the total number of bot users (admin only).\n"
                "/broadcast - Send a message to all bot users (admin only, reply to a message).\n"
            ),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Close", callback_data="close")]])
        )
    
    elif callback_query.data == "close":
        # Close the panel by deleting the message
        callback_query.message.delete()
