#!/bin/bash

# Deployment script for Vultr or any Ubuntu/Debian server
# Run this on your Vultr server after initial setup

set -e  # Exit on error

echo "🚀 Starting CRM Backend Deployment..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running as deploy user
if [ "$USER" != "deploy" ]; then
    echo "⚠️  This script should be run as the 'deploy' user"
    echo "Run: su - deploy"
    exit 1
fi

# Navigate to project directory
cd ~/QHacks2026/backend || exit 1

echo -e "${BLUE}📥 Pulling latest code...${NC}"
git pull origin main

echo -e "${BLUE}📦 Installing dependencies...${NC}"
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${BLUE}🔄 Restarting service...${NC}"
sudo systemctl restart crm-backend

echo -e "${BLUE}⏳ Waiting for service to start...${NC}"
sleep 5

echo -e "${BLUE}🔍 Checking service status...${NC}"
sudo systemctl status crm-backend --no-pager

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo -e "${GREEN}🌐 Backend is running at http://$(curl -s ifconfig.me)${NC}"
