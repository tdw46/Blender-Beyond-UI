"""Host-logical measurements of the approved 752 px-wide Format menu crop.

Reference scale: 752 / 224. Keep body type at host size; never fit artboard
pixels to the panel width. Both geometry and input use these dimensions.
"""

from dataclasses import replace


class Metrics:
    WIDTH = 224.0
    PADDING = 8.0
    ROW_HEIGHT = 22.5
    SEARCH_HEIGHT = 24.5
    HEADER_GAP = 8.0
    TITLE_HEIGHT = 18.0
    TITLE_GAP = 5.5
    TEXT_INSET = 10.0
    SEARCH_INSET = 4.5
    TITLE_INSET = 7.0
    TITLE_SIZE = 12.0
    SEARCH_FONT_SIZE = 10.0
    HIGHLIGHT_BLEED = 1.25
    SEARCH_ICON = 15.0
    SEARCH_TEXT = 28.0

    @staticmethod
    def highlight(rect, scale=1.0):
        """Presentation only: leave row spacing, text and hit targets unchanged."""
        x, y, w, h = rect
        bleed = Metrics.HIGHLIGHT_BLEED * scale
        return (x, y - bleed, w, h + 2 * bleed)

    @staticmethod
    def theme(parent):
        return replace(
            parent,
            padding=Metrics.PADDING,
            row_height=Metrics.ROW_HEIGHT,
            gap=0,
            radius=8,
        )
