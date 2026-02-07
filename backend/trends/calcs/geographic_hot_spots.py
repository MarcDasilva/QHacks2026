"""
Geographic Hot Spots Analysis - Choropleth by Electoral District

Generates data for a choropleth map showing:
- Volume: Total number of service requests
- Unresolved: Count of unresolved/open requests
- Slow p90: 90th percentile of time-to-close (days)

Why it helps: "Where" is often as important as "what" for dispatch and planning.
Identifies districts that need more resources or have systemic issues.

Produces a GEOJSON file with 136,744 features with geographic boundaries and 52,387 features 
with 3 key metrics (volume, unresolved, slow_p90) for each electoral district. Use this for
mapping in JavaScript (Leaflet or MapTiler) by styling features based on the volume, unresolved
or slow_p90 metrics.
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from db_utils import load_crm_data_cached

# Configuration
GEOJSON_FILE = Path(__file__).parent.parent.parent / "CRMServiceRequests_-2988053277932401441.geojson"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "geographic_hot_spots.geojson"
GROUP_BY_COLUMN = "Electoral District"


def load_data():
    """Load the CRM service request data"""
    df = load_crm_data_cached()
    
    print(f"Total records loaded: {len(df)}")
    print(f"Columns: {df.columns.tolist()}")
    
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


def calculate_geographic_metrics(df):
    """
    Calculate geographic metrics by Electoral District
    
    Returns:
    --------
    pd.DataFrame with columns:
        - electoral_district: District name
        - volume: Total number of requests
        - unresolved: Number of unresolved/open requests
        - slow_p90: 90th percentile of time-to-close (days)
    """
    
    print(f"\nCalculating metrics by {GROUP_BY_COLUMN}...")
    
    # Filter out rows with missing district
    df_with_district = df[df[GROUP_BY_COLUMN].notna()].copy()
    
    print(f"Records with valid electoral district: {len(df_with_district)}")
    print(f"Unique electoral districts: {df_with_district[GROUP_BY_COLUMN].nunique()}")
    
    # Calculate metrics by district
    results = []
    
    for district in df_with_district[GROUP_BY_COLUMN].unique():
        district_df = df_with_district[df_with_district[GROUP_BY_COLUMN] == district]
        
        # 1. Volume: total count
        volume = len(district_df)
        
        # 2. Unresolved: count of non-solved requests
        unresolved = len(district_df[district_df['Status Type'] != 'Solved'])
        
        # 3. Slow p90: 90th percentile of time-to-close for solved requests
        solved_district_df = district_df[district_df['Status Type'] == 'Solved'].copy()
        
        if len(solved_district_df) > 0:
            solved_district_df['days_to_close'] = (
                solved_district_df['Date Closed'] - solved_district_df['Date Created']
            ).dt.days
            
            # Remove negative or invalid values
            valid_times = solved_district_df[solved_district_df['days_to_close'] >= 0]['days_to_close']
            
            if len(valid_times) > 0:
                slow_p90 = np.percentile(valid_times, 90)
            else:
                slow_p90 = None
        else:
            slow_p90 = None
        
        results.append({
            'electoral_district': district,
            'volume': volume,
            'unresolved': unresolved,
            'slow_p90': slow_p90
        })
    
    # Create DataFrame
    result_df = pd.DataFrame(results)
    
    # Sort by volume (descending) to show busiest districts first
    result_df = result_df.sort_values('volume', ascending=False)
    
    return result_df


def print_summary(df_geo):
    """Print summary statistics and insights"""
    
    print("\n" + "="*80)
    print("GEOGRAPHIC HOT SPOTS BY ELECTORAL DISTRICT - SUMMARY")
    print("="*80)
    
    print(f"\nTotal electoral districts: {len(df_geo)}")
    print(f"Total volume across all districts: {df_geo['volume'].sum():,.0f}")
    print(f"Total unresolved across all districts: {df_geo['unresolved'].sum():,.0f}")
    
    # Summary statistics
    print(f"\nVolume statistics:")
    print(f"  Mean: {df_geo['volume'].mean():,.1f} requests/district")
    print(f"  Median: {df_geo['volume'].median():,.1f} requests/district")
    print(f"  Max: {df_geo['volume'].max():,.0f} requests (in {df_geo.loc[df_geo['volume'].idxmax(), 'electoral_district']})")
    print(f"  Min: {df_geo['volume'].min():,.0f} requests (in {df_geo.loc[df_geo['volume'].idxmin(), 'electoral_district']})")
    
    print(f"\nUnresolved statistics:")
    print(f"  Mean: {df_geo['unresolved'].mean():,.1f} requests/district")
    print(f"  Median: {df_geo['unresolved'].median():,.1f} requests/district")
    print(f"  Max: {df_geo['unresolved'].max():,.0f} requests (in {df_geo.loc[df_geo['unresolved'].idxmax(), 'electoral_district']})")
    
    # Slow p90 statistics (excluding None values)
    df_with_p90 = df_geo[df_geo['slow_p90'].notna()]
    if len(df_with_p90) > 0:
        print(f"\nSlow P90 statistics:")
        print(f"  Mean: {df_with_p90['slow_p90'].mean():,.1f} days")
        print(f"  Median: {df_with_p90['slow_p90'].median():,.1f} days")
        print(f"  Max: {df_with_p90['slow_p90'].max():,.1f} days (in {df_with_p90.loc[df_with_p90['slow_p90'].idxmax(), 'electoral_district']})")
        print(f"  Min: {df_with_p90['slow_p90'].min():,.1f} days (in {df_with_p90.loc[df_with_p90['slow_p90'].idxmin(), 'electoral_district']})")
    
    # Top 5 districts by volume
    print("\n" + "-"*80)
    print("TOP 5 DISTRICTS BY VOLUME:")
    print("-"*80)
    top_volume = df_geo.head(5)
    for idx, row in top_volume.iterrows():
        p90_str = f"{row['slow_p90']:.1f} days" if pd.notna(row['slow_p90']) else "N/A"
        print(f"{row['electoral_district']:30s} | Vol: {row['volume']:6,.0f} | Unresolved: {row['unresolved']:5,.0f} | P90: {p90_str}")
    
    # Top 5 districts by unresolved count
    print("\n" + "-"*80)
    print("TOP 5 DISTRICTS BY UNRESOLVED COUNT:")
    print("-"*80)
    top_unresolved = df_geo.nlargest(5, 'unresolved')
    for idx, row in top_unresolved.iterrows():
        p90_str = f"{row['slow_p90']:.1f} days" if pd.notna(row['slow_p90']) else "N/A"
        resolution_rate = (row['volume'] - row['unresolved']) / row['volume'] * 100
        print(f"{row['electoral_district']:30s} | Unresolved: {row['unresolved']:5,.0f} | Vol: {row['volume']:6,.0f} | Res: {resolution_rate:5.1f}% | P90: {p90_str}")
    
    # Top 5 districts by slow p90
    df_with_p90 = df_geo[df_geo['slow_p90'].notna()]
    if len(df_with_p90) >= 5:
        print("\n" + "-"*80)
        print("TOP 5 DISTRICTS BY SLOW P90 (slowest resolution time):")
        print("-"*80)
        top_slow = df_with_p90.nlargest(5, 'slow_p90')
        for idx, row in top_slow.iterrows():
            print(f"{row['electoral_district']:30s} | P90: {row['slow_p90']:6.1f} days | Vol: {row['volume']:6,.0f} | Unresolved: {row['unresolved']:5,.0f}")
    
    print("\n" + "="*80)


def create_geojson_output(df_geo):
    """
    Create GeoJSON output by reading the original GeoJSON file and adding metrics
    
    Parameters:
    -----------
    df_geo : pd.DataFrame
        DataFrame with electoral district metrics
    
    Returns:
    --------
    dict : GeoJSON FeatureCollection with metrics added to properties
    """
    print(f"\nReading GeoJSON file: {GEOJSON_FILE}")
    print("This may take a moment for large files...")
    
    # Read the original GeoJSON file
    with open(GEOJSON_FILE, 'r', encoding='utf-8') as f:
        geojson_data = json.load(f)
    
    print(f"GeoJSON loaded: {geojson_data.get('type', 'Unknown')} with {len(geojson_data.get('features', []))} features")
    
    # Create a lookup dictionary from our metrics
    metrics_lookup = df_geo.set_index('electoral_district').to_dict('index')
    
    # Process each feature and add/update metrics
    features_updated = 0
    features_with_district = 0
    
    for feature in geojson_data.get('features', []):
        props = feature.get('properties', {})
        district = props.get('Electoral District') or props.get('electoral_district') or props.get('Electoral_District')
        
        if district:
            features_with_district += 1
            if district in metrics_lookup:
                # Add our calculated metrics to the properties
                metrics = metrics_lookup[district]
                props['volume'] = int(metrics['volume'])
                props['unresolved'] = int(metrics['unresolved'])
                props['slow_p90'] = float(metrics['slow_p90']) if pd.notna(metrics['slow_p90']) else None
                features_updated += 1
    
    print(f"Features with electoral district: {features_with_district}")
    print(f"Features updated with metrics: {features_updated}")
    
    return geojson_data


def main():
    """Main execution function"""
    
    print("="*80)
    print("GEOGRAPHIC HOT SPOTS ANALYSIS - CHOROPLETH BY ELECTORAL DISTRICT")
    print("="*80)
    
    # Load data
    print("\n1. Loading data...")
    df = load_data()
    
    # Calculate geographic metrics
    print("\n2. Calculating geographic metrics...")
    df_geo = calculate_geographic_metrics(df)
    
    # Print summary
    print_summary(df_geo)
    
    # Create GeoJSON output
    print(f"\n3. Creating GeoJSON output...")
    geojson_output = create_geojson_output(df_geo)
    
    # Save to GeoJSON file
    print(f"\n4. Saving results to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(geojson_output, f)
    
    print(f"✓ Success! GeoJSON file created with {len(df_geo)} electoral districts.")
    
    # Show sample of output
    print("\nSample metrics (first 10 districts):")
    print(df_geo.head(10).to_string(index=False))
    
    print("\n" + "="*80)
    print("Analysis complete!")
    print("="*80)
    print(f"\nOutput file: {OUTPUT_FILE}")
    print("\nThis GeoJSON file includes:")
    print("  - Geographic boundaries for each electoral district")
    print("  - volume: Total service request count")
    print("  - unresolved: Count of open/unresolved requests")
    print("  - slow_p90: 90th percentile resolution time (days)")
    print("\nUse this for:")
    print("  - Choropleth map visualization in JavaScript (Leaflet, Mapbox, D3.js)")
    print("  - Resource allocation and dispatch planning")
    print("  - Identifying geographic hot spots needing attention")
    print("="*80)


if __name__ == "__main__":
    main()
