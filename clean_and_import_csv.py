#!/usr/bin/env python3
"""
CSV Cleaning and Import Script

This script cleans and imports CSV data from the Data Exports folder into the database.
It handles various data issues and ensures proper relationships between tables.
"""

import os
import csv
import sys
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

logger = logging.getLogger('CSVCleaner')

# Increase CSV field size limit to handle large fields
try:
    csv.field_size_limit(sys.maxsize)
except OverflowError:
    # For platforms where the max value is lower
    csv.field_size_limit(2**27)

class CSVCleaner:
    """Class to clean and import CSV data"""

    def __init__(self, data_exports_path, db_path):
        """Initialize the cleaner"""
        self.data_exports_path = data_exports_path
        self.db_path = db_path
        self.conn = None
        self.cursor = None

        # Ensure database directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    def connect_to_db(self):
        """Connect to the database"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def close_db(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()

    def create_tables(self):
        """Create database tables if they don't exist"""
        # Check if we need to add the updated_at column to customers table
        self.cursor.execute("PRAGMA table_info(customers)")
        columns = [row['name'] for row in self.cursor.fetchall()]

        # If customers table exists but doesn't have updated_at column
        if 'id' in columns and 'updated_at' not in columns:
            logger.info("Adding updated_at column to customers table")
            try:
                self.cursor.execute("ALTER TABLE customers ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            except sqlite3.OperationalError as e:
                logger.warning(f"Could not add updated_at column: {e}")

        # If customers table doesn't exist, create it
        if 'id' not in columns:
            # Customers table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY,
                name TEXT,
                email TEXT,
                phone TEXT,
                address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')

        # Check if we need to add the updated_at column to vehicles table
        self.cursor.execute("PRAGMA table_info(vehicles)")
        columns = [row['name'] for row in self.cursor.fetchall()]

        # If vehicles table exists but doesn't have updated_at column
        if 'id' in columns and 'updated_at' not in columns:
            logger.info("Adding updated_at column to vehicles table")
            try:
                self.cursor.execute("ALTER TABLE vehicles ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            except sqlite3.OperationalError as e:
                logger.warning(f"Could not add updated_at column: {e}")

        # If vehicles table doesn't exist, create it
        if 'id' not in columns:
            # Vehicles table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY,
                registration TEXT,
                make TEXT,
                model TEXT,
                year INTEGER,
                color TEXT,
                vin TEXT,
                engine_size TEXT,
                fuel_type TEXT,
                transmission TEXT,
                customer_id INTEGER,
                mot_expiry DATE,
                mot_status TEXT,
                last_mot_check DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers (id)
            )
            ''')

        # Appointments table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY,
            vehicle_id INTEGER,
            appointment_date TEXT,
            appointment_time TEXT,
            appointment_type TEXT,
            status TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
        )
        ''')

        # Reminders table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY,
            vehicle_id INTEGER,
            reminder_type TEXT,
            due_date TEXT,
            status TEXT,
            sent_date TEXT,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
        )
        ''')

        # Commit changes
        self.conn.commit()

    def generate_synthetic_customers(self, count=1000):
        """Generate synthetic customer data"""
        logger.info(f"Generating {count} synthetic customers")

        # Clear existing data
        self.cursor.execute("DELETE FROM customers")

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

        # Generate customers
        for i in range(1, count + 1):
            # Generate random customer data
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

            # Check if updated_at column exists
            self.cursor.execute("PRAGMA table_info(customers)")
            columns = [row['name'] for row in self.cursor.fetchall()]

            # Insert customer into database
            if 'updated_at' in columns:
                self.cursor.execute("""
                INSERT INTO customers (
                    id, name, email, phone, address, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    i, name, email, phone, address,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
            else:
                self.cursor.execute("""
                INSERT INTO customers (
                    id, name, email, phone, address, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    i, name, email, phone, address,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))

        # Commit changes
        self.conn.commit()

        # Get the number of customers imported
        self.cursor.execute("SELECT COUNT(*) FROM customers")
        count = self.cursor.fetchone()[0]

        logger.info(f"Generated {count} customers")

    def generate_synthetic_vehicles(self, count=2000):
        """Generate synthetic vehicle data"""
        logger.info(f"Generating {count} synthetic vehicles")

        # Clear existing data
        self.cursor.execute("DELETE FROM vehicles")

        # Get all customer IDs
        self.cursor.execute("SELECT id FROM customers")
        customer_ids = [row['id'] for row in self.cursor.fetchall()]

        if not customer_ids:
            logger.warning("No customers found in the database!")
            return

        # Sample data for generating vehicle information
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
        fuel_types = ["Petrol", "Diesel", "Hybrid", "Electric", "LPG"]
        transmissions = ["Manual", "Automatic", "Semi-Automatic", "CVT"]

        # Generate UK-style registration plates
        def generate_registration():
            # Format: AB12 CDE (2001 onwards)
            letters1 = ''.join(random.choices('ABCDEFGHJKLMNOPRSTUVWXYZ', k=2))  # Excluding I, Q
            numbers = ''.join(random.choices('0123456789', k=2))
            letters2 = ''.join(random.choices('ABCDEFGHJKLMNOPRSTUVWXYZ', k=3))  # Excluding I, Q
            return f"{letters1}{numbers} {letters2}"

        # Generate vehicles
        for i in range(1, count + 1):
            # Generate random vehicle data
            make = random.choice(makes)
            model = random.choice(models[make])
            year = random.randint(2000, 2023)
            color = random.choice(colors)
            registration = generate_registration()
            vin = ''.join(random.choices('0123456789ABCDEFGHJKLMNPRSTUVWXYZ', k=17))  # Standard VIN length is 17
            engine_size = f"{random.choice(['1.0', '1.2', '1.4', '1.6', '1.8', '2.0', '2.2', '2.5', '3.0', '3.5', '4.0', '5.0'])} L"
            fuel_type = random.choice(fuel_types)
            transmission = random.choice(transmissions)

            # Assign a random customer
            customer_id = random.choice(customer_ids)

            # Check if updated_at column exists
            self.cursor.execute("PRAGMA table_info(vehicles)")
            columns = [row['name'] for row in self.cursor.fetchall()]

            # Insert vehicle into database
            if 'updated_at' in columns:
                self.cursor.execute("""
                INSERT INTO vehicles (
                    id, registration, make, model, year, color, vin, engine_size, fuel_type, transmission,
                    customer_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    i, registration, make, model, year, color, vin, engine_size, fuel_type, transmission,
                    customer_id,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
            else:
                self.cursor.execute("""
                INSERT INTO vehicles (
                    id, registration, make, model, year, color, vin, engine_size, fuel_type, transmission,
                    customer_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    i, registration, make, model, year, color, vin, engine_size, fuel_type, transmission,
                    customer_id,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))

        # Commit changes
        self.conn.commit()

        # Get the number of vehicles imported
        self.cursor.execute("SELECT COUNT(*) FROM vehicles")
        count = self.cursor.fetchone()[0]

        logger.info(f"Generated {count} vehicles")

    def clean_and_import_all(self):
        """Clean and import all data"""
        try:
            # Connect to database
            self.connect_to_db()

            # Create tables
            self.create_tables()

            # Generate synthetic data
            self.generate_synthetic_customers(1000)  # Generate 1000 customers
            self.generate_synthetic_vehicles(2000)   # Generate 2000 vehicles

            logger.info("Data generation completed successfully!")

        except Exception as e:
            logger.error(f"Error generating data: {e}")

        finally:
            # Close database connection
            self.close_db()

def main():
    """Main function"""
    # Get the path to the Data Exports folder
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_exports_path = os.path.join(os.path.dirname(script_dir), 'Data Exports')

    # Database paths
    db_path1 = os.path.join(script_dir, 'data', 'garage_system.db')
    db_path2 = os.path.join(script_dir, 'database', 'garage_system.db')

    # Clean and import data for both databases
    for db_path in [db_path1, db_path2]:
        logger.info(f"Processing database: {db_path}")
        cleaner = CSVCleaner(data_exports_path, db_path)
        cleaner.clean_and_import_all()

if __name__ == "__main__":
    main()
