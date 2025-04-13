#!/usr/bin/env python3
"""
Integrated Garage Management System

This script implements a comprehensive garage management system that integrates:
1. GA4 Direct Access Tool - For accessing GA4 data
2. MOT Reminder System - For managing MOT reminders
3. Customer Management - For managing customer information
4. Invoice Management - For generating and tracking invoices
5. Appointment Scheduling - For managing appointments
6. Document Browser - For browsing and connecting all GA4 data

All components work together with a unified interface and shared data.
"""

import os
import sys
import json
import csv
import sqlite3
import logging
import re
import time
import argparse
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_file
from werkzeug.utils import secure_filename
from apscheduler.schedulers.background import BackgroundScheduler
import threading
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Increase CSV field size limit to handle large fields in GA4 exports
csv.field_size_limit(2**30)  # Set to a very large value (1GB)

# Import document browser module
# Commented out to prevent loading the document browser connector
"""
try:
    from document_browser import (
        import_documents, 
        get_documents, 
        get_document_by_id, 
        get_document_types,
        get_customer_documents,
        get_vehicle_documents
    )
    document_browser_available = True
except ImportError:
    document_browser_available = False
    logging.warning("Document browser module not available")
"""
# Set document_browser_available to False
document_browser_available = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('IntegratedSystem')

# Import DVLA integration
try:
    # Import after logger is defined
    from dvla_integration import (
        verify_vehicle_mot, 
        batch_verify_vehicles, 
        schedule_mot_verification, 
        verify_single_vehicle_and_update,
        DVLA_AVAILABLE
    )
    logger.info("DVLA integration module loaded successfully")
except ImportError as e:
    logger.error(f"Could not import DVLA integration module: {e}")
    DVLA_AVAILABLE = False

# Add parent directory to path to import modules
parent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(parent_dir)

# Create Flask app
app = Flask(__name__, 
            template_folder=os.path.join(parent_dir, 'templates'),
            static_folder=os.path.join(parent_dir, 'static'))
app.secret_key = os.urandom(24)

# Add custom filters
@app.template_filter('to_datetime')
def to_datetime(date_str):
    """Convert a date string to a datetime object"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return None

# Global variables
config = {}
db_path = ""
last_sync_time = datetime.now()

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
            logger.info(f"Found GA4 installation at {path}")
            return path
    
    # Check if environment variable is set
    if 'GA4_PATH' in os.environ:
        path = os.environ['GA4_PATH']
        if os.path.exists(path) and os.path.isdir(path):
            logger.info(f"Found GA4 installation from environment variable at {path}")
            return path
    
    logger.warning("GA4 installation not found")
    return None

def load_config():
    """Load configuration from file"""
    global config, db_path
    
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'garage_system_config.json')
    
    # Create default config if it doesn't exist
    if not os.path.exists(config_path):
        default_config = {
            "ga4_path": find_ga4_installation(),
            "db_path": os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'garage_system.db'),
            "mot_reminder_days": [30, 14, 7, 1],
            "email": {
                "enabled": False,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "smtp_username": "",
                "smtp_password": "",
                "sender_email": ""
            }
        }
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Write default config
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=4)
        
        config = default_config
        logger.info(f"Created default configuration at {config_path}")
    else:
        # Load existing config
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            config = {}
    
    # Set database path
    db_path = config.get('db_path', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'garage_system.db'))
    
    # Create database directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

def init_database():
    """Initialize the database"""
    global db_path
    
    # Create database directory if it doesn't exist
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables if they don't exist
    
    # Customers table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT,
        last_name TEXT,
        email TEXT,
        phone TEXT,
        address TEXT,
        city TEXT,
        postal_code TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Vehicles table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS vehicles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        registration TEXT,
        make TEXT,
        model TEXT,
        year INTEGER,
        color TEXT,
        vin TEXT,
        engine_size TEXT,
        fuel_type TEXT,
        transmission TEXT,
        customer_id INTEGER,
        mot_expiry DATE,
        mot_status TEXT,
        last_mot_check DATE,
        tax_expiry DATE,
        service_interval INTEGER,
        next_service_date DATE,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers (id)
    )
    ''')
    
    # Service records table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS service_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_id INTEGER,
        service_date DATE,
        service_type TEXT,
        mileage INTEGER,
        description TEXT,
        cost REAL,
        technician TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
    )
    ''')
    
    # MOT history table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS mot_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_id INTEGER,
        test_date DATE,
        expiry_date DATE,
        result TEXT,
        advisory_notes TEXT,
        failure_reasons TEXT,
        test_center TEXT,
        mileage INTEGER,
        tester TEXT,
        certificate_number TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
    )
    ''')
    
    # Reminders table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_id INTEGER,
        reminder_date DATE,
        reminder_type TEXT,
        notes TEXT,
        status TEXT DEFAULT 'Pending',
        sent_at TIMESTAMP,
        created_at TIMESTAMP,
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
    )
    ''')
    
    # Invoices table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT NOT NULL,
        customer_id INTEGER,
        vehicle_id INTEGER,
        invoice_date TEXT,
        due_date TEXT,
        total_amount REAL,
        status TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers (id),
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
    )
    ''')
    
    # Appointments table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_id INTEGER,
        appointment_date TEXT,
        appointment_time TEXT,
        appointment_type TEXT,
        duration INTEGER,
        notes TEXT,
        status TEXT DEFAULT 'Scheduled',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
    )
    ''')
    
    # Commit changes
    conn.commit()
    
    # Close connection
    conn.close()
    
    logger.info("Database initialized successfully")

def import_ga4_data():
    """Import data from GA4 files"""
    ga4_path = config.get('ga4_path')
    if not ga4_path or not os.path.exists(ga4_path):
        logger.warning("GA4 path not set or does not exist. Cannot import data.")
        return
    
    # Don't automatically open the data loader window
    # Instead, just log that data import is available
    logger.info("GA4 data import is available through the web interface.")
    
    # Process any available data files in the background
    process_ga4_data_files()

def process_ga4_data_files():
    """Process GA4 data files in the background"""
    try:
        ga4_path = config.get('ga4_path')
        if not ga4_path or not os.path.exists(ga4_path):
            return
        
        # Check for vehicle data
        vehicle_files = []
        for file in os.listdir(ga4_path):
            if file.lower().startswith('vehicle') and file.lower().endswith('.csv'):
                vehicle_files.append(os.path.join(ga4_path, file))
        
        # Process vehicle files
        for file_path in vehicle_files:
            try:
                import_vehicles_from_csv(file_path)
                # Move processed file to archive folder
                archive_folder = os.path.join(ga4_path, 'archive')
                if not os.path.exists(archive_folder):
                    os.makedirs(archive_folder)
                shutil.move(file_path, os.path.join(archive_folder, os.path.basename(file_path)))
            except Exception as e:
                logger.error(f"Error processing vehicle file {file_path}: {e}")
        
        # Check for customer data
        customer_files = []
        for file in os.listdir(ga4_path):
            if file.lower().startswith('customer') and file.lower().endswith('.csv'):
                customer_files.append(os.path.join(ga4_path, file))
        
        # Process customer files
        for file_path in customer_files:
            try:
                import_customers_from_csv(file_path)
                # Move processed file to archive folder
                archive_folder = os.path.join(ga4_path, 'archive')
                if not os.path.exists(archive_folder):
                    os.makedirs(archive_folder)
                shutil.move(file_path, os.path.join(archive_folder, os.path.basename(file_path)))
            except Exception as e:
                logger.error(f"Error processing customer file {file_path}: {e}")
    
    except Exception as e:
        logger.error(f"Error processing GA4 data files: {e}")

def sync_ga4_data():
    """Manually sync data from GA4"""
    global last_sync_time
    
    # Import data from GA4
    import_ga4_data()
    
    # Update last sync time
    last_sync_time = datetime.now()
    
    return last_sync_time.strftime("%Y-%m-%d %H:%M:%S")

def get_vehicles_due_for_mot(days=30):
    """Get vehicles due for MOT within the specified number of days"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get current date
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Get vehicles due for MOT
        cursor.execute("""
        SELECT v.id, v.registration, v.make, v.model, v.mot_expiry, c.name as customer_name, c.phone, c.email
        FROM vehicles v
        LEFT JOIN customers c ON v.customer_id = c.id
        WHERE date(v.mot_expiry) <= date(?, '+' || ? || ' days')
        AND date(v.mot_expiry) >= date(?)
        ORDER BY v.mot_expiry
        """, (current_date, days, current_date))
        
        vehicles = []
        for row in cursor.fetchall():
            vehicles.append(dict(row))
        
        conn.close()
        return vehicles
    except Exception as e:
        logger.error(f"Error getting vehicles due for MOT: {e}")
        return []

