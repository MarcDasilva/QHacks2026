# QHacks2026 - CRM Analytics Platform

A full-stack application for analyzing CRM service request data, featuring automated Python analytics with Supabase backend, Next.js frontend for visualizations, and **AI-powered chat with voice interaction** using Gemini AI and Gradium voice services.

## ✨ Features

### 🤖 AI Chat Assistant (Gemini)
- **Intelligent Data Analysis**: Two-stage agent architecture for planning and analysis
- **Dual Modes**: 
  - Simple chat mode for conversational interactions
  - Deep analysis mode for comprehensive data investigation
- **Automatic Navigation**: Intelligently routes users to relevant analytics visualizations
- **Real-time Streaming**: Server-Sent Events (SSE) for live response streaming
- **Cluster Prediction**: Uses BERT/sentence-transformers to predict relevant clusters from user queries
- **Search Keyword Extraction**: Gemini extracts search keywords before embedding-based cluster matching
- **Context-Aware Responses**: Adapts messaging based on user's analysis mode history

### 🎙️ Voice Interaction (Gradium)
- **Text-to-Speech (TTS)**: Professional voice output with Jack (British voice)
  - Standard TTS endpoint for complete audio generation
  - Streaming TTS for low-latency audio chunks
  - Word-level timestamps for subtitle synchronization
- **Speech-to-Text (STT)**: Voice input with automatic transcription
  - Streaming STT with real-time partial transcripts via SSE
  - Always transcribes in English
  - Supports WAV, PCM, and Opus audio formats
- **Low-Latency Streaming**: Optimized for real-time voice interactions

### 📊 Cluster Visualization
- **2D Cluster Scatter View**: Interactive UMAP-based visualization of request embeddings
- **3D Cluster Scatter View**: Three-dimensional cluster exploration (optional)
- **Cluster Highlighting**: Automatic highlighting of predicted clusters from chat queries
- **Cluster Navigation**: Seamless flow from cluster selection to detailed analytics
- **Embedding-Based Clustering**: 384D request embeddings clustered using MiniBatchKMeans
- **Level-1 Clusters**: 25 primary clusters with hierarchical sub-clusters
- **Smart Sampling**: Configurable sampling (default 1-in-6) for performance optimization

### 📄 PDF Report Generation
- **Automated Report Creation**: Generate comprehensive PDF reports from cluster analysis
- **Structured Content**: Includes answer, rationale, and key metrics
- **Supporting Data Analysis**: CSV-based charts and visualizations embedded in reports
- **Cluster Context**: Reports include parent and child cluster labels
- **Timestamped Reports**: Automatically includes generation date and time
- **Report Flow**: Complete workflow from cluster → analytics visit → report generation

### 📈 Analytics Dashboard
- **Frequency Over Time**: Request volume trends and patterns over time periods
- **Backlog Analytics**: 
  - Ranked list of unresolved tickets by service type
  - Distribution histogram of backlog ages
- **Priority Quadrant**: Volume vs. time-to-close scatter plot for resource allocation
- **Geographic Hot Spots**: Choropleth map visualization by district
- **Time to Close**: Resolution time distributions and statistics
- **Interactive Visualizations**: Modern, responsive charts and graphs
- **Data Tables**: Sortable, filterable data tables for detailed exploration

### 🔍 Advanced Analytics Features
- **Top 10 Rankings**: Multiple top-10 lists including:
  - Volume (30-day)
  - Worst P90 time-to-close
  - Backlog age
  - Trending categories
  - Geographic hotspots
- **First Call Resolution (FCR)**: FCR rates by service category
- **Seasonality Heatmap**: Monthly patterns by service type
- **Analytics Visit Flow**: Intelligent routing from cluster analysis to relevant analytics pages

## 📚 Documentation

### For Frontend Integration
- **[BACKEND_API_INTEGRATION.md](./BACKEND_API_INTEGRATION.md)** - Complete API reference with examples
- **[BACKEND_CHANGES.md](./BACKEND_CHANGES.md)** - Summary of backend changes and requirements
- **[GEMINI_INTEGRATION_GUIDE.md](./GEMINI_INTEGRATION_GUIDE.md)** - Gemini AI chat integration guide
- **[VOICE_FEATURES.md](./VOICE_FEATURES.md)** - Voice interaction implementation details

### For Backend Development
- **[backend/README.md](./backend/README.md)** - Backend setup and structure
- **[backend/agent/README.md](./backend/agent/README.md)** - Agent implementation details

## 🚀 Quick Start

### Backend API Server

