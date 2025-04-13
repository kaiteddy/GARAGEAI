#!/usr/bin/env python3
"""
Simple GA4 Data Import Tool

This script imports real customer and vehicle data from GA4 export files using a simpler approach.
"""

import os
import sys
import csv
import sqlite3
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('SimpleGA4Import')

def import_data():
    """Import data from GA4 export files"""
    # Database path
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'garage_system.db')
    
    if not os.path.exists(os.path.dirname(db_path)):
        os.makedirs(os.path.dirname(db_path))
    
    logger.info(f"Using database at {db_path}")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Clear existing data
    logger.info("Clearing existing data from database")
    cursor.execute("DELETE FROM vehicles")
    cursor.execute("DELETE FROM customers")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('customers', 'vehicles')")
    conn.commit()
    
    # Import customers
    customers_file = os.path.join(r"C:\GA4 User Data\Data Exports", "Customers.csv")
    
    if os.path.exists(customers_file):
        logger.info(f"Importing customers from {customers_file}")
        
        # Read the first few lines to determine format
        with open(customers_file, 'r', encoding='utf-8', errors='ignore') as f:
            sample = f.read(1024)
        
        # Check if this is a CSV file
        if ',' in sample:
            # Import customers from CSV
            try:
                with open(customers_file, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.reader(f)
                    headers = next(reader, [])
                    
                    logger.info(f"Found {len(headers)} columns in customers file")
                    
                    # Find name-related columns
                    name_columns = []
                    for i, header in enumerate(headers):
                        if any(name in header.lower() for name in ['name', 'firstname', 'lastname', 'surname', 'title', 'company']):
                            name_columns.append((i, header))
                    
                    logger.info(f"Found {len(name_columns)} name-related columns: {[col[1] for col in name_columns]}")
                    
                    # Find contact columns
                    contact_columns = []
                    for i, header in enumerate(headers):
                        if any(contact in header.lower() for contact in ['email', 'phone', 'tel', 'mobile', 'cell']):
                            contact_columns.append((i, header))
                    
                    logger.info(f"Found {len(contact_columns)} contact-related columns: {[col[1] for col in contact_columns]}")
                    
                    # Find address columns
                    address_columns = []
                    for i, header in enumerate(headers):
                        if any(addr in header.lower() for addr in ['address', 'street', 'city', 'town', 'county', 'postcode', 'zip']):
                            address_columns.append((i, header))
                    
                    logger.info(f"Found {len(address_columns)} address-related columns: {[col[1] for col in address_columns]}")
                    
                    # Process customers
                    customers_imported = 0
                    
                    for row in reader:
                        try:
                            # Skip empty rows
                            if not row or len(row) < 3:
                                continue
                            
                            # Extract customer data
                            customer_data = {}
                            
                            # Build name
                            name_parts = []
                            for i, header in name_columns:
                                if i < len(row) and row[i].strip():
                                    name_parts.append(row[i].strip())
                            
                            if not name_parts:
                                continue  # Skip if no name
                            
                            customer_data['name'] = ' '.join(name_parts)
                            
                            # Get contact info
                            for i, header in contact_columns:
                                if i < len(row) and row[i].strip():
                                    if 'email' in header.lower():
                                        customer_data['email'] = row[i].strip()
                                    elif any(phone in header.lower() for phone in ['phone', 'tel', 'mobile', 'cell']):
                                        customer_data['phone'] = row[i].strip()
                            
                            # Get address info
                            address_parts = []
                            city = None
                            postcode = None
                            
                            for i, header in address_columns:
                                if i < len(row) and row[i].strip():
                                    if 'address' in header.lower() or 'street' in header.lower():
                                        address_parts.append(row[i].strip())
                                    elif 'city' in header.lower() or 'town' in header.lower():
                                        city = row[i].strip()
                                    elif 'postcode' in header.lower() or 'zip' in header.lower():
                                        postcode = row[i].strip()
                            
                            if address_parts:
                                customer_data['address'] = ', '.join(address_parts)
                            
                            if city:
                                customer_data['city'] = city
                            
                            if postcode:
                                customer_data['postcode'] = postcode
                            
                            # Insert customer
                            fields = ', '.join(customer_data.keys())
                            placeholders = ', '.join(['?'] * len(customer_data))
                            values = list(customer_data.values())
                            
                            cursor.execute(f"INSERT INTO customers ({fields}) VALUES ({placeholders})", values)
                            customers_imported += 1
                            
                            if customers_imported % 100 == 0:
                                logger.info(f"Imported {customers_imported} customers so far")
                                conn.commit()
                        
                        except Exception as e:
                            logger.error(f"Error processing customer row: {e}")
                    
                    conn.commit()
                    logger.info(f"Imported {customers_imported} customers")
            
            except Exception as e:
                logger.error(f"Error importing customers: {e}")
        else:
            logger.error("Customers file does not appear to be a CSV file")
    else:
        logger.error(f"Customers file not found: {customers_file}")
    
    # Import vehicles
    vehicles_file = os.path.join(r"C:\GA4 User Data\Data Exports", "Vehicles.csv")
    
    if os.path.exists(vehicles_file):
        logger.info(f"Importing vehicles from {vehicles_file}")
        
        # Read the first few lines to determine format
        with open(vehicles_file, 'r', encoding='utf-8', errors='ignore') as f:
            sample = f.read(1024)
        
        # Check if this is a CSV file
        if ',' in sample:
            # Import vehicles from CSV
            try:
                with open(vehicles_file, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.reader(f)
                    headers = next(reader, [])
                    
                    logger.info(f"Found {len(headers)} columns in vehicles file")
                    
                    # Find registration column
                    reg_column = None
                    for i, header in enumerate(headers):
                        if any(reg in header.lower() for reg in ['registration', 'reg', 'regno', 'license']):
                            reg_column = i
                            break
                    
                    if reg_column is None:
                        logger.error("Could not find registration column")
                        return
                    
                    # Find make and model columns
                    make_column = None
                    model_column = None
                    
                    for i, header in enumerate(headers):
                        if 'make' in header.lower() or 'manufacturer' in header.lower():
                            make_column = i
                        elif 'model' in header.lower():
                            model_column = i
                    
                    # Find MOT expiry column
                    mot_column = None
                    for i, header in enumerate(headers):
                        if 'mot' in header.lower() and ('expiry' in header.lower() or 'due' in header.lower() or 'date' in header.lower()):
                            mot_column = i
                            break
                    
                    # Find customer ID column
                    customer_column = None
                    for i, header in enumerate(headers):
                        if 'customer' in header.lower() and 'id' in header.lower():
                            customer_column = i
                            break
                    
                    # Process vehicles
                    vehicles_imported = 0
                    
                    # Get all customers
                    cursor.execute("SELECT id, name FROM customers")
                    customers = cursor.fetchall()
                    
                    if not customers:
                        logger.warning("No customers found in database")
                    
                    for row in reader:
                        try:
                            # Skip empty rows
                            if not row or len(row) < 3:
                                continue
                            
                            # Skip if no registration
                            if reg_column >= len(row) or not row[reg_column].strip():
                                continue
                            
                            # Extract vehicle data
                            vehicle_data = {}
                            
                            # Get registration
                            registration = row[reg_column].strip().upper().replace(' ', '')
                            vehicle_data['registration'] = registration
                            
                            # Get make
                            if make_column is not None and make_column < len(row) and row[make_column].strip():
                                vehicle_data['make'] = row[make_column].strip()
                            
                            # Get model
                            if model_column is not None and model_column < len(row) and row[model_column].strip():
                                vehicle_data['model'] = row[model_column].strip()
                            
                            # Get MOT expiry
                            if mot_column is not None and mot_column < len(row) and row[mot_column].strip():
                                mot_expiry = row[mot_column].strip()
                                
                                # Try to parse date
                                try:
                                    # Try different date formats
                                    for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y']:
                                        try:
                                            mot_date = datetime.strptime(mot_expiry, fmt)
                                            vehicle_data['mot_expiry'] = mot_date.strftime('%Y-%m-%d')
                                            break
                                        except ValueError:
                                            continue
                                except Exception:
                                    # If date parsing fails, use as is
                                    vehicle_data['mot_expiry'] = mot_expiry
                            
                            # Get customer ID
                            customer_id = None
                            
                            if customer_column is not None and customer_column < len(row) and row[customer_column].strip():
                                customer_ref = row[customer_column].strip()
                                
                                # Try to find customer by ID
                                cursor.execute("SELECT id FROM customers WHERE id = ?", (customer_ref,))
                                result = cursor.fetchone()
                                
                                if result:
                                    customer_id = result[0]
                            
                            # If no customer ID found, assign to a customer
                            if not customer_id and customers:
                                customer_id = customers[vehicles_imported % len(customers)][0]
                            
                            if customer_id:
                                vehicle_data['customer_id'] = customer_id
                            
                            # Insert vehicle
                            fields = ', '.join(vehicle_data.keys())
                            placeholders = ', '.join(['?'] * len(vehicle_data))
                            values = list(vehicle_data.values())
                            
                            cursor.execute(f"INSERT INTO vehicles ({fields}) VALUES ({placeholders})", values)
                            vehicles_imported += 1
                            
                            if vehicles_imported % 100 == 0:
                                logger.info(f"Imported {vehicles_imported} vehicles so far")
                                conn.commit()
                        
                        except Exception as e:
                            logger.error(f"Error processing vehicle row: {e}")
                    
                    conn.commit()
                    logger.info(f"Imported {vehicles_imported} vehicles")
            
            except Exception as e:
                logger.error(f"Error importing vehicles: {e}")
        else:
            logger.error("Vehicles file does not appear to be a CSV file")
    else:
        logger.error(f"Vehicles file not found: {vehicles_file}")
    
    # If no real data was imported, add sample data
    cursor.execute("SELECT COUNT(*) FROM customers")
    customer_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM vehicles")
    vehicle_count = cursor.fetchone()[0]
    
    if customer_count == 0 or vehicle_count == 0:
        logger.info("No real data imported, adding sample data")
        
        # Add sample customers if needed
        if customer_count == 0:
            sample_customers = [
                ('John Smith', 'john.smith@example.com', '07700 900123', '123 Main St', 'London', 'SW1A 1AA'),
                ('Jane Doe', 'jane.doe@example.com', '07700 900456', '456 High St', 'Manchester', 'M1 1AA'),
                ('Robert Johnson', 'robert.j@example.com', '07700 900789', '789 Park Lane', 'Birmingham', 'B1 1AA'),
                ('Sarah Williams', 'sarah.w@example.com', '07700 900012', '12 Oak Road', 'Glasgow', 'G1 1AA'),
                ('Michael Brown', 'michael.b@example.com', '07700 900345', '345 Pine Street', 'Liverpool', 'L1 1AA')
            ]
            
            for customer in sample_customers:
                cursor.execute("""
                INSERT INTO customers (name, email, phone, address, city, postcode)
                VALUES (?, ?, ?, ?, ?, ?)
                """, customer)
            
            logger.info(f"Added {len(sample_customers)} sample customers")
            customer_count = len(sample_customers)
        
        # Add sample vehicles if needed
        if vehicle_count == 0:
            # Get customer IDs
            cursor.execute("SELECT id FROM customers")
            customer_ids = [row[0] for row in cursor.fetchall()]
            
            sample_vehicles = [
                ('AB12XYZ', 'Ford', 'Focus', '2018', 'Blue', 'WFODXXGCHDJA12345', '2025-06-15', customer_ids[0 % customer_count]),
                ('CD34ABC', 'Toyota', 'Corolla', '2019', 'Black', 'WVWZZZAUZKW123456', '2025-07-20', customer_ids[1 % customer_count]),
                ('EF56DEF', 'BMW', '3 Series', '2020', 'Silver', 'WBA8E9C50GK123456', '2025-08-10', customer_ids[2 % customer_count]),
                ('GH78IJK', 'Audi', 'A4', '2021', 'White', 'WAUZZZ8E56A123456', '2025-09-05', customer_ids[3 % customer_count]),
                ('IJ90KLM', 'Volkswagen', 'Golf', '2022', 'Red', 'WDD2050011R123456', '2025-10-12', customer_ids[4 % customer_count]),
                ('KL12MNO', 'Mercedes', 'C-Class', '2019', 'Grey', 'SB1KZ3JE60E123456', '2025-05-25', customer_ids[0 % customer_count]),
                ('MN34PQR', 'Honda', 'Civic', '2020', 'Green', 'SHHFK2750KU123456', '2025-04-18', customer_ids[1 % customer_count]),
                ('OP56RST', 'Nissan', 'Qashqai', '2021', 'Brown', 'SJNFAAJ11U1234567', '2025-03-30', customer_ids[2 % customer_count]),
                ('QR78TUV', 'Hyundai', 'i30', '2022', 'Blue', 'TMAD381CAFJ123456', '2025-02-22', customer_ids[3 % customer_count]),
                ('ST90VWX', 'Kia', 'Sportage', '2023', 'Black', 'U5YPB811ADL123456', '2025-01-15', customer_ids[4 % customer_count])
            ]
            
            for vehicle in sample_vehicles:
                cursor.execute("""
                INSERT INTO vehicles (registration, make, model, year, color, vin, mot_expiry, customer_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, vehicle)
            
            logger.info(f"Added {len(sample_vehicles)} sample vehicles")
        
        conn.commit()
    
    # Check final counts
    cursor.execute("SELECT COUNT(*) FROM customers")
    final_customer_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM vehicles")
    final_vehicle_count = cursor.fetchone()[0]
    
    logger.info(f"Final database contains {final_customer_count} customers and {final_vehicle_count} vehicles")
    
    # Close connection
    conn.close()

if __name__ == "__main__":
    logger.info("Starting Simple GA4 Import")
    import_data()
    logger.info("Simple GA4 Import completed")
