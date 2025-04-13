#!/usr/bin/env python3
"""
Index Routes Module

This module handles the main routes for the application, including the dashboard.
"""

import os
import logging
from datetime import datetime, timedelta
from flask import render_template, redirect, url_for, flash, request, jsonify

from app import app
from app.utils.database import get_db_connection
from app.services.reminder_service import get_vehicles_due_for_mot, get_recent_reminders
from app.services.appointment_service import get_upcoming_appointments

logger = logging.getLogger(__name__)

# Get database path from app config
db_path = app.config.get('DATABASE_PATH', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'garage_system.db'))

@app.route('/')
def index():
    """Home page / Dashboard"""
    try:
        # Get database connection
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        # Get statistics
        cursor.execute("""
        SELECT
            (SELECT COUNT(*) FROM vehicles) as total_vehicles,
            (SELECT COUNT(*) FROM customers) as total_customers,
            (SELECT COUNT(*) FROM reminders WHERE status = 'Pending') as pending_reminders,
            (SELECT COUNT(*) FROM appointments WHERE appointment_date >= date('now') AND status = 'Scheduled') as upcoming_appointments
        """)

        stats = cursor.fetchone()

        # Get vehicles due for MOT
        vehicles_due = get_vehicles_due_for_mot(db_path, days=30)

        # Get recent reminders
        recent_reminders = get_recent_reminders(db_path, limit=5)

        # Get upcoming appointments
        upcoming_appointments = get_upcoming_appointments(db_path, days=7)

        # Close connection
        conn.close()

        return render_template('index_new.html',
                               stats=stats,
                               vehicles_due=vehicles_due,
                               recent_reminders=recent_reminders,
                               upcoming_appointments=upcoming_appointments)

    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return render_template('errors/500.html', error=str(e)), 500

@app.route('/system_status')
def system_status():
    """System status page"""
    try:
        # Get GA4 path from config
        ga4_path = app.config.get('GA4_PATH', '')

        # Check if GA4 is installed
        ga4_installed = os.path.exists(ga4_path) if ga4_path else False

        # Get database connection
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        # Get database statistics
        cursor.execute("""
        SELECT
            (SELECT COUNT(*) FROM vehicles) as vehicle_count,
            (SELECT COUNT(*) FROM customers) as customer_count,
            (SELECT COUNT(*) FROM reminders) as reminder_count,
            (SELECT COUNT(*) FROM appointments) as appointment_count,
            (SELECT COUNT(*) FROM invoices) as invoice_count,
            (SELECT COUNT(*) FROM documents) as document_count
        """)

        db_stats = cursor.fetchone()

        # Get last sync time
        last_sync_time = app.config.get('LAST_SYNC_TIME', datetime.now() - timedelta(days=1))

        # Close connection
        conn.close()

        return render_template('system_status.html',
                               ga4_installed=ga4_installed,
                               ga4_path=ga4_path,
                               db_stats=db_stats,
                               last_sync_time=last_sync_time,
                               now=datetime.now())

    except Exception as e:
        logger.error(f"Error loading system status: {e}")
        return render_template('errors/500.html', error=str(e)), 500
