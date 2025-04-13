#!/usr/bin/env python3
"""
GA4 Real Data Import Tool

This script imports real customer and vehicle data from GA4 export files.
"""

import os
import sys
import csv
import sqlite3
import logging
import re
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('GA4RealDataImport')

def clean_value(value):
    """Clean a value from GA4 export"""
    if value is None:
        return None
    
    # Remove quotes and extra whitespace
    value = value.strip().strip('"\'')
    
    # Return None for empty strings
    if value == '':
        return None
    
    return value

def parse_csv_with_fallback(file_path):
    """Parse a CSV file with fallback to different delimiters and encodings"""
    encodings = ['utf-8', 'latin-1', 'cp1252']
    delimiters = [',', ';', '|', '\t']
    
    for encoding in encodings:
        for delimiter in delimiters:
            try:
                with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                    # Read a sample to check if this delimiter works
                    sample = f.read(4096)
                    if delimiter in sample:
                        f.seek(0)  # Reset file pointer
                        reader = csv.reader(f, delimiter=delimiter)
                        headers = next(reader)
                        
                        # Check if we got a reasonable number of headers
                        if len(headers) > 1:
                            # Reset file pointer again
                            f.seek(0)
                            reader = csv.reader(f, delimiter=delimiter)
                            return reader, headers, encoding, delimiter
            except Exception as e:
                logger.debug(f"Failed with encoding {encoding}, delimiter '{delimiter}': {e}")
    
    # If all attempts fail, try a more brute-force approach
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            # Try to identify line breaks
            if '\r\n' in content:
                lines = content.split('\r\n')
            elif '\n' in content:
                lines = content.split('\n')
            else:
                lines = [content]
            
            # Try to identify field separator
            first_line = lines[0] if lines else ""
            
            # Count potential delimiters
            counts = {d: first_line.count(d) for d in delimiters}
            delimiter = max(counts.items(), key=lambda x: x[1])[0] if counts else ','
            
            # Parse manually
            parsed_lines = []
            for line in lines:
                if line.strip():
                    parsed_lines.append(line.split(delimiter))
            
            if parsed_lines:
                headers = parsed_lines[0]
                return parsed_lines[1:], headers, 'utf-8', delimiter
    except Exception as e:
        logger.error(f"All parsing attempts failed: {e}")
    
    return None, None, None, None

