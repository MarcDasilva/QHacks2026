"""
Backlog Ranked List Analysis
Generates data for horizontal bar chart showing unresolved service requests by type
with average age in days.
"""

import pandas as pd
from datetime import datetime
import os
from db_utils import load_crm_data_cached

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)

# Today's date
today = datetime(2026, 2, 7)

# Load the data from cache (or Supabase if cache expired)
print("Loading CRM Service Requests data...")
df = load_crm_data_cached()  # Uses cache - much faster!

print(f"Total records: {len(df)}")
print(f"Status Type distribution:\n{df['Status Type'].value_counts()}\n")

# Filter for unresolved requests only
unresolved_df = df[df['Status Type'] == 'Unresolved'].copy()
print(f"Unresolved records: {len(unresolved_df)}")

# Convert Date Created to datetime
unresolved_df['Date Created'] = pd.to_datetime(unresolved_df['Date Created'])

# Calculate age in days (today - Date Created)
unresolved_df['age_days'] = (today - unresolved_df['Date Created']).dt.days

# Group by Service Level 1 and Service Level 2 for stacked bar chart
backlog_stacked = unresolved_df.groupby(['Service Level 1', 'Service Level 2']).agg(
    unresolved_count=('Service Request ID', 'count'),
    avg_age_days=('age_days', 'mean')
).reset_index()

# Get totals by Service Level 1 for sorting
level1_totals = backlog_stacked.groupby('Service Level 1')['unresolved_count'].sum().sort_values(ascending=False)

# Sort the stacked data by Service Level 1 totals, then by Service Level 2 count within each Level 1
backlog_stacked['level1_total'] = backlog_stacked['Service Level 1'].map(level1_totals)
backlog_stacked = backlog_stacked.sort_values(
    ['level1_total', 'Service Level 1', 'unresolved_count'], 
    ascending=[False, True, False]
).drop('level1_total', axis=1)

print("\n" + "="*80)
print("BACKLOG RANKED LIST - STACKED BAR CHART DATA")
print("Service Level 1 (Main Bars) with Service Level 2 (Stacked Segments)")
print("="*80)
print(f"\n{backlog_stacked.to_string(index=False)}")
print("\n" + "="*80)

# Save to CSV for chart generation
output_file = os.path.join(project_dir, 'data', 'backlog_ranked_list.csv')
backlog_stacked.to_csv(output_file, index=False)
print(f"\nStacked bar chart data saved to: {output_file}")

# Also create a summary by Service Level 1 only
print("\n" + "="*80)
print("SUMMARY BY SERVICE LEVEL 1")
print("="*80)
backlog_level1 = unresolved_df.groupby('Service Level 1').agg(
    unresolved_count=('Service Request ID', 'count'),
    avg_age_days=('age_days', 'mean')
).reset_index()
backlog_level1 = backlog_level1.sort_values('unresolved_count', ascending=False)
print(f"\n{backlog_level1.to_string(index=False)}")

output_file_summary = os.path.join(project_dir, 'data', 'backlog_ranked_list_level1_summary.csv')
backlog_level1.to_csv(output_file_summary, index=False)
print(f"\nSummary data saved to: {output_file_summary}")

# Statistics summary
print("\n" + "="*80)
print("STATISTICS SUMMARY")
print("="*80)
print(f"Total unresolved requests: {backlog_stacked['unresolved_count'].sum()}")
print(f"Number of Service Level 1 categories: {unresolved_df['Service Level 1'].nunique()}")
print(f"Number of Service Level 2 categories: {unresolved_df['Service Level 2'].nunique()}")
print(f"Average age of all unresolved requests: {unresolved_df['age_days'].mean():.1f} days")
print(f"Oldest unresolved request: {unresolved_df['age_days'].max()} days")
print(f"Newest unresolved request: {unresolved_df['age_days'].min()} days")
print("="*80)
