#!/usr/bin/env python3
"""Test if all dependencies are installed correctly"""

import sys

def test_imports():
    """Test if all Python packages are installed"""
    print("Testing Python packages...")
    
    try:
        import pandas
        print(f"✓ pandas {pandas.__version__}")
    except ImportError:
        print("✗ pandas not installed")
        return False
    
    try:
        import numpy
        print(f"✓ numpy {numpy.__version__}")
    except ImportError:
        print("✗ numpy not installed")
        return False
    
    try:
        import sklearn
        print(f"✓ scikit-learn {sklearn.__version__}")
    except ImportError:
        print("✗ scikit-learn not installed")
        return False
    
    try:
        import xgboost
        print(f"✓ xgboost {xgboost.__version__}")
    except ImportError:
        print("✗ xgboost not installed")
        return False
    
    try:
        import matplotlib
        print(f"✓ matplotlib {matplotlib.__version__}")
    except ImportError:
        print("✗ matplotlib not installed")
        return False
    
    try:
        import git
        print(f"✓ gitpython installed")
    except ImportError:
        print("✗ gitpython not installed")
        return False
    
    return True

def test_database():
    """Test PostgreSQL connection"""
    print("\nTesting PostgreSQL connection...")
    
    try:
        import psycopg2
        conn = psycopg2.connect(
            dbname="perfsense",
            user="postgres",
            password="admin",  # Replace with your password
            host="localhost",
            port="5432"
        )
        print("✓ PostgreSQL connection successful")
        conn.close()
        return True
    except Exception as e:
        print(f"✗ PostgreSQL connection failed: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("PerfSense Setup Test")
    print("="*60)
    
    imports_ok = test_imports()
    db_ok = test_database()
    
    if imports_ok and db_ok:
        print("\n✓ All tests passed! You're ready to start.")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed. Please fix the issues above.")
        sys.exit(1)