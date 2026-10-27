"""Indexed visible ranges: O(log n + visible rows), zero offscreen value reads."""

from bisect import bisect_right, bisect_left
from itertools import accumulate
from math import isfinite


class VirtualList:
    def __init__(self, heights):
        self.replace(heights)
        self.offset = 0.0

    def replace(self, heights):
        heights = tuple(float(h) for h in heights)
        if any(not isfinite(h) or h <= 0 for h in heights):
            raise ValueError("Row heights must be finite and positive")
        self.edges = (0.0, *accumulate(heights))

    @property
    def height(self):
        return self.edges[-1]

    def scroll(self, delta, viewport):
        self.offset = max(
            0.0, min(max(0.0, self.height - viewport), self.offset + delta)
        )

    def visible(self, viewport):
        if viewport <= 0:
            return
        self.scroll(0, viewport)
        start = max(0, bisect_right(self.edges, self.offset) - 1)
        end = min(len(self.edges) - 1, bisect_left(self.edges, self.offset + viewport))
        for i in range(start, end):
            yield i, self.edges[i] - self.offset, self.edges[i + 1] - self.edges[i]
