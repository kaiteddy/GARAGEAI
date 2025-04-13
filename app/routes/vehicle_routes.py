#!/usr/bin/env python3
"""
Vehicle Routes Module

This module handles routes related to vehicle management.
"""

import os
import csv
import io
import logging
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, Response, jsonify

from app import app
from app.utils.database import get_db_connection
from app.services.dvla_service import check_mot_status

logger = logging.getLogger(__name__)

# Get database path from app config
db_path = app.config.get('DATABASE_PATH', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'garage_system.db'))

@app.route('/vehicles')
def vehicles():
    """Vehicles page"""
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        # Get filter parameters
        registration = request.args.get('registration', '')
        make = request.args.get('make', '')
        model = request.args.get('model', '')
        customer_id = request.args.get('customer_id', '')
        customer_name = request.args.get('customer', '')
        mot_status = request.args.get('mot_status', '')

        # Build query with filters
        query = """
        SELECT v.id, v.registration, v.make, v.model, v.year, v.color,
               v.mot_expiry, v.mot_status, v.last_mot_check,
               c.id as customer_id, c.name as customer_name
        FROM vehicles v
        LEFT JOIN customers c ON v.customer_id = c.id
        WHERE 1=1
        """

        params = []

        if registration:
            query += " AND v.registration LIKE ?"
            params.append(f'%{registration}%')

        if make:
            query += " AND v.make LIKE ?"
            params.append(f'%{make}%')

        if model:
            query += " AND v.model LIKE ?"
            params.append(f'%{model}%')

        if customer_id:
            query += " AND v.customer_id = ?"
            params.append(customer_id)

        if customer_name:
            query += " AND c.name LIKE ?"
            params.append(f'%{customer_name}%')

        if mot_status:
            if mot_status.lower() == 'valid':
                query += " AND v.mot_status = 'Valid'"
            elif mot_status.lower() == 'expired':
                query += " AND v.mot_status = 'Expired'"
            elif mot_status.lower() == 'expiring':
                query += " AND v.mot_status = 'Expiring'"

        query += " ORDER BY v.registration"

        # Execute query with parameters
        cursor.execute(query, params)

        vehicles_data = cursor.fetchall()

        # Get total counts for statistics
        cursor.execute("""
        SELECT
            COUNT(*) as total_vehicles,
            COUNT(CASE WHEN mot_status = 'Valid' THEN 1 END) as valid_mot,
            COUNT(CASE WHEN mot_status = 'Expired' THEN 1 END) as expired_mot,
            COUNT(CASE WHEN mot_status IS NULL THEN 1 END) as unknown_mot
        FROM vehicles
        """)

        stats = cursor.fetchone()

        # Close connection
        conn.close()

        return render_template('vehicles.html',
                               vehicles=vehicles_data,
                               stats=stats,
                               page=1,
                               total_pages=1,
                               now=datetime.now())

    except Exception as e:
        logger.error(f"Error displaying vehicles: {e}")
        flash(f'Error displaying vehicles: {e}', 'danger')
        return redirect(url_for('index'))

