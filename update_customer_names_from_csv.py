#!/usr/bin/env python3
"""
Update Customer Names from CSV

This script updates customer names in the database using the real names from the Customers.csv file.
"""

import os
import csv
import sqlite3
import logging
import unicodedata
import re
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('update_customer_names.log')
    ]
)

logger = logging.getLogger('UpdateCustomerNames')

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

def update_customer_names(csv_path, db_path):
    """Update customer names from CSV file"""
    logger.info(f"Updating customer names from {csv_path} to {db_path}")

    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Create a mapping of customer IDs to database IDs
    cursor.execute("SELECT id FROM customers ORDER BY id")
    db_ids = [row['id'] for row in cursor.fetchall()]

    logger.info(f"Found {len(db_ids)} customers in database")

    # Read CSV file
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
            required_columns = ['nametitle', 'nameforename', 'namesurname', 'namecompany']

            # Convert header names to lowercase for comparison
            lowercase_headers = [h.lower() for h in headers]

            # Check if required columns exist in the CSV file
            missing_columns = []
            for col in required_columns:
                found = False
                for header in lowercase_headers:
                    if col.lower() in header.lower():
                        header_map[col.lower()] = lowercase_headers.index(header)
                        found = True
                        break
                if not found:
                    missing_columns.append(col)

            if missing_columns:
                logger.error(f"Missing required columns: {missing_columns}")
                return 0

            # Process rows
            updated_count = 0
            csv_rows = list(reader)

            logger.info(f"Found {len(csv_rows)} rows in CSV file")

            # Process each row
            for i, row in enumerate(csv_rows):
                try:
                    # Skip if row is too short
                    if len(row) < 5:
                        continue

                    # Get database ID (if available)
                    db_id = None
                    if i < len(db_ids):
                        db_id = db_ids[i]
                    else:
                        logger.warning(f"No database ID for CSV row {i+2}")
                        continue

                    # Build name
                    name_parts = []

                    # Add title if available
                    title_idx = header_map.get('nametitle')
                    if title_idx is not None and title_idx < len(row):
                        title = clean_text(row[title_idx])
                        if title:
                            name_parts.append(title)

                    # Add forename if available
                    forename_idx = header_map.get('nameforename')
                    if forename_idx is not None and forename_idx < len(row):
                        forename = clean_text(row[forename_idx])
                        if forename:
                            name_parts.append(forename)

                    # Add surname if available
                    surname_idx = header_map.get('namesurname')
                    if surname_idx is not None and surname_idx < len(row):
                        surname = clean_text(row[surname_idx])
                        if surname:
                            name_parts.append(surname)

                    # Use company name if no personal name
                    if not name_parts or (len(name_parts) == 1 and title):
                        company_idx = header_map.get('namecompany')
                        if company_idx is not None and company_idx < len(row):
                            company = clean_text(row[company_idx])
                            if company:
                                name_parts = [company]

                    # Skip if no name
                    if not name_parts:
                        logger.warning(f"No name found for CSV row {i+2}")
                        continue

                    # Build full name
                    full_name = ' '.join(name_parts)

                    # Get contact info
                    email = None
                    phone = None

                    # Find email column
                    for header in lowercase_headers:
                        if 'email' in header:
                            email_idx = lowercase_headers.index(header)
                            if email_idx < len(row):
                                email = clean_text(row[email_idx])
                                break

                    # Find phone column (try mobile first, then telephone)
                    for header in lowercase_headers:
                        if 'mobile' in header:
                            phone_idx = lowercase_headers.index(header)
                            if phone_idx < len(row):
                                phone = clean_text(row[phone_idx])
                                break

                    if not phone:
                        for header in lowercase_headers:
                            if 'telephone' in header or 'phone' in header:
                                phone_idx = lowercase_headers.index(header)
                                if phone_idx < len(row):
                                    phone = clean_text(row[phone_idx])
                                    break

                    # Update customer
                    cursor.execute("""
                    UPDATE customers
                    SET name = ?, email = ?, phone = ?, updated_at = ?
                    WHERE id = ?
                    """, (
                        full_name,
                        email,
                        phone,
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        db_id
                    ))

                    updated_count += 1

                    if updated_count % 100 == 0:
                        logger.info(f"Updated {updated_count} customer names so far")
                        conn.commit()

                except Exception as e:
                    logger.error(f"Error processing row {i+2}: {e}")

            # Final commit
            conn.commit()

            logger.info(f"Updated {updated_count} customer names")

            # Close connection
            conn.close()

            return updated_count

    except Exception as e:
        logger.error(f"Error updating customer names: {e}")
        conn.close()
        return 0

def main():
    """Main function"""
    logger.info("Starting Update Customer Names from CSV")

    # Find CSV file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    csv_path = os.path.join(parent_dir, 'Data Exports', 'Customers.csv')

    # Check if the file exists, if not try alternative paths
    if not os.path.exists(csv_path):
        # Try current directory
        csv_path = os.path.join(script_dir, 'Data Exports', 'Customers.csv')

    if not os.path.exists(csv_path):
        # Try one level up from current directory
        csv_path = os.path.join(os.path.dirname(script_dir), 'Data Exports', 'Customers.csv')

    if not os.path.exists(csv_path):
        # Try absolute path
        csv_path = '/Users/adamrutstein/Library/CloudStorage/GoogleDrive-adam@elimotors.co.uk/My Drive/Data Exports/Customers.csv'

    if not os.path.exists(csv_path):
        logger.error(f"Customers.csv file not found at {csv_path}")
        return

    # Database paths
    db_path = os.path.join(script_dir, 'data', 'garage_system.db')

    # Update customer names
    if os.path.exists(db_path):
        logger.info(f"Updating customer names in {db_path}")
        updated = update_customer_names(csv_path, db_path)
        logger.info(f"Total customer names updated: {updated}")
    else:
        logger.error(f"Database file not found at {db_path}")

    logger.info("Update Customer Names from CSV completed")

if __name__ == "__main__":
    main()
