#!/usr/bin/env python3
"""
GA4 Service Module

This module handles interactions with Garage Assistant 4 (GA4), including file watching
and data synchronization.
"""

import os
import csv
import time
import logging
import sqlite3
import threading
import sys
from typing import Dict, Any, List
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from app.utils.database import get_db_connection

logger = logging.getLogger(__name__)

# Increase CSV field size limit to handle large fields in GA4 exports
try:
    csv.field_size_limit(sys.maxsize)
except OverflowError:
    # For platforms where the max value is lower
    csv.field_size_limit(2**27)

class GA4FileHandler(FileSystemEventHandler):
    """
    File system event handler for GA4 export files.
    """

    def __init__(self, app, config, db_path):
        """
        Initialize the handler.

        Args:
            app: Flask application
            config (dict): Configuration dictionary
            db_path (str): Path to the database file
        """
        self.app = app
        self.config = config
        self.db_path = db_path
        self.processed_files = set()

    def on_created(self, event):
        """
        Handle file creation events.

        Args:
            event: File system event
        """
        if event.is_directory:
            return

        file_path = event.src_path

        # Check if this is a CSV file
        if not file_path.lower().endswith('.csv'):
            return

        # Check if we've already processed this file
        if file_path in self.processed_files:
            return

        logger.info(f"New file detected: {file_path}")

        # Process the file
        self.process_ga4_export(file_path)

        # Add to processed files
        self.processed_files.add(file_path)

    def process_ga4_export(self, file_path):
        """
        Process a GA4 export file.

        Args:
            file_path (str): Path to the export file
        """
        try:
            # Determine file type based on filename
            filename = os.path.basename(file_path).lower()

            if 'vehicle' in filename or 'car' in filename:
                self.process_vehicle_export(file_path)
            elif 'customer' in filename or 'client' in filename:
                self.process_customer_export(file_path)
            elif 'invoice' in filename or 'bill' in filename:
                self.process_invoice_export(file_path)
            else:
                logger.warning(f"Unknown export file type: {filename}")

        except Exception as e:
            logger.error(f"Error processing GA4 export file: {e}")

    def process_vehicle_export(self, file_path):
        """
        Process a vehicle export file.

        Args:
            file_path (str): Path to the export file
        """
        try:
            logger.info(f"Processing vehicle export: {file_path}")

            # Connect to database
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()

            # Read CSV file
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                # Process each row
                for row in reader:
                    # Extract vehicle data
                    registration = row.get('Registration', '').strip().upper()

                    if not registration:
                        continue

                    # Check if vehicle already exists
                    cursor.execute("SELECT id FROM vehicles WHERE registration = ?", (registration,))
                    vehicle = cursor.fetchone()

                    # Extract customer data
                    customer_name = row.get('Customer', '').strip()
                    customer_id = None

                    if customer_name:
                        # Check if customer exists
                        cursor.execute("SELECT id FROM customers WHERE name = ?", (customer_name,))
                        customer = cursor.fetchone()

                        if customer:
                            customer_id = customer['id']

                    # Extract vehicle details
                    make = row.get('Make', '').strip()
                    model = row.get('Model', '').strip()
                    year = row.get('Year', '').strip()
                    color = row.get('Colour', '').strip() or row.get('Color', '').strip()
                    vin = row.get('VIN', '').strip() or row.get('Chassis', '').strip()
                    engine_size = row.get('Engine', '').strip() or row.get('CC', '').strip()
                    fuel_type = row.get('Fuel', '').strip()
                    transmission = row.get('Transmission', '').strip()
                    mot_expiry = row.get('MOT Expiry', '').strip() or row.get('MOT Due', '').strip()

                    # Convert year to integer if possible
                    try:
                        year = int(year)
                    except (ValueError, TypeError):
                        year = None

                    # Format MOT expiry date if present
                    if mot_expiry:
                        try:
                            # Try different date formats
                            for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y']:
                                try:
                                    mot_date = datetime.strptime(mot_expiry, fmt)
                                    mot_expiry = mot_date.strftime('%Y-%m-%d')
                                    break
                                except ValueError:
                                    continue
                        except Exception:
                            mot_expiry = None

                    # If vehicle exists, update it
                    if vehicle:
                        cursor.execute("""
                        UPDATE vehicles
                        SET make = ?, model = ?, year = ?, color = ?, vin = ?,
                            engine_size = ?, fuel_type = ?, transmission = ?,
                            mot_expiry = ?, customer_id = ?, updated_at = ?
                        WHERE id = ?
                        """, (
                            make, model, year, color, vin,
                            engine_size, fuel_type, transmission,
                            mot_expiry, customer_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            vehicle['id']
                        ))

                        logger.info(f"Updated vehicle: {registration}")

                    # Otherwise, create a new vehicle
                    else:
                        cursor.execute("""
                        INSERT INTO vehicles (
                            registration, make, model, year, color, vin,
                            engine_size, fuel_type, transmission,
                            mot_expiry, customer_id, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            registration, make, model, year, color, vin,
                            engine_size, fuel_type, transmission,
                            mot_expiry, customer_id,
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        ))

                        logger.info(f"Added new vehicle: {registration}")

            # Commit changes
            conn.commit()
            conn.close()

            logger.info(f"Finished processing vehicle export: {file_path}")

        except Exception as e:
            logger.error(f"Error processing vehicle export: {e}")

    def process_customer_export(self, file_path):
        """
        Process a customer export file.

        Args:
            file_path (str): Path to the export file
        """
        try:
            logger.info(f"Processing customer export: {file_path}")

            # Connect to database
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()

            # Read CSV file
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                # Process each row
                for row in reader:
                    # Extract customer data
                    name = row.get('Name', '').strip()

                    if not name:
                        continue

                    # Extract contact details
                    email = row.get('Email', '').strip()
                    phone = row.get('Phone', '').strip() or row.get('Telephone', '').strip()
                    address = row.get('Address', '').strip()

                    # Check if customer already exists
                    cursor.execute("SELECT id FROM customers WHERE name = ?", (name,))
                    customer = cursor.fetchone()

                    # If customer exists, update it
                    if customer:
                        cursor.execute("""
                        UPDATE customers
                        SET email = ?, phone = ?, address = ?, updated_at = ?
                        WHERE id = ?
                        """, (
                            email, phone, address,
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            customer['id']
                        ))

                        logger.info(f"Updated customer: {name}")

                    # Otherwise, create a new customer
                    else:
                        cursor.execute("""
                        INSERT INTO customers (
                            name, email, phone, address, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            name, email, phone, address,
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        ))

                        logger.info(f"Added new customer: {name}")

            # Commit changes
            conn.commit()
            conn.close()

            logger.info(f"Finished processing customer export: {file_path}")

        except Exception as e:
            logger.error(f"Error processing customer export: {e}")

    def process_invoice_export(self, file_path):
        """
        Process an invoice export file.

        Args:
            file_path (str): Path to the export file
        """
        try:
            logger.info(f"Processing invoice export: {file_path}")

            # Connect to database
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()

            # Read CSV file
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                # Process each row
                for row in reader:
                    # Extract invoice data
                    invoice_number = row.get('Invoice Number', '').strip()

                    if not invoice_number:
                        continue

                    # Extract customer data
                    customer_name = row.get('Customer', '').strip()
                    customer_id = None

                    if customer_name:
                        # Check if customer exists
                        cursor.execute("SELECT id FROM customers WHERE name = ?", (customer_name,))
                        customer = cursor.fetchone()

                        if customer:
                            customer_id = customer['id']

                    # Extract vehicle data
                    registration = row.get('Registration', '').strip().upper()
                    vehicle_id = None

                    if registration:
                        # Check if vehicle exists
                        cursor.execute("SELECT id FROM vehicles WHERE registration = ?", (registration,))
                        vehicle = cursor.fetchone()

                        if vehicle:
                            vehicle_id = vehicle['id']

                    # Extract invoice details
                    invoice_date = row.get('Date', '').strip()
                    due_date = row.get('Due Date', '').strip()
                    total_amount = row.get('Total', '').strip() or row.get('Amount', '').strip()
                    status = row.get('Status', '').strip()
                    notes = row.get('Notes', '').strip()

                    # Format dates if present
                    if invoice_date:
                        try:
                            # Try different date formats
                            for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y']:
                                try:
                                    date_obj = datetime.strptime(invoice_date, fmt)
                                    invoice_date = date_obj.strftime('%Y-%m-%d')
                                    break
                                except ValueError:
                                    continue
                        except Exception:
                            invoice_date = None

                    if due_date:
                        try:
                            # Try different date formats
                            for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y']:
                                try:
                                    date_obj = datetime.strptime(due_date, fmt)
                                    due_date = date_obj.strftime('%Y-%m-%d')
                                    break
                                except ValueError:
                                    continue
                        except Exception:
                            due_date = None

                    # Convert total amount to float if possible
                    try:
                        total_amount = float(total_amount.replace('£', '').replace(',', ''))
                    except (ValueError, TypeError, AttributeError):
                        total_amount = 0.0

                    # Set default status if not provided
                    if not status:
                        status = 'Unpaid'

                    # Check if invoice already exists
                    cursor.execute("SELECT id FROM invoices WHERE invoice_number = ?", (invoice_number,))
                    invoice = cursor.fetchone()

                    # If invoice exists, update it
                    if invoice:
                        cursor.execute("""
                        UPDATE invoices
                        SET customer_id = ?, vehicle_id = ?, invoice_date = ?,
                            due_date = ?, total_amount = ?, status = ?, notes = ?, updated_at = ?
                        WHERE id = ?
                        """, (
                            customer_id, vehicle_id, invoice_date,
                            due_date, total_amount, status, notes,
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            invoice['id']
                        ))

                        logger.info(f"Updated invoice: {invoice_number}")

                    # Otherwise, create a new invoice
                    else:
                        cursor.execute("""
                        INSERT INTO invoices (
                            customer_id, vehicle_id, invoice_number, invoice_date,
                            due_date, total_amount, status, notes, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            customer_id, vehicle_id, invoice_number, invoice_date,
                            due_date, total_amount, status, notes,
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        ))

                        logger.info(f"Added new invoice: {invoice_number}")

            # Commit changes
            conn.commit()
            conn.close()

            logger.info(f"Finished processing invoice export: {file_path}")

        except Exception as e:
            logger.error(f"Error processing invoice export: {e}")

def start_file_watcher(app, config):
    """
    Start the file watcher for GA4 exports.

    Args:
        app: Flask application
        config (dict): Configuration dictionary
    """
    try:
        # Get export directory from config
        export_dir = config.get('ga4_export_dir', '')

        if not export_dir or not os.path.exists(export_dir):
            logger.warning(f"GA4 export directory not found: {export_dir}")
            return

        # Get database path
        db_path = config.get('database_path', '')

        # Create event handler
        event_handler = GA4FileHandler(app, config, db_path)

        # Create observer
        observer = Observer()
        observer.schedule(event_handler, export_dir, recursive=False)

        # Start observer
        observer.start()
        logger.info(f"Started file watcher for GA4 exports: {export_dir}")

        # Store observer in app context for later access
        app.ga4_observer = observer

    except Exception as e:
        logger.error(f"Error starting file watcher: {e}")

def sync_ga4_data(app=None, config=None, db_path=None):
    """
    Synchronize data from GA4.

    Args:
        app: Flask application (optional)
        config (dict): Configuration dictionary (optional)
        db_path (str): Path to the database file (optional)

    Returns:
        dict: Result of the operation
    """
    # Import app if not provided
    from app import app as flask_app
    if app is None:
        app = flask_app

    # Get config if not provided
    if config is None:
        from app.config.config import load_config
        config = load_config()

    # Get db_path if not provided
    if db_path is None:
        db_path = app.config.get('DATABASE_PATH', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'garage_system.db'))
    try:
        # Use the Data Exports folder in Google Drive instead of GA4 installation
        data_exports_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'Data Exports')

        if os.path.exists(data_exports_path):
            # Process CSV files from Data Exports folder
            csv_files = [f for f in os.listdir(data_exports_path) if f.lower().endswith('.csv')]

            if not csv_files:
                return {
                    'success': True,
                    'message': 'No CSV files found in Data Exports folder',
                    'files_processed': 0
                }

            # Process each CSV file
            files_processed = 0

            # Connect to database
            conn = get_db_connection(db_path)
            cursor = conn.cursor()

            for file_name in csv_files:
                try:
                    file_path = os.path.join(data_exports_path, file_name)
                    table_name = os.path.splitext(file_name)[0].lower()

                    # Import data from CSV file
                    try:
                        # Try UTF-8 encoding first
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                            reader = csv.reader(f)
                            headers = next(reader)  # Get column names from first row

                            # Create a more robust table schema
                            # Use a fixed schema for known tables
                            if table_name == 'customers':
                                create_table_sql = '''
                                CREATE TABLE IF NOT EXISTS customers (
                                    id INTEGER PRIMARY KEY,
                                    name TEXT,
                                    email TEXT,
                                    phone TEXT,
                                    address TEXT,
                                    created_at TEXT,
                                    updated_at TEXT,
                                    notes TEXT
                                )
                                '''
                            elif table_name == 'vehicles':
                                create_table_sql = '''
                                CREATE TABLE IF NOT EXISTS vehicles (
                                    id INTEGER PRIMARY KEY,
                                    registration TEXT,
                                    make TEXT,
                                    model TEXT,
                                    year INTEGER,
                                    color TEXT,
                                    vin TEXT,
                                    engine_size TEXT,
                                    fuel_type TEXT,
                                    transmission TEXT,
                                    mot_expiry TEXT,
                                    mot_status TEXT,
                                    last_mot_check TEXT,
                                    customer_id INTEGER,
                                    created_at TEXT,
                                    updated_at TEXT
                                )
                                '''
                            elif table_name == 'appointments':
                                create_table_sql = '''
                                CREATE TABLE IF NOT EXISTS appointments (
                                    id INTEGER PRIMARY KEY,
                                    vehicle_id INTEGER,
                                    appointment_date TEXT,
                                    appointment_time TEXT,
                                    appointment_type TEXT,
                                    status TEXT,
                                    notes TEXT,
                                    created_at TEXT,
                                    updated_at TEXT
                                )
                                '''
                            elif table_name == 'reminders':
                                create_table_sql = '''
                                CREATE TABLE IF NOT EXISTS reminders (
                                    id INTEGER PRIMARY KEY,
                                    vehicle_id INTEGER,
                                    reminder_type TEXT,
                                    due_date TEXT,
                                    status TEXT,
                                    sent_date TEXT,
                                    message TEXT,
                                    created_at TEXT,
                                    updated_at TEXT
                                )
                                '''
                            elif table_name == 'documents':
                                create_table_sql = '''
                                CREATE TABLE IF NOT EXISTS documents (
                                    id INTEGER PRIMARY KEY,
                                    vehicle_id INTEGER,
                                    customer_id INTEGER,
                                    document_type TEXT,
                                    file_name TEXT,
                                    file_path TEXT,
                                    created_at TEXT,
                                    updated_at TEXT
                                )
                                '''
                            else:
                                # For other tables, create a generic schema based on headers
                                columns = [f'"{h.lower().replace(" ", "_")}" TEXT' for h in headers]
                                create_table_sql = f'CREATE TABLE IF NOT EXISTS {table_name} ({", ".join(columns)})'

                            cursor.execute(create_table_sql)

                            # Clear existing data
                            cursor.execute(f'DELETE FROM {table_name}')

                            # For known tables, use specific insert statements
                            if table_name in ['customers', 'vehicles', 'appointments', 'reminders', 'documents']:
                                # Get the column names from the table schema
                                cursor.execute(f"PRAGMA table_info({table_name})")
                                table_columns = [row[1] for row in cursor.fetchall()]

                                # Map CSV headers to table columns
                                column_mapping = {}
                                for i, header in enumerate(headers):
                                    normalized_header = header.lower().replace(' ', '_')

                                    # Special case for customers table
                                    if table_name == 'customers':
                                        if normalized_header == 'customer_name' or normalized_header == 'fullname':
                                            column_mapping[i] = table_columns.index('name')
                                        elif normalized_header == 'customer_email' or normalized_header == 'email_address':
                                            column_mapping[i] = table_columns.index('email')
                                        elif normalized_header == 'customer_phone' or normalized_header == 'telephone' or normalized_header == 'mobile':
                                            column_mapping[i] = table_columns.index('phone')
                                        elif normalized_header == 'customer_address' or normalized_header == 'full_address':
                                            column_mapping[i] = table_columns.index('address')
                                        elif normalized_header in table_columns:
                                            column_mapping[i] = table_columns.index(normalized_header)
                                    # Special case for vehicles table
                                    elif table_name == 'vehicles':
                                        if normalized_header == 'reg' or normalized_header == 'reg_number':
                                            column_mapping[i] = table_columns.index('registration')
                                        elif normalized_header == 'vehicle_make':
                                            column_mapping[i] = table_columns.index('make')
                                        elif normalized_header == 'vehicle_model':
                                            column_mapping[i] = table_columns.index('model')
                                        elif normalized_header == 'vehicle_year' or normalized_header == 'year_of_manufacture':
                                            column_mapping[i] = table_columns.index('year')
                                        elif normalized_header == 'vehicle_color' or normalized_header == 'colour':
                                            column_mapping[i] = table_columns.index('color')
                                        elif normalized_header == 'customer_id' or normalized_header == 'owner_id':
                                            column_mapping[i] = table_columns.index('customer_id')
                                        elif normalized_header in table_columns:
                                            column_mapping[i] = table_columns.index(normalized_header)
                                    else:
                                        if normalized_header in table_columns:
                                            column_mapping[i] = table_columns.index(normalized_header)

                                # Process rows in batches
                                batch_size = 1000
                                batch = []

                                for row in reader:
                                    # Create a row with the correct number of columns
                                    new_row = [None] * len(table_columns)

                                    # Map values from CSV to the correct columns
                                    for i, value in enumerate(row):
                                        if i in column_mapping:
                                            new_row[column_mapping[i]] = value

                                    batch.append(new_row)

                                    if len(batch) >= batch_size:
                                        placeholders = ', '.join(['?'] * len(table_columns))
                                        insert_sql = f'INSERT INTO {table_name} VALUES ({placeholders})'
                                        cursor.executemany(insert_sql, batch)
                                        batch = []

                                # Insert remaining rows
                                if batch:
                                    placeholders = ', '.join(['?'] * len(table_columns))
                                    insert_sql = f'INSERT INTO {table_name} VALUES ({placeholders})'
                                    cursor.executemany(insert_sql, batch)
                            else:
                                # For other tables, use the generic approach
                                placeholders = ', '.join(['?'] * len(headers))
                                insert_sql = f'INSERT INTO {table_name} VALUES ({placeholders})'

                                # Process rows in batches
                                batch_size = 1000
                                batch = []

                                for row in reader:
                                    # Ensure row has the correct number of columns
                                    if len(row) > len(headers):
                                        row = row[:len(headers)]  # Truncate extra columns
                                    elif len(row) < len(headers):
                                        row = row + [None] * (len(headers) - len(row))  # Pad with None

                                    batch.append(row)

                                    if len(batch) >= batch_size:
                                        cursor.executemany(insert_sql, batch)
                                        batch = []

                                # Insert remaining rows
                                if batch:
                                    cursor.executemany(insert_sql, batch)
                    except UnicodeDecodeError:
                        # If UTF-8 fails, try with Latin-1 encoding
                        with open(file_path, 'r', encoding='latin-1') as f:
                            # Repeat the same process as above
                            reader = csv.reader(f)
                            headers = next(reader)  # Get column names from first row

                            # Create a more robust table schema (same as above)
                            if table_name == 'customers':
                                create_table_sql = '''
                                CREATE TABLE IF NOT EXISTS customers (
                                    id INTEGER PRIMARY KEY,
                                    name TEXT,
                                    email TEXT,
                                    phone TEXT,
                                    address TEXT,
                                    created_at TEXT,
                                    updated_at TEXT,
                                    notes TEXT
                                )
                                '''
                            elif table_name == 'vehicles':
                                create_table_sql = '''
                                CREATE TABLE IF NOT EXISTS vehicles (
                                    id INTEGER PRIMARY KEY,
                                    registration TEXT,
                                    make TEXT,
                                    model TEXT,
                                    year INTEGER,
                                    color TEXT,
                                    vin TEXT,
                                    engine_size TEXT,
                                    fuel_type TEXT,
                                    transmission TEXT,
                                    mot_expiry TEXT,
                                    mot_status TEXT,
                                    last_mot_check TEXT,
                                    customer_id INTEGER,
                                    created_at TEXT,
                                    updated_at TEXT
                                )
                                '''
                            elif table_name == 'appointments':
                                create_table_sql = '''
                                CREATE TABLE IF NOT EXISTS appointments (
                                    id INTEGER PRIMARY KEY,
                                    vehicle_id INTEGER,
                                    appointment_date TEXT,
                                    appointment_time TEXT,
                                    appointment_type TEXT,
                                    status TEXT,
                                    notes TEXT,
                                    created_at TEXT,
                                    updated_at TEXT
                                )
                                '''
                            elif table_name == 'reminders':
                                create_table_sql = '''
                                CREATE TABLE IF NOT EXISTS reminders (
                                    id INTEGER PRIMARY KEY,
                                    vehicle_id INTEGER,
                                    reminder_type TEXT,
                                    due_date TEXT,
                                    status TEXT,
                                    sent_date TEXT,
                                    message TEXT,
                                    created_at TEXT,
                                    updated_at TEXT
                                )
                                '''
                            elif table_name == 'documents':
                                create_table_sql = '''
                                CREATE TABLE IF NOT EXISTS documents (
                                    id INTEGER PRIMARY KEY,
                                    vehicle_id INTEGER,
                                    customer_id INTEGER,
                                    document_type TEXT,
                                    file_name TEXT,
                                    file_path TEXT,
                                    created_at TEXT,
                                    updated_at TEXT
                                )
                                '''
                            else:
                                # For other tables, create a generic schema based on headers
                                columns = [f'"{h.lower().replace(" ", "_")}" TEXT' for h in headers]
                                create_table_sql = f'CREATE TABLE IF NOT EXISTS {table_name} ({", ".join(columns)})'

                            cursor.execute(create_table_sql)

                            # Clear existing data
                            cursor.execute(f'DELETE FROM {table_name}')

                            # For known tables, use specific insert statements
                            if table_name in ['customers', 'vehicles', 'appointments', 'reminders', 'documents']:
                                # Get the column names from the table schema
                                cursor.execute(f"PRAGMA table_info({table_name})")
                                table_columns = [row[1] for row in cursor.fetchall()]

                                # Map CSV headers to table columns
                                column_mapping = {}
                                for i, header in enumerate(headers):
                                    normalized_header = header.lower().replace(' ', '_')
                                    if normalized_header in table_columns:
                                        column_mapping[i] = table_columns.index(normalized_header)

                                # Process rows in batches
                                batch_size = 1000
                                batch = []

                                for row in reader:
                                    # Create a row with the correct number of columns
                                    new_row = [None] * len(table_columns)

                                    # Map values from CSV to the correct columns
                                    for i, value in enumerate(row):
                                        if i in column_mapping:
                                            new_row[column_mapping[i]] = value

                                    batch.append(new_row)

                                    if len(batch) >= batch_size:
                                        placeholders = ', '.join(['?'] * len(table_columns))
                                        insert_sql = f'INSERT INTO {table_name} VALUES ({placeholders})'
                                        cursor.executemany(insert_sql, batch)
                                        batch = []

                                # Insert remaining rows
                                if batch:
                                    placeholders = ', '.join(['?'] * len(table_columns))
                                    insert_sql = f'INSERT INTO {table_name} VALUES ({placeholders})'
                                    cursor.executemany(insert_sql, batch)
                            else:
                                # For other tables, use the generic approach
                                placeholders = ', '.join(['?'] * len(headers))
                                insert_sql = f'INSERT INTO {table_name} VALUES ({placeholders})'

                                # Process rows in batches
                                batch_size = 1000
                                batch = []

                                for row in reader:
                                    # Ensure row has the correct number of columns
                                    if len(row) > len(headers):
                                        row = row[:len(headers)]  # Truncate extra columns
                                    elif len(row) < len(headers):
                                        row = row + [None] * (len(headers) - len(row))  # Pad with None

                                    batch.append(row)

                                    if len(batch) >= batch_size:
                                        cursor.executemany(insert_sql, batch)
                                        batch = []

                                # Insert remaining rows
                                if batch:
                                    cursor.executemany(insert_sql, batch)

                    files_processed += 1
                    logger.info(f'Imported {file_name} into {table_name} table')

                except Exception as e:
                    logger.error(f'Error importing {file_name}: {e}')

            # Commit changes and close connection
            conn.commit()
            conn.close()

            # Update last sync time
            app.config['LAST_SYNC_TIME'] = datetime.now()

            return {
                'success': True,
                'message': f'Successfully processed {files_processed} CSV files from Data Exports folder',
                'files_processed': files_processed
            }
        else:
            # Data Exports folder not found
            return {
                'success': False,
                'message': f'Data Exports folder not found at {data_exports_path}'
            }

    except Exception as e:
        logger.error(f"Error synchronizing GA4 data: {e}")
        return {
            'success': False,
            'message': f'Error synchronizing GA4 data: {e}'
        }

def start_auto_sync(app, config, db_path):
    """
    Start automatic synchronization with GA4.

    Args:
        app: Flask application
        config (dict): Configuration dictionary
        db_path (str): Path to the database file
    """
    # Get sync interval from config (minutes)
    interval = config.get('auto_sync_interval', 15)

    # Convert to seconds
    interval_seconds = interval * 60

    # Define sync function
    def sync_loop():
        while True:
            try:
                # Sync data
                result = sync_ga4_data(app, config, db_path)
                logger.info(f"Auto sync result: {result.get('message')}")

                # Sleep for interval
                time.sleep(interval_seconds)

            except Exception as e:
                logger.error(f"Error in auto sync loop: {e}")
                time.sleep(interval_seconds)

    # Start sync thread
    sync_thread = threading.Thread(target=sync_loop, daemon=True)
    sync_thread.start()

    logger.info(f"Started auto sync with interval: {interval} minutes")

    # Store thread in app context for later access
    app.ga4_sync_thread = sync_thread
