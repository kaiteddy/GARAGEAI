#!/usr/bin/env python3
"""
Reminder Service Module

This module handles MOT reminder generation and sending.
"""

import os
import logging
import smtplib
import sqlite3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from app.utils.database import get_db_connection

logger = logging.getLogger(__name__)

def get_vehicles_due_for_mot(db_path: str, days: int = 30) -> List[Dict[str, Any]]:
    """
    Get vehicles due for MOT within the specified number of days.
    
    Args:
        db_path (str): Path to the database file
        days (int): Number of days to look ahead
        
    Returns:
        list: List of vehicles due for MOT
    """
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Calculate date range
        today = datetime.now().date()
        future_date = today + timedelta(days=days)
        
        # Get vehicles due for MOT
        cursor.execute("""
        SELECT v.id, v.registration, v.make, v.model, v.year, v.mot_expiry,
               c.id as customer_id, c.name as customer_name, c.email, c.phone
        FROM vehicles v
        LEFT JOIN customers c ON v.customer_id = c.id
        WHERE v.mot_expiry BETWEEN ? AND ?
        ORDER BY v.mot_expiry
        """, (today.strftime('%Y-%m-%d'), future_date.strftime('%Y-%m-%d')))
        
        vehicles = [dict(v) for v in cursor.fetchall()]
        
        # Close connection
        conn.close()
        
        return vehicles
    
    except Exception as e:
        logger.error(f"Error getting vehicles due for MOT: {e}")
        return []

