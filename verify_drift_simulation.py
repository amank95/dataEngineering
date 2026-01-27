"""
Verify Drift Simulation
========================
Simulates a drift scenario to verify detection and alerting logic.
Does NOT require real database connection unless integration features are tested.
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import logging

try:
    from drift_monitor import detect_feature_drift, calculate_psi, calculate_drift_score
except ImportError:
    print("❌ Could not import drift_monitor. Make sure you are in the project root.")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def generate_data(n_samples=1000, mean=0, std=1):
    """Generate synthetic data."""
    return pd.DataFrame({
        "feature_a": np.random.normal(mean, std, n_samples),
        "feature_b": np.random.normal(mean, std, n_samples)
    })

def print_section(title):
    print(f"\n{'-'*50}\n{title}\n{'-'*50}")

def main():
    print_section("Drift Detection Simulation")
    
    # 1. Generate Baseline Data
    logger.info("Generating baseline data (Mean=0, Std=1)...")
    baseline_df = generate_data(n_samples=2000, mean=0, std=1)
    
    # 2. Generate Drifted Data (Mean Shift)
    logger.info("Generating drifted data (Mean=1.0, Std=1.2)...")
    drifted_df = generate_data(n_samples=500, mean=1.0, std=1.2)
    
    # 3. Generate Normal Data (No Drift)
    logger.info("Generating normal data (Mean=0.0, Std=1.0)...")
    normal_df = generate_data(n_samples=500, mean=0.0, std=1.0)
    
    # 4. Test PSI Calculation
    print_section("Testing PSI Calculation")
    
    psi_drift = calculate_psi(
        baseline_df["feature_a"].values, 
        drifted_df["feature_a"].values
    )
    psi_normal = calculate_psi(
        baseline_df["feature_a"].values, 
        normal_df["feature_a"].values
    )
    
    print(f"PSI (Drifted): {psi_drift:.4f} {'(> 0.2, Drift Detected)' if psi_drift > 0.2 else ''}")
    print(f"PSI (Normal):  {psi_normal:.4f} {'(< 0.1, Stable)' if psi_normal < 0.1 else ''}")
    
    if psi_drift > 0.2 and psi_normal < 0.1:
        print("[PASS] PSI Check: PASSED")
    else:
        print("[FAIL] PSI Check: FAILED")
    
    # 5. Test Full Detection Logic
    print_section("Testing Full Detection Logic")
    
    # Test on Drifted Data
    logger.info("Running detection on drifted data...")
    results_drift = detect_feature_drift(
        baseline_df, 
        drifted_df, 
        features=["feature_a", "feature_b"],
        alpha=0.05, 
        psi_threshold=0.2
    )
    
    drift_detected = results_drift["feature_a"]["drift"]
    score = results_drift["feature_a"]["drift_score"]
    
    print(f"\nFeature A (Drifted):")
    print(f"  Drift Detected: {drift_detected}")
    print(f"  Drift Score:    {score:.4f}")
    print(f"  PSI:            {results_drift['feature_a']['psi']:.4f}")
    print(f"  P-Value:        {results_drift['feature_a']['p_value']:.4f}")
    
    if drift_detected and score > 0.5:
        print("[PASS] Detection Check: PASSED")
    else:
        print("[FAIL] Detection Check: FAILED")
        
    # 6. Test on Normal Data
    results_normal = detect_feature_drift(
        baseline_df, 
        normal_df, 
        features=["feature_a"],
        alpha=0.05, 
        psi_threshold=0.2
    )
    
    drift_detected_norm = results_normal["feature_a"]["drift"]
    
    print(f"\nFeature A (Normal):")
    print(f"  Drift Detected: {drift_detected_norm}")
    
    if not drift_detected_norm:
        print("[PASS] False Positive Check: PASSED")
    else:
        print("[FAIL] False Positive Check: FAILED (False Alarm)")

    print_section("Simulation Complete")
    
    if psi_drift > 0.2 and drift_detected and not drift_detected_norm:
       print("[PASS] ALL TESTS PASSED: Logic is sound.")
       return 0
    else:
       print("[FAIL] SOME TESTS FAILED: Check logic.")
       return 1

if __name__ == "__main__":
    sys.exit(main())
