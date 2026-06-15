"""
Tests for xml.py (forked from tdda.testutils TestXMLGeneration).
"""

import os

from tdda.referencetest import ReferenceTestCase, tag

from tdda.xmlgen import XML


TESTDIR = os.path.join(os.path.dirname(__file__), 'testdata')


class TestXMLGeneration(ReferenceTestCase):
    def testSimpleXMLGen(self):
        x = XML()
        x.OpenElement('foo')
        x.WriteElement(
            'bar',
            'Contents of bar oné, twø, thrέé',
            attributes=(('a1', 1), ('a2', 2)),
        )
        x.CloseElement()
        stripped = x.xml().strip()
        self.assertEqual(
            stripped,
            """
<?xml version="1.0" encoding="UTF-8"?>
<foo>
    <bar a1="1" a2="2">Contents of bar oné, twø, thrέé</bar>
</foo>
""".strip(),
        )
        self.assertEqual(type(stripped), str)

    def testSimpleLatin1XMLGen(self):
        x = XML(inputEncoding='latin1')
        x.OpenElement('foo')
        x.WriteElement(
            'bar',
            'Contents of bar oné, twø, threé'.encode('latin1'),
            attributes=(('a1', 1), ('a2', 2)),
        )
        x.CloseElement()
        stripped = x.xml().strip()
        self.assertEqual(
            stripped,
            """
<?xml version="1.0" encoding="UTF-8"?>
<foo>
    <bar a1="1" a2="2">Contents of bar oné, twø, threé</bar>
</foo>
""".strip(),
        )
        self.assertEqual(type(stripped), str)

    def testSimpleLatin9XMLGen(self):
        x = XML(inputEncoding='latin9')
        x.OpenElement('foo')
        x.WriteElement(
            'bar',
            'Contents of bar oné, twø, threé at €3.'.encode('latin9'),
            attributes=(('a1', 1), ('a2', 2)),
        )
        x.CloseElement()
        stripped = x.xml().strip()
        self.assertEqual(
            stripped,
            """
<?xml version="1.0" encoding="UTF-8"?>
<foo>
    <bar a1="1" a2="2">Contents of bar oné, twø, threé at €3.</bar>
</foo>
""".strip(),
        )
        self.assertEqual(type(stripped), str)

    def testHarderLatin9XMLGen(self):
        x = XML(inputEncoding='latin9')
        x.OpenElement('foo')
        x.WriteElement(
            'bar',
            'Contents of bar oné, twø, threé at €3.',
            attributes=(('a1', 1), ('a2', 2)),
        )
        x.WriteElement(
            'bas',
            ('N/A/N/A of 78042 on N/A at N/Abarceló hotels & resorts').encode(
                'latin9'
            ),
        )
        x.CloseElement()
        stripped = x.xml().strip()
        self.assertEqual(
            stripped,
            """
<?xml version="1.0" encoding="UTF-8"?>
<foo>
    <bar a1="1" a2="2">Contents of bar oné, twø, threé at €3.</bar>
    <bas>N/A/N/A of 78042 on N/A at N/Abarceló hotels &amp; resorts</bas>
</foo>
""".strip(),
        )
        self.assertEqual(type(stripped), str)

    def testHTML5ExternalCSS(self):
        x = XML(html=5, title='Test Page', css=['style.css', 'theme.css'])
        x.WriteElement('h1', 'Hello World')
        x.CloseXML()
        self.assertStringCorrect(
            x.xml(), os.path.join(TESTDIR, 'html5-ext.html')
        )

    def testHTML5InlineCSS(self):
        x = XML(html=5, title='Test Page', css='body { margin: 0; }')
        x.WriteElement('p', 'Content')
        x.CloseXML()
        self.assertStringCorrect(
            x.xml(), os.path.join(TESTDIR, 'html5-inline.html')
        )

    def testHTML5EmptyElements(self):
        x = XML(html=5, omitHeader=1)
        x.OpenElement('div', '', {})
        # Non-void empty elements should use open/close tags
        x.WriteElement('td', '', {})
        x.WriteElement('span', '', {})
        x.WriteElement('div', '', {})
        # Void elements should self-close
        x.WriteElement('input', '', {'type': 'text'})
        x.WriteElement('br', '', {})
        x.WriteElement('hr', '', {})
        x.WriteElement('img', '', {'src': 'test.png'})
        x.CloseElement('div')
        x.CloseXML()
        self.assertStringCorrect(
            x.xml(), os.path.join(TESTDIR, 'html5-empty-elements.html')
        )

    def testHTML5TableFormatting(self):
        x = XML(html=5, omitHeader=1)
        x.OpenElement('table')
        x.OpenElement('tr')
        # Pattern: tight on OpenElement suppresses newline after </tag>
        x.OpenElement('td', tight=True)
        x.WriteContent('Cell 1')
        x.CloseElement('td')
        x.WriteElement('td', 'Cell 2')
        x.WriteElement('td', '')  # Empty cell
        x.CloseElement('tr')
        x.CloseElement('table')
        x.CloseXML()
        self.assertStringCorrect(
            x.xml(), os.path.join(TESTDIR, 'html5-table-formatting.html')
        )

    def testEntitizeQuotesDefault(self):
        # Default behavior: quotes and apostrophes are escaped
        x = XML(omitHeader=1)
        x.WriteElement('p', 'patient\'s "test"')
        stripped = x.xml().strip()
        self.assertIn('&apos;', stripped)
        self.assertIn('&quot;', stripped)
        self.assertEqual(stripped, '<p>patient&apos;s &quot;test&quot;</p>')

    def testEntitizeQuotesFalse(self):
        # With entitize_quotes=False: quotes preserved in content
        x = XML(omitHeader=1, entitize_quotes=False)
        x.WriteElement('p', 'patient\'s "test"')
        stripped = x.xml().strip()
        self.assertNotIn('&apos;', stripped)
        self.assertNotIn('&quot;', stripped)
        self.assertEqual(stripped, '<p>patient\'s "test"</p>')

    def testTightBlockWithInlineContent(self):
        """Test block element with inline content using tight=True."""
        x = XML(omitHeader=1)
        x.OpenElement('header', tight=True)
        x.WriteContent('Title Text', tight=True)
        x.CloseElement('header')
        result = x.xml().strip()
        # Expected: <header>, no newline after >, content inline, </header> with newline
        expected = '<header>Title Text</header>'
        self.assertEqual(result, expected)

    def testNestedTightInline(self):
        """Test truly inline element nested in tight parent."""
        x = XML(omitHeader=1)
        x.OpenElement('header', tight=True)
        x.OpenElement(
            'a', attributes={'href': 'http://example.com'}, tight=True
        )
        x.WriteContent('link', tight=True)
        x.CloseElement('a')
        x.CloseElement('header')
        result = x.xml().strip()
        # Expected: <header><a href="...">link</a></header>
        # The </a> should NOT have a newline because parent <header> is tight
        expected = '<header><a href="http://example.com">link</a></header>'
        self.assertEqual(result, expected)

    def testInlineInNonTightParent(self):
        """Test inline element in non-tight parent (control case)."""
        x = XML(omitHeader=1)
        x.OpenElement('div')  # NOT tight
        x.OpenElement(
            'a', attributes={'href': 'http://example.com'}, tight=True
        )
        x.WriteContent('link', tight=True)
        x.CloseElement('a')
        x.CloseElement('div')
        result = x.xml().strip()
        # Expected: <div>\n    <a>link</a>\n</div>
        # The </a> SHOULD have a newline because parent is NOT tight
        expected = '<div>\n    <a href="http://example.com">link</a>\n</div>'
        self.assertEqual(result, expected)

    def testNestedTightInlineExplicitClose(self):
        """Same as testNestedTightInline but with explicit tight=True on CloseElement.

        This verifies backward compatibility - explicitly passing tight to CloseElement
        should produce the same result as relying on the stack.
        """
        x = XML(omitHeader=1)
        x.OpenElement('header', tight=True)
        x.OpenElement(
            'a', attributes={'href': 'http://example.com'}, tight=True
        )
        x.WriteContent('link', tight=True)
        x.CloseElement('a', tight=True)
        x.CloseElement('header', tight=True)
        result = x.xml().strip()
        # Should produce identical output to testNestedTightInline
        expected = '<header><a href="http://example.com">link</a></header>'
        self.assertEqual(result, expected)


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
