"""
Top 10 Rankings for CRM Service Requests

Generates five different top-10 rankings:
1. Top 10 categories by volume (last 30 days)
2. Top 10 by worst P90 time-to-close
3. Top 10 by backlog age (oldest open requests)
4. Top 10 trending up (highest growth rate)
5. Top 10 geographic hotspots (by neighbourhood)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from db_utils import load_crm_data_cached

# Configuration
LAST_N_DAYS = 30
TRENDING_COMPARISON_DAYS = 30  # Compare last 30 vs previous 30


def load_data():
    """Load and preprocess the CRM service request data"""
    print(f"Loading data from cache...")
    df = load_crm_data_cached()  # Uses cache - much faster!
    
    # Convert date columns to datetime if not already
    for col in ['Date Created', 'Date Closed', 'Date Last Updated']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    print(f"Total records loaded: {len(df)}")
    return df


def top_10_by_volume(df, days=LAST_N_DAYS):
    """
    Top 10 categories by volume (last 30 days)
    
    Returns:
    --------
    pd.DataFrame with columns:
        - category: Service Level 1 category
        - volume: Number of requests in last N days
        - pct_of_total: Percentage of total volume
    """
    print(f"\n{'='*60}")
    print(f"Calculating Top 10 Categories by Volume (Last {days} Days)")
    print(f"{'='*60}")
    
    # Get latest date and calculate cutoff
    latest_date = df['Date Created'].max()
    cutoff_date = latest_date - timedelta(days=days)
    
    print(f"Latest date in dataset: {latest_date.date()}")
    print(f"Looking at requests from: {cutoff_date.date()} onwards")
    
    # Filter to recent requests
    recent = df[df['Date Created'] >= cutoff_date].copy()
    
    # Count by Service Level 1
    volume_counts = recent.groupby('Service Level 1').size().reset_index(name='volume')
    
    # Calculate percentage
    total_volume = volume_counts['volume'].sum()
    volume_counts['pct_of_total'] = (volume_counts['volume'] / total_volume * 100).round(2)
    
    # Sort and get top 10
    top_10 = volume_counts.nlargest(10, 'volume').reset_index(drop=True)
    top_10.rename(columns={'Service Level 1': 'category'}, inplace=True)
    
    print(f"\nTotal recent requests: {total_volume}")
    print(f"\nTop 10 Categories by Volume:")
    print(top_10.to_string(index=False))
    
    return top_10


def top_10_by_worst_p90(df, min_requests=10):
    """
    Top 10 categories by worst P90 time-to-close
    
    Parameters:
    -----------
    min_requests : int
        Minimum number of closed requests to include category
    
    Returns:
    --------
    pd.DataFrame with columns:
        - category: Service Level 1 category
        - p90_days: 90th percentile days to close
        - median_days: Median days to close
        - request_count: Number of closed requests
    """
    print(f"\n{'='*60}")
    print(f"Calculating Top 10 Categories by Worst P90 Time-to-Close")
    print(f"{'='*60}")
    
    # Filter to closed requests only
    closed = df[df['Status Type'] == 'Solved'].copy()
    
    # Calculate days to close
    closed['days_to_close'] = (closed['Date Closed'] - closed['Date Created']).dt.days
    
    # Remove negative or invalid values
    closed = closed[closed['days_to_close'] >= 0]
    
    # Group by Service Level 1 and calculate metrics
    stats = closed.groupby('Service Level 1')['days_to_close'].agg([
        ('p90_days', lambda x: np.percentile(x, 90)),
        ('median_days', 'median'),
        ('request_count', 'count')
    ]).reset_index()
    
    # Filter by minimum requests
    stats = stats[stats['request_count'] >= min_requests]
    
    # Round days
    stats['p90_days'] = stats['p90_days'].round(1)
    stats['median_days'] = stats['median_days'].round(1)
    
    # Sort and get top 10 worst
    top_10 = stats.nlargest(10, 'p90_days').reset_index(drop=True)
    top_10.rename(columns={'Service Level 1': 'category'}, inplace=True)
    
    print(f"\nCategories considered (with >= {min_requests} closed requests): {len(stats)}")
    print(f"\nTop 10 Categories by Worst P90:")
    print(top_10.to_string(index=False))
    
    return top_10


def top_10_by_backlog_age(df, min_requests=10):
    """
    Top 10 categories by backlog age (looking at P90 age of all requests)
    
    For open requests: age = current date - created date
    For closed requests: age = closed date - created date
    
    Parameters:
    -----------
    min_requests : int
        Minimum number of requests to include category
    
    Returns:
    --------
    pd.DataFrame with columns:
        - category: Service Level 1 category
        - p90_age_days: 90th percentile age/duration
        - avg_age_days: Average age/duration
        - open_count: Number of currently open requests
        - total_count: Total requests in category
    """
    print(f"\n{'='*60}")
    print(f"Calculating Top 10 Categories by Backlog Age")
    print(f"{'='*60}")
    
    # Calculate age for all requests
    latest_date = df['Date Created'].max()
    print(f"Calculating age as of: {latest_date.date()}")
    
    df_calc = df.copy()
    
    # For open requests, use current date. For closed, use closed date
    df_calc['age_days'] = df_calc.apply(
        lambda row: (latest_date - row['Date Created']).days 
        if row['Status Type'] != 'Solved' 
        else (row['Date Closed'] - row['Date Created']).days,
        axis=1
    )
    
    # Remove negative or invalid values
    df_calc = df_calc[df_calc['age_days'] >= 0]
    
    # Group by Service Level 1 and calculate metrics
    backlog_stats = df_calc.groupby('Service Level 1').agg(
        p90_age_days=('age_days', lambda x: np.percentile(x, 90)),
        avg_age_days=('age_days', 'mean'),
        total_count=('age_days', 'count')
    ).reset_index()
    
    # Also count open requests separately
    open_counts = df[df['Status Type'] != 'Solved'].groupby('Service Level 1').size().reset_index(name='open_count')
    backlog_stats = pd.merge(backlog_stats, open_counts, on='Service Level 1', how='left').fillna(0)
    backlog_stats['open_count'] = backlog_stats['open_count'].astype(int)
    
    # Filter by minimum requests
    backlog_stats = backlog_stats[backlog_stats['total_count'] >= min_requests]
    
    # Round days
    backlog_stats['p90_age_days'] = backlog_stats['p90_age_days'].round(1)
    backlog_stats['avg_age_days'] = backlog_stats['avg_age_days'].round(1)
    
    # Sort and get top 10 by P90 age
    top_10 = backlog_stats.nlargest(10, 'p90_age_days').reset_index(drop=True)
    top_10.rename(columns={'Service Level 1': 'category'}, inplace=True)
    
    print(f"\nCategories considered (with >= {min_requests} requests): {len(backlog_stats)}")
    print(f"\nTop 10 Categories by Backlog Age:")
    print(top_10.to_string(index=False))
    
    return top_10


def top_10_trending_up(df, recent_days=TRENDING_COMPARISON_DAYS, previous_days=TRENDING_COMPARISON_DAYS):
    """
    Top 10 categories trending up (highest growth rate)
    
    Compares volume in last N days vs previous N days
    
    Returns:
    --------
    pd.DataFrame with columns:
        - category: Service Level 1 category
        - recent_volume: Volume in last N days
        - previous_volume: Volume in previous N days
        - growth_rate: Percentage growth
        - absolute_change: Absolute difference
    """
    print(f"\n{'='*60}")
    print(f"Calculating Top 10 Trending Up Categories")
    print(f"{'='*60}")
    
    # Get latest date
    latest_date = df['Date Created'].max()
    recent_cutoff = latest_date - timedelta(days=recent_days)
    previous_cutoff = recent_cutoff - timedelta(days=previous_days)
    
    print(f"Latest date: {latest_date.date()}")
    print(f"Recent period: {recent_cutoff.date()} to {latest_date.date()}")
    print(f"Previous period: {previous_cutoff.date()} to {recent_cutoff.date()}")
    
    # Split into recent and previous periods
    recent = df[df['Date Created'] >= recent_cutoff]
    previous = df[(df['Date Created'] >= previous_cutoff) & (df['Date Created'] < recent_cutoff)]
    
    # Count by Service Level 1
    recent_counts = recent.groupby('Service Level 1').size().reset_index(name='recent_volume')
    previous_counts = previous.groupby('Service Level 1').size().reset_index(name='previous_volume')
    
    # Merge
    trends = pd.merge(recent_counts, previous_counts, on='Service Level 1', how='outer').fillna(0)
    
    # Calculate growth metrics
    trends['absolute_change'] = trends['recent_volume'] - trends['previous_volume']
    
    # Calculate growth rate (avoid division by zero)
    trends['growth_rate'] = trends.apply(
        lambda row: ((row['recent_volume'] - row['previous_volume']) / row['previous_volume'] * 100) 
        if row['previous_volume'] > 0 else (100.0 if row['recent_volume'] > 0 else 0.0),
        axis=1
    )
    
    trends['growth_rate'] = trends['growth_rate'].round(1)
    trends['recent_volume'] = trends['recent_volume'].astype(int)
    trends['previous_volume'] = trends['previous_volume'].astype(int)
    trends['absolute_change'] = trends['absolute_change'].astype(int)
    
    # Filter out categories with very low previous volume (to avoid misleading percentages)
    # and sort by absolute change to find meaningful trends
    trends_filtered = trends[trends['previous_volume'] >= 5].copy()
    
    # Sort by absolute change first, then by growth rate
    top_10 = trends_filtered.nlargest(10, 'absolute_change').reset_index(drop=True)
    top_10.rename(columns={'Service Level 1': 'category'}, inplace=True)
    
    print(f"\nTotal categories analyzed: {len(trends)}")
    print(f"Categories with >= 5 previous requests: {len(trends_filtered)}")
    print(f"\nTop 10 Trending Up Categories:")
    print(top_10.to_string(index=False))
    
    return top_10


def top_10_geographic_hotspots(df, days=LAST_N_DAYS):
    """
    Top 10 geographic hotspots by neighbourhood (last 30 days)
    
    Returns:
    --------
    pd.DataFrame with columns:
        - neighbourhood: Neighbourhood name
        - volume: Number of requests in last N days
        - pct_of_total: Percentage of total volume
        - top_category: Most common Service Level 1 in this neighbourhood
    """
    print(f"\n{'='*60}")
    print(f"Calculating Top 10 Geographic Hotspots (Last {days} Days)")
    print(f"{'='*60}")
    
    # Get latest date and calculate cutoff
    latest_date = df['Date Created'].max()
    cutoff_date = latest_date - timedelta(days=days)
    
    print(f"Looking at requests from: {cutoff_date.date()} onwards")
    
    # Filter to recent requests with valid neighbourhood
    recent = df[(df['Date Created'] >= cutoff_date) & (df['Neighbourhood'].notna())].copy()
    
    # Count by Neighbourhood
    volume_counts = recent.groupby('Neighbourhood').size().reset_index(name='volume')
    
    # Calculate percentage
    total_volume = volume_counts['volume'].sum()
    volume_counts['pct_of_total'] = (volume_counts['volume'] / total_volume * 100).round(2)
    
    # Get top category for each neighbourhood
    top_categories = recent.groupby('Neighbourhood')['Service Level 1'].agg(
        lambda x: x.value_counts().index[0] if len(x) > 0 else 'N/A'
    ).reset_index()
    top_categories.rename(columns={'Service Level 1': 'top_category'}, inplace=True)
    
    # Merge
    hotspots = pd.merge(volume_counts, top_categories, on='Neighbourhood')
    
    # Sort and get top 10
    top_10 = hotspots.nlargest(10, 'volume').reset_index(drop=True)
    top_10.rename(columns={'Neighbourhood': 'neighbourhood'}, inplace=True)
    
    print(f"\nTotal recent requests with neighbourhood: {total_volume}")
    print(f"Unique neighbourhoods: {len(volume_counts)}")
    print(f"\nTop 10 Geographic Hotspots:")
    print(top_10.to_string(index=False))
    
    return top_10


def save_results(data, filename):
    """Save results to CSV file"""
    output_path = Path(__file__).parent.parent / "data" / filename
    data.to_csv(output_path, index=False)
    print(f"\nResults saved to: {output_path}")


def combine_all_rankings(top_volume, top_p90, top_backlog, top_trending, top_geo):
    """
    Combine all top 10 rankings into a single DataFrame
    
    Returns:
    --------
    pd.DataFrame with all rankings combined
    """
    print(f"\n{'='*60}")
    print(f"Combining All Rankings into Single Dataset")
    print(f"{'='*60}")
    
    all_rankings = []
    
    # 1. Volume rankings
    for idx, row in top_volume.iterrows():
        all_rankings.append({
            'ranking_type': 'Volume (Last 30 Days)',
            'rank': idx + 1,
            'category': row['category'],
            'primary_metric': row['volume'],
            'primary_metric_name': 'volume',
            'secondary_metric': row['pct_of_total'],
            'secondary_metric_name': 'pct_of_total',
            'tertiary_metric': None,
            'tertiary_metric_name': None
        })
    
    # 2. P90 rankings
    for idx, row in top_p90.iterrows():
        all_rankings.append({
            'ranking_type': 'Worst P90 Time-to-Close',
            'rank': idx + 1,
            'category': row['category'],
            'primary_metric': row['p90_days'],
            'primary_metric_name': 'p90_days',
            'secondary_metric': row['median_days'],
            'secondary_metric_name': 'median_days',
            'tertiary_metric': row['request_count'],
            'tertiary_metric_name': 'request_count'
        })
    
    # 3. Backlog age rankings
    for idx, row in top_backlog.iterrows():
        all_rankings.append({
            'ranking_type': 'Backlog Age',
            'rank': idx + 1,
            'category': row['category'],
            'primary_metric': row['p90_age_days'],
            'primary_metric_name': 'p90_age_days',
            'secondary_metric': row['avg_age_days'],
            'secondary_metric_name': 'avg_age_days',
            'tertiary_metric': row['open_count'],
            'tertiary_metric_name': 'open_count'
        })
    
    # 4. Trending rankings
    for idx, row in top_trending.iterrows():
        all_rankings.append({
            'ranking_type': 'Trending Up',
            'rank': idx + 1,
            'category': row['category'],
            'primary_metric': row['absolute_change'],
            'primary_metric_name': 'absolute_change',
            'secondary_metric': row['growth_rate'],
            'secondary_metric_name': 'growth_rate',
            'tertiary_metric': row['recent_volume'],
            'tertiary_metric_name': 'recent_volume'
        })
    
    # 5. Geographic hotspots
    for idx, row in top_geo.iterrows():
        all_rankings.append({
            'ranking_type': 'Geographic Hotspots',
            'rank': idx + 1,
            'category': row['neighbourhood'],
            'primary_metric': row['volume'],
            'primary_metric_name': 'volume',
            'secondary_metric': row['pct_of_total'],
            'secondary_metric_name': 'pct_of_total',
            'tertiary_metric': None,
            'tertiary_metric_name': 'top_category: ' + row['top_category']
        })
    
    combined_df = pd.DataFrame(all_rankings)
    
    print(f"\nTotal rankings combined: {len(combined_df)}")
    print(f"Ranking types: {combined_df['ranking_type'].nunique()}")
    
    return combined_df


def main():
    """Run all top 10 calculations and combine into single CSV"""
    print("\n" + "="*60)
    print("TOP 10 RANKINGS - CRM SERVICE REQUESTS")
    print("="*60)
    
    # Load data once
    df = load_data()
    
    # 1. Top 10 by volume (last 30 days)
    top_volume = top_10_by_volume(df)
    
    # 2. Top 10 by worst P90
    top_p90 = top_10_by_worst_p90(df)
    
    # 3. Top 10 by backlog age
    top_backlog = top_10_by_backlog_age(df)
    
    # 4. Top 10 trending up
    top_trending = top_10_trending_up(df)
    
    # 5. Top 10 geographic hotspots
    top_geo = top_10_geographic_hotspots(df)
    
    # Combine all rankings into single CSV
    combined = combine_all_rankings(top_volume, top_p90, top_backlog, top_trending, top_geo)
    save_results(combined, "top10.csv")
    
    print("\n" + "="*60)
    print("ALL TOP 10 RANKINGS COMPLETED")
    print("="*60)
    print("\nOutput file generated:")
    print("  - top10_all_rankings.csv")
    print("\nThis single CSV contains all 5 top-10 rankings:")
    print("  1. Volume (Last 30 Days)")
    print("  2. Worst P90 Time-to-Close")
    print("  3. Backlog Age")
    print("  4. Trending Up")
    print("  5. Geographic Hotspots")


if __name__ == "__main__":
    main()
