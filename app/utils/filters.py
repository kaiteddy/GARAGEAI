#!/usr/bin/env python3
"""
Custom Jinja2 Filters

This module provides custom Jinja2 filters for the templates.
"""

from datetime import datetime
from flask import Flask

def to_datetime(date_str):
    """
    Convert a date string to a datetime object.
    
    Args:
        date_str (str): Date string in format YYYY-MM-DD
        
    Returns:
        datetime: Datetime object
    """
    if not date_str:
        return None
    
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        try:
            return datetime.strptime(date_str, '%d/%m/%Y')
        except ValueError:
            return None

def format_currency(value):
    """
    Format a value as currency (GBP).
    
    Args:
        value (float): Value to format
        
    Returns:
        str: Formatted currency string
    """
    if value is None:
        return "£0.00"
    
    return f"£{value:.2f}"

def format_date(date_str, format_str='%d/%m/%Y'):
    """
    Format a date string.
    
    Args:
        date_str (str): Date string
        format_str (str): Format string
        
    Returns:
        str: Formatted date string
    """
    if not date_str:
        return ""
    
    dt = to_datetime(date_str)
    if not dt:
        return date_str
    
    return dt.strftime(format_str)

def nl2br(text):
    """
    Convert newlines to HTML line breaks.
    
    Args:
        text (str): Text with newlines
        
    Returns:
        str: Text with HTML line breaks
    """
    if not text:
        return ""
    
    return text.replace('\n', '<br>')

def register_filters(app: Flask):
    """
    Register all custom filters with the Flask app.
    
    Args:
        app (Flask): Flask application
    """
    app.jinja_env.filters['to_datetime'] = to_datetime
    app.jinja_env.filters['format_currency'] = format_currency
    app.jinja_env.filters['format_date'] = format_date
    app.jinja_env.filters['nl2br'] = nl2br
