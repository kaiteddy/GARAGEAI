#!/usr/bin/env python3
"""
Customer Routes Module

This module handles routes related to customer management.
"""

import os
import csv
import io
import logging
import tempfile
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import render_template, redirect, url_for, flash, request, Response

from app import app
from app.utils.database import get_db_connection

logger = logging.getLogger(__name__)

# Get database path from app config
db_path = app.config.get('DATABASE_PATH', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'garage_system.db'))

@app.route('/customers')
def customers():
    """Customers page"""
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        # Get customers with vehicle count
        cursor.execute("""
        SELECT c.id, c.name as full_name, c.phone, c.email, c.address,
               COUNT(v.id) as vehicle_count
        FROM customers c
        LEFT JOIN vehicles v ON c.id = v.customer_id
        GROUP BY c.id
        ORDER BY c.name
        """)

        customers_data = cursor.fetchall()

        # Get total counts for statistics
        cursor.execute("""
        SELECT
            COUNT(*) as total_customers,
            (SELECT COUNT(DISTINCT customer_id) FROM vehicles) as active_customers,
            (SELECT COUNT(*) FROM vehicles) as total_vehicles
        FROM customers
        """)

        stats = cursor.fetchone()

        # Close connection
        conn.close()

        # Format customers for template
        customers = []
        for customer in customers_data:
            # Split full name into first and last name for display
            name_parts = customer['full_name'].split(' ', 1) if customer['full_name'] else ['', '']
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''

            customers.append({
                'id': customer['id'],
                'first_name': first_name,
                'last_name': last_name,
                'full_name': customer['full_name'],  # Use the actual name from the database
                'name': customer['full_name'],  # Add name field for compatibility
                'phone': customer['phone'],
                'email': customer['email'],
                'address': customer['address'],
                'vehicle_count': customer['vehicle_count']
            })

        return render_template('customers.html',
                               customers=customers,
                               stats=stats,
                               page=1,
                               total_pages=1,
                               now=datetime.now())

    except Exception as e:
        logger.error(f"Error displaying customers: {e}")
        flash(f'Error displaying customers: {e}', 'danger')
        return redirect(url_for('index'))

