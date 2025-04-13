#!/usr/bin/env python3
"""
Import Customers from CSV

This script imports customer data from the Customers.csv file in the Data Exports folder.
"""

import os
import csv
import sqlite3
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('ImportCustomersFromCSV')

def clean_value(value):
    """Clean a value from CSV"""
    if value is None:
        return None
    
    # Remove quotes and extra whitespace
    value = value.strip().strip('"\'')
    
    # Return None for empty strings
    if value == '':
        return None
    
    return value

def import_customers(csv_path, db_path):
    """Import customers from CSV file"""
    logger.info(f"Importing customers from {csv_path} to {db_path}")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if we should clear existing data
    cursor.execute("SELECT COUNT(*) FROM customers")
    existing_count = cursor.fetchone()[0]
    
    if existing_count > 0:
        logger.info(f"Found {existing_count} existing customers in database")
        response = input("Do you want to clear existing customer data? (y/n): ")
        
        if response.lower() == 'y':
            logger.info("Clearing existing customer data")
            cursor.execute("DELETE FROM customers")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'customers'")
            conn.commit()
    
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
            
            # Check for required columns
            required_columns = ['_id', 'nameforename', 'namesurname', 'nametitle', 'namecompany']
            missing_columns = [col for col in required_columns if col not in header_map]
            
            if missing_columns:
                logger.error(f"Missing required columns: {missing_columns}")
                return 0
            
            # Process rows
            customers_imported = 0
            
            for row in reader:
                try:
                    # Skip empty rows
                    if not row or len(row) < 5:
                        continue
                    
                    # Extract customer data
                    customer_id = clean_value(row[header_map['_id']])
                    
                    if not customer_id:
                        logger.warning("Skipping row with no customer ID")
                        continue
                    
                    # Build name
                    name_parts = []
                    
                    # Add title if available
                    title = clean_value(row[header_map['nametitle']])
                    if title:
                        name_parts.append(title)
                    
                    # Add forename if available
                    forename = clean_value(row[header_map['nameforename']])
                    if forename:
                        name_parts.append(forename)
                    
                    # Add surname if available
                    surname = clean_value(row[header_map['namesurname']])
                    if surname:
                        name_parts.append(surname)
                    
                    # Use company name if no personal name
                    if not name_parts:
                        company = clean_value(row[header_map['namecompany']])
                        if company:
                            name_parts.append(company)
                    
                    # Skip if no name
                    if not name_parts:
                        logger.warning(f"Skipping customer {customer_id} with no name")
                        continue
                    
                    # Build full name
                    full_name = ' '.join(name_parts)
                    
                    # Get contact info
                    email = None
                    phone = None
                    mobile = None
                    
                    if 'contactemail' in header_map and header_map['contactemail'] < len(row):
                        email = clean_value(row[header_map['contactemail']])
                    
                    if 'contactmobile' in header_map and header_map['contactmobile'] < len(row):
                        mobile = clean_value(row[header_map['contactmobile']])
                    
                    if 'contacttelephone' in header_map and header_map['contacttelephone'] < len(row):
                        phone = clean_value(row[header_map['contacttelephone']])
                    
                    # Use mobile as primary phone if available, otherwise use landline
                    contact_phone = mobile or phone
                    
                    # Build address
                    address_parts = []
                    
                    # Add house number if available
                    if 'addresshouseno' in header_map and header_map['addresshouseno'] < len(row):
                        house_no = clean_value(row[header_map['addresshouseno']])
                        if house_no:
                            address_parts.append(house_no)
                    
                    # Add road if available
                    if 'addressroad' in header_map and header_map['addressroad'] < len(row):
                        road = clean_value(row[header_map['addressroad']])
                        if road:
                            address_parts.append(road)
                    
                    # Add locality if available
                    if 'addresslocality' in header_map and header_map['addresslocality'] < len(row):
                        locality = clean_value(row[header_map['addresslocality']])
                        if locality:
                            address_parts.append(locality)
                    
                    # Add town if available
                    if 'addresstown' in header_map and header_map['addresstown'] < len(row):
                        town = clean_value(row[header_map['addresstown']])
                        if town:
                            address_parts.append(town)
                    
                    # Add county if available
                    if 'addresscounty' in header_map and header_map['addresscounty'] < len(row):
                        county = clean_value(row[header_map['addresscounty']])
                        if county:
                            address_parts.append(county)
                    
                    # Add postcode if available
                    if 'addresspostcode' in header_map and header_map['addresspostcode'] < len(row):
                        postcode = clean_value(row[header_map['addresspostcode']])
                        if postcode:
                            address_parts.append(postcode)
                    
                    # Build full address
                    full_address = ', '.join(address_parts) if address_parts else None
                    
                    # Insert customer
                    cursor.execute("""
                    INSERT INTO customers (id, name, email, phone, address, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        customer_id,
                        full_name,
                        email,
                        contact_phone,
                        full_address,
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ))
                    
                    customers_imported += 1
                    
                    if customers_imported % 100 == 0:
                        logger.info(f"Imported {customers_imported} customers so far")
                        conn.commit()
                
                except Exception as e:
                    logger.error(f"Error processing customer row: {e}")
            
            # Final commit
            conn.commit()
            
            logger.info(f"Imported {customers_imported} customers")
            
            # Close connection
            conn.close()
            
            return customers_imported
    
    except Exception as e:
        logger.error(f"Error importing customers: {e}")
        conn.close()
        return 0

def main():
    """Main function"""
    logger.info("Starting Import Customers from CSV")
    
    # Find CSV file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    csv_path = os.path.join(parent_dir, 'Data Exports', 'Customers.csv')
    
    if not os.path.exists(csv_path):
        logger.error(f"Customers.csv file not found at {csv_path}")
        return
    
    # Database paths
    db_path1 = os.path.join(script_dir, 'data', 'garage_system.db')
    db_path2 = os.path.join(script_dir, 'database', 'garage_system.db')
    
    # Import customers to both databases
    total_imported = 0
    
    for db_path in [db_path1, db_path2]:
        if os.path.exists(db_path):
            logger.info(f"Importing customers to {db_path}")
            imported = import_customers(csv_path, db_path)
            total_imported += imported
    
    logger.info(f"Total customers imported: {total_imported}")
    logger.info("Import Customers from CSV completed")

if __name__ == "__main__":
    main()