def get_recent_reminders(limit=10):
    """Get recent MOT reminders"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT r.id, r.reminder_date, r.reminder_type, r.reminder_status, r.sent_date,
               v.registration, v.make, v.model, v.mot_expiry, c.name as customer_name
        FROM mot_reminders r
        JOIN vehicles v ON r.vehicle_id = v.id
        LEFT JOIN customers c ON v.customer_id = c.id
        ORDER BY r.id DESC
        LIMIT ?
        """, (limit,))
        
        reminders = []
        for row in cursor.fetchall():
            reminders.append(dict(row))
        
        conn.close()
        return reminders
    except Exception as e:
        logger.error(f"Error getting recent reminders: {e}")
        return []

def get_upcoming_appointments(days=7):
    """Get upcoming appointments within the specified number of days"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get current date
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        cursor.execute("""
        SELECT a.id, a.appointment_date, a.appointment_time, a.service_type, a.status,
               v.registration, v.make, v.model, c.name as customer_name, c.phone
        FROM appointments a
        JOIN vehicles v ON a.vehicle_id = v.id
        JOIN customers c ON a.customer_id = c.id
        WHERE date(a.appointment_date) <= date(?, '+' || ? || ' days')
        AND date(a.appointment_date) >= date(?)
        ORDER BY a.appointment_date, a.appointment_time
        """, (current_date, days, current_date))
        
        appointments = []
        for row in cursor.fetchall():
            appointments.append(dict(row))
        
        conn.close()
        return appointments
    except Exception as e:
        logger.error(f"Error getting upcoming appointments: {e}")
        return []

def create_mot_reminder(vehicle_id, reminder_date, reminder_type='email'):
    """Create a new MOT reminder"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get vehicle details
        cursor.execute("""
        SELECT v.*, c.name as customer_name, c.email, c.phone
        FROM vehicles v
        LEFT JOIN customers c ON v.customer_id = c.id
        WHERE v.id = ?
        """, (vehicle_id,))
        
        vehicle = cursor.fetchone()
        
        if not vehicle:
            logger.error(f"Vehicle not found: {vehicle_id}")
            return False
        
        # Create reminder
        cursor.execute("""
        INSERT INTO mot_reminders (vehicle_id, reminder_date, reminder_type, reminder_status, notes)
        VALUES (?, ?, ?, ?, ?)
        """, (
            vehicle_id,
            reminder_date,
            reminder_type,
            'pending',
            f"MOT due on {vehicle['mot_expiry']}"
        ))
        
        reminder_id = cursor.lastrowid
        
        # Commit changes
        conn.commit()
        conn.close()
        
        logger.info(f"Created MOT reminder for vehicle {vehicle['registration']}")
        
        return reminder_id
    
    except Exception as e:
        logger.error(f"Error creating MOT reminder: {e}")
        return False

