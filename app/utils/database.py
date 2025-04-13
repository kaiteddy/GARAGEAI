#!/usr/bin/env python3
"""
Database Utility Module

This module handles database initialization and common database operations.
"""

import os
import sqlite3
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def init_database(db_path: str) -> None:
    """
    Initialize the database.
    
    Args:
        db_path (str): Path to the database file
    """
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
        name TEXT,
        email TEXT,
        phone TEXT,
        address TEXT,
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers (id)
    )
    ''')
    
    # Reminders table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_id INTEGER,
        reminder_date DATE,
        reminder_type TEXT,
        status TEXT DEFAULT 'Pending',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
    )
    ''')
    
    # Appointments table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_id INTEGER,
        appointment_date DATE,
        appointment_time TIME,
        appointment_type TEXT,
        status TEXT DEFAULT 'Scheduled',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
    )
    ''')
    
    # Invoices table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        vehicle_id INTEGER,
        invoice_number TEXT,
        invoice_date DATE,
        due_date DATE,
        total_amount REAL,
        status TEXT DEFAULT 'Unpaid',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers (id),
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
    )
    ''')
    
    # Invoice items table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS invoice_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER,
        description TEXT,
        quantity INTEGER,
        unit_price REAL,
        tax_rate REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (invoice_id) REFERENCES invoices (id)
    )
    ''')
    
    # Documents table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        vehicle_id INTEGER,
        document_type TEXT,
        filename TEXT,
        file_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers (id),
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
    )
    ''')
    
    # Commit changes
    conn.commit()
    conn.close()
    
    logger.info("Database initialized successfully")

def create_tables(db_path: str) -> None:
    """
    Create additional tables that might be needed after initial setup.
    
    Args:
        db_path (str): Path to the database file
    """
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

def get_db_connection(db_path: str) -> sqlite3.Connection:
    """
    Get a database connection with row factory set to sqlite3.Row.
    
    Args:
        db_path (str): Path to the database file
        
    Returns:
        sqlite3.Connection: Database connection
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
