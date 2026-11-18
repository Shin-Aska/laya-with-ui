#!/usr/bin/env python3
"""Create a project-local virtual environment and install CPU dependencies."""
import argparse
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]


def _marker_matches(marker: str) -> bool:
    marker = marker.strip()
    if not marker:
        return True
    cur = sys.version_info[:2]
    if marker == 'python_version < "3.13"' or marker == "python_version < '3.13'":
        return cur < (3, 13)
    if marker == 'python_version >= "3.13"' or marker == "python_version >= '3.13'":
        return cur >= (3, 13)
    raise ValueError(f"Unsupported environment marker in requirements.txt: {marker}")


def venv_matches_python(python: Path) -> bool:
    if not python.exists():
        return False
    expected = f"{sys.version_info.major}.{sys.version_info.minor}"
    res = subprocess.run(
        [str(python), "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
        capture_output=True,
        text=True,
    )
    return res.returncode == 0 and res.stdout.strip() == expected


def is_ready(python: Path, expected_torch: str, require_cpu_tag: bool) -> bool:
    if not venv_matches_python(python):
        return False
    reqs = []
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        spec, _, marker = line.partition(";")
        if not _marker_matches(marker):
            continue
        if "==" not in spec:
            continue
        name, ver = spec.split("==", 1)
        reqs.append((name.strip(), ver.strip()))
    check_code = (
        "import importlib.metadata as m, sys; "
        "require_cpu = sys.argv[1] == '1'; "
        "expected_torch = sys.argv[2]; "
        "tv = m.version('torch'); "
        "torch_ok = (tv == expected_torch) if require_cpu else (tv.split('+', 1)[0] == expected_torch); "
        "pairs = [p.split('==', 1) for p in sys.argv[3:]]; "
        "reqs_ok = all(m.version(n).split('+', 1)[0] == v for n, v in pairs); "
        "sys.exit(0 if (torch_ok and reqs_ok) else 1)"
    )
    args = ["1" if require_cpu_tag else "0", expected_torch, *(f"{n}=={v}" for n, v in reqs)]
    if subprocess.run([str(python), "-c", check_code, *args], capture_output=True).returncode != 0:
        return False
    return subprocess.run([str(python), "-m", "pip", "check"], capture_output=True).returncode == 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Reinstall packages even if already present")
    args = parser.parse_args()

    intel_mac = platform.system() == "Darwin" and platform.machine().lower() in ("x86_64", "amd64")
    if intel_mac and sys.version_info[:2] > (3, 12):
        raise SystemExit("Intel macOS supports Python 3.10–3.12 only (PyTorch 2.2.2 legacy wheel).")
    if not (3, 10) <= sys.version_info[:2] <= (3, 14):
        raise SystemExit("Use Python 3.10–3.14. On Windows, Python 3.14 is required.")
    target = ROOT / ".venv"
    python = target / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    cpu_index_os = platform.system() in ("Linux", "Windows")
    torch_base = "2.2.2" if intel_mac else ("2.15.0" if sys.version_info[:2] >= (3, 13) else "2.6.0")
    expected_torch = torch_base if (intel_mac or not cpu_index_os) else f"{torch_base}+cpu"

    if not args.force and os.environ.get("LAYA_REINSTALL") != "1" and is_ready(python, expected_torch, cpu_index_os):
        print("Backend virtual environment is already set up. Skipping reinstall (pass --force to reinstall).", flush=True)
        return

    if target.exists() and not venv_matches_python(python):
        print(f"Recreating {target} for Python {sys.version_info.major}.{sys.version_info.minor}", flush=True)
        shutil.rmtree(target)

    if not python.exists():
        print(f"Creating {target}", flush=True)
        try:
            venv.EnvBuilder(with_pip=True).create(target)
        except Exception as exc:
            raise SystemExit(f"Could not create virtual environment: {exc}\nOn Ubuntu/Mint install python3-venv, or use an installed Python 3.10–3.14.") from exc
    def pip(*pip_args):
        subprocess.run([str(python), "-m", "pip", "install", *pip_args], cwd=ROOT, check=True)
    pip("--upgrade", "pip")
    if intel_mac:
        print("Intel macOS: selecting the legacy PyTorch 2.2.2 CPU wheel. This platform has not been tested in the supplied report.", flush=True)
        pip("--force-reinstall", "--no-deps", "torch==2.2.2")
        pip("numpy==1.26.4")
    elif cpu_index_os:
        # Force-reinstall torch so any existing CUDA wheel (+cu*) is replaced by +cpu.
        pip("--force-reinstall", "--no-deps", f"torch=={torch_base}", "--index-url", "https://download.pytorch.org/whl/cpu")
        pip(f"torch=={torch_base}", "--index-url", "https://download.pytorch.org/whl/cpu")
    else:
        pip("--force-reinstall", "--no-deps", f"torch=={torch_base}")
    pip("-r", str(ROOT / "requirements.txt"))
    subprocess.run([str(python), "-m", "pip", "check"], check=True)
    print("\nSetup complete. Start with bash run.sh or .\\run.ps1.")
    print("First inference downloads one checkpoint from Hugging Face. Model weights are not in this ZIP.")


if __name__ == "__main__":
    main()
