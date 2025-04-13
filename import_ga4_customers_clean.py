#!/usr/bin/env python3
"""
Import GA4 Customers with Data Cleaning

This script imports customer data from the GA4 Customers.csv file into the garage system database.
It includes comprehensive data cleaning and validation to ensure data integrity.
"""

import os
import csv
import re
import sqlite3
import logging
import unicodedata
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('customer_import.log')
    ]
)

logger = logging.getLogger('ImportGA4Customers')

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
    def clean_email(value):
        """Clean and validate email addresses"""
        value = DataCleaner.clean_text(value)
        
        if not value:
            return None
        
        # Extract email from text if it contains other information
        email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', value)
        if email_match:
            value = email_match.group(0)
        
        # Basic email validation
        if not re.match(r'^[\w.+-]+@[\w-]+\.[\w.-]+$', value):
            logger.warning(f"Invalid email format: {value}")
            return None
        
        return value.lower()
    
    @staticmethod
    def clean_phone(value):
        """Clean and format phone numbers"""
        value = DataCleaner.clean_text(value)
        
        if not value:
            return None
        
        # Extract phone number from text if it contains other information
        # Look for sequences of digits, possibly with spaces, dashes, or parentheses
        phone_match = re.search(r'(?:\+\d{1,3})?[\s-]?\(?\d{3,5}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}', value)
        if phone_match:
            value = phone_match.group(0)
        
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', value)
        
        # Format UK phone numbers
        if len(digits_only) >= 10:
            # For UK numbers, keep the last 10 digits
            if len(digits_only) > 10:
                digits_only = digits_only[-10:]
            
            # Format as 07XXX XXXXXX for mobile or 0XXXX XXXXXX for landline
            if digits_only.startswith('7'):
                return f"0{digits_only[0:4]} {digits_only[4:]}"
            else:
                return f"0{digits_only[0:4]} {digits_only[4:]}"
        
        return value
    
    @staticmethod
    def clean_name(value):
        """Clean name values"""
        value = DataCleaner.clean_text(value)
        
        if not value:
            return None
        
        # Capitalize each word
        value = ' '.join(word.capitalize() for word in value.split())
        
        return value
    
    @staticmethod
    def clean_address(value):
        """Clean address values"""
        value = DataCleaner.clean_text(value)
        
        if not value:
            return None
        
        # Capitalize first letter of each word except for common prepositions
        words = value.split()
        prepositions = {'of', 'the', 'in', 'on', 'at', 'by', 'for', 'with', 'to', 'from'}
        
        for i, word in enumerate(words):
            if i > 0 and word.lower() in prepositions:
                words[i] = word.lower()
            else:
                words[i] = word.capitalize()
        
        return ' '.join(words)
    
    @staticmethod
    def clean_postcode(value):
        """Clean and format UK postcodes"""
        value = DataCleaner.clean_text(value)
        
        if not value:
            return None
        
        # Remove all spaces and convert to uppercase
        value = re.sub(r'\s', '', value).upper()
        
        # Basic UK postcode validation
        if not re.match(r'^[A-Z]{1,2}[0-9R][0-9A-Z]?[0-9][ABD-HJLNP-UW-Z]{2}$', value):
            logger.warning(f"Invalid UK postcode format: {value}")
            return value
        
        # Format with a space in the correct position
        if len(value) > 3:
            return f"{value[:-3]} {value[-3:]}"
        
        return value

