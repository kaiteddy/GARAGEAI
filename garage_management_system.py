#!/usr/bin/env python3
"""
Garage Management System

This is the main application file for the Garage Management System.
It integrates all components into a single web application.
"""

import os
import sys
import json
import logging
import argparse
import webbrowser
import threading
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('GarageManagementSystem')

# Add parent directory to path to import modules
parent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(parent_dir)

# Create Flask app
app = Flask(__name__)

# Global variables
config = {}

def load_config(config_path):
    """Load configuration from file
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration dictionary
    """
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded configuration from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
    
    # Create default configuration if file doesn't exist
    return create_default_config(config_path)

def create_default_config(config_path):
    """Create default configuration file
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration dictionary
    """
    default_config = {
        "system": {
            "name": "Garage Management System",
            "version": "0.1.0",
            "port": 5000,
            "host": "0.0.0.0",
            "debug": False
        },
        "database": {
            "path": os.path.join(os.path.dirname(config_path), "database", "garage_system.db")
        },
        "ga4": {
            "path": "",
            "auto_import": True
        }
    }
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    # Write configuration to file
    with open(config_path, 'w') as f:
        json.dump(default_config, f, indent=4)
    
    logger.info(f"Created default configuration at {config_path}")
    return default_config

def init_system(config_path):
    """Initialize the system
    
    Args:
        config_path: Path to configuration file
    """
    global config
    
    # Load configuration
    config = load_config(config_path)
    
    # TODO: Initialize components
    
    logger.info("System initialized")

# Routes
@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

# TODO: Add routes for each component

def run_app(host='0.0.0.0', port=5000, debug=False):
    """Run the Flask application"""
    app.run(host=host, port=port, debug=debug)

def main():
    """Main function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Garage Management System')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--port', type=int, default=5000, help='Port to run web server on')
    parser.add_argument('--host', default='0.0.0.0', help='Host to run web server on')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    args = parser.parse_args()
    
    # Determine configuration path
    if args.config:
        config_path = args.config
    else:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "garage_system_config.json")
    
    # Initialize system
    init_system(config_path)
    
    # Open web browser
    url = f"http://localhost:{args.port}"
    webbrowser.open(url)
    
    # Run web server
    logger.info(f"Starting web server at {url}")
    run_app(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main()
