# Backend - CRM Analytics

This backend contains Python scripts for analyzing CRM service request data from Supabase.

## Setup

### 1. Install Dependencies

```powershell
cd backend
pip install -r requirements.txt
```

### 2. Configure Supabase Connection

1. Copy `.env.example` to `.env`:
   ```powershell
   cp .env.example .env
   ```

2. Edit `.env` and add your Supabase credentials:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-anon-key
   SUPABASE_TABLE_NAME=CRMServiceRequests
   ```

### 3. Verify Connection

Test the connection by running any calculation script:

```powershell
cd trends/calcs
python backlog_distribution.py
```

## Structure

```
backend/
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variables template
├── .env                     # Your actual credentials (gitignored)
└── trends/
    ├── calcs/               # Analysis scripts
    │   ├── db_utils.py      # Shared Supabase connection utilities
    │   ├── backlog_distribution.py
    │   ├── backlog_ranked_list.py
    │   ├── first_calls.py
    │   ├── frequency_over_time.py
    │   ├── geographic_hot_spots.py
    │   ├── priority_quadrant.py
    │   ├── seasonality_heatmap.py
    │   ├── time_to_close.py
    │   └── top10.py
    └── data/                # Generated output files (CSV/GeoJSON)
```

## Running Analysis Scripts

All scripts now connect to Supabase instead of reading local CSV files. Simply run any script from the `trends/calcs` directory:

```powershell
cd trends/calcs
python <script_name>.py
```

The scripts will:
1. Connect to Supabase using credentials from `.env`
2. Fetch CRM data from the table
3. Process and analyze the data
4. Save results to `trends/data/`

## Notes

- **Geographic Hot Spots**: This script requires a GeoJSON source file at the root level (`CRMServiceRequests_-2988053277932401441.geojson`). If you don't have this file, the script will fail. You may need to upload it or modify the script to work without it.

- **All scripts** now use `db_utils.py` for data loading, making it easy to switch data sources or add caching in the future.

## Troubleshooting

### Import errors in calculation scripts

Make sure you're running scripts from the `trends/calcs` directory:
```powershell
cd trends/calcs
python script_name.py
```

### Supabase connection errors

1. Verify your `.env` file exists and has correct credentials
2. Test your Supabase connection using:
   ```python
   from db_utils import load_crm_data_from_supabase
   df = load_crm_data_from_supabase()
   print(f"Loaded {len(df)} records")
   ```

### Missing dependencies

```powershell
pip install -r requirements.txt
```
