#!/usr/bin/env python3
"""
Integrated Garage Management System

This script launches the complete Garage Management System that combines:
1. GA4 Direct Access Tool - For accessing GA4 data
2. MOT Reminder System - For managing MOT reminders
3. Customer Management - For managing customer information
4. Invoice Management - For generating and tracking invoices

All components work together with a unified interface and shared data.
"""

import os
import sys
import json
import logging
import argparse
import webbrowser
import sqlite3
import threading
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('IntegratedGarageSystem')

# Add parent directory to path to import modules
parent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(parent_dir)

# Import GA4 Direct Access Tool
sys.path.insert(0, parent_dir)
try:
    import ga4_direct_access
    from ga4_direct_access import DirectGA4Browser
except ImportError:
    logger.error("Could not import GA4 Direct Access Tool. Make sure ga4_direct_access.py is in the same directory.")
    sys.exit(1)

# Import MOT Reminder System
try:
    from mot_reminder.reminder_manager import MOTReminderManager
    from mot_reminder.notification_handler import NotificationHandler
    from mot_reminder.web_interface import init_app as init_mot_app
except ImportError:
    logger.error("Could not import MOT Reminder System. Make sure mot_reminder module is available.")
    sys.exit(1)

# Create Flask app
app = Flask(__name__, 
            template_folder=os.path.join(parent_dir, 'templates'),
            static_folder=os.path.join(parent_dir, 'static'))
CORS(app)

# Global variables
ga4_browser = None
reminder_manager = None
notification_handler = None
config = {}
ga4_thread = None

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
        },
        "dvla_api": {
            "enabled": False,
            "api_key": ""
        },
        "system": {
            "port": 5000,
            "host": "0.0.0.0",
            "debug": False,
            "auto_import_csv": True,
            "auto_create_reminders": True
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

def start_ga4_browser(ga4_path, db_path):
    """Start GA4 Direct Access Browser in a separate thread
    
    Args:
        ga4_path: Path to GA4 installation directory
        db_path: Path to SQLite database
    """
    global ga4_browser
    
    try:
        # Initialize GA4 browser
        ga4_browser = DirectGA4Browser(ga4_path, db_path)
        
        # Start monitoring for CSV files
        ga4_browser.start_monitoring()
        
        logger.info("GA4 Direct Access Browser started")
    except Exception as e:
        logger.error(f"Error starting GA4 Direct Access Browser: {e}")

def init_system(config_path):
    """Initialize the integrated system
    
    Args:
        config_path: Path to configuration file
    """
    global config, reminder_manager, notification_handler, ga4_thread
    
    # Load configuration
    config = load_config(config_path)
    
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
    
    # Start GA4 browser in a separate thread
    ga4_thread = threading.Thread(
        target=start_ga4_browser,
        args=(config['ga4_path'], config['sqlite_db_path']),
        daemon=True
    )
    ga4_thread.start()
    
    # Initialize reminder manager
    reminder_manager = MOTReminderManager(config['sqlite_db_path'], config_path)
    
    # Initialize notification handler
    notification_handler = NotificationHandler(config_path)
    
    # Initialize MOT reminder app
    init_mot_app(config['sqlite_db_path'], config_path)
    
    logger.info("Integrated system initialized")

# Routes for the integrated system
@app.route('/')
def index():
    """Home page"""
    return render_template('integrated_index.html')

@app.route('/ga4')
def ga4_page():
    """GA4 Direct Access page"""
    return redirect('/ga4_browser')

@app.route('/mot')
def mot_page():
    """MOT Reminder page"""
    return redirect('/vehicles')

@app.route('/customers')
def customers_page():
    """Customer Management page"""
    return render_template('customers.html')

@app.route('/invoices')
def invoices_page():
    """Invoice Management page"""
    return render_template('invoices.html')

@app.route('/api/system_status')
def system_status():
    """API endpoint for system status"""
    try:
        # Check GA4 browser status
        ga4_status = "Running" if ga4_browser and ga4_browser.is_monitoring else "Stopped"
        
        # Get vehicle count
        vehicle_count = 0
        reminder_count = 0
        
        try:
            # Get vehicle count from database
            conn = sqlite3.connect(config['sqlite_db_path'])
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Check if Vehicles table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Vehicles'")
            if cursor.fetchone():
                cursor.execute("SELECT COUNT(*) as count FROM Vehicles")
                row = cursor.fetchone()
                if row:
                    vehicle_count = row['count']
            
            # Get reminder count
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mot_reminders'")
            if cursor.fetchone():
                cursor.execute("SELECT COUNT(*) as count FROM mot_reminders")
                row = cursor.fetchone()
                if row:
                    reminder_count = row['count']
            
            conn.close()
        except Exception as e:
            logger.error(f"Error getting counts from database: {e}")
        
        return jsonify({
            'success': True,
            'ga4_status': ga4_status,
            'ga4_path': config['ga4_path'],
            'vehicle_count': vehicle_count,
            'reminder_count': reminder_count,
            'system_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return jsonify({
            'success': False,
            'message': f'Error getting system status: {str(e)}'
        })

def run_app(host='0.0.0.0', port=5000, debug=False):
    """Run the Flask application"""
    app.run(host=host, port=port, debug=debug)

def main():
    """Main function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Integrated Garage Management System')
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
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "garage_system_config.json")
    
    # Initialize system
    init_system(config_path)
    
    # Override GA4 path if specified
    if args.ga4_path:
        config['ga4_path'] = args.ga4_path
    
    # Open web browser
    url = f"http://localhost:{args.port}"
    webbrowser.open(url)
    
    # Run web server
    logger.info(f"Starting web server at {url}")
    run_app(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main()
