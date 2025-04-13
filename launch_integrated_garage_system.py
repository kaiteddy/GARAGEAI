#!/usr/bin/env python3
"""
Integrated Garage Management System Launcher

This script launches the Integrated Garage Management System on port 8080
to avoid conflicts with the GA4 Direct Access Tool.
"""

import os
import sys
import subprocess
import webbrowser
import time
import argparse
from pathlib import Path

def find_ga4_installation():
    """Find GA4 installation directory"""
    # Common installation paths
    common_paths = [
        r"C:\Program Files (x86)\Garage Assistant GA4",
        r"C:\Program Files\Garage Assistant GA4",
        r"C:\Garage Assistant GA4"
    ]
    
    # Check common paths
    for path in common_paths:
        if os.path.exists(path) and os.path.isdir(path):
            print(f"Found GA4 installation at {path}")
            return path
    
    # Check if environment variable is set
    if 'GA4_PATH' in os.environ:
        path = os.environ['GA4_PATH']
        if os.path.exists(path) and os.path.isdir(path):
            print(f"Found GA4 installation from environment variable at {path}")
            return path
    
    print("GA4 installation not found")
    return None

def wait_for_server(port):
    """Wait for server to start"""
    time.sleep(2)

def main():
    """Main function to launch the integrated garage system"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Launch Integrated Garage Management System')
    parser.add_argument('--port', type=int, default=8080, help='Port to run the server on')
    parser.add_argument('--ga4-path', type=str, help='Path to GA4 installation')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--auto-sync-interval', type=int, default=5, help='Auto-sync interval in minutes')
    parser.add_argument('--mot-verify-interval', type=int, default=60, help='MOT verification interval in minutes')
    args = parser.parse_args()
    
    # Get GA4 path
    ga4_path = args.ga4_path or find_ga4_installation()
    
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Set environment variables
    os.environ['FLASK_APP'] = 'integrated_system.py'
    if args.debug:
        os.environ['FLASK_ENV'] = 'development'
    
    # Build command
    cmd = [sys.executable, os.path.join(script_dir, 'integrated_system.py')]
    if ga4_path:
        cmd.extend(['--ga4-path', ga4_path])
    cmd.extend(['--port', str(args.port)])
    cmd.extend(['--auto-sync-interval', str(args.auto_sync_interval)])
    cmd.extend(['--mot-verify-interval', str(args.mot_verify_interval)])
    if args.debug:
        cmd.append('--debug')
    
    # Print command
    print(f"Launching Integrated Garage Management System with command: {' '.join(cmd)}")
    
    # Launch system
    process = subprocess.Popen(cmd, cwd=script_dir)
    
    # Wait for server to start
    print(f"Waiting for server to start on port {args.port}...")
    wait_for_server(args.port)
    
    # Open web browser
    url = f"http://localhost:{args.port}"
    print(f"Opening browser to {url}")
    webbrowser.open(url)
    
    try:
        # Wait for process to finish
        process.wait()
    except KeyboardInterrupt:
        # Handle Ctrl+C
        print("Shutting down...")
        process.terminate()
        process.wait()

if __name__ == "__main__":
    main()
