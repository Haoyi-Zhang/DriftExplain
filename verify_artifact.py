#!/usr/bin/env python3
"""Run the complete finite-artifact verification in an isolated temporary copy."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def run(command: list[str], cwd: Path, env: dict[str, str]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    display_command = ["python", *command[1:]] if command else []
    return {
        "command": " ".join(display_command),
        "exit_status": completed.returncode,
        "output": completed.stdout,
    }


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    source = args.root.resolve()
    output = args.output or (source / "results" / "one_command_verification.json")

    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONHASHSEED"] = "0"

    with tempfile.TemporaryDirectory(prefix="artifact-verify-") as temporary:
        copy_root = Path(temporary) / "artifact"
        shutil.copytree(source, copy_root)
        for path in copy_root.rglob("__pycache__"):
            shutil.rmtree(path)
        for path in copy_root.rglob("*.py[co]"):
            path.unlink()

        steps = [
            ("unit_tests", [sys.executable, "run_tests.py"]),
            ("abstract_model", [sys.executable, "abstract_model_check.py"]),
            ("monotone_core", [sys.executable, "monotone_core_check.py"]),
            ("generated_differential", [sys.executable, "generated_differential_check.py"]),
            ("static_audit", [sys.executable, "audit_static.py", "--root", "."]),
        ]
        executions: dict[str, dict[str, Any]] = {}
        for name, command in steps:
            executions[name] = run(command, copy_root, env)

        deterministic_files = [
            "results/abstract_model_check.json",
            "results/monotone_core_check.json",
            "results/generated_differential_check.json",
        ]
        comparisons: dict[str, bool] = {}
        for relative in deterministic_files:
            comparisons[relative] = (source / relative).read_bytes() == (copy_root / relative).read_bytes()

        audit = load(copy_root / "results" / "static_consistency.json")
        generated = load(copy_root / "results" / "generated_differential_check.json")
        abstract = load(copy_root / "results" / "abstract_model_check.json")
        monotone = load(copy_root / "results" / "monotone_core_check.json")
        residue = sorted(
            str(path.relative_to(copy_root))
            for path in copy_root.rglob("*")
            if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}
        )

        status = (
            all(step["exit_status"] == 0 for step in executions.values())
            and all(comparisons.values())
            and audit.get("summary", {}).get("status") == "PASS"
            and generated.get("status") == "PASS"
            and abstract.get("status") == "PASS"
            and monotone.get("status") == "PASS"
            and not residue
        )
        unit_output = executions["unit_tests"].get("output", "")
        unit_match = re.search(r"Ran\s+(\d+)\s+tests?", unit_output)
        current_unit_tests = int(unit_match.group(1)) if unit_match else None
        status = status and current_unit_tests is not None
        report = {
            "status": "PASS" if status else "FAIL",
            "scope": "isolated-copy unit, finite-check, deterministic-result, static-consistency, and residue verification",
            "executions": {
                name: {
                    "command": value["command"],
                    "exit_status": value["exit_status"],
                }
                for name, value in executions.items()
            },
            "deterministic_result_matches": comparisons,
            "current_unit_tests": current_unit_tests,
            "finite_check_totals": {
                "abstract_endpoint_pairs": abstract.get("totals", {}).get("endpoint_pairs"),
                "abstract_subset_replays": abstract.get("totals", {}).get("subset_replays"),
                "monotone_predicates": monotone.get("totals", {}).get("all_predicates_examined"),
                "monotone_theorem_checks": monotone.get("totals", {}).get("theorem_checks"),
                "generated_endpoint_pairs": generated.get("totals", {}).get("generated_endpoint_pairs"),
                "generated_subset_replays": generated.get("totals", {}).get("subset_replays"),
            },
            "static_audit": audit.get("summary", {}),
            "bytecode_or_cache_residue": residue,
        }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
