# Image Review Helper

A Python application for reviewing and processing images with realistic metadata and effects.

## Features

- **Image Review Interface**: Easy-to-use GUI for reviewing images with keyboard shortcuts
- **Realistic Effects**: Applies luminance-dependent noise and subtle chromatic aberration
- **Metadata Generation**: Adds authentic EXIF data including GPS coordinates, camera info, and timestamps
- **Batch Processing**: Process multiple images efficiently with threading
- **Flexible Output**: Choose between local folder output or central folder management

## Requirements

- Python 3.7+
- Pillow (PIL)
- tkinterdnd2
- piexif
- numpy

## Installation

1. Clone this repository:
```bash
git clone https://github.com/Elwii04/image-review-helper.git
cd image-review-helper
```

2. Install required packages:
```bash
pip install Pillow tkinterdnd2 piexif numpy
```

## Usage

Run the main application:
```bash
python main.py
```

### Controls

- **Keep Image**: Right Arrow or 'k' - Saves the image with effects and metadata
- **Discard Image**: Left Arrow or 'd' - Skips the image without processing
- **Modify Image**: Up Arrow or 'u' - Saves to a separate "modify" folder

### Features

- **JPEG Quality Control**: Adjustable quality slider (50-100)
- **Realism Effects**: Toggle for noise, blur, and chromatic aberration
- **Central Folder**: Option to output all processed images to a central location
- **Date Stamping**: Images are stamped with today's date and random times

## File Structure

When processing images, the application creates:
- `keep/` - Images you want to keep
- `modify/` - Images marked for modification
- `archive/` - Original unmodified copies

## Configuration

Settings are automatically saved in `config.json` including:
- JPEG quality preferences
- Realism effects toggle
- Central folder settings

## License

This project is open source and available under the MIT License.
