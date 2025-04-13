#!/usr/bin/env python3
"""
CSV Data Cleaner using PyJanitor

This script cleans CSV data using PyJanitor, a powerful data cleaning library.
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
        logging.FileHandler("janitor_cleaner.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('JanitorCleaner')

def install_pyjanitor():
    """Install pyjanitor if not already installed"""
    try:
        import janitor
        logger.info("pyjanitor is already installed.")
    except ImportError:
        logger.info("Installing pyjanitor...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyjanitor"])
        logger.info("pyjanitor installed successfully.")

def clean_csv_data(input_file, output_file, target_column=None):
    """
    Clean CSV data using PyJanitor
    
    Args:
        input_file (str): Path to input CSV file
        output_file (str): Path to output CSV file
        target_column (str, optional): Name of target column. Defaults to None.
    """
    try:
        # Install pyjanitor if not already installed
        install_pyjanitor()
        
        # Import janitor after ensuring it's installed
        import janitor
        
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
        
        # Clean column names
        logger.info("Cleaning column names...")
        df = df.clean_names()
        
        # Remove empty rows and columns
        logger.info("Removing empty rows and columns...")
        df = df.remove_empty()
        
        # Drop duplicate rows
        logger.info("Removing duplicate rows...")
        df = df.drop_duplicates()
        
        # Identify and convert date columns
        logger.info("Converting date columns...")
        for col in df.columns:
            # Check if column might contain dates
            if df[col].dtype == 'object':
                try:
                    # Try to convert to datetime
                    pd.to_datetime(df[col], errors='raise')
                    # If successful, convert the column
                    df = df.convert_datetime(col)
                    logger.info(f"Converted column '{col}' to datetime")
                except:
                    pass
        
        # Fill missing values
        logger.info("Filling missing values...")
        
        # For numeric columns, fill with median
        numeric_cols = df.select_dtypes(include=['number']).columns
        for col in numeric_cols:
            df = df.impute_values(col, df[col].median())
        
        # For categorical columns, fill with mode
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns
        for col in categorical_cols:
            if not df[col].empty and df[col].mode().size > 0:
                df = df.impute_values(col, df[col].mode()[0])
        
        # Encode categorical variables
        logger.info("Encoding categorical variables...")
        for col in categorical_cols:
            # Only encode if the column has a reasonable number of categories
            if df[col].nunique() < 10:
                try:
                    df = df.encode_categorical(col)
                    logger.info(f"Encoded column '{col}'")
                except:
                    logger.warning(f"Could not encode column '{col}'")
        
        # Remove outliers from numeric columns
        logger.info("Handling outliers...")
        for col in numeric_cols:
            try:
                # Calculate IQR
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                
                # Define bounds
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                # Cap outliers (winsorization)
                df[col] = df[col].clip(lower_bound, upper_bound)
                logger.info(f"Capped outliers in column '{col}'")
            except:
                logger.warning(f"Could not handle outliers in column '{col}'")
        
        # Save cleaned data to CSV
        logger.info(f"Saving cleaned data to: {output_file}")
        df.to_csv(output_file, index=False)
        logger.info("Data cleaning completed successfully!")
        
        # Print summary of changes
        logger.info(f"Original data shape: {original_shape}")
        logger.info(f"Cleaned data shape: {df.shape}")
        
        # Calculate percentage of data cleaned/removed
        rows_removed = original_shape[0] - df.shape[0]
        cols_removed = original_shape[1] - df.shape[1]
        
        if original_shape[0] > 0:
            rows_removed_pct = (rows_removed / original_shape[0]) * 100
            logger.info(f"Rows removed: {rows_removed} ({rows_removed_pct:.2f}%)")
        
        if original_shape[1] > 0:
            cols_removed_pct = (cols_removed / original_shape[1]) * 100
            logger.info(f"Columns removed: {cols_removed} ({cols_removed_pct:.2f}%)")
        
        return df
        
    except Exception as e:
        logger.error(f"Error cleaning CSV data: {e}")
        raise

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Clean CSV data using PyJanitor')
    parser.add_argument('input_file', help='Path to input CSV file')
    parser.add_argument('output_file', help='Path to output CSV file')
    parser.add_argument('--target', help='Name of target column (optional)')
    
    args = parser.parse_args()
    
    clean_csv_data(args.input_file, args.output_file, args.target)

if __name__ == "__main__":
    main()
