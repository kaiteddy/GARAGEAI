#!/usr/bin/env python3
"""
GA4 Export Analyzer

This script analyzes GA4 export files to understand their structure and content.
"""

import os
import sys
import csv
import logging
from collections import Counter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('GA4ExportAnalyzer')

def analyze_csv_file(file_path):
    """Analyze a CSV file to understand its structure"""
    logger.info(f"Analyzing CSV file: {file_path}")
    
    try:
        # Try to determine the delimiter
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            sample = f.read(4096)
            
        # Count occurrences of potential delimiters
        delimiter_counts = Counter(char for char in sample if char in ',;|\t')
        delimiter = max(delimiter_counts.items(), key=lambda x: x[1])[0] if delimiter_counts else ','
        
        logger.info(f"Detected delimiter: '{delimiter}'")
        
        # Read the CSV file
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f, delimiter=delimiter)
            
            # Get headers
            try:
                headers = next(reader)
                logger.info(f"Found {len(headers)} columns")
                
                # Display headers
                for i, header in enumerate(headers):
                    logger.info(f"  Column {i+1}: '{header}'")
                
                # Sample data
                logger.info("Sample data rows:")
                for i, row in enumerate(reader):
                    if i >= 3:  # Only show first 3 rows
                        break
                    
                    # Handle rows with fewer columns than headers
                    row_data = {}
                    for j, value in enumerate(row):
                        if j < len(headers):
                            row_data[headers[j]] = value
                    
                    logger.info(f"  Row {i+1}: {row_data}")
            except StopIteration:
                logger.warning("File appears to be empty or has no data rows")
    
    except Exception as e:
        logger.error(f"Error analyzing CSV file: {e}")

def analyze_ga4_exports():
    """Analyze GA4 export files"""
    ga4_data_path = r"C:\GA4 User Data\Data Exports"
    
    if not os.path.exists(ga4_data_path):
        logger.error(f"GA4 data path not found: {ga4_data_path}")
        return
    
    # Get list of CSV files
    csv_files = [os.path.join(ga4_data_path, f) for f in os.listdir(ga4_data_path) if f.endswith('.csv')]
    
    logger.info(f"Found {len(csv_files)} CSV files in {ga4_data_path}")
    
    # Analyze each file
    for file_path in csv_files:
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path) / 1024  # Size in KB
        
        logger.info(f"File: {file_name} (Size: {file_size:.2f} KB)")
        
        # Only analyze customer and vehicle files in detail
        if "Customer" in file_name or "Vehicle" in file_name:
            analyze_csv_file(file_path)
        else:
            logger.info(f"Skipping detailed analysis of {file_name}")

if __name__ == "__main__":
    logger.info("Starting GA4 Export Analyzer")
    analyze_ga4_exports()
    logger.info("GA4 Export Analyzer completed")
