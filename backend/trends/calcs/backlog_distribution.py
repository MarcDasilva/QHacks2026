"""
Backlog Distribution Histogram

Generates data for a histogram (or stacked histogram by Service Level 1) showing:
- X-axis: age_days of unresolved (or open) items
- Y-axis: count

This visualization helps identify:
- "Long tail" of ancient tickets (indicates process problem)
- vs. mostly recent ones (normal flow)
- Which service categories have the oldest backlogs
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
from db_utils import load_crm_data_cached

# Configuration
OUTPUT_FILE_STACKED = Path(__file__).parent.parent / "data" / "backlog_distribution.csv"
OUTPUT_FILE_SUMMARY = Path(__file__).parent.parent / "data" / "backlog_distribution_level1_summary.csv"

# Age bins for histogram (in days)
AGE_BINS = [0, 7, 14, 30, 60, 90, 180, 365, 730, float('inf')]
AGE_LABELS = ['0-7 days', '8-14 days', '15-30 days', '31-60 days', 
              '61-90 days', '91-180 days', '181-365 days', '1-2 years', '2+ years']


def load_data():
    """Load the CRM service request data"""
    df = load_crm_data_cached()
    
    # Convert date columns to datetime
    df['Date Created'] = pd.to_datetime(df['Date Created'], errors='coerce')
    df['Date Closed'] = pd.to_datetime(df['Date Closed'], errors='coerce')
    
    print(f"Total records loaded: {len(df)}")
    print(f"Columns: {df.columns.tolist()}")
    
    return df


def filter_unresolved_items(df):
    """
    Filter for unresolved/open items
    Unresolved = Status Type is not 'Solved' or Date Closed is NaT (not closed)
    """
    # Items that are not solved OR don't have a close date
    unresolved = df[(df['Status Type'] != 'Solved') | (df['Date Closed'].isna())]
    
    print(f"\nTotal unresolved items: {len(unresolved)}")
    print(f"Status types in unresolved: {unresolved['Status Type'].value_counts().to_dict()}")
    
    return unresolved


def calculate_age_days(df, reference_date=None):
    """
    Calculate age in days from Date Created to reference_date (default: today)
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with 'Date Created' column
    reference_date : datetime, optional
        Date to calculate age from (default: current date)
    
    Returns:
    --------
    pd.Series with age in days
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    age_days = (reference_date - df['Date Created']).dt.days
    
    print(f"\nAge statistics:")
    print(f"  Min age: {age_days.min()} days")
    print(f"  Max age: {age_days.max()} days")
    print(f"  Mean age: {age_days.mean():.1f} days")
    print(f"  Median age: {age_days.median():.1f} days")
    
    return age_days


def create_histogram_bins(age_days, bins=AGE_BINS, labels=AGE_LABELS):
    """
    Create histogram bins for age distribution
    
    Parameters:
    -----------
    age_days : pd.Series
        Series with age in days
    bins : list
        List of bin edges
    labels : list
        List of bin labels
    
    Returns:
    --------
    pd.Series with bin labels
    """
    age_bins = pd.cut(age_days, bins=bins, labels=labels, right=False)
    return age_bins


def generate_stacked_histogram_data(df):
    """
    Generate data for stacked histogram by Service Level 1
    
    Returns:
    --------
    pd.DataFrame with columns:
        - age_bin: Age range label
        - service_level_1: Service category
        - count: Number of items in this bin and category
    """
    # Filter unresolved items
    unresolved = filter_unresolved_items(df)
    
    # Calculate age
    unresolved['age_days'] = calculate_age_days(unresolved)
    
    # Create age bins
    unresolved['age_bin'] = create_histogram_bins(unresolved['age_days'])
    
    # Group by age bin and Service Level 1
    stacked_data = unresolved.groupby(['age_bin', 'Service Level 1'], 
                                       observed=True).size().reset_index(name='count')
    
    # Sort by age bin order
    stacked_data['age_bin'] = pd.Categorical(stacked_data['age_bin'], 
                                              categories=AGE_LABELS, 
                                              ordered=True)
    stacked_data = stacked_data.sort_values(['age_bin', 'count'], 
                                             ascending=[True, False])
    
    print(f"\nGenerated stacked histogram data with {len(stacked_data)} rows")
    print(f"Age bins: {stacked_data['age_bin'].unique().tolist()}")
    print(f"Service Level 1 categories: {stacked_data['Service Level 1'].nunique()}")
    
    return stacked_data


def generate_summary_by_level1(df):
    """
    Generate summary statistics by Service Level 1 for supplementary analysis
    
    Returns:
    --------
    pd.DataFrame with columns:
        - service_level_1: Service category
        - total_unresolved: Total unresolved items
        - avg_age_days: Average age in days
        - median_age_days: Median age in days
        - max_age_days: Maximum age in days
        - pct_over_90_days: Percentage of items over 90 days old
    """
    # Filter unresolved items
    unresolved = filter_unresolved_items(df)
    
    # Calculate age
    unresolved['age_days'] = calculate_age_days(unresolved)
    
    # Group by Service Level 1 and calculate statistics
    summary = unresolved.groupby('Service Level 1').agg(
        total_unresolved=('age_days', 'count'),
        avg_age_days=('age_days', 'mean'),
        median_age_days=('age_days', 'median'),
        max_age_days=('age_days', 'max'),
        over_90_days=('age_days', lambda x: (x > 90).sum())
    ).reset_index()
    
    # Calculate percentage over 90 days
    summary['pct_over_90_days'] = (summary['over_90_days'] / summary['total_unresolved'] * 100).round(2)
    
    # Round age columns
    summary['avg_age_days'] = summary['avg_age_days'].round(1)
    summary['median_age_days'] = summary['median_age_days'].round(1)
    
    # Sort by total unresolved descending
    summary = summary.sort_values('total_unresolved', ascending=False)
    
    print(f"\nGenerated summary for {len(summary)} Service Level 1 categories")
    
    return summary


def main():
    """Main execution function"""
    print("=" * 70)
    print("BACKLOG DISTRIBUTION ANALYSIS")
    print("=" * 70)
    
    # Load data
    df = load_data()
    
    # Generate stacked histogram data
    print("\n" + "-" * 70)
    print("GENERATING STACKED HISTOGRAM DATA")
    print("-" * 70)
    stacked_data = generate_stacked_histogram_data(df)
    
    # Save stacked histogram data
    stacked_data.to_csv(OUTPUT_FILE_STACKED, index=False)
    print(f"\n✓ Saved stacked histogram data to: {OUTPUT_FILE_STACKED}")
    print(f"  Sample rows:")
    print(stacked_data.head(10).to_string(index=False))
    
    # Generate summary by Service Level 1
    print("\n" + "-" * 70)
    print("GENERATING SERVICE LEVEL 1 SUMMARY")
    print("-" * 70)
    summary = generate_summary_by_level1(df)
    
    # Save summary
    summary.to_csv(OUTPUT_FILE_SUMMARY, index=False)
    print(f"\n✓ Saved Service Level 1 summary to: {OUTPUT_FILE_SUMMARY}")
    print(f"  Sample rows:")
    print(summary.head(10).to_string(index=False))
    
    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
