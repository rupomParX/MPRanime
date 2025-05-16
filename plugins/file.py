import requests
import os
import string
import random
import shutil
import re
from helper.database import*
import subprocess
import json
from config import LOG_CHANNEL
def create_short_name(name):
    # Check if the name length is greater than 25
    if len(name) > 30:
        # Extract all capital letters from the name
        short_name = ''.join(word[0].upper() for word in name.split())					
        return short_name    
    return name
def get_media_details(path):
    try:
        # Run ffprobe command to get media info in JSON format
        result = subprocess.run(
            [
                "ffprobe",
                "-hide_banner",
                "-loglevel",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                path,
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"Error: Unable to process the file. FFprobe output:\n{result.stderr}")
            return None

        # Parse JSON output
        media_info = json.loads(result.stdout)

        # Extract width, height, and duration
        video_stream = next((stream for stream in media_info["streams"] if stream["codec_type"] == "video"), None)
        width = video_stream.get("width") if video_stream else None
        height = video_stream.get("height") if video_stream else None
        duration = media_info["format"].get("duration")

        return width, height, duration

    except Exception as e:
        print(f"An error occurred: {e}")
        return None
USE_PROXY = False  # Set to False to disable proxy for downloads

def download_file(url, download_path):
    proxies = {
        'http': 'socks5://rupom11:password@ip:port',
        'https': 'socks5://rupom11:password@ip:port'
    }
    if USE_PROXY:
        # Test: Print public IP as seen by remote server via proxy
        try:
            ip_resp = requests.get('https://httpbin.org/ip', proxies=proxies, timeout=10)
            print('Proxy Test IP:', ip_resp.text)
        except Exception as e:
            print('Proxy Test Failed:', e)
        try:
            with requests.get(url, stream=True, proxies=proxies, timeout=60) as r:
                r.raise_for_status()
                with open(download_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            return download_path
        except Exception as e:
            print('Download via proxy failed:', e)
            raise
    else:
        print('Downloading without proxy...')
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(download_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return download_path


def sanitize_filename(file_name):
    # Remove invalid characters from the file name
    file_name = re.sub(r'[<>:"/\\|?*]', '', file_name)
    return file_name
    
        
'''def send_and_delete_file(client, chat_id, file_path, thumbnail=None, caption="", user_id=None):
    upload_method = get_upload_method(user_id)  # Retrieve user's upload method
    
    try:
        if upload_method == "document":
            # Send as document
            client.send_document(
                chat_id,
                file_path,
                thumb=thumbnail if thumbnail else None,
                caption=caption
            )
        else:
            # Send as video
            client.send_video(
                chat_id,
                file_path,
                #thumb=thumbnail if thumbnail else None,
                thumb=None,
                caption=caption
            )
        
        os.remove(file_path)  # Delete the file after sending
        
    except Exception as e:
        client.send_message(chat_id, f"Error: {str(e)}")'''


def send_and_delete_file(client, chat_id, file_path, thumbnail=None, caption="", user_id=None):
    upload_method = get_upload_method(user_id)  # Retrieve user's upload method
    forwarding_channel = LOG_CHANNEL  # Channel to forward the file

    try:        
        user_info = client.get_users(user_id)
        user_details = f"Downloaded by: @{user_info.username if user_info.username else 'Unknown'} (ID: {user_id})"
        
        # Add user info to the caption
        caption_with_info = f"{caption}\n\n{user_details}"
        if upload_method == "document":
            # Send as document
            sent_message = client.send_document(
                chat_id,
                file_path,
                thumb=thumbnail if thumbnail else None,
                caption=caption
            )
        else:
            # Send as video
            details = get_media_details(file_path)
            if details:
                width, height, duration = details  # Unpack the values properly
                width = int(width) if width else None
                height = int(height) if height else None
                duration = int(float(duration)) if duration else None
            sent_message = client.send_video(
                chat_id,
                file_path,
                duration= duration if duration else None,
                width= width if width else None,
                height= height if height else None,
                supports_streaming= True,
                has_spoiler= True,
                thumb=None,
                caption=caption
            )
        
        # Forward the message to the specified channel
        forward_message = client.copy_message(
            chat_id=forwarding_channel,
            from_chat_id=chat_id,
            message_id=sent_message.id,
            caption=caption_with_info
        )
        
        # Delete the file after sending and forwarding
        os.remove(file_path)
        
    except Exception as e:
        client.send_message(chat_id, f"Error: {str(e)}")
        

def remove_directory(directory_path):
    if not os.path.exists(directory_path):
        raise FileNotFoundError(f"The directory '{directory_path}' does not exist.")
    
    try:
        shutil.rmtree(directory_path)
        #print(f"Directory '{directory_path}' has been removed successfully.")
    except PermissionError as e:
        print(f"Permission denied: {e}")
    except Exception as e:
        print(f"An error occurred while removing the directory: {e}")

def random_string(length):
    if length < 1:
        raise ValueError("Length must be a positive integer.")
    
    # Define the characters to choose from (letters and digits)
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


