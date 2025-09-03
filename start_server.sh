#!/bin/bash

# Diet Generator Server Startup Script
# This script helps manage the Gunicorn server with proper configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/home/ubuntu/DietProject_samsara"
VENV_DIR="$PROJECT_DIR/venv"
SERVICE_NAME="diet-generator"
CONFIG_FILE="gunicorn.conf.py"

echo -e "${GREEN}Starting Diet Generator Server...${NC}"

# Check if we're in the right directory
if [ ! -f "$PROJECT_DIR/app.py" ]; then
    echo -e "${RED}Error: app.py not found in $PROJECT_DIR${NC}"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}Error: Virtual environment not found at $VENV_DIR${NC}"
    exit 1
fi

# Check if gunicorn config exists
if [ ! -f "$PROJECT_DIR/$CONFIG_FILE" ]; then
    echo -e "${YELLOW}Warning: $CONFIG_FILE not found, using default settings${NC}"
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source "$VENV_DIR/bin/activate"

# Install/upgrade dependencies
echo -e "${YELLOW}Checking dependencies...${NC}"
pip install -r requirements.txt

# Stop existing service if running
echo -e "${YELLOW}Stopping existing service...${NC}"
sudo systemctl stop "$SERVICE_NAME" 2>/dev/null || true

# Copy service file to systemd directory
echo -e "${YELLOW}Installing systemd service...${NC}"
sudo cp "$PROJECT_DIR/$SERVICE_NAME.service" /etc/systemd/system/

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

# Start the service
echo -e "${YELLOW}Starting service...${NC}"
sudo systemctl start "$SERVICE_NAME"

# Check status
echo -e "${YELLOW}Checking service status...${NC}"
sleep 3
sudo systemctl status "$SERVICE_NAME" --no-pager

echo -e "${GREEN}Server started successfully!${NC}"
echo -e "${GREEN}Service status: sudo systemctl status $SERVICE_NAME${NC}"
echo -e "${GREEN}View logs: sudo journalctl -u $SERVICE_NAME -f${NC}"
echo -e "${GREEN}Stop service: sudo systemctl stop $SERVICE_NAME${NC}"
