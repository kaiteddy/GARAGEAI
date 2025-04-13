#!/usr/bin/env python3
"""
Process Screenshot - A tool to process screenshots for analysis.

This script processes a screenshot and saves it as a JPEG file.
"""

import os
import sys
import argparse

# Check if required packages are installed
try:
    from PIL import Image
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call(["pip3", "install", "pillow"])
    from PIL import Image

def process_screenshot(image_path, max_width=1200, quality=70):
    """Process a screenshot for analysis.
    
    Args:
        image_path (str): Path to the screenshot
        max_width (int): Maximum width of the processed image
        quality (int): JPEG quality (0-100)
        
    Returns:
        str: Path to the processed image
    """
    # Open image
    image = Image.open(image_path)
    
    # Resize if needed
    width, height = image.size
    if width > max_width:
        # Calculate new height to maintain aspect ratio
        new_height = int(height * (max_width / width))
        image = image.resize((max_width, new_height), Image.LANCZOS)
        print(f"Resized image from {width}x{height} to {image.size[0]}x{image.size[1]}")
    
    # Convert RGBA to RGB if needed
    if image.mode == 'RGBA':
        rgb_image = Image.new('RGB', image.size, (255, 255, 255))
        rgb_image.paste(image, mask=image.split()[3])  # Use alpha channel as mask
        image = rgb_image
    
    # Generate output path
    output_path = os.path.splitext(image_path)[0] + "_processed.jpg"
    
    # Save processed image
    image.save(output_path, format="JPEG", quality=quality)
    
    return output_path

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Process a screenshot for analysis')
    parser.add_argument('image_path', help='Path to the screenshot')
    parser.add_argument('--max-width', type=int, default=1200,
                        help='Maximum width of the processed image (default: 1200)')
    parser.add_argument('--quality', type=int, default=70,
                        help='JPEG quality (0-100) (default: 70)')
    
    args = parser.parse_args()
    
    try:
        # Process screenshot
        output_path = process_screenshot(args.image_path, args.max_width, args.quality)
        
        # Print result
        print(f"Processed screenshot saved to: {output_path}")
        
        return 0
    
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
