import os
import shutil
import random
import json
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import filedialog, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
from PIL import Image, ImageTk, ImageFilter, ImageOps
import piexif
import numpy as np
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
    """Loads configuration from a JSON file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    # Default values
    return {
        "use_central_folder": False, 
        "central_folder_path": "",
        "jpeg_quality": 85,
        "apply_realism_effects": True,
    }

def save_config(config):
    """Saves configuration to a JSON file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def generate_todays_datetime():
    """Generates today's datetime with a random time during the day."""
    today = datetime.now().date()
    random_time = datetime.combine(today, datetime.min.time()) + timedelta(
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59)
    )
    return random_time

def generate_random_datetime(start_year=2021, end_year=2024):
    """Generates a random datetime object and a formatted string."""
    start_date = datetime(start_year, 1, 1)
    end_date = datetime(end_year, 12, 28)
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_number_of_days = random.randrange(days_between_dates)
    random_date = start_date + timedelta(days=random_number_of_days, 
                                          hours=random.randint(0, 23),
                                          minutes=random.randint(0, 59),
                                          seconds=random.randint(0, 59))
    return random_date

def generate_random_gps():
    """Generates random plausible GPS coordinates (e.g., within a city)."""
    # Example: Random coordinates roughly within Los Angeles
    lat = random.uniform(34.0, 34.1)
    lon = random.uniform(-118.3, -118.2)
    
    def to_deg_min_sec(d):
        d = abs(d)
        deg = int(d)
        min = int((d - deg) * 60)
        sec = int(((d - deg) * 60 - min) * 3600 * 100)
        return ((deg, 1), (min, 1), (sec, 100))

    return {
        piexif.GPSIFD.GPSLatitudeRef: 'N' if lat > 0 else 'S',
        piexif.GPSIFD.GPSLatitude: to_deg_min_sec(lat),
        piexif.GPSIFD.GPSLongitudeRef: 'E' if lon > 0 else 'W',
        piexif.GPSIFD.GPSLongitude: to_deg_min_sec(lon),
    }
    
def apply_realism_effects(img):
    """
    Applies a chain of refined effects based on user feedback.
    - Luminance-dependent noise (more noise in shadows, less in highlights).
    - No more global blur.
    - Subtler chromatic aberration.
    """
    # Ensure we are working with an RGB image
    if img.mode != 'RGB':
        img = img.convert('RGB')
        
    # 1. Luminance-Dependent Noise
    np_img = np.array(img).astype(np.float32)
    
    # Create a grayscale version to determine brightness (0=black, 255=white)
    luminance = np.array(img.convert('L')).astype(np.float32)
    
    # Create a "noise mask": Brighter areas get a smaller multiplier, darker areas get a larger one.
    # We invert luminance (255 - lum) so dark areas have high values.
    # The strength factor (e.g., / 255.0 * 4.0) controls the max noise intensity.
    noise_strength_mask = (255.0 - luminance) / 255.0 * 3.5  # Max noise factor of 3.5 in pure black
    noise_strength_mask = np.expand_dims(noise_strength_mask, axis=-1) # Match shape for broadcasting
    
    # Generate standard noise and scale it by our mask
    noise = np.random.normal(0, 1, np_img.shape)
    scaled_noise = noise * noise_strength_mask

    # Add the scaled noise to the image and clip to valid range
    np_img = np.clip(np_img + scaled_noise, 0, 255)
    img = Image.fromarray(np_img.astype(np.uint8), 'RGB')


    # 2. Simulate subtle chromatic aberration with blending for a weaker effect
    r, g, b = img.split()
    offset = 1 # Shift by 1 pixel

    # Create empty channels for shifted Red and Blue
    r_shifted = Image.new('L', img.size)
    b_shifted = Image.new('L', img.size)
    
    # Paste the original channels with an offset
    r_shifted.paste(r, (-offset, 0))
    b_shifted.paste(b, (offset, 0))

    # Blend the shifted channels with the originals to make the effect subtle
    # Reduced alpha from 0.4 to 0.2 for weaker chromatic aberration
    blend_alpha = 0.2 
    r_final = Image.blend(r, r_shifted, alpha=blend_alpha)
    b_final = Image.blend(b, b_shifted, alpha=blend_alpha)

    # Merge the final channels
    img = Image.merge('RGB', (r_final, g, b_final))

    return img

