# Quick Start: Connecting Frontend to Cloud Backend

After deploying your backend to Vultr, follow these steps to connect your frontend:

## 1. Get Your Backend URL

After deploying to Vultr, you'll have:
- **IP Address**: `http://YOUR_SERVER_IP` (e.g., `http://123.45.67.89`)
- **Or Domain**: `https://api.yourdomain.com` (if you set up a domain + SSL)

## 2. Update Frontend Environment

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://YOUR_SERVER_IP
```

**Example:**
```env
NEXT_PUBLIC_API_URL=http://123.45.67.89
```

## 3. Update Backend CORS (Already Done ✅)

The backend has been updated to accept the `FRONTEND_URL` environment variable.

On your Vultr server, add to `backend/.env`:

```env
FRONTEND_URL=http://localhost:3000
```

Or if you deploy your frontend too:
```env
FRONTEND_URL=https://your-frontend-domain.com
```

## 4. Update Frontend API Calls

Find all API calls in your frontend code and ensure they use `process.env.NEXT_PUBLIC_API_URL`:

```typescript
// Example API call
const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/chat/stream`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message, mode })
});
```

## 5. Test the Connection

```bash
# Test from your local machine
curl http://YOUR_SERVER_IP/health

# Should return:
# {"status":"healthy","agent_initialized":true,"gradium_initialized":true}
```

## 6. Run Frontend Locally (Connected to Cloud)

```bash
cd frontend
npm install
npm run dev
```

Your frontend now connects to the cloud backend! No need to run the backend locally anymore.

## Optional: Deploy Frontend Too

You can also deploy your Next.js frontend to:
- **Vercel** (easiest, free tier available)
- **Netlify** (also easy, free tier)
- **Vultr** (same server or separate instance)

### Quick Vercel Deployment:
```bash
cd frontend
npm install -g vercel
vercel
```

Then set environment variables in Vercel dashboard:
- `NEXT_PUBLIC_API_URL` = `http://YOUR_SERVER_IP`

## Troubleshooting

### CORS errors?
Make sure backend `.env` has:
```env
FRONTEND_URL=http://localhost:3000
```

Or for production:
```env
ALLOW_ALL_ORIGINS=true  # Temporary for testing
```

### Can't connect to backend?
1. Check firewall: `sudo ufw status`
2. Check backend is running: `sudo systemctl status crm-backend`
3. Check backend logs: `sudo journalctl -u crm-backend -f`
4. Test directly: `curl http://YOUR_SERVER_IP/health`

### Still using localhost:8000?
Search your frontend code for hardcoded URLs:
```bash
grep -r "localhost:8000" frontend/src/
```

Replace with `${process.env.NEXT_PUBLIC_API_URL}`
