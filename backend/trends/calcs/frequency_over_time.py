import pandas as pd
import numpy as np
from datetime import datetime
import os
from db_utils import load_crm_data_cached

# Get the directory of this script
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)

# Read the CRM Service Requests data from cache
df = load_crm_data_cached()

# Convert Date Created to datetime
df['Date Created'] = pd.to_datetime(df['Date Created'])

# Extract year-month for time grouping
df['YearMonth'] = df['Date Created'].dt.to_period('M')

# Get unique Service Level 1 groups
service_level_1_groups = sorted(df['Service Level 1'].unique())

# Group by YearMonth and Service Level 1, count frequency
frequency_data = df.groupby(['YearMonth', 'Service Level 1']).size().reset_index(name='Frequency')

# Pivot to create a wide format with each Service Level 1 as a column
pivot_data = frequency_data.pivot(index='YearMonth', columns='Service Level 1', values='Frequency')

# Fill NaN values with 0 (for months where a service level had no requests)
pivot_data = pivot_data.fillna(0)

# Reset index to make YearMonth a column
pivot_data = pivot_data.reset_index()

# Convert period to string for better CSV compatibility
pivot_data['YearMonth'] = pivot_data['YearMonth'].astype(str)

# Rename the YearMonth column to Time for clarity
pivot_data = pivot_data.rename(columns={'YearMonth': 'Time'})

# Display summary information
print("Frequency Over Time Analysis")
print("=" * 80)
print(f"\nTotal Service Requests: {len(df)}")
print(f"Date Range: {df['Date Created'].min()} to {df['Date Created'].max()}")
print(f"\nNumber of Service Level 1 Groups: {len(service_level_1_groups)}")
print("\nService Level 1 Groups:")
for i, group in enumerate(service_level_1_groups, 1):
    total = df[df['Service Level 1'] == group].shape[0]
    print(f"  {i}. {group}: {total:,} requests")

print(f"\nTime Periods: {len(pivot_data)} months")
print(f"Date Range: {pivot_data['Time'].min()} to {pivot_data['Time'].max()}")

# Save to CSV for visualization
output_file = os.path.join(parent_dir, 'data', 'frequency_over_time.csv')
pivot_data.to_csv(output_file, index=False)
print(f"\n✓ Data exported to: {output_file}")

# Display first few rows
print("\nSample Data (first 5 months):")
print(pivot_data.head())

# Calculate and display statistics for each service level group
print("\n" + "=" * 80)
print("Summary Statistics by Service Level 1 Group")
print("=" * 80)

stats_data = []
for group in service_level_1_groups:
    group_data = pivot_data[group]
    stats_data.append({
        'Service Level 1': group,
        'Mean Frequency': round(group_data.mean(), 2),
        'Min Frequency': int(group_data.min()),
        'Max Frequency': int(group_data.max()),
        'Total Requests': int(group_data.sum())
    })

stats_df = pd.DataFrame(stats_data)
print(stats_df.to_string(index=False))

print("\n" + "=" * 80)
print("Chart Configuration")
print("=" * 80)
print("Chart Type: Line chart")
print("X-axis: Time (monthly)")
print("Y-axis: Frequency (number of requests)")
print(f"Lines: {len(service_level_1_groups)} (one for each Service Level 1 Group)")
print("\nThis data shows the trend and popularity of each service group over time.")
