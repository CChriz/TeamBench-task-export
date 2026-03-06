#!/usr/bin/env python3
"""Launch cross-model ablation for a single model.

Usage:
    python scripts/run_crossmodel.py --model gpt-5-nano
"""
import argparse
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TASKS = [
    "MULTI1_fullstack_fix", "TEST1_spec_to_tests", "O2_incident_rootcause",
    "PIPE1_etl_fix", "TRAP1_spec_conflict", "TRAP3_metric_mirage",
    "TRAP5_security_theater", "CROSS1_api_contract", "CROSS3_protocol_bridge",
    "CRYPTO1_nonce_reuse", "DIST1_queue_race", "SEC1_vuln_patch",
    "SEC3_crypto_upgrade", "D1_schema_drift", "D8_csv_cleanup",
    "TEST2_regression", "TEST5_mutation_resistant", "O1_service_health",
    "O3_log_analysis", "P1_policy_config", "P3_access_control",
    "SPEC1_feature_impl", "SPEC3_data_model", "INC1_cascade_failure",
    "INC4_dns_miscfg", "IR1_evidence_qa", "NEG1_tradeoff_config",
    "CR5_test_coverage",
]

CONDITIONS = ["oracle", "restricted", "team_no_verify", "team_no_plan", "full"]

MODEL_TO_FILE = {
    "gpt-5-nano": "crossmodel_gpt5nano_seed0.json",
    "gpt-5-mini": "crossmodel_gpt5mini_seed0.json",
    "gemini-3.1-flash-lite-preview": "crossmodel_g31lite_seed0.json",
    "gemini-3-flash-preview": "crossmodel_g3flash_seed0.json",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--seeds", nargs="+", type=int, default=[0])
    args = ap.parse_args()

    fname = MODEL_TO_FILE.get(args.model, f"crossmodel_{args.model.replace('-','')}_seed0.json")
    outpath = os.path.join("shared", "ablation_results", fname)

    from harness.ablation import run_full_ablation, AblationCondition
    conds = [AblationCondition(c) for c in CONDITIONS]
    run_full_ablation(
        model=args.model,
        tasks=TASKS,
        seeds=args.seeds,
        tasks_dir="tasks",
        output=outpath,
        conditions=conds,
    )


if __name__ == "__main__":
    main()
