import unittest
from beyond_ui.context_arguments import Arguments


class ArgumentSnapshots(unittest.TestCase):
    def test_nested_values_are_isolated_from_original_and_returned_mutations(self):
        original = {"vector": [1, 2], "nested": [{"flags": {"A"}}]}
        args = Arguments()
        args.capture(original)
        original["vector"][0] = 9
        original["nested"][0]["flags"].add("B")
        values = args.values()
        self.assertEqual(values, {"vector": [1, 2], "nested": [{"flags": {"A"}}]})
        values["vector"][1] = 8
        self.assertEqual(args.values()["vector"], [1, 2])

    def test_pointer_lifetime_and_bounded_rejection(self):
        class Pointer:
            value = 123

            def as_pointer(self):
                return self.value

        pointer = Pointer()
        args = Arguments()
        args.capture({"owner": pointer})
        self.assertIs(args.values()["owner"], pointer)
        pointer.value = 0
        self.assertFalse(args.valid())
        with self.assertRaises(ReferenceError):
            args.values()
        recursive = []
        recursive.append(recursive)
        args.capture({"recursive": recursive})
        self.assertFalse(args.valid())
        args.capture({"too_many": list(range(1000))})
        self.assertFalse(args.valid())
        args.capture({"value": 1})
        self.assertEqual(args.values(), {"value": 1})
