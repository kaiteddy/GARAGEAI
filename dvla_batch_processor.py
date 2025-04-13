#!/usr/bin/env python3
"""
DVLA Vehicle Enquiry Service Batch Processor

This script processes multiple vehicle registrations from a CSV file
and retrieves their details from the DVLA Vehicle Enquiry Service API.
"""

import argparse
import csv
import json
import logging
import os
import sys
import time
from datetime import datetime

import pandas as pd
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("dvla_batch.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('DVLABatchProcessor')

# Constants
API_ENDPOINT = "https://driver-vehicle-licensing.api.gov.uk/vehicle-enquiry/v1/vehicles"
DEFAULT_API_KEY = "AXPW4KqAyS4G7eb53rav46TzufDC3a1v2yJUCJAi"  # Your API key
RATE_LIMIT_DELAY = 1  # Delay between API calls in seconds to avoid rate limiting

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
        registration_number = str(registration_number).strip().upper().replace(" ", "")
        
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
                    logger.error(f"API Error for {registration_number}: {error.get('title')} ({error.get('code')}) - {error.get('detail')}")
                    return {"registrationNumber": registration_number, "error": error.get('detail')}
                else:
                    logger.error(f"Bad Request for {registration_number}: {error_data.get('message', str(e))}")
                    return {"registrationNumber": registration_number, "error": error_data.get('message', str(e))}
            elif response.status_code == 401:
                logger.error(f"Authentication Error for {registration_number}: Invalid API key")
                return {"registrationNumber": registration_number, "error": "Authentication Error: Invalid API key"}
            elif response.status_code == 429:
                logger.error(f"Rate Limit Exceeded for {registration_number}: Too many requests")
                return {"registrationNumber": registration_number, "error": "Rate Limit Exceeded: Too many requests"}
            else:
                logger.error(f"HTTP Error for {registration_number}: {e}")
                return {"registrationNumber": registration_number, "error": f"HTTP Error: {e}"}
        except requests.exceptions.RequestException as e:
            logger.error(f"Request Error for {registration_number}: {e}")
            return {"registrationNumber": registration_number, "error": f"Request Error: {e}"}
        except ValueError as e:
            logger.error(f"JSON Parsing Error for {registration_number}: {e}")
            return {"registrationNumber": registration_number, "error": f"JSON Parsing Error: {e}"}
        except Exception as e:
            logger.error(f"Unexpected Error for {registration_number}: {e}")
            return {"registrationNumber": registration_number, "error": f"Unexpected Error: {e}"}

def process_csv_file(input_file, api_key, column_name=None, skip_header=True):
    """Process a CSV file containing vehicle registration numbers.
    
    Args:
        input_file (str): Path to the input CSV file
        api_key (str): DVLA API key
        column_name (str, optional): Name of the column containing registration numbers
        skip_header (bool): Whether to skip the header row
        
    Returns:
        list: List of vehicle details dictionaries
    """
    results = []
    client = DVLAVehicleEnquiry(api_key)
    
    try:
        # Read the CSV file
        df = pd.read_csv(input_file)
        
        # If column_name is not provided, try to find a column that might contain registration numbers
        if column_name is None:
            # Look for columns with names like 'reg', 'registration', 'vrm', etc.
            possible_columns = [col for col in df.columns if any(
                keyword in col.lower() for keyword in ['reg', 'registration', 'vrm', 'plate', 'number']
            )]
            
            if possible_columns:
                column_name = possible_columns[0]
                logger.info(f"Using column '{column_name}' for registration numbers")
            else:
                # If no suitable column is found, use the first column
                column_name = df.columns[0]
                logger.info(f"No registration column specified, using first column: '{column_name}'")
        
        # Check if the column exists
        if column_name not in df.columns:
            logger.error(f"Column '{column_name}' not found in the CSV file")
            return results
        
        # Process each registration number
        total_rows = len(df)
        for index, row in df.iterrows():
            reg_number = row[column_name]
            
            # Skip empty values
            if pd.isna(reg_number) or reg_number == "":
                logger.warning(f"Skipping empty registration number at row {index + 2}")
                continue
            
            # Get vehicle details
            logger.info(f"Processing {index + 1}/{total_rows}: {reg_number}")
            vehicle_data = client.get_vehicle_details(reg_number)
            results.append(vehicle_data)
            
            # Add a delay to avoid rate limiting
            if index < total_rows - 1:
                time.sleep(RATE_LIMIT_DELAY)
        
        return results
    
    except Exception as e:
        logger.error(f"Error processing CSV file: {e}")
        raise

def save_results_to_csv(results, output_file=None):
    """Save results to a CSV file.
    
    Args:
        results (list): List of vehicle details dictionaries
        output_file (str, optional): Output filename. If None, a default name will be used.
        
    Returns:
        str: Path to the saved file
    """
    if not results:
        logger.warning("No results to save")
        return None
    
    if output_file is None:
        output_file = f"dvla_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    try:
        # Convert results to a DataFrame
        df = pd.DataFrame(results)
        
        # Save to CSV
        df.to_csv(output_file, index=False)
        
        logger.info(f"Results saved to {output_file}")
        return output_file
    
    except Exception as e:
        logger.error(f"Error saving results to CSV: {e}")
        raise

def save_results_to_excel(results, output_file=None):
    """Save results to an Excel file.
    
    Args:
        results (list): List of vehicle details dictionaries
        output_file (str, optional): Output filename. If None, a default name will be used.
        
    Returns:
        str: Path to the saved file
    """
    if not results:
        logger.warning("No results to save")
        return None
    
    if output_file is None:
        output_file = f"dvla_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    try:
        # Convert results to a DataFrame
        df = pd.DataFrame(results)
        
        # Save to Excel
        df.to_excel(output_file, index=False)
        
        logger.info(f"Results saved to {output_file}")
        return output_file
    
    except Exception as e:
        logger.error(f"Error saving results to Excel: {e}")
        raise

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='DVLA Vehicle Enquiry Service Batch Processor')
    parser.add_argument('input_file', help='Path to the input CSV file containing vehicle registration numbers')
    parser.add_argument('--api-key', help='Your DVLA API key (optional, will use default if not provided)')
    parser.add_argument('--column', help='Name of the column containing registration numbers')
    parser.add_argument('--output', help='Output filename (optional)')
    parser.add_argument('--format', choices=['csv', 'excel', 'json'], default='csv', help='Output format (default: csv)')
    parser.add_argument('--no-header', action='store_true', help='CSV file has no header row')
    
    args = parser.parse_args()
    
    try:
        # Check if the input file exists
        if not os.path.isfile(args.input_file):
            logger.error(f"Input file not found: {args.input_file}")
            sys.exit(1)
        
        # Process the CSV file
        api_key = args.api_key if args.api_key else DEFAULT_API_KEY
        results = process_csv_file(args.input_file, api_key, args.column, not args.no_header)
        
        # Save the results
        if args.format == 'csv':
            output_file = args.output if args.output else None
            save_results_to_csv(results, output_file)
        elif args.format == 'excel':
            output_file = args.output if args.output else None
            save_results_to_excel(results, output_file)
        elif args.format == 'json':
            output_file = args.output if args.output else f"dvla_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=4)
            logger.info(f"Results saved to {output_file}")
        
        # Print summary
        total = len(results)
        errors = sum(1 for r in results if 'error' in r)
        success = total - errors
        
        print(f"\nSummary:")
        print(f"Total registrations processed: {total}")
        print(f"Successful queries: {success}")
        print(f"Failed queries: {errors}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
