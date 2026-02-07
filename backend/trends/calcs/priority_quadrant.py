"""
Priority Quadrant Analysis for CRM Service Requests

Generates data for a priority quadrant scatter/bubble plot:
- X-axis: Volume (request count)
- Y-axis: Time-to-close (median or P90 days - takes 90th percentile of time it takes to close service requests)
- Bubble size: Open count (or last-30-days volume)
- Color: Service Level 1 (or district/channel)

Helps identify systemic problems (high volume + slow) vs special/backlog projects (low volume + very slow)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from db_utils import load_crm_data_cached

# Configuration
GROUP_BY_COLUMN = "Service Level 1"  # Can change to "Electoral District", "Channel", etc.
TIME_METRIC = "p90"  # "median" or "p90"
LAST_N_DAYS = 30  # For recent volume calculation


def load_data():
    """Load and preprocess the CRM service request data"""
    df = load_crm_data_cached()
    
    # Convert date columns to datetime if not already
    for col in ['Date Created', 'Date Closed', 'Date Last Updated']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    return df


def calculate_time_to_close(df):
    """Calculate time to close in days for closed requests"""
    closed_df = df[df['Status Type'] == 'Solved'].copy()
    
    # Calculate days to close
    closed_df['days_to_close'] = (closed_df['Date Closed'] - closed_df['Date Created']).dt.days
    
    # Remove negative or invalid values
    closed_df = closed_df[closed_df['days_to_close'] >= 0]
    
    return closed_df


def calculate_recent_volume(df, days=30):
    """Calculate volume of requests in the last N days"""
    if df['Date Created'].isna().all():
        return df
    
    latest_date = df['Date Created'].max()
    cutoff_date = latest_date - timedelta(days=days)
    
    df['is_recent'] = df['Date Created'] >= cutoff_date
    
    return df


def generate_priority_quadrant_data(
    group_by=GROUP_BY_COLUMN,
    time_metric=TIME_METRIC,
    bubble_metric="recent_volume",
    last_n_days=LAST_N_DAYS
):
    """
    Generate priority quadrant data for visualization
    
    Parameters:
    -----------
    group_by : str
        Column to group by (e.g., "Service Level 1", "Electoral District", "Channel")
    time_metric : str
        "median" or "p90" for time-to-close calculation
    bubble_metric : str
        "open_count" or "recent_volume" for bubble size
    last_n_days : int
        Number of days for recent volume calculation
    
    Returns:
    --------
    pd.DataFrame with columns:
        - group: The grouping category
        - request_count: Total number of requests (X-axis)
        - time_to_close_days: Median or P90 days to close (Y-axis)
        - open_count: Number of currently open requests
        - recent_volume: Volume in last N days
        - bubble_size: The metric to use for bubble size
    """
    
    df = load_data()
    
    print(f"Total records: {len(df)}")
    print(f"Grouping by: {group_by}")
    
    # Filter out rows with missing group values
    df_filtered = df[df[group_by].notna()].copy()
    print(f"Records with valid {group_by}: {len(df_filtered)}")
    
    # Calculate time to close for solved requests
    closed_df = calculate_time_to_close(df_filtered)
    
    # Add recent volume flag
    df_with_recent = calculate_recent_volume(df_filtered, last_n_days)
    
    # Group by the specified column and calculate metrics
    results = []
    
    for group_name in df_filtered[group_by].unique():
        if pd.isna(group_name):
            continue
        
        group_df = df_filtered[df_filtered[group_by] == group_name]
        group_closed_df = closed_df[closed_df[group_by] == group_name]
        
        # Calculate metrics
        request_count = len(group_df)
        
        # Time to close metric
        if len(group_closed_df) > 0 and 'days_to_close' in group_closed_df.columns:
            if time_metric == "p90":
                time_to_close_days = group_closed_df['days_to_close'].quantile(0.90)
            else:  # median
                time_to_close_days = group_closed_df['days_to_close'].median()
        else:
            time_to_close_days = np.nan
        
        # Open count
        open_count = len(group_df[group_df['Status Type'] != 'Solved'])
        
        # Recent volume (last N days)
        recent_volume = group_df['is_recent'].sum() if 'is_recent' in group_df.columns else 0
        
        # Determine bubble size based on selected metric
        if bubble_metric == "recent_volume":
            bubble_size = recent_volume
        else:  # default to open_count
            bubble_size = open_count
        
        results.append({
            'group': group_name,
            'request_count': request_count,
            'time_to_close_days': time_to_close_days,
            'open_count': open_count,
            'recent_volume': recent_volume,
            'bubble_size': bubble_size,
            'closed_count': len(group_closed_df)
        })
    
    result_df = pd.DataFrame(results)
    
    # Sort by request count (descending) for easier analysis
    result_df = result_df.sort_values('request_count', ascending=False)
    
    print(f"\nGenerated data for {len(result_df)} groups")
    
    return result_df


def categorize_priority(df, volume_threshold=None, time_threshold=None):
    """
    Add priority categorization based on volume and time thresholds
    
    Categories:
    - High Priority (Systemic): High volume + High time-to-close
    - Medium Priority: High volume + Low time-to-close OR Low volume + High time-to-close
    - Low Priority: Low volume + Low time-to-close
    """
    
    if volume_threshold is None:
        volume_threshold = df['request_count'].median()
    
    if time_threshold is None:
        time_threshold = df['time_to_close_days'].median()
    
    def assign_priority(row):
        if pd.isna(row['time_to_close_days']):
            return 'Unknown'
        
        high_volume = row['request_count'] >= volume_threshold
        high_time = row['time_to_close_days'] >= time_threshold
        
        if high_volume and high_time:
            return 'High Priority (Systemic)'
        elif high_volume or high_time:
            return 'Medium Priority'
        else:
            return 'Low Priority'
    
    df['priority_category'] = df.apply(assign_priority, axis=1)
    
    return df


def save_results(df, output_file='priority_quadrant_data_p90.csv'):
    """Save the results to a CSV file"""
    output_path = Path(__file__).parent.parent / "data" / output_file
    df.to_csv(output_path, index=False)
    print(f"\nResults saved to: {output_path}")
    return output_path


def print_summary(df):
    """Print a summary of the priority quadrant data"""
    print("\n" + "="*80)
    print("PRIORITY QUADRANT ANALYSIS SUMMARY")
    print("="*80)
    
    print(f"\nMetrics calculated for {len(df)} groups")
    
    print("\n--- TOP 10 BY VOLUME (Request Count) ---")
    top_volume = df.nlargest(10, 'request_count')[
        ['group', 'request_count', 'time_to_close_days', 'open_count']
    ]
    print(top_volume.to_string(index=False))
    
    print("\n--- TOP 10 BY TIME-TO-CLOSE ---")
    top_time = df.nlargest(10, 'time_to_close_days')[
        ['group', 'request_count', 'time_to_close_days', 'open_count']
    ]
    print(top_time.to_string(index=False))
    
    if 'priority_category' in df.columns:
        print("\n--- PRIORITY CATEGORY DISTRIBUTION ---")
        print(df['priority_category'].value_counts())
    
    print("\n--- OVERALL STATISTICS ---")
    print(f"Total requests across all groups: {df['request_count'].sum():,.0f}")
    print(f"Total open requests: {df['open_count'].sum():,.0f}")
    print(f"Median time-to-close: {df['time_to_close_days'].median():.1f} days")
    print(f"Mean time-to-close: {df['time_to_close_days'].mean():.1f} days")
    print(f"Max time-to-close: {df['time_to_close_days'].max():.1f} days")
    
    print("\n" + "="*80)


def main():
    """Main execution function"""
    
    # Generate the priority quadrant data
    df = generate_priority_quadrant_data(
        group_by=GROUP_BY_COLUMN,
        time_metric=TIME_METRIC,
        bubble_metric="open_count",  # or "recent_volume"
        last_n_days=LAST_N_DAYS
    )
    
    # Add priority categorization
    df = categorize_priority(df)
    
    # Print summary
    print_summary(df)
    
    # Save results
    save_results(df)
    
    return df


if __name__ == "__main__":
    # Run the analysis
    result_df = main()
    
    # Optional: Display full dataset
    print("\n\nFULL DATASET:")
    print(result_df.to_string(index=False))
