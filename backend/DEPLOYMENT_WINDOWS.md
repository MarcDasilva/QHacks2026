# Backend Deployment - Windows/PowerShell Guide

This README provides Windows-specific instructions for deploying the CRM Analytics backend to Vultr.

## 📋 Prerequisites

- ✅ Windows 10/11 with PowerShell 5.1+ (built-in)
- ✅ SSH client (built into Windows 10+)
- ✅ Vultr account
- ✅ Git for Windows (optional, for cloning on server)

## 🚀 Quick Deployment

### 1. Deploy Vultr Server

Follow [VULTR_DEPLOYMENT_GUIDE.md](../VULTR_DEPLOYMENT_GUIDE.md) - it now includes PowerShell commands!

**Quick summary:**
1. Create Vultr instance (2GB RAM, Ubuntu/Debian)
2. Note your server IP address (e.g., `123.45.67.89`)

### 2. Connect from PowerShell

```powershell
# Open PowerShell and connect
ssh root@YOUR_SERVER_IP
```

### 3. Set Up Server (Linux commands on server)

```bash
# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y python3 python3-venv python3-pip nginx git

# Clone your repo
cd ~
git clone YOUR_REPO_URL QHacks2026
cd QHacks2026/backend

# Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env file
nano .env
# Add: GEMINI_API_KEY=your_key_here
# Add: GRADIUM_API_KEY=your_key_here
# Save: Ctrl+X, Y, Enter

# Test it works
python app/main.py
# Press Ctrl+C to stop
```

### 4. Set Up systemd Service (Keep Running)

Follow Steps 4-6 in [VULTR_DEPLOYMENT_GUIDE.md](../VULTR_DEPLOYMENT_GUIDE.md)

### 5. Test from Your Local Machine (PowerShell)

Exit SSH (type `exit`), then from your local PowerShell:

```powershell
# Test backend
Invoke-WebRequest -Uri http://YOUR_SERVER_IP/health -UseBasicParsing | Select-Object -ExpandProperty Content
```

### 6. Update Frontend

```powershell
cd frontend
@"
NEXT_PUBLIC_API_URL=http://YOUR_SERVER_IP
"@ | Out-File -FilePath .env.local -Encoding utf8

# Verify
cat .env.local

# Start frontend
npm run dev
```

## 🛠️ PowerShell Helper Script

A convenience script for common tasks:

```powershell
# Test backend connection
.\backend\deploy-windows.ps1 -ServerIP YOUR_SERVER_IP -Action test

# Set up frontend .env.local
.\backend\deploy-windows.ps1 -ServerIP YOUR_SERVER_IP -Action setup-env

# Show help
.\backend\deploy-windows.ps1 -Action help
```

## 📝 Common PowerShell Commands

### Testing Endpoints

```powershell
# Health check
Invoke-WebRequest -Uri http://YOUR_SERVER_IP/health -UseBasicParsing

# Chat endpoint (POST)
$body = @{
    message = "What are the top issues?"
    mode = "auto"
} | ConvertTo-Json

Invoke-WebRequest -Uri http://YOUR_SERVER_IP/api/chat `
    -Method POST `
    -Body $body `
    -ContentType "application/json" `
    -UseBasicParsing | Select-Object -ExpandProperty Content
```

### File Operations

```powershell
# Upload a file to server
scp C:\path\to\file.txt root@YOUR_SERVER_IP:/home/deploy/

# Download from server
scp root@YOUR_SERVER_IP:/home/deploy/file.txt C:\local\path\

# Upload entire backend folder
scp -r .\backend root@YOUR_SERVER_IP:/home/deploy/QHacks2026/
```

### Server Management

```powershell
# SSH into server
ssh root@YOUR_SERVER_IP

# Once on server, check logs
sudo journalctl -u crm-backend -f

# Restart service
sudo systemctl restart crm-backend

# Check status
sudo systemctl status crm-backend
```

## 🐛 Troubleshooting

### Can't connect via SSH?

```powershell
# Test if server is reachable
Test-NetConnection -ComputerName YOUR_SERVER_IP -Port 22

# Check server status in Vultr dashboard
```

### Backend not responding?

```powershell
# From PowerShell (local)
Test-NetConnection -ComputerName YOUR_SERVER_IP -Port 80

# SSH into server and check
ssh root@YOUR_SERVER_IP
sudo systemctl status crm-backend
sudo journalctl -u crm-backend -n 50
```

### Frontend can't connect?

1. Check `.env.local` exists:
   ```powershell
   cat frontend\.env.local
   ```

2. Restart Next.js dev server (Ctrl+C then `npm run dev`)

3. Check browser console for CORS errors

4. Verify backend CORS settings allow your frontend URL

## 📚 Full Documentation

- **[VULTR_DEPLOYMENT_GUIDE.md](../VULTR_DEPLOYMENT_GUIDE.md)** - Complete deployment guide with PowerShell support
- **[FRONTEND_CLOUD_CONNECTION.md](../FRONTEND_CLOUD_CONNECTION.md)** - Connecting frontend to cloud backend
- **[Dockerfile](./Dockerfile)** - Docker deployment option
- **[docker-compose.yml](./docker-compose.yml)** - Docker Compose setup

## 💰 Cost

- **Vultr VPS**: $6-12/month (2GB RAM plan recommended)
- **Domain** (optional): $10-15/year
- **SSL** (optional): Free with Let's Encrypt

## 🎯 Next Steps

After deployment:

1. ✅ Set up SSL/HTTPS (Step 9 in deployment guide)
2. ✅ Configure automatic backups in Vultr
3. ✅ Set up monitoring (optional)
4. ✅ Deploy frontend to Vercel/Netlify (optional)

## 🆘 Getting Help

- Check [VULTR_DEPLOYMENT_GUIDE.md](../VULTR_DEPLOYMENT_GUIDE.md) troubleshooting section
- Vultr Docs: https://www.vultr.com/docs/
- FastAPI Deployment: https://fastapi.tiangolo.com/deployment/

---

**Windows PowerShell Tips:**

- Use tab completion for paths and commands
- `Get-History` shows command history
- `Clear-Host` or `cls` clears the screen
- PowerShell ISE or VS Code provide better editing for scripts
