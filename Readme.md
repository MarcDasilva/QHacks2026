# Compass - Contextual Ai Agent

A full-stack application for analyzing Kingston Databases with a friendly faec, featuring automated Python analytics with Supabase backend, Next.js frontend for visualizations, and **AI-powered chat with voice interaction** using Gemini AI and Gradium voice services.

## ✨ Features

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
