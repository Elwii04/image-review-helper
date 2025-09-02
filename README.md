<<<<<<< HEAD
# 📸 Image Review Helper

A powerful Python application for reviewing and processing images with realistic metadata and effects. Perfect for adding authentic camera metadata, realistic visual effects, and organizing your image collections.

## ✨ Features

- **🖼️ Intuitive Review Interface**: Easy-to-use GUI with keyboard shortcuts for fast image review
- **🎨 Realistic Effects**: 
  - Luminance-dependent noise (more grain in shadows, like real cameras)
  - Subtle chromatic aberration for authenticity
  - Adjustable JPEG quality (50-100)
- **📋 Authentic Metadata**: Generates realistic EXIF data including:
  - Random GPS coordinates
  - Popular phone camera models (iPhone, Samsung Galaxy, Google Pixel)
  - Today's date with random times
  - Camera settings (ISO, F-stop, exposure)
- **⚡ Fast Processing**: Multi-threaded processing for efficient batch operations
- **📁 Flexible Organization**: 
  - Local folder output or central folder management
  - Automatic archiving of originals
  - Separate folders for "keep" and "modify" actions

## 🎮 Controls

| Action | Key | Function |
|--------|-----|----------|
| **Keep** | `→` or `K` | Save with effects and metadata to "keep" folder |
| **Discard** | `←` or `D` | Skip image without processing |
| **Modify** | `↑` or `U` | Save to "modify" folder for later editing |

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- Required packages: `Pillow`, `tkinterdnd2`, `piexif`, `numpy`

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/Elwii04/image-review-helper.git
cd image-review-helper
```

2. **Install dependencies:**
```bash
pip install Pillow tkinterdnd2 piexif numpy
```

3. **Run the application:**
```bash
python main.py
```

## 📂 How It Works

1. **Drag & Drop** a folder of images or use "Choose Folder"
2. **Review** each image using keyboard shortcuts
3. **Automatic Processing**: 
   - Original images are archived safely
   - Processed images get realistic effects and metadata
   - Files are organized into `keep/` and `modify/` folders

### Output Structure
```
📁 Your Folder/
├── 📁 keep/           # Images you want to keep (with effects)
├── 📁 modify/         # Images marked for modification
└── 📁 archive/        # Original unmodified copies
```

## ⚙️ Configuration

- **JPEG Quality**: Adjustable slider (50-100)
- **Realism Effects**: Toggle noise, blur, and chromatic aberration
- **Central Folder**: Output all processed images to one location
- **Auto-save**: Settings automatically saved in `config.json`

## 🎯 Perfect For

- 📱 Making screenshots look like phone camera photos
- 🎨 Adding realistic effects to digital artwork
- 📸 Organizing and processing large image collections
- 🔧 Batch processing with consistent metadata

## 🗂️ Project Structure

- `main.py` - Latest version with all features
- `Review V1/` - Original simple version
- `Review V2/` - Intermediate version
- `Review V3/` - Advanced version (same as main.py)

## 🤝 Contributing

Feel free to open issues or submit pull requests! This project is open source and welcomes improvements.

## 📄 License

This project is open source and available under the MIT License.

---

**Made with ❤️ for the image processing community**
=======
# image-review-helper
>>>>>>> ec83a5f6e15f7cbc95cdc657f24a2004897e97fd