def send_mot_reminders():
    """Send pending MOT reminders"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get pending reminders
        cursor.execute("""
        SELECT r.id, r.vehicle_id, r.reminder_date, r.reminder_type, r.notes,
               v.registration, v.make, v.model, v.mot_expiry, c.name as customer_name, c.email, c.phone
        FROM mot_reminders r
        JOIN vehicles v ON r.vehicle_id = v.id
        LEFT JOIN customers c ON v.customer_id = c.id
        WHERE r.reminder_status = 'pending'
        AND date(r.reminder_date) <= date('now')
        """)
        
        reminders = cursor.fetchall()
        
        for reminder in reminders:
            success = False
            
            # Send reminder based on type
            if reminder['reminder_type'] == 'email' and reminder['email']:
                success = send_email_reminder(reminder)
            elif reminder['reminder_type'] == 'sms' and reminder['phone']:
                success = send_sms_reminder(reminder)
            
            # Update reminder status
            if success:
                cursor.execute("""
                UPDATE mot_reminders
                SET reminder_status = 'sent', sent_date = date('now')
                WHERE id = ?
                """, (reminder['id'],))
            else:
                cursor.execute("""
                UPDATE mot_reminders
                SET notes = ?
                WHERE id = ?
                """, (
                    f"{reminder['notes']} - Failed to send on {datetime.now().strftime('%Y-%m-%d')}",
                    reminder['id']
                ))
        
        # Commit changes
        conn.commit()
        conn.close()
        
        logger.info(f"Processed {len(reminders)} MOT reminders")
        
        return len(reminders)
    
    except Exception as e:
        logger.error(f"Error sending MOT reminders: {e}")
        return 0

def start_reminder_scheduler():
    """Start the reminder scheduler"""
    def reminder_worker():
        while True:
            try:
                # Send reminders
                send_mot_reminders()
                
                # Sleep for 1 hour
                time.sleep(3600)
            except Exception as e:
                logger.error(f"Error in reminder worker: {e}")
                time.sleep(60)  # Sleep for 1 minute on error
    
    # Start reminder worker thread
    thread = threading.Thread(target=reminder_worker, daemon=True)
    thread.start()
    
    logger.info("Started MOT reminder scheduler")
    
    return thread

def start_auto_sync(interval_minutes=15):
    """Start automatic synchronization of GA4 data at regular intervals"""
    def auto_sync_worker():
        while True:
            try:
                logger.info(f"Auto-sync: Starting scheduled synchronization of GA4 data")
                sync_ga4_data()
                logger.info(f"Auto-sync: Completed scheduled synchronization of GA4 data")
            except Exception as e:
                logger.error(f"Auto-sync: Error during scheduled synchronization: {e}")
            
            # Sleep for the specified interval
            time.sleep(interval_minutes * 60)
    
    # Start the auto-sync thread
    auto_sync_thread = threading.Thread(target=auto_sync_worker, daemon=True)
    auto_sync_thread.start()
    logger.info(f"Started automatic synchronization of GA4 data every {interval_minutes} minutes")

class GA4FileHandler(FileSystemEventHandler):
    """Handler for GA4 file system events"""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.last_import_time = 0
        self.import_cooldown = 10  # Seconds between imports to prevent multiple imports
    
    def on_created(self, event):
        """Handle file creation events"""
        self._handle_file_event(event)
    
    def on_modified(self, event):
        """Handle file modification events"""
        self._handle_file_event(event)
    
    def _handle_file_event(self, event):
        """Process file events"""
        # Skip directories
        if event.is_directory:
            return
        
        # Check if file is a GA4 data file
        if event.src_path.endswith('.GA4') or (event.src_path.endswith('.csv') and 'export' in event.src_path.lower()):
            # Check cooldown
            current_time = time.time()
            if current_time - self.last_import_time > self.import_cooldown:
                logger.info(f"Detected change in GA4 data file: {event.src_path}")
                self.last_import_time = current_time
                
                # Import data
                import_ga4_data()

def start_file_watcher():
    """Start the GA4 file watcher"""
    ga4_path = config.get('ga4_path')
    if not ga4_path or not os.path.exists(ga4_path):
        logger.warning("GA4 path not set or does not exist. Cannot start file watcher.")
        return
    
    try:
        # Create event handler and observer
        event_handler = GA4FileHandler(app)
        observer = Observer()
        
        # Watch GA4 directory
        observer.schedule(event_handler, ga4_path, recursive=True)
        
        # Start observer
        observer.start()
        logger.info(f"Started GA4 file watcher for {ga4_path}")
        
        # Also watch exports directory if it exists
        exports_dir = os.path.join(ga4_path, 'exports')
        if os.path.exists(exports_dir) and os.path.isdir(exports_dir):
            observer.schedule(event_handler, exports_dir, recursive=True)
            logger.info(f"Watching GA4 exports directory: {exports_dir}")
        
        return observer
    
    except Exception as e:
        logger.error(f"Error starting GA4 file watcher: {e}")
        return None

# Routes
@app.route('/')
def index():
    """Home page"""
    try:
        # Get counts
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get vehicle count
        cursor.execute("SELECT COUNT(*) FROM vehicles")
        vehicle_count = cursor.fetchone()[0]
        
        # Get customer count
        cursor.execute("SELECT COUNT(*) FROM customers")
        customer_count = cursor.fetchone()[0]
        
        # Get reminder count
        cursor.execute("SELECT COUNT(*) FROM mot_reminders")
        reminder_count = cursor.fetchone()[0]
        
        # Get invoice count
        cursor.execute("SELECT COUNT(*) FROM invoices")
        invoice_count = cursor.fetchone()[0]
        
        # Get appointment count
        cursor.execute("SELECT COUNT(*) FROM appointments")
        appointment_count = cursor.fetchone()[0]
        
        # Get document counts if document browser is available
        document_count = 0
        estimate_count = 0
        jobcard_count = 0
        
        if document_browser_available:
            try:
                # Get total document count
                cursor.execute("SELECT COUNT(*) FROM documents")
                document_count = cursor.fetchone()[0]
                
                # Get estimate count
                cursor.execute("SELECT COUNT(*) FROM documents WHERE document_type = 'Estimate'")
                estimate_count = cursor.fetchone()[0]
                
                # Get job card count
                cursor.execute("SELECT COUNT(*) FROM documents WHERE document_type = 'Job Card'")
                jobcard_count = cursor.fetchone()[0]
            except Exception as e:
                logger.error(f"Error getting document counts: {e}")
        
        conn.close()
        
        # Get vehicles due for MOT
        vehicles_due = get_vehicles_due_for_mot()
        
        # Get recent reminders
        recent_reminders = get_recent_reminders()
        
        # Get upcoming appointments
        upcoming_appointments = get_upcoming_appointments()
        
        # Prepare stats
        stats = {
            'vehicle_count': vehicle_count,
            'customer_count': customer_count,
            'reminder_count': reminder_count,
            'invoice_count': invoice_count,
            'appointment_count': appointment_count,
            'document_count': document_count,
            'estimate_count': estimate_count,
            'jobcard_count': jobcard_count
        }
        
        # Prepare components
        components = [
            {
                'title': 'Vehicles Due for MOT',
                'icon': 'car-front',
                'count': len(vehicles_due),
                'items': vehicles_due,
                'link': '/reminders/create',
                'link_text': 'Create Reminder'
            },
            {
                'title': 'Recent Reminders',
                'icon': 'bell',
                'count': len(recent_reminders),
                'items': recent_reminders,
                'link': '/reminders',
                'link_text': 'View All Reminders'
            },
            {
                'title': 'Upcoming Appointments',
                'icon': 'calendar-check',
                'count': len(upcoming_appointments),
                'items': upcoming_appointments,
                'link': '/appointments',
                'link_text': 'View All Appointments'
            }
        ]
        
        return render_template('index.html', stats=stats, components=components)
    
    except Exception as e:
        logger.error(f"Error rendering index page: {e}")
        return f"Error: {e}"

@app.route('/customers')
def customers():
    """Customers page"""
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get customers with vehicle count
        cursor.execute("""
        SELECT c.id, c.name as full_name, c.phone, c.email, c.address,
               COUNT(v.id) as vehicle_count
        FROM customers c
        LEFT JOIN vehicles v ON c.id = v.customer_id
        GROUP BY c.id
        ORDER BY c.name
        """)
        
        customers_data = cursor.fetchall()
        
        # Get total counts for statistics
        cursor.execute("""
        SELECT 
            COUNT(*) as total_customers,
            (SELECT COUNT(DISTINCT customer_id) FROM vehicles) as active_customers,
            (SELECT COUNT(*) FROM vehicles) as total_vehicles
        FROM customers
        """)
        
        stats = cursor.fetchone()
        
        # Close connection
        conn.close()
        
        # Format customers for template
        customers = []
        for customer in customers_data:
            # Split full name into first and last name for display
            name_parts = customer['full_name'].split(' ', 1) if customer['full_name'] else ['', '']
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            customers.append({
                'id': customer['id'],
                'first_name': first_name,
                'last_name': last_name,
                'full_name': customer['full_name'],
                'phone': customer['phone'],
                'email': customer['email'],
                'address': customer['address'],
                'vehicle_count': customer['vehicle_count']
            })
        
        return render_template('customers.html', 
                               customers=customers, 
                               stats=stats,
                               page=1,
                               total_pages=1,
                               now=datetime.now())
    
    except Exception as e:
        logger.error(f"Error displaying customers: {e}")
        flash(f'Error displaying customers: {e}', 'danger')
        return redirect(url_for('index'))

@app.route('/vehicles')
def vehicles():
    """Vehicle management page"""
    try:
        # Get query parameters
        registration = request.args.get('registration', '')
        make = request.args.get('make', '')
        model = request.args.get('model', '')
        customer = request.args.get('customer', '')
        mot_status = request.args.get('mot_status', '')
        service_due = request.args.get('service_due', '')
        sort_by = request.args.get('sort_by', 'registration')
        page = int(request.args.get('page', 1))
        per_page = 20
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Build query
        query = """
        SELECT v.*, c.name as customer_name
        FROM vehicles v
        LEFT JOIN customers c ON v.customer_id = c.id
        WHERE 1=1
        """
        params = []
        
        if registration:
            query += " AND v.registration LIKE ?"
            params.append(f"%{registration}%")
        
        if make:
            query += " AND v.make LIKE ?"
            params.append(f"%{make}%")
        
        if model:
            query += " AND v.model LIKE ?"
            params.append(f"%{model}%")
        
        if customer:
            query += " AND c.name LIKE ?"
            params.append(f"%{customer}%")
        
        # Current date for MOT status filtering
        current_date = datetime.now().strftime('%Y-%m-%d')
        expiring_soon_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        if mot_status == 'valid':
            query += " AND v.mot_expiry > ?"
            params.append(current_date)
        elif mot_status == 'expiring':
            query += " AND v.mot_expiry BETWEEN ? AND ?"
            params.append(current_date)
            params.append(expiring_soon_date)
        elif mot_status == 'expired':
            query += " AND v.mot_expiry < ?"
            params.append(current_date)
        
        if service_due == 'due':
            query += " AND (julianday(?) - julianday(v.last_service)) > 365"
            params.append(current_date)
        elif service_due == 'not_due':
            query += " AND (julianday(?) - julianday(v.last_service)) <= 365"
            params.append(current_date)
        
        # Count total vehicles matching criteria
        count_query = f"SELECT COUNT(*) FROM ({query})"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        total_pages = (total_count + per_page - 1) // per_page
        
        # Add sorting and pagination
        if sort_by == 'registration':
            query += " ORDER BY v.registration"
        elif sort_by == 'make':
            query += " ORDER BY v.make"
        elif sort_by == 'model':
            query += " ORDER BY v.model"
        elif sort_by == 'mot_expiry':
            query += " ORDER BY v.mot_expiry"
        elif sort_by == 'last_service':
            query += " ORDER BY v.last_service"
        
        query += f" LIMIT {per_page} OFFSET {(page - 1) * per_page}"
        
        # Execute query
        cursor.execute(query, params)
        vehicles = cursor.fetchall()
        
        # Process vehicles to add MOT status
        processed_vehicles = []
        for vehicle in vehicles:
            v = dict(vehicle)
            if v['mot_expiry']:
                try:
                    mot_date = datetime.strptime(v['mot_expiry'], '%Y-%m-%d')
                    days_until_expiry = (mot_date - datetime.now()).days
                    
                    if days_until_expiry < 0:
                        v['mot_status'] = 'expired'
                    elif days_until_expiry <= 30:
                        v['mot_status'] = 'expiring'
                    else:
                        v['mot_status'] = 'valid'
                except:
                    v['mot_status'] = 'unknown'
            else:
                v['mot_status'] = 'unknown'
            
            processed_vehicles.append(v)
        
        # Get vehicle statistics
        cursor.execute("SELECT COUNT(*) FROM vehicles")
        total_vehicles = cursor.fetchone()[0]
        
        cursor.execute(f"SELECT COUNT(*) FROM vehicles WHERE mot_expiry < '{current_date}'")
        expired_mot_count = cursor.fetchone()[0]
        
        cursor.execute(f"SELECT COUNT(*) FROM vehicles WHERE mot_expiry BETWEEN '{current_date}' AND '{expiring_soon_date}'")
        expiring_mot_count = cursor.fetchone()[0]
        
        cursor.execute(f"SELECT COUNT(*) FROM vehicles WHERE (julianday('{current_date}') - julianday(last_service)) > 365")
        service_due_count = cursor.fetchone()[0]
        
        conn.close()
        
        return render_template('vehicles.html', 
                              vehicles=processed_vehicles,
                              page=page,
                              total_pages=total_pages,
                              total_vehicles=total_vehicles,
                              expired_mot_count=expired_mot_count,
                              expiring_mot_count=expiring_mot_count,
                              service_due_count=service_due_count)
    
    except Exception as e:
        logger.error(f"Error in vehicles route: {e}")
        return f"Error: {e}"

@app.route('/vehicles/<int:vehicle_id>')
def vehicle_detail(vehicle_id):
    """Display vehicle details"""
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get vehicle details
        cursor.execute("""
        SELECT v.*, c.name as customer_name, c.id as customer_id
        FROM vehicles v
        LEFT JOIN customers c ON v.customer_id = c.id
        WHERE v.id = ?
        """, (vehicle_id,))
        
        vehicle = cursor.fetchone()
        
        if not vehicle:
            flash('Vehicle not found', 'danger')
            return redirect(url_for('vehicles'))
        
        # Get customer details if available
        customer = None
        if vehicle['customer_id']:
            cursor.execute("SELECT * FROM customers WHERE id = ?", (vehicle['customer_id'],))
            customer = cursor.fetchone()
        
        # Get all customers for owner assignment
        cursor.execute("SELECT id, name FROM customers ORDER BY name")
        all_customers = cursor.fetchall()
        
        # Get service records
        cursor.execute("""
        SELECT * FROM service_records
        WHERE vehicle_id = ?
        ORDER BY service_date DESC
        """, (vehicle_id,))
        service_records = cursor.fetchall()
        
        # Get MOT history
        cursor.execute("""
        SELECT * FROM mot_history
        WHERE vehicle_id = ?
        ORDER BY test_date DESC
        """, (vehicle_id,))
        mot_history = cursor.fetchall()
        
        # Get related documents
        cursor.execute("""
        SELECT d.id, d.date, d.type, d.description, d.amount
        FROM documents d
        WHERE d.vehicle_id = ?
        ORDER BY d.date DESC
        """, (vehicle_id,))
        documents = cursor.fetchall()
        
        # Get reminders for this vehicle
        cursor.execute("""
        SELECT * FROM mot_reminders
        WHERE vehicle_id = ?
        ORDER BY created_at DESC
        """, (vehicle_id,))
        reminders = cursor.fetchall()
        
        # Get appointments for this vehicle
        cursor.execute("""
        SELECT * FROM appointments
        WHERE vehicle_id = ?
        ORDER BY appointment_date DESC
        """, (vehicle_id,))
        appointments = cursor.fetchall()
        
        conn.close()
        
        # Current date for templates
        today_date = datetime.now().strftime('%Y-%m-%d')
        
        return render_template('vehicle_detail.html', 
                               vehicle=vehicle, 
                               customer=customer,
                               all_customers=all_customers,
                               service_records=service_records,
                               mot_history=mot_history,
                               documents=documents,
                               reminders=reminders,
                               appointments=appointments,
                               today_date=today_date,
                               now=datetime.now())
    
    except Exception as e:
        logger.error(f"Error displaying vehicle details: {e}")
        flash(f'Error displaying vehicle details: {e}', 'danger')
        return redirect(url_for('vehicles'))

@app.route('/vehicles/edit/<int:vehicle_id>', methods=['GET', 'POST'])
def edit_vehicle(vehicle_id):
    """Edit vehicle details"""
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if request.method == 'POST':
            # Get form data
            registration = request.form.get('registration')
            customer_id = request.form.get('customer_id') or None
            make = request.form.get('make')
            model = request.form.get('model')
            year = request.form.get('year')
            color = request.form.get('color')
            vin = request.form.get('vin')
            engine_size = request.form.get('engine_size')
            fuel_type = request.form.get('fuel_type')
            transmission = request.form.get('transmission')
            mot_expiry = request.form.get('mot_expiry')
            last_service = request.form.get('last_service')
            
            # Update vehicle
            cursor.execute("""
            UPDATE vehicles SET
                registration = ?,
                customer_id = ?,
                make = ?,
                model = ?,
                year = ?,
                color = ?,
                vin = ?,
                engine_size = ?,
                fuel_type = ?,
                transmission = ?,
                mot_expiry = ?,
                last_service = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (registration, customer_id, make, model, year, color, vin, engine_size, 
                  fuel_type, transmission, mot_expiry, last_service, vehicle_id))
            
            conn.commit()
            flash('Vehicle updated successfully', 'success')
            return redirect(url_for('vehicle_detail', vehicle_id=vehicle_id))
        
        # Get vehicle details for GET request
        cursor.execute("""
        SELECT * FROM vehicles WHERE id = ?
        """, (vehicle_id,))
        
        vehicle = cursor.fetchone()
        
        if not vehicle:
            flash('Vehicle not found', 'danger')
            return redirect(url_for('vehicles'))
        
        # Get all customers for dropdown
        cursor.execute("SELECT id, name FROM customers ORDER BY name")
        customers = cursor.fetchall()
        
        conn.close()
        
        return render_template('edit_vehicle.html', vehicle=vehicle, customers=customers)
    
    except Exception as e:
        logger.error(f"Error editing vehicle: {e}")
        flash(f'Error editing vehicle: {e}', 'danger')
        return redirect(url_for('vehicle_detail', vehicle_id=vehicle_id))

