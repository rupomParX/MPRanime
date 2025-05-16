import tkinter as tk
from PIL import Image, ImageTk
import os
import sys

# Theme colors
TOP_BAR_BG = "#ffb6c1"  # light pink
TOP_BAR_FG = "#ffffff"  # white text
BG_COLOR = "#f8f8fa"    # very light background

BLACK_TOP_BAR_BG = "#222222"
BLACK_TOP_BAR_FG = "#ffffff"
BLACK_BG_COLOR = "#111111"

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Path to your background image (should be in the same folder as gui_app.py)
BG_IMAGE_PATH = resource_path("6156608.jpg")

def set_theme(root):
    # Set window background color
    root.configure(bg=BG_COLOR)
    # Set all children backgrounds recursively
    for widget in root.winfo_children():
        try:
            widget.configure(bg=BG_COLOR)
        except Exception:
            pass

def set_black_theme(root):
    root.configure(bg=BLACK_BG_COLOR)
    for widget in root.winfo_children():
        try:
            widget.configure(bg=BLACK_BG_COLOR)
        except Exception:
            pass

def set_topbar_style(widget, black=True):
    if black:
        widget.configure(bg=BLACK_TOP_BAR_BG, fg=BLACK_TOP_BAR_FG)
    else:
        widget.configure(bg=TOP_BAR_BG, fg=TOP_BAR_FG)

def set_background_image(root):
    # Place a transparent background image (if exists)
    if os.path.exists(BG_IMAGE_PATH):
        root.update_idletasks()
        width = root.winfo_screenwidth()
        height = root.winfo_screenheight()
        img = Image.open(BG_IMAGE_PATH).convert("RGBA")
        try:
            resample = Image.LANCZOS
        except AttributeError:
            resample = Image.ANTIALIAS
        img = img.resize((width, height), resample)
        # Set alpha for transparency (lower alpha = more transparent)
        alpha = 250  # 0=fully transparent, 255=opaque. Try 40-80 for more transparency.
        # Apply alpha to the whole image
        r, g, b, a = img.split()
        a = a.point(lambda i: alpha)
        img = Image.merge('RGBA', (r, g, b, a))
        bg_img = ImageTk.PhotoImage(img)
        if not hasattr(root, "_bg_img_refs"):
            root._bg_img_refs = []
        # Use a valid color name for bg (do not use empty string)
        label = tk.Label(root, image=bg_img, bg=BG_COLOR, borderwidth=0, highlightthickness=0)
        label.image = bg_img
        root._bg_img_refs.append(bg_img)
        label.place(x=0, y=0, relwidth=1, relheight=1)
        label.lower()
        return label
    return None
