import sys
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from beyond_ui.gpu import glass


class SharedViewportObserverTests(unittest.TestCase):
    def test_two_hosts_publish_one_revision_and_release_the_last_handler(self):
        space = Mock()
        window = NS(as_pointer=lambda: 1)
        viewport = NS(type="WINDOW", x=0, y=0, width=800, height=500)
        sidebar = NS(type="UI", x=500, y=0, width=300, height=500, as_pointer=lambda: 3, tag_redraw=Mock())
        area = NS(type="VIEW_3D", as_pointer=lambda: 2, regions=(viewport, sidebar))
        context = NS(window=window, region=viewport, area=area, preferences=NS(system=NS(use_region_overlap=True)))
        fake = NS(types=NS(SpaceView3D=space), context=context)
        key = (1, 2, 3)
        late = {key: {"valid": True, "late": True}}
        immediate = {key: {"valid": True}}
        with (patch.dict(sys.modules, bpy=fake), patch.object(glass, "_viewport_hosts", {}),
              patch.object(glass, "_viewport_handler", None), patch.object(glass, "_views", {})):
            glass.watch_viewport(late)
            glass.watch_viewport(immediate)
            space.draw_handler_add.assert_called_once()
            glass._viewport_draw()
            self.assertEqual(glass._views[(1, 2)], 1)
            sidebar.tag_redraw.assert_called_once()
            glass.unwatch_viewport(immediate)
            space.draw_handler_remove.assert_not_called()
            glass._viewport_draw()
            self.assertEqual(glass._views[(1, 2)], 2)
            sidebar.tag_redraw.assert_called_once()
            late[key]["valid"] = False
            glass._viewport_draw()
            self.assertEqual(glass._views[(1, 2)], 2)
            glass.unwatch_viewport(late)
            space.draw_handler_remove.assert_called_once()
            self.assertFalse(glass._views)
