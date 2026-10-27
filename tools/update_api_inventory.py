"""Fetch exact versioned official docs; retain member names/signatures, not prose."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess

VERSIONS = ("4.2", "4.3", "4.4", "4.5", "5.0", "5.1", "5.2")
TYPES = ("UILayout", "Panel", "Menu", "UIList", "Header")


class Members(HTMLParser):
    def __init__(self, typename):
        super().__init__()
        self.prefix = "bpy.types." + typename + "."
        self.members = {}
        self.current = None
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        identifier = attrs.get("id", "")
        if tag == "dt" and identifier.startswith(self.prefix):
            self.current = identifier.removeprefix(self.prefix)
            self.parts = []

    def handle_data(self, data):
        if self.current is not None:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "dt" and self.current is not None:
            self.members[self.current] = (
                re.sub(r"\s+", " ", "".join(self.parts)).strip().rstrip("¶#")
            )
            self.current = None


def fetch(task):
    version, typename = task
    url = f"https://docs.blender.org/api/{version}/bpy.types.{typename}.html"
    result = subprocess.run(
        ["curl", "-fsSL", "--retry", "2", "--max-time", "30", url + "?beyond-ui=1"],
        capture_output=True,
        text=True,
        check=True,
    )
    parser = Members(typename)
    parser.feed(result.stdout)
    if not parser.members:
        raise RuntimeError(f"No members found: {url}")
    return version, typename, {"url": url, "members": parser.members}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--versions", nargs="+", default=VERSIONS)
    args = parser.parse_args()
    result = {v: {} for v in args.versions}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for v, t, data in pool.map(
            fetch, ((v, t) for v in args.versions for t in TYPES)
        ):
            result[v][t] = data
            print(v, t, len(data["members"]), flush=True)
    target = Path(__file__).resolve().parents[1] / "docs/api_inventory.json"
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
