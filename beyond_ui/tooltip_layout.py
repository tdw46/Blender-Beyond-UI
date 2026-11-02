"""Retained tooltip typography in host units; no RNA, GPU or I/O in layout."""
from dataclasses import dataclass, replace

# Measured from the immutable developer-tooltips-v1 reference, normalized to
# its 360-unit card width (not the generated artboard's outer margins).
PADDING_X = 16.5
PADDING_TOP = 7.0
PADDING_BOTTOM = 13.5
BODY_SIZE = 13.5
DETAIL_SIZE = 12.2
LABEL_SIZE = 12.5
BODY_WIDTH = 300.0
BODY_LEADING = 18.0
DETAIL_LEADING = 16.0
LABEL_ADVANCE = 15.0
DESCRIPTION_GAP = 8.0
SECTION_GAP = 10.0


@dataclass(frozen=True)
class Run:
    text: str
    x: float
    y: float
    width: float
    height: float
    role: str = 'body'
    size: float = 11


def wrap(text, width, measure, size, *, code=False):
    """Measure real glyph widths and prefer semantic breaks in identifiers."""
    result = []
    while text:
        lo, hi = 1, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if measure(text[:mid], size) <= width:
                lo = mid
            else:
                hi = mid - 1
        end = lo
        if end < len(text):
            candidates = [i + 1 for i, char in enumerate(text[:end])
                          if char in ('.])' if code else ' \t')]
            if candidates:
                end = candidates[-1]
        result.append(text[:end].rstrip())
        text = text[end:] if code else text[end:].lstrip()
    return result


def layout(text, max_width, max_height, measure):
    padding = min(PADDING_X, max_width / 4)
    sections = []
    for line in str(text).splitlines():
        label, sep, value = line.partition(':')
        if sep and label in {'Python', 'Data Path'}:
            sections.append((label, value.strip()))
        elif line.strip():
            sections.append(('', line.strip()))
        else:
            sections.append(('', ''))
    developer = any(label for label, _ in sections)
    width = min(360., max_width)
    if not developer:
        width = min(width, max(48., max((measure(value, BODY_SIZE) for _, value in sections), default=0) + 2 * padding))
    inner = max(1., width - padding * 2)
    runs = []; y = PADDING_TOP; truncated = False
    for index, (label, value) in enumerate(sections):
        if not value:
            y += 8
            continue
        if label:
            y += (DESCRIPTION_GAP if index == 1 else SECTION_GAP) if runs else 0
            # Never strand a section label without any of its value.
            if y + LABEL_ADVANCE + DETAIL_LEADING + PADDING_BOTTOM > max_height:
                truncated = True
                break
            runs.append(Run(label, padding, y, inner, DETAIL_LEADING, 'title', LABEL_SIZE))
            y += LABEL_ADVANCE
        elif runs:
            y += 4
        size, leading = (DETAIL_SIZE, DETAIL_LEADING) if label else (BODY_SIZE, BODY_LEADING)
        line_width = inner if label else min(BODY_WIDTH, inner)
        for line in wrap(value, line_width, measure, size, code=bool(label)):
            if y + leading + PADDING_BOTTOM > max_height:
                truncated = True
                break
            runs.append(Run(line, padding, y, line_width, leading, 'body', size))
            y += leading
        if truncated:
            break
    if not runs:
        return width, 0, ()
    if truncated:
        last = runs[-1]; value = last.text
        while value and measure(value + '…', last.size) > last.width:
            value = value[:-1]
        runs[-1] = replace(last, text=value + '…')
    return width, min(max_height, y + PADDING_BOTTOM), tuple(runs)