@app.route('/vehicles/assign_owner/<int:vehicle_id>', methods=['POST'])
def assign_owner(vehicle_id):
    """Assign an owner to a vehicle"""
    try:
        # Get form data
        customer_id = request.form.get('customer_id')
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Update vehicle
        cursor.execute("""
        UPDATE vehicles SET
            customer_id = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (customer_id, vehicle_id))
        
        conn.commit()
        conn.close()
        
        flash('Owner assigned successfully', 'success')
        return redirect(url_for('vehicle_detail', vehicle_id=vehicle_id))
    
    except Exception as e:
        logger.error(f"Error assigning owner: {e}")
        flash(f'Error assigning owner: {e}', 'danger')
        return redirect(url_for('vehicle_detail', vehicle_id=vehicle_id))

@app.route('/api/import_vehicles', methods=['POST'])
def api_import_vehicles():
    """API endpoint to import vehicles from GA4"""
    try:
        result = import_vehicles_from_ga4()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error importing vehicles: {e}")
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/upload_vehicles_csv', methods=['POST'])
def api_upload_vehicles_csv():
    """API endpoint to upload and process a vehicles CSV file"""
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "message": "No file part"})
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"success": False, "message": "No selected file"})
        
        if file and file.filename.endswith('.csv'):
            # Save the file temporarily
            temp_path = os.path.join(os.path.dirname(db_path), 'temp_vehicles.csv')
            file.save(temp_path)
            
            # Process the CSV file
            result = import_vehicles_from_csv(temp_path)
            
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            return jsonify(result)
        
        return jsonify({"success": False, "message": "Invalid file format. Please upload a CSV file."})
    
    except Exception as e:
        logger.error(f"Error uploading vehicles CSV: {e}")
        return jsonify({"success": False, "message": str(e)})

@app.route('/export_vehicles')
def export_vehicles():
    """Export vehicles to CSV"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all vehicles with customer names
        cursor.execute("""
        SELECT v.*, c.name as customer_name
        FROM vehicles v
        LEFT JOIN customers c ON v.customer_id = c.id
        """)
        
        vehicles = cursor.fetchall()
        conn.close()
        
        # Create CSV in memory
        from io import StringIO
        import csv
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['ID', 'Registration', 'Make', 'Model', 'Year', 'Color', 'VIN', 
                        'Engine Size', 'Fuel Type', 'Transmission', 'MOT Expiry', 
                        'Last Service', 'Customer ID', 'Customer Name'])
        
        # Write data
        for vehicle in vehicles:
            writer.writerow([
                vehicle['id'],
                vehicle['registration'],
                vehicle['make'],
                vehicle['model'],
                vehicle['year'],
                vehicle['color'],
                vehicle['vin'],
                vehicle['engine_size'],
                vehicle['fuel_type'],
                vehicle['transmission'],
                vehicle['mot_expiry'],
                vehicle['last_service'],
                vehicle['customer_id'],
                vehicle['customer_name']
            ])
        
        # Prepare response
        output.seek(0)
        
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=vehicles_export.csv"}
        )
    
    except Exception as e:
        logger.error(f"Error exporting vehicles: {e}")
        return f"Error: {e}"

def import_vehicles_from_ga4():
    """Import vehicles from GA4 exports"""
    try:
        ga4_path = config.get('ga4_path')
        if not ga4_path or not os.path.exists(ga4_path):
            return {"success": False, "message": "GA4 path not set or does not exist"}
        
        vehicles_csv = os.path.join(ga4_path, 'Data Exports', 'Vehicles.csv')
        
        if not os.path.exists(vehicles_csv):
            return {"success": False, "message": f"Vehicles CSV not found at {vehicles_csv}"}
        
        result = import_vehicles_from_csv(vehicles_csv)
        return result
    
    except Exception as e:
        logger.error(f"Error importing vehicles from GA4: {e}")
        return {"success": False, "message": str(e)}

