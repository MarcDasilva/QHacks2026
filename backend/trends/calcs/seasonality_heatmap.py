import pandas as pd
import numpy as np
from pathlib import Path
from db_utils import load_crm_data_cached

def generate_seasonality_heatmap():
    """
    Generate heatmap data showing average requests per month by service type.
    
    Rows: Service Type (using Service Level 1)
    Columns: Month-of-year (1-12)
    Value: Average requests per month (averaged across all years in dataset)
    
    This helps identify seasonal patterns for staffing and resource allocation.
    """
    
    # Load the CRM service requests data from cache
    df = load_crm_data_cached()
    
    # Convert Date Created to datetime
    df['Date Created'] = pd.to_datetime(df['Date Created'], errors='coerce')
    
    # Extract month and year
    df['Month'] = df['Date Created'].dt.month
    df['Year'] = df['Date Created'].dt.year
    
    # Use Service Level 1 as the primary service type, fallback to Service Type if empty
    df['Service Category'] = df['Service Level 1'].fillna(df['Service Type'])
    
    # Remove rows with missing date or service category
    df = df.dropna(subset=['Month', 'Service Category'])
    
    # Group by Service Category, Year, and Month to count requests
    grouped = df.groupby(['Service Category', 'Year', 'Month']).size().reset_index(name='Request Count')
    
    # Calculate average requests per month across all years for each service type
    # This shows the typical volume for each month regardless of which year
    avg_by_month = grouped.groupby(['Service Category', 'Month'])['Request Count'].mean().reset_index()
    avg_by_month.columns = ['Service Category', 'Month', 'Avg Requests']
    
    # Pivot to create heatmap format: rows = service categories, columns = months
    heatmap_data = avg_by_month.pivot(
        index='Service Category',
        columns='Month',
        values='Avg Requests'
    )
    
    # Fill any missing values with 0 (some service types may not have data for all months)
    heatmap_data = heatmap_data.fillna(0)
    
    # Ensure all 12 months are present as columns
    for month in range(1, 13):
        if month not in heatmap_data.columns:
            heatmap_data[month] = 0
    
    # Sort columns to ensure months are in order
    heatmap_data = heatmap_data[sorted(heatmap_data.columns)]
    
    # Sort rows by total average volume (descending) for better visualization
    heatmap_data['Total'] = heatmap_data.sum(axis=1)
    heatmap_data = heatmap_data.sort_values('Total', ascending=False)
    heatmap_data = heatmap_data.drop('Total', axis=1)
    
    # Add month names as column headers for readability
    month_names = {
        1: 'January', 2: 'February', 3: 'March', 4: 'April',
        5: 'May', 6: 'June', 7: 'July', 8: 'August',
        9: 'September', 10: 'October', 11: 'November', 12: 'December'
    }
    heatmap_data.columns = [month_names[col] for col in heatmap_data.columns]
    
    # Save the heatmap data
    output_path = Path(__file__).parent.parent / "data" / "seasonality_heatmap.csv"
    heatmap_data.to_csv(output_path)
    
    print(f"Seasonality heatmap data saved to: {output_path}")
    print(f"\nShape: {heatmap_data.shape[0]} service types × {heatmap_data.shape[1]} months")
    print(f"\nTop 10 service types by total volume:")
    print(heatmap_data.head(10).round(1))
    
    # Generate summary statistics
    print("\n" + "="*80)
    print("SEASONALITY INSIGHTS:")
    print("="*80)
    
    # Find peak month for each service type
    peak_months = []
    for service in heatmap_data.index[:15]:  # Top 15 services
        peak_month = heatmap_data.loc[service].idxmax()
        peak_value = heatmap_data.loc[service].max()
        low_month = heatmap_data.loc[service].idxmin()
        low_value = heatmap_data.loc[service].min()
        
        if peak_value > 0:  # Only show if there's actual data
            peak_months.append({
                'Service': service,
                'Peak Month': peak_month,
                'Peak Avg': round(peak_value, 1),
                'Low Month': low_month,
                'Low Avg': round(low_value, 1),
                'Seasonality Ratio': round(peak_value / low_value, 2) if low_value > 0 else 'N/A'
            })
    
    peak_df = pd.DataFrame(peak_months)
    print("\nTop service types with seasonal patterns:")
    print(peak_df.to_string(index=False))
    
    return heatmap_data


if __name__ == "__main__":
    heatmap_data = generate_seasonality_heatmap()
