#!/usr/bin/env python3
"""Génère le site statique ARGH avec le balisage exact du renderer WordPress 1.5.0.

Port fidèle de publication/argh/renderer/argh-renderer.php : mêmes classes, même
ordre, mêmes quatre variantes dans le DOM. Le CSS et le JS sont ceux du plugin,
copiés sans modification ; c'est donc le même rendu, servi en statique.
"""
import json, html, re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "entities"
TAXONOMY = ROOT / "data" / "taxonomy.json"
VISUAL_TAXONOMY = ROOT / "data" / "visual-taxonomy.json"
ACTIVITY = ROOT / "data" / "activity.json"
VERSION = "1.7.0"
PLURAL = {"dossier": "dossiers", "project": "projects", "pattern": "patterns"}
PAGE_ILLUSTRATIONS = {
    "dossier": "/assets/illustrations/page-dossiers-640.jpg",
    "pattern": "/assets/illustrations/page-patterns-640.jpg",
    "project": "/assets/illustrations/page-projects-640.jpg",
    "atlas": "/assets/illustrations/page-atlas-640.jpg",
    "about": "/assets/illustrations/page-about-640.jpg",
}
PLACE_ILLUSTRATIONS = {
    "objectifs-instructions": "/assets/illustrations/category-objectives-instructions-320.jpg",
    "dependances-externes": "/assets/illustrations/category-external-dependencies-320.jpg",
    "entrees-declencheurs": "/assets/illustrations/category-inputs-triggers-320.jpg",
    "donnees-memoire-etat": "/assets/illustrations/category-data-memory-state-320.jpg",
    "configuration-environnement": "/assets/illustrations/category-configuration-environment-320.jpg",
    "isolation-concurrence": "/assets/illustrations/category-isolation-concurrency-320.jpg",
    "roles-orchestration": "/assets/illustrations/category-roles-orchestration-320.jpg",
    "outils-infrastructure": "/assets/illustrations/category-tools-infrastructure-320.jpg",
    "execution-cycle-vie": "/assets/illustrations/category-execution-lifecycle-320.jpg",
    "validation-preuves": "/assets/illustrations/category-validation-evidence-320.jpg",
    "publication-resultat": "/assets/illustrations/category-publication-outcome-320.jpg",
    "couts-quotas": "/assets/illustrations/category-costs-quotas-320.jpg",
    "annulation-recuperation": "/assets/illustrations/category-cancellation-recovery-320.jpg",
    "historique-tracabilite": "/assets/illustrations/category-history-traceability-320.jpg",
}

def esc(s): return html.escape(s or "", quote=True)

def sanitize_title(name):
    """Équivalent de sanitize_title() de WordPress, pour les libellés de projet."""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")

def quad(q, tag="span", cls=""):
    q = q or {}
    fr, en = q.get("fr") or {}, q.get("en") or {}
    modes = [("fr-cuisine", fr.get("cuisine", "")),
             ("fr-specialist", fr.get("expert", fr.get("specialist", ""))),
             ("en-kitchen", en.get("kitchen", "")),
             ("en-specialist", en.get("expert", en.get("specialist", "")))]
    out = '<%s class="argh-q%s">' % (tag, (" " + esc(cls)) if cls else "")
    for mode, text in modes:
        out += '<span class="argh-mode argh-%s">%s</span>' % (mode, esc(text))
    return out + "</%s>" % tag


def visual(image, cls, loading="lazy"):
    if not image:
        return ""
    priority = ' fetchpriority="high"' if loading == "eager" else ""
    return ('<picture class="%s"><img src="%s" width="640" height="427" alt="" '
            'aria-hidden="true" loading="%s" decoding="async"%s></picture>'
            % (esc(cls), esc(image), loading, priority))

def teaching_visual(image, alt):
    if not image:
        return ""
    return ('<figure class="argh-teaching-card"><img src="%s" width="1536" height="1024" '
            'alt="%s" loading="eager" decoding="async" fetchpriority="high"></figure>'
            % (esc(image), esc(alt)))


def is_teaching_card_image(image):
    return bool(image and image.startswith("/assets/illustrations/dossier-"))


def teaching_alt(e):
    hero = slot_of(e, "hero")
    lesson = slot_of(e, "lesson")
    response = slot_of(e, "response")
    parts = []
    if hero:
        parts.append(hero["heading"]["fr"]["cuisine"])
    if response and response.get("body"):
        parts.append(response["body"][0]["fr"]["cuisine"])
    if lesson and lesson.get("body"):
        parts.append(lesson["body"][0]["fr"]["cuisine"])
    return " ".join(part.strip() for part in parts if isinstance(part, str) and part.strip())


def nav(href, section, body, current):
    cur = ' aria-current="page"' if current == section else ""
    return '<a href="%s"%s>%s</a>' % (esc(href), cur, body)

def header(section=""):
    n = ("".join([
        nav("/", "home", '<span class="nav-en">Home</span><span class="nav-fr">Accueil</span>', section),
        nav("/dossiers/", "dossiers", "Dossiers", section),
        nav("/patterns/", "patterns", '<span class="nav-en">Patterns</span><span class="nav-fr">Motifs</span>', section),
        nav("/projects/", "projects", '<span class="nav-en">Projects</span><span class="nav-fr">Projets</span>', section),
        nav("/atlas/", "atlas", "Atlas", section),
        nav("/harness/", "harness", '<span class="nav-en">The harness</span><span class="nav-fr">Le harnais</span>', section),
        nav("/glossary/", "glossary", '<span class="nav-en">Glossary</span><span class="nav-fr">Glossaire</span>', section),
        nav("/about/", "about", '<span class="nav-en">About</span><span class="nav-fr">À propos</span>', section),
    ]))
    return ('<header class="argh-top"><div class="argh-topin">'
      '<a class="argh-brand" href="/" aria-label="ARGH">'
      '<img src="/assets/logo-imagine.png" alt="ARGH — Agent Reliability &amp; Guard for Harnesses" loading="eager"></a>'
      '<nav class="argh-nav">' + n + '</nav>'
      '<div class="argh-controls">'
      '<div class="argh-toggle argh-reader">'
      '<button type="button" data-reader="simple"><span class="nav-en">Kitchen</span><span class="nav-fr">Cuisine</span></button>'
      '<button type="button" data-reader="expert"><span class="nav-en">Expert</span><span class="nav-fr">Expert</span></button></div>'
      '<div class="argh-toggle argh-lang">'
      '<button type="button" data-lang="en">EN</button>'
      '<button type="button" data-lang="fr">FR</button></div></div></div></header>')

