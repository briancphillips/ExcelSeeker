#!/bin/bash

echo "ExcelSeeker Installer"
echo "==================="
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed! Please install Python 3.6 or higher."
    echo "You can download Python from https://www.python.org/downloads/"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install requirements
echo "Installing required packages..."
source venv/bin/activate
python3 -m pip install --upgrade pip
pip install flask flask-uploads werkzeug==2.0.3 xlrd python-dotenv xlwt

# Create necessary directories
mkdir -p temp static templates

echo
echo "Installation complete!"
echo
echo "To start ExcelSeeker:"
echo "1. Run: ./run.sh"
echo 