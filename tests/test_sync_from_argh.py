import hashlib
import io
import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from scripts.sync_from_argh import (
    SyncError, VISUAL_DERIVATIVE_MIN_BYTES, _sync_visuals, _visual_payload, sync,
)


def encoded_image(image, **options):
    output = io.BytesIO()
    image.save(output, **options)
    return output.getvalue()


def visual_revision(root, raw, *, slug="one", suffix=".webp"):
    revision = root / f"card-{slug}" / "r1"
    revision.mkdir(parents=True)
    (revision / f"image{suffix}").write_bytes(raw)
    (revision / "contexte.json").write_text(json.dumps({
        "schema": "argh/visual-brief/v1", "teaching_card": {"public_entity_slug": slug},
    }) + "\n")
    (revision / "generation.json").write_text(json.dumps({
        "schema": "argh/visual-generation/v1", "outcome": "generated",
        "generated_at": "2026-10-07T00:00:00Z",
        "image": {"path": f"image{suffix}", "sha256": hashlib.sha256(raw).hexdigest(),
                  "bytes": len(raw)},
    }) + "\n")
    return revision


def tree_bytes(root):
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def entity(kind, slug):
    plural = {"dossier": "dossiers", "project": "projects", "pattern": "patterns"}[kind]
    return {
        "schema": "argh/public-entity/v1", "id": f"{kind}:{slug}", "type": kind,
        "slug": slug, "route": f"/{plural}/{slug}/",
    }


def blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def source_store(root, values):
    entries = {}
    for value in values:
        plural = {"dossier": "dossiers", "project": "projects", "pattern": "patterns"}[
            value["type"]
        ]
        relative = f"{plural}/{value['slug']}.json"
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
        path.write_bytes(raw)
        entries[relative] = blob(raw)
    (root / "README.md").write_text("public store\n")
    (root / "index.json").write_text(json.dumps({
        "schema": "argh/public-entity-index/v2", "generated_at": "now",
        "entries": entries,
    }, indent=2) + "\n")


