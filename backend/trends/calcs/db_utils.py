"""
Database Utilities for Supabase Connection

Provides shared functions for connecting to Supabase and loading CRM service request data.
"""

import os
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables from .env file
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TABLE_NAME = os.getenv("SUPABASE_TABLE_NAME", "CRMServiceRequests")  # Default table name

# Cache configuration
CACHE_DIR = os.path.join(os.path.dirname(__file__), "../data")
CACHE_FILE = os.path.join(CACHE_DIR, "cached_crm_data.csv")
CACHE_EXPIRY_HOURS = 24  # Refresh cache after 24 hours

def get_supabase_client() -> Client:
    """
    Create and return a Supabase client instance
    
    Returns:
    --------
    Client: Supabase client instance
    
    Raises:
    -------
    ValueError: If SUPABASE_URL or SUPABASE_KEY is not set
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError(
            "Supabase credentials not found. Please set SUPABASE_URL and SUPABASE_KEY "
            "environment variables in your .env file."
        )
    
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def load_crm_data_from_supabase() -> pd.DataFrame:
    """
    Load CRM service request data from Supabase
    
    Returns:
    --------
    pd.DataFrame: DataFrame containing all CRM service request records
    
    Notes:
    ------
    - Automatically handles pagination for large datasets
    - Returns all columns from the table
    """
    print(f"Connecting to Supabase and loading data from '{TABLE_NAME}' table...")
    
    supabase = get_supabase_client()
    
    # Fetch all data from the table
    # Supabase has a default limit, so we need to handle pagination
    all_data = []
    page_size = 1000  # Fetch 1000 records at a time
    offset = 0
    
    while True:
        response = supabase.table(TABLE_NAME).select("*").range(offset, offset + page_size - 1).execute()
        
        if not response.data:
            break
            
        all_data.extend(response.data)
        
        # If we got fewer records than page_size, we've reached the end
        if len(response.data) < page_size:
            break
            
        offset += page_size
        print(f"Loaded {len(all_data)} records...")
    
    print(f"Total records loaded from Supabase: {len(all_data)}")
    
    # Convert to pandas DataFrame
    df = pd.DataFrame(all_data)
    
    return df


def load_crm_data_with_filter(filters: dict = None) -> pd.DataFrame:
    """
    Load CRM service request data from Supabase with optional filters
    
    Parameters:
    -----------
    filters : dict, optional
        Dictionary of column names and values to filter by
        Example: {"Status Type": "Unresolved", "Service Level 1": "Roads"}
    
    Returns:
    --------
    pd.DataFrame: Filtered DataFrame containing CRM service request records
    """
    print(f"Connecting to Supabase and loading filtered data from '{TABLE_NAME}' table...")
    
    supabase = get_supabase_client()
    
    # Start building the query
    query = supabase.table(TABLE_NAME).select("*")
    
    # Apply filters if provided
    if filters:
        for column, value in filters.items():
            query = query.eq(column, value)
    
    # Fetch data with pagination
    all_data = []
    page_size = 1000
    offset = 0
    
    while True:
        response = query.range(offset, offset + page_size - 1).execute()
        
        if not response.data:
            break
            
        all_data.extend(response.data)
        
        if len(response.data) < page_size:
            break
            
        offset += page_size
        print(f"Loaded {len(all_data)} records...")
    
    print(f"Total records loaded from Supabase: {len(all_data)}")
    
    # Convert to pandas DataFrame
    df = pd.DataFrame(all_data)
    
    return df


def load_crm_data_cached(force_refresh=False) -> pd.DataFrame:
    """
    Load CRM service request data with caching support
    
    This function checks for a local cached CSV file and only fetches from Supabase
    if the cache doesn't exist, has expired, or force_refresh is True.
    
    Parameters:
    -----------
    force_refresh : bool, optional
        If True, ignore cache and fetch fresh data from Supabase (default: False)
    
    Returns:
    --------
    pd.DataFrame: DataFrame containing all CRM service request records
    
    Notes:
    ------
    - Cache expires after CACHE_EXPIRY_HOURS (default: 24 hours)
    - Cache is stored in backend/trends/data/cached_crm_data.csv
    - Use force_refresh=True to update cache with latest data
    """
    # Check if cache exists and is fresh
    if not force_refresh and os.path.exists(CACHE_FILE):
        cache_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(CACHE_FILE))
        
        if cache_age < timedelta(hours=CACHE_EXPIRY_HOURS):
            cache_hours = cache_age.total_seconds() / 3600
            print(f"✓ Loading from cache ({CACHE_FILE})")
            print(f"  Cache age: {cache_hours:.1f} hours (expires in {CACHE_EXPIRY_HOURS - cache_hours:.1f} hours)")
            
            df = pd.read_csv(CACHE_FILE)
            print(f"  Loaded {len(df)} records from cache")
            return df
        else:
            print(f"Cache expired (age: {cache_age.total_seconds() / 3600:.1f} hours)")
    
    # Cache miss or expired - fetch from Supabase
    print("Fetching fresh data from Supabase...")
    df = load_crm_data_from_supabase()
    
    # Save to cache
    os.makedirs(CACHE_DIR, exist_ok=True)
    df.to_csv(CACHE_FILE, index=False)
    print(f"✓ Data cached to {CACHE_FILE}")
    print(f"  Next refresh needed after: {datetime.now() + timedelta(hours=CACHE_EXPIRY_HOURS)}")
    
    return df
