import unittest
from scripts.verify_projection import forbidden_product_name


class PublicBoundaryTests(unittest.TestCase):
    def test_official_public_repository_link_is_allowed(self):
        self.assertFalse(forbidden_product_name(
            '<footer><a href="https://github.com/bacoco/loriq-argh-website">GitHub</a></footer>'))

    def test_visible_private_name_still_fails_with_official_link(self):
        self.assertTrue(forbidden_product_name(
            '<a href="https://github.com/bacoco/loriq-argh-website">Loriq</a>'))

    def test_private_links_hidden_content_and_url_suffixes_are_refused(self):
        for html in ('<a href="https://github.com/bacoco/Loriq">GitHub</a>',
                     '<span hidden>Loriq</span>', '<div data-source="loriq">ARGH</div>',
                     '<a href="https://github.com/bacoco/loriq-argh-website?private=1">GitHub</a>'):
            with self.subTest(html=html):
                self.assertTrue(forbidden_product_name(html))
