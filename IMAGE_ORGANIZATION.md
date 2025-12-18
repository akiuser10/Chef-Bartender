# Image Organization Guide

## Overview

All images uploaded through the application are automatically saved to organized directories. This document explains where images are saved and how the system works.

## Directory Structure

```
static/uploads/
├── slides/                    # Homepage slide images
│   └── default/               # Default/stock slide images (for reference)
├── books/
│   ├── covers/                # Book cover images for Knowledge Hub
│   │   └── default/           # Default/stock book cover images (for reference)
│   └── pdfs/                  # PDF files for books
├── recipes/                   # Recipe images
└── products/                  # Product images
```

## Automatic Image Saving

### Slide Images
- **Location**: `static/uploads/slides/`
- **How it works**: 
  - When users upload images through "Manage Slides" interface, images are automatically saved to `uploads/slides/`
  - Function: `save_slide_image()` in `utils/file_upload.py`
  - Files are saved with timestamp prefix: `YYYYMMDD_HHMMSS_filename.jpg`
- **Default Images**: Place any default/stock slide images in `uploads/slides/default/` for reference

### Book Cover Images
- **Location**: `static/uploads/books/covers/`
- **How it works**:
  - **Manual Upload**: When users upload cover images through "Add Book" or "Edit Book", images are saved to `uploads/books/covers/`
  - **Automatic Fetching**: When a book's article URL is provided, the system automatically fetches the cover image from the website and saves it to `uploads/books/covers/`
  - Functions: 
    - `save_uploaded_file(cover_file, 'books/covers')` in `utils/file_upload.py`
    - `fetch_cover_image_from_url()` in `blueprints/knowledge.py`
  - Files are saved with timestamp prefix or UUID for auto-fetched images
- **Default Images**: Place any default/stock book cover images in `uploads/books/covers/default/` for reference

## Image Types Supported

- **Formats**: PNG, JPG, JPEG, GIF, WEBP
- **Max Size**: 50MB (configured in `config.py`)

## Organizing Default Images

### Using the Utility Script

A utility script is available to help organize default images:

```bash
# Organize slide images
python utils/organize_images.py --type slides --source /path/to/slide/images

# Organize book cover images
python utils/organize_images.py --type covers --source /path/to/cover/images
```

### Manual Organization

1. **For Slide Images**: Copy images to `static/uploads/slides/default/`
2. **For Book Cover Images**: Copy images to `static/uploads/books/covers/default/`

## Image Serving

All images are served through the Flask route:
- **Route**: `/uploads/<path:filename>`
- **Handler**: `uploaded_file()` in `blueprints/main.py`
- **Example URLs**:
  - Slide: `/uploads/slides/20250115_143022_my-slide.jpg`
  - Book Cover: `/uploads/books/covers/20250115_143022_my-cover.jpg`

## Persistent Storage

On deployment platforms (like Railway):
- The `UPLOAD_FOLDER` can be configured via environment variable
- Set `UPLOAD_FOLDER` to a persistent volume path to ensure images survive redeployments
- Example: `UPLOAD_FOLDER=/app/data/uploads`

## File Naming

### User-Uploaded Files
- Format: `YYYYMMDD_HHMMSS_original-filename.ext`
- Example: `20250115_143022_my-image.jpg`
- Original filename is sanitized using `secure_filename()`

### Auto-Fetched Book Covers
- Format: `{uuid}.jpg`
- Example: `a1b2c3d4e5f6.jpg`
- UUID ensures uniqueness

## Notes

- All directories are automatically created on application startup (see `app.py`)
- Images are organized by type automatically
- No manual intervention needed - the system handles everything
- Default images in `default/` subdirectories are for reference only and won't be automatically used

## Verification

To verify images are being saved correctly:
1. Upload an image through the frontend
2. Check the corresponding directory in `static/uploads/`
3. The file should appear with a timestamped filename

