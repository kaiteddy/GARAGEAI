"""
DVLA Integration Module for Garage Management System

This module integrates the DVLA Verifier functionality from GA4 with the Garage Management System
to provide automatic MOT status verification and updates.
"""

import os
import sys
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add GA4 installation path to system path to import dvla_verifier
ga4_path = None
common_paths = [
    r"C:\Program Files (x86)\Garage Assistant GA4",
    r"C:\Program Files\Garage Assistant GA4",
    r"C:\Garage Assistant GA4"
]

for path in common_paths:
    if os.path.exists(path) and os.path.isdir(path):
        ga4_path = path
        break

if not ga4_path:
    logger.error("GA4 installation not found. DVLA verification will not be available.")
else:
    logger.info(f"Found GA4 installation at {ga4_path}")
    sys.path.append(ga4_path)

# Try to import the DVLA verifier
try:
    from dvla_verifier import verify_vehicle, verify_multiple_vehicles
    DVLA_AVAILABLE = True
    logger.info("DVLA Verifier module loaded successfully")
except ImportError as e:
    logger.error(f"Could not import DVLA Verifier module: {e}")
    DVLA_AVAILABLE = False


def verify_vehicle_mot(registration: str) -> Dict[str, Any]:
    """
    Verify a vehicle's MOT status using the DVLA Verifier.
    
    Args:
        registration (str): The vehicle registration number
        
    Returns:
        dict: Vehicle information including MOT status
    """
    if not DVLA_AVAILABLE:
        logger.warning("DVLA verification not available")
        return {
            'registration': registration,
            'mot_status': 'Verification Unavailable',
            'expiry_date': None,
            'days_remaining': None,
            'make': None,
            'model': None,
            'color': None,
            'fuel_type': None,
            'source': 'None'
        }
    
    try:
        result = verify_vehicle(registration)
        logger.info(f"MOT verification completed for {registration}: {result.get('mot_status', 'Unknown')}")
        return result
    except Exception as e:
        logger.error(f"Error verifying MOT status for {registration}: {e}")
        return {
            'registration': registration,
            'mot_status': 'Error',
            'expiry_date': None,
            'days_remaining': None,
            'make': None,
            'model': None,
            'color': None,
            'fuel_type': None,
            'source': 'Error',
            'error': str(e)
        }


def batch_verify_vehicles(db_path: str, limit: int = 50) -> Tuple[int, int]:
    """
    Verify MOT status for multiple vehicles in the database.
    
    Args:
        db_path (str): Path to the database
        limit (int): Maximum number of vehicles to verify in one batch
        
    Returns:
        tuple: (number of vehicles verified, number of updates made)
    """
    if not DVLA_AVAILABLE:
        logger.warning("DVLA verification not available")
        return (0, 0)
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get vehicles that need verification
        # Prioritize vehicles with:
        # 1. No MOT expiry date
        # 2. MOT expiry date within the next 60 days
        # 3. MOT expiry date that hasn't been verified in the last 7 days
        cursor.execute("""
        SELECT id, registration, mot_expiry, make, model
        FROM vehicles
        WHERE registration IS NOT NULL AND registration != ''
        AND (
            mot_expiry IS NULL
            OR julianday(mot_expiry) - julianday('now') BETWEEN 0 AND 60
            OR julianday('now') - julianday(last_mot_check) > 7
            OR last_mot_check IS NULL
        )
        ORDER BY 
            CASE WHEN mot_expiry IS NULL THEN 0 ELSE 1 END,
            CASE WHEN last_mot_check IS NULL THEN 0 ELSE 1 END,
            julianday(mot_expiry) - julianday('now')
        LIMIT ?
        """, (limit,))
        
        vehicles = cursor.fetchall()
        
        if not vehicles:
            logger.info("No vehicles found that need MOT verification")
            conn.close()
            return (0, 0)
        
        logger.info(f"Found {len(vehicles)} vehicles that need MOT verification")
        
        # Prepare registrations for batch verification
        registrations = [vehicle['registration'] for vehicle in vehicles]
        
        # Verify vehicles in batch
        results = verify_multiple_vehicles(registrations)
        
        # Update database with results
        updates = 0
        
        for vehicle, result in zip(vehicles, results):
            if not result or result.get('mot_status') == 'Unknown':
                # Skip if verification failed
                continue
            
            # Extract data from result
            mot_status = result.get('mot_status')
            expiry_date = result.get('expiry_date')
            make = result.get('make')
            model = result.get('model')
            color = result.get('color')
            fuel_type = result.get('fuel_type')
            
            # Prepare update data
            update_data = {
                'last_mot_check': datetime.now().strftime('%Y-%m-%d'),
                'mot_status': mot_status
            }
            
            # Only update expiry date if it's provided and valid
            if expiry_date:
                try:
                    # Convert to standard format if needed
                    if '/' in expiry_date:
                        # DD/MM/YYYY format
                        date_obj = datetime.strptime(expiry_date, '%d/%m/%Y')
                        update_data['mot_expiry'] = date_obj.strftime('%Y-%m-%d')
                    else:
                        # Assume YYYY-MM-DD format
                        update_data['mot_expiry'] = expiry_date
                except ValueError:
                    logger.error(f"Invalid date format: {expiry_date}")
            
            # Update vehicle details if they're missing
            if make and not vehicle['make']:
                update_data['make'] = make
            
            if model and not vehicle['model']:
                update_data['model'] = model
            
            if color:
                update_data['color'] = color
            
            if fuel_type:
                update_data['fuel_type'] = fuel_type
            
            # Build SQL update statement
            set_clause = ", ".join([f"{key} = ?" for key in update_data.keys()])
            values = list(update_data.values())
            values.append(vehicle['id'])
            
            cursor.execute(f"UPDATE vehicles SET {set_clause} WHERE id = ?", values)
            
            # Log the update
            logger.info(f"Updated vehicle {vehicle['registration']} with MOT status: {mot_status}")
            updates += 1
            
            # Create reminder if MOT is expiring soon
            if mot_status == 'Valid' and expiry_date:
                try:
                    # Parse expiry date
                    if '/' in expiry_date:
                        expiry_date_obj = datetime.strptime(expiry_date, '%d/%m/%Y')
                    else:
                        expiry_date_obj = datetime.strptime(expiry_date, '%Y-%m-%d')
                    
                    # Calculate days remaining
                    days_remaining = (expiry_date_obj - datetime.now()).days
                    
                    # Create reminder if within reminder thresholds
                    if 0 < days_remaining <= 30:
                        # Check if reminder already exists
                        cursor.execute("""
                        SELECT id FROM mot_reminders
                        WHERE vehicle_id = ? AND reminder_type = 'MOT Due' AND status = 'Pending'
                        """, (vehicle['id'],))
                        
                        if not cursor.fetchone():
                            # Create new reminder
                            cursor.execute("""
                            INSERT INTO mot_reminders (vehicle_id, reminder_type, status, created_at)
                            VALUES (?, 'MOT Due', 'Pending', CURRENT_TIMESTAMP)
                            """, (vehicle['id'],))
                            
                            logger.info(f"Created MOT reminder for {vehicle['registration']} (expires in {days_remaining} days)")
                except Exception as e:
                    logger.error(f"Error creating reminder for {vehicle['registration']}: {e}")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        return (len(vehicles), updates)
    
    except Exception as e:
        logger.error(f"Error in batch verification: {e}")
        return (0, 0)


