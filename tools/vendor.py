"""Copy a pinned, self-contained Beyond UI package into an add-on's vendor folder."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MARKER = "vendor-record.json"


def vendor(destination, *, replace=False):
    parent = Path(destination).expanduser().absolute()
    target = parent / "beyond_ui"
    source = (ROOT / "beyond_ui").resolve()
    if target.resolve() == source or source in target.resolve().parents:
        raise ValueError("Destination must be outside the source package")
    parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink():
        raise ValueError("Refusing to replace a symlink")
    if target.exists() and (not replace or not (target / MARKER).is_file()):
        raise ValueError(
            "Destination exists; --replace requires a prior vendor-record.json"
        )
    if target.exists():
        record = json.loads((target / MARKER).read_text())
        if record.get("repository") != "Blender-Beyond-UI":
            raise ValueError("Destination is not a Beyond UI vendor record")
        actual = {
            p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in target.rglob("*")
            if p.is_file()
            and p.name != MARKER
            and "__pycache__" not in p.parts
            and p.suffix not in {".pyc", ".pyo"}
            and p.name != ".DS_Store"
        }
        recorded = {name.replace("\\", "/"): value for name, value in record.get("files", {}).items()}
        if actual != recorded:
            raise ValueError(
                "Vendored files were edited; preserve that copy before updating"
            )
    if target.resolve() == (ROOT / "beyond_ui").resolve():
        raise ValueError("Destination must be outside the source package")
    with tempfile.TemporaryDirectory(prefix=".beyond-ui-", dir=parent) as staging:
        copied = Path(staging) / "beyond_ui"
        shutil.copytree(
            ROOT / "beyond_ui",
            copied,
            ignore=shutil.ignore_patterns(
                "__pycache__", "*.pyc", "*.pyo", ".DS_Store", MARKER
            ),
        )
        files = {
            p.relative_to(copied).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(copied.rglob("*"))
            if p.is_file()
        }
        commit = dirty = None
        try:
            if not (ROOT / ".git").exists():
                raise FileNotFoundError("Source archive has no Git metadata")
            revision = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True
            )
            if revision.returncode == 0:
                commit = revision.stdout.strip()
                status = subprocess.run(
                    ["git", "status", "--porcelain", "--", "beyond_ui"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                )
                dirty = bool(status.stdout) if status.returncode == 0 else None
        except OSError:
            pass  # Source ZIPs still have exact per-file provenance, without Git.
        (copied / MARKER).write_text(
            json.dumps(
                dict(
                    repository="Blender-Beyond-UI",
                    commit=commit,
                    working_tree_changes=dirty,
                    files=files,
                ),
                indent=2,
            )
            + "\n", encoding="utf-8", newline="\n"
        )
        backup = Path(staging) / "previous"
        if target.exists():
            target.rename(backup)
        try:
            copied.rename(target)
        except Exception:
            if backup.exists():
                backup.rename(target)
            raise
    (parent / "__init__.py").touch(exist_ok=True)
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", help="Add-on-local _vendor directory")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace only a previously recorded vendored copy",
    )
    args = parser.parse_args()
    print(vendor(args.destination, replace=args.replace))
