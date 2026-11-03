import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock
from beyond_ui import AddonUI
from beyond_ui.hosts.addon import Runtime


def ptr(n, **kw):
    return NS(as_pointer=lambda: n, **kw)


class AuthorRevision(unittest.TestCase):
    def setUp(self):
        self.calls = 0
        self.revision = 'first'
        test = self

        class Panel:
            bl_label = 'Test'
            beyond_ui_draw_cache_key = staticmethod(lambda ctx: test.revision)

            def draw(self, context):
                test.calls += 1
                self.layout.label(text=test.revision, translate=False)

        self.panel = Panel
        self.context = NS(window=ptr(1), scene=ptr(2), view_layer=ptr(3), object=None,
                          space_data=ptr(4), mode='OBJECT', region=NS(width=300),
                          preferences=NS(system=NS(ui_scale=1), view=NS(language='en_US',
                              use_translate_interface=False, use_translate_tooltips=False)))
        self.rt = Runtime(AddonUI('test'), [Panel], adopt=True)
        self.rt.running.add(1)
        self.host = NS(bridge=object(), _key=lambda ctx: (1, 2, 3),
                       defer_draw=Mock(return_value=False), draw=Mock(return_value=True))
        self.rt.hosts[Panel] = self.host
        self.rt.canvases[Panel] = {}

    def draw(self):
        self.rt.draw(self.panel, NS(), self.context)
        self.assertEqual(self.rt.errors, {})
        return self.rt.canvases[self.panel][(1, 2, 3)][1]

    def test_backdrop_redraw_reuses_authored_controls_but_refreshes_live_widgets(self):
        canvas = self.draw()
        refresh = Mock()
        control = next(iter(canvas.controls.values()))
        control.options['widget'] = NS(refresh_display=refresh)
        canvas.backdrop_revision += 1
        for _ in range(20):
            self.assertIs(self.draw(), canvas)
        self.assertEqual(self.calls, 1)
        self.assertEqual(refresh.call_count, 20)
        self.assertEqual(self.host.draw.call_count, 21)

    def test_changed_literal_reauthors_and_patch_preserves_unrelated_edit(self):
        canvas = self.draw()
        edit = object()
        canvas.edit = edit
        self.revision = 'second'
        self.assertIs(self.draw(), canvas)
        self.assertEqual(self.calls, 2)
        self.assertEqual(next(iter(canvas.controls.values())).label, 'second')
        self.assertIs(canvas.edit, edit)

    def test_owner_replacement_width_locale_and_disclosure_reauthor(self):
        self.draw()
        for mutate in (
            lambda: setattr(self.context, 'object', ptr(5)),
            lambda: setattr(self.context.region, 'width', 400),
            lambda: setattr(self.context.preferences.view, 'language', 'fr_FR'),
            lambda: self.rt.layout_states[(self.panel, (1, 2, 3))].update(open=False),
        ):
            before = self.calls
            mutate()
            self.draw()
            self.assertEqual(self.calls, before + 1)

    def test_default_panels_still_author_each_redraw(self):
        del self.panel.beyond_ui_draw_cache_key
        self.draw()
        self.draw()
        self.assertEqual(self.calls, 2)

    def test_revoked_cache_does_not_reuse_authoring(self):
        old = self.draw()
        old.park()
        self.rt.canvases[self.panel].clear()
        self.assertIsNot(self.draw(), old)
        self.assertEqual(self.calls, 2)
