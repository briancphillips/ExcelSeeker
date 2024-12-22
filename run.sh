#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting ExcelSeeker...${NC}"

# Check if Python virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${BLUE}Setting up Python virtual environment...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Check if Node.js is installed
if ! command -v node >/dev/null 2>&1; then
    echo -e "${RED}Error: Node.js is not installed. Please install Node.js to use the folder selection feature.${NC}"
    exit 1
fi

# Install dependencies and start folder service
echo -e "${BLUE}Setting up folder selection service...${NC}"
npm install

# Function to cleanup processes on exit
cleanup() {
    echo -e "\n${BLUE}Shutting down services...${NC}"
    pkill -f "electron" 2>/dev/null
    pkill -f "python app.py" 2>/dev/null
    deactivate 2>/dev/null
    echo -e "${GREEN}Cleanup complete${NC}"
    exit 0
}

# Set up trap for cleanup
trap cleanup SIGINT SIGTERM

# Start folder service
echo -e "${GREEN}Starting folder selection service...${NC}"
npm start &

# Wait a moment for the folder service to start
sleep 2

# Start Flask application
echo -e "${GREEN}Starting Flask application...${NC}"
python app.py 