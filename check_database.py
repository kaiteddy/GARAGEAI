#!/usr/bin/env python3
"""
Database Check Tool - Examines the database structure and contents
"""

import os
import sys
import sqlite3
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('DatabaseCheck')

def check_database():
    """Check the database structure and contents"""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'garage_system.db')
    
    if not os.path.exists(db_path):
        logger.error(f"Database not found at {db_path}")
        return
    
    logger.info(f"Checking database at {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    logger.info(f"Found {len(tables)} tables in database:")
    for table in tables:
        logger.info(f"  Table: {table[0]}")
        
        # Get table schema
        cursor.execute(f"PRAGMA table_info({table[0]})")
        columns = cursor.fetchall()
        logger.info(f"  Schema for {table[0]}:")
        for column in columns:
            logger.info(f"    {column[1]} ({column[2]})")
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        row_count = cursor.fetchone()[0]
        logger.info(f"  Row count for {table[0]}: {row_count}")
        
        # Get sample data
        cursor.execute(f"SELECT * FROM {table[0]} LIMIT 5")
        rows = cursor.fetchall()
        if rows:
            logger.info(f"  Sample data for {table[0]}:")
            for row in rows:
                logger.info(f"    {row}")
    
    conn.close()
    logger.info("Database check completed")

if __name__ == "__main__":
    logger.info("Starting Database Check Tool")
    check_database()
    logger.info("Database Check Tool completed")
