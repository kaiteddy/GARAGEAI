#!/usr/bin/env python3
"""
CSV Data Cleaner using AutoClean

This script cleans CSV data using AutoClean, a powerful automated data cleaning library.
It handles various data issues and ensures proper data quality.
"""

import os
import sys
import pandas as pd
import numpy as np
import argparse
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("autoclean_cleaner.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('AutoCleanCleaner')

def install_autoclean():
    """Install AutoClean if not already installed"""
    try:
        from AutoClean import AutoClean
        logger.info("AutoClean is already installed.")
    except ImportError:
        logger.info("Installing AutoClean...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "py-AutoClean"])
        logger.info("AutoClean installed successfully.")

def clean_csv_data(input_file, output_file):
    """
    Clean CSV data using AutoClean
    
    Args:
        input_file (str): Path to input CSV file
        output_file (str): Path to output CSV file
    """
    try:
        # Install AutoClean if not already installed
        install_autoclean()
        
        # Import AutoClean after ensuring it's installed
        from AutoClean import AutoClean
        
        logger.info(f"Reading CSV file: {input_file}")
        
        # Try to read the CSV file with different encodings
        encodings = ['utf-8', 'latin1', 'ISO-8859-1', 'cp1252']
        df = None
        
        for encoding in encodings:
            try:
                df = pd.read_csv(input_file, encoding=encoding, low_memory=False)
                logger.info(f"Successfully read CSV with encoding: {encoding}")
                break
            except Exception as e:
                logger.warning(f"Failed to read CSV with encoding {encoding}: {e}")
        
        if df is None:
            logger.error("Failed to read CSV with any encoding. Exiting.")
            return
        
        # Store original shape for comparison
        original_shape = df.shape
        
        # Clean data using AutoClean
        logger.info("Cleaning data using AutoClean...")
        
        # Create AutoClean pipeline with all cleaning steps enabled
        pipeline = AutoClean(
            df,
            mode='auto',
            duplicates='auto',
            missing_num='auto',
            missing_categ='auto',
            encode_categ='auto',
            extract_datetime='auto',
            outliers='auto',
            outlier_param=1.5,
            logfile=True,
            verbose=True
        )
        
        # Get the cleaned dataframe
        df_cleaned = pipeline.output
        
        # Save cleaned data to CSV
        logger.info(f"Saving cleaned data to: {output_file}")
        df_cleaned.to_csv(output_file, index=False)
        logger.info("Data cleaning completed successfully!")
        
        # Print summary of changes
        logger.info(f"Original data shape: {original_shape}")
        logger.info(f"Cleaned data shape: {df_cleaned.shape}")
        
        # Calculate percentage of data cleaned/removed
        rows_removed = original_shape[0] - df_cleaned.shape[0]
        cols_removed = original_shape[1] - df_cleaned.shape[1]
        
        if original_shape[0] > 0:
            rows_removed_pct = (rows_removed / original_shape[0]) * 100
            logger.info(f"Rows removed: {rows_removed} ({rows_removed_pct:.2f}%)")
        
        if original_shape[1] > 0:
            cols_removed_pct = (cols_removed / original_shape[1]) * 100
            logger.info(f"Columns removed: {cols_removed} ({cols_removed_pct:.2f}%)")
        
        return df_cleaned
        
    except Exception as e:
        logger.error(f"Error cleaning CSV data: {e}")
        raise

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Clean CSV data using AutoClean')
    parser.add_argument('input_file', help='Path to input CSV file')
    parser.add_argument('output_file', help='Path to output CSV file')
    
    args = parser.parse_args()
    
    clean_csv_data(args.input_file, args.output_file)

if __name__ == "__main__":
    main()
