# Garage Management System

This package contains the complete Garage Management System that integrates with Garage Assistant 4 (GA4). The system provides comprehensive garage business management including customer tracking, vehicle service history, MOT reminders, document management, and invoicing.

## Quick Start

1. Download this package from Google Drive
2. Extract the files to a directory on your computer
3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Run the application:
   ```
   python run.py --debug --host 127.0.0.1 --port 5000
   ```
5. The system will open in your web browser at http://127.0.0.1:5000

## Key Features

- **Customer Management**: Track customer information, contact details, and communication history
- **Vehicle Management**: Maintain comprehensive vehicle records including service history and MOT status
- **MOT Reminder System**: Automatically track MOT due dates and send reminders to customers
- **Document Management**: Store and organize important documents related to customers and vehicles
- **Invoice Generation**: Create and manage invoices for services provided
- **GA4 Integration**: Seamless connection with your Garage Assistant 4 data

## System Requirements

- Python 3.6 or higher
- Required packages (installed via requirements.txt):
  - Flask
  - Flask-APScheduler
  - SQLite3 (included with Python)
  - Requests
  - Werkzeug
  - Jinja2

## Configuration

The system is pre-configured to work with your GA4 installation. If you need to modify any settings:

1. Edit the `app/config/config.py` file to update paths or API settings
2. Restart the application for changes to take effect

## Troubleshooting

### JSON Parsing Error

If you encounter the error "SyntaxError: Unexpected token '<', "<!DOCTYPE "... is not valid JSON":

1. This has been fixed in the current version by adding proper error handling for non-JSON responses
2. If you still encounter this issue, check that your API endpoints are returning proper JSON responses
3. Verify that your browser is not caching old JavaScript files by clearing your browser cache

### Other Common Issues

1. **Application won't start**: Make sure all required packages are installed and port 5000 is not in use
2. **Database errors**: Check file permissions for the data directory
3. **Missing templates**: Ensure all template files are in the correct location

## Backup and Data Management

1. The system stores data in SQLite databases in the `data` directory
2. Regular backups are recommended - copy the entire `data` directory to a secure location
3. To migrate data, simply copy the database files to the new installation

## Integration with GA4

This system is designed to work alongside your existing GA4 installation:

1. It reads data directly from GA4 database files when available
2. You can also import data via CSV exports from GA4
3. Changes made in GA4 will be reflected in this system during the next synchronization

## Security Notes

1. The system uses a secret key for session management - this is pre-configured
2. For production use, consider updating the secret key in `app/__init__.py`
3. Access control is basic - implement additional security if exposing to a network

## For Future Updates

Check the Google Drive folder periodically for updates to this system. New features and bug fixes will be added regularly.