def import_vehicles_from_csv(csv_path):
    """Import vehicles from a CSV file"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Track statistics
        stats = {
            'total': 0,
            'new': 0,
            'updated': 0,
            'errors': 0
        }
        
        with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                stats['total'] += 1
                
                try:
                    # Check if vehicle exists
                    cursor.execute("SELECT id FROM vehicles WHERE registration = ?", 
                                  (row.get('Registration', ''),))
                    
                    existing_vehicle = cursor.fetchone()
                    
                    # Try to find customer ID
                    customer_id = None
                    if 'Customer' in row and row['Customer']:
                        cursor.execute("SELECT id FROM customers WHERE name = ?", 
                                      (row['Customer'],))
                        customer_result = cursor.fetchone()
                        if customer_result:
                            customer_id = customer_result[0]
                    
                    # Prepare vehicle data
                    vehicle_data = {
                        'registration': row.get('Registration', ''),
                        'make': row.get('Make', ''),
                        'model': row.get('Model', ''),
                        'year': row.get('Year', ''),
                        'color': row.get('Colour', ''),
                        'vin': row.get('VIN', ''),
                        'engine_size': row.get('Engine Size', ''),
                        'fuel_type': row.get('Fuel Type', ''),
                        'transmission': row.get('Transmission', ''),
                        'mot_expiry': row.get('MOT Expiry', ''),
                        'last_service': row.get('Last Service', ''),
                        'customer_id': customer_id
                    }
                    
                    if existing_vehicle:
                        # Update existing vehicle
                        vehicle_id = existing_vehicle[0]
                        placeholders = ', '.join(f"{k} = ?" for k in vehicle_data.keys())
                        query = f"UPDATE vehicles SET {placeholders} WHERE id = ?"
                        
                        cursor.execute(query, list(vehicle_data.values()) + [vehicle_id])
                        stats['updated'] += 1
                    else:
                        # Insert new vehicle
                        placeholders = ', '.join(['?'] * len(vehicle_data))
                        columns = ', '.join(vehicle_data.keys())
                        query = f"INSERT INTO vehicles ({columns}) VALUES ({placeholders})"
                        
                        cursor.execute(query, list(vehicle_data.values()))
                        stats['new'] += 1
                
                except Exception as e:
                    logger.error(f"Error processing vehicle row: {e}")
                    stats['errors'] += 1
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": f"Processed {stats['total']} vehicles: {stats['new']} new, {stats['updated']} updated, {stats['errors']} errors"
        }
    
    except Exception as e:
        logger.error(f"Error importing vehicles from CSV: {e}")
        return {"success": False, "message": str(e)}

@app.route('/reminders')
def reminders():
    """Display MOT reminders"""
    try:
        # Get filter parameters
        days_filter = request.args.get('days', type=int)
        status_filter = request.args.get('status')
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Build query based on filters
        query = """
        SELECT v.id, v.registration, v.make, v.model, v.mot_expiry, v.mot_status, v.last_mot_check,
               c.id as customer_id, c.first_name, c.last_name, c.email, c.phone
        FROM vehicles v
        LEFT JOIN customers c ON v.customer_id = c.id
        WHERE v.mot_expiry IS NOT NULL
        """
        params = []
        
        if days_filter:
            query += " AND julianday(v.mot_expiry) - julianday('now') BETWEEN 0 AND ?"
            params.append(days_filter)
        
        if status_filter:
            query += " AND v.mot_status = ?"
            params.append(status_filter)
        
        query += " ORDER BY julianday(v.mot_expiry) - julianday('now')"
        
        # Execute query
        cursor.execute(query, params)
        reminders = cursor.fetchall()
        
        # Get statistics
        cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN julianday(mot_expiry) - julianday('now') BETWEEN 0 AND 14 THEN 1 ELSE 0 END) as due_soon,
            SUM(CASE WHEN julianday(mot_expiry) - julianday('now') < 0 THEN 1 ELSE 0 END) as overdue
        FROM vehicles
        WHERE mot_expiry IS NOT NULL
        """)
        stats = cursor.fetchone()
        
        # Close connection
        conn.close()
        
        return render_template('reminders.html', 
                               reminders=reminders, 
                               stats=stats, 
                               days_filter=days_filter,
                               status_filter=status_filter,
                               dvla_available=DVLA_AVAILABLE,
                               now=datetime.now())
    
    except Exception as e:
        logger.error(f"Error displaying reminders: {e}")
        flash(f'Error displaying reminders: {e}', 'danger')
        return redirect(url_for('index'))

@app.route('/reminders/create', methods=['GET', 'POST'])
def create_reminder():
    """Create a new MOT reminder"""
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if request.method == 'POST':
            # Get form data
            vehicle_id = request.form.get('vehicle_id', type=int)
            reminder_date = request.form.get('reminder_date')
            reminder_type = request.form.get('reminder_type')
            notes = request.form.get('notes')
            
            # Validate data
            if not vehicle_id or not reminder_date:
                flash('Vehicle and reminder date are required', 'danger')
                return redirect(url_for('create_reminder'))
            
            # Insert reminder
            cursor.execute("""
            INSERT INTO reminders (vehicle_id, reminder_date, reminder_type, notes, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            """, (vehicle_id, reminder_date, reminder_type, notes))
            
            # Commit changes
            conn.commit()
            
            flash('Reminder created successfully', 'success')
            return redirect(url_for('reminders'))
        
        # Get vehicles for dropdown
        cursor.execute("""
        SELECT v.id, v.registration, v.make, v.model, v.mot_expiry, v.mot_status,
               c.first_name, c.last_name
        FROM vehicles v
        LEFT JOIN customers c ON v.customer_id = c.id
        ORDER BY v.registration
        """)
        vehicles = cursor.fetchall()
        
        # Close connection
        conn.close()
        
        return render_template('create_reminder.html', vehicles=vehicles)
    
    except Exception as e:
        logger.error(f"Error creating reminder: {e}")
        flash(f'Error creating reminder: {e}', 'danger')
        return redirect(url_for('reminders'))

@app.route('/reminders/verify_all', methods=['GET'])
def verify_all_reminders():
    """Verify MOT status for all vehicles with reminders"""
    try:
        if not DVLA_AVAILABLE:
            flash('DVLA verification is not available', 'warning')
            return redirect(url_for('reminders'))
        
        # Get batch size from query parameter, default to 20
        batch_size = request.args.get('batch_size', 20, type=int)
        
        # Verify MOT status for vehicles
        verified, updated = batch_verify_vehicles(db_path, batch_size)
        
        flash(f"Verified {verified} vehicles, updated {updated} MOT records", 'success')
        return redirect(url_for('reminders'))
    
    except Exception as e:
        logger.error(f"Error verifying all reminders: {e}")
        flash(f'Error verifying all reminders: {e}', 'danger')
        return redirect(url_for('reminders'))

@app.route('/reminders/send/<int:reminder_id>', methods=['POST'])
def send_reminder(reminder_id):
    """Send a reminder to a customer"""
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get reminder details
        cursor.execute("""
        SELECT r.id, r.vehicle_id, r.reminder_date, r.reminder_type, r.notes,
               v.registration, v.make, v.model, v.mot_expiry,
               c.id as customer_id, c.first_name, c.last_name, c.email, c.phone
        FROM reminders r
        JOIN vehicles v ON r.vehicle_id = v.id
        LEFT JOIN customers c ON v.customer_id = c.id
        WHERE r.id = ?
        """, (reminder_id,))
        reminder = cursor.fetchone()
        
        if not reminder:
            flash('Reminder not found', 'danger')
            return redirect(url_for('reminders'))
        
        # Update reminder status
        cursor.execute("""
        UPDATE reminders
        SET sent_at = datetime('now'), status = 'Sent'
        WHERE id = ?
        """, (reminder_id,))
        
        # Commit changes
        conn.commit()
        
        # Close connection
        conn.close()
        
        # In a real system, this would send an email or SMS
        flash(f"Reminder sent to {reminder['first_name']} {reminder['last_name']} for {reminder['registration']}", 'success')
        return redirect(url_for('reminders'))
    
    except Exception as e:
        logger.error(f"Error sending reminder: {e}")
        flash(f'Error sending reminder: {e}', 'danger')
        return redirect(url_for('reminders'))

@app.route('/invoices')
def invoices():
    """Invoices page"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT i.id, i.invoice_number, i.invoice_date, i.due_date, i.total_amount, i.status,
               c.name as customer_name, v.registration
        FROM invoices i
        LEFT JOIN customers c ON i.customer_id = c.id
        LEFT JOIN vehicles v ON i.vehicle_id = v.id
        ORDER BY i.invoice_date DESC
        """)
        
        invoices = []
        for row in cursor.fetchall():
            invoices.append(dict(row))
        
        conn.close()
        return render_template('invoices.html', invoices=invoices)
    
    except Exception as e:
        logger.error(f"Error getting invoices: {e}")
        return f"Error: {e}"

@app.route('/appointments')
def appointments():
    """Appointments page"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT a.id, a.appointment_date, a.appointment_time, a.service_type, a.status, a.notes,
               v.registration, v.make, v.model, c.name as customer_name, c.phone
        FROM appointments a
        JOIN vehicles v ON a.vehicle_id = v.id
        JOIN customers c ON a.customer_id = c.id
        ORDER BY a.appointment_date, a.appointment_time
        """)
        
        appointments = []
        for row in cursor.fetchall():
            appointments.append(dict(row))
        
        conn.close()
        return render_template('appointments.html', appointments=appointments)
    
    except Exception as e:
        logger.error(f"Error getting appointments: {e}")
        return f"Error: {e}"

@app.route('/reports')
def reports():
    """Reports page"""
    return render_template('reports.html')

