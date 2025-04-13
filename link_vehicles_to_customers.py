#!/usr/bin/env python3
"""
Vehicle-Customer Link Tool

This script links vehicles to customers in the database.
"""

import os
import sys
import sqlite3
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('VehicleCustomerLink')

def link_vehicles_to_customers():
    """Link vehicles to customers in the database"""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'garage_system.db')
    
    if not os.path.exists(db_path):
        logger.error(f"Database not found at {db_path}")
        return
    
    logger.info(f"Connecting to database at {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all customers
    cursor.execute("SELECT id, name FROM customers")
    customers = cursor.fetchall()
    
    if not customers:
        logger.error("No customers found in database")
        conn.close()
        return
    
    logger.info(f"Found {len(customers)} customers")
    
    # Get all vehicles
    cursor.execute("SELECT id, registration, make, model FROM vehicles")
    vehicles = cursor.fetchall()
    
    if not vehicles:
        logger.error("No vehicles found in database")
        conn.close()
        return
    
    logger.info(f"Found {len(vehicles)} vehicles")
    
    # Link vehicles to customers
    vehicles_updated = 0
    
    for i, vehicle in enumerate(vehicles):
        vehicle_id, registration, make, model = vehicle
        
        # Assign to a customer based on index
        customer_id = customers[i % len(customers)][0]
        customer_name = customers[i % len(customers)][1]
        
        cursor.execute("UPDATE vehicles SET customer_id = ? WHERE id = ?", (customer_id, vehicle_id))
        vehicles_updated += 1
        logger.info(f"Linked vehicle {registration} ({make} {model}) to customer {customer_name}")
    
    conn.commit()
    
    # Verify the links
    cursor.execute("""
    SELECT v.registration, v.make, v.model, c.name as customer_name
    FROM vehicles v
    JOIN customers c ON v.customer_id = c.id
    """)
    linked_vehicles = cursor.fetchall()
    
    logger.info(f"Successfully linked {len(linked_vehicles)} vehicles to customers")
    logger.info("Sample of linked vehicles:")
    for i, vehicle in enumerate(linked_vehicles):
        if i < 10:  # Show only first 10
            logger.info(f"  {vehicle[0]} ({vehicle[1]} {vehicle[2]}) -> {vehicle[3]}")
    
    conn.close()
    logger.info("Vehicle-Customer linking completed")

if __name__ == "__main__":
    logger.info("Starting Vehicle-Customer Link Tool")
    link_vehicles_to_customers()
    logger.info("Vehicle-Customer Link Tool completed")
