# Bonus Reports Platform

A publishing platform for H Heuristics research output: reports, dashboards, datasets, and experimental projects. Built for **mass production** — every project ships with a fixed metadata schema, structured data, and machine-readable indexes so search engines, scholars, and machines can find it.

- **Repo:** `github.com/Hunterhghs/Bonus-reports-platform`
- **Deploy:** Cloudflare Pages (static, no server)
- **Aesthetic:** professional economist / consultant editorial (paper, ink, oxblood, brass, hairlines)
- **Pipeline:** Veles (Fable-5 × DeepSeek) discipline — bootstrap → build → verify → push

## Repository layout

```
build.py                    # static-site generator (Python 3, stdlib)
site/style.css              # editorial design system
site/app.js                 # catalog filtering (vanilla JS)
projects/<slug>/project.json  # metadata for ONE project (the source of truth)
projects/<slug>/content.md    # optional rendered prose body
projects/<slug>/<file>        # PDF / HTML / images referenced in project.json
projects.json               # generated machine-readable index (in dist/)
dist/                       # generated site — committed so Pages can serve it directly
new_project.py              # scaffolds a new project folder from the CLI
```

## How a project is added (the workflow)

1. A document or dashboard is dropped into the workspace (e.g. a PDF attachment).
2. The agent creates `projects/<slug>/` with:
   - `project.json` — full metadata (see schema below)
   - `content.md` — English summary prose, drafted through the `english-report-writing` skill and linted with `prose_lint.py`
   - the source file(s), copied with a URL-safe filename
3. `python3 build.py` regenerates `dist/`.
4. The agent verifies (HTML validity, internal links, JSON-LD parses, feeds parse, PDF present) and pushes to `main`.
5. Cloudflare Pages rebuilds on push (or serves the committed `dist/` as-is).

To scaffold the next project by hand:

```bash
python3 new_project.py "Air Pollution and the Atmospheric Pollution Cycle" --type report
```

## Metadata schema (`project.json`)

| Field | Required | Notes |
|-------|----------|-------|
| `slug` | ✓ | URL-safe id, matches folder name |
| `title` | ✓ | headline |
| `subtitle` | | secondary line |
| `type` | ✓ | `report` \| `dashboard` \| `project` \| `dataset` |
| `status` | | `published` (default) or `draft` |
| `featured` | | boolean, future carousel use |
| `date` / `dateLabel` | ✓ | ISO date + display label |
| `authors[]` | | `name`, `role`, `org` |
| `description` | ✓ | ≤160 chars, used for SEO/meta |
| `abstract` | | 1–2 paragraph summary |
| `keywords[]` | | SEO keywords |
| `tags[]` | | short classifier tags (chips) |
| `categories[]` | | thematic buckets |
| `series` | | imprint/series label |
| `language` | | ISO code, default `en` |
| `license` | | distribution terms |
| `pages` / `chapters` / `exhibits` / `tables` / `citations` | | report specs |
| `figures[]` | | `value` + `caption` key-figure cards |
| `chapterOutline[]` | | `chapter`, `title`, `focus` |
| `files[]` | | `path`, `label`, `kind`, `size` — copied next to the page |
| `external[]` | | external links |
| `bindingTerm` | | closing methodological directive |

Every field flows into the generated page: SEO tags, Open Graph, Twitter cards, JSON-LD (`WebSite`, `ItemList`, `Report`, `BreadcrumbList`), `sitemap.xml`, `rss.xml`, and `projects.json`.

## Build & deploy

```bash
python3 build.py               # build dist/
python3 build.py --check       # validate metadata only
python3 build.py --include-drafts
```

**Cloudflare Pages settings**

| Setting | Value |
|---------|-------|
| Framework preset | None |
| Build command | `python3 build.py` |
| Build output directory | `dist` |

The committed `dist/` also works with **no build command** if you just point the output directory at `dist`. `_headers` ships security headers, PDF caching, and CORS for `projects.json`.

After the custom domain is known, update `SITE_URL` in `build.py` and rebuild — canonical URLs, sitemap, and JSON-LD all derive from it.

## First project

**Air Pollution and the Atmospheric Pollution Cycle** — 40-page H Heuristics strategic monograph (Polycrisis Series, October 2026). Fourteen chapters trace the atmospheric pollution cycle from PM2.5 physics to a phased 2026–2040 clean-air roadmap ($1.96T, 38.2M avoided mortalities).