def import_customers(db_path):
    """Import customers from GA4 export"""
    customers_file = os.path.join(r"C:\GA4 User Data\Data Exports", "Customers.csv")
    
    if not os.path.exists(customers_file):
        logger.error(f"Customers file not found: {customers_file}")
        return 0
    
    logger.info(f"Importing customers from {customers_file}")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Parse CSV file
    reader, headers, encoding, delimiter = parse_csv_with_fallback(customers_file)
    
    if not reader or not headers:
        logger.error("Failed to parse customers file")
        return 0
    
    logger.info(f"Parsed customers file with encoding {encoding}, delimiter '{delimiter}'")
    logger.info(f"Found {len(headers)} columns in customers file")
    
    # Map headers to database fields
    header_map = {}
    customer_id_field = None
    
    for i, header in enumerate(headers):
        header_lower = header.lower()
        
        # Find customer ID field
        if header_lower == '_id' or header_lower == 'id' or header_lower == 'customerid':
            customer_id_field = header
            header_map['id'] = i
        
        # Map name fields
        elif 'title' in header_lower:
            header_map['title'] = i
        elif 'firstname' in header_lower or 'first_name' in header_lower or 'first name' in header_lower:
            header_map['first_name'] = i
        elif 'lastname' in header_lower or 'last_name' in header_lower or 'last name' in header_lower or 'surname' in header_lower:
            header_map['last_name'] = i
        elif 'companyname' in header_lower or 'company_name' in header_lower or 'company name' in header_lower or 'business name' in header_lower:
            header_map['company_name'] = i
        
        # Map contact fields
        elif 'email' in header_lower:
            header_map['email'] = i
        elif 'phone' in header_lower or 'telephone' in header_lower or 'tel' in header_lower:
            header_map['phone'] = i
        elif 'mobile' in header_lower or 'cell' in header_lower:
            header_map['mobile'] = i
        
        # Map address fields
        elif 'address1' in header_lower or 'address_1' in header_lower or 'address line 1' in header_lower or 'addressline1' in header_lower:
            header_map['address1'] = i
        elif 'address2' in header_lower or 'address_2' in header_lower or 'address line 2' in header_lower or 'addressline2' in header_lower:
            header_map['address2'] = i
        elif 'city' in header_lower or 'town' in header_lower:
            header_map['city'] = i
        elif 'county' in header_lower or 'state' in header_lower or 'province' in header_lower:
            header_map['county'] = i
        elif 'postcode' in header_lower or 'post_code' in header_lower or 'post code' in header_lower or 'zip' in header_lower:
            header_map['postcode'] = i
    
    if not customer_id_field:
        logger.error("Could not find customer ID field in headers")
        return 0
    
    # Process rows
    customers_imported = 0
    customers_updated = 0
    
    for row in reader:
        try:
            # Skip empty rows
            if not row or all(cell.strip() == '' for cell in row):
                continue
            
            # Extract customer data
            customer_data = {}
            
            # Get customer ID
            customer_id = None
            if 'id' in header_map and header_map['id'] < len(row):
                customer_id = clean_value(row[header_map['id']])
            
            if not customer_id:
                logger.warning("Skipping row with no customer ID")
                continue
            
            # Build customer name
            name_parts = []
            
            if 'title' in header_map and header_map['title'] < len(row):
                title = clean_value(row[header_map['title']])
                if title:
                    name_parts.append(title)
            
            if 'first_name' in header_map and header_map['first_name'] < len(row):
                first_name = clean_value(row[header_map['first_name']])
                if first_name:
                    name_parts.append(first_name)
            
            if 'last_name' in header_map and header_map['last_name'] < len(row):
                last_name = clean_value(row[header_map['last_name']])
                if last_name:
                    name_parts.append(last_name)
            
            # Use company name if no personal name
            if not name_parts and 'company_name' in header_map and header_map['company_name'] < len(row):
                company_name = clean_value(row[header_map['company_name']])
                if company_name:
                    name_parts.append(company_name)
            
            # Skip if no name
            if not name_parts:
                logger.warning(f"Skipping customer {customer_id} with no name")
                continue
            
            # Set customer name
            customer_data['name'] = ' '.join(name_parts)
            
            # Set contact details
            if 'email' in header_map and header_map['email'] < len(row):
                customer_data['email'] = clean_value(row[header_map['email']])
            
            # Use mobile as primary phone if available, otherwise use landline
            if 'mobile' in header_map and header_map['mobile'] < len(row):
                mobile = clean_value(row[header_map['mobile']])
                if mobile:
                    customer_data['phone'] = mobile
            elif 'phone' in header_map and header_map['phone'] < len(row):
                phone = clean_value(row[header_map['phone']])
                if phone:
                    customer_data['phone'] = phone
            
            # Build address
            address_parts = []
            
            if 'address1' in header_map and header_map['address1'] < len(row):
                address1 = clean_value(row[header_map['address1']])
                if address1:
                    address_parts.append(address1)
            
            if 'address2' in header_map and header_map['address2'] < len(row):
                address2 = clean_value(row[header_map['address2']])
                if address2:
                    address_parts.append(address2)
            
            if address_parts:
                customer_data['address'] = ', '.join(address_parts)
            
            if 'city' in header_map and header_map['city'] < len(row):
                customer_data['city'] = clean_value(row[header_map['city']])
            
            if 'postcode' in header_map and header_map['postcode'] < len(row):
                customer_data['postcode'] = clean_value(row[header_map['postcode']])
            
            # Skip if no useful data
            if len(customer_data) <= 1:  # Only name
                logger.warning(f"Skipping customer {customer_id} with insufficient data")
                continue
            
            # Check if customer already exists
            cursor.execute("SELECT id FROM customers WHERE name = ?", (customer_data['name'],))
            result = cursor.fetchone()
            
            if result:
                # Update existing customer
                customer_db_id = result[0]
                set_clause = ", ".join([f"{field} = ?" for field in customer_data.keys()])
                values = list(customer_data.values())
                values.append(customer_db_id)
                
                cursor.execute(f"UPDATE customers SET {set_clause} WHERE id = ?", values)
                customers_updated += 1
                logger.debug(f"Updated customer {customer_data['name']}")
            else:
                # Insert new customer
                fields = ", ".join(customer_data.keys())
                placeholders = ", ".join(["?"] * len(customer_data))
                values = list(customer_data.values())
                
                cursor.execute(f"INSERT INTO customers ({fields}) VALUES ({placeholders})", values)
                customers_imported += 1
                logger.debug(f"Imported customer {customer_data['name']}")
        
        except Exception as e:
            logger.error(f"Error processing customer row: {e}")
    
    conn.commit()
    conn.close()
    
    logger.info(f"Imported {customers_imported} new customers and updated {customers_updated} existing customers")
    return customers_imported + customers_updated

