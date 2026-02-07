"""  
First Call Resolution (FCR) Rate Analysis

Generates data for a bar chart showing FCR rate by service category:
- Y-axis: Service Level 1
- X-axis: FCR rate (% of requests resolved on first call)
- Shows all 16 Service Level 1 categories

Identifies "confusing" or "complex" categories that create more work per request
and may deserve process fixes or better UI prompts. Also highlights "quick fixes"
with high FCR rates.
"""

import pandas as pd
from pathlib import Path
from db_utils import load_crm_data_cached

# Configuration
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "fcr_by_category.csv"
GROUP_BY_COLUMN = "Service Level 1"  # Can also use "Service Type"
MIN_VOLUME = 0  # No minimum volume filter - show all categories


def load_data():
    """Load the CRM service request data"""
    df = load_crm_data_cached()
    
    print(f"Total records loaded: {len(df)}")
    print(f"Columns: {df.columns.tolist()}")
    
    return df


def calculate_fcr_rate(df, group_by=GROUP_BY_COLUMN, min_volume=MIN_VOLUME):
    """
    Calculate First Call Resolution rate by category
    
    Parameters:
    -----------
    df : pd.DataFrame
        The CRM service request data
    group_by : str
        Column to group by (e.g., "Service Level 2", "Service Type")
    min_volume : int
        Minimum number of requests for a category to be included
    
    Returns:
    --------
    pd.DataFrame with columns:
        - category: The service category
        - total_requests: Total number of requests
        - fcr_yes: Number of requests with FCR = Yes
        - fcr_no: Number of requests with FCR = No
        - fcr_rate: Percentage of requests resolved on first call (0-100)
    """
    
    print(f"\nGrouping by: {group_by}")
    
    # Filter out rows with missing category or FCR values
    df_clean = df[[group_by, 'First call resolution']].dropna()
    
    print(f"Records with valid category and FCR data: {len(df_clean)}")
    
    # Group by category and count FCR responses
    fcr_stats = df_clean.groupby([group_by, 'First call resolution']).size().unstack(fill_value=0)
    
    # Ensure both Yes and No columns exist
    if 'Yes' not in fcr_stats.columns:
        fcr_stats['Yes'] = 0
    if 'No' not in fcr_stats.columns:
        fcr_stats['No'] = 0
    
    # Calculate totals and rates
    result = pd.DataFrame({
        'category': fcr_stats.index,
        'fcr_yes': fcr_stats['Yes'].values,
        'fcr_no': fcr_stats['No'].values,
    })
    
    result['total_requests'] = result['fcr_yes'] + result['fcr_no']
    result['fcr_rate'] = (result['fcr_yes'] / result['total_requests'] * 100).round(2)
    
    # Filter by minimum volume (if specified)
    if min_volume > 0:
        result = result[result['total_requests'] >= min_volume].copy()
        print(f"\nCategories meeting minimum volume threshold ({min_volume}): {len(result)}")
    else:
        print(f"\nAll categories (no volume filter): {len(result)}")
    
    # Sort by FCR rate (ascending) to show problematic categories first
    result = result.sort_values('fcr_rate', ascending=True)
    
    return result


def print_summary(df_fcr):
    """Print summary statistics and insights"""
    
    print("\n" + "="*80)
    print("FIRST CALL RESOLUTION RATE BY CATEGORY - SUMMARY")
    print("="*80)
    
    print(f"\nTotal categories analyzed: {len(df_fcr)}")
    print(f"Total requests covered: {df_fcr['total_requests'].sum():,}")
    
    print("\n--- LOWEST FCR RATES (Most Complex/Confusing) ---")
    print(df_fcr.head(10).to_string(index=False))
    
    print("\n--- HIGHEST FCR RATES (Quick Fixes) ---")
    print(df_fcr.tail(10).to_string(index=False))
    
    # Calculate overall FCR rate
    overall_fcr = (df_fcr['fcr_yes'].sum() / df_fcr['total_requests'].sum() * 100)
    print(f"\nOverall FCR Rate: {overall_fcr:.2f}%")
    
    # Identify categories below average
    low_fcr = df_fcr[df_fcr['fcr_rate'] < overall_fcr]
    print(f"\nCategories below average FCR: {len(low_fcr)} ({len(low_fcr)/len(df_fcr)*100:.1f}%)")
    print(f"Requests in below-average categories: {low_fcr['total_requests'].sum():,} "
          f"({low_fcr['total_requests'].sum()/df_fcr['total_requests'].sum()*100:.1f}%)")


def main():
    """Main execution function"""
    
    print("="*80)
    print("FIRST CALL RESOLUTION RATE ANALYSIS")
    print("="*80)
    
    # Load data
    df = load_data()
    
    # Calculate FCR rates
    df_fcr = calculate_fcr_rate(df, group_by=GROUP_BY_COLUMN, min_volume=MIN_VOLUME)
    
    # Print summary
    print_summary(df_fcr)
    
    # Save to CSV
    df_fcr.to_csv(OUTPUT_FILE, index=False)
    print(f"\n✓ Data saved to: {OUTPUT_FILE}")
    print(f"  Columns: {df_fcr.columns.tolist()}")
    print(f"  Rows: {len(df_fcr)}")
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    
    return df_fcr


if __name__ == "__main__":
    main()
