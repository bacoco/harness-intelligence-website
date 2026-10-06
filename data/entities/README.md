# ARGH public entity store

This directory is the canonical public editorial store after the entity-store migration.

```text
publication/argh/entities/
  index.json
  dossiers/<slug>.json
  projects/<slug>.json
  patterns/<slug>.json
```

Rules:

- one JSON file = one public entity;
- each entity uses `argh/public-entity/v1`;
- every slot contains FR/Cuisine, FR/Expert, EN/Kitchen and EN/Expert;
- every entity carries `event_date` (`YYYY-MM-DD`, the date of the event it documents)
  and `date_basis`: `incident` when the date is derived from a dated evidence record
  and may be displayed, `backfilled` when it is a placeholder that orders the entry
  and must never be shown as a date;
- Cuisine/Kitchen is independently authored from meaning, never lexically transformed from Expert;
- exact source/provenance stays private and is forbidden in this tree;
- `index.json` uses `argh/public-entity-index/v2` and binds each entity to its exact Git blob identity; it contains no editorial prose;
- Git history is the editorial history; do not duplicate the site into a monolithic editorial JSON;
- `bacoco/loriq-argh-website` mirrors this tree and `publication/argh/navigation/`, rebuilds every static route and publishes through GitHub Pages.

The repository corpus is complete and canonical. The scheduled `APPLY_PUBLIC_DATA`
action applies only a fully validated LLM-authored batch. Once that change reaches
`main`, the bounded ChatGPT job synchronizes the static projection; the hourly
website workflow provides the same operation as recovery.
