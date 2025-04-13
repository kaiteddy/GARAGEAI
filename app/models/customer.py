#!/usr/bin/env python3
"""
Customer Model

This module defines the Customer model class.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

class Customer:
    """Customer model class"""
    
    def __init__(self, id: int = None, name: str = "", email: str = "", 
                 phone: str = "", address: str = "", 
                 created_at: str = None, updated_at: str = None):
        """
        Initialize a Customer object.
        
        Args:
            id (int): Customer ID
            name (str): Customer name
            email (str): Customer email
            phone (str): Customer phone number
            address (str): Customer address
            created_at (str): Creation timestamp
            updated_at (str): Last update timestamp
        """
        self.id = id
        self.name = name
        self.email = email
        self.phone = phone
        self.address = address
        self.created_at = created_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.updated_at = updated_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Derived properties
        self.first_name = name.split(' ')[0] if name else ""
        self.last_name = ' '.join(name.split(' ')[1:]) if name and ' ' in name else ""
        
        # Related objects
        self.vehicles = []
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'Customer':
        """
        Create a Customer object from a database row.
        
        Args:
            row (dict): Database row
            
        Returns:
            Customer: Customer object
        """
        return cls(
            id=row.get('id'),
            name=row.get('name') or row.get('full_name', ''),
            email=row.get('email', ''),
            phone=row.get('phone', ''),
            address=row.get('address', ''),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert Customer object to dictionary.
        
        Returns:
            dict: Dictionary representation of Customer
        """
        return {
            'id': self.id,
            'name': self.name,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'vehicle_count': len(self.vehicles)
        }
    
    def __repr__(self) -> str:
        """String representation of Customer"""
        return f"<Customer {self.id}: {self.name}>"