FOOT = ('<footer class="argh-foot"><span>ARGH — Agent Reliability &amp; Guard for Harnesses</span>'
        '<a href="https://github.com/bacoco/loriq-argh-website">GitHub</a></footer>')

def page(title, body, desc=""):
    return ("<!doctype html>\n<html lang=\"fr-FR\">\n<head>\n"
      '<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n'
      '<title>%s</title>\n<meta name="description" content="%s">\n'
      '<link rel="icon" href="/assets/logo.png">\n'
      '<link rel="stylesheet" href="/assets/renderer.css?v=%s-date-layout-1">\n'
      '<script src="/assets/renderer.js?v=%s" defer></script>\n</head>\n'
      '<body class="argh-fr argh-reader-simple argh-rendered-page">\n%s\n</body>\n</html>\n'
      % (esc(title), esc(desc), VERSION, VERSION, body))

def slot_of(e, sid):
    for s in e.get("slots", []):
        if s.get("id") == sid: return s
    return None

def pattern_heading(slug, store):
    e = store["patterns"].get(slug)
    h = slot_of(e, "hero") if e else None
    return h.get("heading") if h else None

def relationships(e, store):
    r = e.get("relationships") or {}
    chips = []
    for name in r.get("projects", []):
        href = "/projects/%s/" % esc(sanitize_title(name))
        # Source attribution belongs to Expert. Cuisine/Kitchen receives the
        # self-contained scene and must not expose the originating product.
        for mode in ("fr-specialist", "en-specialist"):
            chips.append('<a class="argh-chip argh-mode argh-%s" href="%s">%s</a>'
                         % (mode, href, esc(name)))
    for slug in r.get("patterns", []):
        h = pattern_heading(slug, store)
        if not h: continue
        chips.append('<a class="argh-chip" href="/patterns/%s/">%s</a>' % (esc(slug), quad(h, "span", "argh-chip-label")))
    return '<div class="argh-chips">%s</div>' % "".join(chips) if chips else ""

def context(t):
    q = {"dossier": ("Dossier", "Dossier"), "project": ("Projet", "Project"),
         "pattern": ("Motif", "Pattern")}.get(t, ("ARGH", "ARGH"))
    return '<div class="argh-context"><span class="nav-fr">%s</span><span class="nav-en">%s</span></div>' % q

def render_slot(s):
    out = '<section class="argh-section argh-kind-%s">%s' % (esc(s.get("kind", "section")), quad(s.get("heading"), "h2"))
    for p in s.get("body", []): out += quad(p, "p")
    return out + "</section>"

def related(e, store):
    rels = (e.get("relationships") or {}).get("dossiers") or []
    if not rels: return ""
    out = ('<section class="argh-related"><div class="argh-section-head"><h2>'
           '<span class="nav-en">Related dossiers</span><span class="nav-fr">Dossiers associés</span>'
           '</h2></div><div class="argh-related-grid">')
    for slug in rels[:36]:
        x = store["by_route"].get("/dossiers/%s/" % slug)
        if not x: continue
        h = slot_of(x, "hero")
        out += '<a class="argh-related-card" href="%s">%s</a>' % (esc(x["route"]), quad(h["heading"], "h3", "argh-related-title"))
    return out + "</div></section>"


def entity_visual(e, store):
    if e.get("type") == "dossier":
        for suffix in (".webp", ".jpg", ".jpeg", ".png"):
            custom = ROOT / "assets" / "illustrations" / ("dossier-%s-640%s" % (e["slug"], suffix))
            if custom.is_file():
                place = store["place_by_id"].get(store["assignments"].get(e["slug"]))
                label = place["label"] if place else None
                href = "/places/%s/" % place["id"] if place else None
                return ("/assets/illustrations/" + custom.name, label, href)
        place = store["place_by_id"].get(store["assignments"].get(e["slug"]))
        image = (place.get("image") or PLACE_ILLUSTRATIONS.get(place["id"])) if place else None
        return (image, place["label"], "/places/%s/" % place["id"]) if place else (None, None, None)
    if e.get("type") == "pattern":
        family = store["family_by_id"].get(store["pattern_assignments"].get(e["slug"]))
        return (family["image"], family["label"], "/patterns/#%s" % family["id"]) if family else (None, None, None)
    if e.get("type") == "project":
        state = store["project_state_by_id"].get(store["project_state_assignments"].get(e["slug"]))
        return (state["image"], state["label"], "/projects/#%s" % state["id"]) if state else (None, None, None)
    return None, None, None


def classification_badge(label, href):
    if not label:
        return ""
    return '<a class="argh-classification" href="%s">%s</a>' % (esc(href), quad(label))


def detail(e, store):
    h = slot_of(e, "hero")
    image, label, href = entity_visual(e, store)
    teaching = e.get("type") == "dossier" and is_teaching_card_image(image)
    hero_class = "argh-detail-hero argh-detail-hero-text-only" if teaching else "argh-detail-hero"
    hero_visual = "" if teaching else visual(image, "argh-detail-visual", "eager")
    card = teaching_visual(image, teaching_alt(e)) if teaching else ""
    body = ('<div class="argh-site" data-argh-renderer="%s" data-argh-route="%s">%s'
            '<main class="argh-wrap"><article class="argh-article">'
            '<div class="%s"><div class="argh-detail-hero-copy">%s%s%s%s</div>%s</div>%s%s'
            % (VERSION, esc(e["route"]), header(PLURAL[e["type"]]), hero_class,
               context(e["type"]), quad(h["heading"], "h1"),
               quad((h.get("body") or [{}])[0], "p", "argh-standfirst"),
               classification_badge(label, href), hero_visual,
               relationships(e, store), card))
    for s in e.get("slots", []):
        if s.get("id") != "hero": body += render_slot(s)
    if e.get("type") != "dossier": body += related(e, store)
    body += "</article>" + FOOT + "</main></div>"
    title = (h["heading"]["fr"]["cuisine"] or e["slug"]) + " — ARGH"
    desc = ((h.get("body") or [{}])[0].get("fr", {}) or {}).get("expert", "")
    return page(title, body, desc[:180])


