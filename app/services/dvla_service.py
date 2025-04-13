#!/usr/bin/env python3
"""
DVLA Service Module

This module handles interactions with the DVLA API for MOT status checking.
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Any

logger = logging.getLogger(__name__)

def check_mot_status(registration: str) -> Dict[str, Any]:
    """
    Check the MOT status of a vehicle using the DVLA API.
    
    Args:
        registration (str): Vehicle registration number
        
    Returns:
        dict: MOT status information
    """
    try:
        # Clean registration number
        registration = registration.strip().upper().replace(' ', '')
        
        # In a real implementation, we would call the DVLA API
        # For now, we'll simulate the response
        
        # Simulate API call
        logger.info(f"Checking MOT status for {registration}")
        
        # Get API key from config
        # In a real implementation, this would come from app.config
        # api_key = app.config.get('DVLA_API_KEY', '')
        
        # Simulate API response
        # This would be replaced with actual API call in production
        # response = requests.get(
        #     f"https://dvla-api.example.com/v1/vehicles/{registration}/mot",
        #     headers={"Authorization": f"Bearer {api_key}"}
        # )
        
        # For now, generate a simulated response
        # In a real implementation, we would parse the API response
        
        # Simulate a valid MOT for most vehicles
        is_valid = True
        
        # Generate expiry date 1 year from now for valid MOTs
        if is_valid:
            expiry_date = (datetime.now().replace(day=1) + timedelta(days=365)).strftime('%Y-%m-%d')
            test_date = (datetime.now().replace(day=1) - timedelta(days=30)).strftime('%Y-%m-%d')
            status_message = f"MOT valid until {expiry_date}"
        else:
            expiry_date = (datetime.now().replace(day=1) - timedelta(days=30)).strftime('%Y-%m-%d')
            test_date = (datetime.now().replace(day=1) - timedelta(days=395)).strftime('%Y-%m-%d')
            status_message = f"MOT expired on {expiry_date}"
        
        return {
            'success': True,
            'registration': registration,
            'is_valid': is_valid,
            'expiry_date': expiry_date,
            'test_date': test_date,
            'status_message': status_message,
            'mileage': 50000,  # Simulated mileage
            'advisory_notes': 'No advisory notes'  # Simulated advisory notes
        }
    
    except Exception as e:
        logger.error(f"Error checking MOT status: {e}")
        return {
            'success': False,
            'registration': registration,
            'error_message': f'Error checking MOT status: {e}'
        }

def bulk_check_mot_status(registrations: list) -> Dict[str, Dict[str, Any]]:
    """
    Check the MOT status of multiple vehicles.
    
    Args:
        registrations (list): List of vehicle registration numbers
        
    Returns:
        dict: Dictionary of MOT status information keyed by registration
    """
    results = {}
    
    for registration in registrations:
        results[registration] = check_mot_status(registration)
    
    return results

def verify_mot_from_file(input_file: str, output_file: str) -> Dict[str, Any]:
    """
    Verify MOT status for vehicles listed in a file.
    
    Args:
        input_file (str): Path to input file with registration numbers
        output_file (str): Path to output file for results
        
    Returns:
        dict: Result of the operation
    """
    try:
        # Check if input file exists
        if not os.path.exists(input_file):
            return {
                'success': False,
                'message': f'Input file not found: {input_file}'
            }
        
        # Read registrations from file
        registrations = []
        with open(input_file, 'r') as f:
            for line in f:
                reg = line.strip()
                if reg:
                    registrations.append(reg)
        
        if not registrations:
            return {
                'success': False,
                'message': 'No registrations found in input file'
            }
        
        # Check MOT status for each registration
        results = bulk_check_mot_status(registrations)
        
        # Write results to output file
        with open(output_file, 'w') as f:
            f.write("Registration,MOT Status,Expiry Date,Test Date,Mileage,Advisory Notes\n")
            for reg, result in results.items():
                if result['success']:
                    f.write(f"{reg},{result['is_valid']},{result['expiry_date']},{result['test_date']},{result['mileage']},{result['advisory_notes']}\n")
                else:
                    f.write(f"{reg},Error,,,{result['error_message']}\n")
        
        return {
            'success': True,
            'message': f'Verified MOT status for {len(registrations)} vehicles',
            'results': results
        }
    
    except Exception as e:
        logger.error(f"Error verifying MOT from file: {e}")
        return {
            'success': False,
            'message': f'Error verifying MOT from file: {e}'
        }
