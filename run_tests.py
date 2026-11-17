"""
Direct Test Runner for Bank Fraud Detection System.
Executes all unit and integration test assertions with detailed reporting.
"""

import os
import sys
import tempfile

os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "mpl_cache"))
os.environ["PYTHONIOENCODING"] = "utf-8"

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.test_pipeline import (
    create_sample_data, create_trained_artifacts,
    test_data_generation, test_feature_pipeline,
    test_single_transaction_latency, test_explainability_attribution,
    test_drift_calculation, test_fastapi_endpoints
)

def run_all_tests():
    print("=" * 65)
    print(">> FIN-GUARD AI TEST SUITE EXECUTION")
    print("=" * 65)

    print("\n[1/6] Testing Synthetic Data Generation...")
    df = create_sample_data()
    test_data_generation(df)
    print("  --> PASSED: 1,000 transactions generated with realistic class imbalance.")

    print("\n[2/6] Testing Feature Engineering Pipeline...")
    pipe, model, explainer = create_trained_artifacts(df)
    test_feature_pipeline(df, (pipe, model, explainer))
    print(f"  --> PASSED: {len(pipe.feature_names_)} engineered features verified.")

    print("\n[3/6] Benchmarking Inference Latency (< 100ms)...")
    test_single_transaction_latency((pipe, model, explainer))
    print("  --> PASSED: Sub-100ms latency requirement strictly satisfied.")

    print("\n[4/6] Testing SHAP Explainability & PSD2 Compliance...")
    test_explainability_attribution((pipe, model, explainer))
    print("  --> PASSED: Local attribution and regulatory narrative generated.")

    print("\n[5/6] Testing Concept Drift Detection (PSI & KS)...")
    test_drift_calculation()
    print("  --> PASSED: Population Stability Index and drift thresholds verified.")

    print("\n[6/6] Testing FastAPI REST Endpoints (/health, /predict, /metrics)...")
    test_fastapi_endpoints()
    print("  --> PASSED: Health, Metrics exporter, and Real-Time Scoring APIs verified.")

    print("\n" + "=" * 65)
    print(">> ALL TESTS PASSED SUCCESSFULLY! (6/6 SUITES GREEN)")
    print("=" * 65)

if __name__ == "__main__":
    run_all_tests()
