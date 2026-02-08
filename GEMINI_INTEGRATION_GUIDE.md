# 🎯 CRM Analytics with Gemini AI Chat Integration

## Overview
This project integrates a Gemini AI-powered chat assistant with your CRM analytics dashboard. The assistant can analyze data, provide insights, and automatically navigate to relevant visualization pages.

## Architecture
- **Backend**: FastAPI server with streaming Gemini AI integration
- **Frontend**: Next.js dashboard with real-time chat interface
- **AI Agent**: Two-stage Gemini process (planning → data retrieval → analysis)

## 🚀 Quick Start

### 1. Backend Setup (Terminal 1)

```powershell
# Navigate to backend directory
cd backend

# Activate virtual environment (if not already active)
.venv\Scripts\Activate.ps1

# Start the FastAPI server
python app/main.py
```

The API will start on: `http://localhost:8000`

### 2. Frontend Setup (Terminal 2)

```powershell
# Navigate to frontend directory
cd frontend

# Start the Next.js dev server
npm run dev
```

The frontend will start on: `http://localhost:3000`

## 💬 Using the Chat Interface

### Where to Find It
- Navigate to the dashboard: `http://localhost:3000/dashboard`
- Look for the **Boohoo mascot** on the right side
- The **chat interface** is overlaid on Boohoo's body

### Example Questions

1. **"What are the top service categories by volume?"**
   - Agent will select relevant data products
   - Navigate to appropriate analytics pages
   - Provide analysis with specific numbers

2. **"Show me trends over time"**
   - Agent navigates to frequency analytics
   - Analyzes temporal patterns
   - Highlights key insights

3. **"What's in the backlog?"**
   - Loads backlog data
   - Navigates to backlog view
   - Provides ranked analysis

4. **"Show me geographic hotspots"**
   - Navigates to geographic view
   - Analyzes location-based data
   - Highlights high-volume areas

### Chat Features

**Real-time Thought Process**:
- 🤔 **Planning**: See what data products the agent selects
- 📊 **Data Loading**: Watch as data is retrieved
- 🧭 **Navigation**: Agent automatically opens relevant pages
- 🧠 **Analysis**: Final insights with metrics and rationale

**Message Types**:
- **User messages**: Your questions (blue, right-aligned)
- **Thought bubbles**: Agent's reasoning process (italic, with spinner)
- **Plan cards**: Selected data products (blue box)
- **Navigation**: Automatic page transitions (purple text)
- **Answer cards**: Final analysis (green box with metrics)
- **Errors**: Connection or processing issues (red box)

## 🔧 Technical Details

### Backend API Endpoints

- `GET /`: API status
- `GET /health`: Health check (shows if agent is initialized)
- `POST /api/chat/stream`: Streaming chat endpoint (SSE)
- `POST /api/chat`: Non-streaming chat endpoint (for testing)

### Data Flow

1. **User asks question** → Frontend sends to `/api/chat/stream`
2. **Server-Sent Events (SSE)** stream real-time updates
3. **Stage 1: Planning** → Gemini selects data products from catalog
4. **Stage 2: Data Retrieval** → Load summaries or raw data
5. **Stage 3: Analysis** → Gemini analyzes data and generates insights
6. **Navigation** → Frontend router automatically switches tabs
7. **Final Answer** → Complete analysis with metrics

### Frontend Components

- **ChatInterface** (`components/chat-interface.tsx`): Main chat UI
- **Dashboard Layout** (`app/dashboard/layout.tsx`): Integrates chat with Boohoo
- **Analytics Pages**: `/dashboard/analytics/[frequency|backlog|geographic|priority-quadrant|population]`

### Backend Components

- **FastAPI Server** (`app/main.py`): HTTP API with SSE streaming
- **CRMAnalyticsAgent** (`agent/agent.py`): Orchestrates two-stage process
- **GeminiAgent** (`agent/gemini_client.py`): Direct Gemini API integration
- **DataLoader** (`agent/data_loader.py`): Loads CSV data and summaries
- **Catalog** (`agent/catalog.py`): Data product metadata

## 🎨 Customization

### Adjusting Chat Position

In `frontend/src/app/dashboard/layout.tsx`, modify the spacer height:

```tsx
{/* Adjust this percentage to move chat up/down on Boohoo's body */}
<div className="h-[30%] shrink-0" />
```

### Chat UI Styling

In `frontend/src/components/chat-interface.tsx`:
- Modify message colors and styles
- Customize loading animations
- Change layout and spacing

### Backend Prompts

In `backend/agent/gemini_client.py`:
- Customize planning prompts
- Adjust analysis format
- Modify JSON output structure

## 🐛 Troubleshooting

### Backend won't start
- **Error**: `Agent not initialized`
- **Fix**: Check that `GEMINI_API_KEY` is set in `backend/.env`

### Chat shows connection error
- **Error**: `Failed to connect to the backend`
- **Fix**: Make sure backend is running on `http://localhost:8000`
- Test with: `curl http://localhost:8000/health`

### Navigation not working
- **Check**: Frontend routes match the navigation mapping in `app/main.py`
- **Verify**: All analytics pages exist under `/dashboard/analytics/`

### Streaming stops mid-response
- **Check**: Browser console for errors
- **Verify**: SSE connection is maintained (no CORS issues)
- **Test**: Use non-streaming endpoint `/api/chat` first

### Gemini API errors
- **Rate limits**: Wait and retry
- **Invalid API key**: Check `.env` file
- **JSON parsing errors**: Agent will fallback to raw text response

## 📊 Data Products Available

The agent has access to these data products:
- `top10_volume_30d`: Top categories by recent volume
- `top10_worst_p90_time`: Slowest resolution times
- `top10_backlog_age`: Oldest open requests
- `top10_trending_up`: Growing categories
- `frequency_over_time`: Monthly trends 2019-present
- `backlog_ranked_list`: Prioritized backlog
- `backlog_distribution`: Backlog age distribution
- `priority_quadrant`: Urgency vs. volume matrix
- `geographic_hot_spots`: Location-based analysis
- `time_to_close`: Resolution time analysis

## 🔐 Environment Variables

### Backend (`backend/.env`)
```env
GEMINI_API_KEY=your_key_here
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SUPABASE_TABLE_NAME=CRMServiceRequests
```

### Frontend
No additional environment variables needed for local development.

## 📝 Next Steps

1. **Test the integration**: Start both servers and try example questions
2. **Customize prompts**: Adjust Gemini prompts for your specific use case
3. **Add more data products**: Extend the catalog in `agent/catalog.py`
4. **Enhance UI**: Customize chat styling and Boohoo interactions
5. **Deploy**: Configure production CORS, API keys, and hosting

## 🎉 Features

✅ Real-time streaming responses
✅ Automatic page navigation
✅ Two-stage AI reasoning (planning + analysis)
✅ Beautiful chat UI overlaid on mascot
✅ Detailed thought process visibility
✅ Error handling and fallbacks
✅ Support for multiple data products
✅ Mobile-responsive design

---

**Need help?** Check the console logs in both frontend and backend for debugging information.
