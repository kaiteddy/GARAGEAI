#!/usr/bin/env python3
"""
Fix Customer Data Script

This script updates customer data in the database with sample names and information.
"""

import os
import sqlite3
import random
from datetime import datetime

# Sample data for generating customer information
first_names = [
    "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles",
    "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica", "Sarah", "Karen"
]

last_names = [
    "Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor",
    "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin", "Thompson", "Garcia", "Martinez", "Robinson"
]

email_domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"]
street_names = ["Main St", "Oak Ave", "Maple Rd", "Cedar Ln", "Pine Dr", "Elm St", "Washington Ave", "Park Rd"]
cities = ["London", "Manchester", "Birmingham", "Liverpool", "Leeds", "Glasgow", "Edinburgh", "Bristol"]
postcodes = ["AB1 2CD", "EF3 4GH", "IJ5 6KL", "MN7 8OP", "QR9 0ST", "UV1 2WX", "YZ3 4AB", "CD5 6EF"]

def generate_customer_data():
    """Generate random customer data"""
    first_name = random.choice(first_names)
    last_name = random.choice(last_names)
    name = f"{first_name} {last_name}"

    email = f"{first_name.lower()}.{last_name.lower()}@{random.choice(email_domains)}"
    phone = f"07{random.randint(100, 999)} {random.randint(100, 999)} {random.randint(100, 999)}"

    house_number = random.randint(1, 100)
    street = random.choice(street_names)
    city = random.choice(cities)
    postcode = random.choice(postcodes)
    address = f"{house_number} {street}, {city}, {postcode}"

    return name, email, phone, address

def main():
    """Main function to update customer data"""
    # Database path
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'garage_system.db')

    # Also update the database in the database directory
    db_path2 = os.path.join(os.path.dirname(__file__), 'database', 'garage_system.db')

    # Function to update customers in a database
    def update_customers_in_db(db_path):
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get all customers
        cursor.execute("SELECT id FROM customers")
        customers = cursor.fetchall()

        print(f"Updating {len(customers)} customer records in {db_path}...")

        # Update each customer with random data
        for customer in customers:
            name, email, phone, address = generate_customer_data()

            # Check if updated_at column exists
            cursor.execute("PRAGMA table_info(customers)")
            columns = [row['name'] for row in cursor.fetchall()]

            if 'updated_at' in columns:
                cursor.execute("""
                UPDATE customers
                SET name = ?, email = ?, phone = ?, address = ?, updated_at = ?
                WHERE id = ?
                """, (
                    name, email, phone, address,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    customer['id']
                ))
            else:
                cursor.execute("""
                UPDATE customers
                SET name = ?, email = ?, phone = ?, address = ?
                WHERE id = ?
                """, (
                    name, email, phone, address,
                    customer['id']
                ))

        # Commit changes
        conn.commit()
        conn.close()

        return len(customers)

    # Update customers in both databases
    count1 = update_customers_in_db(db_path)
    count2 = update_customers_in_db(db_path2)

    print("Customer data updated successfully!")

if __name__ == "__main__":
    main()
