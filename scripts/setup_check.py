"""Verify the local environment required by Resilient-RAG.

The check is deliberately diagnostic: it reports every capability and exits
non-zero only when a required Python dependency or CUDA device is unavailable.
The Ollama desktop service is checked separately because it is not a Python
package and may not be installed in the current environment.
"""

from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str
    required: bool = True


def _module_check(module_name: str) -> CheckResult:
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:  # pragma: no cover - environment-specific branch
        return CheckResult(module_name, False, f"{type(exc).__name__}: {exc}")

    version = getattr(module, "__version__", "installed")
    return CheckResult(module_name, True, str(version))


def _cuda_check() -> CheckResult:
    try:
        import torch
    except Exception as exc:  # pragma: no cover - covered by module check
        return CheckResult("CUDA", False, f"torch unavailable: {exc}")

    if not torch.cuda.is_available():
        return CheckResult("CUDA", False, "torch.cuda.is_available() is False")

    device_name = torch.cuda.get_device_name(0)
    return CheckResult("CUDA", True, device_name)


def _ollama_check() -> CheckResult:
    executable = shutil.which("ollama")
    if executable is None:
        local_app_data = os.environ.get("LOCALAPPDATA")
        installed_path = (
            Path(local_app_data) / "Programs" / "Ollama" / "ollama.exe"
            if local_app_data
            else None
        )
        executable = str(installed_path) if installed_path and installed_path.is_file() else None
    if executable is None:
        return CheckResult(
            "Ollama CLI",
            False,
            "executable not found on PATH",
            required=False,
        )

    completed = subprocess.run(
        [executable, "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    detail = (completed.stdout or completed.stderr).strip()
    return CheckResult("Ollama CLI", completed.returncode == 0, detail, required=False)


def collect_checks() -> list[CheckResult]:
    modules = [
        "numpy",
        "pandas",
        "sklearn",
        "scipy",
        "matplotlib",
        "torch",
        "sentence_transformers",
        "transformers",
        "faiss",
        "ollama",
        "yaml",
        "pytest",
    ]
    checks = [_module_check(module) for module in modules]
    checks.append(_cuda_check())
    checks.append(_ollama_check())
    return checks


def main() -> int:
    print(f"Python: {sys.version.split()[0]}")
    checks = collect_checks()
    for result in checks:
        status = "PASS" if result.ok else "FAIL"
        requirement = "required" if result.required else "optional"
        print(f"[{status}] {result.name} ({requirement}): {result.detail}")

    required_failures = [result for result in checks if result.required and not result.ok]
    if required_failures:
        print(f"Required checks failed: {len(required_failures)}")
        return 1

    print("All required Python and CUDA checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
