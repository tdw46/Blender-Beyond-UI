"""Build the optional panel accelerator with CPython 3.13 x64, Cython and Zig.

Use the same paint.py for the interpreted and compiled implementations. The
release build uses Cython 3.3.1 and ziglang 0.14.1 from the developer venv.
Blender uses public Python GPU/BLF modules and never needs a toolchain.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import sysconfig
import tempfile

ROOT = Path(__file__).resolve().parents[1]
GPU = ROOT / "beyond_ui" / "gpu"


def build():
    if sysconfig.get_platform() != "win-amd64" or sys.version_info[:2] != (3, 13):
        raise SystemExit("Use 64-bit Windows CPython 3.13")
    name = "_win_panel"
    binary = GPU / (name + ".cp313-win_amd64.pyd")
    source = GPU / "paint.py"
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        c_file = target / (name + ".c")
        subprocess.run([sys.executable, "-m", "cython", "-3", "-X",
                        "binding=False,infer_types=True", "--module-name",
                        "beyond_ui.gpu." + name, "-o", str(c_file), str(source)], check=True)
        subprocess.run([sys.executable, "-m", "ziglang", "cc", "-target", "x86_64-windows-gnu",
                        "-O2", "-ffp-contract=off", "-s", "-shared", "-DMS_WIN64", "-D_WIN64",
                        "-I" + sysconfig.get_path("include"), str(c_file),
                        str(Path(sys.base_prefix) / "libs" / "python313.lib"), "-o", binary.name],
                       cwd=target, check=True)
        binary.write_bytes((target / binary.name).read_bytes())
    record = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (source, binary)}
    (GPU / "windows-panel-painter.json").write_text(json.dumps(record, indent=2) + "\n",
                                                    encoding="utf-8", newline="\n")


if __name__ == "__main__":
    build()
