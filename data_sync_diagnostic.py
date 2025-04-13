#!/usr/bin/env python3
"""
GA4 Data Sync Diagnostic Tool

This script checks the GA4 data synchronization process and diagnoses any issues.
"""

import os
import sys
import sqlite3
import csv
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('DataSyncDiagnostic')

def find_ga4_installation():
    """Find GA4 installation directory"""
    # Common installation paths
    common_paths = [
        r"C:\Program Files\Garage Assistant GA4",
        r"C:\Program Files (x86)\Garage Assistant GA4",
        r"C:\Garage Assistant GA4",
        r"D:\Garage Assistant GA4"
    ]
    
    # Check common paths
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    # Check if environment variable is set
    ga4_path = os.environ.get('GA4_PATH')
    if ga4_path and os.path.exists(ga4_path):
        return ga4_path
    
    return None

def check_database():
    """Check the database for vehicles and customers"""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'garage_system.db')
    
    if not os.path.exists(db_path):
        logger.error(f"Database not found at {db_path}")
        return
    
    logger.info(f"Checking database at {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check vehicles table
    cursor.execute("SELECT COUNT(*) FROM vehicles")
    vehicle_count = cursor.fetchone()[0]
    logger.info(f"Found {vehicle_count} vehicles in database")
    
    # Check customers table
    cursor.execute("SELECT COUNT(*) FROM customers")
    customer_count = cursor.fetchone()[0]
    logger.info(f"Found {customer_count} customers in database")
    
    # Check if there are any non-sample vehicles
    cursor.execute("SELECT registration FROM vehicles WHERE registration NOT LIKE 'AB%' AND registration NOT LIKE 'CD%' AND registration NOT LIKE 'EF%' AND registration NOT LIKE 'GH%' AND registration NOT LIKE 'IJ%' AND registration NOT LIKE 'KL%' AND registration NOT LIKE 'MN%' AND registration NOT LIKE 'OP%' AND registration NOT LIKE 'QR%' AND registration NOT LIKE 'ST%' AND registration NOT LIKE 'UV%' AND registration NOT LIKE 'WX%' AND registration NOT LIKE 'YZ%' AND registration NOT LIKE 'AC%' AND registration NOT LIKE 'DF%'")
    non_sample_vehicles = cursor.fetchall()
    logger.info(f"Found {len(non_sample_vehicles)} non-sample vehicles")
    
    # Get sample of vehicles
    cursor.execute("SELECT id, registration, make, model, customer_id FROM vehicles LIMIT 10")
    vehicles = cursor.fetchall()
    logger.info("Sample vehicles:")
    for vehicle in vehicles:
        logger.info(f"  ID: {vehicle[0]}, Reg: {vehicle[1]}, Make: {vehicle[2]}, Model: {vehicle[3]}, Customer ID: {vehicle[4]}")
    
    # Get sample of customers
    cursor.execute("SELECT id, name, email, phone FROM customers LIMIT 10")
    customers = cursor.fetchall()
    logger.info("Sample customers:")
    for customer in customers:
        logger.info(f"  ID: {customer[0]}, Name: {customer[1]}, Email: {customer[2]}, Phone: {customer[3]}")
    
    conn.close()

def check_ga4_files():
    """Check GA4 files for available data"""
    ga4_path = find_ga4_installation()
    
    if not ga4_path:
        logger.error("GA4 installation not found")
        return
    
    logger.info(f"Checking GA4 installation at {ga4_path}")
    
    # Find GA4 data files
    ga4_files = []
    csv_files = []
    
    # Look for GA4 data files and CSV exports
    for root, dirs, files in os.walk(ga4_path):
        for file in files:
            file_path = os.path.join(root, file)
            if file.endswith('.GA4'):
                ga4_files.append(file_path)
            elif file.endswith('.csv'):
                csv_files.append(file_path)
    
    logger.info(f"Found {len(ga4_files)} GA4 data files")
    for file in ga4_files:
        logger.info(f"  {file}")
    
    logger.info(f"Found {len(csv_files)} CSV export files")
    for file in csv_files:
        logger.info(f"  {file}")
        
        # Check CSV content
        try:
            with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)
                headers = next(reader, [])
                logger.info(f"    Headers: {headers}")
                
                # Count rows
                row_count = sum(1 for _ in reader)
                logger.info(f"    Rows: {row_count}")
                
            # Reset and check first few rows
            with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)
                headers = next(reader, [])
                
                # Check first 3 rows
                logger.info(f"    Sample data:")
                for i, row in enumerate(reader):
                    if i >= 3:
                        break
                    logger.info(f"      Row {i+1}: {row}")
        except Exception as e:
            logger.error(f"    Error reading CSV file: {e}")

def check_config():
    """Check configuration settings"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'garage_system_config.json')
    
    if not os.path.exists(config_path):
        logger.error(f"Configuration file not found at {config_path}")
        return
    
    logger.info(f"Checking configuration at {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        logger.info(f"Configuration: {json.dumps(config, indent=2)}")
        
        # Check GA4 path
        ga4_path = config.get('ga4_path')
        if ga4_path:
            logger.info(f"GA4 path in config: {ga4_path}")
            if os.path.exists(ga4_path):
                logger.info(f"GA4 path exists")
            else:
                logger.error(f"GA4 path does not exist")
        else:
            logger.warning(f"GA4 path not set in config")
    
    except Exception as e:
        logger.error(f"Error reading configuration: {e}")

def main():
    """Main function"""
    logger.info("Starting GA4 Data Sync Diagnostic")
    
    # Check configuration
    check_config()
    
    # Check GA4 files
    check_ga4_files()
    
    # Check database
    check_database()
    
    logger.info("GA4 Data Sync Diagnostic completed")

if __name__ == "__main__":
    main()
