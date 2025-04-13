#!/usr/bin/env python3
"""
Fix Vehicle Links Script

This script links vehicles to customers directly in the database.
"""

import os
import sqlite3
import random
from datetime import datetime

def main():
    """Main function to link vehicles to customers"""
    # Database paths
    db_path1 = os.path.join(os.path.dirname(__file__), 'data', 'garage_system.db')
    db_path2 = os.path.join(os.path.dirname(__file__), 'database', 'garage_system.db')

    # Function to link vehicles to customers in a database
    def link_vehicles_in_db(db_path):
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get all vehicles
        cursor.execute("SELECT id FROM vehicles")
        vehicles = cursor.fetchall()

        # Get all customer IDs
        cursor.execute("SELECT id FROM customers")
        customer_ids = [row['id'] for row in cursor.fetchall()]

        if not customer_ids:
            print(f"No customers found in the database: {db_path}!")
            return 0

        print(f"Linking {len(vehicles)} vehicles to customers in {db_path}...")

        # Link each vehicle to a random customer
        for vehicle in vehicles:
            customer_id = random.choice(customer_ids)

            cursor.execute("""
            UPDATE vehicles
            SET customer_id = ?
            WHERE id = ?
            """, (
                customer_id,
                vehicle['id']
            ))

        # Commit changes
        conn.commit()
        conn.close()

        return len(vehicles)

    # Link vehicles in both databases
    count1 = link_vehicles_in_db(db_path1)
    count2 = link_vehicles_in_db(db_path2)

    print(f"Vehicles linked to customers successfully! ({count1} in data, {count2} in database)")

if __name__ == "__main__":
    main()
