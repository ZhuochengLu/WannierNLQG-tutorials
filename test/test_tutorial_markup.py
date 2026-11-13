#!/usr/bin/env python3
"""Focused regression tests for mixed Markdown and HTML tutorial pages."""
import tempfile
import unittest
from pathlib import Path
from validate_layout import tutorial_assets, check_local_links, check_tutorial_text

class TutorialMarkupTests(unittest.TestCase):
    def check_page(self, text):
        return check_tutorial_text(text, ['example'], ['spectrum'])

    def test_markdown_images(self):
        self.assertEqual(self.check_page('![one](a.png)\n![two](b.png)'), 2)

    def test_html_images_with_anchors_and_math(self):
        text = '$E=0$\n\n$$\\sigma(\\omega)=1$$\n<a href="a.pdf"><img src="a.png" width="880" alt="Band energies"></a>\n<img alt="Optical response" width="880" src="b.png" />'
        self.assertEqual(self.check_page(text), 2)
        self.assertEqual(tutorial_assets(text)[1], ['a.pdf', 'a.png', 'b.png'])

    def test_mixed_images(self):
        self.assertEqual(self.check_page('![one](a.png)\n<IMG SRC="b.png" ALT="Two">'), 2)

    def test_code_and_comments_not_counted(self):
        text = '![one](a.png)\n![two](b.png)\n```html\n<img src="missing.png">\n```\n<!-- ![hidden](missing.png) -->'
        self.assertEqual(self.check_page(text), 2)

    def test_core_count_follows_content(self):
        for count in (1, 2, 3, 5):
            text = '\n'.join(f'![Figure {i}](figure{i}.png)' for i in range(count))
            self.assertEqual(self.check_page(text), count)
        with self.assertRaises(AssertionError): self.check_page('No result figure')

    def test_html_alt_and_source(self):
        for tag in ['<img src="a.png">', '<img alt="plot">']:
            with self.assertRaises(AssertionError): tutorial_assets(tag)

    def test_local_html_and_markdown_links(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root/'a b.png').touch(); (root/'plot.pdf').touch()
            check_local_links('<a href="plot.pdf#page=1"><img src="a%20b.png" alt="Plot"></a>\n[PDF](plot.pdf "Download")\n[web](https://example.org/no-file)\n<a href="#section">Section</a>', root/'README.md')

    def test_missing_html_source_and_anchor(self):
        with tempfile.TemporaryDirectory() as d:
            for text in ['<img src="missing.png" alt="Plot">', '<a href="missing.pdf">PDF</a>']:
                with self.assertRaises(AssertionError): check_local_links(text, Path(d)/'README.md')

    def test_command_ids_still_checked(self):
        prefix = '![one](a.png)\n![two](b.png)\n'
        self.check_page(prefix+'`--case=example --figure=spectrum`')
        for command in ['--case=missing', '--figure=missing']:
            with self.assertRaises(AssertionError): self.check_page(prefix+command)

    def test_english_and_teaching_narrative(self):
        prefix = '![one](a.png)\n![two](b.png)\n'
        for prose in ['Historical comparison', 'New minus Old', '\u6559\u7a0b']:
            with self.assertRaises(AssertionError): self.check_page(prefix+prose)

if __name__ == '__main__': unittest.main()
