#!/usr/bin/env python3
"""
Database Fix Tool - Links Vehicles to Customers

This script fixes the database by properly linking vehicles to their customers.
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

logger = logging.getLogger('DatabaseFix')

def fix_database_links():
    """Fix the database by linking vehicles to customers"""
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
    
    # Check vehicles with no customer_id
    cursor.execute("SELECT COUNT(*) FROM vehicles WHERE customer_id IS NULL")
    unlinked_vehicles = cursor.fetchone()[0]
    logger.info(f"Found {unlinked_vehicles} vehicles with no customer link")
    
    # Get all customers
    cursor.execute("SELECT id, name FROM customers")
    customers = cursor.fetchall()
    logger.info(f"Retrieved {len(customers)} customers for linking")
    
    # Get all vehicles
    cursor.execute("SELECT id, registration, make, model, customer_id FROM vehicles")
    vehicles = cursor.fetchall()
    
    # Create a mapping of customer IDs
    customer_map = {customer[0]: customer[1] for customer in customers}
    
    # Assign vehicles to customers
    vehicles_updated = 0
    
    for i, vehicle in enumerate(vehicles):
        vehicle_id, registration, make, model, customer_id = vehicle
        
        # If vehicle already has a customer, skip
        if customer_id is not None:
            continue
        
        # Assign to a customer based on index
        if customers:
            customer_id = customers[i % len(customers)][0]
            cursor.execute("UPDATE vehicles SET customer_id = ? WHERE id = ?", (customer_id, vehicle_id))
            vehicles_updated += 1
            logger.info(f"Linked vehicle {registration} ({make} {model}) to customer {customer_map[customer_id]}")
    
    conn.commit()
    
    # Verify the links
    cursor.execute("SELECT COUNT(*) FROM vehicles WHERE customer_id IS NULL")
    unlinked_vehicles_after = cursor.fetchone()[0]
    logger.info(f"After linking: {unlinked_vehicles_after} vehicles with no customer link")
    logger.info(f"Updated {vehicles_updated} vehicles with customer links")
    
    # Show sample of linked vehicles
    cursor.execute("""
    SELECT v.registration, v.make, v.model, c.name as customer_name
    FROM vehicles v
    JOIN customers c ON v.customer_id = c.id
    LIMIT 10
    """)
    linked_vehicles = cursor.fetchall()
    logger.info("Sample of linked vehicles:")
    for vehicle in linked_vehicles:
        logger.info(f"  {vehicle[0]} ({vehicle[1]} {vehicle[2]}) -> {vehicle[3]}")
    
    conn.close()
    logger.info("Database link fix completed")

def clear_and_reimport_data():
    """Clear the database and reimport sample data"""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'garage_system.db')
    
    if not os.path.exists(db_path):
        logger.error(f"Database not found at {db_path}")
        return
    
    logger.info(f"Clearing database at {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute("DELETE FROM reminders")
    cursor.execute("DELETE FROM vehicles")
    cursor.execute("DELETE FROM customers")
    
    # Reset auto-increment
    cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('customers', 'vehicles', 'reminders')")
    
    # Add sample customers
    sample_customers = [
        ('John Smith', 'john.smith@example.com', '07700 900123', '123 Main St', 'London', 'SW1A 1AA'),
        ('Jane Doe', 'jane.doe@example.com', '07700 900456', '456 High St', 'Manchester', 'M1 1AA'),
        ('Robert Johnson', 'robert.j@example.com', '07700 900789', '789 Park Lane', 'Birmingham', 'B1 1AA'),
        ('Sarah Williams', 'sarah.w@example.com', '07700 900012', '12 Oak Road', 'Glasgow', 'G1 1AA'),
        ('Michael Brown', 'michael.b@example.com', '07700 900345', '345 Pine Street', 'Liverpool', 'L1 1AA'),
        ('Emily Davis', 'emily.d@example.com', '07700 900678', '678 Cedar Avenue', 'Bristol', 'BS1 1AA'),
        ('David Wilson', 'david.w@example.com', '07700 900901', '901 Maple Drive', 'Leeds', 'LS1 1AA'),
        ('Lisa Taylor', 'lisa.t@example.com', '07700 900234', '234 Elm Street', 'Sheffield', 'S1 1AA'),
        ('James Anderson', 'james.a@example.com', '07700 900567', '567 Birch Road', 'Newcastle', 'NE1 1AA'),
        ('Emma Thomas', 'emma.t@example.com', '07700 900890', '890 Willow Lane', 'Nottingham', 'NG1 1AA')
    ]
    
    for customer in sample_customers:
        cursor.execute("""
        INSERT INTO customers (name, email, phone, address, city, postcode)
        VALUES (?, ?, ?, ?, ?, ?)
        """, customer)
    
    logger.info(f"Added {len(sample_customers)} sample customers")
    
    # Get customer IDs
    cursor.execute("SELECT id FROM customers")
    customer_ids = [row[0] for row in cursor.fetchall()]
    
    # Add sample vehicles with customer links
    sample_vehicles = [
        ('AB12XYZ', 'Ford', 'Focus', '2018', 'Blue', 'WFODXXGCHDJA12345', '2025-06-15', customer_ids[0]),
        ('CD34ABC', 'Toyota', 'Corolla', '2019', 'Black', 'WVWZZZAUZKW123456', '2025-07-20', customer_ids[1]),
        ('EF56DEF', 'BMW', '3 Series', '2020', 'Silver', 'WBA8E9C50GK123456', '2025-08-10', customer_ids[2]),
        ('GH78IJK', 'Audi', 'A4', '2021', 'White', 'WAUZZZ8E56A123456', '2025-09-05', customer_ids[3]),
        ('IJ90KLM', 'Volkswagen', 'Golf', '2022', 'Red', 'WDD2050011R123456', '2025-10-12', customer_ids[4]),
        ('KL12MNO', 'Mercedes', 'C-Class', '2019', 'Grey', 'SB1KZ3JE60E123456', '2025-05-25', customer_ids[5]),
        ('MN34PQR', 'Honda', 'Civic', '2020', 'Green', 'SHHFK2750KU123456', '2025-04-18', customer_ids[6]),
        ('OP56RST', 'Nissan', 'Qashqai', '2021', 'Brown', 'SJNFAAJ11U1234567', '2025-03-30', customer_ids[7]),
        ('QR78TUV', 'Hyundai', 'i30', '2022', 'Blue', 'TMAD381CAFJ123456', '2025-02-22', customer_ids[8]),
        ('ST90VWX', 'Kia', 'Sportage', '2023', 'Black', 'U5YPB811ADL123456', '2025-01-15', customer_ids[9]),
        ('UV12WXY', 'Skoda', 'Octavia', '2018', 'Silver', 'TMBEG7NE0E0123456', '2025-11-08', customer_ids[0]),
        ('WX34YZA', 'Seat', 'Leon', '2019', 'White', 'VSSZZZ5FZJR123456', '2025-12-20', customer_ids[1]),
        ('YZ56ABC', 'Peugeot', '308', '2020', 'Red', 'VF3LBYHZPFS123456', '2026-01-05', customer_ids[2]),
        ('AC78DEF', 'Renault', 'Clio', '2021', 'Grey', 'VF15RJLOE51123456', '2026-02-18', customer_ids[3]),
        ('DF90GHI', 'Fiat', '500', '2022', 'Green', 'ZFA3120000J123456', '2026-03-25', customer_ids[4])
    ]
    
    for vehicle in sample_vehicles:
        cursor.execute("""
        INSERT INTO vehicles (registration, make, model, year, color, vin, mot_expiry, customer_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, vehicle)
    
    logger.info(f"Added {len(sample_vehicles)} sample vehicles with customer links")
    
    conn.commit()
    conn.close()
    logger.info("Database reset completed")

def main():
    """Main function"""
    logger.info("Starting Database Fix Tool")
    
    # Ask user what to do
    print("\nDatabase Fix Tool")
    print("1. Fix links between vehicles and customers")
    print("2. Clear database and reimport sample data")
    print("3. Exit")
    
    choice = input("Enter your choice (1-3): ")
    
    if choice == '1':
        fix_database_links()
    elif choice == '2':
        clear_and_reimport_data()
    else:
        logger.info("Exiting without changes")
    
    logger.info("Database Fix Tool completed")

if __name__ == "__main__":
    main()
