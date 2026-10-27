"""Explicit macOS developer build. Never invoked by the runtime."""

import hashlib
import json
from pathlib import Path
import platform
import subprocess
import argparse

ROOT = Path(__file__).resolve().parents[1]
BUILDS = {"d0cbe84903e8": 42, "ec6e62d40fa9": 51, "d13f752e3b9c": 52}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destination", type=Path, default=ROOT / "beyond_ui/_native/macos-arm64"
    )
    args = parser.parse_args()
    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        parser.error(
            "This adapter requires macOS arm64/libc++; Windows source remains unqualified"
        )
    source = ROOT / "beyond_ui/_native/bridge_macos.cpp"
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    target = args.destination / f"bridge-{sha[:16]}.dylib"
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["clang++", "-std=c++17", "-dynamiclib", "-O2", str(source), "-o", str(target)],
        check=True,
    )
    subprocess.run(["codesign", "--force", "--sign", "-", str(target)], check=True)
    manifest = {
        "platform": "Darwin",
        "machine": "arm64",
        "builds": BUILDS,
        "library": target.name,
        "source_sha256": sha,
        "binary_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "abi": "beyond-ui-extra-v1",
        "qualification": "experimental; see docs/VALIDATION.md",
    }
    (target.parent / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(target)


if __name__ == "__main__":
    main()
