#!/usr/bin/env python3
"""
Invoice Service Module

This module provides services for invoice management.
"""

import os
import csv
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

from app.utils.database import get_db_connection
from app.models.invoice import Invoice, InvoiceItem

logger = logging.getLogger(__name__)

class InvoiceService:
    """Invoice service class"""
    
    def __init__(self, db_path: str):
        """
        Initialize the invoice service.
        
        Args:
            db_path (str): Path to the database file
        """
        self.db_path = db_path
    
    def get_invoices(self, status: str = None, customer_id: int = None, 
                    vehicle_id: int = None, date_from: str = None, 
                    date_to: str = None) -> List[Invoice]:
        """
        Get invoices from the database.
        
        Args:
            status (str): Filter by status
            customer_id (int): Filter by customer ID
            vehicle_id (int): Filter by vehicle ID
            date_from (str): Filter by date from
            date_to (str): Filter by date to
            
        Returns:
            list: List of Invoice objects
        """
        try:
            # Connect to database
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Build query
            query = """
            SELECT i.id, i.customer_id, i.vehicle_id, i.invoice_date, i.due_date, 
                   i.status, i.notes, i.created_at, i.updated_at,
                   c.name as customer_name, c.email as customer_email, c.phone as customer_phone,
                   v.registration, v.make, v.model
            FROM invoices i
            LEFT JOIN customers c ON i.customer_id = c.id
            LEFT JOIN vehicles v ON i.vehicle_id = v.id
            """
            
            # Add filters
            params = []
            conditions = []
            
            if status:
                conditions.append("i.status = ?")
                params.append(status)
            
            if customer_id:
                conditions.append("i.customer_id = ?")
                params.append(customer_id)
            
            if vehicle_id:
                conditions.append("i.vehicle_id = ?")
                params.append(vehicle_id)
            
            if date_from:
                conditions.append("i.invoice_date >= ?")
                params.append(date_from)
            
            if date_to:
                conditions.append("i.invoice_date <= ?")
                params.append(date_to)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            # Add order by
            query += " ORDER BY i.invoice_date DESC"
            
            # Execute query
            cursor.execute(query, params)
            
            # Create Invoice objects
            invoices = []
            for row in cursor.fetchall():
                invoice = Invoice.from_db_row(row)
                
                # Add related data
                if row.get('customer_name'):
                    from app.models.customer import Customer
                    invoice.customer = Customer(
                        id=row.get('customer_id'),
                        name=row.get('customer_name'),
                        email=row.get('customer_email'),
                        phone=row.get('customer_phone')
                    )
                
                if row.get('registration'):
                    from app.models.vehicle import Vehicle
                    invoice.vehicle = Vehicle(
                        id=row.get('vehicle_id'),
                        registration=row.get('registration'),
                        make=row.get('make'),
                        model=row.get('model')
                    )
                
                # Get invoice items
                cursor.execute("""
                SELECT id, invoice_id, description, quantity, unit_price, tax_rate, 
                       created_at, updated_at
                FROM invoice_items
                WHERE invoice_id = ?
                ORDER BY id
                """, (invoice.id,))
                
                for item_row in cursor.fetchall():
                    item = InvoiceItem.from_db_row(item_row)
                    invoice.items.append(item)
                
                invoices.append(invoice)
            
            # Close connection
            conn.close()
            
            return invoices
        
        except Exception as e:
            logger.error(f"Error getting invoices: {e}")
            return []
    
    def get_invoice(self, invoice_id: int) -> Optional[Invoice]:
        """
        Get an invoice by ID.
        
        Args:
            invoice_id (int): Invoice ID
            
        Returns:
            Invoice: Invoice object, or None if not found
        """
        try:
            # Connect to database
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Get invoice
            cursor.execute("""
            SELECT i.id, i.customer_id, i.vehicle_id, i.invoice_date, i.due_date, 
                   i.status, i.notes, i.created_at, i.updated_at,
                   c.name as customer_name, c.email as customer_email, 
                   c.phone as customer_phone, c.address as customer_address,
                   v.registration, v.make, v.model, v.year, v.vin
            FROM invoices i
            LEFT JOIN customers c ON i.customer_id = c.id
            LEFT JOIN vehicles v ON i.vehicle_id = v.id
            WHERE i.id = ?
            """, (invoice_id,))
            
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return None
            
            # Create Invoice object
            invoice = Invoice.from_db_row(row)
            
            # Add related data
            if row.get('customer_name'):
                from app.models.customer import Customer
                invoice.customer = Customer(
                    id=row.get('customer_id'),
                    name=row.get('customer_name'),
                    email=row.get('customer_email'),
                    phone=row.get('customer_phone'),
                    address=row.get('customer_address')
                )
            
            if row.get('registration'):
                from app.models.vehicle import Vehicle
                invoice.vehicle = Vehicle(
                    id=row.get('vehicle_id'),
                    registration=row.get('registration'),
                    make=row.get('make'),
                    model=row.get('model'),
                    year=row.get('year'),
                    vin=row.get('vin')
                )
            
            # Get invoice items
            cursor.execute("""
            SELECT id, invoice_id, description, quantity, unit_price, tax_rate, 
                   created_at, updated_at
            FROM invoice_items
            WHERE invoice_id = ?
            ORDER BY id
            """, (invoice_id,))
            
            for item_row in cursor.fetchall():
                item = InvoiceItem.from_db_row(item_row)
                invoice.items.append(item)
            
            # Close connection
            conn.close()
            
            return invoice
        
        except Exception as e:
            logger.error(f"Error getting invoice: {e}")
            return None
    
    def create_invoice(self, customer_id: int, vehicle_id: int = None, 
                      invoice_date: str = None, due_date: str = None, 
                      status: str = "Draft", notes: str = "") -> Optional[Invoice]:
        """
        Create a new invoice.
        
        Args:
            customer_id (int): Customer ID
            vehicle_id (int): Vehicle ID
            invoice_date (str): Invoice date
            due_date (str): Due date
            status (str): Invoice status
            notes (str): Additional notes
            
        Returns:
            Invoice: Created Invoice object, or None if error
        """
        try:
            # Set default dates if not provided
            if not invoice_date:
                invoice_date = datetime.now().strftime('%Y-%m-%d')
            
            if not due_date:
                due_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            
            # Connect to database
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Create invoice
            cursor.execute("""
            INSERT INTO invoices (
                customer_id, vehicle_id, invoice_date, due_date, status, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                customer_id,
                vehicle_id,
                invoice_date,
                due_date,
                status,
                notes,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            # Get invoice ID
            invoice_id = cursor.lastrowid
            
            # Commit changes
            conn.commit()
            
            # Get the created invoice
            invoice = self.get_invoice(invoice_id)
            
            # Close connection
            conn.close()
            
            return invoice
        
        except Exception as e:
            logger.error(f"Error creating invoice: {e}")
            return None
    
    def update_invoice(self, invoice_id: int, customer_id: int = None, 
                      vehicle_id: int = None, invoice_date: str = None, 
                      due_date: str = None, status: str = None, 
                      notes: str = None) -> Optional[Invoice]:
        """
        Update an existing invoice.
        
        Args:
            invoice_id (int): Invoice ID
            customer_id (int): Customer ID
            vehicle_id (int): Vehicle ID
            invoice_date (str): Invoice date
            due_date (str): Due date
            status (str): Invoice status
            notes (str): Additional notes
            
        Returns:
            Invoice: Updated Invoice object, or None if error
        """
        try:
            # Get current invoice
            current_invoice = self.get_invoice(invoice_id)
            
            if not current_invoice:
                logger.error(f"Invoice not found: {invoice_id}")
                return None
            
            # Connect to database
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Build update query
            query = "UPDATE invoices SET updated_at = ?"
            params = [datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
            
            if customer_id is not None:
                query += ", customer_id = ?"
                params.append(customer_id)
            
            if vehicle_id is not None:
                query += ", vehicle_id = ?"
                params.append(vehicle_id)
            
            if invoice_date is not None:
                query += ", invoice_date = ?"
                params.append(invoice_date)
            
            if due_date is not None:
                query += ", due_date = ?"
                params.append(due_date)
            
            if status is not None:
                query += ", status = ?"
                params.append(status)
            
            if notes is not None:
                query += ", notes = ?"
                params.append(notes)
            
            # Add where clause
            query += " WHERE id = ?"
            params.append(invoice_id)
            
            # Execute update
            cursor.execute(query, params)
            
            # Commit changes
            conn.commit()
            
            # Get the updated invoice
            invoice = self.get_invoice(invoice_id)
            
            # Close connection
            conn.close()
            
            return invoice
        
        except Exception as e:
            logger.error(f"Error updating invoice: {e}")
            return None
    
    def delete_invoice(self, invoice_id: int) -> bool:
        """
        Delete an invoice and its items.
        
        Args:
            invoice_id (int): Invoice ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Connect to database
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Delete invoice items
            cursor.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
            
            # Delete invoice
            cursor.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
            
            # Commit changes
            conn.commit()
            conn.close()
            
            return True
        
        except Exception as e:
            logger.error(f"Error deleting invoice: {e}")
            return False
    
    def add_invoice_item(self, invoice_id: int, description: str, 
                        quantity: float, unit_price: float, 
                        tax_rate: float = 20.0) -> Optional[InvoiceItem]:
        """
        Add an item to an invoice.
        
        Args:
            invoice_id (int): Invoice ID
            description (str): Item description
            quantity (float): Item quantity
            unit_price (float): Item unit price
            tax_rate (float): Item tax rate
            
        Returns:
            InvoiceItem: Created InvoiceItem object, or None if error
        """
        try:
            # Connect to database
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Add invoice item
            cursor.execute("""
            INSERT INTO invoice_items (
                invoice_id, description, quantity, unit_price, tax_rate, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                invoice_id,
                description,
                quantity,
                unit_price,
                tax_rate,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            # Get item ID
            item_id = cursor.lastrowid
            
            # Commit changes
            conn.commit()
            
            # Get the created item
            cursor.execute("""
            SELECT id, invoice_id, description, quantity, unit_price, tax_rate, 
                   created_at, updated_at
            FROM invoice_items
            WHERE id = ?
            """, (item_id,))
            
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return None
            
            # Create InvoiceItem object
            item = InvoiceItem.from_db_row(row)
            
            # Close connection
            conn.close()
            
            return item
        
        except Exception as e:
            logger.error(f"Error adding invoice item: {e}")
            return None
    
    def update_invoice_item(self, item_id: int, description: str = None, 
                           quantity: float = None, unit_price: float = None, 
                           tax_rate: float = None) -> Optional[InvoiceItem]:
        """
        Update an invoice item.
        
        Args:
            item_id (int): Item ID
            description (str): Item description
            quantity (float): Item quantity
            unit_price (float): Item unit price
            tax_rate (float): Item tax rate
            
        Returns:
            InvoiceItem: Updated InvoiceItem object, or None if error
        """
        try:
            # Connect to database
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Build update query
            query = "UPDATE invoice_items SET updated_at = ?"
            params = [datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
            
            if description is not None:
                query += ", description = ?"
                params.append(description)
            
            if quantity is not None:
                query += ", quantity = ?"
                params.append(quantity)
            
            if unit_price is not None:
                query += ", unit_price = ?"
                params.append(unit_price)
            
            if tax_rate is not None:
                query += ", tax_rate = ?"
                params.append(tax_rate)
            
            # Add where clause
            query += " WHERE id = ?"
            params.append(item_id)
            
            # Execute update
            cursor.execute(query, params)
            
            # Commit changes
            conn.commit()
            
            # Get the updated item
            cursor.execute("""
            SELECT id, invoice_id, description, quantity, unit_price, tax_rate, 
                   created_at, updated_at
            FROM invoice_items
            WHERE id = ?
            """, (item_id,))
            
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return None
            
            # Create InvoiceItem object
            item = InvoiceItem.from_db_row(row)
            
            # Close connection
            conn.close()
            
            return item
        
        except Exception as e:
            logger.error(f"Error updating invoice item: {e}")
            return None
    
    def delete_invoice_item(self, item_id: int) -> bool:
        """
        Delete an invoice item.
        
        Args:
            item_id (int): Item ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Connect to database
            conn = get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Delete invoice item
            cursor.execute("DELETE FROM invoice_items WHERE id = ?", (item_id,))
            
            # Commit changes
            conn.commit()
            conn.close()
            
            return True
        
        except Exception as e:
            logger.error(f"Error deleting invoice item: {e}")
            return False
    
    def export_invoices_to_csv(self, output_path: str, status: str = None, 
                              date_from: str = None, date_to: str = None) -> Tuple[bool, str]:
        """
        Export invoices to CSV file.
        
        Args:
            output_path (str): Output file path
            status (str): Filter by status
            date_from (str): Filter by date from
            date_to (str): Filter by date to
            
        Returns:
            tuple: (success, message)
        """
        try:
            # Get invoices
            invoices = self.get_invoices(status=status, date_from=date_from, date_to=date_to)
            
            if not invoices:
                return False, "No invoices found matching the criteria"
            
            # Create CSV file
            with open(output_path, 'w', newline='') as csvfile:
                fieldnames = [
                    'Invoice ID', 'Date', 'Due Date', 'Status', 'Customer', 'Vehicle',
                    'Subtotal', 'Tax', 'Total', 'Notes'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for invoice in invoices:
                    writer.writerow({
                        'Invoice ID': invoice.id,
                        'Date': invoice.invoice_date,
                        'Due Date': invoice.due_date,
                        'Status': invoice.status,
                        'Customer': invoice.customer.name if invoice.customer else '',
                        'Vehicle': f"{invoice.vehicle.registration} ({invoice.vehicle.make} {invoice.vehicle.model})" if invoice.vehicle else '',
                        'Subtotal': f"£{invoice.subtotal:.2f}",
                        'Tax': f"£{invoice.tax_amount:.2f}",
                        'Total': f"£{invoice.total:.2f}",
                        'Notes': invoice.notes
                    })
            
            return True, f"Successfully exported {len(invoices)} invoices to {output_path}"
        
        except Exception as e:
            logger.error(f"Error exporting invoices to CSV: {e}")
            return False, f"Error exporting invoices: {e}"
