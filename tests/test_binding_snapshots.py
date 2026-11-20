import unittest
from types import SimpleNamespace as NS
from beyond_ui import Canvas
from beyond_ui.bindings import Binding, Edit
from beyond_ui.widgets import DataPicker


class BindingSnapshots(unittest.TestCase):
    def dynamic(self):
        owners = [{"name": "First"}, {"name": "Second"}]
        selection = [0]
        commits = []

        def freeze():
            index = selection[0]
            return Binding(
                lambda: owners[index]["name"],
                lambda v: owners[index].update(name=v),
                lambda: selection[0] == index,
                lambda a, b: commits.append((index, a, b)),
            )

        binding = Binding(
            lambda: owners[selection[0]]["name"],
            lambda v: freeze().write(v),
            snapshot=freeze,
        )
        return binding, owners, selection, commits

    def test_selection_change_cannot_redirect_edit_or_cancel(self):
        binding, owners, selection, commits = self.dynamic()
        edit = Edit(binding)
        edit.update("Changed")
        selection[0] = 1
        with self.assertRaises(ReferenceError):
            edit.update("Wrong owner")
        edit.finish(cancel=True)
        self.assertEqual(owners, [{"name": "Changed"}, {"name": "Second"}])
        self.assertEqual(commits, [])
        edit = Edit(binding)
        edit.update("Accepted")
        edit.finish()
        self.assertEqual(commits, [(1, "Second", "Accepted")])

    def test_text_commits_before_clicked_action_and_escape_discards(self):
        binding, owners, _, commits = self.dynamic()
        canvas = Canvas()
        field = canvas.text("speech", "", binding)
        submitted = []
        generate = canvas.button("generate", "Generate", lambda: submitted.append(binding.read()))
        canvas.arrange(300)
        clip = (0, 0, 300, 200)

        def send(kind, control, char=""):
            event = NS(type=kind, value="PRESS", unicode=char)
            return canvas.event(event, control.rect[0] + 4, control.rect[1] + 4, clip)

        send("LEFTMOUSE", field)
        send("T", field, "Typed speech")
        send("LEFTMOUSE", generate)
        self.assertEqual(submitted, ["Typed speech"])
        self.assertEqual(commits, [(0, "First", "Typed speech")])
        send("LEFTMOUSE", field)
        send("X", field, "Discard")
        send("ESC", field)
        self.assertEqual(owners[0]["name"], "Typed speech")
        self.assertEqual(len(commits), 1)

    def test_canvas_stale_editor_closes_without_writing_new_selection(self):
        binding, owners, selection, commits = self.dynamic()
        canvas = Canvas()
        c = canvas.text("name", "", binding)
        canvas.arrange(300)
        clip = (0, 0, 300, 200)
        canvas.event(
            NS(type="LEFTMOUSE", value="PRESS"), c.rect[0] + 4, c.rect[1] + 4, clip
        )
        self.assertIsNotNone(canvas.editor)
        canvas.editor.text = "Wrong owner"
        selection[0] = 1
        canvas.event(NS(type="RET", value="PRESS"), 0, 0, clip)
        self.assertIsNone(canvas.edit)
        self.assertEqual(owners[1]["name"], "Second")
        self.assertEqual(commits, [])

    def test_context_snapshot_expires_on_selection_change(self):
        binding, owners, selection, commits = self.dynamic()
        canvas = Canvas()
        c = canvas.text("name", "", binding)
        canvas.arrange(300)
        context = NS(window_manager=NS(clipboard=""))
        self.assertTrue(
            canvas.open_context(c, 10, 10, (0, 0, 300, 200), context=context)
        )
        menu = canvas.context_menu
        selection[0] = 1
        menu.choose(0, context)
        self.assertEqual(context.window_manager.clipboard, "")
        self.assertTrue(menu.closed)

    def test_picker_visibility_policy_and_query_remain_composed(self):
        picker = DataPicker(((1, ".Hidden", ""), (2, "Visible", "")), lambda k: None)
        calls = []
        picker.filter_item = (
            lambda item, query: calls.append(item[0])
            or query.startswith(".")
            or not item[1].startswith(".")
        )
        picker._filter()
        self.assertEqual([i[0] for i in picker.filtered], [2])
        picker.query = "."
        picker._filter()
        self.assertEqual([i[0] for i in picker.filtered], [1])
        picker.query = "missing"
        picker._filter()
        self.assertEqual(picker.filtered, ())
        self.assertEqual(calls, [1, 2, 1])
