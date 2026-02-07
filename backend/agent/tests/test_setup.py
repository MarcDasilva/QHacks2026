"""
Test script to verify the agent setup without making API calls
Tests data loading, catalog, and structure
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))


def test_imports():
    """Test that all modules can be imported"""
    print("🧪 Testing imports...")
    try:
        from agent import CRMAnalyticsAgent, DATA_CATALOG, DataLoader
        from agent.catalog import get_catalog_summary
        print("   ✅ All imports successful")
        return True
    except Exception as e:
        print(f"   ❌ Import error: {e}")
        return False


def test_catalog():
    """Test the data catalog"""
    print("\n🧪 Testing data catalog...")
    try:
        from agent.catalog import DATA_CATALOG, get_catalog_summary
        
        print(f"   ✅ Catalog contains {len(DATA_CATALOG)} products")
        print(f"   Products: {', '.join(list(DATA_CATALOG.keys())[:3])}...")
        
        summary = get_catalog_summary()
        print(f"   ✅ Catalog summary generated ({len(summary)} chars)")
        return True
    except Exception as e:
        print(f"   ❌ Catalog error: {e}")
        return False


def test_data_loader():
    """Test data loading without API"""
    print("\n🧪 Testing data loader...")
    try:
        from agent.data_loader import DataLoader
        
        loader = DataLoader()
        print(f"   ✅ DataLoader initialized")
        print(f"   Data directory: {loader.data_dir}")
        
        # Test loading a product
        df = loader.load_product("frequency_over_time")
        if df is not None:
            print(f"   ✅ Loaded frequency_over_time: {df.shape[0]} rows × {df.shape[1]} cols")
            
            # Test summary generation
            summary = loader.get_data_summary(df, max_rows=5)
            print(f"   ✅ Generated data summary ({len(summary)} chars)")
            return True
        else:
            print("   ⚠️  Could not load frequency_over_time.csv")
            print("   Make sure CSV files exist in backend/trends/data/")
            return False
            
    except Exception as e:
        print(f"   ❌ Data loader error: {e}")
        return False


def test_multiple_products():
    """Test loading multiple products"""
    print("\n🧪 Testing multiple product loading...")
    try:
        from agent.data_loader import DataLoader
        
        loader = DataLoader()
        products = ["top10_volume_30d", "backlog_ranked_list"]
        
        data = loader.load_multiple_products(products)
        print(f"   ✅ Loaded {len(data)}/{len(products)} products")
        
        for product_id, df in data.items():
            print(f"   ✅ {product_id}: {df.shape}")
        
        return len(data) > 0
        
    except Exception as e:
        print(f"   ❌ Multiple product error: {e}")
        return False


def test_file_structure():
    """Verify all data files exist"""
    print("\n🧪 Checking data files...")
    try:
        from agent.catalog import DATA_CATALOG
        from agent.data_loader import DataLoader
        
        loader = DataLoader()
        missing = []
        found = []
        
        for product_id, details in DATA_CATALOG.items():
            file_path = loader.data_dir / details["file"]
            if file_path.exists():
                found.append(details["file"])
            else:
                missing.append(details["file"])
        
        print(f"   ✅ Found {len(found)} data files")
        
        if missing:
            print(f"   ⚠️  Missing {len(missing)} files:")
            for f in missing[:5]:  # Show first 5
                print(f"      - {f}")
        
        return len(missing) == 0
        
    except Exception as e:
        print(f"   ❌ File check error: {e}")
        return False


def main():
    """Run all tests"""
    print("="*60)
    print("CRM Analytics Agent - Setup Verification")
    print("="*60)
    
    tests = [
        ("Imports", test_imports),
        ("Catalog", test_catalog),
        ("Data Loader", test_data_loader),
        ("Multiple Products", test_multiple_products),
        ("File Structure", test_file_structure),
    ]
    
    results = {}
    for name, test_func in tests:
        results[name] = test_func()
    
    # Summary
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    
    passed = sum(results.values())
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Agent is ready to use.")
        print("Next steps:")
        print("  1. Set GEMINI_API_KEY environment variable")
        print("  2. Run: python example.py")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
        print("Common issues:")
        print("  - CSV files missing from backend/trends/data/")
        print("  - Wrong working directory")
        print("  - Missing dependencies (run: pip install -r requirements.txt)")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
