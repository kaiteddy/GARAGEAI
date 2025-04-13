#!/usr/bin/env python3
"""
Data Access Module

This module provides data access functions for the application models.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.utils.database import get_db_connection
from app.models.customer import Customer
from app.models.vehicle import Vehicle
from app.models.reminder import Reminder

logger = logging.getLogger(__name__)

class DataAccess:
    """Data access class for the application"""
    
    def __init__(self, db_path: str):
        """
        Initialize the data access object.
        
        Args:
            db_path (str): Path to the database file
        """
        self.db_path = db_path
    
    def get_customers(self, limit: int = None, offset: int = None) -> List[Customer]:
        """
        Get customers from the database.
        
        Args:
            limit (int): Maximum number of customers to return
            offset (int): Offset for pagination
            
        Returns:
            list: List of Customer objects
        """
        try:
            # Connect to database
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Build query
            query = """
            SELECT c.id, c.name, c.email, c.phone, c.address, c.created_at, c.updated_at,
                   COUNT(v.id) as vehicle_count
            FROM customers c
            LEFT JOIN vehicles v ON c.id = v.customer_id
            GROUP BY c.id
            ORDER BY c.name
            """
            
            # Add limit and offset if provided
            params = []
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)
                
                if offset is not None:
                    query += " OFFSET ?"
                    params.append(offset)
            
            # Execute query
            cursor.execute(query, params)
            
            # Create Customer objects
            customers = []
            for row in cursor.fetchall():
                customer = Customer.from_db_row(row)
                customers.append(customer)
            
            # Close connection
            conn.close()
            
            return customers
        
        except Exception as e:
            logger.error(f"Error getting customers: {e}")
            return []
    
    def get_customer(self, customer_id: int) -> Optional[Customer]:
        """
        Get a customer by ID.
        
        Args:
            customer_id (int): Customer ID
            
        Returns:
            Customer: Customer object, or None if not found
        """
        try:
            # Connect to database
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Get customer
            cursor.execute("""
            SELECT c.id, c.name, c.email, c.phone, c.address, c.created_at, c.updated_at
            FROM customers c
            WHERE c.id = ?
            """, (customer_id,))
            
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return None
            
            # Create Customer object
            customer = Customer.from_db_row(row)
            
            # Get customer vehicles
            cursor.execute("""
            SELECT v.id, v.registration, v.make, v.model, v.year, v.color, 
                   v.vin, v.engine_size, v.fuel_type, v.transmission,
                   v.mot_expiry, v.mot_status, v.last_mot_check,
                   v.created_at, v.updated_at
            FROM vehicles v
            WHERE v.customer_id = ?
            ORDER BY v.registration
            """, (customer_id,))
            
            # Add vehicles to customer
            for v_row in cursor.fetchall():
                vehicle = Vehicle.from_db_row(v_row)
                vehicle.customer_id = customer_id
                vehicle.customer = customer
                customer.vehicles.append(vehicle)
            
            # Close connection
            conn.close()
            
            return customer
        
        except Exception as e:
            logger.error(f"Error getting customer: {e}")
            return None
    
    def get_vehicles(self, limit: int = None, offset: int = None) -> List[Vehicle]:
        """
        Get vehicles from the database.
        
        Args:
            limit (int): Maximum number of vehicles to return
            offset (int): Offset for pagination
            
        Returns:
            list: List of Vehicle objects
        """
        try:
            # Connect to database
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Build query
            query = """
            SELECT v.id, v.registration, v.make, v.model, v.year, v.color, 
                   v.vin, v.engine_size, v.fuel_type, v.transmission,
                   v.mot_expiry, v.mot_status, v.last_mot_check,
                   v.customer_id, v.created_at, v.updated_at,
                   c.name as customer_name, c.email as customer_email, 
                   c.phone as customer_phone
            FROM vehicles v
            LEFT JOIN customers c ON v.customer_id = c.id
            ORDER BY v.registration
            """
            
            # Add limit and offset if provided
            params = []
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)
                
                if offset is not None:
                    query += " OFFSET ?"
                    params.append(offset)
            
            # Execute query
            cursor.execute(query, params)
            
            # Create Vehicle objects
            vehicles = []
            for row in cursor.fetchall():
                vehicle = Vehicle.from_db_row(row)
                
                # Add customer if available
                if row.get('customer_id'):
                    customer = Customer(
                        id=row.get('customer_id'),
                        name=row.get('customer_name', ''),
                        email=row.get('customer_email', ''),
                        phone=row.get('customer_phone', '')
                    )
                    vehicle.customer = customer
                
                vehicles.append(vehicle)
            
            # Close connection
            conn.close()
            
            return vehicles
        
        except Exception as e:
            logger.error(f"Error getting vehicles: {e}")
            return []
    
    def get_vehicle(self, vehicle_id: int) -> Optional[Vehicle]:
        """
        Get a vehicle by ID.
        
        Args:
            vehicle_id (int): Vehicle ID
            
        Returns:
            Vehicle: Vehicle object, or None if not found
        """
        try:
            # Connect to database
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Get vehicle
            cursor.execute("""
            SELECT v.id, v.registration, v.make, v.model, v.year, v.color, 
                   v.vin, v.engine_size, v.fuel_type, v.transmission,
                   v.mot_expiry, v.mot_status, v.last_mot_check,
                   v.customer_id, v.created_at, v.updated_at,
                   c.name as customer_name, c.email as customer_email, 
                   c.phone as customer_phone
            FROM vehicles v
            LEFT JOIN customers c ON v.customer_id = c.id
            WHERE v.id = ?
            """, (vehicle_id,))
            
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return None
            
            # Create Vehicle object
            vehicle = Vehicle.from_db_row(row)
            
            # Add customer if available
            if row.get('customer_id'):
                customer = Customer(
                    id=row.get('customer_id'),
                    name=row.get('customer_name', ''),
                    email=row.get('customer_email', ''),
                    phone=row.get('customer_phone', '')
                )
                vehicle.customer = customer
            
            # Get vehicle service records
            cursor.execute("""
            SELECT id, service_date, service_type, mileage, description, cost
            FROM service_records
            WHERE vehicle_id = ?
            ORDER BY service_date DESC
            """, (vehicle_id,))
            
            # Add service records to vehicle
            for sr_row in cursor.fetchall():
                vehicle.service_records.append(dict(sr_row))
            
            # Get vehicle MOT history
            cursor.execute("""
            SELECT id, test_date, result, expiry_date, mileage, advisory_notes
            FROM mot_history
            WHERE vehicle_id = ?
            ORDER BY test_date DESC
            """, (vehicle_id,))
            
            # Add MOT history to vehicle
            for mot_row in cursor.fetchall():
                vehicle.mot_history.append(dict(mot_row))
            
            # Get vehicle reminders
            cursor.execute("""
            SELECT id, reminder_date, reminder_type, status, notes, created_at, updated_at
            FROM reminders
            WHERE vehicle_id = ?
            ORDER BY reminder_date DESC
            """, (vehicle_id,))
            
            # Add reminders to vehicle
            for r_row in cursor.fetchall():
                reminder = Reminder.from_db_row(r_row)
                reminder.vehicle = vehicle
                reminder.customer = vehicle.customer
                vehicle.reminders.append(reminder)
            
            # Close connection
            conn.close()
            
            return vehicle
        
        except Exception as e:
            logger.error(f"Error getting vehicle: {e}")
            return None
    
    def get_reminders(self, status: str = None, limit: int = None, offset: int = None) -> List[Reminder]:
        """
        Get reminders from the database.
        
        Args:
            status (str): Filter by status
            limit (int): Maximum number of reminders to return
            offset (int): Offset for pagination
            
        Returns:
            list: List of Reminder objects
        """
        try:
            # Connect to database
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Build query
            query = """
            SELECT r.id, r.vehicle_id, r.reminder_date, r.reminder_type, r.status, r.notes,
                   r.created_at, r.updated_at,
                   v.registration, v.make, v.model, v.customer_id,
                   c.name as customer_name, c.email as customer_email, c.phone as customer_phone
            FROM reminders r
            JOIN vehicles v ON r.vehicle_id = v.id
            LEFT JOIN customers c ON v.customer_id = c.id
            """
            
            # Add status filter if provided
            params = []
            if status:
                query += " WHERE r.status = ?"
                params.append(status)
            
            # Add order by
            query += " ORDER BY r.reminder_date DESC"
            
            # Add limit and offset if provided
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)
                
                if offset is not None:
                    query += " OFFSET ?"
                    params.append(offset)
            
            # Execute query
            cursor.execute(query, params)
            
            # Create Reminder objects
            reminders = []
            for row in cursor.fetchall():
                reminder = Reminder.from_db_row(row)
                
                # Create Vehicle object
                vehicle = Vehicle(
                    id=row.get('vehicle_id'),
                    registration=row.get('registration', ''),
                    make=row.get('make', ''),
                    model=row.get('model', ''),
                    customer_id=row.get('customer_id')
                )
                
                # Create Customer object if available
                if row.get('customer_id'):
                    customer = Customer(
                        id=row.get('customer_id'),
                        name=row.get('customer_name', ''),
                        email=row.get('customer_email', ''),
                        phone=row.get('customer_phone', '')
                    )
                    vehicle.customer = customer
                    reminder.customer = customer
                
                reminder.vehicle = vehicle
                reminders.append(reminder)
            
            # Close connection
            conn.close()
            
            return reminders
        
        except Exception as e:
            logger.error(f"Error getting reminders: {e}")
            return []
    
    def get_vehicles_due_for_mot(self, days: int = 30) -> List[Vehicle]:
        """
        Get vehicles due for MOT within the specified number of days.
        
        Args:
            days (int): Number of days to look ahead
            
        Returns:
            list: List of Vehicle objects
        """
        try:
            # Connect to database
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Calculate date range
            today = datetime.now().date()
            future_date = today + timedelta(days=days)
            
            # Get vehicles due for MOT
            cursor.execute("""
            SELECT v.id, v.registration, v.make, v.model, v.year, v.color, 
                   v.mot_expiry, v.mot_status, v.customer_id,
                   c.name as customer_name, c.email as customer_email, 
                   c.phone as customer_phone
            FROM vehicles v
            LEFT JOIN customers c ON v.customer_id = c.id
            WHERE v.mot_expiry BETWEEN ? AND ?
            ORDER BY v.mot_expiry
            """, (today.strftime('%Y-%m-%d'), future_date.strftime('%Y-%m-%d')))
            
            # Create Vehicle objects
            vehicles = []
            for row in cursor.fetchall():
                vehicle = Vehicle.from_db_row(row)
                
                # Add customer if available
                if row.get('customer_id'):
                    customer = Customer(
                        id=row.get('customer_id'),
                        name=row.get('customer_name', ''),
                        email=row.get('customer_email', ''),
                        phone=row.get('customer_phone', '')
                    )
                    vehicle.customer = customer
                
                vehicles.append(vehicle)
            
            # Close connection
            conn.close()
            
            return vehicles
        
        except Exception as e:
            logger.error(f"Error getting vehicles due for MOT: {e}")
            return []
