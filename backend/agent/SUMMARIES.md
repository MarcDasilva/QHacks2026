# Data Summaries System

## Overview

Pre-generate and save data summaries to improve performance. Instead of loading full CSV files and summarizing them every time Gemini needs data, the agent can load pre-generated text summaries instantly.

## Benefits

- **Faster Response Times**: Load summaries in milliseconds vs. loading full CSVs
- **Reduced Memory**: Text files are smaller than DataFrames
- **Consistent Format**: All summaries follow the same structure
- **Lower Token Usage**: Optimized summaries vs. raw data conversion

## Commands

### Generate All Summaries

```powershell
# Generate summaries for all 13 data products
& .venv/Scripts/python.exe backend/agent/generate_summaries.py generate

# Generate with custom row limit
& .venv/Scripts/python.exe backend/agent/generate_summaries.py generate 100
```

### List Available Summaries

```powershell
& .venv/Scripts/python.exe backend/agent/generate_summaries.py list
```

### View a Specific Summary

```powershell
& .venv/Scripts/python.exe backend/agent/generate_summaries.py view top10_volume_30d
```

### Regenerate One Summary

```powershell
& .venv/Scripts/python.exe backend/agent/generate_summaries.py regenerate top10_volume_30d 50
```

## Summary Format

Each summary file includes:
- **Metadata**: Product info, generation timestamp, description
- **Stats**: Shape, columns, data types
- **Preview**: First N rows of data (default: 50)

Example format:
```
# Data Summary: top10_volume_30d
# Generated: 2026-02-07 14:30:00
# Description: Top 10 service categories by volume in the last 30 days
# Source File: top10.csv
# Filter: ranking_type == 'Volume (Last 30 Days)'
# Use Cases: identify highest demand, prioritize resources, current trends
# Metrics: volume, percentage of total
================================================================================

Shape: 10 rows × 9 columns
Columns: ranking_type, rank, category, primary_metric, ...

First 50 rows (of 10 total):
ranking_type        rank  category                    ...
Volume (Last 30 Days)  1  Recreation and leisure      ...
...
```

## Location

Summaries are saved to: `backend/trends/data/summaries/`

Each summary is named: `{product_id}.txt`

## Python Usage

### Generate Programmatically

```python
from backend.agent.generate_summaries import generate_all_summaries

# Generate all summaries
generate_all_summaries(max_rows=50)
```

### View Summaries

```python
from backend.agent.generate_summaries import view_summary, list_summaries

# List all
list_summaries()

# View one
view_summary("top10_volume_30d")
```

### Using Summaries in Agent

The agent automatically uses summaries if they exist:

```python
from backend.agent import CRMAnalyticsAgent

# Agent will automatically use pre-generated summaries
agent = CRMAnalyticsAgent()
result = agent.query("What are the top categories?")

# The agent checks for summaries first:
# 📄 = loaded from pre-generated summary (fast)
# 💾 = loaded and summarized from CSV (slower)
```

### Disable Summary Usage

```python
# Force loading from CSV every time (not recommended)
agent = CRMAnalyticsAgent()
agent.data_loader.use_summaries = False
```

## When to Regenerate

Regenerate summaries when:
- CSV data files are updated
- You add new data products to the catalog
- You want to change the number of preview rows
- Data structure changes

## Workflow

1. **Initial Setup**: Generate all summaries once
   ```powershell
   & .venv/Scripts/python.exe backend/agent/generate_summaries.py
   ```

2. **Use Agent**: Agent automatically uses summaries
   ```python
   agent = CRMAnalyticsAgent()
   result = agent.query("Your question")
   ```

3. **Update Data**: When CSV files change, regenerate summaries
   ```powershell
   & .venv/Scripts/python.exe backend/agent/generate_summaries.py generate
   ```

## File Structure

```
backend/
  trends/
    data/
      summaries/               ← Summary files saved here
        top10_volume_30d.txt
        top10_backlog_age.txt
        top10_trending_up.txt
        top10_geographic_hotspots.txt
        frequency_over_time.txt
        ... (13 total)
      top10.csv                ← Original data
      frequency_over_time.csv
      ...
```

## Performance

**Before (loading CSVs)**:
- Load CSV: ~100-500ms per file
- Convert to summary: ~50-100ms
- Total: ~150-600ms per product

**After (using pre-generated summaries)**:
- Load text file: ~5-10ms per file
- Total: ~5-10ms per product

**Result**: 15-60x faster! ⚡
