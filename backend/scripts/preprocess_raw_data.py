"""
Preprocess data from the data folder to create a CSV matching the requests table schema.
This script:
1. Reads the original CSV file from the data folder
2. Transforms data to match requests table columns
3. Randomly samples 50% of the rows
4. Saves a new CSV file that matches the requests table schema (no id, no embeddings, no clusters)

Usage:
python scripts/preprocess_raw_data.py
python scripts/preprocess_raw_data.py --input data/CRMServiceRequests_1548651211056691263.csv --output data/requests_50pct.csv --percent 50
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import pandas as pd
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))


def parse_date(date_str):
    """Parse date string to date object. Returns None if invalid."""
    if not date_str or pd.isna(date_str):
        return None
    
    date_formats = [
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%d/%m/%Y',
        '%Y-%m-%d %H:%M:%S',
        '%m/%d/%Y %H:%M:%S',
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(str(date_str).strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    
    return None


def build_description(row):
    """Build description from Service Level 1-5 columns."""
    levels = []
    for i in range(1, 6):
        level = row.get(f'Service Level {i}')
        if level and pd.notna(level) and str(level).strip():
            levels.append(str(level).strip())
    
    return ' > '.join(levels) if levels else None


def build_location(row):
    """Build location from Electoral District and Neighbourhood."""
    parts = []
    
    electoral_district = row.get('Electoral District')
    if electoral_district and pd.notna(electoral_district):
        parts.append(str(electoral_district).strip())
    
    neighbourhood = row.get('Neighbourhood')
    if neighbourhood and pd.notna(neighbourhood):
        parts.append(str(neighbourhood).strip())
    
    return ', '.join(parts) if parts else None


def preprocess_csv(input_path, output_path, percent=50, random_seed=42):
    """
    Preprocess CSV file to match requests table schema.
    
    Args:
        input_path: Path to input CSV file
        output_path: Path to output CSV file
        percent: Percentage of rows to keep (default: 50)
        random_seed: Random seed for reproducibility (default: 42)
    """
    print(f"[INFO] Reading CSV file: {input_path}")
    
    # Read the CSV file
    df = pd.read_csv(input_path)
    print(f"[INFO] Found {len(df):,} rows in original CSV file")
    
    # Required columns from original CSV
    required_columns = [
        "Service Request ID",
        "Reference Number",
        "Service Type",
        "Date Created",
        "Date Closed",
        "Electoral District",
        "Neighbourhood"
    ]
    
    # Check for required columns
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"[ERROR] Missing required columns in CSV: {missing_columns}")
        print(f"[INFO] Available columns: {df.columns.tolist()}")
        return False
    
    # Filter out rows without required fields before sampling
    initial_count = len(df)
    df = df[
        df['Service Request ID'].notna() &
        df['Service Type'].notna() &
        df['Date Created'].notna()
    ].copy()
    
    filtered_count = len(df)
    if filtered_count < initial_count:
        print(f"[INFO] Filtered out {initial_count - filtered_count} rows missing required fields")
    
    if filtered_count == 0:
        print("[ERROR] No valid rows remaining after filtering")
        return False
    
    # Calculate number of rows to keep
    rows_to_keep = int(filtered_count * percent / 100)
    
    print(f"[INFO] Sampling {rows_to_keep:,} rows ({percent}% of {filtered_count:,} valid rows)")
    
    # Randomly sample the rows
    df_sampled = df.sample(n=rows_to_keep, random_state=random_seed)
    
    # Transform to requests table schema
    print(f"[INFO] Transforming data to match requests table schema...")
    
    requests_data = []
    skipped_count = 0
    
    for idx, row in df_sampled.iterrows():
        # Parse dates
        created_at = parse_date(row.get('Date Created'))
        if not created_at:
            skipped_count += 1
            continue  # created_at is required
        
        resolved_at = parse_date(row.get('Date Closed'))
        
        # Build fields
        service_request_id = str(row.get('Service Request ID')).strip()
        ref_number = row.get('Reference Number')
        if ref_number and pd.notna(ref_number):
            ref_number = str(ref_number).strip()
        else:
            ref_number = None
        
        service_type = str(row.get('Service Type')).strip()
        description = build_description(row)
        location = build_location(row)
        
        requests_data.append({
            'service_request_id': service_request_id,
            'ref_number': ref_number,
            'service_type': service_type,
            'description': description,
            'created_at': created_at,
            'resolved_at': resolved_at,
            'location': location
        })
    
    if skipped_count > 0:
        print(f"[WARNING] Skipped {skipped_count} rows due to invalid dates")
    
    # Create DataFrame with requests table columns
    df_requests = pd.DataFrame(requests_data)
    
    # Ensure output directory exists
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save to CSV
    print(f"[INFO] Saving to: {output_path}")
    df_requests.to_csv(output_path, index=False)
    
    print(f"[SUCCESS] Created CSV with {len(df_requests):,} rows")
    print(f"[INFO] File saved to: {output_path}")
    
    # Show sample of the output
    print(f"\n[INFO] Sample of output data:")
    print(df_requests.head())
    
    return True


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Preprocess CSV data to match raw_requests table schema'
    )
    parser.add_argument(
        '--input',
        type=str,
        default='data/CRMServiceRequests_1548651211056691263.csv',
        help='Path to input CSV file (default: data/CRMServiceRequests_1548651211056691263.csv)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='data/raw_requests_50pct.csv',
        help='Path to output CSV file (default: data/raw_requests_50pct.csv)'
    )
    parser.add_argument(
        '--percent',
        type=int,
        default=50,
        help='Percentage of rows to keep (default: 50)'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed for reproducibility (default: 42)'
    )
    
    args = parser.parse_args()
    
    if args.percent <= 0 or args.percent >= 100:
        print("[ERROR] Percent must be between 1 and 99")
        return 1
    
    # Check if input file exists
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[ERROR] Input file not found: {input_path}")
        return 1
    
    try:
        success = preprocess_csv(
            str(input_path),
            args.output,
            percent=args.percent,
            random_seed=args.seed
        )
        
        if success:
            print("\n[SUCCESS] Preprocessing complete!")
            print(f"[INFO] You can now upload {args.output} to the requests table")
            print(f"[INFO] CSV columns: service_request_id, ref_number, service_type, description, created_at, resolved_at, location")
            return 0
        else:
            print("\n[ERROR] Preprocessing failed")
            return 1
    
    except Exception as e:
        print(f"[ERROR] Failed to preprocess CSV: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