INDEX_DECK = {
    "dossier": {
        "fr": {"cuisine": "Toutes les histoires sont rangées selon l’endroit de la cuisine où le problème apparaît.",
               "expert": "Tous les incidents sont classés selon l’étape du parcours où le mécanisme devient observable."},
        "en": {"kitchen": "Every story is arranged by the place in the kitchen where the problem appears.",
               "expert": "Every incident is classified by the stage where its mechanism becomes observable."}},
    "pattern": {
        "fr": {"cuisine": "Les problèmes qui reviennent sont réunis en dix familles faciles à parcourir.",
               "expert": "Les mécanismes récurrents sont répartis dans dix familles transversales explicites."},
        "en": {"kitchen": "Recurring problems are gathered into ten families that are easy to browse.",
               "expert": "Recurring mechanisms are assigned to ten explicit cross-cutting families."}},
    "project": {
        "fr": {"cuisine": "Chaque maison est rangée selon ce que l’on sait aujourd’hui de son activité.",
               "expert": "Chaque système est regroupé selon son état de cycle de vie documenté."},
        "en": {"kitchen": "Each house is arranged by what is currently known about its activity.",
               "expert": "Each system is grouped by its documented lifecycle state."}},
}


def grouped_index_section(group, items):
    count = {
        "fr": {"cuisine": "%d fiche%s" % (len(items), "s" if len(items) != 1 else ""),
               "expert": "%d entrée%s" % (len(items), "s" if len(items) != 1 else "")},
        "en": {"kitchen": "%d card%s" % (len(items), "s" if len(items) != 1 else ""),
               "expert": "%d entr%s" % (len(items), "ies" if len(items) != 1 else "y")},
    }
    return ('<section class="argh-taxonomy-group" id="%s">'
            '<div class="argh-taxonomy-head">%s<div class="argh-taxonomy-copy">%s%s%s</div></div>'
            '<div class="argh-index-grid">%s</div></section>'
            % (esc(group["id"]), visual(group.get("image"), "argh-taxonomy-picture"),
               quad(group["label"], "h2"), quad(group["description"], "p"),
               quad(count, "span", "argh-taxonomy-count"), "".join(card(e) for e in items)))


def index(t, store):
    items = sorted([e for e in store["items"] if e.get("type") == t], key=lambda e: e["slug"])
    label = {"dossier": ("Dossiers", "Dossiers"), "project": ("Projets", "Projects"),
             "pattern": ("Motifs", "Patterns")}[t]
    body = ('<div class="argh-site argh-index" data-argh-renderer="%s">%s'
            '<main class="argh-wrap"><section class="argh-index-hero argh-index-hero-illustrated">'
            '<div class="argh-index-hero-copy"><div class="argh-kicker">ARGH</div>'
            '<h1><span class="nav-fr">%s</span><span class="nav-en">%s</span></h1>%s'
            '<div class="argh-index-count">%d <span class="nav-fr">entrées</span><span class="nav-en">entries</span></div>'
            '</div>%s</section>'
            % (VERSION, header(PLURAL[t]), label[0], label[1], quad(INDEX_DECK[t], "p", "argh-standfirst"),
               len(items), visual(PAGE_ILLUSTRATIONS[t], "argh-page-visual", "eager")))
    if t == "dossier":
        for place in store["places"]:
            grouped_items = store["dossiers_by_place"].get(place["id"], [])
            if grouped_items:
                group = {**place, "image": place.get("image") or PLACE_ILLUSTRATIONS.get(place["id"], PAGE_ILLUSTRATIONS["dossier"])}
                body += grouped_index_section(group, grouped_items)
    elif t == "pattern":
        for family in store["families"]:
            body += grouped_index_section(family, store["patterns_by_family"][family["id"]])
    else:
        for state in store["project_states"]:
            body += grouped_index_section(state, store["projects_by_state"][state["id"]])
    body += FOOT + "</main></div>"
    return page("%s — ARGH" % label[0], body, "%d %s publiés par ARGH." % (len(items), label[0].lower()))

def atlas(store):
    ds = [e for e in store["items"] if e.get("type") == "dossier"]
    pc, mc = {}, {}
    for e in ds:
        for p in (e.get("relationships") or {}).get("projects", []): pc[p] = pc.get(p, 0) + 1
        for m in (e.get("relationships") or {}).get("patterns", []): mc[m] = mc.get(m, 0) + 1
    ps = [k for k, _ in sorted(pc.items(), key=lambda x: -x[1])][:8]
    ms = [k for k, _ in sorted(mc.items(), key=lambda x: -x[1])][:16]
    title = {"fr": {"cuisine": "Mêmes postes. Des garanties différentes.", "expert": "Mêmes primitives. Garanties différentes."},
             "en": {"kitchen": "Same stations. Different guarantees.", "expert": "Same primitives. Different guarantees."}}
    deck = {"fr": {"cuisine": "Cette carte montre où les mêmes problèmes reviennent d’une cuisine à l’autre.",
                   "expert": "L’Atlas est dérivé du graphe public complet des entités ARGH."},
            "en": {"kitchen": "This map shows where the same problems recur across different kitchens.",
                   "expert": "The Atlas is derived from the complete public ARGH entity graph."}}
    families_title = {
        "fr": {"cuisine": "Dix familles de problèmes", "expert": "Dix familles transversales"},
        "en": {"kitchen": "Ten families of problems", "expert": "Ten cross-cutting families"}}
    families_deck = {
        "fr": {"cuisine": "Elles permettent de retrouver le même type de problème, quel que soit l’endroit où il s’est produit.",
               "expert": "Elles complètent les étapes du parcours en regroupant les mécanismes de défaillance comparables."},
        "en": {"kitchen": "They reveal the same kind of problem wherever it happened.",
               "expert": "They complement lifecycle stages by grouping comparable failure mechanisms."}}
    body = ('<div class="argh-site argh-atlas" data-argh-renderer="%s">%s'
            '<main class="argh-wrap"><section class="argh-index-hero argh-index-hero-illustrated">'
            '<div class="argh-index-hero-copy"><div class="argh-kicker">Atlas</div>%s%s</div>%s</section>'
            '<div class="argh-atlas-stats"><div class="argh-stat"><b>%d</b><span>Dossiers</span></div>'
            '<div class="argh-stat"><b>%d</b><span><span class="nav-fr">Projets</span><span class="nav-en">Projects</span></span></div>'
            '<div class="argh-stat"><b>%d</b><span><span class="nav-fr">Motifs</span><span class="nav-en">Patterns</span></span></div>'
            '<div class="argh-stat"><b>%d</b><span><span class="nav-fr">Familles</span><span class="nav-en">Families</span></span></div></div>'
            '<section class="argh-atlas-families">%s%s<div class="argh-family-grid">%s</div></section>'
            '<section class="argh-section"><div class="argh-atlas-wrap"><table class="argh-atlas-table"><thead><tr>'
            '<th><span class="nav-fr">Motif</span><span class="nav-en">Pattern</span></th>'
            % (VERSION, header("atlas"), quad(title, "h1"), quad(deck, "p", "argh-standfirst"),
               visual(PAGE_ILLUSTRATIONS["atlas"], "argh-page-visual", "eager"), len(ds),
               len([e for e in store["items"] if e.get("type") == "project"]), len(mc),
               len(store["families"]), quad(families_title, "h2"), quad(families_deck, "p"),
               "".join(
                   '<a class="argh-family-card" href="/patterns/#%s">%s<div>%s%s</div></a>'
                   % (esc(family["id"]), visual(family["image"], "argh-family-picture"),
                      quad(family["label"], "h3"), quad(family["description"], "p"))
                   for family in store["families"])))
    for p in ps: body += "<th>%s</th>" % esc(p)
    body += "</tr></thead><tbody>"
    for m in ms:
        h = pattern_heading(m, store)
        if not h: continue
        body += "<tr><td>%s</td>" % quad(h)
        for p in ps:
            n = sum(1 for e in ds
                    if p in ((e.get("relationships") or {}).get("projects") or [])
                    and m in ((e.get("relationships") or {}).get("patterns") or []))
            body += "<td>%s</td>" % ('<span class="argh-count">%d</span>' % n if n else "—")
        body += "</tr>"
    body += "</tbody></table></div></section>" + FOOT + "</main></div>"
    return page("Atlas — ARGH", body, "Carte des motifs récurrents entre projets.")