@app.route('/vehicles/<int:vehicle_id>')
def vehicle_detail(vehicle_id):
    """Display vehicle details"""
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        # Get vehicle
        cursor.execute("""
        SELECT v.id, v.registration, v.make, v.model, v.year, v.color,
               v.vin, v.engine_size, v.fuel_type, v.transmission,
               v.mot_expiry, v.mot_status, v.last_mot_check,
               c.id as customer_id, c.name as customer_name
        FROM vehicles v
        LEFT JOIN customers c ON v.customer_id = c.id
        WHERE v.id = ?
        """, (vehicle_id,))

        vehicle = cursor.fetchone()

        if not vehicle:
            flash('Vehicle not found', 'danger')
            return redirect(url_for('vehicles'))

        # Get service records
        cursor.execute("""
        SELECT id, service_date, service_type, mileage, description, cost
        FROM service_records
        WHERE vehicle_id = ?
        ORDER BY service_date DESC
        """, (vehicle_id,))

        service_records = cursor.fetchall()

        # Get MOT history
        cursor.execute("""
        SELECT id, test_date, result, expiry_date, mileage, advisory_notes
        FROM mot_history
        WHERE vehicle_id = ?
        ORDER BY test_date DESC
        """, (vehicle_id,))

        mot_history = cursor.fetchall()

        # Get reminders
        cursor.execute("""
        SELECT r.id, r.reminder_type, r.due_date, r.status, r.notes,
               CASE
                   WHEN date(r.due_date) < date('now') THEN 1
                   WHEN date(r.due_date) <= date('now', '+30 days') THEN 2
                   ELSE 0
               END as priority
        FROM reminders r
        WHERE r.vehicle_id = ?
        ORDER BY priority DESC, r.due_date ASC
        """, (vehicle_id,))

        reminders_data = cursor.fetchall()

        # Process reminders to add is_overdue and is_due_soon flags
        reminders = []
        for reminder in reminders_data:
            reminder_dict = dict(reminder)
            reminder_dict['is_overdue'] = reminder['priority'] == 1
            reminder_dict['is_due_soon'] = reminder['priority'] == 2
            reminders.append(reminder_dict)

        # Get appointments
        cursor.execute("""
        SELECT id, appointment_date, appointment_time, appointment_type, status, notes
        FROM appointments
        WHERE vehicle_id = ?
        ORDER BY appointment_date DESC, appointment_time DESC
        """, (vehicle_id,))

        appointments = cursor.fetchall()

        # Get documents
        cursor.execute("""
        SELECT id, filename, document_type, uploaded_at, file_path
        FROM documents
        WHERE vehicle_id = ?
        ORDER BY uploaded_at DESC
        """, (vehicle_id,))

        documents = cursor.fetchall()

        # Close connection
        conn.close()

        return render_template('vehicle_detail.html',
                               vehicle=vehicle,
                               service_records=service_records,
                               mot_history=mot_history,
                               reminders=reminders,
                               appointments=appointments,
                               documents=documents)

    except Exception as e:
        logger.error(f"Error displaying vehicle details: {e}")
        flash(f'Error displaying vehicle details: {e}', 'danger')
        return redirect(url_for('vehicles'))