**Prerequisites:**
- Python 3.8+ (Python 3.12+ required for Gradium voice features)
- Valid `GEMINI_API_KEY` (from [Google AI Studio](https://aistudio.google.com/))
- Valid `GRADIUM_API_KEY` (from [Gradium.ai](https://gradium.ai)) - Optional, for voice features
- `DATABASE_URL` - Supabase PostgreSQL connection string (for cluster features)
- `SUPABASE_URL` and `SUPABASE_KEY` - For analytics data loading

**Setup:**
1. Navigate to backend directory:
   ```powershell
   cd backend
   ```

2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

3. Create `.env` file with API keys and database configuration:
   ```env
   # AI & Voice Services
   GEMINI_API_KEY=your_gemini_key_here
   GRADIUM_API_KEY=your_gradium_key_here  # Optional, for voice features
   
   # Database (for cluster visualization and analytics)
   DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-anon-key
   SUPABASE_TABLE_NAME=CRMServiceRequests
   ```

4. Start the FastAPI server:
   ```powershell
   python app/main.py
   ```

   Server runs on: `http://localhost:8000`

5. Verify health:
   ```bash
   curl http://localhost:8000/health
   ```

### API Endpoints

The backend provides the following REST API endpoints:

**Chat & AI:**
- `POST /api/chat/stream` - Streaming AI chat with SSE (supports "auto", "deep_analysis", "chat" modes)
- `POST /api/chat` - Non-streaming chat endpoint (for testing)
- `POST /api/cluster/predict` - Predict parent/child cluster IDs from text message
- `POST /api/chat/analytics-visit` - Get analytics page URL and discussion for cluster context

**Voice (Text-to-Speech):**
- `POST /api/voice/tts` - Convert text to speech (WAV, PCM, Opus formats)
- `POST /api/voice/tts/stream` - Streaming TTS with audio chunks
- `POST /api/voice/tts/with-timestamps` - TTS with word-level timestamps for subtitle sync

**Voice (Speech-to-Text):**
- `POST /api/voice/stt/stream` - Streaming STT with SSE (real-time partial transcripts)
- `POST /api/voice/stt` - Non-streaming STT (complete transcription)

**Reports:**
- `POST /api/report/generate` - Generate PDF report from cluster analysis and discussion

**Health & Info:**
- `GET /health` - Service health check (includes agent and Gradium initialization status)
- `GET /` - API information and status

See [BACKEND_API_INTEGRATION.md](./BACKEND_API_INTEGRATION.md) for detailed endpoint documentation and examples.

## Project Structure

```
QHacks2026/
├── backend/                          # Python analytics backend
│   ├── requirements.txt              # Python dependencies
│   ├── .env.example                  # Environment configuration template
│   ├── README.md                     # Backend-specific documentation
│   └── trends/
│       ├── calcs/                    # Analysis calculation scripts
│       │   ├── db_utils.py          # Shared Supabase utilities
│       │   └── *.py                 # Individual analysis scripts
│       └── data/                     # Generated analysis outputs
│
├── frontend/                         # Next.js visualization frontend
│   ├── package.json
│   ├── src/
│   └── ...
│
└── CRMServiceRequests_*.csv         # Legacy local data (for reference)
```

## Data Analytics Scripts

### Running Analysis Scripts

The backend includes Python scripts for generating analytics data:

1. Navigate to backend directory:
   ```powershell
   cd backend
   ```

2. Configure Supabase connection:
   ```powershell
   cp .env.example .env
   ```
   Edit `.env` with your Supabase credentials.

3. Run individual analysis scripts:
   ```powershell
   cd trends/calcs
   python backlog_distribution.py
   python frequency_over_time.py
   # ... etc
   ```

See [backend/README.md](backend/README.md) for detailed documentation.

### Cluster Visualization Setup

To enable cluster visualization features (2D/3D scatter views):

1. **Apply database migrations** (in Supabase SQL editor):
   - Run `backend/app/db/migrations/003_request_2d.sql` to create the `request_2d` table
   - For 3D visualization, also run `backend/app/db/migrations/004_add_z_2d.sql`

2. **Compute UMAP embeddings**:
   ```powershell
   cd backend
   python scripts/compute_2d_umap.py
   ```
   
   Options:
   - `--sample-every 1` - No sampling (include all records)
   - `--n-neighbors 30` - Tune UMAP neighborhood size
   - `--3d` - Generate 3D coordinates (requires z_2d column)

3. **View in dashboard**: The cluster scatter views will appear on the dashboard home page after UMAP computation.

**Note**: Only level-1 clusters (all 25) are included in the visualization. Uses 1-in-6 sampling by default for performance.

### Frontend Setup

1. Navigate to frontend directory:
   ```powershell
   cd frontend
   ```

2. Install dependencies:
   ```powershell
   npm install
   ```

3. Run development server:
   ```powershell
   npm run dev
   ```

## Data Source

The application now uses **Supabase as the primary data source**. The local CSV file is kept for reference only. All Python scripts have been updated to:
- Load data directly from Supabase
- Use environment variables for configuration
- Share common database utilities via `db_utils.py`

## Available Data Products & Analyses

The backend generates the following analytics data products (accessible via the AI agent):

**Top 10 Rankings:**
- `top10_volume_30d` - Top categories by recent volume (30 days)
- `top10_worst_p90_time` - Categories with worst P90 time-to-close
- `top10_backlog_age` - Top 10 oldest backlogs by P90 age
- `top10_trending_up` - Top 10 categories trending upward
- `top10_geographic_hotspots` - Top 10 geographic areas by volume

**Time Series & Trends:**
- `frequency_over_time` - Monthly time series by category
- `seasonality_heatmap` - Day/month patterns by service type

**Backlog Analysis:**
- `backlog_ranked_list` - Unresolved requests by service type with average age
- `backlog_distribution` - Histogram of unresolved ticket ages

**Performance Metrics:**
- `time_to_close` - Resolution time distributions and statistics
- `fcr_by_category` - First Call Resolution rates by service category

**Spatial & Priority Analysis:**
- `geographic_hot_spots` - Geographic clustering and choropleth map data by district
- `priority_quadrant` - Priority matrix (volume × time-to-close) for resource allocation

All data products are stored as CSV files in `backend/trends/data/` and can be accessed programmatically via the AI agent's data catalog.

## Technologies

**Backend:**
- Python 3.8+ (Python 3.12+ required for Gradium voice features)
- FastAPI - REST API framework with async support
- Pandas - Data analysis and manipulation
- Supabase - PostgreSQL database with pgvector extension
- Gemini AI - Google's AI model for chat and analysis
- Gradium - Voice services (TTS/STT)
- UMAP - Dimensionality reduction for cluster visualization
- Sentence-transformers - BERT embeddings for cluster prediction
- ReportLab - PDF report generation

**Frontend:**
- Next.js - React framework with App Router
- TypeScript - Type-safe JavaScript
- React - UI component library
- Tailwind CSS - Utility-first styling
- shadcn/ui - Component library

**Database & Infrastructure:**
- Supabase (PostgreSQL) - Primary data storage
- pgvector - Vector similarity search for embeddings
- MiniBatchKMeans - Clustering algorithm for request embeddings

## Complete Workflow

### User Journey: Cluster → Analytics → Report

1. **Cluster Discovery**: 
   - User interacts with AI chat assistant
   - AI predicts relevant clusters from user queries
   - Dashboard highlights matching clusters in 2D/3D scatter view

2. **Cluster Selection**:
   - User selects a cluster (parent/child combination)
   - System loads cluster records and context

3. **Analytics Visit**:
   - AI suggests relevant analytics page based on cluster context
   - User navigates to analytics dashboard (Frequency, Backlog, Priority Quadrant, etc.)
   - System provides discussion linking cluster to analytics insights

4. **Report Generation**:
   - User completes analysis flow
   - System generates comprehensive PDF report
   - Report includes answer, rationale, key metrics, and supporting data visualizations
   - Report is displayed in the Reports page

### AI Agent Workflow

1. **Planning Stage**: Gemini analyzes user question and selects relevant data products
2. **Data Fetching**: System loads CSV data from `backend/trends/data/`
3. **Analysis Stage**: Gemini generates insights using retrieved data
4. **Navigation**: System automatically routes to relevant visualization pages
5. **Response**: Structured answer with rationale and key metrics

## Development Notes

- All Python scripts use relative paths that work with the new `backend/` folder structure
- Output files are saved to `backend/trends/data/`
- The `.env` file is gitignored and must be created from `.env.example`
- Frontend and backend can be developed independently
- Cluster visualization requires UMAP computation (see Cluster Visualization Setup above)
- Voice features require Python 3.12+ and Gradium API key
- Report generation requires `reportlab` package (`pip install reportlab`)

## Contributing

1. Make sure to test Python scripts from the `backend/trends/calcs/` directory
2. Keep environment variables in `.env` (never commit this file)
3. Follow the existing code structure and naming conventions