LATEST_N = 6

def entry_date(e):
    """Return the documented incident date only when it is evidence-backed."""
    return e.get("event_date") if e.get("date_basis") == "incident" else None

def sort_key(e):
    return (e.get("event_date") or "", e.get("updated_at") or "", e.get("slug") or "")

def card(e):
    h = slot_of(e, "hero")
    d = entry_date(e)
    meta = ('<div class="argh-card-meta"><time datetime="%s">%s</time></div>'
            % (esc(d), esc(d[:10]))) if d else ""
    return ('<a class="argh-index-card" href="%s">%s%s%s</a>'
            % (esc(e["route"]), meta, quad(h["heading"], "h2"),
               quad((h.get("body") or [{}])[0], "p", "argh-card-summary")))

def section_head(q):
    return '<div class="argh-section-head">%s</div>' % quad(q, "h2")

HOME_TITLE = {
    "fr": {"cuisine": "Comment les harnais d’agents travaillent, se trompent et s’améliorent.",
           "expert": "État des lieux et post-mortems des harnais d’agents."},
    "en": {"kitchen": "How agent harnesses work, make mistakes and improve.",
           "expert": "Agent harness landscape and post-mortems."}}

HOME_DECK = {
    "fr": {"cuisine": "ARGH observe l’usine à harnais. Chaque fiche raconte un incident réel comme un service de cuisine : ce qui s’est passé, ce que le raté a provoqué et comment le voir venir.",
           "expert": "ARGH cartographie les harnais d’agents. Chaque dossier documente un incident réel, ses preuves, son mécanisme, son impact et ses signaux précurseurs."},
    "en": {"kitchen": "ARGH watches the harness factory. Each card tells a real incident as a kitchen service: what happened, what the mistake caused and how to see it coming.",
           "expert": "ARGH maps agent harnesses. Each dossier documents a real incident, its evidence, mechanism, impact and leading signals."}}

HOME_IDENTITY_TITLE = {
    "fr": {"cuisine": "Ce que rassemble ARGH", "expert": "Ce que documente ARGH"},
    "en": {"kitchen": "What ARGH brings together", "expert": "What ARGH documents"}}

HOME_IDENTITY = [
    {"fr": {"cuisine": "Les harnais qui existent aujourd’hui", "expert": "La cartographie des harnais existants"},
     "en": {"kitchen": "The harnesses that exist today", "expert": "The current harness landscape"}},
    {"fr": {"cuisine": "Les erreurs rencontrées pendant le service", "expert": "Les incidents et mécanismes de défaillance"},
     "en": {"kitchen": "Mistakes encountered during service", "expert": "Incidents and failure mechanisms"}},
    {"fr": {"cuisine": "Les post-mortems qui expliquent pourquoi", "expert": "Les post-mortems fondés sur les preuves"},
     "en": {"kitchen": "Post-mortems that explain why", "expert": "Evidence-based post-mortems"}},
    {"fr": {"cuisine": "Les signes à surveiller avant la prochaine panne", "expert": "Les axes de surveillance et signaux précurseurs"},
     "en": {"kitchen": "Signs to watch before the next failure", "expert": "Monitoring axes and leading signals"}},
]

HOME_HARNESS_TITLE = {
    "fr": {"cuisine": "Un harnais, à quoi ça sert ?", "expert": "Comprendre le rôle d’un harnais d’agents"},
    "en": {"kitchen": "What is a harness for?", "expert": "Understand the role of an agent harness"}}

HOME_HARNESS_DECK = {
    "fr": {"cuisine": "Suivez une commande du ticket jusqu’à la table pour voir comment toute la cuisine tient ensemble.",
           "expert": "Suivez le parcours complet : entrée, orchestration, outils, exécution, validation, livraison et reprise."},
    "en": {"kitchen": "Follow an order from its ticket to the table and see how the whole kitchen holds together.",
           "expert": "Follow the complete path: input, orchestration, tools, execution, validation, delivery and recovery."}}

HOME_HARNESS_LINK = {
    "fr": {"cuisine": "Découvrir le harnais", "expert": "Voir le parcours expliqué"},
    "en": {"kitchen": "Discover the harness", "expert": "See the explained path"}}