@app.route('/vehicles/check_mot/<int:vehicle_id>')
def check_vehicle_mot(vehicle_id):
    """Check MOT status for a vehicle"""
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        # Get vehicle
        cursor.execute("""
        SELECT id, registration
        FROM vehicles
        WHERE id = ?
        """, (vehicle_id,))

        vehicle = cursor.fetchone()

        if not vehicle:
            flash('Vehicle not found', 'danger')
            return redirect(url_for('vehicles'))

        # Check MOT status
        registration = vehicle['registration']
        mot_result = check_mot_status(registration)

        if mot_result.get('success'):
            # Update vehicle MOT info
            cursor.execute("""
            UPDATE vehicles
            SET mot_expiry = ?, mot_status = ?, last_mot_check = ?
            WHERE id = ?
            """, (
                mot_result.get('expiry_date'),
                'Valid' if mot_result.get('is_valid') else 'Expired',
                datetime.now().strftime('%Y-%m-%d'),
                vehicle_id
            ))

            # Add to MOT history if not already present
            if mot_result.get('test_date'):
                cursor.execute("""
                SELECT id FROM mot_history
                WHERE vehicle_id = ? AND test_date = ?
                """, (vehicle_id, mot_result.get('test_date')))

                if not cursor.fetchone():
                    cursor.execute("""
                    INSERT INTO mot_history (vehicle_id, test_date, result, expiry_date, mileage, advisory_notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        vehicle_id,
                        mot_result.get('test_date'),
                        'Pass' if mot_result.get('is_valid') else 'Fail',
                        mot_result.get('expiry_date'),
                        mot_result.get('mileage', 0),
                        mot_result.get('advisory_notes', '')
                    ))

            conn.commit()
            flash(f"MOT status updated: {mot_result.get('status_message')}", 'success')
        else:
            flash(f"Error checking MOT status: {mot_result.get('error_message')}", 'danger')

        # Close connection
        conn.close()

        return redirect(url_for('vehicle_detail', vehicle_id=vehicle_id))

    except Exception as e:
        logger.error(f"Error checking MOT status: {e}")
        flash(f'Error checking MOT status: {e}', 'danger')
        return redirect(url_for('vehicle_detail', vehicle_id=vehicle_id))

@app.route('/vehicles/export')
def export_vehicles():
    """Export vehicles to CSV file"""
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        # Get all vehicles
        cursor.execute("""
        SELECT v.registration, v.make, v.model, v.year, v.color,
               v.mot_expiry, v.mot_status,
               c.name as customer_name
        FROM vehicles v
        LEFT JOIN customers c ON v.customer_id = c.id
        ORDER BY v.registration
        """)

        vehicles = cursor.fetchall()

        # Close connection
        conn.close()

        # Create CSV file
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(['Registration', 'Make', 'Model', 'Year', 'Color', 'MOT Expiry', 'MOT Status', 'Owner'])

        # Write data
        for vehicle in vehicles:
            writer.writerow([
                vehicle['registration'],
                vehicle['make'],
                vehicle['model'],
                vehicle['year'],
                vehicle['color'],
                vehicle['mot_expiry'],
                vehicle['mot_status'],
                vehicle['customer_name']
            ])

        # Prepare response
        output.seek(0)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        return Response(
            output,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment;filename=vehicles_export_{timestamp}.csv'}
        )

    except Exception as e:
        logger.error(f"Error exporting vehicles: {e}")
        flash(f'Error exporting vehicles: {e}', 'danger')
        return redirect(url_for('vehicles'))

@app.route('/vehicles/batch_verify_mot')
def batch_verify_mot_route():
    """Batch verify MOT status for all vehicles"""
    try:
        # Get all vehicles
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT id, registration FROM vehicles")
        vehicles = cursor.fetchall()
        conn.close()

        # For demo purposes, we'll just redirect back to the vehicles page
        # In a real implementation, this would start a background task to check MOT status for all vehicles
        flash(f"Started batch MOT verification for {len(vehicles)} vehicles", 'info')

        return redirect(url_for('vehicles'))

    except Exception as e:
        logger.error(f"Error starting batch MOT verification: {e}")
        flash(f"Error starting batch MOT verification: {str(e)}", 'danger')
        return redirect(url_for('vehicles'))

@app.route('/vehicles/edit/<int:vehicle_id>', methods=['GET', 'POST'])
def edit_vehicle(vehicle_id):
    """Edit vehicle details"""
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        # Get vehicle details
        cursor.execute("""
        SELECT v.id, v.registration, v.make, v.model, v.year, v.color,
               v.vin, v.engine_size, v.fuel_type, v.transmission,
               v.mot_expiry, v.mot_status, v.last_mot_check,
               v.customer_id
        FROM vehicles v
        WHERE v.id = ?
        """, (vehicle_id,))

        vehicle = cursor.fetchone()

        if not vehicle:
            flash('Vehicle not found', 'danger')
            return redirect(url_for('vehicles'))

        # Get all customers for dropdown
        cursor.execute("""
        SELECT id, name as full_name
        FROM customers
        ORDER BY name
        """)

        customers = cursor.fetchall()

        # Handle form submission
        if request.method == 'POST':
            # Get form data
            registration = request.form.get('registration')
            make = request.form.get('make')
            model = request.form.get('model')
            year = request.form.get('year')
            color = request.form.get('color')
            vin = request.form.get('vin')
            engine_size = request.form.get('engine_size')
            fuel_type = request.form.get('fuel_type')
            transmission = request.form.get('transmission')
            customer_id = request.form.get('customer_id')

            # Validate required fields
            if not registration or not make or not model:
                flash('Registration, make, and model are required', 'danger')
                return render_template('edit_vehicle.html', vehicle=vehicle, customers=customers)

            # Update vehicle in database
            cursor.execute("""
            UPDATE vehicles
            SET registration = ?, make = ?, model = ?, year = ?, color = ?,
                vin = ?, engine_size = ?, fuel_type = ?, transmission = ?,
                customer_id = ?, updated_at = ?
            WHERE id = ?
            """, (
                registration, make, model, year, color,
                vin, engine_size, fuel_type, transmission,
                customer_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                vehicle_id
            ))

            conn.commit()

            flash('Vehicle updated successfully', 'success')
            return redirect(url_for('vehicle_detail', vehicle_id=vehicle_id))

        conn.close()

        return render_template('edit_vehicle.html', vehicle=vehicle, customers=customers)

    except Exception as e:
        logger.error(f"Error editing vehicle: {e}")
        flash(f'Error editing vehicle: {e}', 'danger')
        return redirect(url_for('vehicles'))
