#!/usr/bin/env python3
"""
Database Content Checker

This script checks the contents of the garage system database to verify
that vehicles and customers from GA4 are properly imported and linked.
"""

import os
import sqlite3
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('DatabaseChecker')

def check_database():
    """Check the contents of the database"""
    # Database path
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'garage_system.db')
    
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        return
    
    logger.info(f"Checking database at {db_path}")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    logger.info(f"Found {len(tables)} tables in database:")
    for table in tables:
        logger.info(f"  - {table[0]}")
    
    # Check customers
    try:
        cursor.execute("SELECT COUNT(*) FROM customers")
        customer_count = cursor.fetchone()[0]
        logger.info(f"Found {customer_count} customers in database")
        
        if customer_count > 0:
            # Get sample customers
            cursor.execute("SELECT id, name, email, phone, address, city, postcode FROM customers LIMIT 5")
            customers = cursor.fetchall()
            
            logger.info("Sample customers:")
            for customer in customers:
                logger.info(f"  ID: {customer[0]}, Name: {customer[1]}, Email: {customer[2]}, Phone: {customer[3]}")
                logger.info(f"    Address: {customer[4]}, City: {customer[5]}, Postcode: {customer[6]}")
    except Exception as e:
        logger.error(f"Error checking customers: {e}")
    
    # Check vehicles
    try:
        cursor.execute("SELECT COUNT(*) FROM vehicles")
        vehicle_count = cursor.fetchone()[0]
        logger.info(f"Found {vehicle_count} vehicles in database")
        
        if vehicle_count > 0:
            # Get sample vehicles
            cursor.execute("""
            SELECT v.id, v.registration, v.make, v.model, v.mot_expiry, c.name as customer_name
            FROM vehicles v
            LEFT JOIN customers c ON v.customer_id = c.id
            LIMIT 10
            """)
            vehicles = cursor.fetchall()
            
            logger.info("Sample vehicles:")
            for vehicle in vehicles:
                logger.info(f"  ID: {vehicle[0]}, Reg: {vehicle[1]}, Make/Model: {vehicle[2]} {vehicle[3]}")
                logger.info(f"    MOT Expiry: {vehicle[4]}, Customer: {vehicle[5]}")
    except Exception as e:
        logger.error(f"Error checking vehicles: {e}")
    
    # Check vehicle-customer links
    try:
        cursor.execute("""
        SELECT COUNT(*) FROM vehicles WHERE customer_id IS NOT NULL
        """)
        linked_count = cursor.fetchone()[0]
        
        cursor.execute("""
        SELECT COUNT(*) FROM vehicles WHERE customer_id IS NULL
        """)
        unlinked_count = cursor.fetchone()[0]
        
        logger.info(f"Vehicle-customer links: {linked_count} linked, {unlinked_count} unlinked")
        
        if unlinked_count > 0:
            logger.warning(f"Found {unlinked_count} vehicles with no customer link")
            
            # Get sample unlinked vehicles
            cursor.execute("""
            SELECT id, registration, make, model FROM vehicles WHERE customer_id IS NULL LIMIT 5
            """)
            unlinked = cursor.fetchall()
            
            logger.info("Sample unlinked vehicles:")
            for vehicle in unlinked:
                logger.info(f"  ID: {vehicle[0]}, Reg: {vehicle[1]}, Make/Model: {vehicle[2]} {vehicle[3]}")
    except Exception as e:
        logger.error(f"Error checking vehicle-customer links: {e}")
    
    # Check reminders
    try:
        cursor.execute("SELECT COUNT(*) FROM mot_reminders")
        reminder_count = cursor.fetchone()[0]
        logger.info(f"Found {reminder_count} MOT reminders in database")
        
        if reminder_count > 0:
            # Get sample reminders
            cursor.execute("""
            SELECT r.id, r.vehicle_id, r.reminder_date, r.reminder_type, v.registration
            FROM mot_reminders r
            JOIN vehicles v ON r.vehicle_id = v.id
            LIMIT 5
            """)
            reminders = cursor.fetchall()
            
            logger.info("Sample reminders:")
            for reminder in reminders:
                logger.info(f"  ID: {reminder[0]}, Vehicle ID: {reminder[1]}, Date: {reminder[2]}")
                logger.info(f"    Type: {reminder[3]}, Vehicle Reg: {reminder[4]}")
    except Exception as e:
        logger.error(f"Error checking reminders: {e}")
    
    # Close connection
    conn.close()
    
    logger.info("Database check completed")

if __name__ == "__main__":
    logger.info("Starting database content check")
    check_database()
    logger.info("Database content check completed")
