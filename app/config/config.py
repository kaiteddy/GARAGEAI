#!/usr/bin/env python3
"""
Configuration Module

This module handles loading and managing configuration settings for the Garage Management System.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def find_ga4_installation() -> Optional[str]:
    """
    Find the Garage Assistant 4 installation directory.
    
    Returns:
        str: Path to GA4 installation directory, or None if not found
    """
    # Common installation paths
    common_paths = [
        r"C:\Program Files\Garage Assistant GA4",
        r"C:\Program Files (x86)\Garage Assistant GA4",
        r"D:\Program Files\Garage Assistant GA4",
        r"D:\Program Files (x86)\Garage Assistant GA4"
    ]
    
    # Check common paths
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    # Check environment variable
    ga4_path = os.environ.get("GA4_PATH")
    if ga4_path and os.path.exists(ga4_path):
        return ga4_path
    
    return None

def load_config() -> Dict[str, Any]:
    """
    Load configuration from file or create default configuration.
    
    Returns:
        dict: Configuration dictionary
    """
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'garage_system_config.json')
    
    # Default configuration
    default_config = {
        "ga4_path": find_ga4_installation(),
        "database_path": os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'garage_system.db'),
        "ga4_export_dir": os.path.join(find_ga4_installation() or "", "exports") if find_ga4_installation() else "",
        "auto_sync_interval": 15,  # minutes
        "mot_verify_interval": 60,  # minutes
        "reminder_days_before": 30,
        "smtp_server": "",
        "smtp_port": 587,
        "smtp_username": "",
        "smtp_password": "",
        "sender_email": "",
        "dvla_api_key": ""
    }
    
    # Create data directory if it doesn't exist
    data_dir = os.path.dirname(default_config["database_path"])
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # Load existing configuration or create default
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                
            # Update with any missing default values
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
                    
            logger.info("Loaded configuration from file")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            config = default_config
    else:
        # Create default configuration file
        config = default_config
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
            logger.info("Created default configuration file")
        except Exception as e:
            logger.error(f"Error creating configuration file: {e}")
    
    return config

def save_config(config: Dict[str, Any]) -> bool:
    """
    Save configuration to file.
    
    Args:
        config (dict): Configuration dictionary
        
    Returns:
        bool: True if successful, False otherwise
    """
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'garage_system_config.json')
    
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        logger.info("Saved configuration to file")
        return True
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        return False
