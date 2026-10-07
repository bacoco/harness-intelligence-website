"""Regression coverage for homepage activity date metadata."""
import re
import unittest
from pathlib import Path

import build


ROOT = Path(__file__).resolve().parents[1]


class ActivityDateTests(unittest.TestCase):
    def setUp(self):
        text = {"fr": {"cuisine": "Titre", "expert": "Titre expert"},
                "en": {"kitchen": "Title", "expert": "Expert title"}}
        self.entity = {
            "type": "dossier", "slug": "date-example", "route": "/dossiers/date-example/",
            "event_date": "2026-10-06", "date_basis": "incident",
            "slots": [{"id": "hero", "heading": text, "body": [text]}],
        }
        self.store = {"assignments": {}, "place_by_id": {}}
        self.event = {"kind": "new", "detected_at": "2026-10-07T08:00:00Z"}

    def render(self):
        return build.update_card(self.entity, self.event, self.store)

    def test_distinct_dates_keep_separate_localized_labels(self):
        markup = self.render()
        self.assertEqual(markup.count('class="argh-update-dates"'), 1)
        self.assertIn('<span class="argh-update-date"><span class="nav-fr">Nouveau le 2026-10-07</span>'
                      '<span class="nav-en">New 2026-10-07</span></span>', markup)
        self.assertIn('<span class="argh-incident-date"><span class="nav-fr">Incident du 2026-10-06</span>'
                      '<span class="nav-en">Incident 2026-10-06</span></span>', markup)
        self.assertLess(markup.index('class="argh-update-dates"'), markup.index('<h3'))

    def test_updated_and_recent_labels_are_preserved(self):
        for kind, french, english in [("updated", "Mis à jour le", "Updated"),
                                      ("recent", "Publié le", "Published")]:
            with self.subTest(kind=kind):
                self.event["kind"] = kind
                markup = self.render()
                self.assertIn(f"{french} 2026-10-07", markup)
                self.assertIn(f"{english} 2026-10-07", markup)

    def test_equal_dates_are_not_duplicated(self):
        self.entity["event_date"] = "2026-10-07"
        markup = self.render()
        self.assertIn('class="argh-update-date"', markup)
        self.assertNotIn('class="argh-incident-date"', markup)

    def test_missing_or_unverified_dates_are_not_invented(self):
        self.event["detected_at"] = ""
        self.assertNotIn('class="argh-update-date"', self.render())
        self.assertIn('class="argh-incident-date"', self.render())
        self.entity["date_basis"] = "unknown"
        self.assertNotIn('class="argh-update-dates"', self.render())

    def test_metadata_wraps_between_items_and_is_visually_subordinate(self):
        css = (ROOT / "assets/renderer.css").read_text(encoding="utf-8")
        match = re.search(r"\.argh-update-dates\s*\{([^}]+)\}", css)
        self.assertIsNotNone(match, "Date metadata needs a layout rule.")
        properties = dict(piece.strip().split(":", 1) for piece in match[1].split(";") if piece.strip())
        self.assertEqual(properties["display"].strip(), "flex")
        self.assertEqual(properties["flex-wrap"].strip(), "wrap")
        self.assertTrue(all(float(value.removesuffix("px")) > 0 for value in properties["gap"].split()))
        self.assertGreater(float(properties["margin-bottom"].removesuffix("px")), 0)
        self.assertLess(float(properties["font-size"].removesuffix("px")), 16)
        self.assertEqual(properties["color"].strip(), "var(--argh-muted)")
        for selector in (".argh-update-date", ".argh-incident-date"):
            rules = re.findall(r"([^{}]+)\{([^{}]+)\}", css)
            self.assertTrue(any(selector in [s.strip() for s in selectors.split(",")]
                                and re.search(r"white-space\s*:\s*nowrap(?:;|$)", body)
                                for selectors, body in rules), selector)

    def test_stylesheet_cache_key_changes_without_changing_script_version(self):
        markup = build.page("Example", "<main>Unchanged text</main>")
        self.assertIn(f'/assets/renderer.css?v={build.VERSION}-date-layout-1', markup)
        self.assertIn(f'/assets/renderer.js?v={build.VERSION}"', markup)
        self.assertIn("<main>Unchanged text</main>", markup)


if __name__ == "__main__":
    unittest.main()
