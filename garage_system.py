#!/usr/bin/env python3
"""
Garage Management System - Main Application

This is the main entry point for the Garage Management System that integrates:
1. GA4 Direct Access Tool - For accessing GA4 data
2. MOT Reminder System - For managing MOT reminders
3. Customer Management - For managing customer information
4. Invoice Management - For generating and tracking invoices
5. Appointment Scheduling - For managing garage appointments
6. Reporting - For business analytics and reporting

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
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('GarageSystem')

# Add parent directory to path to import modules
parent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(parent_dir)

# Import GA4 Direct Access Tool
try:
    from ga4_direct_access import DirectGA4Browser, GA4DirectAccess
except ImportError:
    logger.warning("Could not import GA4 Direct Access Tool. Some features may not work correctly.")
    # Define a simple replacement class if import fails
    class DirectGA4Browser:
        def __init__(self, ga4_path, db_path):
            self.ga4_path = ga4_path
            self.db_path = db_path
            self.is_monitoring = False

        def start_monitoring(self):
            self.is_monitoring = True

# Import MOT Reminder System
try:
    from mot_reminder.reminder_manager import MOTReminderManager
    from mot_reminder.notification_handler import NotificationHandler
except ImportError:
    logger.warning("Could not import MOT Reminder System. Some features may not work correctly.")

# Import Customer Management
try:
    from customer_management.customer_manager import CustomerManager
except ImportError:
    logger.warning("Could not import Customer Management. Some features may not work correctly.")

# Import Invoice Management
try:
    from invoicing.invoice_manager import InvoiceManager
except ImportError:
    logger.warning("Could not import Invoice Management. Some features may not work correctly.")

# Import Appointment Scheduling
try:
    from scheduling.appointment_manager import AppointmentManager
except ImportError:
    logger.warning("Could not import Appointment Scheduling. Some features may not work correctly.")

# Import Reporting
try:
    from reporting.report_generator import ReportGenerator
except ImportError:
    logger.warning("Could not import Reporting. Some features may not work correctly.")

# Create Flask app
app = Flask(__name__,
            template_folder=os.path.join(parent_dir, 'templates'),
            static_folder=os.path.join(parent_dir, 'static'))
CORS(app)

# Global variables
config = {}
ga4_browser = None
reminder_manager = None
notification_handler = None
customer_manager = None
invoice_manager = None
appointment_manager = None
report_generator = None

def find_ga4_installation():
    """Find GA4 installation directory or Data Exports folder

    Returns:
        Path to GA4 installation directory or Data Exports folder, or None if not found
    """
    # Look for Data Exports folder in Google Drive
    data_exports_path = r"/Users/adamrutstein/Library/CloudStorage/GoogleDrive-adam@elimotors.co.uk/My Drive/Data Exports"
    if os.path.exists(data_exports_path) and os.path.isdir(data_exports_path):
        logger.info(f"Found Data Exports folder at {data_exports_path}")
        return data_exports_path

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
        "sqlite_db_path": os.path.join(os.path.dirname(config_path), "garage_system.db"),
        "system": {
            "name": "Garage Management System",
            "version": "1.0.0",
            "port": 5000,
            "host": "0.0.0.0",
            "debug": False,
            "auto_import_csv": True,
            "auto_create_reminders": True
        },
        "garage_details": {
            "name": "Your Garage",
            "address": "123 Main Street, Anytown, AN1 1AA",
            "phone": "01234 567890",
            "email": "info@yourgarage.com",
            "website": "www.yourgarage.com"
        },
        "mot_reminder": {
            "reminder_days": [30, 14, 7, 3, 1],
            "templates": {
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
            }
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
        "dvla_api": {
            "enabled": False,
            "api_key": ""
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

            # Ensure database path is valid
            if not config.get('sqlite_db_path') or not os.path.dirname(config.get('sqlite_db_path')):
                config['sqlite_db_path'] = os.path.join(os.path.dirname(config_path), "garage_system.db")
                logger.info(f"Updated database path to {config['sqlite_db_path']}")

                # Save updated config
                with open(config_path, 'w') as f:
                    json.dump(config, f, indent=4)

            return config
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")

    # Create default configuration if file doesn't exist
    ga4_path = find_ga4_installation()
    return create_default_config(config_path, ga4_path)

def init_database(db_path):
    """Initialize the database

    Args:
        db_path: Path to SQLite database
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables if they don't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        address TEXT,
        phone TEXT,
        email TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS vehicles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        registration TEXT NOT NULL,
        make TEXT,
        model TEXT,
        year INTEGER,
        color TEXT,
        vin TEXT,
        mot_expiry TEXT,
        customer_id INTEGER,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers (id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS mot_reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_id INTEGER,
        reminder_date TEXT,
        reminder_type TEXT,
        reminder_status TEXT,
        sent_date TEXT,
        response_date TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT NOT NULL,
        customer_id INTEGER,
        vehicle_id INTEGER,
        invoice_date TEXT,
        due_date TEXT,
        total_amount REAL,
        tax_amount REAL,
        status TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers (id),
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS invoice_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER,
        description TEXT,
        quantity INTEGER,
        unit_price REAL,
        tax_rate REAL,
        amount REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (invoice_id) REFERENCES invoices (id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        vehicle_id INTEGER,
        appointment_date TEXT,
        appointment_time TEXT,
        duration INTEGER,
        service_type TEXT,
        status TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers (id),
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
    )
    ''')

    # Commit changes and close connection
    conn.commit()
    conn.close()

    logger.info(f"Initialized database at {db_path}")

def init_system(config_path):
    """Initialize the system

    Args:
        config_path: Path to configuration file
    """
    global config, ga4_browser, reminder_manager, notification_handler
    global customer_manager, invoice_manager, appointment_manager, report_generator

    # Load configuration
    config = load_config(config_path)

    # Initialize database
    init_database(config['sqlite_db_path'])

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

    # Initialize GA4 browser
    try:
        ga4_browser = DirectGA4Browser(config['ga4_path'], config['sqlite_db_path'])
        # Start monitoring for CSV files in a separate thread
        threading.Thread(target=ga4_browser.start_monitoring, daemon=True).start()
        logger.info("GA4 Direct Access Browser started")
    except Exception as e:
        logger.error(f"Error starting GA4 Direct Access Browser: {e}")

    # Initialize MOT reminder manager
    try:
        reminder_manager = MOTReminderManager(config['sqlite_db_path'], config_path)
        notification_handler = NotificationHandler(config_path)
        logger.info("MOT Reminder System initialized")
    except Exception as e:
        logger.error(f"Error initializing MOT Reminder System: {e}")

    # Initialize Customer Management
    try:
        customer_manager = CustomerManager(config['sqlite_db_path'])
        logger.info("Customer Management initialized")
    except Exception as e:
        logger.error(f"Error initializing Customer Management: {e}")

    # Initialize Invoice Management
    try:
        invoice_manager = InvoiceManager(config['sqlite_db_path'], config_path)
        logger.info("Invoice Management initialized")
    except Exception as e:
        logger.error(f"Error initializing Invoice Management: {e}")

    # Initialize Appointment Scheduling
    try:
        appointment_manager = AppointmentManager(config['sqlite_db_path'], config_path)
        logger.info("Appointment Scheduling initialized")
    except Exception as e:
        logger.error(f"Error initializing Appointment Scheduling: {e}")

    # Initialize Reporting
    try:
        report_generator = ReportGenerator(config['sqlite_db_path'], config_path)
        logger.info("Reporting initialized")
    except Exception as e:
        logger.error(f"Error initializing Reporting: {e}")

    logger.info("System initialized")

# Routes for the system
@app.route('/')
def index():
    """Home page"""
    # Get component status
    components = [
        {
            "id": "ga4",
            "name": "GA4 Data Access",
            "description": "Access and search GA4 data",
            "status": "Running" if ga4_browser and ga4_browser.is_monitoring else "Stopped",
            "url": "/ga4"
        },
        {
            "id": "mot",
            "name": "MOT Reminders",
            "description": "Manage MOT reminders",
            "status": "Running" if reminder_manager else "Not Available",
            "url": "/mot"
        },
        {
            "id": "customers",
            "name": "Customer Management",
            "description": "Manage customer information",
            "status": "Running" if customer_manager else "Not Available",
            "url": "/customers"
        },
        {
            "id": "invoices",
            "name": "Invoice Management",
            "description": "Generate and track invoices",
            "status": "Running" if invoice_manager else "Not Available",
            "url": "/invoices"
        },
        {
            "id": "appointments",
            "name": "Appointment Scheduling",
            "description": "Manage garage appointments",
            "status": "Running" if appointment_manager else "Not Available",
            "url": "/appointments"
        },
        {
            "id": "reports",
            "name": "Reporting",
            "description": "Business analytics and reporting",
            "status": "Running" if report_generator else "Not Available",
            "url": "/reports"
        }
    ]

    # Get stats
    stats = {
        "vehicle_count": 0,
        "customer_count": 0,
        "reminder_count": 0,
        "appointment_count": 0,
        "invoice_count": 0,
        "document_count": 0,
        "estimate_count": 0,
        "jobcard_count": 0
    }

    # Try to get actual counts from database
    try:
        conn = sqlite3.connect(config['sqlite_db_path'])
        cursor = conn.cursor()

        # Get vehicle count
        cursor.execute("SELECT COUNT(*) FROM vehicles")
        stats["vehicle_count"] = cursor.fetchone()[0]

        # Get customer count
        cursor.execute("SELECT COUNT(*) FROM customers")
        stats["customer_count"] = cursor.fetchone()[0]

        # Get reminder count
        cursor.execute("SELECT COUNT(*) FROM mot_reminders")
        stats["reminder_count"] = cursor.fetchone()[0]

        # Get appointment count
        cursor.execute("SELECT COUNT(*) FROM appointments")
        stats["appointment_count"] = cursor.fetchone()[0]

        # Get invoice count
        cursor.execute("SELECT COUNT(*) FROM invoices")
        stats["invoice_count"] = cursor.fetchone()[0]

        conn.close()
    except Exception as e:
        logger.error(f"Error getting stats: {e}")

    return render_template('index.html',
                          components=components,
                          stats=stats,
                          current_year=datetime.now().year,
                          garage_name=config.get('garage_details', {}).get('name', 'Your Garage'))

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

@app.route('/appointments')
def appointments_page():
    """Appointment Scheduling page"""
    return render_template('appointments.html')

@app.route('/reports')
def reports_page():
    """Reporting page"""
    return render_template('reports.html')

@app.route('/api/system_status')
def system_status():
    """API endpoint for system status"""
    try:
        # Check GA4 browser status
        ga4_status = "Running" if ga4_browser and ga4_browser.is_monitoring else "Stopped"

        # Get counts from database
        conn = sqlite3.connect(config['sqlite_db_path'])
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get vehicle count
        vehicle_count = 0
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vehicles'")
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) as count FROM vehicles")
            row = cursor.fetchone()
            if row:
                vehicle_count = row['count']

        # Get customer count
        customer_count = 0
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customers'")
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) as count FROM customers")
            row = cursor.fetchone()
            if row:
                customer_count = row['count']

        # Get reminder count
        reminder_count = 0
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mot_reminders'")
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) as count FROM mot_reminders")
            row = cursor.fetchone()
            if row:
                reminder_count = row['count']

        # Get invoice count
        invoice_count = 0
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invoices'")
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) as count FROM invoices")
            row = cursor.fetchone()
            if row:
                invoice_count = row['count']

        # Get appointment count
        appointment_count = 0
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='appointments'")
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) as count FROM appointments")
            row = cursor.fetchone()
            if row:
                appointment_count = row['count']

        conn.close()

        return jsonify({
            'success': True,
            'ga4_status': ga4_status,
            'ga4_path': config['ga4_path'],
            'vehicle_count': vehicle_count,
            'customer_count': customer_count,
            'reminder_count': reminder_count,
            'invoice_count': invoice_count,
            'appointment_count': appointment_count,
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
    parser = argparse.ArgumentParser(description='Garage Management System')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--ga4-path', help='Path to GA4 installation directory')
    parser.add_argument('--port', type=int, default=8090, help='Port to run web server on')
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