def save_with_metadata_and_effects(src_path, dst_path, quality, apply_effects):
    """
    Opens an image, applies optional realism effects, generates rich metadata,
    and saves it as a new JPEG with specified quality.
    """
    phone_brands = [
        ("Apple",   ["iPhone 13", "iPhone 13 Pro", "iPhone 14", "iPhone 14 Pro", "iPhone 15"]),
        ("Samsung", ["Galaxy S22", "Galaxy S23", "Galaxy S23 Ultra", "Galaxy S24"]),
        ("Google",  ["Pixel 6", "Pixel 7", "Pixel 8", "Pixel 8 Pro"]),
    ]
    brand, models = random.choice(phone_brands)
    model = random.choice(models)

    # Generate today's datetime with random time for the photo
    photo_datetime = generate_todays_datetime()
    date_time_str = photo_datetime.strftime("%Y:%m:%d %H:%M:%S")

    with Image.open(src_path) as img:
        # Convert to RGB if it has an alpha channel (like PNG) or is greyscale
        if img.mode not in ('RGB'):
            img = img.convert('RGB')
        
        # --- NEW: Apply realism effects ---
        if apply_effects:
            img = apply_realism_effects(img)

        # --- ENHANCED: More authentic metadata ---
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}}
        
        # 0th IFD
        exif_dict["0th"][piexif.ImageIFD.Make] = brand.encode('utf-8')
        exif_dict["0th"][piexif.ImageIFD.Model] = model.encode('utf-8')
        exif_dict["0th"][piexif.ImageIFD.Software] = "HDR+ 1.0.1234567".encode('utf-8')
        exif_dict["0th"][piexif.ImageIFD.DateTime] = date_time_str.encode('utf-8')

        # Exif IFD
        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_time_str.encode('utf-8')
        exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = date_time_str.encode('utf-8')
        exif_dict["Exif"][piexif.ExifIFD.FNumber] = (random.choice([16, 17, 18]), 10) # F/1.6, F/1.7, etc.
        exif_dict["Exif"][piexif.ExifIFD.ISOSpeedRatings] = random.choice([50, 64, 80, 100, 125, 200])
        exif_dict["Exif"][piexif.ExifIFD.Flash] = 16 # Flash did not fire, auto mode
        exif_dict["Exif"][piexif.ExifIFD.ColorSpace] = 1 # sRGB

        # GPS IFD
        exif_dict["GPS"] = generate_random_gps()
        
        exif_bytes = piexif.dump(exif_dict)
        
        # --- MODIFIED: Use quality slider and add chroma subsampling for authenticity ---
        subsampling = '4:2:0' if quality < 90 else '4:4:4'
        img.save(dst_path, "jpeg", exif=exif_bytes, quality=quality, subsampling=subsampling)


