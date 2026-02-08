#!/bin/bash

# Setup script for scheduled data updates on Vultr server
# This script installs and configures the systemd service and timer

set -e  # Exit on any error

echo "=================================================="
echo "QHacks Scheduled Data Update - Setup Script"
echo "=================================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/root/QHacks2026"
BACKEND_DIR="$PROJECT_DIR/backend"
VENV_DIR="$PROJECT_DIR/.venv"
SYSTEMD_DIR="/etc/systemd/system"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}✗ Please run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Running as root${NC}"

# Check if project directory exists
if [ ! -d "$BACKEND_DIR" ]; then
    echo -e "${RED}✗ Backend directory not found: $BACKEND_DIR${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Backend directory found${NC}"

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}! Virtual environment not found at $VENV_DIR${NC}"
    echo -e "${YELLOW}  Creating virtual environment...${NC}"
    cd "$PROJECT_DIR"
    python3 -m venv .venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment and install dependencies
echo ""
echo "Installing Python dependencies..."
source "$VENV_DIR/bin/activate"

# Install required packages
pip install --quiet --upgrade pip
pip install --quiet sentence-transformers requests psycopg2-binary python-dotenv pandas

echo -e "${GREEN}✓ Python dependencies installed${NC}"

# Check if .env file exists
if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo -e "${RED}✗ .env file not found at $BACKEND_DIR/.env${NC}"
    echo -e "${YELLOW}  Please create .env file with DATABASE_URL before continuing${NC}"
    exit 1
fi

echo -e "${GREEN}✓ .env file found${NC}"

# Test database connection
echo ""
echo "Testing database connection..."
cd "$BACKEND_DIR"
if python -c "from app.db.connection import get_conn; conn = get_conn(); conn.close(); print('✓ Database connection successful')" 2>&1; then
    echo -e "${GREEN}✓ Database connection successful${NC}"
else
    echo -e "${RED}✗ Database connection failed${NC}"
    echo -e "${YELLOW}  Please check DATABASE_URL in .env file${NC}"
    exit 1
fi

# Test the update script with dry-run
echo ""
echo "Testing update script (dry run)..."
if python scripts/scheduled_data_update.py --dry-run --skip-api 2>&1 | tail -20; then
    echo -e "${GREEN}✓ Update script test passed${NC}"
else
    echo -e "${RED}✗ Update script test failed${NC}"
    exit 1
fi

# Create logs directory
mkdir -p "$BACKEND_DIR/logs"
echo -e "${GREEN}✓ Logs directory created${NC}"

# Copy systemd service file
echo ""
echo "Installing systemd service..."
if [ -f "$BACKEND_DIR/systemd/qhacks-data-update.service" ]; then
    cp "$BACKEND_DIR/systemd/qhacks-data-update.service" "$SYSTEMD_DIR/"
    echo -e "${GREEN}✓ Service file installed${NC}"
else
    echo -e "${RED}✗ Service file not found at $BACKEND_DIR/systemd/qhacks-data-update.service${NC}"
    exit 1
fi

# Copy systemd timer file
echo "Installing systemd timer..."
if [ -f "$BACKEND_DIR/systemd/qhacks-data-update.timer" ]; then
    cp "$BACKEND_DIR/systemd/qhacks-data-update.timer" "$SYSTEMD_DIR/"
    echo -e "${GREEN}✓ Timer file installed${NC}"
else
    echo -e "${RED}✗ Timer file not found at $BACKEND_DIR/systemd/qhacks-data-update.timer${NC}"
    exit 1
fi

# Reload systemd
echo ""
echo "Reloading systemd daemon..."
systemctl daemon-reload
echo -e "${GREEN}✓ Systemd daemon reloaded${NC}"

# Enable and start timer
echo ""
echo "Enabling and starting timer..."
systemctl enable qhacks-data-update.timer
systemctl start qhacks-data-update.timer
echo -e "${GREEN}✓ Timer enabled and started${NC}"

# Show timer status
echo ""
echo "=================================================="
echo "Setup Complete!"
echo "=================================================="
echo ""
echo "Timer Status:"
systemctl status qhacks-data-update.timer --no-pager -l
echo ""
echo "Next scheduled run:"
systemctl list-timers qhacks-data-update.timer --no-pager
echo ""
echo "=================================================="
echo "Useful Commands:"
echo "=================================================="
echo ""
echo "# View timer status"
echo "  sudo systemctl status qhacks-data-update.timer"
echo ""
echo "# View service status"
echo "  sudo systemctl status qhacks-data-update.service"
echo ""
echo "# View logs"
echo "  sudo journalctl -u qhacks-data-update.service -f"
echo ""
echo "# Manual run"
echo "  sudo systemctl start qhacks-data-update.service"
echo ""
echo "# View log files"
echo "  ls -lh $BACKEND_DIR/logs/"
echo ""
echo "# Stop timer"
echo "  sudo systemctl stop qhacks-data-update.timer"
echo ""
echo "# Disable timer"
echo "  sudo systemctl disable qhacks-data-update.timer"
echo ""
echo "=================================================="
echo -e "${GREEN}Setup completed successfully!${NC}"
echo "=================================================="
