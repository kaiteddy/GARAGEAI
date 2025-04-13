#!/usr/bin/env python3
"""
Integrated Garage Management System Launcher

This script launches the complete Integrated Garage Management System
that combines GA4 Direct Access Tool and MOT Reminder System into
a single unified interface.
"""

import os
import sys
import subprocess
import webbrowser
import time
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('IntegratedSystemLauncher')

def find_python_executable():
    """Find the Python executable to use"""
    # Try using the current Python interpreter
    python_exe = sys.executable
    if python_exe and os.path.exists(python_exe):
        return python_exe
    
    # Try common Python paths
    common_paths = [
        "python",
        "python3",
        r"C:\Python39\python.exe",
        r"C:\Python310\python.exe",
        r"C:\Python311\python.exe",
        r"C:\Program Files\Python39\python.exe",
        r"C:\Program Files\Python310\python.exe",
        r"C:\Program Files\Python311\python.exe",
        r"C:\Users\elimotors\AppData\Local\Programs\Python\Python39\python.exe",
        r"C:\Users\elimotors\AppData\Local\Programs\Python\Python310\python.exe",
        r"C:\Users\elimotors\AppData\Local\Programs\Python\Python311\python.exe"
    ]
    
    for path in common_paths:
        try:
            # Check if the command exists and is executable
            subprocess.run([path, "--version"], capture_output=True, check=True)
            return path
        except (subprocess.SubprocessError, FileNotFoundError):
            continue
    
    logger.error("Could not find Python executable")
    return None

def main():
    """Main function"""
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Find Python executable
    python_exe = find_python_executable()
    if not python_exe:
        print("Error: Could not find Python executable. Please install Python 3.6 or higher.")
        sys.exit(1)
    
    # Check if integrated system script exists
    integrated_script = os.path.join(script_dir, "integrated_garage_system.py")
    if not os.path.exists(integrated_script):
        print(f"Error: Could not find integrated system script at {integrated_script}")
        sys.exit(1)
    
    # Launch the integrated system
    try:
        print("Starting Integrated Garage Management System...")
        print("This will combine GA4 Direct Access Tool and MOT Reminder System into a single interface.")
        print("Please wait while the system initializes...")
        
        # Run the integrated system script
        process = subprocess.Popen(
            [python_exe, integrated_script],
            cwd=script_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Wait for the server to start
        started = False
        for line in process.stdout:
            print(line.strip())
            if "Running on http://" in line:
                started = True
                # Extract the URL from the output
                url = line.strip().split("Running on ")[1].split()[0]
                # Open web browser
                print(f"Opening browser to {url}")
                webbrowser.open(url)
                break
        
        if not started:
            print("Error: Could not start the integrated system.")
            sys.exit(1)
        
        # Keep the process running
        print("Integrated system is running. Press Ctrl+C to stop.")
        while True:
            if process.poll() is not None:
                print("Integrated system has stopped.")
                break
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\nStopping Integrated Garage Management System...")
        if process and process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        print("System stopped.")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
