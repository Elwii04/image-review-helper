import os
import shutil
import random
import time
import json
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
from PIL import Image, ImageTk, ImageFile
import piexif
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Allows loading of truncated image files without error
ImageFile.LOAD_TRUNCATED_IMAGES = True

CONFIG_FILE = "config.json"
KEEP_FOLDER = "keep"
ARCHIVE_FOLDER = "archive"
MODIFY_FOLDER = "modify"  # Renamed from "upscale" to match UI

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"use_central_folder": False, "central_folder_path": ""}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def generate_phone_name():
    return time.strftime("IMG_%Y%m%d_%H%M%S.jpg")

def save_with_random_metadata(src_path, dst_path):
    """
    Loads an image, generates new random EXIF data, and saves it to the destination.
    This version is much faster as it avoids unnecessary pixel manipulation.
    """
    phone_brands = [
        ("Apple",   ["iPhone 13", "iPhone 13 Pro", "iPhone 14", "iPhone 14 Pro", "iPhone 15", "iPhone 15 Pro"]),
        ("Samsung", ["Galaxy S22", "Galaxy S23 Ultra", "Galaxy S24", "Galaxy S24 Ultra"]),
        ("Google",  ["Pixel 6", "Pixel 7", "Pixel 8", "Pixel 9"]),
    ]
    brand, models = random.choice(phone_brands)
    model = random.choice(models)

    year = random.randint(2022, 2024)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    hour = random.randint(0, 23)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    date_time_str = f"{year}:{month:02d}:{day:02d} {hour:02d}:{minute:02d}:{second:02d}"

    try:
        with Image.open(src_path) as img:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}}

            exif_dict["0th"][piexif.ImageIFD.Make] = brand.encode('utf-8')
            exif_dict["0th"][piexif.ImageIFD.Model] = model.encode('utf-8')
            exif_dict["0th"][piexif.ImageIFD.DateTime] = date_time_str.encode('utf-8')

            exif_dict["Exif"][piexif.ExifIFD.ExposureTime] = (1, random.choice([30, 60, 125, 250, 500]))
            exif_dict["Exif"][piexif.ExifIFD.FNumber] = (random.choice([16, 18, 20]), 10) # e.g., f/1.8
            exif_dict["Exif"][piexif.ExifIFD.ISOSpeedRatings] = random.choice([100, 200, 400, 800])
            exif_dict["Exif"][piexif.ExifIFD.FocalLength] = (random.randint(24, 70), 1)
            exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_time_str.encode('utf-8')
            exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = date_time_str.encode('utf-8')

            exif_bytes = piexif.dump(exif_dict)
            img.save(dst_path, exif=exif_bytes)

    except Exception as e:
        print(f"ERROR in save_with_random_metadata for {src_path}: {e}")
        # As a fallback, just copy the file if EXIF manipulation fails
        shutil.copy2(src_path, dst_path)


