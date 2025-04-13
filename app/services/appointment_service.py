#!/usr/bin/env python3
"""
Appointment Service Module

This module handles appointment scheduling and management.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

from app.utils.database import get_db_connection

logger = logging.getLogger(__name__)

def get_upcoming_appointments(db_path: str, days: int = 7) -> List[Dict[str, Any]]:
    """
    Get upcoming appointments within the specified number of days.
    
    Args:
        db_path (str): Path to the database file
        days (int): Number of days to look ahead
        
    Returns:
        list: List of upcoming appointments
    """
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Calculate date range
        today = datetime.now().date()
        future_date = today + timedelta(days=days)
        
        # Get upcoming appointments
        cursor.execute("""
        SELECT a.id, a.appointment_date, a.appointment_time, a.appointment_type, a.status, a.notes,
               v.id as vehicle_id, v.registration, v.make, v.model,
               c.id as customer_id, c.name as customer_name, c.phone
        FROM appointments a
        JOIN vehicles v ON a.vehicle_id = v.id
        LEFT JOIN customers c ON v.customer_id = c.id
        WHERE a.appointment_date BETWEEN ? AND ?
        AND a.status = 'Scheduled'
        ORDER BY a.appointment_date, a.appointment_time
        """, (today.strftime('%Y-%m-%d'), future_date.strftime('%Y-%m-%d')))
        
        appointments = [dict(a) for a in cursor.fetchall()]
        
        # Close connection
        conn.close()
        
        return appointments
    
    except Exception as e:
        logger.error(f"Error getting upcoming appointments: {e}")
        return []

def schedule_appointment(db_path: str, vehicle_id: int, appointment_date: str, 
                        appointment_time: str, appointment_type: str, notes: str = '') -> Dict[str, Any]:
    """
    Schedule a new appointment.
    
    Args:
        db_path (str): Path to the database file
        vehicle_id (int): ID of the vehicle
        appointment_date (str): Date of the appointment (YYYY-MM-DD)
        appointment_time (str): Time of the appointment (HH:MM)
        appointment_type (str): Type of appointment
        notes (str): Additional notes
        
    Returns:
        dict: Result of the operation
    """
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Check if vehicle exists
        cursor.execute("SELECT id FROM vehicles WHERE id = ?", (vehicle_id,))
        if not cursor.fetchone():
            conn.close()
            return {
                'success': False,
                'message': 'Vehicle not found'
            }
        
        # Check if there's already an appointment at the same time
        cursor.execute("""
        SELECT id FROM appointments
        WHERE appointment_date = ? AND appointment_time = ? AND status = 'Scheduled'
        """, (appointment_date, appointment_time))
        
        if cursor.fetchone():
            conn.close()
            return {
                'success': False,
                'message': 'There is already an appointment scheduled at this time'
            }
        
        # Create appointment
        cursor.execute("""
        INSERT INTO appointments (vehicle_id, appointment_date, appointment_time, appointment_type, status, notes)
        VALUES (?, ?, ?, ?, 'Scheduled', ?)
        """, (vehicle_id, appointment_date, appointment_time, appointment_type, notes))
        
        appointment_id = cursor.lastrowid
        
        # Commit changes
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': 'Appointment scheduled successfully',
            'appointment_id': appointment_id
        }
    
    except Exception as e:
        logger.error(f"Error scheduling appointment: {e}")
        return {
            'success': False,
            'message': f'Error scheduling appointment: {e}'
        }

def update_appointment_status(db_path: str, appointment_id: int, status: str) -> Dict[str, Any]:
    """
    Update the status of an appointment.
    
    Args:
        db_path (str): Path to the database file
        appointment_id (int): ID of the appointment
        status (str): New status
        
    Returns:
        dict: Result of the operation
    """
    try:
        # Validate status
        valid_statuses = ['Scheduled', 'Completed', 'Cancelled', 'No Show']
        if status not in valid_statuses:
            return {
                'success': False,
                'message': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            }
        
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Check if appointment exists
        cursor.execute("SELECT id FROM appointments WHERE id = ?", (appointment_id,))
        if not cursor.fetchone():
            conn.close()
            return {
                'success': False,
                'message': 'Appointment not found'
            }
        
        # Update appointment status
        cursor.execute("""
        UPDATE appointments
        SET status = ?, updated_at = ?
        WHERE id = ?
        """, (status, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), appointment_id))
        
        # Commit changes
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': f'Appointment status updated to {status}'
        }
    
    except Exception as e:
        logger.error(f"Error updating appointment status: {e}")
        return {
            'success': False,
            'message': f'Error updating appointment status: {e}'
        }

def get_available_slots(db_path: str, date: str) -> Dict[str, Any]:
    """
    Get available appointment slots for a specific date.
    
    Args:
        db_path (str): Path to the database file
        date (str): Date to check (YYYY-MM-DD)
        
    Returns:
        dict: Available slots
    """
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Get booked slots
        cursor.execute("""
        SELECT appointment_time
        FROM appointments
        WHERE appointment_date = ? AND status = 'Scheduled'
        """, (date,))
        
        booked_slots = [row['appointment_time'] for row in cursor.fetchall()]
        
        # Close connection
        conn.close()
        
        # Define business hours (9 AM to 5 PM, 1-hour slots)
        all_slots = [f"{hour:02d}:00" for hour in range(9, 17)]
        
        # Filter out booked slots
        available_slots = [slot for slot in all_slots if slot not in booked_slots]
        
        return {
            'success': True,
            'date': date,
            'available_slots': available_slots,
            'booked_slots': booked_slots
        }
    
    except Exception as e:
        logger.error(f"Error getting available slots: {e}")
        return {
            'success': False,
            'message': f'Error getting available slots: {e}'
        }
