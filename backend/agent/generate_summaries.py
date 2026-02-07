"""
Generate and save data summaries for all catalog products
Summaries are saved as .txt files for faster loading by Gemini
"""

import sys
from pathlib import Path
from datetime import datetime

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from agent.catalog import DATA_CATALOG
from agent.data_loader import DataLoader


def generate_all_summaries(output_dir: str = None, max_rows: int = 50):
    """
    Generate text summaries for all data products and save them
    
    Args:
        output_dir: Directory to save summaries (default: backend/trends/data/summaries)
        max_rows: Maximum rows to include in each summary
    """
    loader = DataLoader()
    
    # Default output directory
    if output_dir is None:
        output_dir = loader.data_dir / "summaries"
    else:
        output_dir = Path(output_dir)
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)
    
    print("="*80)
    print("Generating Data Summaries")
    print("="*80)
    print(f"Output directory: {output_dir}")
    print(f"Max rows per summary: {max_rows}")
    print(f"Total products: {len(DATA_CATALOG)}\n")
    
    successful = 0
    failed = 0
    
    for product_id, details in DATA_CATALOG.items():
        print(f"Processing: {product_id}...")
        
        try:
            # Load the data product
            df = loader.load_product(product_id)
            
            if df is None:
                print(f"  ⚠️  Could not load data")
                failed += 1
                continue
            
            # Generate summary (use last rows for time series like frequency_over_time)
            from_end = product_id in ['frequency_over_time', 'seasonality_heatmap']
            summary = loader.get_data_summary(df, max_rows=max_rows, from_end=from_end)
            
            # Add metadata header
            header = f"""# Data Summary: {product_id}
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Description: {details['description']}
# Source File: {details['file']}
# Filter: {details['filter'] or 'None'}
# Use Cases: {', '.join(details['use_cases'])}
# Metrics: {', '.join(details['metrics'])}
{'='*80}

"""
            
            full_summary = header + summary
            
            # Save to file
            output_file = output_dir / f"{product_id}.txt"
            output_file.write_text(full_summary, encoding='utf-8')
            
            print(f"  ✅ Saved to {output_file.name} ({len(full_summary)} chars, {df.shape[0]} rows)")
            successful += 1
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            failed += 1
    
    print("\n" + "="*80)
    print("Summary Generation Complete")
    print("="*80)
    print(f"✅ Successful: {successful}/{len(DATA_CATALOG)}")
    if failed > 0:
        print(f"❌ Failed: {failed}/{len(DATA_CATALOG)}")
    print(f"\nSummaries saved to: {output_dir}")
    
    return successful, failed


def view_summary(product_id: str):
    """
    Display a saved summary for a product
    
    Args:
        product_id: The product identifier
    """
    loader = DataLoader()
    summary_dir = loader.data_dir / "summaries"
    summary_file = summary_dir / f"{product_id}.txt"
    
    if not summary_file.exists():
        print(f"❌ Summary not found: {summary_file}")
        print(f"Run generate_all_summaries() first")
        return
    
    print("="*80)
    print(f"Summary: {product_id}")
    print("="*80)
    print(summary_file.read_text(encoding='utf-8'))


def list_summaries():
    """List all available summaries"""
    loader = DataLoader()
    summary_dir = loader.data_dir / "summaries"
    
    if not summary_dir.exists():
        print("❌ No summaries directory found")
        print("Run generate_all_summaries() first")
        return
    
    summaries = list(summary_dir.glob("*.txt"))
    
    print("="*80)
    print(f"Available Summaries ({len(summaries)} files)")
    print("="*80)
    
    for i, summary_file in enumerate(sorted(summaries), 1):
        product_id = summary_file.stem
        size = summary_file.stat().st_size
        
        # Check if product is in catalog
        marker = "✅" if product_id in DATA_CATALOG else "⚠️"
        
        print(f"{i:2d}. {marker} {product_id:30s} ({size:,} bytes)")
    
    print(f"\nTotal: {len(summaries)} summaries")


def regenerate_summary(product_id: str, max_rows: int = 50):
    """
    Regenerate a single summary
    
    Args:
        product_id: The product identifier
        max_rows: Maximum rows to include
    """
    if product_id not in DATA_CATALOG:
        print(f"❌ Product '{product_id}' not found in catalog")
        return
    
    loader = DataLoader()
    summary_dir = loader.data_dir / "summaries"
    summary_dir.mkdir(exist_ok=True)
    
    print(f"Regenerating summary for: {product_id}")
    
    try:
        df = loader.load_product(product_id)
        if df is None:
            print(f"  ❌ Could not load data")
            return
        
        # Use last rows for time series data
        from_end = product_id in ['frequency_over_time', 'seasonality_heatmap']
        summary = loader.get_data_summary(df, max_rows=max_rows, from_end=from_end)
        details = DATA_CATALOG[product_id]
        
        header = f"""# Data Summary: {product_id}
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Description: {details['description']}
# Source File: {details['file']}
# Filter: {details['filter'] or 'None'}
# Use Cases: {', '.join(details['use_cases'])}
# Metrics: {', '.join(details['metrics'])}
{'='*80}

"""
        
        full_summary = header + summary
        output_file = summary_dir / f"{product_id}.txt"
        output_file.write_text(full_summary, encoding='utf-8')
        
        print(f"  ✅ Saved to {output_file.name} ({len(full_summary)} chars)")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")


def main():
    """Main function with interactive menu"""
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "generate":
            max_rows = int(sys.argv[2]) if len(sys.argv) > 2 else 50
            generate_all_summaries(max_rows=max_rows)
        
        elif command == "list":
            list_summaries()
        
        elif command == "view":
            if len(sys.argv) < 3:
                print("Usage: python generate_summaries.py view <product_id>")
            else:
                view_summary(sys.argv[2])
        
        elif command == "regenerate":
            if len(sys.argv) < 3:
                print("Usage: python generate_summaries.py regenerate <product_id>")
            else:
                max_rows = int(sys.argv[3]) if len(sys.argv) > 3 else 50
                regenerate_summary(sys.argv[2], max_rows=max_rows)
        
        else:
            print(f"Unknown command: {command}")
            print("Usage: python generate_summaries.py [generate|list|view|regenerate]")
    
    else:
        # Default: generate all summaries
        generate_all_summaries()


if __name__ == "__main__":
    main()