HOME_LATEST = {
    "fr": {"cuisine": "Ce qui vient d’arriver", "expert": "Incidents nouveaux ou mis à jour"},
    "en": {"kitchen": "What just came in", "expert": "New or updated incidents"}}

HOME_LATEST_DECK = {
    "fr": {"cuisine": "Toute nouvelle histoire apparaît ici, même si la cuisine ne sait pas encore où la ranger.",
           "expert": "Tout nouvel incident apparaît ici, y compris lorsqu’aucun concept existant ne permet encore de le classer."},
    "en": {"kitchen": "Every new story appears here, even when the kitchen does not yet know where it belongs.",
           "expert": "Every new incident appears here, including when no existing concept can classify it yet."}}

HOME_MAP = {
    "fr": {"cuisine": "Explorer toute la cuisine", "expert": "Explorer tout le cycle"},
    "en": {"kitchen": "Explore the whole kitchen", "expert": "Explore the whole lifecycle"}}

HOME_MAP_DECK = {
    "fr": {"cuisine": "Toutes les fiches sont rangées du menu au cahier de la maison.",
           "expert": "Tous les dossiers sont classés de la définition à la traçabilité."},
    "en": {"kitchen": "Every card is arranged from the menu to the house notebook.",
           "expert": "Every dossier is classified from definition to traceability."}}

UNCLASSIFIED = {
    "fr": {"cuisine": "Sujets à ranger", "expert": "Incidents non classés"},
    "en": {"kitchen": "Stories to put away", "expert": "Unclassified incidents"}}

STATUS = {
    "new": {
        "fr": {"cuisine": "Nouvelle fiche", "expert": "Nouvel incident"},
        "en": {"kitchen": "New card", "expert": "New incident"}},
    "updated": {
        "fr": {"cuisine": "Fiche enrichie", "expert": "Dossier mis à jour"},
        "en": {"kitchen": "Expanded card", "expert": "Updated dossier"}},
    "recent": {
        "fr": {"cuisine": "À découvrir", "expert": "Incident récent"},
        "en": {"kitchen": "Discover", "expert": "Recent incident"}},
    "unclassified": {
        "fr": {"cuisine": "À ranger", "expert": "Incident non classé"},
        "en": {"kitchen": "To put away", "expert": "Unclassified incident"}},
}

UNCLASSIFIED_PLACE = {
    "fr": {"cuisine": "Visible dès son arrivée", "expert": "Taxonomie à réviser"},
    "en": {"kitchen": "Visible as soon as it arrives", "expert": "Taxonomy review required"}}

def latest_dossiers(store):
    """Return real activity first, then fill the initial baseline with recent incidents."""
    selected, seen = [], set()
    for event in store["activity"]:
        e = store["by_rel"].get(event["entity_path"])
        if not e or e.get("type") != "dossier" or e["slug"] in seen:
            continue
        selected.append((e, event))
        seen.add(e["slug"])
        if len(selected) == LATEST_N:
            return selected
    dossiers = sorted(
        [e for e in store["items"] if e.get("type") == "dossier"],
        key=sort_key,
        reverse=True,
    )
    for e in dossiers:
        if e["slug"] in seen:
            continue
        selected.append((e, {"kind": "recent", "detected_at": e.get("updated_at") or e.get("event_date") or ""}))
        seen.add(e["slug"])
        if len(selected) == LATEST_N:
            break
    return selected


def update_card(e, event, store):
    h = slot_of(e, "hero")
    place_id = store["assignments"].get(e["slug"])
    place = store["place_by_id"].get(place_id)
    unclassified = place is None
    kind = event.get("kind", "recent") if isinstance(event, dict) else str(event)
    status = STATUS["unclassified" if unclassified else kind]
    location = place["label"] if place else UNCLASSIFIED_PLACE
    classes = "argh-update-card" + (" argh-unclassified" if unclassified else "")
    detected = (event.get("detected_at") or "") if isinstance(event, dict) else ""
    published_date = detected[:10] if detected else ""
    incident_date = entry_date(e)
    dates = ""
    if published_date:
        dates += '<span class="argh-update-date"><span class="nav-fr">%s le %s</span><span class="nav-en">%s %s</span></span>' % (
            "Nouveau" if kind == "new" else ("Mis à jour" if kind == "updated" else "Publié"),
            esc(published_date),
            "New" if kind == "new" else ("Updated" if kind == "updated" else "Published"),
            esc(published_date),
        )
    if incident_date and incident_date != published_date:
        dates += '<span class="argh-incident-date"><span class="nav-fr">Incident du %s</span><span class="nav-en">Incident %s</span></span>' % (
            esc(incident_date), esc(incident_date))
    date_meta = '<div class="argh-update-dates">%s</div>' % dates if dates else ""
    return ('<a class="%s" href="%s">%s%s%s%s%s</a>'
            % (classes, esc(e["route"]), quad(status, "span", "argh-update-status"),
               quad(location, "span", "argh-update-place"), date_meta,
               quad(h["heading"], "h3"),
               quad((h.get("body") or [{}])[0], "p")))


def place_card(place, number, store):
    dossiers = store["dossiers_by_place"].get(place["id"], [])
    illustration = place.get("image") or PLACE_ILLUSTRATIONS.get(place["id"], PAGE_ILLUSTRATIONS["dossier"])
    classes = "argh-place-card" + (" argh-place-card-illustrated" if illustration else "")
    picture = (
        '<picture class="argh-place-card-picture"><img src="%s" width="320" height="213" '
        'alt="" aria-hidden="true" loading="lazy" decoding="async"></picture>' % esc(illustration)
        if illustration else ""
    )
    count = {
        "fr": {"cuisine": "%d fiche%s" % (len(dossiers), "s" if len(dossiers) != 1 else ""),
               "expert": "%d dossier%s" % (len(dossiers), "s" if len(dossiers) != 1 else "")},
        "en": {"kitchen": "%d card%s" % (len(dossiers), "s" if len(dossiers) != 1 else ""),
               "expert": "%d dossier%s" % (len(dossiers), "s" if len(dossiers) != 1 else "")},
    }
    return ('<a class="%s" data-number="%02d" href="/places/%s/">'
            '<span class="argh-place-number">%02d</span>%s%s%s%s</a>'
            % (classes, number, esc(place["id"]), number, picture, quad(place["label"], "h3"),
               quad(place["description"], "p"), quad(count, "span", "argh-place-count")))


