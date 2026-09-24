#!/usr/bin/env python3
"""Create a project-local virtual environment and install CPU dependencies."""
import os
from pathlib import Path
import platform
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]


def main():
    if not (3, 10) <= sys.version_info[:2] <= (3, 12):
        raise SystemExit("Use Python 3.10, 3.11 or 3.12. Python 3.11 is the suggested choice for Intel Macs.")
    target = ROOT / ".venv"
    python = target / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        print(f"Creating {target}", flush=True)
        try:
            venv.EnvBuilder(with_pip=True).create(target)
        except Exception as exc:
            raise SystemExit(f"Could not create virtual environment: {exc}\nOn Ubuntu/Mint install python3-venv, or use an installed Python 3.11/3.12.") from exc
    def pip(*args):
        subprocess.run([str(python), "-m", "pip", "install", *args], cwd=ROOT, check=True)
    pip("--upgrade", "pip")
    intel_mac = platform.system() == "Darwin" and platform.machine().lower() in ("x86_64", "amd64")
    if intel_mac:
        print("Intel macOS: selecting the legacy PyTorch 2.2.2 CPU wheel. This platform has not been tested in the supplied report.", flush=True)
        pip("torch==2.2.2", "numpy==1.26.4")
    elif platform.system() in ("Linux", "Windows"):
        pip("torch==2.6.0", "--index-url", "https://download.pytorch.org/whl/cpu")
    else:
        pip("torch==2.6.0")
    pip("-r", str(ROOT / "requirements.txt"))
    subprocess.run([str(python), "-m", "pip", "check"], check=True)
    print("\nSetup complete. Start with bash run.sh or .\\run.ps1.")
    print("First inference downloads one checkpoint from Hugging Face. Model weights are not in this ZIP.")


if __name__ == "__main__":
    main()
