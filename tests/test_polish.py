"""Regression checks for Polish localization."""
import string
import unittest
from docindexer.i18n import STRINGS, LANGUAGES, ORDER, set_language, tr
from docindexer.i18n_pl import STRINGS as POLISH

class LocalizationTests(unittest.TestCase):
    def tearDown(self):
        set_language('it')

    def test_complete_catalog_and_format_fields(self):
        self.assertEqual(set(STRINGS), set(POLISH))
        fmt = string.Formatter()
        fields = lambda s: sorted(f for _, f, _, _ in fmt.parse(s) if f is not None)
        set_language('pl')
        for original, translated in POLISH.items():
            with self.subTest(original=original):
                self.assertTrue(translated.strip())
                self.assertEqual(fields(original), fields(translated))
                values = {f: '1' for f in fields(original)}
                self.assertEqual(tr(original, **values), translated.format(**values))

    def test_existing_languages_still_work(self):
        for code in LANGUAGES:
            set_language(code)
            if code == 'pl':
                self.assertEqual(tr('Ricerca'), 'Wyszukiwanie')
            else:
                for original, row in STRINGS.items():
                    if '{' not in original:
                        expected = original if code == 'it' else row[ORDER.index(code)] or original
                        self.assertEqual(tr(original), expected)
        set_language('unknown')
        self.assertEqual(tr('Ricerca'), 'Ricerca')


    def test_polish_terms(self):
        from docindexer import terms
        self.assertEqual(terms.labels('pl')[1], 'Akceptuję')
        self.assertIn('WARUNKI UŻYTKOWANIA', terms.text('pl'))
        self.assertNotIn('{v}', terms.text('pl'))
        self.assertNotIn('{d}', terms.text('pl'))

if __name__ == "__main__":
    unittest.main()