class SyncTests(unittest.TestCase):
    def test_sync_replaces_complete_tree_and_writes_meta(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            website = root / "website"
            (website / "data/entities/dossiers").mkdir(parents=True)
            (website / "data/entities/dossiers/stale.json").write_text("{}")
            source_store(source, [entity("dossier", "one"), entity("project", "alpha")])
            result = sync(source, website, "a" * 40, "2026-09-16T12:00:00Z")
            self.assertEqual(result["dossier"], 1)
            self.assertEqual(result["project"], 1)
            self.assertFalse((website / "data/entities/dossiers/stale.json").exists())
            meta = json.loads((website / "data/meta.json").read_text())
            self.assertEqual(meta["source_head"], "a" * 40)
            activity = json.loads((website / "data/activity.json").read_text())
            self.assertEqual(activity["events"], [])

    def test_sync_records_new_and_enriched_dossiers_after_the_baseline(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            website = root / "website"
            first = entity("dossier", "one")
            source_store(source, [first])
            sync(source, website, "a" * 40, "2026-09-16T12:00:00Z")

            first["revision"] = "enriched"
            source_store(source, [first, entity("dossier", "two")])
            result = sync(source, website, "b" * 40, "2026-09-16T13:00:00Z")

            self.assertEqual(result["new_dossiers"], 1)
            self.assertEqual(result["updated_dossiers"], 1)
            activity = json.loads((website / "data/activity.json").read_text())
            by_path = {event["entity_path"]: event for event in activity["events"]}
            self.assertEqual(by_path["dossiers/one.json"]["kind"], "updated")
            self.assertEqual(by_path["dossiers/two.json"]["kind"], "new")

    def test_invalid_source_does_not_touch_destination(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            website = root / "website"
            source_store(source, [entity("dossier", "one")])
            destination = website / "data/entities"
            destination.mkdir(parents=True)
            marker = destination / "keep.txt"
            marker.write_text("unchanged")
            target = source / "dossiers/one.json"
            target.write_text(target.read_text() + " ")
            with self.assertRaisesRegex(SyncError, "hash mismatch"):
                sync(source, website, "a" * 40, "2026-09-16T12:00:00Z")
            self.assertEqual(marker.read_text(), "unchanged")

    def test_sync_copies_latest_generated_teaching_card_image(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            visuals = root / "visuals"
            website = root / "website"
            source_store(source, [entity("dossier", "one")])
            revision = visuals / "card-one" / "r2"
            revision.mkdir(parents=True)
            image = encoded_image(Image.new("RGB", (8, 6), "red"), format="JPEG")
            (revision / "image.jpg").write_bytes(image)
            (revision / "contexte.json").write_text(json.dumps({
                "schema": "argh/visual-brief/v1",
                "teaching_card": {"public_entity_slug": "one"},
            }) + "\n")
            (revision / "generation.json").write_text(json.dumps({
                "schema": "argh/visual-generation/v1",
                "generated_at": "2026-09-19T07:00:00+02:00",
                "outcome": "generated",
                "image": {
                    "path": "image.jpg",
                    "sha256": hashlib.sha256(image).hexdigest(),
                    "bytes": len(image),
                },
            }) + "\n")

            result = sync(
                source, website, "a" * 40, "2026-09-19T07:00:00Z",
                source_visuals=visuals,
            )

            self.assertTrue(result["visuals_changed"])
            self.assertEqual(result["visual_count"], 1)
            self.assertEqual(
                (website / "assets/illustrations/dossier-one-640.jpg").read_bytes(),
                image,
            )

    def test_sync_copies_public_navigation_from_argh(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            navigation = root / "navigation"
            website = root / "website"
            source_store(source, [entity("dossier", "one")])
            navigation.mkdir()
            (navigation / "taxonomy.json").write_text(json.dumps({
                "schema": "argh/public-navigation/v1", "phases": [],
                "places": [], "assignments": {},
            }) + "\n")
            (navigation / "visual-taxonomy.json").write_text(json.dumps({
                "schema": "argh/visual-taxonomy/v1", "families": [],
                "pattern_assignments": {}, "project_states": [],
                "project_state_assignments": {},
            }) + "\n")

            result = sync(source, website, "a" * 40, "2026-09-16T12:00:00Z", navigation)

            self.assertTrue(result["navigation_changed"])
            self.assertEqual(
                json.loads((website / "data/taxonomy.json").read_text())["schema"],
                "argh/public-navigation/v1",
            )
            self.assertEqual(
                json.loads((website / "data/visual-taxonomy.json").read_text())["schema"],
                "argh/visual-taxonomy/v1",
            )


class VisualDerivativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dimensions = (512, 384)
        cls.image = Image.frombytes(
            "RGB", cls.dimensions, random.Random(42).randbytes(512 * 384 * 3),
        )
        cls.native = encoded_image(cls.image, format="WEBP", lossless=True)
        cls.small = encoded_image(Image.new("RGB", (640, 426), "white"),
                                  format="WEBP", quality=80)

    def test_sha_and_size_mismatch_fail_before_any_encoding_or_target_change(self):
        for field, value in (("sha256", "0" * 64), ("bytes", len(self.native) + 1)):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                visual_revision(root / "visuals", self.native, slug="first")
                revision = visual_revision(root / "visuals", self.native, slug="last")
                path = revision / "generation.json"
                generation = json.loads(path.read_text())
                generation["image"][field] = value
                path.write_text(json.dumps(generation))
                target = root / "site/assets/illustrations"
                target.mkdir(parents=True)
                (target / "dossier-old-640.webp").write_bytes(self.small)
                before = tree_bytes(root / "site")
                with patch("scripts.sync_from_argh._visual_payload") as prepare:
                    with self.assertRaisesRegex(SyncError, "receipt mismatch"):
                        _sync_visuals(root / "visuals", root / "site")
                    prepare.assert_not_called()
                self.assertEqual(tree_bytes(root / "site"), before)

    def test_same_native_bytes_produce_identical_derivative_and_keep_dimensions(self):
        first, receipt = _visual_payload(Path("image.webp"), self.native)
        second, repeated = _visual_payload(Path("image.webp"), self.native)
        self.assertGreater(len(self.native), VISUAL_DERIVATIVE_MIN_BYTES)
        self.assertEqual(first, second)
        self.assertEqual(receipt, repeated)
        self.assertLess(len(first), len(self.native) * 0.6)
        with Image.open(io.BytesIO(first)) as image:
            self.assertEqual(image.size, self.dimensions)
            self.assertEqual(image.format, "WEBP")
        self.assertEqual(receipt["source"]["sha256"], hashlib.sha256(self.native).hexdigest())
        self.assertEqual(receipt["served"]["sha256"], hashlib.sha256(first).hexdigest())
        self.assertEqual(receipt["source"]["bytes"], len(self.native))
        self.assertEqual(receipt["served"]["bytes"], len(first))
        self.assertEqual(receipt["encoding"]["quality"], 90)
        self.assertEqual(receipt["encoding"]["method"], 6)
        self.assertFalse(receipt["encoding"]["resize"])
        self.assertEqual(receipt["versions"], {"pillow": "12.3.0", "libwebp": "1.6.0"})

    def test_small_legacy_image_stays_byte_identical_without_encoding(self):
        with patch("scripts.sync_from_argh._encode_visual_webp") as encode:
            served, receipt = _visual_payload(Path("image.webp"), self.small)
            encode.assert_not_called()
        self.assertEqual(served, self.small)
        self.assertFalse(receipt["derivative"])
        self.assertEqual(receipt["decision"], "kept_small_source")

    def test_threshold_is_inclusive(self):
        with patch("scripts.sync_from_argh.VISUAL_DERIVATIVE_MIN_BYTES", len(self.native)):
            served, receipt = _visual_payload(Path("image.webp"), self.native)
        self.assertEqual(served, self.native)
        self.assertEqual(receipt["decision"], "kept_small_source")

    def test_lossy_source_is_never_recompressed_even_above_threshold(self):
        lossy = encoded_image(self.image, format="WEBP", quality=90)
        with patch("scripts.sync_from_argh.VISUAL_DERIVATIVE_MIN_BYTES", 1), \
                patch("scripts.sync_from_argh._encode_visual_webp") as encode:
            served, receipt = _visual_payload(Path("image.webp"), lossy)
            encode.assert_not_called()
        self.assertEqual(served, lossy)
        self.assertEqual(receipt["decision"], "kept_already_lossy")

    def test_transparency_is_preserved(self):
        image = self.image.convert("RGBA")
        image.putalpha(128)
        native = encoded_image(image, format="WEBP", lossless=True)
        self.assertGreater(len(native), VISUAL_DERIVATIVE_MIN_BYTES)
        with patch("scripts.sync_from_argh._encode_visual_webp") as encode:
            served, receipt = _visual_payload(Path("image.webp"), native)
            encode.assert_not_called()
        self.assertEqual(served, native)
        self.assertEqual(receipt["decision"], "kept_transparency")

    def test_animation_is_preserved(self):
        native = encoded_image(self.image, format="WEBP", lossless=True, save_all=True,
                               append_images=[Image.new("RGB", self.dimensions, "red")])
        with patch("scripts.sync_from_argh._encode_visual_webp") as encode:
            served, receipt = _visual_payload(Path("image.webp"), native)
            encode.assert_not_called()
        self.assertEqual(served, native)
        self.assertEqual(receipt["decision"], "kept_animation")

    def test_other_image_formats_remain_byte_identical(self):
        native = encoded_image(self.image, format="PNG")
        with patch("scripts.sync_from_argh._encode_visual_webp") as encode:
            served, receipt = _visual_payload(Path("image.png"), native)
            encode.assert_not_called()
        self.assertEqual(served, native)
        self.assertEqual(receipt["decision"], "kept_non_webp")

    def test_derivative_must_be_strictly_smaller(self):
        for candidate in (self.native, self.native + b"larger"):
            with self.subTest(size=len(candidate)), \
                    patch("scripts.sync_from_argh._encode_visual_webp", return_value=candidate):
                served, receipt = _visual_payload(Path("image.webp"), self.native)
            self.assertEqual(served, self.native)
            self.assertFalse(receipt["derivative"])
            self.assertEqual(receipt["decision"], "kept_derivative_not_smaller")

    def test_encoder_drift_fails_before_encoding(self):
        with patch("scripts.sync_from_argh.VISUAL_ENCODER_VERSIONS",
                   {"pillow": "different", "libwebp": "different"}), \
                patch("scripts.sync_from_argh._encode_visual_webp") as encode:
            with self.assertRaisesRegex(SyncError, "encoder version mismatch"):
                _visual_payload(Path("image.webp"), self.native)
            encode.assert_not_called()

    def test_full_sync_is_idempotent_and_never_mutates_native_or_provenance(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            visuals, source, website = root / "visuals", root / "entities", root / "site"
            revision = visual_revision(visuals, self.native)
            (revision / "prompt.txt").write_text("Private unchanged prompt")
            (revision / "master.png").write_bytes(encoded_image(self.image, format="PNG"))
            visual_revision(visuals, self.small, slug="legacy")
            source_store(source, [entity("dossier", "one"), entity("dossier", "legacy")])
            native_before = tree_bytes(visuals)
            first = sync(source, website, "a" * 40, "2026-10-07T00:00:00Z",
                         source_visuals=visuals)
            public_before = tree_bytes(website)
            mtimes = {p: p.stat().st_mtime_ns for p in website.rglob("*") if p.is_file()}
            second = sync(source, website, "a" * 40, "2026-10-07T01:00:00Z",
                          source_visuals=visuals)
            self.assertEqual(tree_bytes(visuals), native_before)
            self.assertEqual(tree_bytes(website), public_before)
            self.assertEqual({p: p.stat().st_mtime_ns for p in mtimes}, mtimes)
            self.assertEqual(first["visual_derivatives"], second["visual_derivatives"])
            self.assertTrue(first["visuals_changed"])
            self.assertFalse(second["visuals_changed"])
            self.assertFalse(second["data_changed"])
            self.assertFalse(second["meta_changed"])
            self.assertFalse(second["activity_changed"])
            self.assertEqual((website / "assets/illustrations/dossier-legacy-640.webp").read_bytes(),
                             self.small)
            # Only image payloads, existing entity files and ordinary projection data are served.
            self.assertEqual(set(public_before), {
                Path("assets/illustrations/dossier-one-640.webp"),
                Path("assets/illustrations/dossier-legacy-640.webp"),
                Path("data/entities/README.md"), Path("data/entities/index.json"),
                Path("data/entities/dossiers/one.json"), Path("data/entities/dossiers/legacy.json"),
                Path("data/meta.json"), Path("data/activity.json"),
            })


if __name__ == "__main__":
    unittest.main()
