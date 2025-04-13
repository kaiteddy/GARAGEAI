#!/usr/bin/env python3
"""
Fix Database Data Script

This script fixes the data in the database directory to match the expected schema.
"""

import os
import sqlite3
import random
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('DatabaseFixer')

def generate_customer_data():
    """Generate random customer data"""
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

def generate_vehicle_data():
    """Generate random vehicle data"""
    makes = [
        "Toyota", "Honda", "Ford", "BMW", "Mercedes", "Audi", "Volkswagen", "Nissan", "Hyundai", "Kia",
        "Mazda", "Subaru", "Volvo", "Jaguar", "Land Rover", "Lexus", "Porsche", "Tesla", "Fiat", "Renault"
    ]
    
    models = {
        "Toyota": ["Corolla", "Camry", "RAV4", "Prius", "Yaris", "Highlander", "Tacoma", "Tundra"],
        "Honda": ["Civic", "Accord", "CR-V", "Pilot", "Fit", "HR-V", "Odyssey", "Ridgeline"],
        "Ford": ["Focus", "Fiesta", "Mustang", "Explorer", "Escape", "F-150", "Ranger", "Edge"],
        "BMW": ["3 Series", "5 Series", "7 Series", "X3", "X5", "X7", "i3", "i8"],
        "Mercedes": ["A-Class", "C-Class", "E-Class", "S-Class", "GLA", "GLC", "GLE", "GLS"],
        "Audi": ["A3", "A4", "A6", "A8", "Q3", "Q5", "Q7", "TT"],
        "Volkswagen": ["Golf", "Polo", "Passat", "Tiguan", "T-Roc", "Touareg", "ID.3", "ID.4"],
        "Nissan": ["Micra", "Juke", "Qashqai", "X-Trail", "Leaf", "Navara", "370Z", "GT-R"],
        "Hyundai": ["i10", "i20", "i30", "Tucson", "Santa Fe", "Kona", "Ioniq", "Veloster"],
        "Kia": ["Picanto", "Rio", "Ceed", "Sportage", "Sorento", "Stonic", "Niro", "Soul"],
        "Mazda": ["2", "3", "6", "CX-3", "CX-5", "CX-9", "MX-5", "RX-8"],
        "Subaru": ["Impreza", "Legacy", "Forester", "Outback", "XV", "WRX", "BRZ", "Ascent"],
        "Volvo": ["S60", "S90", "V60", "V90", "XC40", "XC60", "XC90", "C40"],
        "Jaguar": ["XE", "XF", "XJ", "F-Type", "E-Pace", "F-Pace", "I-Pace", "XK"],
        "Land Rover": ["Defender", "Discovery", "Range Rover", "Range Rover Sport", "Range Rover Evoque", "Range Rover Velar", "Discovery Sport", "Freelander"],
        "Lexus": ["IS", "ES", "LS", "UX", "NX", "RX", "LX", "LC"],
        "Porsche": ["911", "Boxster", "Cayman", "Panamera", "Cayenne", "Macan", "Taycan", "918"],
        "Tesla": ["Model 3", "Model S", "Model X", "Model Y", "Cybertruck", "Roadster", "Semi", "Model 3 Performance"],
        "Fiat": ["500", "Panda", "Tipo", "500X", "500L", "124 Spider", "Doblo", "Qubo"],
        "Renault": ["Clio", "Megane", "Captur", "Kadjar", "Zoe", "Twingo", "Scenic", "Koleos"]
    }
    
    colors = ["Red", "Blue", "Green", "Black", "White", "Silver", "Grey", "Yellow", "Orange", "Purple", "Brown", "Gold"]
    
    # Generate UK-style registration plates
    def generate_registration():
        # Format: AB12 CDE (2001 onwards)
        letters1 = ''.join(random.choices('ABCDEFGHJKLMNOPRSTUVWXYZ', k=2))  # Excluding I, Q
        numbers = ''.join(random.choices('0123456789', k=2))
        letters2 = ''.join(random.choices('ABCDEFGHJKLMNOPRSTUVWXYZ', k=3))  # Excluding I, Q
        return f"{letters1}{numbers} {letters2}"
    
    make = random.choice(makes)
    model = random.choice(models[make])
    year = random.randint(2000, 2023)
    color = random.choice(colors)
    registration = generate_registration()
    
    # Generate a random MOT expiry date
    current_year = datetime.now().year
    mot_expiry = f"{random.randint(1, 28):02d}/{random.randint(1, 12):02d}/{current_year + random.randint(-1, 2)}"
    
    return registration, make, model, year, color, mot_expiry

def fix_database_data():
    """Fix the data in the database directory"""
    # Database path
    db_path = os.path.join(os.path.dirname(__file__), 'database', 'garage_system.db')
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Clear existing data
        cursor.execute("DELETE FROM vehicles")
        cursor.execute("DELETE FROM customers")
        
        # Generate customers
        logger.info("Generating customers...")
        for i in range(1, 1001):
            name, email, phone, address = generate_customer_data()
            
            cursor.execute("""
            INSERT INTO customers (
                id, name, email, phone, address, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                i, name, email, phone, address,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
        
        # Get all customer IDs
        cursor.execute("SELECT id FROM customers")
        customer_ids = [row['id'] for row in cursor.fetchall()]
        
        # Generate vehicles
        logger.info("Generating vehicles...")
        for i in range(1, 2001):
            registration, make, model, year, color, mot_expiry = generate_vehicle_data()
            
            # Assign a random customer
            customer_id = random.choice(customer_ids)
            
            cursor.execute("""
            INSERT INTO vehicles (
                id, registration, make, model, year, color, mot_expiry, customer_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                i, registration, make, model, year, color, mot_expiry, customer_id,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
        
        # Commit changes
        conn.commit()
        
        # Get counts
        cursor.execute("SELECT COUNT(*) FROM customers")
        customer_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM vehicles")
        vehicle_count = cursor.fetchone()[0]
        
        logger.info(f"Generated {customer_count} customers and {vehicle_count} vehicles")
        
    except Exception as e:
        logger.error(f"Error fixing database data: {e}")
        conn.rollback()
        
    finally:
        # Close database connection
        conn.close()

if __name__ == "__main__":
    fix_database_data()
