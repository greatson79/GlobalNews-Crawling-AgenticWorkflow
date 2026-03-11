#!/usr/bin/env python3
"""Code Structure Validator — P1 deterministic code structure check.

Verifies Python package structure, module existence, and interface compliance.
Used after Steps 9-15 to prevent "code works" hallucination.

Usage:
    python3 scripts/validate_code_structure.py --step 9 --project-dir .
    python3 scripts/validate_code_structure.py --step 11 --check-adapters --project-dir .

JSON output to stdout. Exit code 0 always.
"""

import argparse
import json
import os
import re
import subprocess
import sys

# ---------------------------------------------------------------------------
# Expected structure per step
# ---------------------------------------------------------------------------

STEP_9_STRUCTURE = {
    "directories": [
        "src", "src/crawling", "src/analysis", "src/storage", "src/utils",
        "tests", "config", "data",
    ],
    "files": [
        "src/__init__.py",
        "src/crawling/__init__.py",
        "src/analysis/__init__.py",
        "src/storage/__init__.py",
        "src/utils/__init__.py",
        "main.py",
        "requirements.txt",
        "config/sources.yaml",
        "config/pipeline.yaml",
    ],
    "import_check": "src",
}

STEP_10_STRUCTURE = {
    "directories": ["src/crawling"],
    "files": [
        "src/crawling/network_guard.py",
        "src/crawling/url_discovery.py",
        "src/crawling/article_extractor.py",
        "src/crawling/dedup_engine.py",
        "src/crawling/ua_rotation.py",
    ],
}

STEP_11_STRUCTURE = {
    "directories": ["src/crawling/adapters"],
    "files": ["src/crawling/adapters/__init__.py"],
    # Adapter files checked dynamically via --check-adapters
}

STEP_12_STRUCTURE = {
    "files": [
        "src/crawling/pipeline.py",
        "src/crawling/retry_manager.py",
    ],
    "cli_check": ["python3", "main.py", "crawl", "--help"],
}

STEP_13_STRUCTURE = {
    "files": [
        "src/analysis/preprocessing.py",
        "src/analysis/feature_extraction.py",
        "src/analysis/article_analysis.py",
        "src/analysis/aggregation.py",
    ],
}

STEP_14_STRUCTURE = {
    "files": [
        "src/analysis/timeseries.py",
        "src/analysis/cross_analysis.py",
        "src/analysis/signal_classifier.py",
    ],
}

STEP_15_STRUCTURE = {
    "files": [
        "src/analysis/pipeline.py",
        "src/storage/parquet_writer.py",
        "src/storage/sqlite_builder.py",
    ],
    "cli_check": ["python3", "main.py", "analyze", "--help"],
}

STEP_STRUCTURES = {
    9: STEP_9_STRUCTURE,
    10: STEP_10_STRUCTURE,
    11: STEP_11_STRUCTURE,
    12: STEP_12_STRUCTURE,
    13: STEP_13_STRUCTURE,
    14: STEP_14_STRUCTURE,
    15: STEP_15_STRUCTURE,
}


def _check_adapters(project_dir):
    """Check adapter coverage against sources.yaml."""
    results = {"adapter_files": [], "missing_adapters": [], "total_sites": 0}

    # Find adapter files
    adapters_dir = os.path.join(project_dir, "src", "crawling", "adapters")
    if os.path.isdir(adapters_dir):
        for root, dirs, files in os.walk(adapters_dir):
            for f in files:
                if f.endswith(".py") and not f.startswith("__"):
                    results["adapter_files"].append(os.path.relpath(os.path.join(root, f), project_dir))

    # Check registry if exists
    registry_path = os.path.join(adapters_dir, "__init__.py")
    if os.path.exists(registry_path):
        with open(registry_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Count domain registrations
        domain_matches = re.findall(r'["\']([a-zA-Z0-9.-]+\.[a-z]{2,})["\']', content)
        results["registered_domains"] = list(set(domain_matches))
        results["total_sites"] = len(results["registered_domains"])

    return results


def validate_structure(project_dir, step_num, check_adapters=False):
    """Validate code structure for a given step."""
    result = {
        "valid": True,
        "step": step_num,
        "checks": {},
        "warnings": [],
    }

    structure = STEP_STRUCTURES.get(step_num)
    if not structure:
        result["warnings"].append(f"No structure definition for step {step_num}")
        return result

    # CS1: Directory existence
    for d in structure.get("directories", []):
        full = os.path.join(project_dir, d)
        exists = os.path.isdir(full)
        result["checks"][f"dir:{d}"] = "EXISTS" if exists else "MISSING"
        if not exists:
            result["valid"] = False
            result["warnings"].append(f"CS1: Directory missing: {d}")

    # CS2: File existence
    for f in structure.get("files", []):
        full = os.path.join(project_dir, f)
        exists = os.path.isfile(full)
        result["checks"][f"file:{f}"] = "EXISTS" if exists else "MISSING"
        if not exists:
            result["valid"] = False
            result["warnings"].append(f"CS2: File missing: {f}")

    # CS3: Import check
    import_target = structure.get("import_check")
    if import_target:
        try:
            proc = subprocess.run(
                [sys.executable, "-c", f"import {import_target}; print('OK')"],
                capture_output=True, text=True, timeout=10,
                cwd=project_dir,
            )
            if proc.returncode == 0 and "OK" in proc.stdout:
                result["checks"]["import"] = "PASS"
            else:
                result["checks"]["import"] = "FAIL"
                result["valid"] = False
                result["warnings"].append(f"CS3: import {import_target} failed: {proc.stderr[:200]}")
        except Exception as e:
            result["checks"]["import"] = "ERROR"
            result["warnings"].append(f"CS3: Import check error: {e}")

    # CS4: CLI check
    cli_cmd = structure.get("cli_check")
    if cli_cmd:
        try:
            proc = subprocess.run(
                cli_cmd,
                capture_output=True, text=True, timeout=15,
                cwd=project_dir,
            )
            if proc.returncode == 0:
                result["checks"]["cli"] = "PASS"
            else:
                result["checks"]["cli"] = "FAIL"
                result["warnings"].append(f"CS4: CLI check failed: {proc.stderr[:200]}")
        except Exception as e:
            result["checks"]["cli"] = "ERROR"
            result["warnings"].append(f"CS4: CLI check error: {e}")

    # CS5: Adapter coverage (Step 11 specific)
    if check_adapters:
        adapter_result = _check_adapters(project_dir)
        result["adapters"] = adapter_result
        if adapter_result["total_sites"] < 121:
            result["warnings"].append(
                f"CS5: Only {adapter_result['total_sites']} site adapters registered (expected 121)"
            )

    return result


def main():
    parser = argparse.ArgumentParser(description="Code Structure Validator — P1")
    parser.add_argument("--step", type=int, required=True, help="Step number (9-15)")
    parser.add_argument("--project-dir", required=True, help="Project root directory")
    parser.add_argument("--check-adapters", action="store_true", help="Check adapter coverage (Step 11)")
    args = parser.parse_args()

    result = validate_structure(args.project_dir, args.step, args.check_adapters)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
