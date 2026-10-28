"""Explicit development build of the audited context-store adapter; never runtime."""

from pathlib import Path
import hashlib, json, platform, subprocess

ROOT = Path(__file__).resolve().parents[1]
assert (platform.system(), platform.machine()) == ("Darwin", "arm64")
source = ROOT / "beyond_ui/_native/menu_context_macos.cpp"
digest = hashlib.sha256(source.read_bytes()).hexdigest()
folder = ROOT / "beyond_ui/_native/macos-arm64"
binary = folder / f"menu-context-{digest[:16]}.dylib"
subprocess.run(
    ["clang++", "-std=c++17", "-dynamiclib", "-O2", str(source), "-o", str(binary)],
    check=True,
)
subprocess.run(["codesign", "--force", "--sign", "-", str(binary)], check=True)
record = dict(
    source_sha256=digest,
    binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
    library=binary.name,
    qualification="Exact menu_native admission required; Darwin arm64 5.1.2/5.2.2 only",
)
(folder / "menu-context.json").write_text(json.dumps(record, indent=2) + "\n")
print(binary)
