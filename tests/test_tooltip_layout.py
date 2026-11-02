import unittest
from beyond_ui.tooltip_layout import layout, wrap


class TooltipLayout(unittest.TestCase):
    measure = staticmethod(lambda text, size: len(text) * size * .55)

    def test_sections_have_shared_padding_bold_labels_and_separate_gaps(self):
        w,h,runs=layout('Description\nPython: Object.location\nData Path: bpy.data.objects["Cube"].location',360,500,self.measure)
        labels=[r for r in runs if r.role=='title']
        self.assertEqual([r.text for r in labels],['Python','Data Path'])
        self.assertTrue(all(r.x==16.5 for r in runs))
        for label in labels:
            i=runs.index(label);prev=runs[i-1];value=runs[i+1]
            self.assertGreaterEqual(label.y-prev.y-prev.height,7)
            self.assertEqual(value.y-label.y,15)
        self.assertEqual(h-runs[-1].y-runs[-1].height,13.5)

    def test_code_wrap_preserves_exact_identifier_and_prefers_punctuation(self):
        value='bpy.data.scenes["Scene"].mesh_object_items[0].auto_fov_max_strength'
        lines=wrap(value,190,self.measure,11,code=True)
        self.assertEqual(''.join(lines),value)
        self.assertTrue(all(self.measure(line,11)<=190 for line in lines))
        self.assertTrue(all(line.endswith(('.',']',')')) for line in lines[:-1]))

    def test_narrow_short_clip_has_no_orphan_label_or_overflow(self):
        text='A useful description with several words\nPython: Object.location\nData Path: bpy.data.objects["Cube"].location'
        for width in (120,200,360):
            for height in (40,90,150,500):
                w,h,runs=layout(text,width,height,self.measure)
                self.assertLessEqual(w,width);self.assertLessEqual(h,height)
                for i,r in enumerate(runs):
                    self.assertLessEqual(r.y+r.height,h)
                    self.assertLessEqual(self.measure(r.text,r.size),r.width)
                    if r.role=='title':self.assertLess(i,len(runs)-1)

    def test_ordinary_help_keeps_paragraph_spacing_and_compact_width(self):
        w,h,r=layout('Copy value\n\nKeep the original.',360,400,self.measure)
        self.assertTrue(all(run.role=='body' for run in r))
        self.assertLess(w,360)
        self.assertGreater(r[1].y-r[0].y-r[0].height,4)
