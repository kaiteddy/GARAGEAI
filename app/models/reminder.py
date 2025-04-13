#!/usr/bin/env python3
"""
Reminder Model

This module defines the Reminder model class for MOT and service reminders.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

class Reminder:
    """Reminder model class"""
    
    def __init__(self, id: int = None, vehicle_id: int = None, 
                 reminder_date: str = None, reminder_type: str = "", 
                 status: str = "Pending", notes: str = "", 
                 created_at: str = None, updated_at: str = None):
        """
        Initialize a Reminder object.
        
        Args:
            id (int): Reminder ID
            vehicle_id (int): Vehicle ID
            reminder_date (str): Reminder date
            reminder_type (str): Reminder type (MOT, Service, etc.)
            status (str): Reminder status (Pending, Sent, Acknowledged)
            notes (str): Additional notes
            created_at (str): Creation timestamp
            updated_at (str): Last update timestamp
        """
        self.id = id
        self.vehicle_id = vehicle_id
        self.reminder_date = reminder_date or datetime.now().strftime('%Y-%m-%d')
        self.reminder_type = reminder_type
        self.status = status
        self.notes = notes
        self.created_at = created_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.updated_at = updated_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Related objects
        self.vehicle = None
        self.customer = None
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'Reminder':
        """
        Create a Reminder object from a database row.
        
        Args:
            row (dict): Database row
            
        Returns:
            Reminder: Reminder object
        """
        return cls(
            id=row.get('id'),
            vehicle_id=row.get('vehicle_id'),
            reminder_date=row.get('reminder_date'),
            reminder_type=row.get('reminder_type', ''),
            status=row.get('status', 'Pending'),
            notes=row.get('notes', ''),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert Reminder object to dictionary.
        
        Returns:
            dict: Dictionary representation of Reminder
        """
        return {
            'id': self.id,
            'vehicle_id': self.vehicle_id,
            'reminder_date': self.reminder_date,
            'reminder_type': self.reminder_type,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'vehicle_registration': self.vehicle.registration if self.vehicle else None,
            'vehicle_make': self.vehicle.make if self.vehicle else None,
            'vehicle_model': self.vehicle.model if self.vehicle else None,
            'customer_id': self.customer.id if self.customer else None,
            'customer_name': self.customer.name if self.customer else None
        }
    
    def is_overdue(self) -> bool:
        """
        Check if reminder is overdue.
        
        Returns:
            bool: True if reminder is overdue, False otherwise
        """
        if not self.reminder_date:
            return False
        
        try:
            reminder_date = datetime.strptime(self.reminder_date, '%Y-%m-%d').date()
            today = datetime.now().date()
            
            return reminder_date < today and self.status == 'Pending'
        
        except Exception:
            return False
    
    def __repr__(self) -> str:
        """String representation of Reminder"""
        return f"<Reminder {self.id}: {self.reminder_type} ({self.status})>"