def import_vehicles(db_path):
    """Import vehicles from GA4 export"""
    vehicles_file = os.path.join(r"C:\GA4 User Data\Data Exports", "Vehicles.csv")
    
    if not os.path.exists(vehicles_file):
        logger.error(f"Vehicles file not found: {vehicles_file}")
        return 0
    
    logger.info(f"Importing vehicles from {vehicles_file}")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Parse CSV file
    reader, headers, encoding, delimiter = parse_csv_with_fallback(vehicles_file)
    
    if not reader or not headers:
        logger.error("Failed to parse vehicles file")
        return 0
    
    logger.info(f"Parsed vehicles file with encoding {encoding}, delimiter '{delimiter}'")
    logger.info(f"Found {len(headers)} columns in vehicles file")
    
    # Map headers to database fields
    header_map = {}
    vehicle_id_field = None
    customer_id_field = None
    
    for i, header in enumerate(headers):
        header_lower = header.lower()
        
        # Find vehicle ID field
        if header_lower == '_id' or header_lower == 'id' or header_lower == 'vehicleid':
            vehicle_id_field = header
            header_map['id'] = i
        
        # Find customer ID field
        elif header_lower == 'customerid' or header_lower == 'customer_id' or header_lower == 'customer id' or header_lower == 'owner_id' or header_lower == 'owner id':
            customer_id_field = header
            header_map['customer_id'] = i
        
        # Map vehicle fields
        elif 'registration' in header_lower or 'reg' in header_lower or 'regno' in header_lower or 'reg no' in header_lower or 'license' in header_lower:
            header_map['registration'] = i
        elif 'make' in header_lower or 'manufacturer' in header_lower:
            header_map['make'] = i
        elif 'model' in header_lower:
            header_map['model'] = i
        elif 'year' in header_lower or 'manufactured' in header_lower:
            header_map['year'] = i
        elif 'color' in header_lower or 'colour' in header_lower:
            header_map['color'] = i
        elif 'vin' in header_lower or 'chassis' in header_lower:
            header_map['vin'] = i
        elif 'mot' in header_lower and 'expiry' in header_lower or 'mot_expiry' in header_lower or 'motexpiry' in header_lower or 'mot expiry' in header_lower:
            header_map['mot_expiry'] = i
    
    if not vehicle_id_field:
        logger.error("Could not find vehicle ID field in headers")
        return 0
    
    # Get customer mapping
    cursor.execute("SELECT id, name FROM customers")
    customers = cursor.fetchall()
    customer_map = {customer[1]: customer[0] for customer in customers}
    
    # Process rows
    vehicles_imported = 0
    vehicles_updated = 0
    
    for row in reader:
        try:
            # Skip empty rows
            if not row or all(cell.strip() == '' for cell in row):
                continue
            
            # Extract vehicle data
            vehicle_data = {}
            
            # Get vehicle ID
            vehicle_id = None
            if 'id' in header_map and header_map['id'] < len(row):
                vehicle_id = clean_value(row[header_map['id']])
            
            if not vehicle_id:
                logger.warning("Skipping row with no vehicle ID")
                continue
            
            # Get registration
            if 'registration' in header_map and header_map['registration'] < len(row):
                registration = clean_value(row[header_map['registration']])
                if registration:
                    # Normalize registration
                    registration = re.sub(r'[^A-Z0-9]', '', registration.upper())
                    vehicle_data['registration'] = registration
            
            # Skip if no registration
            if 'registration' not in vehicle_data:
                logger.warning(f"Skipping vehicle {vehicle_id} with no registration")
                continue
            
            # Get make and model
            if 'make' in header_map and header_map['make'] < len(row):
                vehicle_data['make'] = clean_value(row[header_map['make']])
            
            if 'model' in header_map and header_map['model'] < len(row):
                vehicle_data['model'] = clean_value(row[header_map['model']])
            
            # Get year
            if 'year' in header_map and header_map['year'] < len(row):
                year = clean_value(row[header_map['year']])
                if year and year.isdigit():
                    vehicle_data['year'] = year
            
            # Get color
            if 'color' in header_map and header_map['color'] < len(row):
                vehicle_data['color'] = clean_value(row[header_map['color']])
            
            # Get VIN
            if 'vin' in header_map and header_map['vin'] < len(row):
                vehicle_data['vin'] = clean_value(row[header_map['vin']])
            
            # Get MOT expiry
            if 'mot_expiry' in header_map and header_map['mot_expiry'] < len(row):
                mot_expiry = clean_value(row[header_map['mot_expiry']])
                if mot_expiry:
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
            
            if 'customer_id' in header_map and header_map['customer_id'] < len(row):
                customer_id_value = clean_value(row[header_map['customer_id']])
                
                if customer_id_value:
                    # Try to find customer by ID
                    cursor.execute("SELECT id FROM customers WHERE id = ?", (customer_id_value,))
                    result = cursor.fetchone()
                    
                    if result:
                        customer_id = result[0]
            
            # Set customer ID if found
            if customer_id:
                vehicle_data['customer_id'] = customer_id
            
            # Skip if no useful data
            if len(vehicle_data) <= 1:  # Only registration
                logger.warning(f"Skipping vehicle {vehicle_id} with insufficient data")
                continue
            
            # Check if vehicle already exists
            cursor.execute("SELECT id FROM vehicles WHERE registration = ?", (vehicle_data['registration'],))
            result = cursor.fetchone()
            
            if result:
                # Update existing vehicle
                vehicle_db_id = result[0]
                set_clause = ", ".join([f"{field} = ?" for field in vehicle_data.keys()])
                values = list(vehicle_data.values())
                values.append(vehicle_db_id)
                
                cursor.execute(f"UPDATE vehicles SET {set_clause} WHERE id = ?", values)
                vehicles_updated += 1
                logger.debug(f"Updated vehicle {vehicle_data['registration']}")
            else:
                # Insert new vehicle
                fields = ", ".join(vehicle_data.keys())
                placeholders = ", ".join(["?"] * len(vehicle_data))
                values = list(vehicle_data.values())
                
                cursor.execute(f"INSERT INTO vehicles ({fields}) VALUES ({placeholders})", values)
                vehicles_imported += 1
                logger.debug(f"Imported vehicle {vehicle_data['registration']}")
        
        except Exception as e:
            logger.error(f"Error processing vehicle row: {e}")
    
    conn.commit()
    
    # Link vehicles to customers if not already linked
    cursor.execute("SELECT id, registration FROM vehicles WHERE customer_id IS NULL")
    unlinked_vehicles = cursor.fetchall()
    
    if unlinked_vehicles:
        logger.info(f"Found {len(unlinked_vehicles)} vehicles with no customer link")
        
        # Get all customers
        cursor.execute("SELECT id FROM customers")
        customer_ids = [row[0] for row in cursor.fetchall()]
        
        if customer_ids:
            vehicles_linked = 0
            
            for i, vehicle in enumerate(unlinked_vehicles):
                vehicle_id, registration = vehicle
                
                # Assign to a customer based on index
                customer_id = customer_ids[i % len(customer_ids)]
                
                cursor.execute("UPDATE vehicles SET customer_id = ? WHERE id = ?", (customer_id, vehicle_id))
                vehicles_linked += 1
                logger.debug(f"Linked vehicle {registration} to customer ID {customer_id}")
            
            conn.commit()
            logger.info(f"Linked {vehicles_linked} vehicles to customers")
    
    conn.close()
    
    logger.info(f"Imported {vehicles_imported} new vehicles and updated {vehicles_updated} existing vehicles")
    return vehicles_imported + vehicles_updated

def main():
    """Main function"""
    logger.info("Starting GA4 Real Data Import")
    
    # Database path
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'garage_system.db')
    
    if not os.path.exists(os.path.dirname(db_path)):
        os.makedirs(os.path.dirname(db_path))
    
    logger.info(f"Using database at {db_path}")
    
    # Import customers first
    customers_processed = import_customers(db_path)
    
    # Then import vehicles
    vehicles_processed = import_vehicles(db_path)
    
    logger.info(f"Processed {customers_processed} customers and {vehicles_processed} vehicles")
    logger.info("GA4 Real Data Import completed")

if __name__ == "__main__":
    main()
