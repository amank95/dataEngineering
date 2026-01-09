"""
Verify Drift Monitoring Setup
==============================
Quick script to check if drift monitoring is properly configured.

Usage:
    python verify_drift_setup.py
"""

import os
import sys
from pathlib import Path

def check_file_exists(path: str, description: str) -> tuple[bool, str]:
    """Check if a file exists."""
    exists = os.path.exists(path)
    status = "✓" if exists else "✗"
    return exists, f"{status} {description}: {path}"

def check_env_var(name: str) -> tuple[bool, str]:
    """Check if environment variable is set."""
    from dotenv import load_dotenv
    load_dotenv()
    value = os.getenv(name)
    exists = value is not None and value != ""
    status = "✓" if exists else "✗"
    return exists, f"{status} {name}: {'Set' if exists else 'Not set'}"

def check_table_exists() -> tuple[bool, str]:
    """Check if model_health_alerts table exists in Supabase."""
    try:
        from supabase import create_client
        from dotenv import load_dotenv
        load_dotenv()
        
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            return False, "✗ Supabase credentials not configured"
        
        client = create_client(supabase_url, supabase_key)
        # Try to query the table
        response = client.table('model_health_alerts').select('id').limit(1).execute()
        return True, "✓ model_health_alerts table exists in Supabase"
    except Exception as e:
        return False, f"✗ model_health_alerts table check failed: {str(e)}"

def main():
    print("=" * 70)
    print("DRIFT MONITORING SETUP VERIFICATION")
    print("=" * 70)
    print()
    
    checks = []
    
    # Check files
    print("📁 File Checks:")
    print("-" * 70)
    exists, msg = check_file_exists("drift_monitor.py", "Drift monitor module")
    print(msg)
    checks.append(exists)
    
    exists, msg = check_file_exists("data/processed/baseline_features.parquet", "Baseline file")
    print(msg)
    checks.append(exists)
    
    exists, msg = check_file_exists("data/processed/features_dataset.parquet", "Current features dataset")
    print(msg)
    checks.append(exists)
    
    print()
    
    # Check environment variables
    print("🔐 Environment Variables:")
    print("-" * 70)
    exists, msg = check_env_var("SUPABASE_URL")
    print(msg)
    checks.append(exists)
    
    exists, msg = check_env_var("SUPABASE_KEY")
    print(msg)
    checks.append(exists)
    
    print()
    
    # Check database
    print("🗄️  Database:")
    print("-" * 70)
    exists, msg = check_table_exists()
    print(msg)
    checks.append(exists)
    
    print()
    
    # Check dependencies
    print("📦 Dependencies:")
    print("-" * 70)
    try:
        import scipy
        print(f"✓ scipy: {scipy.__version__}")
        checks.append(True)
    except ImportError:
        print("✗ scipy: Not installed (run: pip install scipy)")
        checks.append(False)
    
    try:
        import pandas
        print(f"✓ pandas: {pandas.__version__}")
        checks.append(True)
    except ImportError:
        print("✗ pandas: Not installed")
        checks.append(False)
    
    try:
        from supabase import create_client
        print("✓ supabase: Installed")
        checks.append(True)
    except ImportError:
        print("✗ supabase: Not installed")
        checks.append(False)
    
    print()
    print("=" * 70)
    
    # Summary
    passed = sum(checks)
    total = len(checks)
    
    if passed == total:
        print(f"✅ ALL CHECKS PASSED ({passed}/{total})")
        print()
        print("Your drift monitoring setup is ready!")
        print()
        print("Next steps:")
        print("  1. If baseline is missing, run: python create_baseline.py")
        print("  2. Run pipeline: python run_all.py --sync")
        print("  3. Check dashboard: streamlit run dashboard.py")
        print("  4. View API: http://127.0.0.1:8000/supabase/model-health")
    else:
        print(f"⚠️  SOME CHECKS FAILED ({passed}/{total})")
        print()
        print("Please fix the issues above before using drift monitoring.")
        print()
        if not os.path.exists("data/processed/baseline_features.parquet"):
            print("💡 TIP: Create baseline with: python create_baseline.py")
        if not os.getenv("SUPABASE_URL"):
            print("💡 TIP: Set SUPABASE_URL and SUPABASE_KEY in .env file")
    
    print("=" * 70)
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())

