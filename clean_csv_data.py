#!/usr/bin/env python3
"""
CSV Data Cleaner

This script cleans CSV data using pandas_dq, a powerful data quality library.
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
        logging.FileHandler("csv_cleaner.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('CSVCleaner')

def install_pandas_dq():
    """Install pandas_dq if not already installed"""
    try:
        import pandas_dq
        logger.info("pandas_dq is already installed.")
    except ImportError:
        logger.info("Installing pandas_dq...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas_dq"])
        logger.info("pandas_dq installed successfully.")

def clean_csv_data(input_file, output_file, target_column=None, html_report=False):
    """
    Clean CSV data using pandas_dq
    
    Args:
        input_file (str): Path to input CSV file
        output_file (str): Path to output CSV file
        target_column (str, optional): Name of target column. Defaults to None.
        html_report (bool, optional): Whether to generate HTML report. Defaults to False.
    """
    try:
        # Install pandas_dq if not already installed
        install_pandas_dq()
        
        # Import pandas_dq after ensuring it's installed
        from pandas_dq import dq_report, Fix_DQ
        
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
        
        # Generate data quality report
        logger.info("Generating data quality report...")
        dqr = dq_report(df, target=target_column, html=html_report, verbose=1)
        logger.info("Data quality report generated.")
        
        # Fix data quality issues
        logger.info("Fixing data quality issues...")
        fdq = Fix_DQ(
            quantile=0.75,  # For outlier detection
            cat_fill_value="missing",  # Fill value for categorical variables
            num_fill_value=np.nan,  # Fill value for numerical variables
            rare_threshold=0.01,  # Threshold for rare categories
            correlation_threshold=0.9  # Threshold for correlation
        )
        
        # If target column is specified, separate it from the features
        if target_column and target_column in df.columns:
            X = df.drop(columns=[target_column])
            y = df[target_column]
            
            # Fix data quality issues in features
            X_cleaned = fdq.fit_transform(X)
            
            # Combine features and target
            df_cleaned = pd.concat([X_cleaned, y], axis=1)
        else:
            # Fix data quality issues in the entire dataframe
            df_cleaned = fdq.fit_transform(df)
        
        # Save cleaned data to CSV
        logger.info(f"Saving cleaned data to: {output_file}")
        df_cleaned.to_csv(output_file, index=False)
        logger.info("Data cleaning completed successfully!")
        
        # Print summary of changes
        logger.info(f"Original data shape: {df.shape}")
        logger.info(f"Cleaned data shape: {df_cleaned.shape}")
        
        # Calculate percentage of data cleaned/removed
        rows_removed = df.shape[0] - df_cleaned.shape[0]
        cols_removed = df.shape[1] - df_cleaned.shape[1]
        
        if df.shape[0] > 0:
            rows_removed_pct = (rows_removed / df.shape[0]) * 100
            logger.info(f"Rows removed: {rows_removed} ({rows_removed_pct:.2f}%)")
        
        if df.shape[1] > 0:
            cols_removed_pct = (cols_removed / df.shape[1]) * 100
            logger.info(f"Columns removed: {cols_removed} ({cols_removed_pct:.2f}%)")
        
        return df_cleaned
        
    except Exception as e:
        logger.error(f"Error cleaning CSV data: {e}")
        raise

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Clean CSV data using pandas_dq')
    parser.add_argument('input_file', help='Path to input CSV file')
    parser.add_argument('output_file', help='Path to output CSV file')
    parser.add_argument('--target', help='Name of target column (optional)')
    parser.add_argument('--html', action='store_true', help='Generate HTML report')
    
    args = parser.parse_args()
    
    clean_csv_data(args.input_file, args.output_file, args.target, args.html)

if __name__ == "__main__":
    main()
