import unittest
from types import SimpleNamespace
from beyond_ui.context_custom_shortcuts import resolve_owner


class CustomShortcutPaths(unittest.TestCase):
    def test_nested_quoted_key(self):
        owner = object()
        context = SimpleNamespace(
            object=SimpleNamespace(children={'quoted "name"': owner})
        )
        self.assertIs(
            resolve_owner(context, 'object.children["quoted \\"name\\""]'), owner
        )

    def test_executable_or_private_paths_rejected(self):
        context = SimpleNamespace(object=SimpleNamespace())
        for path in (
            "object.__class__",
            "object()",
            '__import__("os")',
            "object[1]",
            "context.object",
        ):
            with self.subTest(path=path), self.assertRaises(ValueError):
                resolve_owner(context, path)

    def test_overlong_owner_path_rejected(self):
        with self.assertRaises(ValueError):
            resolve_owner(None, "object." + "a" * 1024)
