#!/usr/bin/env python3
"""
MOT Reminder Web Interface

This module provides a web interface for the MOT Reminder System:
- Viewing vehicles due for MOT
- Managing reminders
- Sending notifications
- Viewing statistics
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
from flask_cors import CORS

# Import local modules
from .reminder_manager import MOTReminderManager
from .notification_handler import NotificationHandler

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('MOTReminderWeb')

# Create Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Global variables
reminder_manager = None
notification_handler = None
config = {}

def init_app(db_path: str, config_path: Optional[str] = None):
    """Initialize the application
    
    Args:
        db_path: Path to the SQLite database
        config_path: Optional path to configuration file
    """
    global reminder_manager, notification_handler, config
    
    # Load configuration
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            config = {}
    
    # Initialize reminder manager
    reminder_manager = MOTReminderManager(db_path, config_path)
    
    # Initialize notification handler
    notification_handler = NotificationHandler(config_path)
    
    logger.info("Application initialized")

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/vehicles')
def vehicles():
    """Vehicles page"""
    # Get vehicles from database
    days_range = [30, 14, 7, 3, 1]
    vehicles_list = reminder_manager.find_vehicles_due_for_mot(days_range)
    
    # Group vehicles by days to expiry
    vehicles_by_days = {}
    for days in days_range:
        vehicles_by_days[days] = [v for v in vehicles_list if v.get('days_to_expiry') == days]
    
    return render_template('vehicles.html', vehicles_by_days=vehicles_by_days, days_range=days_range)

@app.route('/reminders')
def reminders():
    """Reminders page"""
    # Get all reminders
    all_reminders = []
    
    try:
        # Get reminders by status
        statuses = ['created', 'sent', 'responded', 'completed', 'failed']
        reminders_by_status = {}
        
        for status in statuses:
            reminder_manager.cursor.execute(
                "SELECT * FROM mot_reminders WHERE reminder_status = ? ORDER BY days_to_expiry ASC",
                (status,)
            )
            
            reminders = []
            for row in reminder_manager.cursor.fetchall():
                reminder = {}
                for key in row.keys():
                    reminder[key] = row[key]
                reminders.append(reminder)
            
            reminders_by_status[status] = reminders
            all_reminders.extend(reminders)
    
    except Exception as e:
        logger.error(f"Error getting reminders: {e}")
        reminders_by_status = {status: [] for status in statuses}
    
    return render_template('reminders.html', 
                          reminders_by_status=reminders_by_status, 
                          statuses=statuses,
                          all_reminders=all_reminders)

@app.route('/create_reminders', methods=['POST'])
def create_reminders():
    """Create reminders for vehicles due for MOT"""
    try:
        # Get days range from form
        days_range = request.form.getlist('days_range', type=int)
        if not days_range:
            days_range = [30, 14, 7, 3, 1]
        
        # Find vehicles due for MOT
        vehicles = reminder_manager.find_vehicles_due_for_mot(days_range)
        
        # Create reminders for each vehicle
        created_count = 0
        for vehicle in vehicles:
            reminder_id = reminder_manager.create_reminder(vehicle)
            if reminder_id:
                created_count += 1
        
        return jsonify({
            'success': True,
            'message': f'Created {created_count} reminders',
            'created_count': created_count
        })
    
    except Exception as e:
        logger.error(f"Error creating reminders: {e}")
        return jsonify({
            'success': False,
            'message': f'Error creating reminders: {str(e)}'
        })

@app.route('/send_reminder/<int:reminder_id>', methods=['POST'])
def send_reminder(reminder_id):
    """Send a reminder"""
    try:
        # Get reminder details
        reminder_manager.cursor.execute("SELECT * FROM mot_reminders WHERE id = ?", (reminder_id,))
        reminder = reminder_manager.cursor.fetchone()
        
        if not reminder:
            return jsonify({
                'success': False,
                'message': f'Reminder {reminder_id} not found'
            })
        
        # Convert to dictionary
        reminder_dict = {}
        for key in reminder.keys():
            reminder_dict[key] = reminder[key]
        
        # Get notification type from form
        notification_type = request.form.get('notification_type', 'email')
        
        # Generate reminder content
        content = reminder_manager.generate_reminder_content(reminder_dict, notification_type)
        
        if not content:
            return jsonify({
                'success': False,
                'message': f'Error generating reminder content for {notification_type}'
            })
        
        # Send notification
        result = notification_handler.send_notification(reminder_dict, notification_type, content)
        
        if result:
            # Update reminder status
            reminder_manager.update_reminder_status(
                reminder_id, 
                'sent', 
                f'Sent {notification_type} notification on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
            )
            
            return jsonify({
                'success': True,
                'message': f'Sent {notification_type} reminder for {reminder_dict["registration"]}'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Error sending {notification_type} reminder'
            })
    
    except Exception as e:
        logger.error(f"Error sending reminder: {e}")
        return jsonify({
            'success': False,
            'message': f'Error sending reminder: {str(e)}'
        })

@app.route('/update_reminder/<int:reminder_id>', methods=['POST'])
def update_reminder(reminder_id):
    """Update reminder status"""
    try:
        # Get new status from form
        status = request.form.get('status')
        notes = request.form.get('notes', '')
        
        if not status:
            return jsonify({
                'success': False,
                'message': 'No status provided'
            })
        
        # Update reminder status
        result = reminder_manager.update_reminder_status(reminder_id, status, notes)
        
        if result:
            return jsonify({
                'success': True,
                'message': f'Updated reminder {reminder_id} status to {status}'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Error updating reminder status'
            })
    
    except Exception as e:
        logger.error(f"Error updating reminder: {e}")
        return jsonify({
            'success': False,
            'message': f'Error updating reminder: {str(e)}'
        })

@app.route('/statistics')
def statistics():
    """Statistics page"""
    # Get reminder statistics
    stats = reminder_manager.get_reminder_statistics()
    
    return render_template('statistics.html', stats=stats)

@app.route('/settings')
def settings():
    """Settings page"""
    # Get current settings
    current_settings = {}
    
    try:
        reminder_manager.cursor.execute("SELECT setting_name, setting_value, setting_type FROM reminder_settings")
        for row in reminder_manager.cursor.fetchall():
            current_settings[row['setting_name']] = {
                'value': row['setting_value'],
                'type': row['setting_type']
            }
        
        # Get reminder templates
        templates = {}
        reminder_manager.cursor.execute("SELECT id, name, type, subject, body FROM reminder_templates")
        for row in reminder_manager.cursor.fetchall():
            if row['type'] not in templates:
                templates[row['type']] = []
            
            templates[row['type']].append({
                'id': row['id'],
                'name': row['name'],
                'subject': row['subject'],
                'body': row['body']
            })
    
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        current_settings = {}
        templates = {}
    
    return render_template('settings.html', settings=current_settings, templates=templates)

@app.route('/update_settings', methods=['POST'])
def update_settings():
    """Update settings"""
    try:
        # Get settings from form
        for key, value in request.form.items():
            if key.startswith('setting_'):
                setting_name = key.replace('setting_', '')
                
                # Update setting in database
                reminder_manager.cursor.execute(
                    "UPDATE reminder_settings SET setting_value = ? WHERE setting_name = ?",
                    (value, setting_name)
                )
        
        reminder_manager.connection.commit()
        
        return jsonify({
            'success': True,
            'message': 'Settings updated successfully'
        })
    
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        return jsonify({
            'success': False,
            'message': f'Error updating settings: {str(e)}'
        })

@app.route('/update_template', methods=['POST'])
def update_template():
    """Update reminder template"""
    try:
        # Get template details from form
        template_id = request.form.get('template_id')
        name = request.form.get('name')
        template_type = request.form.get('type')
        subject = request.form.get('subject', '')
        body = request.form.get('body')
        
        if not template_id or not name or not template_type or not body:
            return jsonify({
                'success': False,
                'message': 'Missing required fields'
            })
        
        # Update template in database
        reminder_manager.cursor.execute(
            "UPDATE reminder_templates SET name = ?, type = ?, subject = ?, body = ?, last_modified = ? WHERE id = ?",
            (name, template_type, subject, body, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), template_id)
        )
        
        reminder_manager.connection.commit()
        
        return jsonify({
            'success': True,
            'message': 'Template updated successfully'
        })
    
    except Exception as e:
        logger.error(f"Error updating template: {e}")
        return jsonify({
            'success': False,
            'message': f'Error updating template: {str(e)}'
        })

@app.route('/create_template', methods=['POST'])
def create_template():
    """Create new reminder template"""
    try:
        # Get template details from form
        name = request.form.get('name')
        template_type = request.form.get('type')
        subject = request.form.get('subject', '')
        body = request.form.get('body')
        
        if not name or not template_type or not body:
            return jsonify({
                'success': False,
                'message': 'Missing required fields'
            })
        
        # Create template in database
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        reminder_manager.cursor.execute(
            "INSERT INTO reminder_templates (name, type, subject, body, created_date, last_modified) VALUES (?, ?, ?, ?, ?, ?)",
            (name, template_type, subject, body, now, now)
        )
        
        reminder_manager.connection.commit()
        
        return jsonify({
            'success': True,
            'message': 'Template created successfully'
        })
    
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        return jsonify({
            'success': False,
            'message': f'Error creating template: {str(e)}'
        })

@app.route('/api/vehicles')
def api_vehicles():
    """API endpoint for vehicles due for MOT"""
    try:
        # Get days range from query parameters
        days_str = request.args.get('days', '30,14,7,3,1')
        days_range = [int(d) for d in days_str.split(',')]
        
        # Find vehicles due for MOT
        vehicles = reminder_manager.find_vehicles_due_for_mot(days_range)
        
        return jsonify({
            'success': True,
            'count': len(vehicles),
            'vehicles': vehicles
        })
    
    except Exception as e:
        logger.error(f"Error getting vehicles: {e}")
        return jsonify({
            'success': False,
            'message': f'Error getting vehicles: {str(e)}'
        })

@app.route('/api/reminders')
def api_reminders():
    """API endpoint for reminders"""
    try:
        # Get status from query parameters
        status = request.args.get('status')
        
        # Get reminders
        if status:
            reminder_manager.cursor.execute(
                "SELECT * FROM mot_reminders WHERE reminder_status = ? ORDER BY days_to_expiry ASC",
                (status,)
            )
        else:
            reminder_manager.cursor.execute(
                "SELECT * FROM mot_reminders ORDER BY days_to_expiry ASC"
            )
        
        reminders = []
        for row in reminder_manager.cursor.fetchall():
            reminder = {}
            for key in row.keys():
                reminder[key] = row[key]
            reminders.append(reminder)
        
        return jsonify({
            'success': True,
            'count': len(reminders),
            'reminders': reminders
        })
    
    except Exception as e:
        logger.error(f"Error getting reminders: {e}")
        return jsonify({
            'success': False,
            'message': f'Error getting reminders: {str(e)}'
        })

@app.route('/api/statistics')
def api_statistics():
    """API endpoint for statistics"""
    try:
        # Get reminder statistics
        stats = reminder_manager.get_reminder_statistics()
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
    
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({
            'success': False,
            'message': f'Error getting statistics: {str(e)}'
        })

def run_app(host='0.0.0.0', port=5000, debug=False):
    """Run the Flask application"""
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    # Get database path from command line arguments or use default
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ga4_direct.db")
    
    # Get config path from command line arguments or use default
    if len(sys.argv) > 2:
        config_path = sys.argv[2]
    else:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mot_config.json")
    
    # Initialize application
    init_app(db_path, config_path)
    
    # Run application
    run_app(debug=True)
