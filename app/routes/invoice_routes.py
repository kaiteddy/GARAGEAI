#!/usr/bin/env python3
"""
Invoice Routes Module

This module handles routes related to invoice management.
"""

import os
import csv
import io
import logging
from datetime import datetime, timedelta
from flask import render_template, redirect, url_for, flash, request, Response, jsonify

from app import app
from app.utils.database import get_db_connection

logger = logging.getLogger(__name__)

# Get database path from app config
db_path = app.config.get('DATABASE_PATH', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'garage_system.db'))

@app.route('/invoices')
def invoices():
    """Invoices page"""
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Get invoices with customer and vehicle info
        cursor.execute("""
        SELECT i.id, i.invoice_number, i.invoice_date, i.due_date, i.total_amount, i.status, i.notes,
               c.id as customer_id, c.name as customer_name,
               v.id as vehicle_id, v.registration
        FROM invoices i
        LEFT JOIN customers c ON i.customer_id = c.id
        LEFT JOIN vehicles v ON i.vehicle_id = v.id
        ORDER BY i.invoice_date DESC
        """)
        
        invoices_data = cursor.fetchall()
        
        # Get total counts for statistics
        cursor.execute("""
        SELECT 
            COUNT(*) as total_invoices,
            COUNT(CASE WHEN status = 'Paid' THEN 1 END) as paid_invoices,
            COUNT(CASE WHEN status = 'Unpaid' THEN 1 END) as unpaid_invoices,
            COUNT(CASE WHEN status = 'Overdue' THEN 1 END) as overdue_invoices,
            SUM(total_amount) as total_amount,
            SUM(CASE WHEN status = 'Unpaid' OR status = 'Overdue' THEN total_amount ELSE 0 END) as outstanding_amount
        FROM invoices
        """)
        
        stats = cursor.fetchone()
        
        # Close connection
        conn.close()
        
        return render_template('invoices.html', 
                               invoices=invoices_data, 
                               stats=stats,
                               now=datetime.now())
    
    except Exception as e:
        logger.error(f"Error displaying invoices: {e}")
        flash(f'Error displaying invoices: {e}', 'danger')
        return redirect(url_for('index'))

@app.route('/invoices/<int:invoice_id>')
def invoice_detail(invoice_id):
    """Display invoice details"""
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Get invoice
        cursor.execute("""
        SELECT i.id, i.invoice_number, i.invoice_date, i.due_date, i.total_amount, i.status, i.notes,
               c.id as customer_id, c.name as customer_name, c.email, c.phone, c.address,
               v.id as vehicle_id, v.registration, v.make, v.model, v.year
        FROM invoices i
        LEFT JOIN customers c ON i.customer_id = c.id
        LEFT JOIN vehicles v ON i.vehicle_id = v.id
        WHERE i.id = ?
        """, (invoice_id,))
        
        invoice = cursor.fetchone()
        
        if not invoice:
            flash('Invoice not found', 'danger')
            return redirect(url_for('invoices'))
        
        # Get invoice items
        cursor.execute("""
        SELECT id, description, quantity, unit_price, tax_rate
        FROM invoice_items
        WHERE invoice_id = ?
        ORDER BY id
        """, (invoice_id,))
        
        items = cursor.fetchall()
        
        # Close connection
        conn.close()
        
        # Calculate totals
        subtotal = 0
        tax_total = 0
        
        for item in items:
            item_total = item['quantity'] * item['unit_price']
            item_tax = item_total * (item['tax_rate'] / 100)
            
            subtotal += item_total
            tax_total += item_tax
        
        total = subtotal + tax_total
        
        return render_template('invoice_detail.html', 
                               invoice=invoice, 
                               items=items,
                               subtotal=subtotal,
                               tax_total=tax_total,
                               total=total)
    
    except Exception as e:
        logger.error(f"Error displaying invoice details: {e}")
        flash(f'Error displaying invoice details: {e}', 'danger')
        return redirect(url_for('invoices'))

