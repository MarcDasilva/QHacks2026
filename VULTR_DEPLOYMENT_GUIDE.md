# Vultr Deployment Guide

This guide walks you through deploying your FastAPI backend to Vultr so you can access it from anywhere, eliminating the need to run it locally.

## Prerequisites

- Vultr account (you have this ✅)
- Your backend code ready
- Environment variables (GEMINI_API_KEY, GRADIUM_API_KEY, etc.)
- SSH client (built into PowerShell on Windows 10+)

## Important: Command Line Guide

**This guide uses TWO different command line environments:**

1. **Your Local Machine (PowerShell/Windows)**
   - Commands to run on YOUR computer
   - Marked with `# PowerShell (Windows)` or just `powershell` code blocks
   - Used for: SSH connections, testing endpoints, creating local files

2. **Vultr Server (Linux/Bash)**
   - Commands to run ON THE SERVER after SSH connection
   - Marked with `# On Server` or `bash` code blocks
   - Used for: Installing packages, configuring server, starting services

**💡 Tip:** After running `ssh root@YOUR_SERVER_IP` from PowerShell, all subsequent commands run on the Linux server until you disconnect.

## Quick Start (For Impatient Developers 🚀)

**Windows/PowerShell users:**

1. Deploy Vultr server (Steps 1-2 above), get IP address
2. From PowerShell:
   ```powershell
   ssh root@YOUR_SERVER_IP
   ```
3. On server, run:
   ```bash
   apt update && apt upgrade -y
   apt install -y python3 python3-venv python3-pip git
   git clone YOUR_REPO_URL QHacks2026
   cd QHacks2026/backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   nano .env  # Add your GEMINI_API_KEY and GRADIUM_API_KEY
   python app/main.py  # Test it works
   ```
4. Then follow Steps 4-6 for production setup (systemd, nginx, firewall)
5. Back on your local machine (PowerShell):
   ```powershell
   # Test it works
   Invoke-WebRequest -Uri http://YOUR_SERVER_IP:8000/health -UseBasicParsing
   
   # Update frontend
   cd frontend
   echo "NEXT_PUBLIC_API_URL=http://YOUR_SERVER_IP" > .env.local
   ```

Done! Now continue with detailed steps below for production setup.

---

## Step 1: Create a Vultr Instance

1. **Log in to Vultr**: https://my.vultr.com/
2. **Click "Deploy +" or "Deploy New Instance"** (usually blue button in top right)
3. **Select Server Type**:
   - Choose "Cloud Compute" (most common option)
   - Or "Optimized Cloud Compute" for better performance

4. **Choose Location**:
   - Pick closest to your users (e.g., Chicago, New York, Toronto, Los Angeles)

5. **Choose Operating System** (This is the "Server Image"):
   - Look for sections like: "Image", "Server Image", "Operating System", or "Distribution"
   - You might see categories like:
     - **"Marketplace Apps"** (skip this)
     - **"Operating System"** or **"Distributions"** ← Select this tab/section
   - Common options you might see:
     - **Ubuntu** - Choose this! Pick version 22.04 or 20.04
     - Debian - Also works (choose Debian 11 or 12)
     - CentOS / AlmaLinux - Also works but commands will differ
     - Fedora - Works but Ubuntu is easier
   
   **Can't find Ubuntu?** Look for:
   - A dropdown menu or list of OS options
   - Tab options at the top (cloud images, distributions, etc.)
   - "Linux Distributions" section
   - Try **Debian 11 or 12** as an alternative (very similar to Ubuntu)

6. **Choose Server Size** (Plan):
   - Look for pricing options like "$6/mo", "$12/mo", etc.
   - Recommended: **$6-12/month plan with 2GB RAM**
   - Example: "1 vCPU, 2GB Memory, 55GB Storage"

7. **Additional Features** (optional):
   - Enable "Auto Backups" if you want automatic backups
   - Enable "IPv6" if needed
   - Skip "Additional Features" if unsure

8. **Server Hostname & Label** (optional):
   - Give it a name like "compass-backend" for easy identification

9. **Click "Deploy Now"**

