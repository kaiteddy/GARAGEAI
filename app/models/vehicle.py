#!/usr/bin/env python3
"""
Vehicle Model

This module defines the Vehicle model class.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

class Vehicle:
    """Vehicle model class"""
    
    def __init__(self, id: int = None, registration: str = "", make: str = "", 
                 model: str = "", year: int = None, color: str = "", 
                 vin: str = "", engine_size: str = "", fuel_type: str = "", 
                 transmission: str = "", customer_id: int = None, 
                 mot_expiry: str = None, mot_status: str = None, 
                 last_mot_check: str = None, created_at: str = None, 
                 updated_at: str = None):
        """
        Initialize a Vehicle object.
        
        Args:
            id (int): Vehicle ID
            registration (str): Vehicle registration number
            make (str): Vehicle make
            model (str): Vehicle model
            year (int): Vehicle year
            color (str): Vehicle color
            vin (str): Vehicle identification number
            engine_size (str): Vehicle engine size
            fuel_type (str): Vehicle fuel type
            transmission (str): Vehicle transmission
            customer_id (int): Customer ID
            mot_expiry (str): MOT expiry date
            mot_status (str): MOT status
            last_mot_check (str): Last MOT check date
            created_at (str): Creation timestamp
            updated_at (str): Last update timestamp
        """
        self.id = id
        self.registration = registration
        self.make = make
        self.model = model
        self.year = year
        self.color = color
        self.vin = vin
        self.engine_size = engine_size
        self.fuel_type = fuel_type
        self.transmission = transmission
        self.customer_id = customer_id
        self.mot_expiry = mot_expiry
        self.mot_status = mot_status
        self.last_mot_check = last_mot_check
        self.created_at = created_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.updated_at = updated_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Related objects
        self.customer = None
        self.service_records = []
        self.mot_history = []
        self.reminders = []
        self.appointments = []
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'Vehicle':
        """
        Create a Vehicle object from a database row.
        
        Args:
            row (dict): Database row
            
        Returns:
            Vehicle: Vehicle object
        """
        return cls(
            id=row.get('id'),
            registration=row.get('registration', ''),
            make=row.get('make', ''),
            model=row.get('model', ''),
            year=row.get('year'),
            color=row.get('color', ''),
            vin=row.get('vin', ''),
            engine_size=row.get('engine_size', ''),
            fuel_type=row.get('fuel_type', ''),
            transmission=row.get('transmission', ''),
            customer_id=row.get('customer_id'),
            mot_expiry=row.get('mot_expiry'),
            mot_status=row.get('mot_status'),
            last_mot_check=row.get('last_mot_check'),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert Vehicle object to dictionary.
        
        Returns:
            dict: Dictionary representation of Vehicle
        """
        return {
            'id': self.id,
            'registration': self.registration,
            'make': self.make,
            'model': self.model,
            'year': self.year,
            'color': self.color,
            'vin': self.vin,
            'engine_size': self.engine_size,
            'fuel_type': self.fuel_type,
            'transmission': self.transmission,
            'customer_id': self.customer_id,
            'mot_expiry': self.mot_expiry,
            'mot_status': self.mot_status,
            'last_mot_check': self.last_mot_check,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'customer_name': self.customer.name if self.customer else None
        }
    
    def is_mot_due(self, days: int = 30) -> bool:
        """
        Check if MOT is due within the specified number of days.
        
        Args:
            days (int): Number of days to look ahead
            
        Returns:
            bool: True if MOT is due, False otherwise
        """
        if not self.mot_expiry:
            return False
        
        try:
            mot_date = datetime.strptime(self.mot_expiry, '%Y-%m-%d').date()
            today = datetime.now().date()
            days_until = (mot_date - today).days
            
            return 0 <= days_until <= days
        
        except Exception:
            return False
    
    def __repr__(self) -> str:
        """String representation of Vehicle"""
        return f"<Vehicle {self.id}: {self.registration} ({self.make} {self.model})>"