@app.route('/customers/<int:customer_id>')
def customer_detail(customer_id):
    """Display customer details"""
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        # Get customer
        cursor.execute("""
        SELECT c.id, c.name as full_name, c.email, c.phone, c.address, c.created_at, c.updated_at
        FROM customers c
        WHERE c.id = ?
        """, (customer_id,))

        customer_data = cursor.fetchone()

        if not customer_data:
            flash('Customer not found', 'danger')
            return redirect(url_for('customers'))

        # Format customer for template
        name_parts = customer_data['full_name'].split(' ', 1) if customer_data['full_name'] else ['', '']
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        customer = dict(customer_data)
        customer['first_name'] = first_name
        customer['last_name'] = last_name
        customer['name'] = customer_data['full_name']  # Add name field for compatibility

        # Get vehicles
        cursor.execute("""
        SELECT v.id, v.registration, v.make, v.model, v.year, v.color, v.mot_expiry, v.mot_status
        FROM vehicles v
        WHERE v.customer_id = ?
        ORDER BY v.registration
        """, (customer_id,))

        vehicles = cursor.fetchall()

        # Get appointments
        cursor.execute("""
        SELECT a.id, a.appointment_date, a.appointment_time, a.appointment_type, a.status,
               v.id as vehicle_id, v.registration, v.make, v.model
        FROM appointments a
        JOIN vehicles v ON a.vehicle_id = v.id
        WHERE v.customer_id = ?
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
        LIMIT 5
        """, (customer_id,))

        appointments = cursor.fetchall()

        # Get invoices
        cursor.execute("""
        SELECT i.id, i.invoice_number, i.invoice_date, i.total_amount, i.status,
               v.id as vehicle_id, v.registration
        FROM invoices i
        JOIN vehicles v ON i.vehicle_id = v.id
        WHERE i.customer_id = ?
        ORDER BY i.invoice_date DESC
        LIMIT 5
        """, (customer_id,))

        invoices = cursor.fetchall()

        # Get documents
        cursor.execute("""
        SELECT d.id, d.filename, d.document_type, d.uploaded_at, d.file_path,
               d.vehicle_id, v.registration
        FROM documents d
        LEFT JOIN vehicles v ON d.vehicle_id = v.id
        WHERE d.customer_id = ? OR v.customer_id = ?
        ORDER BY d.uploaded_at DESC
        LIMIT 5
        """, (customer_id, customer_id))

        documents = cursor.fetchall()

        # Get reminders
        cursor.execute("""
        SELECT r.id, r.reminder_type, r.due_date, r.status, r.notes,
               v.id as vehicle_id, v.registration, v.make, v.model,
               CASE
                   WHEN date(r.due_date) < date('now') THEN 1
                   WHEN date(r.due_date) <= date('now', '+30 days') THEN 2
                   ELSE 0
               END as priority
        FROM reminders r
        JOIN vehicles v ON r.vehicle_id = v.id
        WHERE v.customer_id = ?
        ORDER BY priority DESC, r.due_date ASC
        LIMIT 5
        """, (customer_id,))

        reminders_data = cursor.fetchall()

        # Process reminders to add is_overdue and is_due_soon flags
        reminders = []
        for reminder in reminders_data:
            reminder_dict = dict(reminder)
            reminder_dict['is_overdue'] = reminder['priority'] == 1
            reminder_dict['is_due_soon'] = reminder['priority'] == 2
            reminders.append(reminder_dict)

        # Close connection
        conn.close()

        return render_template('customer_detail.html',
                               customer=customer,
                               vehicles=vehicles,
                               appointments=appointments,
                               invoices=invoices,
                               documents=documents,
                               reminders=reminders)

    except Exception as e:
        logger.error(f"Error displaying customer details: {e}")
        flash(f'Error displaying customer details: {e}', 'danger')
        return redirect(url_for('customers'))

@app.route('/customers/new')
def new_customer():
    """Display form to create a new customer"""
    return render_template('create_customer.html')

@app.route('/customers/create', methods=['POST'])
def create_customer():
    """Create a new customer"""
    try:
        # Get form data
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        address = request.form.get('address', '')
        city = request.form.get('city', '')
        postal_code = request.form.get('postal_code', '')
        notes = request.form.get('notes', '')

        # Combine address components
        full_address = address
        if city:
            full_address += f", {city}"
        if postal_code:
            full_address += f", {postal_code}"

        # Combine name components
        full_name = f"{first_name} {last_name}".strip()

        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        # Insert customer
        cursor.execute("""
        INSERT INTO customers (name, email, phone, address)
        VALUES (?, ?, ?, ?)
        """, (full_name, email, phone, full_address))

        # Get customer ID
        customer_id = cursor.lastrowid

        # Commit changes
        conn.commit()

        # Close connection
        conn.close()

        flash('Customer created successfully', 'success')
        return redirect(url_for('customer_detail', customer_id=customer_id))

    except Exception as e:
        logger.error(f"Error creating customer: {e}")
        flash(f'Error creating customer: {e}', 'danger')
        return redirect(url_for('customers'))

@app.route('/customers/export')
def export_customers():
    """Export customers to CSV file"""
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        # Get all customers
        cursor.execute("""
        SELECT name, email, phone, address
        FROM customers
        ORDER BY name
        """)

        customers = cursor.fetchall()

        # Close connection
        conn.close()

        # Create CSV file
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(['Name', 'Email', 'Phone', 'Address'])

        # Write data
        for customer in customers:
            writer.writerow([
                customer['name'],
                customer['email'],
                customer['phone'],
                customer['address']
            ])

        # Prepare response
        output.seek(0)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        return Response(
            output,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment;filename=customers_export_{timestamp}.csv'}
        )

    except Exception as e:
        logger.error(f"Error exporting customers: {e}")
        flash(f'Error exporting customers: {e}', 'danger')
        return redirect(url_for('customers'))