def place_page(place, store):
    items = store["dossiers_by_place"].get(place["id"], [])
    illustration = place.get("image") or PLACE_ILLUSTRATIONS.get(place["id"], PAGE_ILLUSTRATIONS["dossier"])
    hero_class = " argh-place-hero-illustrated" if illustration else ""
    picture = (
        '<picture class="argh-place-hero-illustration"><img src="%s" width="320" height="213" '
        'alt="" aria-hidden="true" decoding="async"></picture>' % esc(illustration)
        if illustration else ""
    )
    body = ('<div class="argh-site argh-index" data-argh-renderer="%s">%s'
            '<main class="argh-wrap"><section class="argh-index-hero%s"><div class="argh-place-hero-copy">'
            '<div class="argh-kicker"><a href="/">ARGH</a> · <span class="nav-fr">Carte</span><span class="nav-en">Map</span></div>'
            '%s%s%s<div class="argh-index-count">%d <span class="nav-fr">dossiers</span><span class="nav-en">dossiers</span></div>'
            '</div>%s</section><section class="argh-index-grid">%s</section>%s</main></div>'
            % (VERSION, header("home"), hero_class, quad(place["label"], "h1"),
               quad(place["description"], "p", "argh-standfirst"),
               quad(place["meaning"], "p", "argh-place-meaning"), len(items), picture,
               "".join(card(e) for e in items), FOOT))
    return page("%s — ARGH" % place["label"]["fr"]["expert"], body,
                place["description"]["fr"]["expert"])


def home(store):
    body = ('<div class="argh-site argh-index" data-argh-renderer="%s">%s'
            '<main class="argh-wrap">'
            '<section class="argh-home-hero"><div class="argh-home-intro"><div class="argh-kicker">ARGH — Agent Reliability &amp; Guard for Harnesses</div>%s%s</div>'
            '<picture class="argh-home-illustration">'
            '<source srcset="/assets/illustrations/kitchen-system-home-480.jpg 480w, '
            '/assets/illustrations/kitchen-system-home-960.jpg 960w" '
            'sizes="(max-width:700px) calc(100vw - 34px), (max-width:920px) 42vw, 260px">'
            '<img src="/assets/illustrations/kitchen-system-home-480.jpg" width="480" height="320" '
            'alt="" aria-hidden="true" decoding="async" fetchpriority="high"></picture>'
            '<aside class="argh-home-identity">%s<ul>%s</ul></aside></section>'
            % (VERSION, header("home"), quad(HOME_TITLE, "h1"),
               quad(HOME_DECK, "p", "argh-standfirst"), quad(HOME_IDENTITY_TITLE, "strong"),
               "".join(quad(item, "li") for item in HOME_IDENTITY)))

    body += ('<a class="argh-harness-callout" href="/harness/">'
             '<picture><img src="/assets/illustrations/category-roles-orchestration-320.jpg" '
             'width="320" height="213" alt="" aria-hidden="true" loading="lazy" decoding="async"></picture>'
             '<div>%s%s<span class="argh-harness-callout-link">%s <span aria-hidden="true">→</span></span></div></a>'
             % (quad(HOME_HARNESS_TITLE, "h2"), quad(HOME_HARNESS_DECK, "p"),
                quad(HOME_HARNESS_LINK)))

    body += ('<section class="argh-updates"><div class="argh-updates-head"><div>%s</div>%s</div>'
             '<div class="argh-update-grid">%s</div></section>'
             % (quad(HOME_LATEST, "h2"), quad(HOME_LATEST_DECK, "p"),
                "".join(update_card(e, event, store) for e, event in latest_dossiers(store))))

    if store["unclassified"]:
        body += ('<section class="argh-unclassified-section">%s<div class="argh-update-grid">%s</div></section>'
                 % (section_head(UNCLASSIFIED),
                    "".join(update_card(e, {"kind": "recent", "detected_at": e.get("updated_at") or ""}, store) for e in store["unclassified"])))

    body += ('<section class="argh-map"><div class="argh-map-intro">%s%s</div>'
             % (quad(HOME_MAP, "h2"), quad(HOME_MAP_DECK, "p")))
    number = 1
    for phase in store["phases"]:
        body += '<div class="argh-phase-head">%s%s</div><div class="argh-place-grid">' % (
            quad(phase["label"], "h3"), quad(phase["description"], "p"))
        for place in [p for p in store["places"] if p["phase"] == phase["id"]]:
            body += place_card(place, number, store)
            number += 1
        body += "</div>"
    body += "</section>"

    body += FOOT + "</main></div>"
    return page("ARGH — État des lieux et post-mortems des harnais d’agents", body,
                "État des lieux, incidents, post-mortems et signaux à surveiller pour les harnais d’agents.")

def about(store):
    blk = (ROOT / "recovered" / "about.html").read_text(encoding="utf-8")
    body = ('<div class="argh-site" data-argh-renderer="%s">%s'
            '<main class="argh-wrap">%s</main>%s</div>' % (VERSION, header("about"), blk, FOOT))
    return page("À propos — ARGH", body, "Ce qu'est ARGH et comment ses dossiers sont établis.")


def harness(store):
    blk = (ROOT / "recovered" / "harness.html").read_text(encoding="utf-8")
    body = ('<div class="argh-site" data-argh-renderer="%s">%s'
            '<main class="argh-wrap">%s</main>%s</div>' % (VERSION, header("harness"), blk, FOOT))
    return page("Un harnais, à quoi ça sert ? — ARGH", body,
                "Le parcours illustré d’un harnais d’agents, de la demande au résultat livré.")


def glossary_column(place, reader):
    fr_key, en_key = ("cuisine", "kitchen") if reader == "kitchen" else ("expert", "expert")
    label = place["label"]
    description = place["description"]
    meaning = place["meaning"]
    heading = "Cuisine" if reader == "kitchen" else "Expert"
    return ('<article class="argh-glossary-column argh-glossary-%s">'
            '<div class="argh-glossary-reader">%s</div>'
            '<h3><span class="nav-fr">%s</span><span class="nav-en">%s</span></h3>'
            '<p class="argh-glossary-summary"><span class="nav-fr">%s</span><span class="nav-en">%s</span></p>'
            '<p><span class="nav-fr">%s</span><span class="nav-en">%s</span></p></article>'
            % (reader, heading, esc(label["fr"][fr_key]), esc(label["en"][en_key]),
               esc(description["fr"][fr_key]), esc(description["en"][en_key]),
               esc(meaning["fr"][fr_key]), esc(meaning["en"][en_key])))