class ImageReviewer(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("Image Reviewer v2.1 (Fixed)")
        self.geometry("1200x1000")

        self.config_data = load_config()
        self.executor = ThreadPoolExecutor(max_workers=os.cpu_count())

        # --- BUG FIX: Graceful shutdown ---
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # --- UI Structure ---
        # Top control frame
        self.top_frame = tk.Frame(self)
        self.top_frame.pack(pady=10, padx=10, fill=tk.X)

        self.btn_folder = tk.Button(self.top_frame, text="Choose Folder", command=self.choose_folder)
        self.btn_folder.pack(side=tk.LEFT, padx=5)

        self.toggle_var = tk.BooleanVar(value=self.config_data["use_central_folder"])
        self.btn_toggle = tk.Checkbutton(
            self.top_frame, text="Use Central Folder", variable=self.toggle_var, command=self.toggle_central_folder
        )
        self.btn_toggle.pack(side=tk.LEFT, padx=5)

        self.btn_choose_central = tk.Button(
            self.top_frame, text="Choose Central Folder", command=self.choose_central_folder
        )
        self.btn_choose_central.pack(side=tk.LEFT, padx=5)

        # --- NEW: Authenticity Controls UI ---
        effects_frame = ttk.LabelFrame(self, text="Authenticity Effects", padding=(10, 5))
        effects_frame.pack(pady=5, padx=10, fill=tk.X)

        self.realism_var = tk.BooleanVar(value=self.config_data.get("apply_realism_effects", True))
        self.realism_check = tk.Checkbutton(effects_frame, text="Apply Realism (Noise, Blur, Aberration)", variable=self.realism_var)
        self.realism_check.pack(side=tk.LEFT, padx=5)
        
        self.quality_label = tk.Label(effects_frame, text=f"JPEG Quality: {self.config_data.get('jpeg_quality', 85)}")
        self.quality_label.pack(side=tk.LEFT, padx=(20, 5))

        self.quality_var = tk.IntVar(value=self.config_data.get('jpeg_quality', 85))
        self.quality_slider = ttk.Scale(
            effects_frame, from_=50, to=100, orient=tk.HORIZONTAL, variable=self.quality_var, command=self.on_quality_change
        )
        self.quality_slider.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Info and status labels
        self.info_label = tk.Label(
            self, text="Key Commands: • Keep -> [Right Arrow] or (k)  • Discard -> [Left Arrow] or (d)  • Modify -> [Up Arrow] or (u)", justify=tk.CENTER
        )
        self.info_label.pack(pady=5)
        
        self.current_folder_label = tk.Label(self, text="Current Folder: (none selected)")
        self.current_folder_label.pack()
        self.central_folder_label = tk.Label(self, text="", fg="blue")
        self.central_folder_label.pack()

        # Main image display area
        self.image_label = tk.Label(self, text="\n\nDrag and drop a folder here or use the 'Choose Folder' button.\n\n", bg="grey90")
        self.image_label.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<Drop>>", self.on_drop)

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
        
        # Initial UI state
        self.toggle_central_folder()

    def on_closing(self):
        """Handle window closing event."""
        print("Closing application... waiting for file operations to complete.")
        # Save final config
        self.config_data["jpeg_quality"] = self.quality_var.get()
        self.config_data["apply_realism_effects"] = self.realism_var.get()
        save_config(self.config_data)

        self.executor.shutdown(wait=True)  # Wait for all threads to finish
        self.destroy() # Close the window

    def on_quality_change(self, value):
        """Update label when slider moves."""
        quality = int(float(value))
        self.quality_label.config(text=f"JPEG Quality: {quality}")

    def choose_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.load_images(folder)

    def on_drop(self, event):
        # The event data can sometimes contain multiple files in braces
        folder = event.data.strip('{}')
        if os.path.isdir(folder):
            self.load_images(folder)

    def load_images(self, folder):
        self.current_folder = folder
        valid_exts = [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"]
        
        try:
            all_files = os.listdir(folder)
            self.image_paths = sorted([
                os.path.join(folder, f)
                for f in all_files
                if os.path.splitext(f)[1].lower() in valid_exts
            ])
            self.current_index = 0
            
            if self.toggle_var.get() is False:
                 self.current_folder_label.config(text=f"Current Folder: {folder}")

            if self.image_paths:
                self.show_image()
            else:
                self.image_label.config(text="No images found in the selected folder.", image=None, bg="grey90")
                self.image_label.image = None
        except Exception as e:
            self.image_label.config(text=f"Error loading folder: {e}", image=None, bg="grey90")
            self.image_label.image = None

    def show_image(self):
        if not (0 <= self.current_index < len(self.image_paths)):
             self.display_end_of_review()
             return

        path = self.image_paths[self.current_index]
        try:
            self.current_img = Image.open(path)
            self.render_scaled_image()
        except Exception as e:
            print(f"Error opening {path}: {e}")
            self.go_next_image() # Skip corrupted/unreadable image

    def render_scaled_image(self):
        if not self.current_img:
            return

        # Use the label's dimensions for scaling
        max_w = self.image_label.winfo_width()
        max_h = self.image_label.winfo_height()
        
        if max_w < 50 or max_h < 50: return # Avoid rendering in tiny windows

        temp_img = self.current_img.copy()
        temp_img.thumbnail((max_w, max_h), LANCZOS)
        
        tk_img = ImageTk.PhotoImage(temp_img)
        self.image_label.config(image=tk_img, text="", bg="grey20") # Dark bg for images
        self.image_label.image = tk_img # Keep reference

    def _process_image_task(self, img_path, subfolder):
        """Generic background task for processing and saving an image."""
        base_out = self.get_base_out()
        output_folder = os.path.join(base_out, subfolder)
        archive_folder = os.path.join(base_out, "archive")
        os.makedirs(output_folder, exist_ok=True)
        os.makedirs(archive_folder, exist_ok=True)

        # 1. Archive the original image (lossless copy)
        archive_dst = os.path.join(archive_folder, os.path.basename(img_path))
        shutil.copy2(img_path, archive_dst)

        # 2. Process and save the modified version
        new_filename = f"IMG_{generate_todays_datetime().strftime('%Y%m%d_%H%M%S')}.jpg"
        output_dst = os.path.join(output_folder, new_filename)
        
        # Get settings from UI at the moment of the action
        quality = self.quality_var.get()
        apply_effects = self.realism_var.get()
        
        try:
            save_with_metadata_and_effects(img_path, output_dst, quality, apply_effects)
            print(f"Successfully processed and saved to {output_dst}")
        except Exception as e:
            print(f"!!! FAILED to process {os.path.basename(img_path)}: {e}")


    def keep_image(self, event=None):
        if not self.image_paths or self.current_index >= len(self.image_paths): return
        img_path = self.image_paths[self.current_index]
        self.go_next_image()
        self.executor.submit(self._process_image_task, img_path, "keep")

    def discard_image(self, event=None):
        if not self.image_paths or self.current_index >= len(self.image_paths): return
        # Simply move to the next image without any processing
        self.go_next_image()

    def modify_image(self, event=None):
        if not self.image_paths or self.current_index >= len(self.image_paths): return
        img_path = self.image_paths[self.current_index]
        self.go_next_image()
        self.executor.submit(self._process_image_task, img_path, "modify")

    def go_next_image(self):
        self.current_index += 1
        self.show_image()

    def display_end_of_review(self):
        """Show a message when all images are reviewed."""
        self.image_label.config(text="\n\nNo more images to review.\nDrop a new folder to continue.\n\n", image=None, bg="grey90")
        self.image_label.image = None
        self.current_img = None

    def on_window_resize(self, event):
        if self._resize_after_id:
            self.after_cancel(self._resize_after_id)
        # Debounce resizing to avoid excessive calculations
        self._resize_after_id = self.after(150, self.render_scaled_image)

    def toggle_central_folder(self):
        self.config_data["use_central_folder"] = self.toggle_var.get()
        # No need to save config on every toggle, will be saved on exit
        
        if self.toggle_var.get() and self.config_data["central_folder_path"]:
            self.central_folder_label.config(text=f"Central Folder: {self.config_data['central_folder_path']}")
            self.current_folder_label.config(text="(Outputs will go to the Central Folder)")
        else:
            self.central_folder_label.config(text="")
            if self.current_folder:
                self.current_folder_label.config(text=f"Current Folder: {self.current_folder}")
            else:
                self.current_folder_label.config(text="Current Folder: (none selected)")

    def choose_central_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.config_data["central_folder_path"] = folder
            self.toggle_central_folder() # Update UI based on new path

    def get_base_out(self):
        if self.toggle_var.get() and self.config_data["central_folder_path"]:
            return self.config_data["central_folder_path"]
        return self.current_folder

def main():
    app = ImageReviewer()
    app.mainloop()

if __name__ == "__main__":
    main()