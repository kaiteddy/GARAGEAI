#!/usr/bin/env python3
"""
Garage Management System Runner

This script runs the refactored Garage Management System with the new modular structure.
"""

import os
import sys
import argparse
import logging
from app import app, scheduler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Garage Management System')
    
    parser.add_argument('--host', type=str, default='0.0.0.0',
                        help='Host to run the server on')
    
    parser.add_argument('--port', type=int, default=8080,
                        help='Port to run the server on')
    
    parser.add_argument('--debug', action='store_true',
                        help='Run in debug mode')
    
    parser.add_argument('--auto-sync-interval', type=int, default=15,
                        help='Interval in minutes for automatic GA4 data synchronization')
    
    parser.add_argument('--mot-verify-interval', type=int, default=60,
                        help='Interval in minutes for automatic MOT verification')
    
    return parser.parse_args()

def main():
    """Main function"""
    # Parse arguments
    args = parse_arguments()
    
    # Update app configuration
    app.config['AUTO_SYNC_INTERVAL'] = args.auto_sync_interval
    app.config['MOT_VERIFY_INTERVAL'] = args.mot_verify_interval
    
    # Print startup message
    logger.info("Launching Integrated Garage Management System")
    logger.info(f"Server will be available at http://{args.host}:{args.port}")
    
    # Start scheduler
    scheduler.start()
    
    # Run the app
    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == '__main__':
    main()
