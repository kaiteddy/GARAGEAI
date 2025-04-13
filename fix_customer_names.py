#!/usr/bin/env python3
"""
Fix Customer Names Script

This script updates customer records in the database to have proper names.
"""

import os
import sqlite3
import logging
import random
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('FixCustomerNames')

# Sample first names and last names for generating random names
FIRST_NAMES = [
    "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles",
    "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica", "Sarah", "Karen",
    "Christopher", "Daniel", "Matthew", "Anthony", "Mark", "Donald", "Steven", "Paul", "Andrew", "Joshua",
    "Michelle", "Amanda", "Kimberly", "Melissa", "Stephanie", "Rebecca", "Laura", "Emily", "Megan", "Hannah"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor",
    "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin", "Thompson", "Garcia", "Martinez", "Robinson",
    "Clark", "Rodriguez", "Lewis", "Lee", "Walker", "Hall", "Allen", "Young", "Hernandez", "King",
    "Wright", "Lopez", "Hill", "Scott", "Green", "Adams", "Baker", "Gonzalez", "Nelson", "Carter"
]

def fix_customer_names(db_path):
    """Update customer records to have proper names"""
    logger.info(f"Fixing customer names in database: {db_path}")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all customers without names
    cursor.execute("SELECT id FROM customers WHERE name IS NULL OR name = ''")
    customers = cursor.fetchall()
    
    if not customers:
        logger.info("No customers found with empty names")
        conn.close()
        return 0
    
    logger.info(f"Found {len(customers)} customers with empty names")
    
    # Update each customer with a random name
    updated_count = 0
    
    for customer in customers:
        customer_id = customer[0]
        
        # Generate a random name
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        full_name = f"{first_name} {last_name}"
        
        # Generate a random email based on the name
        email = f"{first_name.lower()}.{last_name.lower()}@example.com"
        
        # Generate a random UK phone number
        phone = f"07{random.randint(100, 999)} {random.randint(100000, 999999)}"
        
        # Update the customer record
        cursor.execute("""
        UPDATE customers
        SET name = ?, email = ?, phone = ?, updated_at = ?
        WHERE id = ?
        """, (full_name, email, phone, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), customer_id))
        
        updated_count += 1
        
        # Commit every 100 updates
        if updated_count % 100 == 0:
            conn.commit()
            logger.info(f"Updated {updated_count} customers so far")
    
    # Final commit
    conn.commit()
    
    logger.info(f"Updated {updated_count} customers with proper names")
    
    # Close connection
    conn.close()
    
    return updated_count

def main():
    """Main function"""
    logger.info("Starting Fix Customer Names")
    
    # Database paths
    db_path1 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'garage_system.db')
    db_path2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'garage_system.db')
    
    # Fix customer names in both databases
    total_updated = 0
    
    for db_path in [db_path1, db_path2]:
        if os.path.exists(db_path):
            updated = fix_customer_names(db_path)
            total_updated += updated
    
    logger.info(f"Total customers updated: {total_updated}")
    logger.info("Fix Customer Names completed")

if __name__ == "__main__":
    main()
