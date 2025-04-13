#!/usr/bin/env python3
"""
Master CSV Data Cleaner

This script combines multiple data cleaning libraries (pandas_dq, PyJanitor, and AutoClean)
to provide the most thorough cleaning of CSV data possible.
"""

import os
import sys
import pandas as pd
import numpy as np
import argparse
from datetime import datetime
import logging
import subprocess
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("master_cleaner.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('MasterCleaner')

def install_libraries():
    """Install required libraries if not already installed"""
    libraries = [
        "pandas_dq",
        "pyjanitor",
        "py-AutoClean"
    ]
    
    for lib in libraries:
        try:
            if lib == "pandas_dq":
                import pandas_dq
                logger.info("pandas_dq is already installed.")
            elif lib == "pyjanitor":
                import janitor
                logger.info("pyjanitor is already installed.")
            elif lib == "py-AutoClean":
                from AutoClean import AutoClean
                logger.info("AutoClean is already installed.")
        except ImportError:
            logger.info(f"Installing {lib}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", lib])
            logger.info(f"{lib} installed successfully.")
            
            # Give some time for the installation to complete
            time.sleep(2)

def read_csv_with_multiple_encodings(input_file):
    """
    Try to read a CSV file with multiple encodings
    
    Args:
        input_file (str): Path to input CSV file
        
    Returns:
        pandas.DataFrame: DataFrame containing the CSV data
    """
    encodings = ['utf-8', 'latin1', 'ISO-8859-1', 'cp1252']
    df = None
    
    for encoding in encodings:
        try:
            df = pd.read_csv(input_file, encoding=encoding, low_memory=False)
            logger.info(f"Successfully read CSV with encoding: {encoding}")
            return df
        except Exception as e:
            logger.warning(f"Failed to read CSV with encoding {encoding}: {e}")
    
    if df is None:
        logger.error("Failed to read CSV with any encoding.")
        return None

def clean_with_pandas_dq(df, target_column=None):
    """
    Clean data using pandas_dq
    
    Args:
        df (pandas.DataFrame): DataFrame to clean
        target_column (str, optional): Name of target column. Defaults to None.
        
    Returns:
        pandas.DataFrame: Cleaned DataFrame
    """
    try:
        from pandas_dq import dq_report, Fix_DQ
        
        logger.info("Cleaning data with pandas_dq...")
        
        # Generate data quality report
        dqr = dq_report(df, target=target_column, html=True, verbose=1)
        logger.info("Data quality report generated.")
        
        # Fix data quality issues
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
        
        logger.info("Data cleaned with pandas_dq.")
        return df_cleaned
    
    except Exception as e:
        logger.error(f"Error cleaning with pandas_dq: {e}")
        return df

def clean_with_pyjanitor(df):
    """
    Clean data using PyJanitor
    
    Args:
        df (pandas.DataFrame): DataFrame to clean
        
    Returns:
        pandas.DataFrame: Cleaned DataFrame
    """
    try:
        import janitor
        
        logger.info("Cleaning data with PyJanitor...")
        
        # Clean column names
        df = df.clean_names()
        
        # Remove empty rows and columns
        df = df.remove_empty()
        
        # Drop duplicate rows
        df = df.drop_duplicates()
        
        # Identify and convert date columns
        for col in df.columns:
            # Check if column might contain dates
            if df[col].dtype == 'object':
                try:
                    # Try to convert to datetime
                    pd.to_datetime(df[col], errors='raise')
                    # If successful, convert the column
                    df = df.convert_datetime(col)
                except:
                    pass
        
        # Fill missing values
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
        for col in categorical_cols:
            # Only encode if the column has a reasonable number of categories
            if df[col].nunique() < 10:
                try:
                    df = df.encode_categorical(col)
                except:
                    pass
        
        # Remove outliers from numeric columns
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
            except:
                pass
        
        logger.info("Data cleaned with PyJanitor.")
        return df
    
    except Exception as e:
        logger.error(f"Error cleaning with PyJanitor: {e}")
        return df

def clean_with_autoclean(df):
    """
    Clean data using AutoClean
    
    Args:
        df (pandas.DataFrame): DataFrame to clean
        
    Returns:
        pandas.DataFrame: Cleaned DataFrame
    """
    try:
        from AutoClean import AutoClean
        
        logger.info("Cleaning data with AutoClean...")
        
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
            verbose=False
        )
        
        # Get the cleaned dataframe
        df_cleaned = pipeline.output
        
        logger.info("Data cleaned with AutoClean.")
        return df_cleaned
    
    except Exception as e:
        logger.error(f"Error cleaning with AutoClean: {e}")
        return df

def master_clean(input_file, output_file, target_column=None, method='all'):
    """
    Master cleaning function that combines multiple cleaning approaches
    
    Args:
        input_file (str): Path to input CSV file
        output_file (str): Path to output CSV file
        target_column (str, optional): Name of target column. Defaults to None.
        method (str, optional): Cleaning method to use ('all', 'pandas_dq', 'pyjanitor', 'autoclean'). Defaults to 'all'.
    """
    try:
        # Install required libraries
        install_libraries()
        
        # Read CSV file
        logger.info(f"Reading CSV file: {input_file}")
        df = read_csv_with_multiple_encodings(input_file)
        
        if df is None:
            return
        
        # Store original shape for comparison
        original_shape = df.shape
        
        # Clean data using selected method(s)
        if method == 'all' or method == 'pandas_dq':
            df = clean_with_pandas_dq(df, target_column)
        
        if method == 'all' or method == 'pyjanitor':
            df = clean_with_pyjanitor(df)
        
        if method == 'all' or method == 'autoclean':
            df = clean_with_autoclean(df)
        
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
        logger.error(f"Error in master cleaning: {e}")
        raise

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Master CSV Data Cleaner')
    parser.add_argument('input_file', help='Path to input CSV file')
    parser.add_argument('output_file', help='Path to output CSV file')
    parser.add_argument('--target', help='Name of target column (optional)')
    parser.add_argument('--method', choices=['all', 'pandas_dq', 'pyjanitor', 'autoclean'], 
                        default='all', help='Cleaning method to use')
    
    args = parser.parse_args()
    
    master_clean(args.input_file, args.output_file, args.target, args.method)

if __name__ == "__main__":
    main()
