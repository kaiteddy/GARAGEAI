# MOT Reminder System

## Overview

The MOT Reminder System is a comprehensive solution for garage businesses to manage MOT reminders for their customers. It integrates directly with Garage Assistant 4 (GA4) to access real vehicle and customer data, allowing you to:

- Automatically identify vehicles with upcoming MOT tests
- Generate and send reminders via email, SMS, or postal mail
- Track reminder status and customer responses
- View statistics and reports on reminder effectiveness

## Features

- **Real-time GA4 Data Access**: Connects directly to your GA4 installation to access the latest vehicle and customer information
- **Automated MOT Expiry Detection**: Identifies vehicles with MOT tests due in the next 30, 14, 7, 3, or 1 days
- **Multi-channel Notifications**: Send reminders via email, SMS, or generate postal letters
- **Customizable Templates**: Create and edit reminder templates for different communication channels
- **Reminder Tracking**: Monitor which reminders have been sent, responded to, or completed
- **Statistics and Reporting**: View dashboards showing reminder effectiveness and MOT expiry timelines
- **User-friendly Interface**: Modern web interface accessible from any device on your network

## Installation

1. **Prerequisites**:
   - Garage Assistant 4 installed
   - Python 3.6 or higher
   - Internet connection (for email/SMS functionality)

2. **Setup**:
   - Ensure the MOT Reminder System is in the same Google Drive folder as your GA4 Direct Access Tool
   - Run `launch_mot_reminder.py` to start the system
   - The system will automatically detect your GA4 installation or prompt you to specify its location
   - A web browser will open with the MOT Reminder System interface

## Using the System

### Dashboard

The dashboard provides an overview of:
- Vehicles due for MOT in the next 30 days
- Pending and sent reminders
- Response rates
- Recent activity

### Vehicles Due for MOT

This page shows all vehicles with upcoming MOT tests, grouped by days until expiry:
- 30 days (blue)
- 14 days (yellow)
- 7 days (orange)
- 3 days (light red)
- 1 day (bright red)

You can filter vehicles by make, registration, or customer name.

### Managing Reminders

1. **Creating Reminders**:
   - Click "Create Reminders" to automatically generate reminders for all vehicles due for MOT
   - Or click "Remind" next to a specific vehicle to create a reminder just for that vehicle

2. **Sending Reminders**:
   - Go to the Reminders page
   - Select the reminder(s) you want to send
   - Choose the notification method (email, SMS, letter)
   - Click "Send Selected Reminders"

3. **Tracking Responses**:
   - Update reminder status when customers respond
   - Mark reminders as "responded" or "completed" when appropriate

### Settings

Configure:
- Garage details (name, address, contact information)
- Email settings (SMTP server, credentials)
- SMS settings (provider, API keys)
- Reminder templates for each notification channel

## Integration with GA4

The MOT Reminder System uses the GA4 Direct Access Tool to connect to your Garage Assistant 4 database. It:

1. Reads vehicle data including registration, make, model, and MOT expiry dates
2. Retrieves customer information for sending notifications
3. Maintains its own database of reminders and their status

**Important**: The system only reads data from GA4 - it does not modify your GA4 database in any way.

## Troubleshooting

If the system cannot find your GA4 installation:
1. Ensure GA4 is installed on your computer
2. Run the launcher with the `--ga4-path` parameter:
   ```
   python launch_mot_reminder.py --ga4-path "C:\Program Files (x86)\Garage Assistant GA4"
   ```

If reminders are not being sent:
1. Check your email/SMS settings in the Settings page
2. Ensure you have internet connectivity
3. Verify that the notification service credentials are correct

## Next Steps

This system is part of a comprehensive Garage Management System that will eventually include:
- Customer management
- Invoice generation and tracking
- Vehicle service history
- Appointment scheduling

Stay tuned for updates as we continue to expand the system's capabilities!
