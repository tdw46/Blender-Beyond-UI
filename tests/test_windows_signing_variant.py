import hashlib
import struct
import unittest
from tools.qualify_windows_signing_variant import qualify, signing_independent_image


def image(certificate=b"signature-one"):
    body = bytearray(512)
    body[:2] = b"MZ"
    struct.pack_into("<I", body, 60, 64)
    body[64:68] = b"PE\0\0"
    struct.pack_into("<HH", body, 68, 0x8664, 1)
    struct.pack_into("<H", body, 84, 240)
    struct.pack_into("<H", body, 88, 0x20B)
    struct.pack_into("<I", body, 88 + 108, 16)
    struct.pack_into("<II", body, 328 + 16, 128, 384)
    cert = struct.pack("<IHH", 8 + len(certificate), 0x200, 2) + certificate
    cert += b"\0" * (-len(cert) % 8)
    struct.pack_into("<II", body, 88 + 144, len(body), len(cert))
    return bytes(body) + cert


class WindowsSigningVariantTests(unittest.TestCase):
    def setUp(self):
        self.reference = image()
        self.manifest = {"platform": "windows-x86_64", "windows": {},
                         "executable_sha256": hashlib.sha256(self.reference).hexdigest()}

    def test_only_signing_bytes_and_checksum_may_differ(self):
        candidate = bytearray(image(b"different, longer signature"))
        struct.pack_into("<I", candidate, 88 + 64, 12345)
        result = qualify(self.manifest, self.reference, candidate, "test fixture")
        self.assertIn(hashlib.sha256(candidate).hexdigest(), result["windows"]["executable_variants"])
        self.assertEqual(result["executable_sha256"], hashlib.sha256(self.reference).hexdigest())

    def test_image_mutation_and_wrong_reference_rejected(self):
        candidate = bytearray(image(b"another signature"))
        candidate[400] = 12
        with self.assertRaisesRegex(ValueError, "outside signing"):
            qualify(self.manifest, self.reference, candidate, "test")
        with self.assertRaisesRegex(ValueError, "pinned executable"):
            qualify(self.manifest, image(b"wrong reference"), image(b"candidate"), "test")

    def test_invalid_certificate_ranges_rejected(self):
        for offset, size in ((0, 0), (400, 112), (512, 999999), (513, 15)):
            candidate = bytearray(self.reference)
            struct.pack_into("<II", candidate, 88 + 144, offset, size)
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                signing_independent_image(candidate)
        with self.assertRaises(ValueError):
            signing_independent_image(self.reference + b"unaccounted overlay")

    def test_darwin_and_identical_candidate_rejected(self):
        with self.assertRaisesRegex(ValueError, "already"):
            qualify(self.manifest, self.reference, self.reference, "test")
        self.manifest["platform"] = "darwin-arm64"
        with self.assertRaisesRegex(ValueError, "Windows-only"):
            qualify(self.manifest, self.reference, image(b"candidate"), "test")
