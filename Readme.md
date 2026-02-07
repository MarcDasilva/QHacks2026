# QHacks2026 - CRM Analytics Platform

A full-stack application for analyzing CRM service request data, featuring automated Python analytics with Supabase backend and Next.js frontend for visualizations.

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

## Quick Start

### Backend Setup

1. Navigate to backend directory:
   ```powershell
   cd backend
   ```

2. Install Python dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

3. Configure Supabase connection:
   ```powershell
   cp .env.example .env
   ```
   Edit `.env` with your Supabase credentials.

4. Run analysis scripts:
   ```powershell
   cd trends/calcs
   python backlog_distribution.py
   ```

See [backend/README.md](backend/README.md) for detailed documentation.

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

## Available Analyses

The backend generates the following analytics:

- **Backlog Distribution** - Histogram of unresolved ticket ages
- **Backlog Ranked List** - Unresolved tickets by service type with average age
- **First Call Resolution** - FCR rates by service category
- **Frequency Over Time** - Request volume trends by period
- **Geographic Hot Spots** - Choropleth map data by district
- **Priority Quadrant** - Volume vs. time-to-close scatter plot
- **Seasonality Heatmap** - Monthly patterns by service type
- **Time to Close** - Resolution time distributions
- **Top 10 Rankings** - Multiple top-10 lists (volume, backlog, trending, etc.)

## Technologies

- **Backend**: Python 3.x, Pandas, Supabase
- **Frontend**: Next.js, TypeScript, React
- **Database**: Supabase (PostgreSQL)

## Development Notes

- All Python scripts use relative paths that work with the new `backend/` folder structure
- Output files are saved to `backend/trends/data/`
- The `.env` file is gitignored and must be created from `.env.example`
- Frontend and backend can be developed independently

## Contributing

1. Make sure to test Python scripts from the `backend/trends/calcs/` directory
2. Keep environment variables in `.env` (never commit this file)
3. Follow the existing code structure and naming conventions

