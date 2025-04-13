#!/usr/bin/env python3
"""
Screen Vision - A tool to capture screenshots and describe them using AI vision.

This script captures your screen periodically and uses OpenAI's GPT-4 Vision API
to generate descriptions of what's on your screen.
"""

import os
import sys
import time
import argparse
import base64
import json
import logging
from datetime import datetime
from io import BytesIO

# Import required libraries
try:
    import pyautogui
    import requests
    from PIL import Image
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call(["pip3", "install", "pyautogui", "pillow", "requests"])
    import pyautogui
    import requests
    from PIL import Image

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("screen_vision.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("ScreenVision")

# Default API key (replace with your own)
DEFAULT_API_KEY = ""

class ScreenVision:
    """A class to capture screenshots and describe them using AI vision."""

    def __init__(self, api_key, api_provider="openai", interval=5, output_file=None):
        """Initialize the ScreenVision class.

        Args:
            api_key (str): API key for the vision service
            api_provider (str): Provider of the vision API (openai, google, azure)
            interval (int): Interval between screenshots in seconds
            output_file (str): File to save the descriptions to
        """
        self.api_key = api_key
        self.api_provider = api_provider.lower()
        self.interval = interval
        self.output_file = output_file
        self.descriptions = []

        # Validate API provider
        valid_providers = ["openai", "google", "azure"]
        if self.api_provider not in valid_providers:
            raise ValueError(f"Invalid API provider. Must be one of: {', '.join(valid_providers)}")

        # Check if API key is provided
        if not self.api_key:
            raise ValueError(f"API key is required for {self.api_provider}")

        logger.info(f"Initialized ScreenVision with {self.api_provider} API")

    def capture_screenshot(self):
        """Capture a screenshot of the screen.

        Returns:
            PIL.Image: Screenshot image
        """
        try:
            # Capture the screen
            screenshot = pyautogui.screenshot()
            logger.info("Screenshot captured successfully")
            return screenshot
        except Exception as e:
            logger.error(f"Error capturing screenshot: {e}")
            raise

    def compress_image(self, image, quality=70, max_size=(1200, 1200)):
        """Compress the image to reduce size.

        Args:
            image (PIL.Image): Image to compress
            quality (int): JPEG quality (0-100)
            max_size (tuple): Maximum width and height

        Returns:
            bytes: Compressed image data
        """
        try:
            # Resize if needed
            width, height = image.size
            if width > max_size[0] or height > max_size[1]:
                image.thumbnail(max_size, Image.LANCZOS)
                logger.info(f"Image resized from {width}x{height} to {image.size[0]}x{image.size[1]}")

            # Save to buffer
            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=quality)
            buffer.seek(0)

            return buffer.getvalue()
        except Exception as e:
            logger.error(f"Error compressing image: {e}")
            raise

    def encode_image_base64(self, image_data):
        """Encode image data as base64.

        Args:
            image_data (bytes): Image data

        Returns:
            str: Base64 encoded image
        """
        return base64.b64encode(image_data).decode('utf-8')

    def describe_image_openai(self, image_data):
        """Describe the image using OpenAI's GPT-4 Vision API.

        Args:
            image_data (bytes): Image data

        Returns:
            str: Description of the image
        """
        try:
            base64_image = self.encode_image_base64(image_data)

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            payload = {
                "model": "gpt-4-vision-preview",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Describe what you see on this screen in detail. Focus on the main UI elements, any data being displayed, and the overall context of what the user is looking at. Be specific about any errors, warnings, or important information visible."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 500
            }

            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )

            response.raise_for_status()
            result = response.json()

            description = result["choices"][0]["message"]["content"]
            logger.info("Image described successfully using OpenAI")
            return description
        except Exception as e:
            logger.error(f"Error describing image with OpenAI: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return f"Error describing image: {str(e)}"

    def describe_image_google(self, image_data):
        """Describe the image using Google Cloud Vision API.

        Args:
            image_data (bytes): Image data

        Returns:
            str: Description of the image
        """
        try:
            base64_image = self.encode_image_base64(image_data)

            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key
            }

            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": "Describe what you see on this screen in detail. Focus on the main UI elements, any data being displayed, and the overall context of what the user is looking at. Be specific about any errors, warnings, or important information visible."
                            },
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": base64_image
                                }
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "maxOutputTokens": 500
                }
            }

            response = requests.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent",
                headers=headers,
                json=payload
            )

            response.raise_for_status()
            result = response.json()

            description = result["candidates"][0]["content"]["parts"][0]["text"]
            logger.info("Image described successfully using Google")
            return description
        except Exception as e:
            logger.error(f"Error describing image with Google: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return f"Error describing image: {str(e)}"

    def describe_image_azure(self, image_data):
        """Describe the image using Azure AI Vision API.

        Args:
            image_data (bytes): Image data

        Returns:
            str: Description of the image
        """
        try:
            # Extract endpoint and key from the API key (format: "endpoint|key")
            if "|" in self.api_key:
                endpoint, key = self.api_key.split("|", 1)
            else:
                raise ValueError("Azure API key should be in the format 'endpoint|key'")

            headers = {
                "Content-Type": "application/octet-stream",
                "Ocp-Apim-Subscription-Key": key
            }

            # Azure Computer Vision API for image analysis
            response = requests.post(
                f"{endpoint}/vision/v3.1/analyze?visualFeatures=Description,Objects,Text",
                headers=headers,
                data=image_data
            )

            response.raise_for_status()
            result = response.json()

            # Extract relevant information
            description = result.get("description", {}).get("captions", [{}])[0].get("text", "No description available")
            objects = ", ".join([obj["object"] for obj in result.get("objects", [])])
            text = " ".join([region["lines"][0]["words"][0]["text"] for region in result.get("regions", [])])

            full_description = f"Description: {description}\n"
            if objects:
                full_description += f"Objects detected: {objects}\n"
            if text:
                full_description += f"Text detected: {text}"

            logger.info("Image described successfully using Azure")
            return full_description
        except Exception as e:
            logger.error(f"Error describing image with Azure: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return f"Error describing image: {str(e)}"

    def describe_image(self, image_data):
        """Describe the image using the selected API provider.

        Args:
            image_data (bytes): Image data

        Returns:
            str: Description of the image
        """
        if self.api_provider == "openai":
            return self.describe_image_openai(image_data)
        elif self.api_provider == "google":
            return self.describe_image_google(image_data)
        elif self.api_provider == "azure":
            return self.describe_image_azure(image_data)
        else:
            raise ValueError(f"Unsupported API provider: {self.api_provider}")

    def save_descriptions(self):
        """Save the descriptions to a file."""
        if not self.output_file or not self.descriptions:
            return

        try:
            with open(self.output_file, 'w') as f:
                for timestamp, description in self.descriptions:
                    f.write(f"=== {timestamp} ===\n")
                    f.write(description)
                    f.write("\n\n")

            logger.info(f"Descriptions saved to {self.output_file}")
        except Exception as e:
            logger.error(f"Error saving descriptions: {e}")

    def run(self, num_captures=None):
        """Run the screen vision process.

        Args:
            num_captures (int, optional): Number of screenshots to capture. If None, run indefinitely.
        """
        try:
            capture_count = 0

            print(f"Starting ScreenVision with {self.api_provider} API")
            print(f"Press Ctrl+C to stop")

            while num_captures is None or capture_count < num_captures:
                # Capture screenshot
                screenshot = self.capture_screenshot()

                # Compress image
                image_data = self.compress_image(screenshot)

                # Describe image
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n=== Screenshot captured at {timestamp} ===")

                description = self.describe_image(image_data)
                print(description)

                # Save description
                self.descriptions.append((timestamp, description))
                if self.output_file:
                    self.save_descriptions()

                capture_count += 1

                # Wait for the next capture
                if num_captures is None or capture_count < num_captures:
                    print(f"\nWaiting {self.interval} seconds for next capture...")
                    time.sleep(self.interval)

        except KeyboardInterrupt:
            print("\nStopped by user")
        finally:
            # Save descriptions
            self.save_descriptions()
            print(f"\nCaptured {capture_count} screenshots")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Capture screenshots and describe them using AI vision')
    parser.add_argument('--api-key', help='API key for the vision service')
    parser.add_argument('--provider', choices=['openai', 'google', 'azure'], default='openai',
                        help='Provider of the vision API (default: openai)')
    parser.add_argument('--interval', type=int, default=5,
                        help='Interval between screenshots in seconds (default: 5)')
    parser.add_argument('--output', help='File to save the descriptions to')
    parser.add_argument('--num-captures', type=int, help='Number of screenshots to capture (default: run indefinitely)')

    args = parser.parse_args()

    # Get API key from arguments or environment variable
    api_key = args.api_key
    if not api_key:
        env_var = f"{args.provider.upper()}_API_KEY"
        api_key = os.environ.get(env_var, DEFAULT_API_KEY)

    if not api_key:
        print(f"Error: API key is required. Provide it with --api-key or set the {env_var} environment variable.")
        return 1

    try:
        # Create ScreenVision instance
        screen_vision = ScreenVision(
            api_key=api_key,
            api_provider=args.provider,
            interval=args.interval,
            output_file=args.output
        )

        # Run the screen vision process
        screen_vision.run(args.num_captures)

        return 0
    except Exception as e:
        print(f"Error: {e}")
        logger.error(f"Error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