class ImageReviewer(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("Image Reviewer")
        self.geometry("1000x1000")
        self.config_data = load_config()
        self.executor = ThreadPoolExecutor(max_workers=3)

        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<Drop>>", self.on_drop)

        self.top_frame = tk.Frame(self)
        self.top_frame.pack(pady=10)

        self.btn_folder = tk.Button(self.top_frame, text="Choose Folder", command=self.choose_folder)
        self.btn_folder.pack(side=tk.LEFT, padx=5)

        self.toggle_var = tk.BooleanVar(value=self.config_data.get("use_central_folder", False))
        self.btn_toggle = tk.Checkbutton(self.top_frame, text="Use Central Folder", variable=self.toggle_var, command=self.update_ui_for_folder_change)
        self.btn_toggle.pack(side=tk.LEFT, padx=5)

        self.btn_choose_central = tk.Button(self.top_frame, text="Choose Central Folder", command=self.choose_central_folder)
        self.btn_choose_central.pack(side=tk.LEFT, padx=5)

        self.info_label = tk.Label(self, text=(
            "Key Commands:\n"
            "  • Keep   -> [Right Arrow] or (k)\n"
            "  • Discard -> [Left Arrow] or (d)\n"
            "  • Modify -> [Up Arrow] or (u)"
        ), justify=tk.LEFT)
        self.info_label.pack(pady=5)

        self.current_folder_label = tk.Label(self, text="Current Folder: (none selected)")
        self.current_folder_label.pack(pady=5)

        self.image_label = tk.Label(self, text="Drag and drop a folder or choose one.")
        self.image_label.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Central folder label is created but not packed initially
        self.central_folder_label = tk.Label(self, text="", fg="blue")

        self.bind("<Right>", self.keep_image)
        self.bind("k", self.keep_image)
        self.bind("<Left>", self.discard_image)
        self.bind("d", self.discard_image)
        self.bind("<Up>", self.modify_image)
        self.bind("u", self.modify_image)

        self.image_paths = []
        self.current_index = -1
        self.current_folder = None
        self.current_img = None

        self._resize_after_id = None
        self.bind("<Configure>", self.on_window_resize)
        
        self.update_ui_for_folder_change() # Initial UI setup

    def choose_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.load_images(folder)

    def on_drop(self, event):
        # Handles single or multiple folders dropped, but uses the first valid one
        path_str = event.data.strip()
        if path_str.startswith('{') and path_str.endswith('}'):
            path_str = path_str[1:-1]
        
        # Split paths if multiple files/folders are dropped
        potential_paths = path_str.split('} {')
        for path in potential_paths:
            path = path.strip()
            if os.path.isdir(path):
                self.load_images(path)
                return # Load the first valid directory

    def load_images(self, folder_path):
        self.current_folder = Path(folder_path)
        valid_exts = [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"]
        
        try:
            self.image_paths = sorted([
                p for p in self.current_folder.iterdir()
                if p.is_file() and p.suffix.lower() in valid_exts
            ])
        except OSError as e:
            messagebox.showerror("Error", f"Could not read folder: {e}")
            return

        self.current_index = 0
        self.update_ui_for_folder_change()

        if self.image_paths:
            self.show_image()
        else:
            self.image_label.config(text="No images found in folder.", image=None)
            self.image_label.image = None
            self.current_img = None
            
    def show_image(self):
        if not (0 <= self.current_index < len(self.image_paths)):
            return
        
        path = self.image_paths[self.current_index]
        try:
            img = Image.open(path)
            self.current_img = img
            self.render_scaled_image()
        except Exception as e:
            print(f"Could not open image {path}: {e}")
            # Skip corrupted/unreadable image
            self.go_next_image()

    def render_scaled_image(self):
        if self.current_img is None:
            return

        # Use image_label's size for scaling, not the whole window
        max_w = self.image_label.winfo_width() - 20
        max_h = self.image_label.winfo_height() - 20
        if max_w < 50 or max_h < 50: # Don't render if the widget is too small
            return

        temp_img = self.current_img.copy()
        # IMPROVEMENT: Use modern resampling method
        temp_img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        
        tk_img = ImageTk.PhotoImage(temp_img)
        self.image_label.config(image=tk_img, text="")
        self.image_label.image = tk_img

    # --- Background Task Helpers ---
    def _run_in_background(self, func, *args):
        """Helper to run a function in the executor and log any exceptions."""
        future = self.executor.submit(func, *args)
        future.add_done_callback(self._task_done)

    def _task_done(self, future):
        """Callback to check for exceptions in background tasks."""
        try:
            future.result()
        except Exception as e:
            print(f"A background task failed: {e}")
            # Optionally, show an error to the user
            # messagebox.showerror("Background Error", f"An operation failed:\n{e}")

    def _perform_keep_image(self, img_path, base_out_dir):
        keep_folder = base_out_dir / KEEP_FOLDER
        archive_folder = base_out_dir / ARCHIVE_FOLDER
        keep_folder.mkdir(parents=True, exist_ok=True)
        archive_folder.mkdir(parents=True, exist_ok=True)

        new_filename = generate_phone_name()
        keep_dst = keep_folder / new_filename
        save_with_random_metadata(img_path, keep_dst)

        archive_dst = archive_folder / img_path.name
        shutil.copy2(img_path, archive_dst)

    def _perform_modify_image(self, img_path, base_out_dir):
        modify_folder = base_out_dir / MODIFY_FOLDER
        archive_folder = base_out_dir / ARCHIVE_FOLDER
        modify_folder.mkdir(parents=True, exist_ok=True)
        archive_folder.mkdir(parents=True, exist_ok=True)

        # Simply copy the file for "modify"
        modify_dst = modify_folder / img_path.name
        shutil.copy2(img_path, modify_dst)
        archive_dst = archive_folder / img_path.name
        shutil.copy2(img_path, archive_dst)

    # --- Button/Key Handlers (BUG FIX APPLIED HERE) ---
    def _handle_image_action(self, action_func):
        if not (0 <= self.current_index < len(self.image_paths)):
            return
            
        img_path = self.image_paths[self.current_index]
        base_output_dir = self.get_base_out()

        if base_output_dir is None:
            messagebox.showwarning("Warning", "No output folder selected. Please choose a folder or a central folder.")
            return

        # Perform action in background with all necessary data
        self._run_in_background(action_func, img_path, base_output_dir)
        
        # UI moves on immediately
        self.go_next_image()

    def keep_image(self, event=None):
        self._handle_image_action(self._perform_keep_image)

    def discard_image(self, event=None):
        if not (0 <= self.current_index < len(self.image_paths)):
            return
        self.go_next_image()

    def modify_image(self, event=None):
        self._handle_image_action(self._perform_modify_image)

    def go_next_image(self):
        self.current_index += 1
        if self.current_index < len(self.image_paths):
            self.show_image()
        else:
            self.image_label.config(text="No more images to review.", image=None)
            self.image_label.image = None
            self.current_img = None
            messagebox.showinfo("Done", "You have reviewed all images in the folder.")

    # --- UI Helpers ---
    def on_window_resize(self, event):
        if self._resize_after_id:
            self.after_cancel(self._resize_after_id)
        self._resize_after_id = self.after(150, self.render_scaled_image) # Reduced delay

    def update_ui_for_folder_change(self):
        use_central = self.toggle_var.get()
        central_path = self.config_data.get("central_folder_path", "")
        
        self.config_data["use_central_folder"] = use_central
        save_config(self.config_data)

        if use_central and central_path:
            self.current_folder_label.config(text="(Using Central Folder)")
            self.central_folder_label.config(text=f"Central Folder: {central_path}")
            self.central_folder_label.pack(after=self.current_folder_label, pady=2)
        else:
            self.central_folder_label.pack_forget()
            if self.current_folder:
                self.current_folder_label.config(text=f"Current Folder: {self.current_folder}")
            else:
                self.current_folder_label.config(text="Current Folder: (none selected)")

    def choose_central_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.config_data["central_folder_path"] = folder
            self.update_ui_for_folder_change()

    def get_base_out(self):
        if self.toggle_var.get() and self.config_data.get("central_folder_path"):
            return Path(self.config_data["central_folder_path"])
        if self.current_folder:
            return self.current_folder
        return None

def main():
    app = ImageReviewer()
    app.mainloop()

if __name__ == "__main__":
    main()