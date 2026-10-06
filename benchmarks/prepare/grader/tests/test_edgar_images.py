"""Native image nodes are evidence objects even though their text is empty."""
import unittest

from benchmarks.prepare.grader.adapters import edgartools_html as adapter


def node(kind, text='', children=(), **attrs):
    cls = type(kind, (), {'text': lambda self: self.content})
    value = cls()
    value.content, value.children = text, list(children)
    for name, item in attrs.items():
        setattr(value, name, item)
    return value


class EdgarImageTests(unittest.TestCase):
    def test_standalone_and_inline_images_keep_native_order_and_identity(self):
        document = node('DocumentNode', children=[
            node('ImageNode', src='standalone.png'),
            node('ParagraphNode', text='before after', children=[
                node('TextNode', text='before '), node('ImageNode', src='inline.png'),
                node('TextNode', text=' after')])])
        units = adapter.to_units(adapter.dump(document))
        self.assertEqual([(u['kind'], u['text'], u.get('src')) for u in units],
                         [('image', '', 'standalone.png'), ('text', 'before', None),
                          ('image', '', 'inline.png'), ('text', 'after', None)])

    def test_empty_text_without_image_stays_empty(self):
        document = node('DocumentNode', children=[node('ParagraphNode', children=[node('TextNode', text=' ')])])
        self.assertEqual(adapter.to_units(adapter.dump(document)), [])


if __name__ == '__main__':
    unittest.main()
