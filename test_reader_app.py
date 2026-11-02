"""验证配图解析及 ZIP/目录入口，不修改用户文档。"""
import base64
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from reader_app import load_document, load_zip, make_document

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jS1cAAAAASUVORK5CYII=')


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / '中文 空格'
        (self.root / 'assets').mkdir(parents=True)
        (self.root / 'assets' / '图 1.png').write_bytes(PNG)
        self.md = self.root / '汇报.md'
        self.md.write_text('# 标题\n\n![图](assets/%E5%9B%BE%201.png)\n\n$x_i < y_i$\n', encoding='utf-8-sig')

    def tearDown(self):
        self.tmp.cleanup()

    def test_local_image_is_independent_of_html_location(self):
        doc = load_document(self.md)
        self.assertIn('data:image/png;base64,', doc['html'])
        self.assertEqual(doc['embedded'], 1)
        self.assertEqual(doc['warnings'], [])
        self.assertIn('$x_i &lt; y_i$', doc['html'])
        self.assertNotIn('<em>i', doc['html'])

    def test_raw_html_and_query_and_fragment(self):
        self.md.write_text('<img src="assets/图%201.png?v=2#figure" alt="raw">', encoding='utf-8')
        self.assertEqual(load_document(self.md)['embedded'], 1)

    def test_missing_and_empty_image_are_reported(self):
        (self.root / 'assets' / 'empty.png').touch()
        self.md.write_text('![空](assets/empty.png)\n![失](assets/missing.png)', encoding='utf-8')
        doc = load_document(self.md)
        self.assertEqual(len(doc['warnings']), 2)
        self.assertIn('0 字节', doc['warnings'][0]['reason'])
        self.assertEqual(doc['embedded'], 0)

    def test_folder_selection_and_ambiguous_folder(self):
        self.assertEqual(load_document(self.root)['embedded'], 1)
        (self.root / '另一份.md').write_text('# 标题', encoding='utf-8')
        with self.assertRaises(ValueError):
            load_document(self.root)

    def test_nested_zip_in_memory_without_extraction(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('报告/汇报.md', self.md.read_bytes())
            archive.writestr('报告/assets/图 1.png', PNG)
        self.assertEqual(load_zip(buffer.getvalue(), '配图.zip')['embedded'], 1)

    def test_zip_with_multiple_markdown_requires_explicit_choice(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('a.md', '# A')
            archive.writestr('b.md', '# B')
        with self.assertRaises(ValueError):
            load_zip(buffer.getvalue(), '配图.zip')

    def test_remote_images_are_preserved_and_not_fetched(self):
        doc = make_document('![外链](https://example.com/a.png)', 'a.md', '', lambda src: self.fail(src))
        self.assertEqual(doc['images'], 1)
        self.assertIn('https://example.com/a.png', doc['html'])


if __name__ == '__main__':
    unittest.main()