def schedule_mot_verification(db_path: str, interval_minutes: int = 60, batch_size: int = 50):
    """
    Schedule regular MOT verification for vehicles in the database.
    
    Args:
        db_path (str): Path to the database
        interval_minutes (int): Interval between verification runs in minutes
        batch_size (int): Number of vehicles to verify in each batch
    """
    if not DVLA_AVAILABLE:
        logger.warning("DVLA verification not available, skipping scheduler")
        return
    
    from apscheduler.schedulers.background import BackgroundScheduler
    
    def verification_job():
        logger.info("Running scheduled MOT verification")
        verified, updated = batch_verify_vehicles(db_path, batch_size)
        logger.info(f"Verified {verified} vehicles, updated {updated}")
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(verification_job, 'interval', minutes=interval_minutes)
    scheduler.start()
    
    logger.info(f"Scheduled MOT verification to run every {interval_minutes} minutes")


def verify_single_vehicle_and_update(db_path: str, vehicle_id: int) -> Dict[str, Any]:
    """
    Verify a single vehicle's MOT status and update the database.
    
    Args:
        db_path (str): Path to the database
        vehicle_id (int): ID of the vehicle to verify
        
    Returns:
        dict: Result of the verification
    """
    if not DVLA_AVAILABLE:
        return {
            'success': False,
            'message': 'DVLA verification not available',
            'mot_status': 'Verification Unavailable'
        }
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get vehicle details
        cursor.execute("SELECT id, registration, mot_expiry, make, model FROM vehicles WHERE id = ?", (vehicle_id,))
        vehicle = cursor.fetchone()
        
        if not vehicle:
            conn.close()
            return {
                'success': False,
                'message': 'Vehicle not found',
                'mot_status': 'Unknown'
            }
        
        if not vehicle['registration']:
            conn.close()
            return {
                'success': False,
                'message': 'Vehicle has no registration number',
                'mot_status': 'Unknown'
            }
        
        # Verify MOT status
        result = verify_vehicle(vehicle['registration'])
        
        if not result or result.get('mot_status') == 'Unknown':
            conn.close()
            return {
                'success': False,
                'message': 'Verification failed',
                'mot_status': 'Unknown'
            }
        
        # Extract data from result
        mot_status = result.get('mot_status')
        expiry_date = result.get('expiry_date')
        make = result.get('make')
        model = result.get('model')
        color = result.get('color')
        fuel_type = result.get('fuel_type')
        
        # Prepare update data
        update_data = {
            'last_mot_check': datetime.now().strftime('%Y-%m-%d'),
            'mot_status': mot_status
        }
        
        # Only update expiry date if it's provided and valid
        if expiry_date:
            try:
                # Convert to standard format if needed
                if '/' in expiry_date:
                    # DD/MM/YYYY format
                    date_obj = datetime.strptime(expiry_date, '%d/%m/%Y')
                    update_data['mot_expiry'] = date_obj.strftime('%Y-%m-%d')
                else:
                    # Assume YYYY-MM-DD format
                    update_data['mot_expiry'] = expiry_date
            except ValueError:
                logger.error(f"Invalid date format: {expiry_date}")
        
        # Update vehicle details if they're missing
        if make and not vehicle['make']:
            update_data['make'] = make
        
        if model and not vehicle['model']:
            update_data['model'] = model
        
        if color:
            update_data['color'] = color
        
        if fuel_type:
            update_data['fuel_type'] = fuel_type
        
        # Build SQL update statement
        set_clause = ", ".join([f"{key} = ?" for key in update_data.keys()])
        values = list(update_data.values())
        values.append(vehicle_id)
        
        cursor.execute(f"UPDATE vehicles SET {set_clause} WHERE id = ?", values)
        
        # Commit changes
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': 'Vehicle updated successfully',
            'mot_status': mot_status,
            'expiry_date': expiry_date,
            'result': result
        }
    
    except Exception as e:
        logger.error(f"Error verifying vehicle {vehicle_id}: {e}")
        return {
            'success': False,
            'message': f'Error: {str(e)}',
            'mot_status': 'Error'
        }
