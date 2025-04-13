#!/usr/bin/env python3
"""
Take Screenshot - A simple tool to capture screenshots on demand.

This script captures a screenshot when run and saves it to a file.
"""

import os
import sys
from datetime import datetime

# Check if required packages are installed
try:
    import pyautogui
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call(["pip3", "install", "pyautogui"])
    import pyautogui

def take_screenshot(output_dir="screenshots", prefix="screenshot"):
    """Take a screenshot and save it to the output directory.
    
    Args:
        output_dir (str): Directory to save the screenshot
        prefix (str): Prefix for the screenshot filename
        
    Returns:
        str: Path to the saved screenshot
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.png"
    filepath = os.path.join(output_dir, filename)
    
    # Take screenshot
    screenshot = pyautogui.screenshot()
    
    # Save screenshot
    screenshot.save(filepath)
    
    return filepath

def main():
    """Main function."""
    try:
        # Take screenshot
        filepath = take_screenshot()
        
        # Print result
        print(f"Screenshot saved to: {filepath}")
        
        return 0
    
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
