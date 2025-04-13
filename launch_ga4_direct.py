#!/usr/bin/env python3
"""
GA4 Direct Access Launcher

This script makes it easy to launch the GA4 Direct Access tool from any computer.
Just run this script and the tool will start automatically.
"""

import os
import sys
import subprocess
import webbrowser
import platform

def main():
    """Main function to launch the GA4 Direct Access tool"""
    print("Launching GA4 Direct Access Tool...")
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Install required packages if not already installed
    try:
        import flask
        import flask_cors
        import watchdog
    except ImportError:
        print("Installing required packages...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "flask", "flask-cors", "watchdog"])
    
    # Set the path to the GA4 Direct Access script
    ga4_script = os.path.join(script_dir, "ga4_direct_access.py")
    
    # Check if the script exists
    if not os.path.exists(ga4_script):
        print(f"Error: Could not find {ga4_script}")
        sys.exit(1)
    
    # Launch the GA4 Direct Access tool
    print("Starting GA4 Direct Access Tool...")
    print("The tool will be available at http://localhost:5000")
    
    # Open browser
    webbrowser.open("http://localhost:5000")
    
    # Run the GA4 Direct Access script
    if platform.system() == "Windows":
        os.chdir(script_dir)
        os.system(f'python "{ga4_script}"')
    else:
        os.chdir(script_dir)
        os.system(f'python3 "{ga4_script}"')

if __name__ == "__main__":
    main()
