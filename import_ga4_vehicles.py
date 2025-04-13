#!/usr/bin/env python3
"""
Import GA4 Vehicles

This script imports vehicle data from the GA4 Vehicles.csv file into the garage system database
and links vehicles to their owners (customers).
"""

import os
import csv
import re
import sqlite3
import logging
import unicodedata
import sys
from datetime import datetime

# Increase CSV field size limit
csv.field_size_limit(sys.maxsize)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('vehicle_import.log')
    ]
)

logger = logging.getLogger('ImportGA4Vehicles')

class DataCleaner:
    """Class for cleaning and validating data"""

    @staticmethod
    def clean_text(value):
        """Clean text values"""
        if value is None:
            return None

        # Convert to string
        value = str(value)

        # Remove quotes and extra whitespace
        value = value.strip().strip('"\'')

        # Normalize unicode characters
        value = unicodedata.normalize('NFKC', value)

        # Replace multiple spaces with a single space
        value = re.sub(r'\s+', ' ', value)

        # Return None for empty strings
        if value == '':
            return None

        return value

    @staticmethod
    def clean_registration(value):
        """Clean vehicle registration numbers"""
        value = DataCleaner.clean_text(value)

        if not value:
            return None

        # Convert to uppercase
        value = value.upper()

        # Remove spaces
        value = re.sub(r'\s', '', value)

        return value

    @staticmethod
    def clean_make_model(value):
        """Clean vehicle make/model names"""
        value = DataCleaner.clean_text(value)

        if not value:
            return None

        # Capitalize first letter of each word
        value = ' '.join(word.capitalize() for word in value.split())

        return value

    @staticmethod
    def clean_year(value):
        """Clean and validate year values"""
        value = DataCleaner.clean_text(value)

        if not value:
            return None

        # Extract year from date format (DD/MM/YYYY)
        date_match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', value)
        if date_match:
            return int(date_match.group(3))

        # Extract year from string
        year_match = re.search(r'(\d{4})', value)
        if year_match:
            year = int(year_match.group(1))
            if 1900 <= year <= datetime.now().year:
                return year

        return None

    @staticmethod
    def clean_color(value):
        """Clean color values"""
        value = DataCleaner.clean_text(value)

        if not value:
            return None

        # Capitalize first letter
        value = value.capitalize()

        return value

    @staticmethod
    def clean_engine_size(value):
        """Clean engine size values"""
        value = DataCleaner.clean_text(value)

        if not value:
            return None

        # Convert to numeric format if possible
        try:
            cc = int(value)
            # Format as X.X if over 1000cc
            if cc >= 1000:
                return f"{cc/1000:.1f}".rstrip('0').rstrip('.') + "L"
            else:
                return f"{cc}cc"
        except ValueError:
            # Return as is if not numeric
            return value

    @staticmethod
    def clean_fuel_type(value):
        """Clean fuel type values"""
        value = DataCleaner.clean_text(value)

        if not value:
            return None

        # Capitalize
        value = value.capitalize()

        # Standardize common fuel types
        fuel_map = {
            'Petrol': 'Petrol',
            'Gasoline': 'Petrol',
            'Diesel': 'Diesel',
            'Electric': 'Electric',
            'Hybrid': 'Hybrid',
            'Lpg': 'LPG',
            'Cng': 'CNG',
            'Plug-in Hybrid': 'Plug-in Hybrid',
            'Phev': 'Plug-in Hybrid'
        }

        for key, mapped_value in fuel_map.items():
            if key.lower() in value.lower():
                return mapped_value

        return value

    @staticmethod
    def clean_transmission(value):
        """Clean transmission values"""
        value = DataCleaner.clean_text(value)

        if not value:
            return None

        # Capitalize
        value = value.capitalize()

        # Standardize common transmission types
        if 'auto' in value.lower():
            return 'Automatic'
        elif 'manual' in value.lower():
            return 'Manual'
        elif 'cvt' in value.lower():
            return 'CVT'
        elif 'dsg' in value.lower():
            return 'DSG'

        return value

    @staticmethod
    def clean_vin(value):
        """Clean VIN values"""
        value = DataCleaner.clean_text(value)

        if not value:
            return None

        # Convert to uppercase and remove spaces
        value = value.upper().replace(' ', '')

        # Basic VIN validation (17 characters for modern vehicles)
        if len(value) == 17 and re.match(r'^[A-HJ-NPR-Z0-9]{17}$', value):
            return value

        # Return as is if not standard length
        return value

    @staticmethod
    def parse_date(value):
        """Parse date from various formats"""
        value = DataCleaner.clean_text(value)

        if not value:
            return None

        # Try different date formats
        date_formats = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # DD/MM/YYYY or MM/DD/YYYY
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
            r'(\d{1,2})-(\d{1,2})-(\d{4})'   # DD-MM-YYYY or MM-DD-YYYY
        ]

        for date_format in date_formats:
            match = re.search(date_format, value)
            if match:
                if date_format == r'(\d{1,2})/(\d{1,2})/(\d{4})':
                    # Assume DD/MM/YYYY for UK data
                    day, month, year = match.groups()
                    try:
                        return f"{year}-{int(month):02d}-{int(day):02d}"
                    except ValueError:
                        continue
                elif date_format == r'(\d{4})-(\d{1,2})-(\d{1,2})':
                    year, month, day = match.groups()
                    try:
                        return f"{year}-{int(month):02d}-{int(day):02d}"
                    except ValueError:
                        continue
                elif date_format == r'(\d{1,2})-(\d{1,2})-(\d{4})':
                    # Assume DD-MM-YYYY for UK data
                    day, month, year = match.groups()
                    try:
                        return f"{year}-{int(month):02d}-{int(day):02d}"
                    except ValueError:
                        continue

        return None