def glossary(store):
    entries = []
    for number, place in enumerate(store["places"], 1):
        illustration = place.get("image") or PLACE_ILLUSTRATIONS.get(place["id"], PAGE_ILLUSTRATIONS["dossier"])
        picture = ('<picture class="argh-glossary-picture"><img src="%s" width="320" height="213" '
                   'alt="" aria-hidden="true" loading="lazy" decoding="async"></picture>'
                   % esc(illustration))
        entries.append(
            '<section class="argh-glossary-entry" id="%s">'
            '<div class="argh-glossary-entry-head"><div class="argh-glossary-marker"><span>%02d</span>%s</div>'
            '<a href="/places/%s/"><span class="nav-fr">Voir les dossiers</span>'
            '<span class="nav-en">View dossiers</span></a></div>'
            '<div class="argh-glossary-pair">%s%s</div></section>'
            % (esc(place["id"]), number, picture, esc(place["id"]),
               glossary_column(place, "kitchen"), glossary_column(place, "expert"))
        )
    body = ('<div class="argh-site argh-index" data-argh-renderer="%s">%s'
            '<main class="argh-wrap"><section class="argh-index-hero argh-glossary-hero">'
            '<div class="argh-kicker">ARGH</div>'
            '<h1><span class="nav-fr">Glossaire Cuisine ↔ Expert</span>'
            '<span class="nav-en">Kitchen ↔ Expert glossary</span></h1>'
            '<p class="argh-standfirst"><span class="nav-fr">Chaque catégorie est expliquée côte à côte : '
            'l’image de cuisine à gauche, sa signification technique exacte à droite.</span>'
            '<span class="nav-en">Every category is explained side by side: the kitchen image on the left, '
            'its exact technical meaning on the right.</span></p></section>%s%s</main></div>'
            % (VERSION, header("glossary"), "".join(entries), FOOT))
    return page("Glossaire — ARGH", body, "Correspondance entre les catégories Cuisine et Expert d’ARGH.")


def load_navigation(store):
    taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    if taxonomy.get("schema") != "argh/public-navigation/v1":
        raise ValueError("wrong public navigation schema")
    phases, places = taxonomy.get("phases"), taxonomy.get("places")
    assignments = taxonomy.get("assignments")
    if not isinstance(phases, list) or not isinstance(places, list) or not isinstance(assignments, dict):
        raise ValueError("public navigation must contain phases, places and assignments")
    phase_ids = [phase.get("id") for phase in phases]
    place_ids = [place.get("id") for place in places]
    if len(set(phase_ids)) != len(phase_ids) or len(set(place_ids)) != len(place_ids):
        raise ValueError("duplicate public navigation id")
    if any(place.get("phase") not in phase_ids for place in places):
        raise ValueError("public navigation place references an unknown phase")
    if any(place_id not in place_ids for place_id in assignments.values()):
        raise ValueError("public navigation assignment references an unknown place")

    visual_taxonomy = json.loads(VISUAL_TAXONOMY.read_text(encoding="utf-8"))
    if visual_taxonomy.get("schema") != "argh/visual-taxonomy/v1":
        raise ValueError("wrong visual taxonomy schema")
    families = visual_taxonomy.get("families")
    pattern_assignments = visual_taxonomy.get("pattern_assignments")
    project_states = visual_taxonomy.get("project_states")
    project_state_assignments = visual_taxonomy.get("project_state_assignments")
    if not isinstance(families, list) or not isinstance(pattern_assignments, dict):
        raise ValueError("visual taxonomy must contain families and pattern assignments")
    if not isinstance(project_states, list) or not isinstance(project_state_assignments, dict):
        raise ValueError("visual taxonomy must contain project states and assignments")
    family_ids = [family.get("id") for family in families]
    project_state_ids = [state.get("id") for state in project_states]
    if len(set(family_ids)) != len(family_ids) or len(set(project_state_ids)) != len(project_state_ids):
        raise ValueError("duplicate visual taxonomy id")
    if any(family_id not in family_ids for family_id in pattern_assignments.values()):
        raise ValueError("pattern assignment references an unknown family")
    if any(state_id not in project_state_ids for state_id in project_state_assignments.values()):
        raise ValueError("project assignment references an unknown state")

    dossiers = {e["slug"]: e for e in store["items"] if e.get("type") == "dossier"}
    patterns = {e["slug"]: e for e in store["items"] if e.get("type") == "pattern"}
    projects = {e["slug"]: e for e in store["items"] if e.get("type") == "project"}
    unknown_patterns = set(pattern_assignments) - set(patterns)
    unknown_projects = set(project_state_assignments) - set(projects)
    if unknown_patterns:
        raise ValueError("pattern assignments reference unknown entities")
    if unknown_projects:
        raise ValueError("project assignments reference unknown entities")

    missing_dossiers = set(dossiers) - set(assignments)
    if missing_dossiers:
        fallback = {
            "id": "unclassified-dossiers",
            "phase": phases[-1]["id"],
            "image": PAGE_ILLUSTRATIONS["dossier"],
            "label": UNCLASSIFIED,
            "description": {
                "fr": {"cuisine": "Ces histoires restent visibles pendant que la bonne place est choisie.",
                       "expert": "Ces incidents restent publiés en attente d’une classification éditoriale."},
                "en": {"kitchen": "These stories remain visible while the right place is chosen.",
                       "expert": "These incidents remain published pending editorial classification."}},
            "meaning": {
                "fr": {"cuisine": "La fiche est servie, mais son rangement doit encore être décidé.",
                       "expert": "Le contenu est public ; seule son affectation taxonomique reste ouverte."},
                "en": {"kitchen": "The card is served, but its shelf still has to be chosen.",
                       "expert": "The content is public; only its taxonomic assignment remains open."}},
        }
        places.append(fallback)
        place_ids.append(fallback["id"])

    missing_patterns = set(patterns) - set(pattern_assignments)
    if missing_patterns:
        fallback = {
            "id": "unclassified-patterns",
            "image": PAGE_ILLUSTRATIONS["pattern"],
            "label": UNCLASSIFIED,
            "description": {
                "fr": {"cuisine": "Ces problèmes restent visibles pendant que la bonne famille est choisie.",
                       "expert": "Ces mécanismes restent publiés en attente d’une classification éditoriale."},
                "en": {"kitchen": "These problems remain visible while the right family is chosen.",
                       "expert": "These mechanisms remain published pending editorial classification."}},
        }
        families.append(fallback)
        family_ids.append(fallback["id"])
        pattern_assignments = dict(pattern_assignments)
        pattern_assignments.update({slug: fallback["id"] for slug in missing_patterns})

    missing_projects = set(projects) - set(project_state_assignments)
    if missing_projects:
        fallback = {
            "id": "unclassified-projects",
            "image": PAGE_ILLUSTRATIONS["project"],
            "label": UNCLASSIFIED,
            "description": {
                "fr": {"cuisine": "Ces maisons restent visibles tant que leur situation n’est pas assez claire.",
                       "expert": "Ces systèmes restent publiés en attente d’un état de cycle de vie documenté."},
                "en": {"kitchen": "These houses remain visible until their situation is clear enough.",
                       "expert": "These systems remain published pending a documented lifecycle state."}},
        }
        project_states.append(fallback)
        project_state_ids.append(fallback["id"])
        project_state_assignments = dict(project_state_assignments)
        project_state_assignments.update({slug: fallback["id"] for slug in missing_projects})
    dossiers_by_place = {place_id: [] for place_id in place_ids}
    for slug, place_id in assignments.items():
        if slug in dossiers:
            dossiers_by_place[place_id].append(dossiers[slug])
    if missing_dossiers:
        dossiers_by_place["unclassified-dossiers"] = [dossiers[slug] for slug in missing_dossiers]
    for items in dossiers_by_place.values():
        items.sort(key=sort_key, reverse=True)

    patterns_by_family = {family_id: [] for family_id in family_ids}
    for slug, family_id in pattern_assignments.items():
        patterns_by_family[family_id].append(patterns[slug])
    for items in patterns_by_family.values():
        items.sort(key=lambda entity: entity["slug"])

    projects_by_state = {state_id: [] for state_id in project_state_ids}
    for slug, state_id in project_state_assignments.items():
        projects_by_state[state_id].append(projects[slug])
    for items in projects_by_state.values():
        items.sort(key=lambda entity: entity["slug"])

    activity = json.loads(ACTIVITY.read_text(encoding="utf-8"))
    if activity.get("schema") != "argh/public-activity/v1" or not isinstance(activity.get("events"), list):
        raise ValueError("wrong public activity schema")

    store.update({
        "phases": phases,
        "places": places,
        "place_by_id": {place["id"]: place for place in places},
        "assignments": assignments,
        "dossiers_by_place": dossiers_by_place,
        "families": families,
        "family_by_id": {family["id"]: family for family in families},
        "pattern_assignments": pattern_assignments,
        "patterns_by_family": patterns_by_family,
        "project_states": project_states,
        "project_state_by_id": {state["id"]: state for state in project_states},
        "project_state_assignments": project_state_assignments,
        "projects_by_state": projects_by_state,
        "unclassified": sorted(
            [entity for slug, entity in dossiers.items() if slug not in assignments],
            key=sort_key,
            reverse=True,
        ),
        "activity": activity["events"],
    })


