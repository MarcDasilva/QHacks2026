"""
Data loader utilities for fetching data products
"""

import pandas as pd
import os
from pathlib import Path
from typing import Optional, Dict, Any
from .catalog import DATA_CATALOG, get_product_details


class DataLoader:
    """Handles loading data products from the trends/data folder"""
    
    def __init__(self, data_dir: Optional[str] = None, use_summaries: bool = True):
        if data_dir is None:
            # Default to backend/trends/data relative to this file
            current_dir = Path(__file__).parent
            self.data_dir = current_dir.parent / "trends" / "data"
        else:
            self.data_dir = Path(data_dir)
        
        self.use_summaries = use_summaries
        self.summary_dir = self.data_dir / "summaries"
    
    def load_product(self, product_id: str) -> Optional[pd.DataFrame]:
        """
        Load a data product by its ID
        
        Args:
            product_id: The product identifier from the catalog
            
        Returns:
            DataFrame containing the data, or None if not found
        """
        product_details = get_product_details(product_id)
        
        if not product_details:
            print(f"Product '{product_id}' not found in catalog")
            return None
        
        file_path = self.data_dir / product_details["file"]
        
        if not file_path.exists():
            print(f"Data file not found: {file_path}")
            return None
        
        try:
            # Load the CSV file
            df = pd.read_csv(file_path)
            
            # Apply filter if specified
            if product_details["filter"]:
                # This is a simple string filter - for more complex, use eval carefully
                df = df.query(product_details["filter"])
            
            return df
        
        except Exception as e:
            print(f"Error loading {product_id}: {str(e)}")
            return None
    
    def load_summary(self, product_id: str) -> Optional[str]:
        """
        Load a pre-generated summary for a data product
        
        Args:
            product_id: The product identifier from the catalog
            
        Returns:
            String containing the summary, or None if not found
        """
        if not self.use_summaries:
            return None
        
        summary_file = self.summary_dir / f"{product_id}.txt"
        
        if not summary_file.exists():
            return None
        
        try:
            return summary_file.read_text(encoding='utf-8')
        except Exception as e:
            print(f"Error loading summary for {product_id}: {str(e)}")
            return None
    
    def load_multiple_products(self, product_ids: list) -> Dict[str, pd.DataFrame]:
        """
        Load multiple data products
        
        Args:
            product_ids: List of product identifiers
            
        Returns:
            Dictionary mapping product_id to DataFrame
        """
        results = {}
        
        for product_id in product_ids:
            df = self.load_product(product_id)
            if df is not None:
                results[product_id] = df
        
        return results
    
    def load_multiple_summaries(self, product_ids: list) -> Dict[str, str]:
        """
        Load pre-generated summaries for multiple data products
        Falls back to loading and summarizing data if summary doesn't exist
        
        Args:
            product_ids: List of product identifiers
            
        Returns:
            Dictionary mapping product_id to summary string
        """
        results = {}
        
        for product_id in product_ids:
            # Try to load pre-generated summary first
            summary = self.load_summary(product_id)
            
            if summary is not None:
                results[product_id] = summary
            else:
                # Fall back to loading and summarizing the data
                df = self.load_product(product_id)
                if df is not None:
                    results[product_id] = self.get_data_summary(df)
        
        return results
    
    def get_data_summary(self, df: pd.DataFrame, max_rows: int = 20, from_end: bool = False) -> str:
        """
        Generate a text summary of a DataFrame suitable for LLM consumption
        
        Args:
            df: The DataFrame to summarize
            max_rows: Maximum number of rows to include
            from_end: If True, show last N rows instead of first N (useful for time series)
            
        Returns:
            String representation of the data
        """
        summary = f"Shape: {df.shape[0]} rows × {df.shape[1]} columns\n"
        summary += f"Columns: {', '.join(df.columns.tolist())}\n\n"
        
        # Include first or last N rows
        if len(df) > max_rows:
            if from_end:
                summary += f"Last {max_rows} rows (of {len(df)} total, showing most recent):\n"
                summary += df.tail(max_rows).to_string(index=False)
            else:
                summary += f"First {max_rows} rows (of {len(df)} total):\n"
                summary += df.head(max_rows).to_string(index=False)
        else:
            summary += df.to_string(index=False)
        
        return summary
