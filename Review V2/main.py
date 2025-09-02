import os
import shutil
import random
import time
import json
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
from tkinterdnd2 import DND_FILES, TkinterDnD
from PIL import Image, ImageTk
import piexif
from concurrent.futures import ThreadPoolExecutor

# --- Fallback for different Pillow versions ---
try:
    # Pillow 9.1+ uses Image.Resampling.LANCZOS
    LANCZOS = Image.Resampling.LANCZOS
except AttributeError:
    # Older Pillow still uses Image.LANCZOS
    LANCZOS = Image.LANCZOS

CONFIG_FILE = "config.json"

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
    phone_brands = [
        ("Apple",   ["iPhone 13", "iPhone 13 Pro", "iPhone 14", "iPhone 14 Pro", "iPhone 15", "iPhone 15 Pro"]),
        ("Samsung", ["Galaxy S22", "Galaxy S22 Plus", "Galaxy S22 Ultra", 
                     "Galaxy S23", "Galaxy S23 Plus", "Galaxy S23 Ultra", 
                     "Galaxy S24", "Galaxy S24 Plus", "Galaxy S24 Ultra", 
                     "Galaxy S25", "Galaxy S25 Plus", "Galaxy S25 Ultra"]),
        ("Google",  ["Pixel 6", "Pixel 7", "Pixel 8", "Pixel 9"]),
    ]
    brand, models = random.choice(phone_brands)
    model = random.choice(models)

    year = random.randint(2020, 2024)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    hour = random.randint(0, 23)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    date_time_str = f"{year}:{month:02d}:{day:02d} {hour:02d}:{minute:02d}:{second:02d}"

    with Image.open(src_path) as img:
        data = list(img.getdata())
        new_img = Image.new(img.mode, img.size)
        new_img.putdata(data)

        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}}
        exif_dict["0th"][piexif.ImageIFD.Make] = brand
        exif_dict["0th"][piexif.ImageIFD.Model] = model
        exif_dict["0th"][piexif.ImageIFD.DateTime] = date_time_str

        exif_dict["Exif"][piexif.ExifIFD.ExposureTime] = (1, random.choice([30, 60, 125, 250, 500]))
        exif_dict["Exif"][piexif.ExifIFD.FNumber] = (17, 10)
        exif_dict["Exif"][piexif.ExifIFD.ISOSpeedRatings] = random.choice([100, 200, 400, 800])
        exif_dict["Exif"][piexif.ExifIFD.FocalLength] = (400, 100)  
        exif_dict["Exif"][piexif.ExifIFD.DigitalZoomRatio] = (random.choice([10, 15, 20]), 10)

        exif_bytes = piexif.dump(exif_dict)
        new_img.save(dst_path, exif=exif_bytes, quality=95, subsampling=0, optimize=True)

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

        self.toggle_var = tk.BooleanVar(value=self.config_data["use_central_folder"])
        self.btn_toggle = tk.Checkbutton(
            self.top_frame, 
            text="Use Central Folder", 
            variable=self.toggle_var,
            command=self.toggle_central_folder
        )
        self.btn_toggle.pack(side=tk.LEFT, padx=5)

        self.btn_choose_central = tk.Button(
            self.top_frame, 
            text="Choose Central Folder",
            command=self.choose_central_folder
        )
        self.btn_choose_central.pack(side=tk.LEFT, padx=5)

        self.info_label = tk.Label(
            self,
            text=(
                "Key Commands:\n"
                "  • Keep    -> [Right Arrow] or (k)\n"
                "  • Discard -> [Left Arrow]  or (d)\n"
                "  • Modify  -> [Up Arrow]    or (u)"
            ),
            justify=tk.LEFT
        )
        self.info_label.pack(pady=5)

        self.current_folder_label = tk.Label(self, text="Current Folder: (none selected)")
        self.current_folder_label.pack(pady=5)

        # Frame to hold main image + preview
        self.image_frame = tk.Frame(self)
        self.image_frame.pack(pady=5)

        # Main image
        self.image_label = tk.Label(self.image_frame, text="Drag and drop a folder or choose one.")
        self.image_label.pack(side=tk.LEFT, padx=10)

        # Preview image (placed to the right of the main image)
        self.preview_label = tk.Label(self.image_frame)
        self.preview_label.pack(side=tk.LEFT, padx=10)

        self.central_folder_label = tk.Label(self, text="", fg="blue")

        self.bind("<Right>", self.keep_image)
        self.bind("k", self.keep_image)
        self.bind("<Left>", self.discard_image)
        self.bind("d", self.discard_image)
        self.bind("<Up>", self.modify_image)
        self.bind("u", self.modify_image)

        self.image_paths = []
        self.current_index = 0
        self.current_folder = None
        self.current_img = None

        self._resize_after_id = None
        self.bind("<Configure>", self.on_window_resize)

    def choose_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.load_images(folder)

    def on_drop(self, event):
        folder = event.data.strip("{}")
        if os.path.isdir(folder):
            self.load_images(folder)

    def load_images(self, folder):
        self.current_folder = folder
        self.show_top_ui()

        valid_exts = [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"]
        all_files = os.listdir(folder)
        self.image_paths = [
            os.path.join(folder, f)
            for f in all_files
            if os.path.splitext(f)[1].lower() in valid_exts
        ]
        self.image_paths.sort()
        self.current_index = 0

        if self.toggle_var.get() and self.config_data["central_folder_path"]:
            self.current_folder_label.config(text="(Using Central Folder)")
        else:
            self.current_folder_label.config(text=f"Current Folder: {folder}")

        if self.toggle_var.get() and self.config_data["central_folder_path"]:
            self.central_folder_label.config(
                text=f"Central Folder: {self.config_data['central_folder_path']}"
            )
            self.central_folder_label.pack(pady=5)
        else:
            self.central_folder_label.pack_forget()

        if self.image_paths:
            self.show_image()
        else:
            self.image_label.config(text="No images found in folder.", image=None)
            self.image_label.image = None

    def show_image(self):
        if not self.image_paths:
            return
        path = self.image_paths[self.current_index]
        self.current_img = Image.open(path)
        self.render_scaled_image()

    def render_scaled_image(self):
        if not self.current_img:
            return

        max_w = self.winfo_width() - 50
        max_h = self.winfo_height() - 150
        if max_w < 100 or max_h < 100:
            return

        # Scale current image
        temp_img = self.current_img.copy()
        temp_img.thumbnail((max_w, max_h), LANCZOS)
        tk_img = ImageTk.PhotoImage(temp_img)
        self.image_label.config(image=tk_img, text="")
        self.image_label.image = tk_img

        # Scale next image for preview
        if self.current_index + 1 < len(self.image_paths):
            next_path = self.image_paths[self.current_index + 1]
            try:
                next_img = Image.open(next_path)
                preview_img = next_img.copy()
                preview_img.thumbnail((200, 200), LANCZOS)
                tk_preview = ImageTk.PhotoImage(preview_img)
                self.preview_label.config(image=tk_preview, text="")
                self.preview_label.image = tk_preview
            except:
                self.preview_label.config(image="", text="")
        else:
            self.preview_label.config(image="", text="")

    def _perform_keep_image(self, img_path):
        base_out = self.get_base_out()
        keep_folder = os.path.join(base_out, "keep")
        archive_folder = os.path.join(base_out, "archive")
        os.makedirs(keep_folder, exist_ok=True)
        os.makedirs(archive_folder, exist_ok=True)

        new_filename = generate_phone_name()
        keep_dst = os.path.join(keep_folder, new_filename)
        save_with_random_metadata(img_path, keep_dst)

        archive_dst = os.path.join(archive_folder, os.path.basename(img_path))
        shutil.copy2(img_path, archive_dst)

    def _perform_modify_image(self, img_path):
        base_out = self.get_base_out()
        modify_folder = os.path.join(base_out, "modify")
        archive_folder = os.path.join(base_out, "archive")
        os.makedirs(modify_folder, exist_ok=True)
        os.makedirs(archive_folder, exist_ok=True)

        new_filename = generate_phone_name()
        modify_dst = os.path.join(modify_folder, new_filename)
        save_with_random_metadata(img_path, modify_dst)

        archive_dst = os.path.join(archive_folder, os.path.basename(img_path))
        shutil.copy2(img_path, archive_dst)

    def keep_image(self, event):
        if not self.image_paths:
            return
        img_path = self.image_paths[self.current_index]
        self.go_next_image()
        self.executor.submit(self._perform_keep_image, img_path)

    def discard_image(self, event):
        if not self.image_paths:
            return
        self.go_next_image()

    def modify_image(self, event):
        if not self.image_paths:
            return
        img_path = self.image_paths[self.current_index]
        self.go_next_image()
        self.executor.submit(self._perform_modify_image, img_path)

    def go_next_image(self):
        self.current_index += 1
        if self.current_index < len(self.image_paths):
            self.show_image()
        else:
            self.image_label.config(text="No more images to review.", image=None)
            self.image_label.image = None
            self.current_img = None
            self.preview_label.config(image="", text="")
            self.show_top_ui()

    def on_window_resize(self, event):
        if self._resize_after_id is not None:
            self.after_cancel(self._resize_after_id)
        self._resize_after_id = self.after(200, self.render_scaled_image)

    def show_top_ui(self):
        self.top_frame.pack(pady=10)
        self.info_label.pack(pady=5)
        self.current_folder_label.pack(pady=5)
        if self.toggle_var.get() and self.config_data["central_folder_path"]:
            self.central_folder_label.config(text=f"Central Folder: {self.config_data['central_folder_path']}")
            self.central_folder_label.pack(pady=5)
        else:
            self.central_folder_label.pack_forget()

    def toggle_central_folder(self):
        self.config_data["use_central_folder"] = self.toggle_var.get()
        save_config(self.config_data)
        if self.toggle_var.get() and self.config_data["central_folder_path"]:
            self.central_folder_label.config(text=f"Central Folder: {self.config_data['central_folder_path']}")
            self.central_folder_label.pack(pady=5)
            self.current_folder_label.config(text="(Using Central Folder)")
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
            save_config(self.config_data)
            if self.toggle_var.get():
                self.central_folder_label.config(text=f"Central Folder: {folder}")
                self.central_folder_label.pack(pady=5)
            else:
                self.central_folder_label.pack_forget()

    def get_base_out(self):
        if self.toggle_var.get() and self.config_data["central_folder_path"]:
            return self.config_data["central_folder_path"]
        return self.current_folder

def main():
    app = ImageReviewer()
    app.mainloop()

if __name__ == "__main__":
    main()