10. **Wait 2-5 minutes** for server to deploy

11. **Note your server's IP address** (displayed after deployment, e.g., `123.45.67.89`)
    - You'll find this on the server details page
    - Save this IP - you'll need it for SSH and frontend configuration!

## Step 2: Initial Server Setup

**From your local machine** (PowerShell/Terminal), connect to your server via SSH:

```powershell
# PowerShell (Windows)
ssh root@YOUR_SERVER_IP
```

```bash
# Or from bash/terminal (Mac/Linux)
ssh root@YOUR_SERVER_IP
```

**Note:** All commands below run ON THE SERVER (Linux), not on your local machine!

### Update system packages (On Server):
```bash
apt update && apt upgrade -y
```

### Install Python and required tools:

**For Ubuntu/Debian:**
```bash
apt install -y python3.11 python3.11-venv python3-pip nginx git
```

**If python3.11 not available, use python3:**
```bash
apt install -y python3 python3-venv python3-pip nginx git
# Then replace python3.11 with python3 in all future commands
```

**For CentOS/AlmaLinux/Fedora:**
```bash
yum install -y python3.11 python3-pip nginx git
# or
dnf install -y python3.11 python3-pip nginx git
```

### Create a deploy user (security best practice):
```bash
adduser deploy
usermod -aG sudo deploy
su - deploy
```

## Step 3: Deploy Your Application

**All commands in this section run ON THE SERVER (after SSH connection)**

### Clone your repository:
```bash
cd ~
git clone YOUR_REPO_URL QHacks2026
cd QHacks2026/backend
```

*If your repo is private, you'll need to set up SSH keys or use a personal access token.*

### Create virtual environment and install dependencies:
```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Set up environment variables:
```bash
nano .env
```

Add your environment variables:
```
GEMINI_API_KEY=your_gemini_api_key_here
GRADIUM_API_KEY=your_gradium_api_key_here
DATABASE_URL=your_database_url_if_needed
```

Save and exit (Ctrl+X, Y, Enter)

## Step 4: Set Up Systemd Service (Keep Backend Running)

**On the server:**

Create a systemd service file to keep your FastAPI app running:

```bash
sudo nano /etc/systemd/system/crm-backend.service
```

Paste this configuration (adjust paths if needed):
```ini
[Unit]
Description=CRM Analytics FastAPI Backend
After=network.target

[Service]
Type=simple
User=deploy
WorkingDirectory=/home/deploy/QHacks2026/backend
Environment="PATH=/home/deploy/QHacks2026/backend/venv/bin"
ExecStart=/home/deploy/QHacks2026/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable crm-backend
sudo systemctl start crm-backend
sudo systemctl status crm-backend
```

## Step 5: Configure Nginx as Reverse Proxy

**On the server:**

Set up Nginx to handle HTTPS and forward requests to your FastAPI app:

```bash
sudo nano /etc/nginx/sites-available/crm-backend
```

**⚠️ IMPORTANT:** Paste ONLY the configuration below (NOT the ```nginx or ``` markers!)

Paste this configuration:
```nginx
server {
    listen 80;
    server_name YOUR_SERVER_IP;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
        proxy_buffering off;
    }
}
```

**Remember to:**
- Replace `YOUR_SERVER_IP` with your actual server IP
- Save: Ctrl+X, then Y, then Enter

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/crm-backend /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

**On the server:**

## Step 6: Configure Firewall

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS (for future SSL)
sudo ufw enable
sudo ufw status
```

## Step 7: Test Your Deployment

**On the server:**
```bash
curl http://localhost:8000/health
```

**From your local machine (PowerShell):**
```powershell
Invoke-WebRequest -Uri http://YOUR_SERVER_IP/health -UseBasicParsing | Select-Object -ExpandProperty Content
```

**Or from bash/terminal:**
```bash
curl http://YOUR_SERVER_IP/health
```

You should see:
```json
{"status":"healthy","agent_initialized":true,"gradium_initialized":true}
```

## Step 8: Update Frontend Configuration

**On your local machine** (PowerShell), update the frontend to use your cloud endpoint:

