"""Admission must reject mismatched native code before loading it into Blender."""

import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from beyond_ui.hosts import portable
from beyond_ui.hosts.bridge import BridgeUnavailable


class PortableAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "_native"
        self.directory = self.root / "packages" / "test"
        self.directory.mkdir(parents=True)
        (self.root / "bridge_portable.cpp").write_text("source")
        (self.directory / "bridge.dll").write_bytes(b"library")
        self.exe = self.root / "blender.exe"
        self.exe.write_bytes(b"host")
        self.manifest = dict(
            schema=1,
            abi="beyond-ui-portable-v1",
            platform="windows-x86_64",
            build_hash="exact",
            backends=["OPENGL", "VULKAN"],
            sources={
                "bridge_portable.cpp": portable.digest(
                    self.root / "bridge_portable.cpp"
                )
            },
            library="bridge.dll",
            binary_sha256=portable.digest(self.directory / "bridge.dll"),
            executable_sha256=portable.digest(self.exe),
        )
        self.manifest["adapters"] = {}
        for name in (
            "hosts/portable.py",
            "hosts/portable_actions.py",
            "hosts/bridge.py",
            "hosts/menu_context.py",
            "hosts/menu_native.py",
        ):
            path = self.root.parent / name
            path.parent.mkdir(exist_ok=True)
            path.write_text(name)
            self.manifest["adapters"][name] = portable.digest(path)
        self.publish()

    def publish(self):
        path = self.directory / "manifest.json"
        path.write_text(json.dumps(self.manifest))
        (self.root / "catalog.json").write_text(
            json.dumps(
                dict(
                    schema=1,
                    packages={
                        self.manifest["platform"] + "/exact": dict(
                            directory="packages/test",
                            manifest_sha256=portable.digest(path),
                        )
                    },
                )
            )
        )

    def admit(self, **kwargs):
        args = dict(
            system="Windows",
            machine="AMD64",
            build="exact",
            backend="VULKAN",
            executable=self.exe,
        )
        args.update(kwargs)
        return portable.package(self.root, **args)

    def test_exact_package_and_backend(self):
        self.assertEqual(self.admit()[0], (self.directory / "bridge.dll").resolve())
        for kwargs in (
            {"build": "different"},
            {"backend": "METAL"},
            {"machine": "arm64"},
            {"system": "Linux"},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(BridgeUnavailable):
                self.admit(**kwargs)

    def test_every_input_is_fingerprinted(self):
        for path in [
            self.root.parent / "hosts/portable_actions.py",
            self.exe,
            self.root / "bridge_portable.cpp",
            self.directory / "bridge.dll",
            self.directory / "manifest.json",
        ]:
            before = path.read_bytes()
            path.write_bytes(before + b"changed")
            with self.subTest(path=path), self.assertRaises(BridgeUnavailable):
                self.admit()
            path.write_bytes(before)

    def test_explicit_windows_signing_variant_only(self):
        variant = b"qualified signed host"
        self.manifest["windows"] = {
            "executable_variants": {hashlib.sha256(variant).hexdigest(): {}}
        }
        self.publish()
        self.exe.write_bytes(variant)
        self.assertEqual(self.admit()[0], (self.directory / "bridge.dll").resolve())
        self.exe.write_bytes(variant + b"unqualified")
        with self.assertRaises(BridgeUnavailable):
            self.admit()

    def test_signing_variants_never_relax_darwin_admission(self):
        actual = hashlib.sha256(b"different signed host").hexdigest()
        manifest = dict(self.manifest, platform="darwin-arm64",
                        windows={"executable_variants": {actual: {}}})
        self.assertFalse(portable.executable_matches(actual, manifest))
        self.assertTrue(portable.executable_matches(manifest["executable_sha256"], manifest))

    def test_darwin_metal_exact_package_admission_is_preserved(self):
        self.manifest.update(platform="darwin-arm64", backends=["METAL", "BACKGROUND"])
        variant = b"unqualified Metal executable"
        self.manifest["windows"] = {"executable_variants": {hashlib.sha256(variant).hexdigest(): {}}}
        self.publish()
        args = dict(system="Darwin", machine="arm64", backend="METAL")
        self.assertEqual(self.admit(**args)[0], (self.directory / "bridge.dll").resolve())
        self.exe.write_bytes(variant)
        with self.assertRaises(BridgeUnavailable):
            self.admit(**args)

    def test_library_escape_rejected(self):
        self.manifest["library"] = "../../blender.exe"
        self.manifest["binary_sha256"] = portable.digest(self.exe)
        self.publish()
        with self.assertRaises(BridgeUnavailable):
            self.admit()

    def test_empty_source_inventory_rejected(self):
        self.manifest["sources"] = {}
        self.publish()
        with self.assertRaises(BridgeUnavailable):
            self.admit()

    def test_pe_function_and_allocator_sections(self):
        data = bytearray(512)
        data[:2] = b"MZ"
        struct.pack_into("<I", data, 0x3C, 64)
        data[64:68] = b"PE\0\0"
        struct.pack_into("<HH", data, 68, 0x8664, 2)
        struct.pack_into("<H", data, 84, 112)
        struct.pack_into("<H", data, 88, 0x20B)
        for i, (addr, flags) in enumerate([(0x1000, 0x60000000), (0x2000, 0x40000000)]):
            pos = 200 + 40 * i
            struct.pack_into("<II", data, pos + 8, 256, addr)
            struct.pack_into("<I", data, pos + 36, flags)
        manifest = dict(
            executable_sha256=hashlib.sha256(data).hexdigest(),
            host_symbols=["function"],
            windows=dict(function_rvas={"function": 0x1000}, free_slot_rva=0x2000),
        )
        self.assertEqual(
            portable.checked_windows_addresses(data, manifest), ([0x1000], 0x2000)
        )
        primary = manifest["executable_sha256"]
        manifest["platform"] = "windows-x86_64"
        manifest["executable_sha256"] = "different primary"
        manifest["windows"]["executable_variants"] = {primary: {}}
        self.assertEqual(portable.checked_windows_addresses(data, manifest), ([0x1000], 0x2000))
        with self.assertRaises(ValueError):
            portable.checked_windows_addresses(data + b"unqualified", manifest)
        manifest["windows"]["function_rvas"]["function"] = 0x2000
        with self.assertRaises(ValueError):
            portable.checked_windows_addresses(data, manifest)
        manifest["windows"]["function_rvas"]["function"] = 0x1000
        manifest["windows"]["free_slot_rva"] = 0x1000
        with self.assertRaises(ValueError):
            portable.checked_windows_addresses(data, manifest)
        with self.assertRaises(ValueError):
            portable.pe_sections(b"MZ")
