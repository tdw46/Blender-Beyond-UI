import unittest
from unittest.mock import patch

from beyond_ui import Layout
from beyond_ui.gpu.typography import text_measurer
from beyond_ui.widgets.choice_card import ChoiceCard


class RecordingPainter:
    texts = []

    def __init__(self, rect, width, height, *args, **kwargs):
        self.width = width

    def map(self, rect):
        return rect

    def surface(self, *args, **kwargs):
        pass

    def text(self, rect, value, **kwargs):
        self.texts.append((rect, value))


class ChoiceCardLayoutTests(unittest.TestCase):
    def test_sized_measure_uses_render_size_and_host_scale(self):
        # Glyph hinting is not linear: scaling advances at 11px is not
        # equivalent to measuring the actual 14.5px title.
        calls = []
        with patch('beyond_ui.gpu.paint.measure', side_effect=lambda f, s, t: calls.append((f, s, t)) or (37, 10)):
            measure = text_measurer(7, 11, 1.5)
            self.assertEqual(measure.at_size('Title', 'title', 14.5), 37 / 1.5)
            self.assertEqual(calls[-1], (7, 21.75, 'Title'))
            measure('Title', 'title')
            self.assertEqual(calls[-1], (7, 12, 'Title'))

    def test_paint_uses_retained_lines_within_card_at_all_widths(self):
        canvas = Layout().canvas
        card = ChoiceCard(canvas, 'Forced Perspective',
                          'Control proportions of parts of your character/scene independent of true camera FOV.',
                          None, None, height=116, padding=6, font_size=14.5,
                          description_size=11.5, line_height=16)
        palette = dict(accent=(1, 1, 1, 1), edge=(1, 1, 1, 1), muted=(1, 1, 1, 1))
        for scale in (1, 1.5, 2):
            for width in range(150, 451):
                w, h = card.dimensions(width * scale, 11 * scale)
                expected = sum(card._text_layout, ())
                RecordingPainter.texts = []
                with patch('beyond_ui.widgets.choice_card.Painter', RecordingPainter), \
                     patch('beyond_ui.widgets.choice_card.skin.draw'), \
                     patch('beyond_ui.widgets.choice_card.wrap_text', side_effect=AssertionError('paint rewrapped text')):
                    card.paint((0, 0, w, h), 0, palette)
                self.assertEqual(tuple(t for _, t in RecordingPainter.texts), expected)
                for (x, y, tw, th), _ in RecordingPainter.texts:
                    self.assertGreaterEqual(y, card.padding - 1e-8)
                    self.assertLessEqual(y + th, card.render_height - card.padding + 1e-8)
                    self.assertLessEqual(x + tw, width - card.padding - card.radio_size)

    def test_dimensions_use_exact_sized_metrics_when_available(self):
        requests = []
        def legacy(text, role):
            raise AssertionError('Compound card used approximate theme-size metrics')
        legacy.at_size = lambda text, role, size: requests.append((role, size)) or len(text) * size
        card = ChoiceCard(Layout().canvas, 'Title', 'Description', None, None)
        card.dimensions(300, 22, legacy)
        self.assertIn(('title', 24), requests)
        self.assertIn(('body', 20), requests)

    def test_retained_canvas_resizes_cards_and_following_controls(self):
        ui = Layout()
        column = ui.column(align=True)
        for index in range(3):
            control = column.group.button(index, 'Choice', lambda: None, height=116)
            control.options['choice_card'] = ChoiceCard(
                ui.canvas, 'Forced Perspective', 'Control proportions of parts of your character/scene independent of true camera FOV.',
                None, None, padding=6, height=116, font_size=14.5, description_size=11.5, line_height=16)
        after = column.label(text='Next')
        for width in (480, 260, 194, 350, 194, 480):
            ui.canvas.arrange(width)
            controls = list(ui.canvas.controls.values())
            for current, following in zip(controls, controls[1:]):
                self.assertLessEqual(current.rect[1] + current.rect[3], following.rect[1])
                card = current.options['choice_card']
                titles, copy = card._text_layout
                required = len(titles) * 17 + len(copy) * 16 + 4 + 12
                self.assertGreaterEqual(current.rect[3], required)
            self.assertGreaterEqual(ui.canvas.height, after.rect[1] + after.rect[3])


if __name__ == '__main__':
    unittest.main()
