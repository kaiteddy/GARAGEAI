# Screen Vision

A tool to capture screenshots and describe them using AI vision. This allows an AI assistant to "see" what's on your screen and provide more accurate assistance.

## Features

- Captures screenshots of your screen at regular intervals
- Uses AI vision APIs to generate detailed descriptions of what's on your screen
- Supports multiple AI providers: OpenAI, Google, and Azure
- Saves descriptions to a file for reference
- Lightweight and easy to use

## Requirements

- Python 3.6 or higher
- An API key for one of the supported vision services:
  - OpenAI API key (for GPT-4 Vision)
  - Google Cloud Vision API key
  - Azure Computer Vision API key

## Installation

1. Make sure you have Python installed
2. The script will automatically install required dependencies:
   - pyautogui
   - pillow
   - requests

## Usage

1. Make the script executable:

```bash
chmod +x screen_vision.py
```

2. Run the script with your API key:

```bash
# Using OpenAI (default)
python3 screen_vision.py --api-key YOUR_OPENAI_API_KEY

# Using Google Cloud Vision
python3 screen_vision.py --provider google --api-key YOUR_GOOGLE_API_KEY

# Using Azure Computer Vision
python3 screen_vision.py --provider azure --api-key "YOUR_AZURE_ENDPOINT|YOUR_AZURE_KEY"
```

### Options

- `--api-key`: Your API key for the vision service
- `--provider`: Vision API provider (openai, google, or azure)
- `--interval`: Interval between screenshots in seconds (default: 5)
- `--output`: File to save the descriptions to
- `--num-captures`: Number of screenshots to capture (default: run indefinitely)

### Example

```bash
# Capture screenshots every 10 seconds and save descriptions to output.txt
python3 screen_vision.py --api-key YOUR_API_KEY --interval 10 --output output.txt

# Capture 5 screenshots using Google's Vision API
python3 screen_vision.py --provider google --api-key YOUR_GOOGLE_API_KEY --num-captures 5
```

## How to Use with an AI Assistant

1. Run the script to start capturing and describing your screen
2. Copy the descriptions from the terminal or output file
3. Paste the descriptions to your AI assistant
4. The AI assistant can now "see" what's on your screen and provide more accurate assistance

## Privacy and Security

- All processing is done through the selected AI vision API
- No screenshots are stored unless you specify an output file
- Be cautious about what's visible on your screen when using this tool
- Review the API provider's privacy policy for information on how they handle your data

## Troubleshooting

- If you encounter permission issues, make sure the script is executable
- If the script fails to capture screenshots, try running it with administrator privileges
- If the API returns errors, check that your API key is valid and has the necessary permissions
