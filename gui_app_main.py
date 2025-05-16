import tkinter as tk
from tkinter import messagebox
import os
import sys
from PIL import Image, ImageTk
from gui_app_core import AnimeDownloaderApp

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

if __name__ == "__main__":
    try:
        from PIL import Image, ImageTk
    except ImportError:
        messagebox.showerror("Missing Dependency", "Please install Pillow: pip install pillow")
        exit(1)
    root = tk.Tk()
    root.title("RupomPar Anime Downloader")  # <-- Change this to your desired app name
    # Set application icon if applogo.png exists
    app_icon_path = resource_path("applogo.png")
    if os.path.exists(app_icon_path):
        try:
            icon_img = Image.open(app_icon_path)
            icon_img = icon_img.resize((64, 64))  # Resize for icon if needed
            icon = ImageTk.PhotoImage(icon_img)
            root.iconphoto(True, icon)
        except Exception:
            pass  # Ignore icon errors
    app = AnimeDownloaderApp(root)
    root.mainloop()
