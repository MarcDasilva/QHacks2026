"""
Time-to-Close Histogram Analysis

Generates data for histograms showing time-to-close distribution per Service Type:
- X-axis: time-to-close days in bins (0, 1-2, 3-7, 8-30, 31-90, 90+)
- Y-axis: count
- Includes median, p75, p90 markers

This visualization helps identify:
- How quickly cases are typically resolved (median)
- The "pain points" where slow cases drag down satisfaction (p90)
- Distribution patterns showing if most cases close fast or if there's a long tail
"""

import pandas as pd
import numpy as np
from pathlib import Path
from db_utils import load_crm_data_cached

# Configuration
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "time_to_close.csv"

# Time-to-close bins (in days)
TIME_BINS = [0, 1, 3, 8, 31, 91, float('inf')]
TIME_LABELS = ['0 days', '1-2 days', '3-7 days', '8-30 days', '31-90 days', '90+ days']


def load_data():
    """Load the CRM service request data"""
    df = load_crm_data_cached()
    
    # Convert date columns to datetime
    df['Date Created'] = pd.to_datetime(df['Date Created'], errors='coerce')
    df['Date Closed'] = pd.to_datetime(df['Date Closed'], errors='coerce')
    
    print(f"Total records loaded: {len(df)}")
    print(f"Columns: {df.columns.tolist()}")
    
    return df


def filter_closed_items(df):
    """
    Filter for closed/resolved items only
    Closed = Status Type is 'Solved' AND Date Closed is not null
    """
    closed = df[(df['Status Type'] == 'Solved') & (df['Date Closed'].notna())]
    
    print(f"\nClosed/Solved records: {len(closed)}")
    return closed


def calculate_time_to_close(df):
    """
    Calculate time-to-close in days
    """
    df = df.copy()
    df['time_to_close_days'] = (df['Date Closed'] - df['Date Created']).dt.days
    
    # Remove any negative values (data quality issue)
    df = df[df['time_to_close_days'] >= 0]
    
    print(f"Records with valid time-to-close: {len(df)}")
    print(f"Time-to-close range: {df['time_to_close_days'].min()} to {df['time_to_close_days'].max()} days")
    
    return df


def generate_histogram_data(df):
    """
    Generate histogram data for each Service Type
    Shows count distribution across time bins
    """
    # Use Service Level 1 as the primary service type
    df = df[df['Service Level 1'].notna()].copy()
    
    # Bin the time-to-close values
    df['time_bin'] = pd.cut(df['time_to_close_days'], 
                             bins=TIME_BINS, 
                             labels=TIME_LABELS, 
                             right=False)
    
    # Count by Service Type and time bin
    histogram = df.groupby(['Service Level 1', 'time_bin'], observed=True).size().reset_index(name='count')
    
    print(f"\nHistogram data generated with {len(histogram)} rows")
    print(f"Service types: {df['Service Level 1'].nunique()}")
    
    return histogram


def calculate_percentiles(df):
    """
    Calculate median, p75, p90 for each Service Type
    """
    # Use Service Level 1 as the primary service type
    df = df[df['Service Level 1'].notna()].copy()
    
    # Group by Service Type and calculate percentiles
    percentiles = df.groupby('Service Level 1')['time_to_close_days'].agg([
        ('count', 'count'),
        ('median', lambda x: x.median()),
        ('p75', lambda x: x.quantile(0.75)),
        ('p90', lambda x: x.quantile(0.90)),
        ('mean', 'mean'),
        ('min', 'min'),
        ('max', 'max')
    ]).reset_index()
    
    # Round to 1 decimal place
    for col in ['median', 'p75', 'p90', 'mean']:
        percentiles[col] = percentiles[col].round(1)
    
    # Sort by count descending to show most common service types first
    percentiles = percentiles.sort_values('count', ascending=False)
    
    print(f"\nPercentiles calculated for {len(percentiles)} service types")
    print("\nTop 10 Service Types by Volume:")
    print(percentiles.head(10)[['Service Level 1', 'count', 'median', 'p75', 'p90']])
    
    return percentiles


def save_results(histogram, percentiles):
    """
    Save the combined results to a single CSV file
    Merges histogram data with percentiles for each service type
    """
    # Ensure output directory exists
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Merge histogram with percentiles (join on Service Level 1)
    combined = histogram.merge(
        percentiles, 
        on='Service Level 1', 
        how='left',
        suffixes=('', '_total')
    )
    
    # Rename 'count' from histogram to 'bin_count' and 'count_total' to 'total_count'
    combined.rename(columns={
        'count': 'bin_count',
        'count_total': 'total_count'
    }, inplace=True)
    
    # Reorder columns for better readability
    column_order = [
        'Service Level 1', 
        'time_bin', 
        'bin_count',
        'total_count',
        'median', 
        'p75', 
        'p90',
        'mean',
        'min',
        'max'
    ]
    combined = combined[column_order]
    
    # Save combined data
    combined.to_csv(OUTPUT_FILE, index=False)
    print(f"\nCombined data saved to: {OUTPUT_FILE}")
    print(f"Total rows: {len(combined)}")


def main():
    """Main execution flow"""
    print("=" * 60)
    print("Time-to-Close Analysis")
    print("=" * 60)
    
    # Load data
    df = load_data()
    
    # Filter for closed items only
    df_closed = filter_closed_items(df)
    
    # Calculate time-to-close
    df_with_time = calculate_time_to_close(df_closed)
    
    # Generate histogram data
    histogram = generate_histogram_data(df_with_time)
    
    # Calculate percentiles
    percentiles = calculate_percentiles(df_with_time)
    
    # Save results
    save_results(histogram, percentiles)
    
    print("\n" + "=" * 60)
    print("Analysis complete!")
    print("=" * 60)
    
    # Show insights
    print("\nKey Insights:")
    print(f"- Total closed requests analyzed: {len(df_with_time):,}")
    print(f"- Overall median time-to-close: {df_with_time['time_to_close_days'].median():.1f} days")
    print(f"- Overall P90 time-to-close: {df_with_time['time_to_close_days'].quantile(0.90):.1f} days")
    
    # Show service types with biggest median vs p90 gap
    percentiles['gap'] = percentiles['p90'] - percentiles['median']
    top_gaps = percentiles.nlargest(5, 'gap')[['Service Level 1', 'median', 'p90', 'gap']]
    print("\nService Types with Biggest Median vs P90 Gap (showing pain points):")
    print(top_gaps.to_string(index=False))


if __name__ == "__main__":
    main()
