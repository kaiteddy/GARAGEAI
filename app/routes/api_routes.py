#!/usr/bin/env python3
"""
API Routes Module

This module handles API endpoints for the application.
"""

import os
import json
import logging
from datetime import datetime
from flask import request, jsonify

from app import app
from app.utils.database import get_db_connection
from app.services.dvla_service import check_mot_status
from app.services.reminder_service import create_mot_reminders, send_reminder
from app.services.appointment_service import get_available_slots, schedule_appointment
from app.services.ga4_service import sync_ga4_data

logger = logging.getLogger(__name__)

# Get database path from app config
db_path = app.config.get('DATABASE_PATH', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'garage_system.db'))

@app.route('/api/vehicles', methods=['GET'])
def api_vehicles():
    """API endpoint to get vehicles"""
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        # Get vehicles
        cursor.execute("""
        SELECT v.id, v.registration, v.make, v.model, v.year, v.color,
               v.mot_expiry, v.mot_status, v.last_mot_check,
               c.id as customer_id, c.name as customer_name
        FROM vehicles v
        LEFT JOIN customers c ON v.customer_id = c.id
        ORDER BY v.registration
        """)

        vehicles = [dict(v) for v in cursor.fetchall()]

        # Close connection
        conn.close()

        return jsonify({
            'success': True,
            'vehicles': vehicles
        })

    except Exception as e:
        logger.error(f"API error getting vehicles: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/vehicles/<int:vehicle_id>', methods=['GET'])
def api_vehicle_detail(vehicle_id):
    """API endpoint to get vehicle details"""
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
            return jsonify({
                'success': False,
                'message': 'Vehicle not found'
            }), 404

        # Close connection
        conn.close()

        return jsonify({
            'success': True,
            'vehicle': dict(vehicle)
        })

    except Exception as e:
        logger.error(f"API error getting vehicle details: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/vehicles/check_mot', methods=['POST'])
def api_check_mot():
    """API endpoint to check MOT status"""
    try:
        # Get registration from request
        data = request.get_json()

        if not data or 'registration' not in data:
            return jsonify({
                'success': False,
                'message': 'Registration number is required'
            }), 400

        registration = data['registration']

        # Check MOT status
        result = check_mot_status(registration)

        return jsonify(result)

    except Exception as e:
        logger.error(f"API error checking MOT status: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/customers', methods=['GET'])
def api_customers():
    """API endpoint to get customers"""
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        # Get customers
        cursor.execute("""
        SELECT c.id, c.name, c.email, c.phone, c.address,
               COUNT(v.id) as vehicle_count
        FROM customers c
        LEFT JOIN vehicles v ON c.id = v.customer_id
        GROUP BY c.id
        ORDER BY c.name
        """)

        customers = [dict(c) for c in cursor.fetchall()]

        # Close connection
        conn.close()

        return jsonify({
            'success': True,
            'customers': customers
        })

    except Exception as e:
        logger.error(f"API error getting customers: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/customers/<int:customer_id>', methods=['GET'])
def api_customer_detail(customer_id):
    """API endpoint to get customer details"""
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        # Get customer
        cursor.execute("""
        SELECT c.id, c.name, c.email, c.phone, c.address, c.created_at, c.updated_at
        FROM customers c
        WHERE c.id = ?
        """, (customer_id,))

        customer = cursor.fetchone()

        if not customer:
            return jsonify({
                'success': False,
                'message': 'Customer not found'
            }), 404

        # Get customer vehicles
        cursor.execute("""
        SELECT v.id, v.registration, v.make, v.model, v.year, v.color, v.mot_expiry, v.mot_status
        FROM vehicles v
        WHERE v.customer_id = ?
        ORDER BY v.registration
        """, (customer_id,))

        vehicles = [dict(v) for v in cursor.fetchall()]

        # Close connection
        conn.close()

        return jsonify({
            'success': True,
            'customer': dict(customer),
            'vehicles': vehicles
        })

    except Exception as e:
        logger.error(f"API error getting customer details: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/reminders/create', methods=['POST'])
def api_create_reminders():
    """API endpoint to create MOT reminders"""
    try:
        # Get days_before from request
        data = request.get_json()
        days_before = data.get('days_before', 30) if data else 30

        # Create reminders
        result = create_mot_reminders(db_path, days_before=days_before)

        return jsonify(result)

    except Exception as e:
        logger.error(f"API error creating reminders: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/reminders/send/<int:reminder_id>', methods=['POST'])
def api_send_reminder(reminder_id):
    """API endpoint to send a reminder"""
    try:
        # Send reminder
        result = send_reminder(db_path, reminder_id)

        return jsonify(result)

    except Exception as e:
        logger.error(f"API error sending reminder: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/appointments/available_slots', methods=['GET'])
def api_available_slots():
    """API endpoint to get available appointment slots"""
    try:
        # Get date from request
        date = request.args.get('date')

        if not date:
            return jsonify({
                'success': False,
                'message': 'Date is required'
            }), 400

        # Get available slots
        result = get_available_slots(db_path, date)

        return jsonify(result)

    except Exception as e:
        logger.error(f"API error getting available slots: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/appointments/schedule', methods=['POST'])
def api_schedule_appointment():
    """API endpoint to schedule an appointment"""
    try:
        # Get appointment data from request
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'message': 'Appointment data is required'
            }), 400

        # Extract appointment details
        vehicle_id = data.get('vehicle_id')
        appointment_date = data.get('appointment_date')
        appointment_time = data.get('appointment_time')
        appointment_type = data.get('appointment_type')
        notes = data.get('notes', '')

        # Validate required fields
        if not vehicle_id or not appointment_date or not appointment_time or not appointment_type:
            return jsonify({
                'success': False,
                'message': 'Missing required fields'
            }), 400

        # Schedule appointment
        result = schedule_appointment(
            db_path, vehicle_id, appointment_date, appointment_time, appointment_type, notes
        )

        return jsonify(result)

    except Exception as e:
        logger.error(f"API error scheduling appointment: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/sync', methods=['POST'])
def api_sync_ga4_data():
    """API endpoint to synchronize GA4 data"""
    try:
        # Sync GA4 data
        result = sync_ga4_data()

        if result.get('success'):
            return jsonify({
                'success': True,
                'message': 'GA4 data synchronized successfully',
                'details': result
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', 'Failed to synchronize GA4 data'),
                'details': result
            }), 500

    except Exception as e:
        logger.error(f"API error synchronizing GA4 data: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