@app.route('/documents')
def documents():
    """Documents page"""
    if not document_browser_available:
        return render_template('error.html', message="Document browser module is not available")
    
    # Get filters from request
    page = request.args.get('page', 1, type=int)
    document_type = request.args.get('document_type', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    search = request.args.get('search', '')
    
    # Build filters
    filters = {}
    if document_type:
        filters['document_type'] = document_type
    if date_from:
        filters['date_from'] = date_from
    if date_to:
        filters['date_to'] = date_to
    if search:
        filters['search'] = search
    
    # Get documents
    result = get_documents(filters, page=page, per_page=20)
    
    # Get document types for filter dropdown
    document_types = get_document_types()
    
    return render_template('documents.html', 
                          documents=result['documents'], 
                          pagination=result, 
                          filters=filters,
                          document_types=document_types)

@app.route('/documents/<int:document_id>')
def document_detail(document_id):
    """Document detail page"""
    if not document_browser_available:
        return render_template('error.html', message="Document browser module is not available")
    
    # Get document
    document = get_document_by_id(document_id)
    
    if not document:
        return render_template('error.html', message=f"Document not found with ID: {document_id}")
    
    # Get related documents
    customer_documents = []
    vehicle_documents = []
    
    if document.get('customer_id'):
        customer_documents = get_customer_documents(document['customer_id'])['documents']
    
    if document.get('vehicle_id'):
        vehicle_documents = get_vehicle_documents(document['vehicle_id'])['documents']
    
    return render_template('document_detail.html', 
                          document=document,
                          customer_documents=customer_documents,
                          vehicle_documents=vehicle_documents)

@app.route('/documents/<int:document_id>/print')
def document_print(document_id):
    """Print document"""
    if not document_browser_available:
        return render_template('error.html', message="Document browser module is not available")
    
    # Get document
    document = get_document_by_id(document_id)
    
    if not document:
        return render_template('error.html', message=f"Document not found with ID: {document_id}")
    
    # Return print-friendly version
    return render_template('document_print.html', document=document)

@app.route('/documents/<int:document_id>/email', methods=['GET', 'POST'])
def document_email(document_id):
    """Email document to customer"""
    if not document_browser_available:
        return render_template('error.html', message="Document browser module is not available")
    
    # Get document
    document = get_document_by_id(document_id)
    
    if not document:
        return render_template('error.html', message=f"Document not found with ID: {document_id}")
    
    if request.method == 'POST':
        # Get form data
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        if not email or not subject or not message:
            flash('Please fill in all required fields', 'danger')
            return redirect(url_for('document_email', document_id=document_id))
        
        # Send email
        try:
            # Create email
            msg = MIMEMultipart()
            msg['From'] = config.get('email', {}).get('sender_email', '')
            msg['To'] = email
            msg['Subject'] = subject
            
            # Add message body
            msg.attach(MIMEText(message, 'plain'))
            
            # TODO: Add document as attachment
            
            # Send email
            smtp_server = config.get('email', {}).get('smtp_server', '')
            smtp_port = config.get('email', {}).get('smtp_port', 587)
            smtp_username = config.get('email', {}).get('smtp_username', '')
            smtp_password = config.get('email', {}).get('smtp_password', '')
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
            server.quit()
            
            flash('Email sent successfully', 'success')
            return redirect(url_for('document_detail', document_id=document_id))
        
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            flash(f'Error sending email: {str(e)}', 'danger')
            return redirect(url_for('document_email', document_id=document_id))
    
    # GET request - display form
    return render_template('document_email.html', document=document)

@app.route('/api/import_documents', methods=['POST'])
def api_import_documents():
    """API endpoint to import documents from GA4"""
    if not document_browser_available:
        return jsonify({
            'success': False,
            'message': 'Document browser module is not available'
        })
    
    try:
        success = import_documents()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Successfully imported documents from GA4'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Error importing documents from GA4'
            })
    
    except Exception as e:
        logger.error(f"Error importing documents from GA4: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/api/system_status')
def system_status():
    """API endpoint for system status"""
    try:
        # Get counts
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get vehicle count
        cursor.execute("SELECT COUNT(*) FROM vehicles")
        vehicle_count = cursor.fetchone()[0]
        
        # Get customer count
        cursor.execute("SELECT COUNT(*) FROM customers")
        customer_count = cursor.fetchone()[0]
        
        # Get reminder count
        cursor.execute("SELECT COUNT(*) FROM mot_reminders")
        reminder_count = cursor.fetchone()[0]
        
        # Get invoice count
        cursor.execute("SELECT COUNT(*) FROM invoices")
        invoice_count = cursor.fetchone()[0]
        
        # Get appointment count
        cursor.execute("SELECT COUNT(*) FROM appointments")
        appointment_count = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'ga4_path': config.get('ga4_path', 'Not set'),
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
            'message': str(e)
        })

@app.route('/api/vehicles/<int:vehicle_id>', methods=['GET'])
def get_vehicle(vehicle_id):
    """API endpoint to get vehicle details by ID"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get vehicle details
        cursor.execute("""
        SELECT v.*, c.name as customer_name, c.email, c.phone
        FROM vehicles v
        LEFT JOIN customers c ON v.customer_id = c.id
        WHERE v.id = ?
        """, (vehicle_id,))
        
        vehicle = cursor.fetchone()
        conn.close()
        
        if not vehicle:
            return jsonify({'error': f'Vehicle not found with ID: {vehicle_id}'})
        
        # Convert to dict
        vehicle_dict = {key: vehicle[key] for key in vehicle.keys()}
        
        return jsonify(vehicle_dict)
    
    except Exception as e:
        logger.error(f"Error getting vehicle details: {e}")
        return jsonify({'error': str(e)})

@app.route('/api/sync', methods=['POST'])
def api_sync():
    """API endpoint to manually sync data from GA4"""
    try:
        sync_time = sync_ga4_data()
        return jsonify({
            'success': True,
            'sync_time': sync_time,
            'message': 'Successfully synchronized data from GA4'
        })
    except Exception as e:
        logger.error(f"Error syncing data from GA4: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/reminders/create', methods=['GET', 'POST'])
def create_reminder():
    """Create a new MOT reminder"""
    if request.method == 'POST':
        vehicle_id = request.form.get('vehicle_id')
        reminder_date = request.form.get('reminder_date')
        reminder_type = request.form.get('reminder_type')
        notes = request.form.get('notes')
        
        if not vehicle_id or not reminder_date or not reminder_type:
            flash('Please fill in all required fields', 'danger')
            return redirect(url_for('create_reminder'))
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Insert reminder
            cursor.execute("""
            INSERT INTO mot_reminders (vehicle_id, reminder_date, reminder_type, notes, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            """, (vehicle_id, reminder_date, reminder_type, notes))
            
            conn.commit()
            
            flash('Reminder created successfully', 'success')
            return redirect(url_for('reminders'))
        except Exception as e:
            logger.error(f"Error creating reminder: {e}")
            flash('Error creating reminder', 'danger')
            return redirect(url_for('create_reminder'))
    
    # GET request - display form
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Count total vehicles in database
        cursor.execute("SELECT COUNT(*) FROM vehicles")
        total_vehicles = cursor.fetchone()[0]
        logger.info(f"Total vehicles in database: {total_vehicles}")
        
        # Get all vehicles with customer information
        cursor.execute("""
        SELECT v.id, v.registration, v.make, v.model, v.mot_expiry, c.name as customer_name
        FROM vehicles v
        LEFT JOIN customers c ON v.customer_id = c.id
        ORDER BY v.registration
        """)
        
        vehicles = cursor.fetchall()
        logger.info(f"Retrieved {len(vehicles)} vehicles for reminder creation")
        
        # Get reminder types
        cursor.execute("SELECT id, name FROM reminder_types ORDER BY name")
        reminder_types = cursor.fetchall()
        
        conn.close()
        
        # Format vehicle options for display
        vehicle_options = []
        for vehicle in vehicles:
            vehicle_id, registration, make, model, mot_expiry, customer_name = vehicle
            
            # Format MOT expiry date if available
            mot_display = ""
            if mot_expiry:
                try:
                    # Try different date formats
                    for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y']:
                        try:
                            mot_date = datetime.strptime(mot_expiry, fmt)
                            mot_display = f" (MOT: {mot_date.strftime('%d/%m/%Y')})"
                            break
                        except ValueError:
                            continue
                except:
                    mot_display = f" (MOT: {mot_expiry})"
            
            # Format customer name if available
            customer_display = f" - {customer_name}" if customer_name else ""
            
            # Format make and model
            vehicle_make_model = ""
            if make and model:
                vehicle_make_model = f"{make} {model}"
            elif make:
                vehicle_make_model = make
            elif model:
                vehicle_make_model = model
            
            # Create display text
            display_text = f"{registration} - {vehicle_make_model}{mot_display}{customer_display}"
            
            vehicle_options.append((vehicle_id, display_text))
        
        # Sort vehicle options by registration
        vehicle_options.sort(key=lambda x: x[1])
        
        return render_template('create_reminder.html', 
                              vehicles=vehicle_options, 
                              reminder_types=reminder_types,
                              total_vehicles=total_vehicles)
    except Exception as e:
        logger.error(f"Error loading create reminder form: {e}")
        flash('Error loading form', 'danger')
        return redirect(url_for('index'))

@app.route('/reminders/send', methods=['POST'])
def send_reminders():
    """Send pending reminders"""
    count = send_mot_reminders()
    return jsonify({'success': True, 'count': count})

@app.route('/vehicles/add_service/<int:vehicle_id>', methods=['POST'])
def add_service(vehicle_id):
    """Add a service record for a vehicle"""
    try:
        # Get form data
        service_date = request.form.get('service_date')
        service_type = request.form.get('service_type')
        mileage = request.form.get('mileage')
        description = request.form.get('description')
        cost = request.form.get('cost')
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if service_records table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='service_records'")
        if not cursor.fetchone():
            # Create service_records table if it doesn't exist
            cursor.execute("""
            CREATE TABLE service_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER,
                service_date TEXT,
                service_type TEXT,
                mileage INTEGER,
                description TEXT,
                cost REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
            )
            """)
        
        # Insert service record
        cursor.execute("""
        INSERT INTO service_records (vehicle_id, service_date, service_type, mileage, description, cost)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (vehicle_id, service_date, service_type, mileage, description, cost))
        
        # Update last_service date in vehicles table
        cursor.execute("""
        UPDATE vehicles SET last_service = ? WHERE id = ?
        """, (service_date, vehicle_id))
        
        conn.commit()
        conn.close()
        
        flash('Service record added successfully', 'success')
        return redirect(url_for('vehicle_detail', vehicle_id=vehicle_id))
    
    except Exception as e:
        logger.error(f"Error adding service record: {e}")
        flash(f'Error adding service record: {e}', 'danger')
        return redirect(url_for('vehicle_detail', vehicle_id=vehicle_id))

