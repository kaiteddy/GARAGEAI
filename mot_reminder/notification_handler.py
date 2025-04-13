#!/usr/bin/env python3
"""
MOT Reminder Notification Handler

This module handles sending notifications for MOT reminders:
- Email notifications
- SMS notifications
- Postal letter generation
"""

import os
import sys
import json
import smtplib
import logging
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('NotificationHandler')

class NotificationHandler:
    """Handler for sending MOT reminder notifications"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the notification handler
        
        Args:
            config_path: Optional path to configuration file
        """
        self.config = self._load_config(config_path)
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict:
        """Load configuration from file or use defaults
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        default_config = {
            "email": {
                "enabled": False,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "smtp_username": "",
                "smtp_password": "",
                "from_email": "",
                "from_name": "Your Garage"
            },
            "sms": {
                "enabled": False,
                "provider": "twilio",  # twilio, nexmo, etc.
                "account_sid": "",
                "auth_token": "",
                "from_number": ""
            },
            "letter": {
                "enabled": False,
                "output_directory": "letters"
            }
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults to ensure all required fields exist
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                        elif isinstance(value, dict):
                            for subkey, subvalue in value.items():
                                if subkey not in config[key]:
                                    config[key][subkey] = subvalue
                    logger.info(f"Loaded configuration from {config_path}")
                    return config
            except Exception as e:
                logger.error(f"Error loading configuration: {e}")
        
        logger.info("Using default configuration")
        return default_config
    
    def send_email(self, to_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
        """Send email notification
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Plain text email body
            html_body: Optional HTML email body
            
        Returns:
            True if successful, False otherwise
        """
        if not self.config["email"]["enabled"]:
            logger.warning("Email notifications are disabled")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.config['email']['from_name']} <{self.config['email']['from_email']}>"
            msg["To"] = to_email
            
            # Add plain text body
            msg.attach(MIMEText(body, "plain"))
            
            # Add HTML body if provided
            if html_body:
                msg.attach(MIMEText(html_body, "html"))
            
            # Connect to SMTP server
            server = smtplib.SMTP(self.config["email"]["smtp_server"], self.config["email"]["smtp_port"])
            server.starttls()
            server.login(self.config["email"]["smtp_username"], self.config["email"]["smtp_password"])
            
            # Send email
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Sent email to {to_email}")
            return True
        
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    def send_sms(self, to_number: str, body: str) -> bool:
        """Send SMS notification
        
        Args:
            to_number: Recipient phone number
            body: SMS message body
            
        Returns:
            True if successful, False otherwise
        """
        if not self.config["sms"]["enabled"]:
            logger.warning("SMS notifications are disabled")
            return False
        
        try:
            provider = self.config["sms"]["provider"].lower()
            
            if provider == "twilio":
                return self._send_twilio_sms(to_number, body)
            elif provider == "nexmo":
                return self._send_nexmo_sms(to_number, body)
            else:
                logger.error(f"Unsupported SMS provider: {provider}")
                return False
        
        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            return False
    
    def _send_twilio_sms(self, to_number: str, body: str) -> bool:
        """Send SMS using Twilio
        
        Args:
            to_number: Recipient phone number
            body: SMS message body
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Import Twilio client
            from twilio.rest import Client
            
            # Create client
            client = Client(self.config["sms"]["account_sid"], self.config["sms"]["auth_token"])
            
            # Send message
            message = client.messages.create(
                body=body,
                from_=self.config["sms"]["from_number"],
                to=to_number
            )
            
            logger.info(f"Sent Twilio SMS to {to_number} (SID: {message.sid})")
            return True
        
        except ImportError:
            logger.error("Twilio library not installed. Install with: pip install twilio")
            return False
        except Exception as e:
            logger.error(f"Error sending Twilio SMS: {e}")
            return False
    
    def _send_nexmo_sms(self, to_number: str, body: str) -> bool:
        """Send SMS using Nexmo/Vonage
        
        Args:
            to_number: Recipient phone number
            body: SMS message body
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Import Vonage client
            import vonage
            
            # Create client
            client = vonage.Client(key=self.config["sms"]["account_sid"], secret=self.config["sms"]["auth_token"])
            sms = vonage.Sms(client)
            
            # Send message
            response = sms.send_message({
                "from": self.config["sms"]["from_number"],
                "to": to_number,
                "text": body
            })
            
            if response["messages"][0]["status"] == "0":
                logger.info(f"Sent Nexmo SMS to {to_number} (ID: {response['messages'][0]['message-id']})")
                return True
            else:
                logger.error(f"Error sending Nexmo SMS: {response['messages'][0]['error-text']}")
                return False
        
        except ImportError:
            logger.error("Vonage library not installed. Install with: pip install vonage")
            return False
        except Exception as e:
            logger.error(f"Error sending Nexmo SMS: {e}")
            return False
    
    def generate_letter(self, customer_name: str, customer_address: str, subject: str, body: str) -> Optional[str]:
        """Generate postal letter
        
        Args:
            customer_name: Customer name
            customer_address: Customer address
            subject: Letter subject
            body: Letter body
            
        Returns:
            Path to generated letter file if successful, None otherwise
        """
        if not self.config["letter"]["enabled"]:
            logger.warning("Letter generation is disabled")
            return None
        
        try:
            # Create output directory if it doesn't exist
            output_dir = self.config["letter"]["output_directory"]
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate letter content
            letter_content = f"""
{customer_name}
{customer_address}

