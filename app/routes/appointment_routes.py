#!/usr/bin/env python3
"""
Appointment Routes Module

This module handles routes related to appointment scheduling and management.
"""

import os
import logging
from datetime import datetime, timedelta
from flask import render_template, redirect, url_for, flash, request, jsonify

from app import app
from app.utils.database import get_db_connection
from app.services.appointment_service import get_available_slots, schedule_appointment, update_appointment_status

logger = logging.getLogger(__name__)

# Get database path from app config
db_path = app.config.get('DATABASE_PATH', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'garage_system.db'))

@app.route('/appointments')
def appointments():
    """Appointments page"""
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Get appointments with vehicle and customer info
        cursor.execute("""
        SELECT a.id, a.appointment_date, a.appointment_time, a.appointment_type, a.status, a.notes,
               v.id as vehicle_id, v.registration, v.make, v.model,
               c.id as customer_id, c.name as customer_name, c.phone
        FROM appointments a
        JOIN vehicles v ON a.vehicle_id = v.id
        LEFT JOIN customers c ON v.customer_id = c.id
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
        """)
        
        appointments_data = cursor.fetchall()
        
        # Get total counts for statistics
        cursor.execute("""
        SELECT 
            COUNT(*) as total_appointments,
            COUNT(CASE WHEN status = 'Scheduled' THEN 1 END) as scheduled_appointments,
            COUNT(CASE WHEN status = 'Completed' THEN 1 END) as completed_appointments,
            COUNT(CASE WHEN status = 'Cancelled' THEN 1 END) as cancelled_appointments,
            COUNT(CASE WHEN status = 'No Show' THEN 1 END) as no_show_appointments
        FROM appointments
        """)
        
        stats = cursor.fetchone()
        
        # Close connection
        conn.close()
        
        return render_template('appointments.html', 
                               appointments=appointments_data, 
                               stats=stats,
                               now=datetime.now())
    
    except Exception as e:
        logger.error(f"Error displaying appointments: {e}")
        flash(f'Error displaying appointments: {e}', 'danger')
        return redirect(url_for('index'))

@app.route('/appointments/calendar')
def appointment_calendar():
    """Appointment calendar view"""
    try:
        # Get date range from request
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Default to current week if not specified
        if not start_date:
            today = datetime.now().date()
            start_date = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')
        
        if not end_date:
            end_date = (datetime.strptime(start_date, '%Y-%m-%d').date() + timedelta(days=6)).strftime('%Y-%m-%d')
        
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Get appointments within date range
        cursor.execute("""
        SELECT a.id, a.appointment_date, a.appointment_time, a.appointment_type, a.status, a.notes,
               v.id as vehicle_id, v.registration, v.make, v.model,
               c.id as customer_id, c.name as customer_name
        FROM appointments a
        JOIN vehicles v ON a.vehicle_id = v.id
        LEFT JOIN customers c ON v.customer_id = c.id
        WHERE a.appointment_date BETWEEN ? AND ?
        ORDER BY a.appointment_date, a.appointment_time
        """, (start_date, end_date))
        
        appointments = cursor.fetchall()
        
        # Close connection
        conn.close()
        
        # Format appointments for calendar view
        calendar_data = {}
        
        for appointment in appointments:
            date = appointment['appointment_date']
            
            if date not in calendar_data:
                calendar_data[date] = []
            
            calendar_data[date].append({
                'id': appointment['id'],
                'time': appointment['appointment_time'],
                'type': appointment['appointment_type'],
                'status': appointment['status'],
                'vehicle': f"{appointment['make']} {appointment['model']} ({appointment['registration']})",
                'customer': appointment['customer_name'],
                'notes': appointment['notes']
            })
        
        # Generate date range for the calendar
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        date_range = []
        current = start
        
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            date_range.append({
                'date': date_str,
                'display': current.strftime('%a, %d %b'),
                'appointments': calendar_data.get(date_str, [])
            })
            current += timedelta(days=1)
        
        return render_template('appointment_calendar.html',
                               date_range=date_range,
                               start_date=start_date,
                               end_date=end_date,
                               prev_week=(start - timedelta(days=7)).strftime('%Y-%m-%d'),
                               next_week=(start + timedelta(days=7)).strftime('%Y-%m-%d'),
                               now=datetime.now())
    
    except Exception as e:
        logger.error(f"Error displaying appointment calendar: {e}")
        flash(f'Error displaying appointment calendar: {e}', 'danger')
        return redirect(url_for('appointments'))

@app.route('/appointments/create', methods=['GET', 'POST'])
def create_appointment():
    """Create a new appointment"""
    if request.method == 'POST':
        try:
            # Get form data
            vehicle_id = request.form.get('vehicle_id')
            appointment_date = request.form.get('appointment_date')
            appointment_time = request.form.get('appointment_time')
            appointment_type = request.form.get('appointment_type')
            notes = request.form.get('notes')
            
            # Validate data
            if not vehicle_id or not appointment_date or not appointment_time or not appointment_type:
                flash('Please fill in all required fields', 'danger')
                return redirect(url_for('create_appointment'))
            
            # Schedule appointment
            result = schedule_appointment(
                db_path, vehicle_id, appointment_date, appointment_time, appointment_type, notes
            )
            
            if result.get('success'):
                flash('Appointment scheduled successfully', 'success')
                return redirect(url_for('appointments'))
            else:
                flash(result.get('message', 'Error scheduling appointment'), 'danger')
                return redirect(url_for('create_appointment'))
        
        except Exception as e:
            logger.error(f"Error creating appointment: {e}")
            flash(f'Error creating appointment: {e}', 'danger')
            return redirect(url_for('create_appointment'))
    
    # GET request
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Get vehicles
        cursor.execute("""
        SELECT v.id, v.registration, v.make, v.model,
               c.name as customer_name
        FROM vehicles v
        LEFT JOIN customers c ON v.customer_id = c.id
        ORDER BY v.registration
        """)
        
        vehicles = cursor.fetchall()
        
        # Close connection
        conn.close()
        
        return render_template('create_appointment.html', 
                               vehicles=vehicles,
                               appointment_types=['MOT', 'Service', 'Repair', 'Inspection', 'Other'],
                               min_date=datetime.now().strftime('%Y-%m-%d'))
    
    except Exception as e:
        logger.error(f"Error loading create appointment form: {e}")
        flash(f'Error loading create appointment form: {e}', 'danger')
        return redirect(url_for('appointments'))

@app.route('/appointments/update_status/<int:appointment_id>/<status>')
def update_appointment_status_route(appointment_id, status):
    """Update appointment status"""
    try:
        # Update status
        result = update_appointment_status(db_path, appointment_id, status)
        
        if result.get('success'):
            flash(result.get('message', 'Appointment status updated'), 'success')
        else:
            flash(result.get('message', 'Error updating appointment status'), 'danger')
        
        return redirect(url_for('appointments'))
    
    except Exception as e:
        logger.error(f"Error updating appointment status: {e}")
        flash(f'Error updating appointment status: {e}', 'danger')
        return redirect(url_for('appointments'))

@app.route('/appointments/available_slots')
def available_slots():
    """Get available appointment slots for a date"""
    try:
        # Get date from request
        date = request.args.get('date')
        
        if not date:
            return jsonify({
                'success': False,
                'message': 'Date is required'
            })
        
        # Get available slots
        result = get_available_slots(db_path, date)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error getting available slots: {e}")
        return jsonify({
            'success': False,
            'message': f'Error getting available slots: {e}'
        })