@app.route('/vehicles/add_mot/<int:vehicle_id>', methods=['POST'])
def add_mot(vehicle_id):
    """Add an MOT record for a vehicle"""
    try:
        # Get form data
        test_date = request.form.get('test_date')
        result = request.form.get('result')
        expiry_date = request.form.get('expiry_date')
        mileage = request.form.get('mileage')
        advisory_notes = request.form.get('advisory_notes')
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if mot_history table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mot_history'")
        if not cursor.fetchone():
            # Create mot_history table if it doesn't exist
            cursor.execute("""
            CREATE TABLE mot_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER,
                test_date TEXT,
                result TEXT,
                expiry_date TEXT,
                mileage INTEGER,
                advisory_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
            )
            """)
        
        # Insert MOT record
        cursor.execute("""
        INSERT INTO mot_history (vehicle_id, test_date, result, expiry_date, mileage, advisory_notes)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (vehicle_id, test_date, result, expiry_date, mileage, advisory_notes))
        
        # Update mot_expiry date in vehicles table if this is a pass result
        if result == 'Pass' and expiry_date:
            cursor.execute("""
            UPDATE vehicles SET mot_expiry = ? WHERE id = ?
            """, (expiry_date, vehicle_id))
        
        conn.commit()
        conn.close()
        
        flash('MOT record added successfully', 'success')
        return redirect(url_for('vehicle_detail', vehicle_id=vehicle_id))
    
    except Exception as e:
        logger.error(f"Error adding MOT record: {e}")
        flash(f'Error adding MOT record: {e}', 'danger')
        return redirect(url_for('vehicle_detail', vehicle_id=vehicle_id))

@app.route('/api/check_mot_status')
def api_check_mot_status():
    """API endpoint to check MOT status for all vehicles"""
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all vehicles with MOT expiry dates
        cursor.execute("""
        SELECT id, registration, make, model, mot_expiry
        FROM vehicles
        WHERE mot_expiry IS NOT NULL
        """)
        
        vehicles = cursor.fetchall()
        
        # Current date
        current_date = datetime.now().strftime('%Y-%m-%d')
        expiring_soon_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Check MOT status for each vehicle
        results = {
            'total': len(vehicles),
            'valid': 0,
            'expiring_soon': 0,
            'expired': 0,
            'vehicles': []
        }
        
        for vehicle in vehicles:
            v = dict(vehicle)
            
            try:
                mot_date = datetime.strptime(v['mot_expiry'], '%Y-%m-%d')
                days_until_expiry = (mot_date - datetime.now()).days
                
                if days_until_expiry < 0:
                    v['status'] = 'expired'
                    v['days'] = abs(days_until_expiry)
                    results['expired'] += 1
                elif days_until_expiry <= 30:
                    v['status'] = 'expiring_soon'
                    v['days'] = days_until_expiry
                    results['expiring_soon'] += 1
                else:
                    v['status'] = 'valid'
                    v['days'] = days_until_expiry
                    results['valid'] += 1
                
                results['vehicles'].append(v)
            except:
                # Skip vehicles with invalid date format
                continue
        
        conn.close()
        
        return jsonify(results)
    
    except Exception as e:
        logger.error(f"Error checking MOT status: {e}")
        return jsonify({"error": str(e)})

def get_vehicles_due_for_mot(days=30):
    """Get vehicles with MOT expiring within the specified number of days"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Current date
        current_date = datetime.now().strftime('%Y-%m-%d')
        future_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Get vehicles with MOT expiring soon
        cursor.execute("""
        SELECT v.id, v.registration, v.make, v.model, v.mot_expiry, c.name as customer_name, c.id as customer_id
        FROM vehicles v
        LEFT JOIN customers c ON v.customer_id = c.id
        WHERE v.mot_expiry BETWEEN ? AND ?
        ORDER BY v.mot_expiry
        LIMIT 10
        """, (current_date, future_date))
        
        vehicles = []
        for row in cursor.fetchall():
            vehicle = dict(row)
            
            # Calculate days until expiry
            try:
                mot_date = datetime.strptime(vehicle['mot_expiry'], '%Y-%m-%d')
                days_until = (mot_date - datetime.now()).days
                vehicle['days_until'] = days_until
            except:
                vehicle['days_until'] = None
            
            vehicles.append(vehicle)
        
        conn.close()
        
        return vehicles
    
    except Exception as e:
        logger.error(f"Error getting vehicles due for MOT: {e}")
        return []

def get_recent_reminders(limit=5):
    """Get recent MOT reminders"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT r.id, r.vehicle_id, r.reminder_type, r.status, r.created_at, r.sent_at,
               v.registration, v.make, v.model, v.mot_expiry, c.name as customer_name
        FROM mot_reminders r
        JOIN vehicles v ON r.vehicle_id = v.id
        LEFT JOIN customers c ON v.customer_id = c.id
        ORDER BY r.created_at DESC
        LIMIT ?
        """, (limit,))
        
        reminders = []
        for row in cursor.fetchall():
            reminders.append(dict(row))
        
        conn.close()
        
        return reminders
    
    except Exception as e:
        logger.error(f"Error getting recent reminders: {e}")
        return []

def get_upcoming_appointments(days=7):
    """Get upcoming appointments within the specified number of days"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Current date
        current_date = datetime.now().strftime('%Y-%m-%d')
        future_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
        
        cursor.execute("""
        SELECT a.id, a.vehicle_id, a.appointment_date, a.appointment_time, a.appointment_type, a.status,
               v.registration, v.make, v.model, c.name as customer_name
        FROM appointments a
        JOIN vehicles v ON a.vehicle_id = v.id
        LEFT JOIN customers c ON v.customer_id = c.id
        WHERE a.appointment_date BETWEEN ? AND ?
        ORDER BY a.appointment_date, a.appointment_time
        LIMIT 10
        """, (current_date, future_date))
        
        appointments = []
        for row in cursor.fetchall():
            appointments.append(dict(row))
        
        conn.close()
        
        return appointments
    
    except Exception as e:
        logger.error(f"Error getting upcoming appointments: {e}")
        return []

# Function to create necessary database tables if they don't exist
def create_tables():
    """Create necessary database tables if they don't exist"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check and create service_records table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='service_records'")
        if not cursor.fetchone():
            cursor.execute("""
            CREATE TABLE service_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER,
                service_date TEXT,
                service_type TEXT,
                mileage INTEGER,
                description TEXT,
                cost REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
            )
            """)
            logger.info("Created service_records table")
        
        # Check and create mot_history table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mot_history'")
        if not cursor.fetchone():
            cursor.execute("""
            CREATE TABLE mot_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER,
                test_date TEXT,
                result TEXT,
                expiry_date TEXT,
                mileage INTEGER,
                advisory_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
            )
            """)
            logger.info("Created mot_history table")
        
        conn.commit()
        conn.close()
    
    except Exception as e:
        logger.error(f"Error creating tables: {e}")

# Call create_tables function when the application starts
create_tables()

