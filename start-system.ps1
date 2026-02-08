# Startup script for CRM Analytics with Gemini Integration
# Run this script to start both backend and frontend servers

Write-Host "🚀 Starting CRM Analytics System..." -ForegroundColor Cyan
Write-Host ""

# Check if we're in the correct directory
if (-not (Test-Path ".\backend") -or -not (Test-Path ".\frontend")) {
    Write-Host "❌ Error: Please run this script from the QHacks2026 root directory" -ForegroundColor Red
    Write-Host "Your current directory: $(Get-Location)" -ForegroundColor Red
    exit 1
}

# Check if virtual environment exists
if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
    Write-Host "❌ Error: Virtual environment not found at .venv" -ForegroundColor Red
    Write-Host "Please create it with: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

Write-Host "1️⃣  Starting Backend API (FastAPI + Gemini)..." -ForegroundColor Green
Write-Host "   Port: 8000" -ForegroundColor Gray

# Start backend in new PowerShell window
$backendPath = Join-Path $PWD "backend"
$venvPath = Join-Path $PWD ".venv\Scripts\Activate.ps1"

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "& '$venvPath'; cd '$backendPath'; Write-Host '🤖 Backend API Server' -ForegroundColor Cyan; Write-Host 'Port: 8000' -ForegroundColor Green; uvicorn app.main:app --host 0.0.0.0 --port 8000"
)

Write-Host "   ✅ Backend window opened" -ForegroundColor Gray
Write-Host ""

# Wait a bit for backend to start
Write-Host "⏳ Waiting for backend to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

Write-Host "2️⃣  Starting Frontend (Next.js)..." -ForegroundColor Green
Write-Host "   Port: 3000" -ForegroundColor Gray

# Start frontend in new PowerShell window
$frontendPath = Join-Path $PWD "frontend"

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$frontendPath'; Write-Host '🎨 Frontend Dev Server' -ForegroundColor Cyan; Write-Host 'Port: 3000' -ForegroundColor Green; npm run dev"
)

Write-Host "   ✅ Frontend window opened" -ForegroundColor Gray
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""
Write-Host "✨ System Started Successfully! ✨" -ForegroundColor Green
Write-Host ""
Write-Host "📍 Access the application:" -ForegroundColor Yellow
Write-Host "   Frontend:  http://localhost:3000/dashboard" -ForegroundColor White
Write-Host "   Backend:   http://localhost:8000" -ForegroundColor White
Write-Host "   API Docs:  http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "💬 The chat interface is on Boohoo's body (right side)" -ForegroundColor Cyan
Write-Host ""
Write-Host "📝 Example questions:" -ForegroundColor Yellow
Write-Host "   • What are the top service categories?" -ForegroundColor Gray
Write-Host "   • Show me trends over time" -ForegroundColor Gray
Write-Host "   • What's in the backlog?" -ForegroundColor Gray
Write-Host "   • Show me geographic hotspots" -ForegroundColor Gray
Write-Host ""
Write-Host "🎮 Keyboard shortcuts:" -ForegroundColor Yellow
Write-Host "   Shift+T = Toggle talking animation" -ForegroundColor Gray
Write-Host "   Shift+Y = Toggle thinking animation" -ForegroundColor Gray
Write-Host "   Shift+U = Toggle glow effect" -ForegroundColor Gray
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to open the dashboard in your browser..." -ForegroundColor Green
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Open browser
Start-Process "http://localhost:3000/dashboard"

Write-Host "🌐 Browser opened!" -ForegroundColor Green
Write-Host ""
Write-Host "To stop the servers, close the backend and frontend PowerShell windows." -ForegroundColor Yellow
Write-Host ""
