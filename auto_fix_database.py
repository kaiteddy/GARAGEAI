#!/usr/bin/env python3
"""
Auto Database Fix Tool - Links Vehicles to Customers

This script automatically fixes the database by properly linking vehicles to their customers.
"""

import os
import sys
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

logger = logging.getLogger('AutoDatabaseFix')

def clear_and_reimport_data():
    """Clear the database and reimport sample data with proper customer links"""
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
    
    conn.commit()
    conn.close()
    logger.info("Database reset completed successfully")

if __name__ == "__main__":
    logger.info("Starting Auto Database Fix Tool")
    clear_and_reimport_data()
    logger.info("Auto Database Fix Tool completed")
