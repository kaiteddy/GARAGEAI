#!/bin/bash
# Run Integrated Garage Management System

echo "Starting Integrated Garage Management System..."
echo "This script will attempt to run the Integrated Garage Management System on port 5000."

# Check if Python is installed
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Python is not installed or not in the PATH."
    exit 1
fi

# Check if Flask is installed
$PYTHON_CMD -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing Flask..."
    $PYTHON_CMD -m pip install flask flask-cors watchdog apscheduler
fi

# Kill any process using port 5000
echo "Checking for processes using port 5000..."
if command -v lsof &>/dev/null; then
    PROCESS_PID=$(lsof -ti:5000)
    if [ ! -z "$PROCESS_PID" ]; then
        echo "Killing process $PROCESS_PID using port 5000..."
        kill -9 $PROCESS_PID
    fi
fi

# Run the Integrated Garage Management System
echo "Running Integrated Garage Management System..."
$PYTHON_CMD integrated_garage_system.py

echo "Done."