@app.route('/invoices/create', methods=['GET', 'POST'])
def create_invoice():
    """Create a new invoice"""
    if request.method == 'POST':
        try:
            # Get form data
            customer_id = request.form.get('customer_id')
            vehicle_id = request.form.get('vehicle_id')
            invoice_date = request.form.get('invoice_date')
            due_date = request.form.get('due_date')
            notes = request.form.get('notes')
            
            # Validate data
            if not customer_id or not vehicle_id or not invoice_date or not due_date:
                flash('Please fill in all required fields', 'danger')
                return redirect(url_for('create_invoice'))
            
            # Connect to database
            conn = get_db_connection(db_path)
            cursor = conn.cursor()
            
            # Generate invoice number
            cursor.execute("SELECT COUNT(*) as count FROM invoices")
            count = cursor.fetchone()['count']
            invoice_number = f"INV-{datetime.now().strftime('%Y%m')}-{count + 1:04d}"
            
            # Create invoice
            cursor.execute("""
            INSERT INTO invoices (
                customer_id, vehicle_id, invoice_number, invoice_date, due_date, 
                total_amount, status, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 0, 'Unpaid', ?, ?, ?)
            """, (
                customer_id, vehicle_id, invoice_number, invoice_date, due_date, 
                notes, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            invoice_id = cursor.lastrowid
            
            # Commit changes
            conn.commit()
            conn.close()
            
            flash('Invoice created successfully', 'success')
            return redirect(url_for('invoice_detail', invoice_id=invoice_id))
        
        except Exception as e:
            logger.error(f"Error creating invoice: {e}")
            flash(f'Error creating invoice: {e}', 'danger')
            return redirect(url_for('create_invoice'))
    
    # GET request
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Get customers
        cursor.execute("""
        SELECT id, name
        FROM customers
        ORDER BY name
        """)
        
        customers = cursor.fetchall()
        
        # Get vehicles
        cursor.execute("""
        SELECT v.id, v.registration, v.make, v.model,
               c.id as customer_id, c.name as customer_name
        FROM vehicles v
        LEFT JOIN customers c ON v.customer_id = c.id
        ORDER BY v.registration
        """)
        
        vehicles = cursor.fetchall()
        
        # Close connection
        conn.close()
        
        return render_template('create_invoice.html', 
                               customers=customers,
                               vehicles=vehicles,
                               today=datetime.now().strftime('%Y-%m-%d'),
                               due_date=(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'))
    
    except Exception as e:
        logger.error(f"Error loading create invoice form: {e}")
        flash(f'Error loading create invoice form: {e}', 'danger')
        return redirect(url_for('invoices'))

@app.route('/invoices/add_item/<int:invoice_id>', methods=['POST'])
def add_invoice_item(invoice_id):
    """Add an item to an invoice"""
    try:
        # Get form data
        description = request.form.get('description')
        quantity = request.form.get('quantity')
        unit_price = request.form.get('unit_price')
        tax_rate = request.form.get('tax_rate')
        
        # Validate data
        if not description or not quantity or not unit_price:
            flash('Please fill in all required fields', 'danger')
            return redirect(url_for('invoice_detail', invoice_id=invoice_id))
        
        # Convert numeric values
        try:
            quantity = int(quantity)
            unit_price = float(unit_price)
            tax_rate = float(tax_rate) if tax_rate else 20.0  # Default UK VAT rate
        except ValueError:
            flash('Invalid numeric values', 'danger')
            return redirect(url_for('invoice_detail', invoice_id=invoice_id))
        
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Check if invoice exists
        cursor.execute("SELECT id FROM invoices WHERE id = ?", (invoice_id,))
        if not cursor.fetchone():
            flash('Invoice not found', 'danger')
            conn.close()
            return redirect(url_for('invoices'))
        
        # Add invoice item
        cursor.execute("""
        INSERT INTO invoice_items (
            invoice_id, description, quantity, unit_price, tax_rate, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            invoice_id, description, quantity, unit_price, tax_rate,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'), datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        # Update invoice total
        cursor.execute("""
        UPDATE invoices
        SET total_amount = (
            SELECT SUM(quantity * unit_price * (1 + tax_rate / 100))
            FROM invoice_items
            WHERE invoice_id = ?
        ),
        updated_at = ?
        WHERE id = ?
        """, (invoice_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), invoice_id))
        
        # Commit changes
        conn.commit()
        conn.close()
        
        flash('Invoice item added successfully', 'success')
        return redirect(url_for('invoice_detail', invoice_id=invoice_id))
    
    except Exception as e:
        logger.error(f"Error adding invoice item: {e}")
        flash(f'Error adding invoice item: {e}', 'danger')
        return redirect(url_for('invoice_detail', invoice_id=invoice_id))

@app.route('/invoices/update_status/<int:invoice_id>/<status>')
def update_invoice_status(invoice_id, status):
    """Update invoice status"""
    try:
        # Validate status
        valid_statuses = ['Paid', 'Unpaid', 'Overdue', 'Cancelled']
        if status not in valid_statuses:
            flash(f'Invalid status. Must be one of: {", ".join(valid_statuses)}', 'danger')
            return redirect(url_for('invoice_detail', invoice_id=invoice_id))
        
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Check if invoice exists
        cursor.execute("SELECT id FROM invoices WHERE id = ?", (invoice_id,))
        if not cursor.fetchone():
            flash('Invoice not found', 'danger')
            conn.close()
            return redirect(url_for('invoices'))
        
        # Update invoice status
        cursor.execute("""
        UPDATE invoices
        SET status = ?, updated_at = ?
        WHERE id = ?
        """, (status, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), invoice_id))
        
        # Commit changes
        conn.commit()
        conn.close()
        
        flash(f'Invoice status updated to {status}', 'success')
        return redirect(url_for('invoice_detail', invoice_id=invoice_id))
    
    except Exception as e:
        logger.error(f"Error updating invoice status: {e}")
        flash(f'Error updating invoice status: {e}', 'danger')
        return redirect(url_for('invoice_detail', invoice_id=invoice_id))

@app.route('/invoices/export')
def export_invoices():
    """Export invoices to CSV file"""
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Get all invoices
        cursor.execute("""
        SELECT i.invoice_number, i.invoice_date, i.due_date, i.total_amount, i.status,
               c.name as customer_name, v.registration
        FROM invoices i
        LEFT JOIN customers c ON i.customer_id = c.id
        LEFT JOIN vehicles v ON i.vehicle_id = v.id
        ORDER BY i.invoice_date DESC
        """)
        
        invoices = cursor.fetchall()
        
        # Close connection
        conn.close()
        
        # Create CSV file
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Invoice Number', 'Date', 'Due Date', 'Amount', 'Status', 'Customer', 'Vehicle'])
        
        # Write data
        for invoice in invoices:
            writer.writerow([
                invoice['invoice_number'],
                invoice['invoice_date'],
                invoice['due_date'],
                invoice['total_amount'],
                invoice['status'],
                invoice['customer_name'],
                invoice['registration']
            ])
        
        # Prepare response
        output.seek(0)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        return Response(
            output,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment;filename=invoices_export_{timestamp}.csv'}
        )
    
    except Exception as e:
        logger.error(f"Error exporting invoices: {e}")
        flash(f'Error exporting invoices: {e}', 'danger')
        return redirect(url_for('invoices'))