def import_customers(csv_path, db_path):
    """Import customers from CSV file with data cleaning"""
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
            conn.commit()
    
    # Statistics
    total_rows = 0
    skipped_rows = 0
    error_rows = 0
    imported_rows = 0
    
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
            required_columns = ['_id', 'nameforename', 'namesurname', 'nametitle', 'namecompany']
            missing_columns = [col for col in required_columns if col.lower() not in header_map]
            
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
                    
                    # Extract customer data
                    ga4_id = DataCleaner.clean_text(row[header_map['_id']])
                    
                    if not ga4_id:
                        logger.warning(f"Skipping row {total_rows}: No customer ID")
                        skipped_rows += 1
                        continue
                    
                    # Build name
                    name_parts = []
                    
                    # Add title if available
                    title = DataCleaner.clean_text(row[header_map['nametitle']])
                    if title:
                        name_parts.append(title)
                    
                    # Add forename if available
                    forename = DataCleaner.clean_name(row[header_map['nameforename']])
                    if forename:
                        name_parts.append(forename)
                    
                    # Add surname if available
                    surname = DataCleaner.clean_name(row[header_map['namesurname']])
                    if surname:
                        name_parts.append(surname)
                    
                    # Use company name if no personal name
                    if not name_parts or (len(name_parts) == 1 and title):
                        company = DataCleaner.clean_name(row[header_map['namecompany']])
                        if company:
                            name_parts = [company]
                    
                    # Skip if no name
                    if not name_parts:
                        logger.warning(f"Skipping row {total_rows}: Customer {ga4_id} has no name")
                        skipped_rows += 1
                        continue
                    
                    # Build full name
                    full_name = ' '.join(name_parts)
                    
                    # Get contact info
                    email = None
                    phone = None
                    mobile = None
                    
                    if 'contactemail' in header_map and header_map['contactemail'] < len(row):
                        email = DataCleaner.clean_email(row[header_map['contactemail']])
                    
                    if 'contactmobile' in header_map and header_map['contactmobile'] < len(row):
                        mobile = DataCleaner.clean_phone(row[header_map['contactmobile']])
                    
                    if 'contacttelephone' in header_map and header_map['contacttelephone'] < len(row):
                        phone = DataCleaner.clean_phone(row[header_map['contacttelephone']])
                    
                    # Use mobile as primary phone if available, otherwise use landline
                    contact_phone = mobile or phone
                    
                    # Build address
                    address_parts = []
                    
                    # Add house number if available
                    if 'addresshouseno' in header_map and header_map['addresshouseno'] < len(row):
                        house_no = DataCleaner.clean_text(row[header_map['addresshouseno']])
                        if house_no:
                            address_parts.append(house_no)
                    
                    # Add road if available
                    if 'addressroad' in header_map and header_map['addressroad'] < len(row):
                        road = DataCleaner.clean_address(row[header_map['addressroad']])
                        if road:
                            address_parts.append(road)
                    
                    # Add locality if available
                    if 'addresslocality' in header_map and header_map['addresslocality'] < len(row):
                        locality = DataCleaner.clean_address(row[header_map['addresslocality']])
                        if locality:
                            address_parts.append(locality)
                    
                    # Add town if available
                    if 'addresstown' in header_map and header_map['addresstown'] < len(row):
                        town = DataCleaner.clean_address(row[header_map['addresstown']])
                        if town:
                            address_parts.append(town)
                    
                    # Add county if available
                    if 'addresscounty' in header_map and header_map['addresscounty'] < len(row):
                        county = DataCleaner.clean_address(row[header_map['addresscounty']])
                        if county:
                            address_parts.append(county)
                    
                    # Add postcode if available
                    if 'addresspostcode' in header_map and header_map['addresspostcode'] < len(row):
                        postcode = DataCleaner.clean_postcode(row[header_map['addresspostcode']])
                        if postcode:
                            address_parts.append(postcode)
                    
                    # Build full address
                    full_address = ', '.join(address_parts) if address_parts else None
                    
                    # Insert customer
                    cursor.execute("""
                    INSERT INTO customers (name, email, phone, address, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        full_name,
                        email,
                        contact_phone,
                        full_address,
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ))
                    
                    imported_rows += 1
                    
                    if imported_rows % 100 == 0:
                        logger.info(f"Imported {imported_rows} customers so far")
                        conn.commit()
                
                except Exception as e:
                    logger.error(f"Error processing row {total_rows}: {e}")
                    error_rows += 1
            
            # Final commit
            conn.commit()
            
            # Log statistics
            logger.info(f"Total rows processed: {total_rows}")
            logger.info(f"Rows imported: {imported_rows}")
            logger.info(f"Rows skipped: {skipped_rows}")
            logger.info(f"Rows with errors: {error_rows}")
            
            # Close connection
            conn.close()
            
            return imported_rows
    
    except Exception as e:
        logger.error(f"Error importing customers: {e}")
        conn.close()
        return 0

def main():
    """Main function"""
    logger.info("Starting Import GA4 Customers with Data Cleaning")
    
    # Find CSV file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    csv_path = os.path.join(parent_dir, 'Data Exports', 'Customers.csv')
    
    if not os.path.exists(csv_path):
        logger.error(f"Customers.csv file not found at {csv_path}")
        return
    
    # Database paths
    db_path = os.path.join(script_dir, 'data', 'garage_system.db')
    
    # Import customers
    if os.path.exists(db_path):
        logger.info(f"Importing customers to {db_path}")
        imported = import_customers(csv_path, db_path)
        logger.info(f"Total customers imported: {imported}")
    else:
        logger.error(f"Database file not found at {db_path}")
    
    logger.info("Import GA4 Customers completed")

if __name__ == "__main__":
    main()