def main():
    idx = json.loads((DATA / "index.json").read_text(encoding="utf-8"))
    store = {"items": [], "by_route": {}, "by_rel": {}, "patterns": {}}
    for rel in sorted(idx["entries"]):
        e = json.loads((DATA / rel).read_text(encoding="utf-8"))
        store["items"].append(e); store["by_route"][e["route"]] = e; store["by_rel"][rel] = e
        if e["type"] == "pattern": store["patterns"][e["slug"]] = e
    load_navigation(store)
    # Generated entity routes mirror the complete store. Remove stale routes before
    # rendering so a deleted entity cannot survive on GitHub Pages.
    for plural in PLURAL.values():
        shutil.rmtree(ROOT / plural, ignore_errors=True)
        (ROOT / plural).mkdir()
    n = 0
    for e in store["items"]:
        out = ROOT / PLURAL[e["type"]] / e["slug"] / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(detail(e, store), encoding="utf-8"); n += 1
    for t in ("dossier", "project", "pattern"):
        (ROOT / PLURAL[t] / "index.html").write_text(index(t, store), encoding="utf-8")
    shutil.rmtree(ROOT / "places", ignore_errors=True)
    (ROOT / "places").mkdir()
    for place in store["places"]:
        out = ROOT / "places" / place["id"] / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(place_page(place, store), encoding="utf-8")
    (ROOT / "atlas").mkdir(exist_ok=True)
    (ROOT / "atlas" / "index.html").write_text(atlas(store), encoding="utf-8")
    (ROOT / "index.html").write_text(home(store), encoding="utf-8")
    (ROOT / "about").mkdir(exist_ok=True)
    (ROOT / "about" / "index.html").write_text(about(store), encoding="utf-8")
    (ROOT / "harness").mkdir(exist_ok=True)
    (ROOT / "harness" / "index.html").write_text(harness(store), encoding="utf-8")
    (ROOT / "glossary").mkdir(exist_ok=True)
    (ROOT / "glossary" / "index.html").write_text(glossary(store), encoding="utf-8")
    (ROOT / "404.html").write_text(page("404 — ARGH",
        '<div class="argh-site">%s<main class="argh-wrap"><article class="argh-article">'
        '<h1>404</h1><p class="argh-standfirst">Cette page n’existe pas.</p>'
        '<div class="argh-chips"><a class="argh-chip" href="/dossiers/">Dossiers</a>'
        '<a class="argh-chip" href="/patterns/">Motifs</a><a class="argh-chip" href="/projects/">Projets</a></div>'
        '</article>%s</main></div>' % (header(), FOOT)), encoding="utf-8")
    print("  %d pages d'entité + %d endroits + 3 index + atlas + harnais + glossaire + accueil + 404" %
          (n, len(store["places"])))

if __name__ == "__main__":
    main()