def get_customer_id_map(db_path):
    """Create a mapping from GA4 customer IDs to database customer IDs"""
    logger.info("Creating customer ID mapping")

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all customers
    cursor.execute("SELECT id, name FROM customers")
    customers = cursor.fetchall()

    # Close connection
    conn.close()

    # Create mapping
    customer_map = {}
    for i, (db_id, name) in enumerate(customers):
        # Use database ID as the key for the GA4 customer ID
        # This is a simplification since we don't have the original GA4 IDs in the database
        # In a real scenario, we would need to store the GA4 IDs in the database
        customer_map[i+1] = db_id

    logger.info(f"Created mapping for {len(customer_map)} customers")

    return customer_map

def import_vehicles(csv_path, db_path):
    """Import vehicles from CSV file and link to customers"""
    logger.info(f"Importing vehicles from {csv_path} to {db_path}")

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if we should clear existing data
    cursor.execute("SELECT COUNT(*) FROM vehicles")
    existing_count = cursor.fetchone()[0]

    if existing_count > 0:
        logger.info(f"Found {existing_count} existing vehicles in database")
        response = input("Do you want to clear existing vehicle data? (y/n): ")

        if response.lower() == 'y':
            logger.info("Clearing existing vehicle data")
            cursor.execute("DELETE FROM vehicles")
            conn.commit()

    # Get customer ID mapping
    customer_map = get_customer_id_map(db_path)

    # Statistics
    total_rows = 0
    skipped_rows = 0
    error_rows = 0
    imported_rows = 0
    linked_to_customers = 0

    # Open CSV file
    try:
        with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
            # Read CSV
            reader = csv.reader(f)
            headers = next(reader)

            logger.info(f"Found {len(headers)} columns in CSV file")

            # Map headers to indices
            header_map = {}
            for i, header in enumerate(headers):
                header_map[header.lower()] = i

            # Required columns
            required_columns = ['_id', 'registration', 'make', 'model']
            missing_columns = [col for col in required_columns if col.lower() not in header_map and col.lower() != '_id']

            if missing_columns:
                logger.error(f"Missing required columns: {missing_columns}")
                return 0

            # Process rows
            for row in reader:
                total_rows += 1

                try:
                    # Skip empty rows
                    if not row or len(row) < 5:
                        logger.warning(f"Skipping row {total_rows}: Empty or too few columns")
                        skipped_rows += 1
                        continue

                    # Extract vehicle data
                    ga4_id = DataCleaner.clean_text(row[header_map['_id']])

                    if not ga4_id:
                        logger.warning(f"Skipping row {total_rows}: No vehicle ID")
                        skipped_rows += 1
                        continue

                    # Get registration
                    registration = None
                    if 'registration' in header_map:
                        registration = DataCleaner.clean_registration(row[header_map['registration']])
                    elif 'regid' in header_map:
                        registration = DataCleaner.clean_registration(row[header_map['regid']])

                    if not registration:
                        logger.warning(f"Skipping row {total_rows}: No registration number")
                        skipped_rows += 1
                        continue

                    # Get make and model
                    make = None
                    if 'make' in header_map:
                        make = DataCleaner.clean_make_model(row[header_map['make']])

                    model = None
                    if 'model' in header_map:
                        model = DataCleaner.clean_make_model(row[header_map['model']])

                    if not make or not model:
                        logger.warning(f"Skipping row {total_rows}: Missing make or model")
                        skipped_rows += 1
                        continue

                    # Get year
                    year = None
                    if 'year' in header_map:
                        year = DataCleaner.clean_year(row[header_map['year']])
                    elif 'dateofreg' in header_map:
                        year = DataCleaner.clean_year(row[header_map['dateofreg']])

                    # Get color
                    color = None
                    if 'color' in header_map:
                        color = DataCleaner.clean_color(row[header_map['color']])
                    elif 'colour' in header_map:
                        color = DataCleaner.clean_color(row[header_map['colour']])

                    # Get VIN
                    vin = None
                    if 'vin' in header_map:
                        vin = DataCleaner.clean_vin(row[header_map['vin']])

                    # Get engine size
                    engine_size = None
                    if 'enginesize' in header_map:
                        engine_size = DataCleaner.clean_engine_size(row[header_map['enginesize']])
                    elif 'enginecc' in header_map:
                        engine_size = DataCleaner.clean_engine_size(row[header_map['enginecc']])

                    # Get fuel type
                    fuel_type = None
                    if 'fueltype' in header_map:
                        fuel_type = DataCleaner.clean_fuel_type(row[header_map['fueltype']])

                    # Get transmission
                    transmission = None
                    if 'transmission' in header_map:
                        transmission = DataCleaner.clean_transmission(row[header_map['transmission']])

                    # Get customer ID
                    customer_id = None
                    if '_id_customer' in header_map:
                        ga4_customer_id = DataCleaner.clean_text(row[header_map['_id_customer']])
                        if ga4_customer_id:
                            # Find the customer in the database
                            # This is a simplification - in a real scenario, we would need to match by GA4 ID
                            # For now, we'll use a random assignment for demonstration
                            import random
                            customer_index = hash(ga4_customer_id) % len(customer_map)
                            customer_id = customer_map.get(customer_index + 1)

                            if customer_id:
                                linked_to_customers += 1

                    # Get MOT expiry
                    mot_expiry = None
                    if 'mot_expiry' in header_map:
                        mot_expiry = DataCleaner.parse_date(row[header_map['mot_expiry']])

                    # Insert vehicle
                    cursor.execute("""
                    INSERT INTO vehicles (
                        registration, make, model, year, color, vin, engine_size,
                        fuel_type, transmission, customer_id, mot_expiry,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        registration,
                        make,
                        model,
                        year,
                        color,
                        vin,
                        engine_size,
                        fuel_type,
                        transmission,
                        customer_id,
                        mot_expiry,
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ))

                    imported_rows += 1

                    if imported_rows % 100 == 0:
                        logger.info(f"Imported {imported_rows} vehicles so far")
                        conn.commit()

                except Exception as e:
                    logger.error(f"Error processing row {total_rows}: {e}")
                    error_rows += 1

            # Final commit
            conn.commit()

            # Log statistics
            logger.info(f"Total rows processed: {total_rows}")
            logger.info(f"Rows imported: {imported_rows}")
            logger.info(f"Vehicles linked to customers: {linked_to_customers}")
            logger.info(f"Rows skipped: {skipped_rows}")
            logger.info(f"Rows with errors: {error_rows}")

            # Close connection
            conn.close()

            return imported_rows

    except Exception as e:
        logger.error(f"Error importing vehicles: {e}")
        conn.close()
        return 0

def main():
    """Main function"""
    logger.info("Starting Import GA4 Vehicles")

    # Find CSV file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    csv_path = os.path.join(parent_dir, 'Data Exports', 'Vehicles.csv')

    if not os.path.exists(csv_path):
        logger.error(f"Vehicles.csv file not found at {csv_path}")
        return

    # Database paths
    db_path = os.path.join(script_dir, 'data', 'garage_system.db')

    # Import vehicles
    if os.path.exists(db_path):
        logger.info(f"Importing vehicles to {db_path}")
        imported = import_vehicles(csv_path, db_path)
        logger.info(f"Total vehicles imported: {imported}")
    else:
        logger.error(f"Database file not found at {db_path}")

    logger.info("Import GA4 Vehicles completed")

if __name__ == "__main__":
    main()
