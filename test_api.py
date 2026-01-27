"""
Comprehensive API Testing Script
Tests all endpoints and displays responses in a readable format
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any
import sys
import io

# Set UTF-8 encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# API Configuration
BASE_URL = "http://127.0.0.1:8000"

# Color codes for terminal output (Windows compatible)
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{title.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")

def print_endpoint(method: str, endpoint: str):
    """Print endpoint being tested"""
    print(f"{Colors.OKBLUE}{Colors.BOLD}{method} {endpoint}{Colors.ENDC}")

def print_response(response: requests.Response):
    """Print formatted response"""
    status_color = Colors.OKGREEN if response.status_code == 200 else Colors.FAIL
    print(f"{status_color}Status Code: {response.status_code}{Colors.ENDC}")
    
    try:
        data = response.json()
        print(f"{Colors.OKCYAN}Response:{Colors.ENDC}")
        print(json.dumps(data, indent=2, default=str))
    except:
        print(f"{Colors.WARNING}Response (text):{Colors.ENDC}")
        print(response.text[:500])  # Limit text output
    print(f"{Colors.HEADER}{'-'*80}{Colors.ENDC}")

def test_endpoint(method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """Test a single endpoint and return results"""
    url = f"{BASE_URL}{endpoint}"
    print_endpoint(method, endpoint)
    
    try:
        if method == "GET":
            response = requests.get(url, **kwargs)
        elif method == "POST":
            response = requests.post(url, **kwargs)
        else:
            print(f"{Colors.FAIL}Unsupported method: {method}{Colors.ENDC}")
            return None
        
        print_response(response)
        return {
            "status": "SUCCESS" if response.status_code == 200 else "FAILED",
            "status_code": response.status_code,
            "endpoint": endpoint,
            "method": method
        }
    except requests.exceptions.ConnectionError:
        print(f"{Colors.FAIL}[ERROR] Connection Error: API server is not running!{Colors.ENDC}")
        print(f"{Colors.WARNING}Please start the API with: python run_all.py --start-api{Colors.ENDC}")
        return {
            "status": "CONNECTION_ERROR",
            "endpoint": endpoint,
            "method": method
        }
    except Exception as e:
        print(f"{Colors.FAIL}[ERROR] Error: {str(e)}{Colors.ENDC}")
        return {
            "status": "ERROR",
            "endpoint": endpoint,
            "method": method,
            "error": str(e)
        }

def main():
    """Run all API tests"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}>>> Stock Data Pipeline API - Comprehensive Test Suite{Colors.ENDC}")
    print(f"{Colors.OKCYAN}Testing API at: {BASE_URL}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}")
    
    results = []
    
    # ========================================
    # 1. BASIC ENDPOINTS
    # ========================================
    print_section("1. BASIC ENDPOINTS")
    
    results.append(test_endpoint("GET", "/"))
    results.append(test_endpoint("GET", "/health"))
    
    # ========================================
    # 2. MLOPS ENDPOINTS
    # ========================================
    print_section("2. MLOPS ENDPOINTS")
    
    results.append(test_endpoint("GET", "/api/mlops/system-health"))
    results.append(test_endpoint("GET", "/api/mlops/pipeline-metrics"))
    
    # ========================================
    # 3. DATA QUALITY ENDPOINTS (with ticker)
    # ========================================
    print_section("3. DATA QUALITY ENDPOINTS")
    
    # Test with common tickers
    tickers = ["TCS.NS", "INFY.NS", "RELIANCE.NS"]
    
    for ticker in tickers:
        print(f"\n{Colors.BOLD}Testing with ticker: {ticker}{Colors.ENDC}")
        results.append(test_endpoint("GET", f"/api/mlops/data-quality/{ticker}"))
    
    # ========================================
    # 4. DRIFT DETECTION ENDPOINTS
    # ========================================
    print_section("4. DRIFT DETECTION ENDPOINTS")
    
    for ticker in tickers[:2]:  # Test with first 2 tickers
        print(f"\n{Colors.BOLD}Testing drift detection for: {ticker}{Colors.ENDC}")
        results.append(test_endpoint("GET", f"/api/mlops/drift-detection/{ticker}"))
    
    # ========================================
    # 5. SUPABASE DATA ENDPOINTS
    # ========================================
    print_section("5. SUPABASE DATA ENDPOINTS")
    
    results.append(test_endpoint("GET", "/supabase/latest"))
    results.append(test_endpoint("GET", "/supabase/ticker/TCS.NS"))
    results.append(test_endpoint("GET", "/supabase/recent/TCS.NS?days=7"))
    
    # Test training data endpoint with date range
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    results.append(test_endpoint("GET", f"/supabase/training-data?start_date={start_date}&end_date={end_date}"))
    
    # ========================================
    # 6. PIPELINE CONTROL ENDPOINTS
    # ========================================
    print_section("6. PIPELINE CONTROL ENDPOINTS")
    
    print(f"{Colors.WARNING}[WARN] Skipping POST /run-pipeline (would trigger actual pipeline execution){Colors.ENDC}")
    print(f"{Colors.OKCYAN}To test manually, use: curl -X POST http://127.0.0.1:8000/run-pipeline{Colors.ENDC}")
    
    results.append(test_endpoint("GET", "/fetch-parquet"))
    
    # ========================================
    # SUMMARY
    # ========================================
    print_section("TEST SUMMARY")
    
    total_tests = len(results)
    successful = sum(1 for r in results if r and r.get("status") == "SUCCESS")
    failed = sum(1 for r in results if r and r.get("status") == "FAILED")
    errors = sum(1 for r in results if r and r.get("status") in ["ERROR", "CONNECTION_ERROR"])
    
    print(f"{Colors.BOLD}Total Tests: {total_tests}{Colors.ENDC}")
    print(f"{Colors.OKGREEN}[OK] Successful: {successful}{Colors.ENDC}")
    print(f"{Colors.FAIL}[FAIL] Failed: {failed}{Colors.ENDC}")
    print(f"{Colors.WARNING}[WARN] Errors: {errors}{Colors.ENDC}")
    
    if errors > 0:
        print(f"\n{Colors.WARNING}Note: Some endpoints may fail if data hasn't been generated yet.{Colors.ENDC}")
        print(f"{Colors.OKCYAN}Run 'python run_all.py --sync' to generate data first.{Colors.ENDC}")
    
    print(f"\n{Colors.OKGREEN}{Colors.BOLD}>>> Testing Complete!{Colors.ENDC}\n")
    
    # Return exit code based on results
    return 0 if errors == 0 else 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Test interrupted by user{Colors.ENDC}")
        sys.exit(1)
