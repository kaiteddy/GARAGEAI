#!/usr/bin/env python3
"""
DVLA Vehicle Enquiry Service API Client

This script provides a simple interface to the DVLA Vehicle Enquiry Service API.
It allows you to query vehicle information by registration number.
"""

import argparse
import json
import logging
import sys
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("dvla_enquiry.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('DVLAEnquiry')

# Constants
API_ENDPOINT = "https://driver-vehicle-licensing.api.gov.uk/vehicle-enquiry/v1/vehicles"
DEFAULT_API_KEY = "AXPW4KqAyS4G7eb53rav46TzufDC3a1v2yJUCJAi"  # Your API key

class DVLAVehicleEnquiry:
    """DVLA Vehicle Enquiry Service API Client"""
    
    def __init__(self, api_key=DEFAULT_API_KEY):
        """Initialize the DVLA Vehicle Enquiry Service API client.
        
        Args:
            api_key (str): Your DVLA Vehicle Enquiry Service API key
        """
        self.api_key = api_key
        self.session = requests.Session()
    
    def get_vehicle_details(self, registration_number):
        """Get vehicle details by registration number.
        
        Args:
            registration_number (str): The vehicle registration number
            
        Returns:
            dict: Vehicle details
            
        Raises:
            Exception: If the API request fails
        """
        # Clean and format the registration number
        registration_number = registration_number.strip().upper().replace(" ", "")
        
        # Prepare the request
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key
        }
        
        payload = {
            "registrationNumber": registration_number
        }
        
        try:
            # Make the request
            logger.info(f"Querying DVLA API for vehicle: {registration_number}")
            response = self.session.post(API_ENDPOINT, headers=headers, json=payload)
            
            # Check if the request was successful
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            
            # Format dates for better readability
            for key in data:
                if isinstance(data[key], str) and key.lower().endswith(('date', 'expirydate', 'duedate')):
                    try:
                        # Try to parse and format the date
                        date_obj = datetime.strptime(data[key], "%Y-%m-%d")
                        data[key] = date_obj.strftime("%d/%m/%Y")
                    except ValueError:
                        # If date parsing fails, keep the original value
                        pass
            
            return data
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 400:
                error_data = response.json()
                if "errors" in error_data:
                    error = error_data["errors"][0]
                    logger.error(f"API Error: {error.get('title')} ({error.get('code')}) - {error.get('detail')}")
                    raise Exception(f"API Error: {error.get('detail')}")
                else:
                    logger.error(f"Bad Request: {error_data.get('message', str(e))}")
                    raise Exception(f"Bad Request: {error_data.get('message', str(e))}")
            elif response.status_code == 401:
                logger.error("Authentication Error: Invalid API key")
                raise Exception("Authentication Error: Invalid API key")
            elif response.status_code == 429:
                logger.error("Rate Limit Exceeded: Too many requests")
                raise Exception("Rate Limit Exceeded: Too many requests")
            else:
                logger.error(f"HTTP Error: {e}")
                raise Exception(f"HTTP Error: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request Error: {e}")
            raise Exception(f"Request Error: {e}")
        except ValueError as e:
            logger.error(f"JSON Parsing Error: {e}")
            raise Exception(f"JSON Parsing Error: {e}")
        except Exception as e:
            logger.error(f"Unexpected Error: {e}")
            raise Exception(f"Unexpected Error: {e}")

def format_vehicle_details(vehicle_data):
    """Format vehicle details for display.
    
    Args:
        vehicle_data (dict): Vehicle details from the API
        
    Returns:
        str: Formatted vehicle details
    """
    # Define the order and labels for the fields
    field_order = [
        ("registrationNumber", "Registration Number"),
        ("make", "Make"),
        ("colour", "Colour"),
        ("yearOfManufacture", "Year of Manufacture"),
        ("engineCapacity", "Engine Capacity (cc)"),
        ("fuelType", "Fuel Type"),
        ("co2Emissions", "CO2 Emissions"),
        ("taxStatus", "Tax Status"),
        ("taxDueDate", "Tax Due Date"),
        ("motStatus", "MOT Status"),
        ("motExpiryDate", "MOT Expiry Date"),
        ("wheelplan", "Wheelplan"),
        ("monthOfFirstRegistration", "Month of First Registration"),
        ("typeApproval", "Type Approval"),
        ("revenueWeight", "Revenue Weight (kg)"),
        ("euroStatus", "Euro Status"),
        ("realDrivingEmissions", "Real Driving Emissions"),
        ("dateOfLastV5CIssued", "Date of Last V5C Issued"),
        ("markedForExport", "Marked For Export"),
        ("artEndDate", "ART End Date")
    ]
    
    # Build the formatted output
    output = []
    output.append("=" * 50)
    output.append("DVLA VEHICLE ENQUIRY RESULTS")
    output.append("=" * 50)
    
    for field, label in field_order:
        if field in vehicle_data and vehicle_data[field] is not None:
            output.append(f"{label}: {vehicle_data[field]}")
    
    output.append("=" * 50)
    
    return "\n".join(output)

def save_to_json(vehicle_data, filename=None):
    """Save vehicle details to a JSON file.
    
    Args:
        vehicle_data (dict): Vehicle details from the API
        filename (str, optional): Output filename. If None, a default name will be used.
        
    Returns:
        str: Path to the saved file
    """
    if filename is None:
        reg_number = vehicle_data.get("registrationNumber", "unknown")
        filename = f"vehicle_{reg_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, 'w') as f:
        json.dump(vehicle_data, f, indent=4)
    
    return filename

def save_to_csv(vehicle_data, filename=None):
    """Save vehicle details to a CSV file.
    
    Args:
        vehicle_data (dict): Vehicle details from the API
        filename (str, optional): Output filename. If None, a default name will be used.
        
    Returns:
        str: Path to the saved file
    """
    import csv
    
    if filename is None:
        reg_number = vehicle_data.get("registrationNumber", "unknown")
        filename = f"vehicle_{reg_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Field', 'Value'])
        for key, value in vehicle_data.items():
            writer.writerow([key, value])
    
    return filename

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='DVLA Vehicle Enquiry Service API Client')
    parser.add_argument('registration', help='Vehicle registration number')
    parser.add_argument('--api-key', help='Your DVLA API key (optional, will use default if not provided)')
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    parser.add_argument('--save-json', action='store_true', help='Save results to a JSON file')
    parser.add_argument('--save-csv', action='store_true', help='Save results to a CSV file')
    parser.add_argument('--output', help='Output filename (optional)')
    
    args = parser.parse_args()
    
    try:
        # Create the DVLA client
        api_key = args.api_key if args.api_key else DEFAULT_API_KEY
        client = DVLAVehicleEnquiry(api_key)
        
        # Get vehicle details
        vehicle_data = client.get_vehicle_details(args.registration)
        
        # Output the results
        if args.json:
            print(json.dumps(vehicle_data, indent=4))
        else:
            print(format_vehicle_details(vehicle_data))
        
        # Save to file if requested
        if args.save_json:
            filename = save_to_json(vehicle_data, args.output)
            print(f"\nResults saved to: {filename}")
        
        if args.save_csv:
            filename = save_to_csv(vehicle_data, args.output)
            print(f"\nResults saved to: {filename}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
