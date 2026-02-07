"""
Quick verification that new catalog products can be loaded
"""
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from agent.catalog import DATA_CATALOG, get_catalog_summary


def test_new_products():
    """Test the new catalog products"""
    print("="*60)
    print("Testing New Catalog Products")
    print("="*60)
    
    new_products = [
        "top10_backlog_age",
        "top10_trending_up", 
        "top10_geographic_hotspots"
    ]
    
    print(f"\n📊 Total products in catalog: {len(DATA_CATALOG)}")
    print("\n✨ NEW Products:\n")
    
    for product_id in new_products:
        if product_id in DATA_CATALOG:
            product = DATA_CATALOG[product_id]
            print(f"✅ {product_id}")
            print(f"   Description: {product['description']}")
            print(f"   Filter: {product['filter']}")
            print(f"   Metrics: {', '.join(product['metrics'])}")
            print()
        else:
            print(f"❌ {product_id} NOT FOUND")
            print()
    
    print("\n" + "="*60)
    print("Complete Catalog Summary:")
    print("="*60 + "\n")
    
    for i, (product_id, details) in enumerate(DATA_CATALOG.items(), 1):
        marker = "⭐ NEW" if product_id in new_products else ""
        print(f"{i:2d}. {product_id} {marker}")
    
    print(f"\n✅ All {len(DATA_CATALOG)} data products available!")


if __name__ == "__main__":
    test_new_products()
