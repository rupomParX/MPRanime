import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import threading
import os
import queue
from gui_theme import set_theme, set_topbar_style, set_background_image
from gui_app_utils import (
    search_anime, get_episodes, get_download_links, download_anime,
    get_anime_info, get_manga_info, show_help, get_airing_anime, get_latest_anime,
    download_progress, sanitize_folder_name, download_dir,
    extract_kwik_link, get_dl_link
)

class DownloadProgressWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Downloading")
        self.geometry("400x300")
        self.tree = ttk.Treeview(self, columns=("file", "progress"), show="headings")
        self.tree.heading("file", text="File")
        self.tree.heading("progress", text="Progress")
        self.tree.pack(expand=True, fill=tk.BOTH)
        self.after(500, self.update_progress)

    def update_progress(self):
        self.tree.delete(*self.tree.get_children())
        for qid, status in download_progress.items():
            fname = os.path.basename(qid)
            if isinstance(status, tuple):
                downloaded, total = status
                percent = f"{(downloaded/total*100):.1f}%" if total else "?"
                prog = f"{downloaded//1024//1024}MB / {total//1024//1024}MB ({percent})"
            elif status == 'done':
                prog = "Done"
            elif isinstance(status, str) and status.startswith('error:'):
                prog = status
            else:
                prog = "Queued"
            self.tree.insert("", tk.END, values=(fname, prog))
        self.after(1000, self.update_progress)

class AnimeDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RMP Ani Downloder")
        self.root.geometry("800x600")

        # Set theme and background image
        set_theme(root)
        self.bg_label = set_background_image(root)

        # Menu bar
        menubar = tk.Menu(root, bg="#ffb6c1", fg="#ffffff")  # pink top bar
        settings_menu = tk.Menu(menubar, tearoff=0, bg="#ffb6c1", fg="#ffffff")
        settings_menu.add_command(label="Change Download Location", command=self.change_download_dir)
        settings_menu.add_command(label="Help", command=lambda: show_help(self.root))
        menubar.add_cascade(label="Settings", menu=settings_menu)
        root.config(menu=menubar)

        # Top bar styling for search label
        top_label = tk.Label(root, text="Search Anime:", bg="#ffb6c1", fg="#ffffff", font=("Arial", 12, "bold"))
        top_label.pack(pady=5)
        # Search bar
        self.search_var = tk.StringVar()
        search_frame = tk.Frame(root, bg="#ffb6c1")
        search_frame.pack()
        tk.Entry(search_frame, textvariable=self.search_var, width=40).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search", command=self.do_search, bg="#ffb6c1", fg="#ffffff").pack(side=tk.LEFT)
        tk.Button(search_frame, text="Downloading", command=self.open_progress_window, bg="#ffb6c1", fg="#ffffff").pack(side=tk.LEFT, padx=10)

        # Airing and Latest buttons
        airing_frame = tk.Frame(root, bg="#ffb6c1")
        airing_frame.pack()
        tk.Button(airing_frame, text="Airing", command=self.show_airing, bg="#ffb6c1", fg="#ffffff").pack(side=tk.LEFT, padx=5)
        tk.Button(airing_frame, text="Latest", command=self.show_latest, bg="#ffb6c1", fg="#ffffff").pack(side=tk.LEFT, padx=5)

        # Anime list
        self.anime_listbox = tk.Listbox(root, width=80, height=10)
        self.anime_listbox.pack(pady=10)
        self.anime_listbox.bind('<<ListboxSelect>>', self.on_anime_select)

        # Anime info and manga info buttons
        info_frame = tk.Frame(root)
        info_frame.pack()
        self.info_button = tk.Button(info_frame, text="Anime Info", command=self.show_anime_info, state=tk.DISABLED)
        self.info_button.pack(side=tk.LEFT, padx=5)
        self.manga_button = tk.Button(info_frame, text="Manga Info", command=self.show_manga_info, state=tk.DISABLED)
        self.manga_button.pack(side=tk.LEFT, padx=5)

        # Episodes list (with multi-select)
        tk.Label(root, text="Episodes: (Ctrl+Click for multi-select)").pack()
        self.episodes_frame = tk.Frame(root)
        self.episodes_frame.pack()
        self.episodes_listbox = tk.Listbox(self.episodes_frame, width=80, height=10, selectmode=tk.EXTENDED)
        self.episodes_listbox.pack(side=tk.LEFT)
        self.episodes_listbox.bind('<<ListboxSelect>>', self.on_episode_select)
        # Pagination controls
        self.episode_page = 1
        self.episodes_per_page = 30
        self.episode_nav_frame = tk.Frame(self.episodes_frame)
        self.episode_nav_frame.pack(side=tk.LEFT, padx=5)
        self.prev_ep_btn = tk.Button(self.episode_nav_frame, text="<< Prev", command=self.prev_episode_page, state=tk.DISABLED)
        self.prev_ep_btn.pack(pady=2)
        self.page_label = tk.Label(self.episode_nav_frame, text="", width=8)
        self.page_label.pack(pady=2)
        self.next_ep_btn = tk.Button(self.episode_nav_frame, text="Next >>", command=self.next_episode_page, state=tk.DISABLED)
        self.next_ep_btn.pack(pady=2)

        # Download links list
        tk.Label(root, text="Available Downloads:").pack()
        self.downloads_listbox = tk.Listbox(root, width=80, height=5, selectmode=tk.EXTENDED)
        self.downloads_listbox.pack(pady=10)
        self.downloads_listbox.bind('<<ListboxSelect>>', self.on_download_select)

        # Download buttons
        btn_frame = tk.Frame(root)
        btn_frame.pack()
        tk.Button(btn_frame, text="Download Selected", command=self.download_selected).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Bulk Download All Selected Episodes", command=self.bulk_download).pack(side=tk.LEFT, padx=5)

        # Bulk download options
        self.bulk_quality = tk.StringVar(value="720p")
        self.bulk_language = tk.StringVar(value="jap")
        bulk_opts = tk.Frame(root)
        bulk_opts.pack()
        tk.Label(bulk_opts, text="Bulk Quality:").pack(side=tk.LEFT)
        ttk.Combobox(bulk_opts, textvariable=self.bulk_quality, values=["1080p", "720p", "360p"], width=6, state="readonly").pack(side=tk.LEFT)
        tk.Label(bulk_opts, text="Language:").pack(side=tk.LEFT)
        ttk.Combobox(bulk_opts, textvariable=self.bulk_language, values=["jap", "eng"], width=4, state="readonly").pack(side=tk.LEFT)

        # State
        self.anime_results = []
        self.episode_results = []
        self.episode_page = 1
        self.episodes_per_page = 30
        self.download_links = []
        self.selected_anime = None
        self.selected_episodes = []
        self.selected_downloads = []
        self.bulk_thread = None
        self.bulk_queue = queue.Queue()
        self.bulk_downloading = False
        self.airing_results = []
        self.latest_results = []
        self.list_mode = "search"  # can be "search", "airing", "latest"

    def do_search(self):
        query = self.search_var.get().strip()
        if not query:
            messagebox.showwarning("Input Needed", "Please enter an anime name.")
            return
        self.anime_results = search_anime(query)
        self.list_mode = "search"
        self.anime_listbox.delete(0, tk.END)
        for anime in self.anime_results:
            self.anime_listbox.insert(tk.END, f"{anime['title']} ({anime['type']}, {anime['year']})")
        self.episodes_listbox.delete(0, tk.END)
        self.downloads_listbox.delete(0, tk.END)
        self.selected_anime = None
        self.selected_episodes = []
        self.info_button.config(state=tk.DISABLED)
        self.manga_button.config(state=tk.DISABLED)

    def on_anime_select(self, event):
        idx = self.anime_listbox.curselection()
        if not idx:
            self.info_button.config(state=tk.DISABLED)
            self.manga_button.config(state=tk.DISABLED)
            return
        index = idx[0]
        self.episodes_listbox.delete(0, tk.END)
        self.downloads_listbox.delete(0, tk.END)
        self.selected_episodes = []
        self.download_links = []
        if self.list_mode == "airing":
            if index >= len(self.airing_results):
                return
            anime = self.airing_results[index]
        elif self.list_mode == "latest":
            if index >= len(self.latest_results):
                return
            anime = self.latest_results[index]
        else:
            if index >= len(self.anime_results):
                return
            anime = self.anime_results[index]
        self.selected_anime = anime
        self.episode_results = get_episodes(anime['session'])
        self.episode_page = 1
        self.show_episode_page()
        self.downloads_listbox.delete(0, tk.END)
        self.selected_episodes = []
        self.download_links = []
        self.info_button.config(state=tk.NORMAL)
        self.manga_button.config(state=tk.NORMAL)

    def show_episode_page(self):
        self.episodes_listbox.delete(0, tk.END)
        total_eps = len(self.episode_results)
        # --- Fix: calculate total_pages and show only 30 per page, but fetch ALL episodes for all pages ---
        # If only 30 episodes are loaded, try to fetch all pages if possible
        if hasattr(self.selected_anime, 'session'):
            session_id = self.selected_anime['session']
        elif self.selected_anime and 'session' in self.selected_anime:
            session_id = self.selected_anime['session']
        else:
            session_id = None
        # If we have less than all episodes, try to fetch all pages
        if total_eps == 30 and session_id:
            # Try to fetch all pages using the same logic as gui_app.py
            try:
                from plugins.headers import session as _session
                url = f"https://animepahe.ru/api?m=release&id={session_id}&sort=episode_asc&page=1"
                resp = _session.get(url, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                episodes = data.get('data', [])
                last_page = int(data.get('last_page', 1))
                for page in range(2, last_page + 1):
                    page_url = f"https://animepahe.ru/api?m=release&id={session_id}&sort=episode_asc&page={page}"
                    resp = _session.get(page_url, timeout=10)
                    resp.raise_for_status()
                    page_data = resp.json()
                    episodes.extend(page_data.get('data', []))
                self.episode_results = episodes
                total_eps = len(self.episode_results)
            except Exception:
                pass
        total_pages = max(1, (total_eps + self.episodes_per_page - 1) // self.episodes_per_page)
        start = (self.episode_page - 1) * self.episodes_per_page
        end = min(start + self.episodes_per_page, total_eps)
        for ep in self.episode_results[start:end]:
            self.episodes_listbox.insert(tk.END, f"Episode {ep['episode']}")
        self.prev_ep_btn.config(state=tk.NORMAL if self.episode_page > 1 else tk.DISABLED)
        self.next_ep_btn.config(state=tk.NORMAL if self.episode_page < total_pages else tk.DISABLED)
        self.page_label.config(text=f"Page {self.episode_page}/{total_pages}")

    def next_episode_page(self):
        total_eps = len(self.episode_results)
        total_pages = max(1, (total_eps + self.episodes_per_page - 1) // self.episodes_per_page)
        if self.episode_page < total_pages:
            self.episode_page += 1
            self.show_episode_page()

    def prev_episode_page(self):
        if self.episode_page > 1:
            self.episode_page -= 1
            self.show_episode_page()

    def show_anime_info(self):
        if self.selected_anime:
            get_anime_info(self.selected_anime['title'], self.root)

    def show_manga_info(self):
        if self.selected_anime:
            get_manga_info(self.selected_anime['title'], self.root)

    def on_episode_select(self, event):
        idxs = self.episodes_listbox.curselection()
        # Map visible indices to actual episode indices
        start = (self.episode_page - 1) * self.episodes_per_page
        self.selected_episodes = [self.episode_results[start + i] for i in idxs] if idxs else []
        self.download_links = []
        self.downloads_listbox.delete(0, tk.END)
        if len(self.selected_episodes) == 1:
            ep = self.selected_episodes[0]
            self.download_links = get_download_links(self.selected_anime['session'], ep['session'])
            for title, _ in self.download_links:
                self.downloads_listbox.insert(tk.END, title)

    def on_download_select(self, event):
        idxs = self.downloads_listbox.curselection()
        if not idxs or not self.selected_episodes:
            return
        ep = self.selected_episodes[0]
        anime_title = self.selected_anime['title']
        # Sanitize anime folder name to avoid Windows errors
        safe_anime_title = sanitize_folder_name(anime_title)
        season = "season1"
        anime_folder = os.path.join(download_dir[0], safe_anime_title, season)
        os.makedirs(anime_folder, exist_ok=True)
        # Run download in a thread to avoid GUI freeze
        def download_selected_links():
            for i in idxs:
                title, url = self.download_links[i]
                # Always use kwik.py and direct_link.py for download
                kwik_link = extract_kwik_link(url)
                if not kwik_link or kwik_link.startswith("Error") or "No kwik.si" in kwik_link:
                    download_progress[f"{anime_title}-ep{ep['episode']}-{title}"] = f"error: Could not extract kwik.si link"
                    continue
                try:
                    direct_link = get_dl_link(kwik_link)
                except Exception as e:
                    download_progress[f"{anime_title}-ep{ep['episode']}-{title}"] = f"error: {e}"
                    continue
                filename = f"{anime_title} - Episode {ep['episode']} - {title}.mp4"
                filename = "".join(x for x in filename if x not in r'<>:"/\|?*')
                save_path = os.path.join(anime_folder, filename)
                qid = save_path
                download_progress[qid] = (0, 0)
                download_anime(direct_link, save_path, qid)
            self.downloads_listbox.selection_clear(0, tk.END)
        threading.Thread(target=download_selected_links, daemon=True).start()

    def download_selected(self):
        idxs = self.downloads_listbox.curselection()
        if not idxs or not self.selected_episodes:
            messagebox.showwarning("Select", "Select an episode and a download link.")
            return
        ep = self.selected_episodes[0]
        anime_title = self.selected_anime['title']
        safe_anime_title = sanitize_folder_name(anime_title)
        season = "season1"  # Could be improved if season info is available
        anime_folder = os.path.join(download_dir[0], safe_anime_title, season)
        os.makedirs(anime_folder, exist_ok=True)
        def download_selected_links():
            for i in idxs:
                title, url = self.download_links[i]
                kwik_link = extract_kwik_link(url)
                if not kwik_link or kwik_link.startswith("Error") or "No kwik.si" in kwik_link:
                    download_progress[f"{anime_title}-ep{ep['episode']}-{title}"] = f"error: Could not extract kwik.si link"
                    continue
                try:
                    direct_link = get_dl_link(kwik_link)
                except Exception as e:
                    download_progress[f"{anime_title}-ep{ep['episode']}-{title}"] = f"error: {e}"
                    continue
                filename = f"{anime_title} - Episode {ep['episode']} - {title}.mp4"
                filename = "".join(x for x in filename if x not in r'<>:"/\|?*')
                save_path = os.path.join(anime_folder, filename)
                qid = save_path
                download_progress[qid] = (0, 0)
                download_anime(direct_link, save_path, qid)
            self.downloads_listbox.selection_clear(0, tk.END)
        threading.Thread(target=download_selected_links, daemon=True).start()

    def bulk_download(self):
        if not self.selected_episodes:
            messagebox.showwarning("Select", "Select episodes for bulk download.")
            return
        if self.bulk_downloading:
            messagebox.showinfo("Bulk Download", "Bulk download already in progress.")
            return
        anime_title = self.selected_anime['title']
        safe_anime_title = sanitize_folder_name(anime_title)
        season = "season1"
        anime_folder = os.path.join(download_dir[0], safe_anime_title, season)
        os.makedirs(anime_folder, exist_ok=True)
        quality = self.bulk_quality.get()
        lang = self.bulk_language.get()
        # Fill the queue
        self.bulk_queue = queue.Queue()
        for ep in self.selected_episodes:
            links = get_download_links(self.selected_anime['session'], ep['session'])
            if not links:
                continue
            # Filter by quality and language
            found = False
            for title, url in links:
                if quality in title and (lang == "jap" and "eng" not in title.lower() or lang == "eng" and "eng" in title.lower()):
                    self.bulk_queue.put((anime_title, ep['episode'], title, url, anime_folder))
                    found = True
                    break
            if not found:
                # fallback: add first link if nothing matches
                title, url = links[0]
                self.bulk_queue.put((anime_title, ep['episode'], title, url, anime_folder))
        # Start background thread for sequential download
        self.bulk_downloading = True
        self.bulk_thread = threading.Thread(target=self._bulk_download_worker, daemon=True)
        self.bulk_thread.start()

    def _bulk_download_worker(self):
        while not self.bulk_queue.empty():
            anime_title, ep_num, title, url, anime_folder = self.bulk_queue.get()
            kwik_link = extract_kwik_link(url)
            if not kwik_link or kwik_link.startswith("Error") or "No kwik.si" in kwik_link:
                download_progress[f"{anime_title}-ep{ep_num}-{title}"] = f"error: Could not extract kwik.si link"
                continue
            try:
                direct_link = get_dl_link(kwik_link)
            except Exception as e:
                download_progress[f"{anime_title}-ep{ep_num}-{title}"] = f"error: {e}"
                continue
            filename = f"{anime_title} - Episode {ep_num} - {title}.mp4"
            filename = "".join(x for x in filename if x not in r'<>:"/\|?*')
            save_path = os.path.join(anime_folder, filename)
            qid = save_path
            download_progress[qid] = (0, 0)
            download_anime(direct_link, save_path, qid)
        self.bulk_downloading = False

    def open_progress_window(self):
        DownloadProgressWindow(self.root)

    def change_download_dir(self):
        new_dir = filedialog.askdirectory(title="Select Download Folder")
        if new_dir:
            download_dir[0] = new_dir
            messagebox.showinfo("Download Folder Changed", f"New download folder:\n{new_dir}")

    def show_airing(self):
        self.airing_results = get_airing_anime()
        self.list_mode = "airing"
        self.anime_listbox.delete(0, tk.END)
        for anime in self.airing_results:
            self.anime_listbox.insert(tk.END, anime['title'])
        self.episodes_listbox.delete(0, tk.END)
        self.downloads_listbox.delete(0, tk.END)
        self.selected_anime = None
        self.selected_episodes = []
        self.info_button.config(state=tk.DISABLED)
        self.manga_button.config(state=tk.DISABLED)

    def show_latest(self):
        self.latest_results = get_latest_anime()
        self.list_mode = "latest"
        self.anime_listbox.delete(0, tk.END)
        for anime in self.latest_results:
            self.anime_listbox.insert(tk.END, anime['title'])
        self.episodes_listbox.delete(0, tk.END)
        self.downloads_listbox.delete(0, tk.END)
        self.selected_anime = None
        self.selected_episodes = []
        self.info_button.config(state=tk.DISABLED)
        self.manga_button.config(state=tk.DISABLED)