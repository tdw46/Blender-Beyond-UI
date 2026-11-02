"""Pin a signing-only Windows executable variant without changing native RVAs.

Developer-only: the reference must match the already pinned executable hash.
All bytes except the PE checksum and trailing WIN_CERTIFICATE table must match.
Runtime admission continues checking complete SHA-256 fingerprints.
"""

import argparse
import hashlib
import json
from pathlib import Path
import struct


def sha(data):
    return hashlib.sha256(data).hexdigest()


def signing_independent_image(data):
    if len(data) < 64 or data[:2] != b"MZ":
        raise ValueError("Not a PE image")
    try:
        pe = struct.unpack_from("<I", data, 60)[0]
        if data[pe:pe + 4] != b"PE\0\0":
            raise ValueError("Invalid PE signature")
        machine, count = struct.unpack_from("<HH", data, pe + 4)
        opt_size = struct.unpack_from("<H", data, pe + 20)[0]
        opt = pe + 24
        if machine != 0x8664 or opt_size < 152 or struct.unpack_from("<H", data, opt)[0] != 0x20B:
            raise ValueError("Expected PE32+ AMD64")
        if struct.unpack_from("<I", data, opt + 108)[0] < 5:
            raise ValueError("Missing security directory")
        security = opt + 144
        offset, size = struct.unpack_from("<II", data, security)
        sections = opt + opt_size
        if not 0 < count <= 96 or sections + count * 40 > len(data):
            raise ValueError("Invalid section table")
        image_end = sections + count * 40
        for index in range(count):
            length, start = struct.unpack_from("<II", data, sections + index * 40 + 16)
            image_end = max(image_end, start + length)
        if not size or offset % 8 or offset < image_end or offset + size != len(data):
            raise ValueError("Expected a trailing, nonoverlapping certificate table")
        cursor = offset
        while cursor < len(data):
            length, revision, kind = struct.unpack_from("<IHH", data, cursor)
            if length < 8 or cursor + length > len(data) or revision != 0x200 or kind != 2:
                raise ValueError("Invalid WIN_CERTIFICATE")
            cursor += (length + 7) & ~7
        if cursor != len(data):
            raise ValueError("Invalid certificate table alignment")
        image = bytearray(data[:offset])
        struct.pack_into("<I", image, opt + 64, 0)
        struct.pack_into("<II", image, security, 0, 0)
        return bytes(image)
    except struct.error as error:
        raise ValueError("Truncated PE image") from error


def qualify(manifest, reference, candidate, provenance):
    if manifest.get("platform") != "windows-x86_64":
        raise ValueError("Signing variants are Windows-only")
    if sha(reference) != manifest["executable_sha256"]:
        raise ValueError("Reference does not match the pinned executable")
    reference_image = signing_independent_image(reference)
    if reference_image != signing_independent_image(candidate):
        raise ValueError("Executable differs outside signing metadata")
    actual = sha(candidate)
    if actual == manifest["executable_sha256"]:
        raise ValueError("Candidate is already the primary executable")
    manifest["windows"].setdefault("executable_variants", {})[actual] = {
        "qualification": "signing-only-equivalent",
        "reference_sha256": sha(reference),
        "image_sha256": sha(reference_image),
        "provenance": provenance,
    }
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--provenance", required=True)
    args = parser.parse_args()
    manifest = qualify(json.loads(args.manifest.read_text()), args.reference.read_bytes(),
                       args.candidate.read_bytes(), args.provenance)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