def get_recent_reminders(db_path: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get recent reminders.
    
    Args:
        db_path (str): Path to the database file
        limit (int): Maximum number of reminders to return
        
    Returns:
        list: List of recent reminders
    """
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Get recent reminders
        cursor.execute("""
        SELECT r.id, r.reminder_date, r.reminder_type, r.status, r.notes,
               v.id as vehicle_id, v.registration, v.make, v.model,
               c.id as customer_id, c.name as customer_name
        FROM reminders r
        JOIN vehicles v ON r.vehicle_id = v.id
        LEFT JOIN customers c ON v.customer_id = c.id
        ORDER BY r.created_at DESC
        LIMIT ?
        """, (limit,))
        
        reminders = [dict(r) for r in cursor.fetchall()]
        
        # Close connection
        conn.close()
        
        return reminders
    
    except Exception as e:
        logger.error(f"Error getting recent reminders: {e}")
        return []

def create_mot_reminders(db_path: str, days_before: int = 30) -> Dict[str, Any]:
    """
    Create MOT reminders for vehicles due for MOT.
    
    Args:
        db_path (str): Path to the database file
        days_before (int): Number of days before MOT expiry to create reminders
        
    Returns:
        dict: Result of the operation
    """
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Calculate date range
        today = datetime.now().date()
        future_date = today + timedelta(days=days_before)
        
        # Get vehicles due for MOT
        cursor.execute("""
        SELECT v.id, v.registration, v.mot_expiry
        FROM vehicles v
        WHERE v.mot_expiry BETWEEN ? AND ?
        AND v.id NOT IN (
            SELECT vehicle_id FROM reminders
            WHERE reminder_type = 'MOT'
            AND status IN ('Pending', 'Sent')
        )
        """, (today.strftime('%Y-%m-%d'), future_date.strftime('%Y-%m-%d')))
        
        vehicles = cursor.fetchall()
        
        if not vehicles:
            return {
                'success': True,
                'message': 'No vehicles due for MOT without existing reminders',
                'count': 0
            }
        
        # Create reminders
        count = 0
        for vehicle in vehicles:
            # Create reminder 14 days before MOT expiry
            mot_date = datetime.strptime(vehicle['mot_expiry'], '%Y-%m-%d').date()
            reminder_date = mot_date - timedelta(days=14)
            
            # Skip if reminder date is in the past
            if reminder_date < today:
                reminder_date = today
            
            cursor.execute("""
            INSERT INTO reminders (vehicle_id, reminder_date, reminder_type, status, notes)
            VALUES (?, ?, 'MOT', 'Pending', ?)
            """, (
                vehicle['id'],
                reminder_date.strftime('%Y-%m-%d'),
                f"MOT due on {vehicle['mot_expiry']} for vehicle {vehicle['registration']}"
            ))
            
            count += 1
        
        # Commit changes
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': f'Created {count} MOT reminders',
            'count': count
        }
    
    except Exception as e:
        logger.error(f"Error creating MOT reminders: {e}")
        return {
            'success': False,
            'message': f'Error creating MOT reminders: {e}',
            'count': 0
        }

def send_reminder(db_path: str, reminder_id: int) -> Dict[str, Any]:
    """
    Send a reminder to the customer.
    
    Args:
        db_path (str): Path to the database file
        reminder_id (int): ID of the reminder to send
        
    Returns:
        dict: Result of the operation
    """
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Get reminder with vehicle and customer info
        cursor.execute("""
        SELECT r.id, r.reminder_date, r.reminder_type, r.notes,
               v.id as vehicle_id, v.registration, v.make, v.model, v.year, v.mot_expiry,
               c.id as customer_id, c.name as customer_name, c.email, c.phone
        FROM reminders r
        JOIN vehicles v ON r.vehicle_id = v.id
        LEFT JOIN customers c ON v.customer_id = c.id
        WHERE r.id = ?
        """, (reminder_id,))
        
        reminder = cursor.fetchone()
        
        if not reminder:
            return {
                'success': False,
                'message': 'Reminder not found'
            }
        
        # Check if customer has email
        if not reminder['email']:
            return {
                'success': False,
                'message': 'Customer has no email address'
            }
        
        # Get email settings from config
        # In a real implementation, this would come from app.config
        # For now, we'll just simulate sending the email
        
        # Prepare email content
        subject = f"{reminder['reminder_type']} Reminder for {reminder['registration']}"
        
        # Create message body based on reminder type
        if reminder['reminder_type'] == 'MOT':
            body = f"""
            <html>
            <body>
                <h2>MOT Reminder</h2>
                <p>Dear {reminder['customer_name']},</p>
                <p>This is a friendly reminder that the MOT for your vehicle is due to expire soon.</p>
                <p><strong>Vehicle Details:</strong></p>
                <ul>
                    <li>Registration: {reminder['registration']}</li>
                    <li>Make/Model: {reminder['make']} {reminder['model']}</li>
                    <li>MOT Expiry Date: {reminder['mot_expiry']}</li>
                </ul>
                <p>Please contact us to schedule an appointment for your MOT test.</p>
                <p>Thank you for choosing our garage for your vehicle maintenance needs.</p>
                <p>Best regards,<br>Garage Management System</p>
            </body>
            </html>
            """
        else:
            body = f"""
            <html>
            <body>
                <h2>{reminder['reminder_type']} Reminder</h2>
                <p>Dear {reminder['customer_name']},</p>
                <p>This is a reminder regarding your vehicle:</p>
                <p><strong>Vehicle Details:</strong></p>
                <ul>
                    <li>Registration: {reminder['registration']}</li>
                    <li>Make/Model: {reminder['make']} {reminder['model']}</li>
                </ul>
                <p><strong>Reminder Notes:</strong></p>
                <p>{reminder['notes']}</p>
                <p>Please contact us if you have any questions.</p>
                <p>Best regards,<br>Garage Management System</p>
            </body>
            </html>
            """
        
        # In a real implementation, we would send the email here
        # For now, we'll just log it and update the reminder status
        logger.info(f"Sending reminder email to {reminder['email']}: {subject}")
        
        # Update reminder status
        cursor.execute("""
        UPDATE reminders
        SET status = 'Sent'
        WHERE id = ?
        """, (reminder_id,))
        
        # Commit changes
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': f"Reminder sent to {reminder['customer_name']} at {reminder['email']}"
        }
    
    except Exception as e:
        logger.error(f"Error sending reminder: {e}")
        return {
            'success': False,
            'message': f'Error sending reminder: {e}'
        }

def start_reminder_scheduler(app, db_path: str) -> None:
    """
    Start the reminder scheduler.
    
    Args:
        app: Flask application
        db_path (str): Path to the database file
    """
    # This function would typically set up a scheduler to automatically
    # check for and send reminders at regular intervals
    # For now, we'll just log that it's been called
    logger.info("Starting reminder scheduler")
    
    # In a real implementation, we would use the APScheduler to schedule tasks
    # For example:
    # app.apscheduler.add_job(
    #     id='check_mot_reminders',
    #     func=create_mot_reminders,
    #     args=[db_path],
    #     trigger='interval',
    #     hours=24
    # )
    
    # app.apscheduler.add_job(
    #     id='send_pending_reminders',
    #     func=send_pending_reminders,
    #     args=[db_path],
    #     trigger='interval',
    #     hours=1
    # )
    
    logger.info("Reminder scheduler started")