```powershell
# Navigate to frontend directory
cd frontend

# Create .env.local file
@"
NEXT_PUBLIC_API_URL=http://YOUR_SERVER_IP
"@ | Out-File -FilePath .env.local -Encoding utf8

# Verify it was created
cat .env.local
```

**Or create manually:**
- Create `frontend/.env.local` file
- Add: `NEXT_PUBLIC_API_URL=http://YOUR_SERVER_IP`
- Replace `YOUR_SERVER_IP` with your actual Vultr server IP

## Step 9: Optional - Set Up SSL/HTTPS (Recommended)

**On the server:**

### Get a domain name (optional but recommended)
Point your domain to your Vultr server IP.

### Install Certbot for free SSL:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

Follow the prompts. Certbot will automatically configure HTTPS.

## Maintenance Commands (On Server)

### View logs:
```bash
sudo journalctl -u crm-backend -f
```

### Restart service:
```bash
sudo systemctl restart crm-backend
```

### Update code (SSH into server first):
```bash
cd ~/QHacks2026
git pull
cd backend
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart crm-backend
```

## Alternative: Docker Deployment (Simpler)

If you prefer Docker, see `docker-compose.yml` in the backend directory.

**Quick Docker setup (On Server):**
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker deploy

# Deploy with Docker Compose
cd ~/QHacks2026
docker-compose up -d
```

## Troubleshooting

**Most troubleshooting happens ON THE SERVER** (SSH in first)

### Backend not starting:
```bash
sudo systemctl status crm-backend
sudo journalctl -u crm-backend -n 50
```

### Check if port 8000 is listening:
```bash
sudo netstat -tlnp | grep 8000
```

### Nginx errors:
```bash
sudo nginx -t
sudo tail -f /var/log/nginx/error.log
```

### Can't connect from local machine:

**From PowerShell (local machine):**
```powershell
# Test if server is reachable
Test-NetConnection -ComputerName YOUR_SERVER_IP -Port 80

# Test health endpoint
Invoke-WebRequest -Uri http://YOUR_SERVER_IP/health -UseBasicParsing
```

**Then SSH into server and check:**
```bash
# Check if backend is running
sudo systemctl status crm-backend

# Check if nginx is running
sudo systemctl status nginx

# Check firewall
sudo ufw status
```

## Cost Estimate

- **Vultr VPS**: $6-12/month (2-4GB RAM)
- **Domain** (optional): $10-15/year
- **Total**: ~$6-12/month

## Your Backend URL

After deployment, your backend will be accessible at:
- **HTTP**: `http://YOUR_SERVER_IP`
- **With domain**: `http://yourdomain.com`
- **With SSL**: `https://yourdomain.com`

Update your frontend to use this URL instead of `http://localhost:8000`!

## PowerShell Quick Reference

**Common tasks from your local Windows machine:**

### Connect to server:
```powershell
ssh root@YOUR_SERVER_IP
# Or if you created deploy user:
ssh deploy@YOUR_SERVER_IP
```

### Test backend endpoint:
```powershell
Invoke-WebRequest -Uri http://YOUR_SERVER_IP/health -UseBasicParsing | Select-Object -ExpandProperty Content
```

### Test backend with POST request:
```powershell
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

### Create .env.local for frontend:
```powershell
cd frontend
@"
NEXT_PUBLIC_API_URL=http://YOUR_SERVER_IP
"@ | Out-File -FilePath .env.local -Encoding utf8
```

### Check if .env.local was created:
```powershell
Get-Content frontend\.env.local
```

### Upload file to server (SCP):
```powershell
scp C:\path\to\local\file.txt root@YOUR_SERVER_IP:/home/deploy/
```

### Download file from server:
```powershell
scp root@YOUR_SERVER_IP:/home/deploy/file.txt C:\path\to\local\
```

### Copy entire backend folder to server:
```powershell
scp -r .\backend root@YOUR_SERVER_IP:/home/deploy/QHacks2026/
```

## Need Help?

- Vultr Documentation: https://www.vultr.com/docs/
- FastAPI Deployment: https://fastapi.tiangolo.com/deployment/
