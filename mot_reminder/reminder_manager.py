#!/usr/bin/env python3
"""
MOT Reminder Manager

This module handles the core functionality of the MOT Reminder System:
- Identifying vehicles with upcoming MOT tests
- Generating reminders
- Tracking reminder status
- Managing follow-ups
"""

import os
import sys
import csv
import json
import sqlite3
import logging
import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('MOTReminderManager')

class MOTReminderManager:
    """Manager for MOT reminders"""
    
    def __init__(self, db_path: str, config_path: Optional[str] = None):
        """Initialize the MOT reminder manager
        
        Args:
            db_path: Path to the SQLite database
            config_path: Optional path to configuration file
        """
        self.db_path = db_path
        self.connection = None
        self.cursor = None
        self.config = self._load_config(config_path)
        
        # Initialize database
        self._init_database()
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict:
        """Load configuration from file or use defaults
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        default_config = {
            "reminder_days": [30, 14, 7, 3, 1],  # Days before MOT expiry to send reminders
            "reminder_templates": {
                "email": {
                    "subject": "MOT Reminder for {registration}",
                    "body": "Dear {customer_name},\n\nThis is a reminder that the MOT for your {make} {model} ({registration}) is due on {mot_expiry}.\n\nPlease contact us to schedule an appointment.\n\nRegards,\nYour Garage"
                },
                "sms": {
                    "body": "MOT Reminder: Your {make} {model} ({registration}) is due for MOT on {mot_expiry}. Please contact us to schedule an appointment."
                },
                "letter": {
                    "body": "Dear {customer_name},\n\nThis is a reminder that the MOT for your {make} {model} ({registration}) is due on {mot_expiry}.\n\nPlease contact us to schedule an appointment.\n\nRegards,\nYour Garage"
                }
            },
            "garage_details": {
                "name": "Your Garage",
                "address": "123 Main Street, Anytown, AN1 1AA",
                "phone": "01234 567890",
                "email": "info@yourgarage.com",
                "website": "www.yourgarage.com"
            }
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults to ensure all required fields exist
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    logger.info(f"Loaded configuration from {config_path}")
                    return config
            except Exception as e:
                logger.error(f"Error loading configuration: {e}")
        
        logger.info("Using default configuration")
        return default_config
    
    def _init_database(self) -> bool:
        """Initialize the database
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Connect to database
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            self.cursor = self.connection.cursor()
            
            # Create reminders table if it doesn't exist
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS mot_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id TEXT,
                registration TEXT,
                customer_id TEXT,
                customer_name TEXT,
                customer_email TEXT,
                customer_phone TEXT,
                make TEXT,
                model TEXT,
                mot_expiry TEXT,
                days_to_expiry INTEGER,
                reminder_date TEXT,
                reminder_type TEXT,
                reminder_status TEXT,
                reminder_sent_date TEXT,
                reminder_response TEXT,
                notes TEXT
            )
            """)
            
            # Create reminder templates table if it doesn't exist
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminder_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                type TEXT,
                subject TEXT,
                body TEXT,
                created_date TEXT,
                last_modified TEXT
            )
            """)
            
            # Create reminder settings table if it doesn't exist
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminder_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_name TEXT UNIQUE,
                setting_value TEXT,
                setting_type TEXT
            )
            """)
            
            # Insert default settings if not exists
            for days in self.config["reminder_days"]:
                self.cursor.execute(
                    "INSERT OR IGNORE INTO reminder_settings (setting_name, setting_value, setting_type) VALUES (?, ?, ?)",
                    (f"reminder_days_{days}", str(days), "integer")
                )
            
            # Insert default templates if not exists
            for reminder_type, templates in self.config["reminder_templates"].items():
                if reminder_type == "email":
                    self.cursor.execute(
                        "INSERT OR IGNORE INTO reminder_templates (name, type, subject, body, created_date, last_modified) VALUES (?, ?, ?, ?, ?, ?)",
                        (f"Default {reminder_type.capitalize()} Template", reminder_type, templates["subject"], templates["body"], 
                         datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    )
                else:
                    self.cursor.execute(
                        "INSERT OR IGNORE INTO reminder_templates (name, type, subject, body, created_date, last_modified) VALUES (?, ?, ?, ?, ?, ?)",
                        (f"Default {reminder_type.capitalize()} Template", reminder_type, "", templates["body"], 
                         datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    )
            
            # Insert garage details if not exists
            for key, value in self.config["garage_details"].items():
                self.cursor.execute(
                    "INSERT OR IGNORE INTO reminder_settings (setting_name, setting_value, setting_type) VALUES (?, ?, ?)",
                    (f"garage_{key}", value, "string")
                )
            
            self.connection.commit()
            logger.info("Database initialized successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            return False
    
    def find_vehicles_due_for_mot(self, days_range: List[int] = None) -> List[Dict]:
        """Find vehicles due for MOT within specified days
        
        Args:
            days_range: List of days to check (e.g. [30, 14, 7])
            
        Returns:
            List of vehicles due for MOT
        """
        if days_range is None:
            days_range = self.config["reminder_days"]
        
        try:
            vehicles = []
            today = datetime.date.today()
            
            # Check if Vehicles table exists
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Vehicles'")
            if not self.cursor.fetchone():
                logger.warning("Vehicles table not found in database")
                return []
            
            # Get schema of Vehicles table
            self.cursor.execute("PRAGMA table_info(Vehicles)")
            columns = [row[1] for row in self.cursor.fetchall()]
            
            # Check if required columns exist
            required_columns = ["Registration", "MOTExpiry"]
            for column in required_columns:
                if column not in columns:
                    logger.warning(f"Required column {column} not found in Vehicles table")
                    return []
            
            # Build query based on available columns
            select_columns = ["Registration", "MOTExpiry"]
            if "Make" in columns:
                select_columns.append("Make")
            if "Model" in columns:
                select_columns.append("Model")
            if "CustomerID" in columns:
                select_columns.append("CustomerID")
            
            # Get vehicles with MOT expiry dates
            query = f"SELECT {', '.join(select_columns)} FROM Vehicles WHERE MOTExpiry IS NOT NULL"
            self.cursor.execute(query)
            
            for row in self.cursor.fetchall():
                try:
                    # Parse MOT expiry date
                    mot_expiry = datetime.datetime.strptime(row["MOTExpiry"], "%Y-%m-%d").date()
                    
                    # Calculate days to expiry
                    days_to_expiry = (mot_expiry - today).days
                    
                    # Check if within reminder range
                    if days_to_expiry in days_range:
                        vehicle = {
                            "registration": row["Registration"],
                            "mot_expiry": row["MOTExpiry"],
                            "days_to_expiry": days_to_expiry
                        }
                        
                        # Add optional fields if available
                        if "Make" in row.keys():
                            vehicle["make"] = row["Make"]
                        if "Model" in row.keys():
                            vehicle["model"] = row["Model"]
                        if "CustomerID" in row.keys():
                            vehicle["customer_id"] = row["CustomerID"]
                            
                            # Get customer details if available
                            if vehicle["customer_id"]:
                                customer = self.get_customer_details(vehicle["customer_id"])
                                if customer:
                                    vehicle.update(customer)
                        
                        vehicles.append(vehicle)
                
                except Exception as e:
                    logger.error(f"Error processing vehicle {row['Registration']}: {e}")
            
            logger.info(f"Found {len(vehicles)} vehicles due for MOT")
            return vehicles
        
        except Exception as e:
            logger.error(f"Error finding vehicles due for MOT: {e}")
            return []
    
    def get_customer_details(self, customer_id: str) -> Optional[Dict]:
        """Get customer details from database
        
        Args:
            customer_id: Customer ID
            
        Returns:
            Customer details or None if not found
        """
        try:
            # Check if Customers table exists
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Customers'")
            if not self.cursor.fetchone():
                logger.warning("Customers table not found in database")
                return None
            
            # Get schema of Customers table
            self.cursor.execute("PRAGMA table_info(Customers)")
            columns = [row[1] for row in self.cursor.fetchall()]
            
            # Build query based on available columns
            select_columns = ["ID"]
            customer_fields = {
                "Name": "customer_name",
                "Email": "customer_email",
                "Phone": "customer_phone",
                "Address": "customer_address",
                "City": "customer_city",
                "Postcode": "customer_postcode"
            }
            
            available_columns = []
            for column, field in customer_fields.items():
                if column in columns:
                    select_columns.append(column)
                    available_columns.append((column, field))
            
            # Get customer details
            query = f"SELECT {', '.join(select_columns)} FROM Customers WHERE ID = ?"
            self.cursor.execute(query, (customer_id,))
            row = self.cursor.fetchone()
            
            if not row:
                logger.warning(f"Customer {customer_id} not found")
                return None
            
            # Build customer details
            customer = {}
            for column, field in available_columns:
                customer[field] = row[column]
            
            return customer
        
        except Exception as e:
            logger.error(f"Error getting customer details: {e}")
            return None
    
    def create_reminder(self, vehicle: Dict) -> Optional[int]:
        """Create a reminder for a vehicle
        
        Args:
            vehicle: Vehicle details
            
        Returns:
            Reminder ID if successful, None otherwise
        """
        try:
            # Check if reminder already exists
            self.cursor.execute(
                "SELECT id FROM mot_reminders WHERE registration = ? AND mot_expiry = ? AND days_to_expiry = ?",
                (vehicle["registration"], vehicle["mot_expiry"], vehicle["days_to_expiry"])
            )
            
            existing_reminder = self.cursor.fetchone()
            if existing_reminder:
                logger.info(f"Reminder already exists for {vehicle['registration']} ({vehicle['days_to_expiry']} days to expiry)")
                return existing_reminder[0]
            
            # Create new reminder
            fields = [
                "vehicle_id", "registration", "customer_id", "customer_name", "customer_email", "customer_phone",
                "make", "model", "mot_expiry", "days_to_expiry", "reminder_date", "reminder_type", "reminder_status"
            ]
            
            values = []
            placeholders = []
            
            for field in fields:
                if field in vehicle:
                    values.append(vehicle[field])
                    placeholders.append("?")
                elif field == "reminder_date":
                    values.append(datetime.datetime.now().strftime("%Y-%m-%d"))
                    placeholders.append("?")
                elif field == "reminder_type":
                    values.append("pending")
                    placeholders.append("?")
                elif field == "reminder_status":
                    values.append("created")
                    placeholders.append("?")
                else:
                    values.append(None)
                    placeholders.append("?")
            
            query = f"INSERT INTO mot_reminders ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
            self.cursor.execute(query, values)
            self.connection.commit()
            
            reminder_id = self.cursor.lastrowid
            logger.info(f"Created reminder {reminder_id} for {vehicle['registration']} ({vehicle['days_to_expiry']} days to expiry)")
            
            return reminder_id
        
        except Exception as e:
            logger.error(f"Error creating reminder: {e}")
            return None
    
    def get_pending_reminders(self) -> List[Dict]:
        """Get pending reminders
        
        Returns:
            List of pending reminders
        """
        try:
            self.cursor.execute(
                "SELECT * FROM mot_reminders WHERE reminder_status = 'created' ORDER BY days_to_expiry ASC"
            )
            
            reminders = []
            for row in self.cursor.fetchall():
                reminder = {}
                for key in row.keys():
                    reminder[key] = row[key]
                reminders.append(reminder)
            
            logger.info(f"Found {len(reminders)} pending reminders")
            return reminders
        
        except Exception as e:
            logger.error(f"Error getting pending reminders: {e}")
            return []
    
    def update_reminder_status(self, reminder_id: int, status: str, notes: Optional[str] = None) -> bool:
        """Update reminder status
        
        Args:
            reminder_id: Reminder ID
            status: New status
            notes: Optional notes
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if status == "sent":
                self.cursor.execute(
                    "UPDATE mot_reminders SET reminder_status = ?, reminder_sent_date = ?, notes = ? WHERE id = ?",
                    (status, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), notes, reminder_id)
                )
            else:
                self.cursor.execute(
                    "UPDATE mot_reminders SET reminder_status = ?, notes = ? WHERE id = ?",
                    (status, notes, reminder_id)
                )
            
            self.connection.commit()
            logger.info(f"Updated reminder {reminder_id} status to {status}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error updating reminder status: {e}")
            return False
    
    def get_reminder_template(self, reminder_type: str) -> Optional[Dict]:
        """Get reminder template
        
        Args:
            reminder_type: Type of reminder (email, sms, letter)
            
        Returns:
            Template if found, None otherwise
        """
        try:
            self.cursor.execute(
                "SELECT * FROM reminder_templates WHERE type = ? ORDER BY id DESC LIMIT 1",
                (reminder_type,)
            )
            
            row = self.cursor.fetchone()
            if not row:
                logger.warning(f"No template found for {reminder_type}")
                return None
            
            template = {}
            for key in row.keys():
                template[key] = row[key]
            
            return template
        
        except Exception as e:
            logger.error(f"Error getting reminder template: {e}")
            return None
    
    def generate_reminder_content(self, reminder: Dict, reminder_type: str) -> Optional[Dict]:
        """Generate reminder content from template
        
        Args:
            reminder: Reminder details
            reminder_type: Type of reminder (email, sms, letter)
            
        Returns:
            Generated content if successful, None otherwise
        """
        try:
            template = self.get_reminder_template(reminder_type)
            if not template:
                return None
            
            # Get garage details
            garage_details = {}
            self.cursor.execute("SELECT setting_name, setting_value FROM reminder_settings WHERE setting_name LIKE 'garage_%'")
            for row in self.cursor.fetchall():
                key = row["setting_name"].replace("garage_", "")
                garage_details[key] = row["setting_value"]
            
            # Prepare replacement variables
            variables = {
                "registration": reminder.get("registration", ""),
                "customer_name": reminder.get("customer_name", "Customer"),
                "make": reminder.get("make", "vehicle"),
                "model": reminder.get("model", ""),
                "mot_expiry": reminder.get("mot_expiry", ""),
                "days_to_expiry": reminder.get("days_to_expiry", ""),
                "garage_name": garage_details.get("name", "Your Garage"),
                "garage_address": garage_details.get("address", ""),
                "garage_phone": garage_details.get("phone", ""),
                "garage_email": garage_details.get("email", ""),
                "garage_website": garage_details.get("website", "")
            }
            
            # Generate content
            content = {}
            
            if reminder_type == "email":
                content["subject"] = template["subject"]
                for key, value in variables.items():
                    content["subject"] = content["subject"].replace(f"{{{key}}}", str(value))
            
            content["body"] = template["body"]
            for key, value in variables.items():
                content["body"] = content["body"].replace(f"{{{key}}}", str(value))
            
            return content
        
        except Exception as e:
            logger.error(f"Error generating reminder content: {e}")
            return None
    
    def process_reminders(self) -> Tuple[int, int]:
        """Process all pending reminders
        
        Returns:
            Tuple of (processed count, error count)
        """
        try:
            # Find vehicles due for MOT
            vehicles = self.find_vehicles_due_for_mot()
            
            # Create reminders for each vehicle
            for vehicle in vehicles:
                self.create_reminder(vehicle)
            
            # Get pending reminders
            reminders = self.get_pending_reminders()
            
            processed_count = 0
            error_count = 0
            
            for reminder in reminders:
                # Generate reminder content
                # In a real implementation, this would send the reminder via email, SMS, etc.
                # For now, we'll just update the status
                
                try:
                    # Update reminder status
                    self.update_reminder_status(
                        reminder["id"], 
                        "sent", 
                        f"Reminder processed on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    processed_count += 1
                
                except Exception as e:
                    logger.error(f"Error processing reminder {reminder['id']}: {e}")
                    error_count += 1
            
            logger.info(f"Processed {processed_count} reminders with {error_count} errors")
            return processed_count, error_count
        
        except Exception as e:
            logger.error(f"Error processing reminders: {e}")
            return 0, 0
    
    def get_reminder_statistics(self) -> Dict:
        """Get reminder statistics
        
        Returns:
            Statistics dictionary
        """
        try:
            stats = {
                "total": 0,
                "created": 0,
                "sent": 0,
                "responded": 0,
                "completed": 0,
                "failed": 0,
                "by_day": {}
            }
            
            # Get total counts by status
            self.cursor.execute("SELECT reminder_status, COUNT(*) as count FROM mot_reminders GROUP BY reminder_status")
            for row in self.cursor.fetchall():
                stats[row["reminder_status"]] = row["count"]
                stats["total"] += row["count"]
            
            # Get counts by day
            self.cursor.execute(
                "SELECT days_to_expiry, COUNT(*) as count FROM mot_reminders GROUP BY days_to_expiry ORDER BY days_to_expiry"
            )
            for row in self.cursor.fetchall():
                stats["by_day"][row["days_to_expiry"]] = row["count"]
            
            return stats
        
        except Exception as e:
            logger.error(f"Error getting reminder statistics: {e}")
            return {}
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")


if __name__ == "__main__":
    # Example usage
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ga4_direct.db")
    manager = MOTReminderManager(db_path)
    
    # Process reminders
    processed, errors = manager.process_reminders()
    print(f"Processed {processed} reminders with {errors} errors")
    
    # Get statistics
    stats = manager.get_reminder_statistics()
    print(f"Reminder statistics: {stats}")
    
    # Close connection
    manager.close()
