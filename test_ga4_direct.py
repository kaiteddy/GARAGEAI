#!/usr/bin/env python3
"""
Test script for GA4 Direct Access
"""

import os
import logging
from flask import Flask

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('TestGA4DirectAccess')

# Add console handler to ensure logs are printed
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
logger.addHandler(console_handler)
logger.setLevel(logging.DEBUG)

logger.debug('Starting Test GA4 Direct Access Tool')

# Create Flask app
app = Flask(__name__)

@app.route('/')
def index():
    logger.debug('Index route accessed')
    return "GA4 Direct Access Tool Test"

if __name__ == '__main__':
    logger.debug('Starting Flask app on port 5001')
    print("Starting Flask app on port 5001")
    app.run(debug=True, host='127.0.0.1', port=5001)
