#!/usr/bin/env python3
"""
Invoice Model

This module defines the Invoice model class and related models.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

class InvoiceItem:
    """Invoice item model class"""
    
    def __init__(self, id: int = None, invoice_id: int = None, 
                 description: str = "", quantity: float = 0, 
                 unit_price: float = 0, tax_rate: float = 0, 
                 created_at: str = None, updated_at: str = None):
        """
        Initialize an InvoiceItem object.
        
        Args:
            id (int): Invoice item ID
            invoice_id (int): Invoice ID
            description (str): Item description
            quantity (float): Item quantity
            unit_price (float): Item unit price
            tax_rate (float): Item tax rate
            created_at (str): Creation timestamp
            updated_at (str): Last update timestamp
        """
        self.id = id
        self.invoice_id = invoice_id
        self.description = description
        self.quantity = quantity
        self.unit_price = unit_price
        self.tax_rate = tax_rate
        self.created_at = created_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.updated_at = updated_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    @property
    def subtotal(self) -> float:
        """Calculate subtotal"""
        return round(self.quantity * self.unit_price, 2)
    
    @property
    def tax_amount(self) -> float:
        """Calculate tax amount"""
        return round(self.subtotal * (self.tax_rate / 100), 2)
    
    @property
    def total(self) -> float:
        """Calculate total"""
        return round(self.subtotal + self.tax_amount, 2)
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'InvoiceItem':
        """
        Create an InvoiceItem object from a database row.
        
        Args:
            row (dict): Database row
            
        Returns:
            InvoiceItem: InvoiceItem object
        """
        return cls(
            id=row.get('id'),
            invoice_id=row.get('invoice_id'),
            description=row.get('description', ''),
            quantity=row.get('quantity', 0),
            unit_price=row.get('unit_price', 0),
            tax_rate=row.get('tax_rate', 0),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert InvoiceItem object to dictionary.
        
        Returns:
            dict: Dictionary representation of InvoiceItem
        """
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'description': self.description,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'tax_rate': self.tax_rate,
            'subtotal': self.subtotal,
            'tax_amount': self.tax_amount,
            'total': self.total,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def __repr__(self) -> str:
        """String representation of InvoiceItem"""
        return f"<InvoiceItem {self.id}: {self.description} (£{self.total})>"


class Invoice:
    """Invoice model class"""
    
    def __init__(self, id: int = None, customer_id: int = None, 
                 vehicle_id: int = None, invoice_date: str = None, 
                 due_date: str = None, status: str = "Draft", 
                 notes: str = "", created_at: str = None, 
                 updated_at: str = None):
        """
        Initialize an Invoice object.
        
        Args:
            id (int): Invoice ID
            customer_id (int): Customer ID
            vehicle_id (int): Vehicle ID
            invoice_date (str): Invoice date
            due_date (str): Due date
            status (str): Invoice status
            notes (str): Additional notes
            created_at (str): Creation timestamp
            updated_at (str): Last update timestamp
        """
        self.id = id
        self.customer_id = customer_id
        self.vehicle_id = vehicle_id
        self.invoice_date = invoice_date or datetime.now().strftime('%Y-%m-%d')
        self.due_date = due_date or (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        self.status = status
        self.notes = notes
        self.created_at = created_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.updated_at = updated_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Related objects
        self.customer = None
        self.vehicle = None
        self.items = []
    
    @property
    def subtotal(self) -> float:
        """Calculate subtotal"""
        return round(sum(item.subtotal for item in self.items), 2)
    
    @property
    def tax_amount(self) -> float:
        """Calculate tax amount"""
        return round(sum(item.tax_amount for item in self.items), 2)
    
    @property
    def total(self) -> float:
        """Calculate total"""
        return round(self.subtotal + self.tax_amount, 2)
    
    @property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue"""
        if not self.due_date or self.status == 'Paid':
            return False
        
        try:
            due_date = datetime.strptime(self.due_date, '%Y-%m-%d').date()
            today = datetime.now().date()
            
            return due_date < today and self.status != 'Paid'
        
        except Exception:
            return False
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'Invoice':
        """
        Create an Invoice object from a database row.
        
        Args:
            row (dict): Database row
            
        Returns:
            Invoice: Invoice object
        """
        return cls(
            id=row.get('id'),
            customer_id=row.get('customer_id'),
            vehicle_id=row.get('vehicle_id'),
            invoice_date=row.get('invoice_date'),
            due_date=row.get('due_date'),
            status=row.get('status', 'Draft'),
            notes=row.get('notes', ''),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert Invoice object to dictionary.
        
        Returns:
            dict: Dictionary representation of Invoice
        """
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'vehicle_id': self.vehicle_id,
            'invoice_date': self.invoice_date,
            'due_date': self.due_date,
            'status': self.status,
            'notes': self.notes,
            'subtotal': self.subtotal,
            'tax_amount': self.tax_amount,
            'total': self.total,
            'is_overdue': self.is_overdue,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'customer_name': self.customer.name if self.customer else None,
            'vehicle_registration': self.vehicle.registration if self.vehicle else None,
            'items': [item.to_dict() for item in self.items]
        }
    
    def __repr__(self) -> str:
        """String representation of Invoice"""
        return f"<Invoice {self.id}: {self.status} (£{self.total})>"
