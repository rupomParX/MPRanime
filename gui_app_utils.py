import os
import queue
import requests  # <-- add this import
from tkinter import messagebox
import tkinter as tk  # <-- add this import
from PIL import Image, ImageTk  # <-- add this import
from plugins.headers import session
from plugins.direct_link import get_dl_link
from plugins.kwik import extract_kwik_link
from plugins.anime_info import fetch_anime_info, fetch_manga_info

DEFAULT_DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
download_dir = [DEFAULT_DOWNLOAD_DIR]
download_queue = queue.Queue()
download_progress = {}

def sanitize_folder_name(name):
    return "".join(c for c in name if c not in r'<>:"/\|?*')

def search_anime(query):
    url = f"https://animepahe.ru/api?m=search&q={query.replace(' ', '+')}"
    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get('data', [])
    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch anime list.\n{e}")
        return []

def get_episodes(session_id):
    url = f"https://animepahe.ru/api?m=release&id={session_id}&sort=episode_asc&page=1"
    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get('data', [])
    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch episodes.\n{e}")
        return []

def get_download_links(anime_session, episode_session):
    url = f"https://animepahe.ru/play/{anime_session}/{episode_session}"
    try:
        resp = session.get(url, timeout=10)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.content, "html.parser")
        links = soup.select("#pickDownload a.dropdown-item")
        return [(a.get_text(strip=True), a['href']) for a in links]
    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch download links.\n{e}")
        return []

def download_anime(direct_url, save_path, qid):
    try:
        with requests.get(direct_url, stream=True, timeout=60) as r:
            r.raise_for_status()
            total = int(r.headers.get('content-length', 0))
            downloaded = 0
            with open(save_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        download_progress[qid] = (downloaded, total)
        download_progress[qid] = 'done'
    except Exception as e:
        download_progress[qid] = f'error: {e}'

def get_anime_info(anime_name, parent):
    info_text = []
    img_path = [None]
    def collect(msg, attachment_path=None):
        info_text.append(msg)
        if attachment_path:
            img_path[0] = attachment_path
    fetch_anime_info(anime_name, collect)
    info = "\n\n".join(info_text)
    info_win = tk.Toplevel(parent)
    info_win.title(f"Anime Info: {anime_name}")
    info_win.geometry("600x600")
    if img_path[0]:
        try:
            with open(img_path[0], "rb") as f:
                img = Image.open(f)
                img.thumbnail((400, 400))
                photo = ImageTk.PhotoImage(img)
                img_label = tk.Label(info_win, image=photo)
                img_label.image = photo
                img_label.pack()
        except Exception:
            pass
        try:
            os.unlink(img_path[0])
        except Exception:
            pass
    text = tk.Text(info_win, wrap=tk.WORD)
    text.insert(tk.END, info)
    text.config(state=tk.DISABLED)
    text.pack(expand=True, fill=tk.BOTH)

def get_manga_info(anime_name, parent):
    info_text = []
    img_path = [None]
    def collect(msg, attachment_path=None):
        info_text.append(msg)
        if attachment_path:
            img_path[0] = attachment_path
    fetch_manga_info(anime_name, collect)
    info = "\n\n".join(info_text)
    info_win = tk.Toplevel(parent)
    info_win.title(f"Manga Info: {anime_name}")
    info_win.geometry("600x600")
    if img_path[0]:
        try:
            with open(img_path[0], "rb") as f:
                img = Image.open(f)
                img.thumbnail((400, 400))
                photo = ImageTk.PhotoImage(img)
                img_label = tk.Label(info_win, image=photo)
                img_label.image = photo
                img_label.pack()
        except Exception:
            pass
        try:
            os.unlink(img_path[0])
        except Exception:
            pass
    text = tk.Text(info_win, wrap=tk.WORD)
    text.insert(tk.END, info)
    text.config(state=tk.DISABLED)
    text.pack(expand=True, fill=tk.BOTH)

def show_help(parent):
    help_text = (
        "AnimePahe GUI Downloader Features:\n\n"
        "- Search for anime and view episode lists.\n"
        "- View detailed anime info.\n"
        "- Download single or multiple episodes (bulk download).\n"
        "- Downloads are saved in a folder structure: Downloads/AnimeName/SeasonX/\n"
        "- Change the default download location in Settings.\n"
        "- See download progress in the Downloading window.\n"
        "- All downloads are direct from AnimePahe sources.\n"
        "- Made By RupomPar and the AnimePahe Community.\n"
    )
    messagebox.showinfo("Help", help_text, parent=parent)

def get_airing_anime():
    url = "https://animepahe.ru/anime/airing"
    try:
        resp = session.get(url, timeout=10)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        anime_list = soup.select(".index-wrapper .index a")
        results = []
        for a in anime_list:
            title = a.get("title", "Unknown Title")
            href = a.get("href", "")
            session_id = href.split("/")[-1] if href else ""
            if session_id:
                results.append({"title": title, "session": session_id})
        return results
    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch airing anime.\n{e}")
        return []

def get_latest_anime():
    url = "https://animepahe.ru/api?m=airing&page=1"
    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        anime_list = data.get('data', [])
        results = []
        for anime in anime_list:
            title = anime.get('anime_title', 'Unknown Title')
            session_id = anime.get('anime_session', '')
            if session_id:
                results.append({"title": title, "session": session_id})
        return results
    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch latest anime.\n{e}")
        return []