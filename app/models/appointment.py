#!/usr/bin/env python3
"""
Appointment Model

This module defines the Appointment model class for scheduling appointments.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

class Appointment:
    """Appointment model class"""
    
    def __init__(self, id: int = None, customer_id: int = None, 
                 vehicle_id: int = None, appointment_date: str = None, 
                 start_time: str = None, end_time: str = None, 
                 service_type: str = "", status: str = "Scheduled", 
                 notes: str = "", created_at: str = None, 
                 updated_at: str = None):
        """
        Initialize an Appointment object.
        
        Args:
            id (int): Appointment ID
            customer_id (int): Customer ID
            vehicle_id (int): Vehicle ID
            appointment_date (str): Appointment date
            start_time (str): Start time
            end_time (str): End time
            service_type (str): Service type
            status (str): Appointment status
            notes (str): Additional notes
            created_at (str): Creation timestamp
            updated_at (str): Last update timestamp
        """
        self.id = id
        self.customer_id = customer_id
        self.vehicle_id = vehicle_id
        self.appointment_date = appointment_date or datetime.now().strftime('%Y-%m-%d')
        self.start_time = start_time or "09:00"
        self.end_time = end_time or "10:00"
        self.service_type = service_type
        self.status = status
        self.notes = notes
        self.created_at = created_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.updated_at = updated_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Related objects
        self.customer = None
        self.vehicle = None
    
    @property
    def datetime_start(self) -> datetime:
        """Get start datetime"""
        try:
            date_str = f"{self.appointment_date} {self.start_time}"
            return datetime.strptime(date_str, '%Y-%m-%d %H:%M')
        except Exception:
            return datetime.now()
    
    @property
    def datetime_end(self) -> datetime:
        """Get end datetime"""
        try:
            date_str = f"{self.appointment_date} {self.end_time}"
            return datetime.strptime(date_str, '%Y-%m-%d %H:%M')
        except Exception:
            return datetime.now() + timedelta(hours=1)
    
    @property
    def duration_minutes(self) -> int:
        """Calculate duration in minutes"""
        delta = self.datetime_end - self.datetime_start
        return int(delta.total_seconds() / 60)
    
    @property
    def is_past(self) -> bool:
        """Check if appointment is in the past"""
        return self.datetime_end < datetime.now()
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'Appointment':
        """
        Create an Appointment object from a database row.
        
        Args:
            row (dict): Database row
            
        Returns:
            Appointment: Appointment object
        """
        return cls(
            id=row.get('id'),
            customer_id=row.get('customer_id'),
            vehicle_id=row.get('vehicle_id'),
            appointment_date=row.get('appointment_date'),
            start_time=row.get('start_time'),
            end_time=row.get('end_time'),
            service_type=row.get('service_type', ''),
            status=row.get('status', 'Scheduled'),
            notes=row.get('notes', ''),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert Appointment object to dictionary.
        
        Returns:
            dict: Dictionary representation of Appointment
        """
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'vehicle_id': self.vehicle_id,
            'appointment_date': self.appointment_date,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'service_type': self.service_type,
            'status': self.status,
            'notes': self.notes,
            'duration_minutes': self.duration_minutes,
            'is_past': self.is_past,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'customer_name': self.customer.name if self.customer else None,
            'vehicle_registration': self.vehicle.registration if self.vehicle else None,
            'vehicle_make': self.vehicle.make if self.vehicle else None,
            'vehicle_model': self.vehicle.model if self.vehicle else None
        }
    
    def __repr__(self) -> str:
        """String representation of Appointment"""
        return f"<Appointment {self.id}: {self.appointment_date} {self.start_time}-{self.end_time} ({self.status})>"
