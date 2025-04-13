#!/usr/bin/env python3
"""
Integrated Garage Management System

This module initializes the Flask application and sets up the necessary configurations.
"""

import os
import logging
from datetime import datetime
from flask import Flask, render_template
from flask_apscheduler import APScheduler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, 
            template_folder='../templates',
            static_folder='../static')

# Set a secret key for the application
app.secret_key = 'garage_management_system_secret_key_2025'

# Initialize scheduler
scheduler = APScheduler()
scheduler.init_app(app)

# Import configuration
from app.config.config import load_config, find_ga4_installation

# Find GA4 installation and load configuration
ga4_path = find_ga4_installation()
if ga4_path:
    logger.info(f"Found GA4 installation at {ga4_path}")
else:
    logger.warning("GA4 installation not found")

config = load_config()

# Import database utilities
from app.utils.database import init_database, create_tables

# Initialize database
db_path = config.get('database_path', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'garage_system.db'))
init_database(db_path)
create_tables(db_path)

# Import routes
from app.routes import index_routes
from app.routes import customer_routes
from app.routes import vehicle_routes
from app.routes import reminder_routes
from app.routes import api_routes
from app.routes import document_routes
from app.routes import appointment_routes
from app.routes import invoice_routes

# Import services
from app.services import ga4_service
from app.services import reminder_service
from app.services import dvla_service

# Register Jinja2 filters
from app.utils.filters import register_filters
register_filters(app)

# Start services
def start_services():
    """Start all background services"""
    # Start file watcher
    ga4_service.start_file_watcher(app, config)
    
    # Start reminder scheduler
    reminder_service.start_reminder_scheduler(app, db_path)
    
    # Start auto sync
    ga4_service.start_auto_sync(app, config, db_path)

# Start services when app is ready
@app.before_first_request
def before_first_request():
    """Initialize services before first request"""
    start_services()

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    logger.error(f"Server error: {e}")
    return render_template('errors/500.html'), 500
