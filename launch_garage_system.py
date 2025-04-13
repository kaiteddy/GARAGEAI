#!/usr/bin/env python3
"""
Garage Management System Launcher

This script launches the complete Garage Management System that integrates:
- GA4 Direct Access Tool
- MOT Reminder System
- Customer Management
- Invoice Management
- Appointment Scheduling
- Reporting and Analytics

All components work together with a unified interface and shared data.
"""

import os
import sys
import subprocess
import webbrowser
import time
import logging
import argparse
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('GarageSystemLauncher')

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
        r"C:\Program Files\Python311\python.exe"
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

def find_ga4_installation():
    """Find GA4 installation directory"""
    # Common installation paths
    common_paths = [
        r"C:\Program Files (x86)\Garage Assistant GA4",
        r"C:\Program Files\Garage Assistant GA4",
        r"C:\Garage Assistant GA4",
        r"D:\Program Files (x86)\Garage Assistant GA4",
        r"D:\Program Files\Garage Assistant GA4",
        r"D:\Garage Assistant GA4"
    ]
    
    # Check common paths
    for path in common_paths:
        if os.path.exists(path) and os.path.isdir(path):
            logger.info(f"Found GA4 installation at {path}")
            return path
    
    # Check if environment variable is set
    if 'GA4_PATH' in os.environ:
        path = os.environ['GA4_PATH']
        if os.path.exists(path) and os.path.isdir(path):
            logger.info(f"Found GA4 installation at {path} (from environment variable)")
            return path
    
    logger.warning("GA4 installation not found")
    return None

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = [
        "flask",
        "flask-cors",
        "pandas",
        "openpyxl",
        "reportlab",
        "requests",
        "python-dateutil",
        "twilio"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.warning(f"Missing dependencies: {', '.join(missing_packages)}")
        print(f"Missing dependencies: {', '.join(missing_packages)}")
        print("Installing missing dependencies...")
        
        python_exe = find_python_executable()
        if not python_exe:
            print("Error: Could not find Python executable. Please install the missing dependencies manually.")
            return False
        
        try:
            subprocess.run([python_exe, "-m", "pip", "install", *missing_packages], check=True)
            print("Dependencies installed successfully.")
            return True
        except subprocess.SubprocessError as e:
            print(f"Error installing dependencies: {e}")
            print("Please install the missing dependencies manually:")
            print(f"pip install {' '.join(missing_packages)}")
            return False
    
    return True

def main():
    """Main function"""
    print("=== Garage Management System Launcher ===")
    print("This launcher will start the complete Garage Management System")
    print("that integrates GA4 Direct Access Tool, MOT Reminder System,")
    print("Customer Management, Invoice Management, Appointment Scheduling,")
    print("and Reporting and Analytics.")
    print()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Garage Management System Launcher')
    parser.add_argument('--ga4-path', help='Path to GA4 installation directory')
    parser.add_argument('--port', type=int, default=5000, help='Port to run web server on')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    args = parser.parse_args()
    
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Check dependencies
    if not check_dependencies():
        print("Warning: Some dependencies are missing. The system may not work correctly.")
    
    # Find GA4 installation
    ga4_path = args.ga4_path or find_ga4_installation()
    if not ga4_path:
        print("Warning: GA4 installation not found. Some features may not work correctly.")
    
    # Find Python executable
    python_exe = find_python_executable()
    if not python_exe:
        print("Error: Could not find Python executable. Please install Python 3.6 or higher.")
        sys.exit(1)
    
    # Check if garage_system.py exists
    garage_system_script = os.path.join(script_dir, "garage_system.py")
    if not os.path.exists(garage_system_script):
        print(f"Error: Could not find garage_system.py at {garage_system_script}")
        sys.exit(1)
    
    # Launch the garage system
    try:
        print("Starting Garage Management System...")
        print("Please wait while the system initializes...")
        
        # Build command
        cmd = [python_exe, garage_system_script]
        if ga4_path:
            cmd.extend(["--ga4-path", ga4_path])
        if args.port:
            cmd.extend(["--port", str(args.port)])
        if args.debug:
            cmd.append("--debug")
        
        # Run the garage system script
        process = subprocess.Popen(
            cmd,
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
            print("Error: Could not start the Garage Management System.")
            sys.exit(1)
        
        # Keep the process running
        print("Garage Management System is running. Press Ctrl+C to stop.")
        while True:
            if process.poll() is not None:
                print("Garage Management System has stopped.")
                break
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\nStopping Garage Management System...")
        if process and process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        print("System stopped.")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
