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

## Cluster visualization (embeddings)

Request embeddings (384D) are clustered in the DB; to visualize them in the dashboard:

1. **Apply migration** `app/db/migrations/003_request_2d.sql` (creates `request_2d` table).
2. **Run UMAP script** (one-off or after re-clustering):
   ```bash
   python scripts/compute_2d_umap.py
   ```
   Only **level-1 clusters (all 25)** are included; other clusters are removed from `request_2d`. Uses **1-in-6 sampling** within those clusters. Optional: `--sample-every 1` for no sampling, `--n-neighbors 30` to tune UMAP. For **3D visualization**, run `python scripts/compute_2d_umap.py --3d` (add `z_2d` column first: run `app/db/migrations/004_add_z_2d.sql` in Supabase).
3. **Dashboard**: Open the dashboard home to see **2D** and **3D** cluster scatter views (3D appears after you run with `--3d`).

**Feder** is a JS tool for visualizing Faiss/HNSW index files. This project uses Supabase + pgvector + MiniBatchKMeans, not Faiss/HNSW. Feder is only relevant if you export a Faiss/HNSW index to inspect; the main visualization is the custom Cluster view above (precomputed 2D from UMAP).

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
