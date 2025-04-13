#!/usr/bin/env python3
"""
MOT Reminder System Launcher

This script launches the MOT Reminder System web interface.
It connects to the GA4 database and provides a user-friendly interface
for managing MOT reminders.
"""

import os
import sys
import json
import logging
import argparse
import sqlite3
import webbrowser
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('MOTReminderLauncher')

# Add parent directory to path to import modules
parent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(parent_dir)

# Import modules
from mot_reminder.web_interface import init_app, app, run_app

def find_ga4_installation():
    """Find GA4 installation directory
    
    Returns:
        Path to GA4 installation directory or None if not found
    """
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

def create_default_config(config_path, ga4_path=None):
    """Create default configuration file
    
    Args:
        config_path: Path to configuration file
        ga4_path: Path to GA4 installation directory
        
    Returns:
        Configuration dictionary
    """
    default_config = {
        "ga4_path": ga4_path or "",
        "sqlite_db_path": os.path.join(os.path.dirname(config_path), "ga4_direct.db"),
        "reminder_days": [30, 14, 7, 3, 1],
        "reminder_templates": {
            "email": {
                "subject": "MOT Reminder for {registration}",
                "body": "Dear {customer_name},\n\nThis is a reminder that the MOT for your {make} {model} ({registration}) is due on {mot_expiry}.\n\nPlease contact us to schedule an appointment.\n\nRegards,\n{garage_name}"
            },
            "sms": {
                "body": "MOT Reminder: Your {make} {model} ({registration}) is due for MOT on {mot_expiry}. Please contact us to schedule an appointment."
            },
            "letter": {
                "body": "Dear {customer_name},\n\nThis is a reminder that the MOT for your {make} {model} ({registration}) is due on {mot_expiry}.\n\nPlease contact us to schedule an appointment.\n\nRegards,\n{garage_name}"
            }
        },
        "garage_details": {
            "name": "Your Garage",
            "address": "123 Main Street, Anytown, AN1 1AA",
            "phone": "01234 567890",
            "email": "info@yourgarage.com",
            "website": "www.yourgarage.com"
        },
        "email": {
            "enabled": False,
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_username": "",
            "smtp_password": "",
            "from_email": "",
            "from_name": "Your Garage"
        },
        "sms": {
            "enabled": False,
            "provider": "twilio",
            "account_sid": "",
            "auth_token": "",
            "from_number": ""
        },
        "letter": {
            "enabled": False,
            "output_directory": "letters"
        }
    }
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    # Write configuration to file
    with open(config_path, 'w') as f:
        json.dump(default_config, f, indent=4)
    
    logger.info(f"Created default configuration at {config_path}")
    return default_config

def load_config(config_path):
    """Load configuration from file
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration dictionary
    """
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded configuration from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
    
    # Create default configuration if file doesn't exist
    ga4_path = find_ga4_installation()
    return create_default_config(config_path, ga4_path)

def create_templates_directory():
    """Create templates directory if it doesn't exist"""
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mot_reminder", "templates")
    os.makedirs(templates_dir, exist_ok=True)
    
    # Create static directory if it doesn't exist
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mot_reminder", "static")
    os.makedirs(static_dir, exist_ok=True)
    
    logger.info(f"Created templates directory at {templates_dir}")
    logger.info(f"Created static directory at {static_dir}")

def main():
    """Main function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='MOT Reminder System')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--ga4-path', help='Path to GA4 installation directory')
    parser.add_argument('--port', type=int, default=5000, help='Port to run web server on')
    parser.add_argument('--host', default='0.0.0.0', help='Host to run web server on')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    args = parser.parse_args()
    
    # Determine configuration path
    if args.config:
        config_path = args.config
    else:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mot_config.json")
    
    # Load configuration
    config = load_config(config_path)
    
    # Override GA4 path if specified
    if args.ga4_path:
        config['ga4_path'] = args.ga4_path
    
    # Check if GA4 path is set
    if not config['ga4_path']:
        ga4_path = find_ga4_installation()
        if ga4_path:
            config['ga4_path'] = ga4_path
            # Update configuration file
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
        else:
            logger.warning("GA4 path not set. Some features may not work correctly.")
    
    # Create templates directory
    create_templates_directory()
    
    # Initialize web application
    init_app(config['sqlite_db_path'], config_path)
    
    # Open web browser
    url = f"http://localhost:{args.port}"
    webbrowser.open(url)
    
    # Run web server
    logger.info(f"Starting web server at {url}")
    run_app(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main()