{subject}

{body}
"""
            
            # Generate filename
            import hashlib
            import datetime
            
            filename = f"letter_{hashlib.md5(customer_name.encode()).hexdigest()}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
            file_path = os.path.join(output_dir, filename)
            
            # Write letter to file
            with open(file_path, 'w') as f:
                f.write(letter_content)
            
            logger.info(f"Generated letter for {customer_name} at {file_path}")
            return file_path
        
        except Exception as e:
            logger.error(f"Error generating letter: {e}")
            return None
    
    def send_notification(self, reminder: Dict, notification_type: str, content: Dict) -> bool:
        """Send notification based on type
        
        Args:
            reminder: Reminder details
            notification_type: Type of notification (email, sms, letter)
            content: Notification content
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if notification_type == "email":
                if "customer_email" not in reminder or not reminder["customer_email"]:
                    logger.warning(f"No email address for customer {reminder.get('customer_name', 'unknown')}")
                    return False
                
                return self.send_email(
                    reminder["customer_email"],
                    content["subject"],
                    content["body"]
                )
            
            elif notification_type == "sms":
                if "customer_phone" not in reminder or not reminder["customer_phone"]:
                    logger.warning(f"No phone number for customer {reminder.get('customer_name', 'unknown')}")
                    return False
                
                return self.send_sms(
                    reminder["customer_phone"],
                    content["body"]
                )
            
            elif notification_type == "letter":
                if "customer_name" not in reminder or not reminder["customer_name"]:
                    logger.warning("No customer name for letter")
                    return False
                
                if "customer_address" not in reminder or not reminder["customer_address"]:
                    logger.warning(f"No address for customer {reminder['customer_name']}")
                    return False
                
                letter_path = self.generate_letter(
                    reminder["customer_name"],
                    reminder["customer_address"],
                    f"MOT Reminder for {reminder['registration']}",
                    content["body"]
                )
                
                return letter_path is not None
            
            else:
                logger.error(f"Unsupported notification type: {notification_type}")
                return False
        
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False


if __name__ == "__main__":
    # Example usage
    handler = NotificationHandler()
    
    # Example reminder
    reminder = {
        "customer_name": "John Smith",
        "customer_email": "john.smith@example.com",
        "customer_phone": "07700 900123",
        "customer_address": "123 Main St\nLondon\nSW1A 1AA",
        "registration": "AB12XYZ",
        "make": "Ford",
        "model": "Focus",
        "mot_expiry": "2025-02-14"
    }
    
    # Example content
    content = {
        "subject": f"MOT Reminder for {reminder['registration']}",
        "body": f"Dear {reminder['customer_name']},\n\nThis is a reminder that the MOT for your {reminder['make']} {reminder['model']} ({reminder['registration']}) is due on {reminder['mot_expiry']}.\n\nPlease contact us to schedule an appointment.\n\nRegards,\nYour Garage"
    }
    
    # Send notifications
    # Note: These will fail without proper configuration
    email_result = handler.send_notification(reminder, "email", content)
    sms_result = handler.send_notification(reminder, "sms", content)
    letter_result = handler.send_notification(reminder, "letter", content)
    
    print(f"Email result: {email_result}")
    print(f"SMS result: {sms_result}")
    print(f"Letter result: {letter_result}")
