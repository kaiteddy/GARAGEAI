#!/usr/bin/env python3
"""
Reminder Routes Module

This module handles routes related to MOT reminders and notifications.
"""

import os
import logging
from datetime import datetime, timedelta
from flask import render_template, redirect, url_for, flash, request, jsonify

from app import app
from app.utils.database import get_db_connection
from app.services.reminder_service import send_reminder, create_mot_reminders

logger = logging.getLogger(__name__)

# Get database path from app config
db_path = app.config.get('DATABASE_PATH', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'garage_system.db'))

@app.route('/reminders')
def reminders():
    """Reminders page"""
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Get reminders with vehicle and customer info
        cursor.execute("""
        SELECT r.id, r.reminder_date, r.reminder_type, r.status, r.notes,
               v.id as vehicle_id, v.registration, v.make, v.model,
               c.id as customer_id, c.name as customer_name, c.email, c.phone
        FROM reminders r
        JOIN vehicles v ON r.vehicle_id = v.id
        LEFT JOIN customers c ON v.customer_id = c.id
        ORDER BY r.reminder_date DESC
        """)
        
        reminders_data = cursor.fetchall()
        
        # Get total counts for statistics
        cursor.execute("""
        SELECT 
            COUNT(*) as total_reminders,
            COUNT(CASE WHEN status = 'Pending' THEN 1 END) as pending_reminders,
            COUNT(CASE WHEN status = 'Sent' THEN 1 END) as sent_reminders,
            COUNT(CASE WHEN status = 'Acknowledged' THEN 1 END) as acknowledged_reminders
        FROM reminders
        """)
        
        stats = cursor.fetchone()
        
        # Close connection
        conn.close()
        
        return render_template('reminders.html', 
                               reminders=reminders_data, 
                               stats=stats,
                               now=datetime.now())
    
    except Exception as e:
        logger.error(f"Error displaying reminders: {e}")
        flash(f'Error displaying reminders: {e}', 'danger')
        return redirect(url_for('index'))

@app.route('/reminders/create', methods=['GET', 'POST'])
def create_reminder():
    """Create a new reminder"""
    if request.method == 'POST':
        try:
            # Get form data
            vehicle_id = request.form.get('vehicle_id')
            reminder_date = request.form.get('reminder_date')
            reminder_type = request.form.get('reminder_type')
            notes = request.form.get('notes')
            
            # Validate data
            if not vehicle_id or not reminder_date or not reminder_type:
                flash('Please fill in all required fields', 'danger')
                return redirect(url_for('create_reminder'))
            
            # Connect to database
            conn = get_db_connection(db_path)
            cursor = conn.cursor()
            
            # Check if vehicle exists
            cursor.execute("SELECT id FROM vehicles WHERE id = ?", (vehicle_id,))
            if not cursor.fetchone():
                flash('Vehicle not found', 'danger')
                conn.close()
                return redirect(url_for('create_reminder'))
            
            # Create reminder
            cursor.execute("""
            INSERT INTO reminders (vehicle_id, reminder_date, reminder_type, status, notes)
            VALUES (?, ?, ?, 'Pending', ?)
            """, (vehicle_id, reminder_date, reminder_type, notes))
            
            reminder_id = cursor.lastrowid
            
            # Commit changes
            conn.commit()
            conn.close()
            
            flash('Reminder created successfully', 'success')
            return redirect(url_for('reminders'))
        
        except Exception as e:
            logger.error(f"Error creating reminder: {e}")
            flash(f'Error creating reminder: {e}', 'danger')
            return redirect(url_for('create_reminder'))
    
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
        
        return render_template('create_reminder.html', 
                               vehicles=vehicles,
                               reminder_types=['MOT', 'Service', 'Insurance', 'Tax', 'Other'],
                               min_date=datetime.now().strftime('%Y-%m-%d'))
    
    except Exception as e:
        logger.error(f"Error loading create reminder form: {e}")
        flash(f'Error loading create reminder form: {e}', 'danger')
        return redirect(url_for('reminders'))

@app.route('/reminders/send/<int:reminder_id>')
def send_reminder_route(reminder_id):
    """Send a reminder"""
    try:
        # Send reminder
        result = send_reminder(db_path, reminder_id)
        
        if result.get('success'):
            flash(result.get('message', 'Reminder sent successfully'), 'success')
        else:
            flash(result.get('message', 'Error sending reminder'), 'danger')
        
        return redirect(url_for('reminders'))
    
    except Exception as e:
        logger.error(f"Error sending reminder: {e}")
        flash(f'Error sending reminder: {e}', 'danger')
        return redirect(url_for('reminders'))

@app.route('/reminders/generate')
def generate_reminders():
    """Generate MOT reminders for vehicles due for MOT"""
    try:
        # Generate reminders
        days_before = int(request.args.get('days', 30))
        result = create_mot_reminders(db_path, days_before=days_before)
        
        if result.get('success'):
            flash(f"Generated {result.get('count', 0)} MOT reminders", 'success')
        else:
            flash(result.get('message', 'Error generating reminders'), 'danger')
        
        return redirect(url_for('reminders'))
    
    except Exception as e:
        logger.error(f"Error generating reminders: {e}")
        flash(f'Error generating reminders: {e}', 'danger')
        return redirect(url_for('reminders'))

@app.route('/reminders/mark/<int:reminder_id>/<status>')
def mark_reminder(reminder_id, status):
    """Mark a reminder as acknowledged or pending"""
    try:
        # Validate status
        if status not in ['Acknowledged', 'Pending', 'Sent']:
            flash('Invalid status', 'danger')
            return redirect(url_for('reminders'))
        
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Update reminder status
        cursor.execute("""
        UPDATE reminders
        SET status = ?
        WHERE id = ?
        """, (status, reminder_id))
        
        # Commit changes
        conn.commit()
        conn.close()
        
        flash(f'Reminder marked as {status}', 'success')
        return redirect(url_for('reminders'))
    
    except Exception as e:
        logger.error(f"Error marking reminder: {e}")
        flash(f'Error marking reminder: {e}', 'danger')
        return redirect(url_for('reminders'))
