# ARGH public site

Static GitHub Pages projection of ARGH public intelligence.

The site mirrors the complete public entity store and exposes the same four authored
reader modes on `/dossiers/`, `/projects/`, `/patterns/` and `/atlas/`:

- French / Cuisine;
- French / Technical;
- English / Kitchen;
- English / Technical.

The browser selects an authored string from the entity JSON. It never translates,
simplifies or rewrites editorial text.

Private evidence, source acquisition, scheduler state and operational provenance
remain in `bacoco/loriq-argh` and are never copied here.

The home page is generated from the real dossier store. `/harness/` explains the
complete path with the same Cuisine/Expert and FR/EN switches, using the compressed
illustrations versioned under `assets/illustrations/`.

`data/taxonomy.json` and `data/visual-taxonomy.json` are synchronized from
`bacoco/loriq-argh/publication/argh/navigation/`. They provide the explicit one-to-one
Cuisine/Expert vocabulary and the authored classifications. A new dossier, pattern
or project without an assignment is never hidden or forced into a category: it is
published in an explicit unclassified group until the LLM-authored taxonomy is
revised.

`data/activity.json` is the public change receipt. On every synchronization the
site compares canonical entity hashes with the preceding projection. A new dossier
is labelled as new; a changed dossier keeps its route and is labelled as enriched.
The first projection is only a baseline, so it cannot manufacture 59 simultaneous
news items.

The primary delivery path is the scheduled ChatGPT `CONSUME_BUNDLE` action in
`bacoco/loriq-argh`. After the validated ARGH commit, that action pins this repository,
runs `scripts/sync_from_argh.py`, the site tests, `build.py` and
`scripts/verify_projection.py`, then commits the generated projection to `main`.
The sync also imports validated generated teaching-card images from ARGH visual briefs.
A dossier-specific asset named `dossier-<slug>-640.*` takes precedence over the
generic taxonomy illustration on that dossier page. Teaching-card assets are rendered
full-width below the dossier introduction so their problem, solution and final rule
remain legible; they are never squeezed into the ordinary 300 px decorative thumbnail. It may write no other public
repository and never authors editorial prose here.

The ARGH scheduler performs the deterministic projection directly from the active
ChatGPT invocation and writes the verified result to `main` through the GitHub
connector. GitHub Actions is not used for synchronization, recovery, validation,
build or publication. No file may be added under `.github/workflows/`; a future
workflow would violate this repository contract. GitHub Pages serves `main`.

## Public teaching-card image derivatives

Visual synchronization requires the pinned Pillow dependency in
`requirements-visuals.txt` and libwebp 1.6.0. The encoder versions are checked before
conversion so a different library build cannot silently replace public images.
Entity-only synchronization and the static site do not require Pillow.

`scripts/sync_from_argh.py --source-visuals ...` first validates every native image's
SHA-256 and byte count against its generation receipt. It then creates public
derivatives only for opaque, single-frame, lossless WebP sources larger than
256 KiB. The derivative keeps the complete original dimensions and uses RGB WebP,
quality 90, method 6, with no resize or metadata passed to the encoder. The original
bytes are kept if the candidate is not strictly smaller. Small images (including
the historical 34 KB teaching card), already-lossy WebPs, transparent or animated
images, and other formats stay byte-identical. The conservative threshold avoids
unnecessary quality loss; the lossless-only gate avoids second-generation lossy
compression. Asset names, routes and authored content are unchanged. The historical
`-640` filename suffix does not impose a 640-pixel resize.

Every run derives from the validated native source, never a previous public
derivative. Native images, masters, prompts, contexts and generation receipts are
read-only inputs. For identical source bytes and the pinned encoder stack, repeated
syncs produce identical output without rewriting unchanged files.

The sync command's additive `visual_derivatives` JSON result records each source
and served SHA-256, byte count, dimensions, format, decision, encoder parameters and
library versions. Keep this operational report with private publication receipts;
it is not written into site data, rendered pages or public asset metadata. Run the
regressions with `python -m unittest discover -s tests` in the prepared environment.
