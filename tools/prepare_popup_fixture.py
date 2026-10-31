"""Build the disposable add-on used by blender_direct_popups.py."""

import argparse
from pathlib import Path
import shutil
from vendor import vendor


def prepare(destination):
    root = destination / "dialog_addon"
    root.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        Path(__file__).resolve().parents[1] / "tests/dialog_consumer.py",
        root / "__init__.py",
    )
    vendor(root / "_vendor", replace=(root / "_vendor/beyond_ui").exists())
    print(destination.absolute())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    prepare(parser.parse_args().destination)
