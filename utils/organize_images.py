"""
Utility script to organize default images for slides and book covers.

This script helps organize default/stock images into the appropriate directories:
- static/uploads/slides/default/ for slide images
- static/uploads/books/covers/default/ for book cover images

Usage:
    python utils/organize_images.py --type slides --source /path/to/images
    python utils/organize_images.py --type covers --source /path/to/images
"""

import os
import shutil
import argparse
from pathlib import Path


def organize_images(image_type, source_dir, target_base='static/uploads'):
    """
    Organize images from source directory to appropriate default folders.
    
    Args:
        image_type: 'slides' or 'covers'
        source_dir: Directory containing images to organize
        target_base: Base directory for uploads (default: 'static/uploads')
    """
    # Determine target directory
    if image_type == 'slides':
        target_dir = os.path.join(target_base, 'slides', 'default')
    elif image_type == 'covers':
        target_dir = os.path.join(target_base, 'books', 'covers', 'default')
    else:
        raise ValueError(f"Invalid image type: {image_type}. Must be 'slides' or 'covers'")
    
    # Create target directory if it doesn't exist
    os.makedirs(target_dir, exist_ok=True)
    
    # Allowed image extensions
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
    
    # Get all image files from source directory
    source_path = Path(source_dir)
    if not source_path.exists():
        print(f"Error: Source directory does not exist: {source_dir}")
        return
    
    image_files = [f for f in source_path.iterdir() 
                   if f.is_file() and f.suffix.lower() in allowed_extensions]
    
    if not image_files:
        print(f"No image files found in {source_dir}")
        return
    
    # Copy images to target directory
    copied_count = 0
    for image_file in image_files:
        target_path = os.path.join(target_dir, image_file.name)
        
        # If file already exists, skip or rename
        if os.path.exists(target_path):
            print(f"Skipping {image_file.name} (already exists in target)")
            continue
        
        try:
            shutil.copy2(image_file, target_path)
            print(f"Copied: {image_file.name} -> {target_path}")
            copied_count += 1
        except Exception as e:
            print(f"Error copying {image_file.name}: {str(e)}")
    
    print(f"\nCompleted: {copied_count} image(s) copied to {target_dir}")


def main():
    parser = argparse.ArgumentParser(
        description='Organize default images for slides and book covers'
    )
    parser.add_argument(
        '--type',
        choices=['slides', 'covers'],
        required=True,
        help='Type of images to organize: slides or covers'
    )
    parser.add_argument(
        '--source',
        required=True,
        help='Source directory containing images to organize'
    )
    parser.add_argument(
        '--target',
        default='static/uploads',
        help='Base target directory (default: static/uploads)'
    )
    
    args = parser.parse_args()
    
    organize_images(args.type, args.source, args.target)


if __name__ == '__main__':
    main()