@app.route('/create_appointment', methods=['GET', 'POST'])
def create_appointment():
    """Create an appointment for a vehicle"""
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if appointments table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='appointments'")
        if not cursor.fetchone():
            # Create appointments table if it doesn't exist
            cursor.execute("""
            CREATE TABLE appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER,
                appointment_date TEXT,
                appointment_time TEXT,
                appointment_type TEXT,
                duration INTEGER,
                notes TEXT,
                status TEXT DEFAULT 'Scheduled',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
            )
            """)
            logger.info("Created appointments table")
        
        if request.method == 'POST':
            # Get form data
            vehicle_id = request.form.get('vehicle_id')
            appointment_date = request.form.get('appointment_date')
            appointment_time = request.form.get('appointment_time')
            appointment_type = request.form.get('appointment_type')
            duration = request.form.get('duration')
            notes = request.form.get('notes')
            
            # Insert appointment
            cursor.execute("""
            INSERT INTO appointments (vehicle_id, appointment_date, appointment_time, appointment_type, duration, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (vehicle_id, appointment_date, appointment_time, appointment_type, duration, notes))
            
            conn.commit()
            
            flash('Appointment created successfully', 'success')
            
            # Redirect to vehicle detail if vehicle_id is provided
            if vehicle_id:
                return redirect(url_for('vehicle_detail', vehicle_id=vehicle_id))
            else:
                return redirect(url_for('appointments'))
        
        # GET request - show appointment form
        # Get all vehicles for dropdown
        cursor.execute("""
        SELECT v.id, v.registration, v.make, v.model, v.mot_expiry, c.name as customer_name
        FROM vehicles v
        LEFT JOIN customers c ON v.customer_id = c.id
        ORDER BY v.registration
        """)
        vehicles = cursor.fetchall()
        
        # Get vehicle_id from query parameter if provided
        vehicle_id = request.args.get('vehicle_id')
        selected_vehicle = None
        
        if vehicle_id:
            cursor.execute("""
            SELECT v.*, c.name as customer_name
            FROM vehicles v
            LEFT JOIN customers c ON v.customer_id = c.id
            WHERE v.id = ?
            """, (vehicle_id,))
            selected_vehicle = cursor.fetchone()
        
        conn.close()
        
        # Current date and time for default values
        today = datetime.now().strftime('%Y-%m-%d')
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        current_time = datetime.now().strftime('%H:%M')
        
        return render_template('create_appointment.html', 
                              vehicles=vehicles, 
                              selected_vehicle=selected_vehicle,
                              today=today,
                              tomorrow=tomorrow,
                              current_time=current_time)
    
    except Exception as e:
        logger.error(f"Error creating appointment: {e}")
        flash(f'Error creating appointment: {e}', 'danger')
        return redirect(url_for('index'))

@app.route('/appointments')
def appointments():
    """Display all appointments"""
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get filter parameters
        status = request.args.get('status')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Base query
        query = """
        SELECT a.*, v.registration, v.make, v.model, c.name as customer_name
        FROM appointments a
        JOIN vehicles v ON a.vehicle_id = v.id
        LEFT JOIN customers c ON v.customer_id = c.id
        WHERE 1=1
        """
        params = []
        
        # Add filters
        if status:
            query += " AND a.status = ?"
            params.append(status)
        
        if date_from:
            query += " AND a.appointment_date >= ?"
            params.append(date_from)
        
        if date_to:
            query += " AND a.appointment_date <= ?"
            params.append(date_to)
        
        # Add order by
        query += " ORDER BY a.appointment_date, a.appointment_time"
        
        # Execute query
        cursor.execute(query, params)
        appointments = cursor.fetchall()
        
        # Get appointment counts by status
        cursor.execute("""
        SELECT status, COUNT(*) as count
        FROM appointments
        GROUP BY status
        """)
        status_counts = {}
        for row in cursor.fetchall():
            status_counts[row['status']] = row['count']
        
        # Get today's appointments
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("""
        SELECT a.*, v.registration, v.make, v.model, c.name as customer_name
        FROM appointments a
        JOIN vehicles v ON a.vehicle_id = v.id
        LEFT JOIN customers c ON v.customer_id = c.id
        WHERE a.appointment_date = ?
        ORDER BY a.appointment_time
        """, (today,))
        todays_appointments = cursor.fetchall()
        
        # Get upcoming appointments (next 7 days)
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        next_week = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        cursor.execute("""
        SELECT a.*, v.registration, v.make, v.model, c.name as customer_name
        FROM appointments a
        JOIN vehicles v ON a.vehicle_id = v.id
        LEFT JOIN customers c ON v.customer_id = c.id
        WHERE a.appointment_date BETWEEN ? AND ?
        ORDER BY a.appointment_date, a.appointment_time
        """, (tomorrow, next_week))
        upcoming_appointments = cursor.fetchall()
        
        conn.close()
        
        return render_template('appointments.html', 
                              appointments=appointments,
                              todays_appointments=todays_appointments,
                              upcoming_appointments=upcoming_appointments,
                              status_counts=status_counts,
                              status=status,
                              date_from=date_from,
                              date_to=date_to)
    
    except Exception as e:
        logger.error(f"Error displaying appointments: {e}")
        flash(f'Error displaying appointments: {e}', 'danger')
        return redirect(url_for('index'))

@app.route('/vehicles/verify_mot/<int:vehicle_id>', methods=['GET', 'POST'])
def verify_vehicle_mot_route(vehicle_id):
    """Verify MOT status for a vehicle using DVLA API"""
    try:
        if not DVLA_AVAILABLE:
            flash('DVLA verification is not available', 'warning')
            return redirect(url_for('vehicle_detail', vehicle_id=vehicle_id))
        
        # Verify MOT status and update vehicle
        result = verify_single_vehicle_and_update(db_path, vehicle_id)
        
        if result['success']:
            flash(f"MOT verification successful: {result['mot_status']}", 'success')
        else:
            flash(f"MOT verification failed: {result['message']}", 'danger')
        
        return redirect(url_for('vehicle_detail', vehicle_id=vehicle_id))
    
    except Exception as e:
        logger.error(f"Error verifying MOT: {e}")
        flash(f'Error verifying MOT: {e}', 'danger')
        return redirect(url_for('vehicle_detail', vehicle_id=vehicle_id))

@app.route('/vehicles/batch_verify_mot', methods=['GET'])
def batch_verify_mot_route():
    """Verify MOT status for multiple vehicles"""
    try:
        if not DVLA_AVAILABLE:
            flash('DVLA verification is not available', 'warning')
            return redirect(url_for('vehicles'))
        
        # Get batch size from query parameter, default to 10
        batch_size = request.args.get('batch_size', 10, type=int)
        
        # Verify MOT status for vehicles
        verified, updated = batch_verify_vehicles(db_path, batch_size)
        
        flash(f"Verified {verified} vehicles, updated {updated}", 'success')
        return redirect(url_for('vehicles'))
    
    except Exception as e:
        logger.error(f"Error batch verifying MOT: {e}")
        flash(f'Error batch verifying MOT: {e}', 'danger')
        return redirect(url_for('vehicles'))

@app.route('/api/verify_mot/<registration>', methods=['GET'])
def api_verify_mot(registration):
    """API endpoint to verify MOT status for a vehicle"""
    try:
        if not DVLA_AVAILABLE:
            return jsonify({
                'success': False,
                'message': 'DVLA verification is not available',
                'mot_status': 'Verification Unavailable'
            })
        
        # Verify MOT status
        result = verify_vehicle_mot(registration)
        
        return jsonify({
            'success': True,
            'result': result
        })
    
    except Exception as e:
        logger.error(f"Error in API verify MOT: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'mot_status': 'Error'
        })

def main():
    """Main function"""
    global config, db_path
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Integrated Garage Management System')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the server on')
    parser.add_argument('--ga4-path', type=str, help='Path to GA4 installation')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--auto-sync-interval', type=int, default=5, help='Auto-sync interval in minutes')
    parser.add_argument('--mot-verify-interval', type=int, default=60, help='MOT verification interval in minutes')
    args = parser.parse_args()
    
    # Load configuration
    load_config()
    
    # Override config with command line arguments
    if args.ga4_path:
        config['ga4_path'] = args.ga4_path
    
    # Initialize database
    init_database()
    
    # Import GA4 data
    import_ga4_data()
    
    # Start auto-sync if enabled
    if args.auto_sync_interval > 0:
        scheduler = BackgroundScheduler()
        scheduler.add_job(import_ga4_data, 'interval', minutes=args.auto_sync_interval)
        scheduler.start()
    
    # Start MOT verification scheduler if DVLA integration is available
    if DVLA_AVAILABLE and args.mot_verify_interval > 0:
        try:
            logger.info(f"Starting MOT verification scheduler with interval {args.mot_verify_interval} minutes")
            schedule_mot_verification(db_path, args.mot_verify_interval)
        except Exception as e:
            logger.error(f"Error starting MOT verification scheduler: {e}")
    
    # Start Flask app
    port = args.port
    debug = args.debug
    
    print(f"Starting Integrated Garage Management System on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)

if __name__ == "__main__":
    main()
