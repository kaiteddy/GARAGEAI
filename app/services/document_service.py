#!/usr/bin/env python3
"""
Document Service Module

This module provides services for document management.
"""

import os
import logging
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional
from werkzeug.utils import secure_filename

from app.utils.database import get_db_connection
from app.models.document import Document

logger = logging.getLogger(__name__)

class DocumentService:
    """Document service class"""
    
    def __init__(self, db_path: str, document_dir: str):
        """
        Initialize the document service.
        
        Args:
            db_path (str): Path to the database file
            document_dir (str): Path to the document storage directory
        """
        self.db_path = db_path
        self.document_dir = document_dir
        
        # Create document directory if it doesn't exist
        if not os.path.exists(self.document_dir):
            os.makedirs(self.document_dir)
    
    def get_documents(self, customer_id: int = None, vehicle_id: int = None) -> List[Document]:
        """
        Get documents from the database.
        
        Args:
            customer_id (int): Filter by customer ID
            vehicle_id (int): Filter by vehicle ID
            
        Returns:
            list: List of Document objects
        """
        try:
            # Connect to database
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Build query
            query = """
            SELECT d.id, d.customer_id, d.vehicle_id, d.document_type, d.filename, d.file_path,
                   d.created_at, d.updated_at,
                   c.name as customer_name,
                   v.registration, v.make, v.model
            FROM documents d
            LEFT JOIN customers c ON d.customer_id = c.id
            LEFT JOIN vehicles v ON d.vehicle_id = v.id
            """
            
            # Add filters
            params = []
            conditions = []
            
            if customer_id is not None:
                conditions.append("d.customer_id = ?")
                params.append(customer_id)
            
            if vehicle_id is not None:
                conditions.append("d.vehicle_id = ?")
                params.append(vehicle_id)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            # Add order by
            query += " ORDER BY d.created_at DESC"
            
            # Execute query
            cursor.execute(query, params)
            
            # Create Document objects
            documents = []
            for row in cursor.fetchall():
                document = Document.from_db_row(row)
                
                # Add related data
                if row.get('customer_name'):
                    from app.models.customer import Customer
                    document.customer = Customer(
                        id=row.get('customer_id'),
                        name=row.get('customer_name')
                    )
                
                if row.get('registration'):
                    from app.models.vehicle import Vehicle
                    document.vehicle = Vehicle(
                        id=row.get('vehicle_id'),
                        registration=row.get('registration'),
                        make=row.get('make'),
                        model=row.get('model')
                    )
                
                documents.append(document)
            
            # Close connection
            conn.close()
            
            return documents
        
        except Exception as e:
            logger.error(f"Error getting documents: {e}")
            return []
    
    def get_document(self, document_id: int) -> Optional[Document]:
        """
        Get a document by ID.
        
        Args:
            document_id (int): Document ID
            
        Returns:
            Document: Document object, or None if not found
        """
        try:
            # Connect to database
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Get document
            cursor.execute("""
            SELECT d.id, d.customer_id, d.vehicle_id, d.document_type, d.filename, d.file_path,
                   d.created_at, d.updated_at,
                   c.name as customer_name,
                   v.registration, v.make, v.model
            FROM documents d
            LEFT JOIN customers c ON d.customer_id = c.id
            LEFT JOIN vehicles v ON d.vehicle_id = v.id
            WHERE d.id = ?
            """, (document_id,))
            
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return None
            
            # Create Document object
            document = Document.from_db_row(row)
            
            # Add related data
            if row.get('customer_name'):
                from app.models.customer import Customer
                document.customer = Customer(
                    id=row.get('customer_id'),
                    name=row.get('customer_name')
                )
            
            if row.get('registration'):
                from app.models.vehicle import Vehicle
                document.vehicle = Vehicle(
                    id=row.get('vehicle_id'),
                    registration=row.get('registration'),
                    make=row.get('make'),
                    model=row.get('model')
                )
            
            # Close connection
            conn.close()
            
            return document
        
        except Exception as e:
            logger.error(f"Error getting document: {e}")
            return None
    
    def save_document(self, file, customer_id: int = None, vehicle_id: int = None, 
                     document_type: str = "") -> Optional[Document]:
        """
        Save a document to the database and file system.
        
        Args:
            file: File object from request.files
            customer_id (int): Customer ID
            vehicle_id (int): Vehicle ID
            document_type (str): Document type
            
        Returns:
            Document: Document object, or None if error
        """
        try:
            # Validate input
            if not file or not file.filename:
                logger.error("No file provided")
                return None
            
            if not document_type:
                logger.error("No document type provided")
                return None
            
            if not customer_id and not vehicle_id:
                logger.error("No customer or vehicle ID provided")
                return None
            
            # Secure filename
            filename = secure_filename(file.filename)
            
            # Create unique filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            
            # Create customer/vehicle subdirectory
            if customer_id:
                upload_dir = os.path.join(self.document_dir, f"customer_{customer_id}")
            else:
                upload_dir = os.path.join(self.document_dir, f"vehicle_{vehicle_id}")
            
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
            
            # Save file
            file_path = os.path.join(upload_dir, unique_filename)
            file.save(file_path)
            
            # Connect to database
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Add document to database
            cursor.execute("""
            INSERT INTO documents (
                customer_id, vehicle_id, document_type, filename, file_path, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                customer_id if customer_id else None,
                vehicle_id if vehicle_id else None,
                document_type,
                filename,
                file_path,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            # Get document ID
            document_id = cursor.lastrowid
            
            # Commit changes
            conn.commit()
            
            # Get the created document
            document = self.get_document(document_id)
            
            # Close connection
            conn.close()
            
            return document
        
        except Exception as e:
            logger.error(f"Error saving document: {e}")
            return None
    
    def delete_document(self, document_id: int) -> bool:
        """
        Delete a document from the database and file system.
        
        Args:
            document_id (int): Document ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get document
            document = self.get_document(document_id)
            
            if not document:
                logger.error(f"Document not found: {document_id}")
                return False
            
            # Delete file if it exists
            if document.file_exists:
                os.remove(document.file_path)
            
            # Connect to database
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Delete document from database
            cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            
            # Commit changes
            conn.commit()
            conn.close()
            
            return True
        
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False
    
    def get_document_types(self) -> List[str]:
        """
        Get list of document types.
        
        Returns:
            list: List of document types
        """
        return [
            'MOT Certificate',
            'Service Record',
            'Invoice',
            'Insurance',
            'Tax',
            'V5C',
            'Other'
        ]
