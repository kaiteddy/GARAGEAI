#!/usr/bin/env python3
"""
Document Model

This module defines the Document model class for managing documents.
"""

import os
from datetime import datetime
from typing import List, Optional, Dict, Any

class Document:
    """Document model class"""
    
    def __init__(self, id: int = None, customer_id: int = None, 
                 vehicle_id: int = None, document_type: str = "", 
                 filename: str = "", file_path: str = "", 
                 created_at: str = None, updated_at: str = None):
        """
        Initialize a Document object.
        
        Args:
            id (int): Document ID
            customer_id (int): Customer ID
            vehicle_id (int): Vehicle ID
            document_type (str): Document type
            filename (str): Original filename
            file_path (str): Path to stored file
            created_at (str): Creation timestamp
            updated_at (str): Last update timestamp
        """
        self.id = id
        self.customer_id = customer_id
        self.vehicle_id = vehicle_id
        self.document_type = document_type
        self.filename = filename
        self.file_path = file_path
        self.created_at = created_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.updated_at = updated_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Related objects
        self.customer = None
        self.vehicle = None
    
    @property
    def file_exists(self) -> bool:
        """Check if file exists"""
        return os.path.exists(self.file_path) if self.file_path else False
    
    @property
    def file_size(self) -> int:
        """Get file size in bytes"""
        return os.path.getsize(self.file_path) if self.file_exists else 0
    
    @property
    def file_extension(self) -> str:
        """Get file extension"""
        return os.path.splitext(self.filename)[1].lower() if self.filename else ""
    
    @property
    def is_image(self) -> bool:
        """Check if document is an image"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
        return self.file_extension in image_extensions
    
    @property
    def is_pdf(self) -> bool:
        """Check if document is a PDF"""
        return self.file_extension == '.pdf'
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'Document':
        """
        Create a Document object from a database row.
        
        Args:
            row (dict): Database row
            
        Returns:
            Document: Document object
        """
        return cls(
            id=row.get('id'),
            customer_id=row.get('customer_id'),
            vehicle_id=row.get('vehicle_id'),
            document_type=row.get('document_type', ''),
            filename=row.get('filename', ''),
            file_path=row.get('file_path', ''),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert Document object to dictionary.
        
        Returns:
            dict: Dictionary representation of Document
        """
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'vehicle_id': self.vehicle_id,
            'document_type': self.document_type,
            'filename': self.filename,
            'file_path': self.file_path,
            'file_exists': self.file_exists,
            'file_size': self.file_size,
            'file_extension': self.file_extension,
            'is_image': self.is_image,
            'is_pdf': self.is_pdf,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'customer_name': self.customer.name if self.customer else None,
            'vehicle_registration': self.vehicle.registration if self.vehicle else None
        }
    
    def __repr__(self) -> str:
        """String representation of Document"""
        return f"<Document {self.id}: {self.document_type} ({self.filename})>"
