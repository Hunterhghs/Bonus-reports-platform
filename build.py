#!/usr/bin/env python3
"""
Bonus Reports Platform — static site builder.

Reads projects/*/project.json (+ optional content.md and binary files),
renders a metadata-rich static catalog into dist/ for Cloudflare Pages.

Usage:
    python3 build.py                 # build all published projects
    python3 build.py --include-drafts
    python3 build.py --check          # validate metadata only, no write

Design: professional economist / consultant editorial aesthetic.
Metadata: per-project SEO tags, Open Graph, Twitter cards, JSON-LD
(WebSite, ItemList, Report, BreadcrumbList), sitemap.xml, robots.txt,
projects.json index, rss.xml.
"""
import html
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
PROJECTS = ROOT / "projects"
DIST = ROOT / "dist"

# ---------------------------------------------------------------------------
# Site configuration (edit SITE_URL when the custom domain is known)
# ---------------------------------------------------------------------------
SITE_NAME = "Bonus Reports Platform"
SITE_TAGLINE = "Reports, dashboards, and experimental projects from H Heuristics"
SITE_URL = "https://bonus-reports.pages.dev"
ORG_NAME = "H Heuristics"
ORG_URL = "https://hheuristics.com"
ORG_SAMEAS = [
    "https://github.com/Hunterhghs",
    "https://hheuristics.com",
]

TYPES = {
    "report": "Report",
    "dashboard": "Dashboard",
    "project": "Project",
    "dataset": "Dataset",
}

REQUIRED_FIELDS = ["slug", "title", "type", "date", "description"]


# ---------------------------------------------------------------------------
# Loading & validation
# ---------------------------------------------------------------------------
def load_projects(include_drafts=False):
    projects = []
    if not PROJECTS.exists():
        return projects
    for meta_path in sorted(PROJECTS.glob("*/project.json")):
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"  ✗ invalid JSON in {meta_path}: {exc}")
            sys.exit(1)
        folder = meta_path.parent
        slug = data.get("slug") or folder.name
        data["slug"] = slug
        data.setdefault("status", "published")
        if data["status"] != "published" and not include_drafts:
            continue
        missing = [f for f in REQUIRED_FIELDS if not data.get(f)]
        if missing:
            print(f"  ✗ {meta_path}: missing fields {missing}")
            sys.exit(1)
        if data.get("type") not in TYPES:
            print(f"  ✗ {meta_path}: unknown type {data.get('type')!r}")
            sys.exit(1)
        data["_dir"] = folder
        projects.append(data)
    projects.sort(key=lambda p: (p.get("date") or "0000"), reverse=True)
    return projects


# ---------------------------------------------------------------------------
# Minimal markdown renderer (headings, paragraphs, lists, quotes, inline)
# ---------------------------------------------------------------------------
INLINE_RE = [
    (re.compile(r"\*\*(.+?)\*\*"), r"<strong>\1</strong>"),
    (re.compile(r"\*(.+?)\*"), r"<em>\1</em>"),
    (re.compile(r"`(.+?)`"), r"<code>\1</code>"),
    (re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)"),
     r'<a href="\2" target="_blank" rel="noopener">\1</a>'),
]


def _inline(text):
    text = html.escape(text, quote=False)
    for pattern, repl in INLINE_RE:
        text = pattern.sub(repl, text)
    return text


def markdown_to_html(md_text):
    out = []
    in_list = False
    for raw in md_text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            if in_list:
                out.append("</ul>")
                in_list = False
            continue
        if line.startswith("### "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h3>{_inline(line[4:])}</h3>")
        elif line.startswith("## "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h2>{_inline(line[3:])}</h2>")
        elif line.startswith("# "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h2 class=\"lede-heading\">{_inline(line[2:])}</h2>")
        elif line.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{_inline(line[2:])}</li>")
        elif line.startswith("> "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<blockquote>{_inline(line[2:])}</blockquote>")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<p>{_inline(line)}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def read_markdown(p):
    md = p["_dir"] / "content.md"
    if md.exists():
        return markdown_to_html(md.read_text(encoding="utf-8"))
    if p.get("abstract"):
        return f"<p>{html.escape(p['abstract'])}</p>"
    return ""


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------
def esc(value):
    return html.escape(str(value), quote=True)


def meta_page(title, description, canonical, og_type="website", extra=""):
    og = "\n".join(
        [
            f'    <meta property="og:title" content="{esc(title)}">',
            f'    <meta property="og:description" content="{esc(description)}">',
            f'    <meta property="og:url" content="{esc(canonical)}">',
            f'    <meta property="og:site_name" content="{esc(SITE_NAME)}">',
            f'    <meta property="og:type" content="{og_type}">',
        ]
    )
    twitter = "\n".join(
        [
            '    <meta name="twitter:card" content="summary_large_image">',
            f'    <meta name="twitter:title" content="{esc(title)}">',
            f'    <meta name="twitter:description" content="{esc(description)}">',
        ]
    )
    return (
        f'    <title>{esc(title)}</title>\n'
        f'    <meta charset="utf-8">\n'
        f'    <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'    <meta name="description" content="{esc(description)}">\n'
        f'    <link rel="canonical" href="{esc(canonical)}">\n'
        f'    <meta name="robots" content="index, follow">\n'
        f'    <meta name="generator" content="bonus-reports-platform build.py">\n'
        f"{og}\n"
        f"{twitter}\n"
        f'    <link rel="preconnect" href="https://fonts.googleapis.com">\n'
        f'    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        f'    <link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">\n'
        f"{extra}"
    )


def nav_html(active=""):
    tabs = [("all", "All"), ("report", "Reports"), ("dashboard", "Dashboards"),
            ("project", "Projects"), ("dataset", "Datasets")]
    items = []
    for key, label in tabs:
        cls = ' class="active"' if key == active else ""
        href = "/" if key == "all" else f"/?type={key}"
        items.append(f'<a href="{href}"{cls} data-nav="{key}">{label}</a>')
    return (
        '<header class="masthead">\n'
        '  <div class="masthead-inner">\n'
        '    <a class="brand" href="/">\n'
        '      <span class="brand-org">H HEURISTICS</span>\n'
        '      <span class="brand-name">Bonus Reports Platform</span>\n'
        '    </a>\n'
        f'    <nav class="site-nav" aria-label="Primary">{"".join(items)}</nav>\n'
        "  </div>\n"
        "</header>"
    )


def footer_html():
    return (
        '<footer class="site-footer">\n'
        "  <div class=\"footer-inner\">\n"
        "    <div>\n"
        "      <p class=\"footer-brand\">H HEURISTICS · BONUS REPORTS PLATFORM</p>\n"
        f"      <p>{esc(SITE_TAGLINE)}. Built for mass publication: every project ships with "
        "SEO metadata, structured data, and machine-readable indexes.</p>\n"
        "    </div>\n"
        "    <div class=\"footer-links\">\n"
        f'      <a href="{ORG_URL}" target="_blank" rel="noopener">hheuristics.com</a>\n'
        '      <a href="https://github.com/Hunterhghs/Bonus-reports-platform" target="_blank" rel="noopener">GitHub repository</a>\n'
        f'      <a href="{SITE_URL}/sitemap.xml">Sitemap</a>\n'
        f'      <a href="{SITE_URL}/rss.xml">RSS</a>\n'
        "    </div>\n"
        "  </div>\n"
        "</footer>"
    )


def jsonld_script(obj):
    return (
        '<script type="application/ld+json">\n'
        f"{json.dumps(obj, ensure_ascii=False, indent=2)}\n"
        "</script>"
    )


def organization_ld():
    return {
        "@type": "Organization",
        "name": ORG_NAME,
        "url": ORG_URL,
        "sameAs": ORG_SAMEAS,
    }


def base_page(title, description, canonical, body, ld_objects, og_type="website", extra_head="", nav_active="all"):
    css = (SITE / "style.css").read_text(encoding="utf-8")
    js = (SITE / "app.js").read_text(encoding="utf-8")
    ld = [{"@context": "https://schema.org", **o} for o in ld_objects]
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        f"{meta_page(title, description, canonical, og_type, extra_head)}\n"
        f'<style>\n{css}\n</style>\n'
        f"{jsonld_script(ld)}\n"
        "</head>\n"
        "<body>\n"
        f"{nav_html(nav_active)}\n"
        f"{body}\n"
        f"{footer_html()}\n"
        f"<script>\n{js}\n</script>\n"
        "</body>\n"
        "</html>\n"
    )


# ---------------------------------------------------------------------------
# Page renderers
# ---------------------------------------------------------------------------
def type_eyebrow(p):
    return TYPES.get(p["type"], "Project")


def tags_html(p):
    tags = p.get("tags") or []
    if not tags:
        return ""
    chips = "".join(f'<span class="chip" data-tag="{esc(t)}">{esc(t)}</span>' for t in tags)
    return f'<div class="chips">{chips}</div>'


def meta_line(p):
    parts = [esc(p.get("dateLabel") or p["date"])]
    if p.get("series"):
        parts.append(esc(p["series"]))
    return " · ".join(parts)


def card_html(p):
    url = f"/projects/{p['slug']}/"
    pages = p.get("pages")
    detail = []
    if p["type"] == "report" and pages:
        detail.append(f"{pages} pages")
    if p.get("chapters") and p["type"] == "report":
        detail.append(f"{p['chapters']} chapters")
    detail_str = f'<span class="card-detail">{" · ".join(esc(d) for d in detail)}</span>' if detail else ""
    return (
        f'<article class="card" data-type="{esc(p["type"])}" data-date="{esc(p["date"])}" '
        f'data-search="{esc((p["title"] + " " + (p.get("subtitle") or "") + " " + " ".join(p.get("tags") or []) + " " + " ".join(p.get("keywords") or [])).lower())}">\n'
        f'  <a class="card-link" href="{url}">\n'
        f'    <span class="eyebrow">{type_eyebrow(p)}</span>\n'
        f'    <h3 class="card-title">{esc(p["title"])}</h3>\n'
        f'    <p class="card-meta">{meta_line(p)} {detail_str}</p>\n'
        f'    <p class="card-desc">{esc(p.get("description") or "")}</p>\n'
        f'  </a>\n'
        f'{tags_html(p)}\n'
        "</article>"
    )


def home_body(projects, include_drafts=False):
    counts = {"all": len(projects)}
    for t in TYPES:
        counts[t] = sum(1 for p in projects if p["type"] == t)
    cards = "\n".join(card_html(p) for p in projects)
    types_json = json.dumps(TYPES, ensure_ascii=False)
    return (
        '<main class="home">\n'
        '  <section class="hero">\n'
        '    <p class="eyebrow">H HEURISTICS · OPEN RESEARCH OUTPUT</p>\n'
        f'    <h1>{esc(SITE_NAME)}</h1>\n'
        f'    <p class="hero-sub">{esc(SITE_TAGLINE)}. Each entry carries full metadata so reports, '
        "dashboards, and projects stay indexable by search engines, scholars, and machines.</p>\n"
        '    <div class="hero-stats" role="list">\n'
        f'      <div role="listitem"><strong>{counts["all"]}</strong><span>projects</span></div>\n'
        f'      <div role="listitem"><strong>{counts["report"]}</strong><span>reports</span></div>\n'
        f'      <div role="listitem"><strong>{counts["dashboard"]}</strong><span>dashboards</span></div>\n'
        f'      <div role="listitem"><strong>{counts["project"] + counts["dataset"]}</strong><span>other work</span></div>\n'
        "    </div>\n"
        "  </section>\n"
        '  <section class="toolbar" aria-label="Filter and search">\n'
        '    <div class="filter-tabs" role="tablist" aria-label="Filter by type">\n'
        '      <button class="filter-tab active" data-filter="all" role="tab" aria-selected="true">All</button>\n'
        '      <button class="filter-tab" data-filter="report" role="tab" aria-selected="false">Reports</button>\n'
        '      <button class="filter-tab" data-filter="dashboard" role="tab" aria-selected="false">Dashboards</button>\n'
        '      <button class="filter-tab" data-filter="project" role="tab" aria-selected="false">Projects</button>\n'
        '      <button class="filter-tab" data-filter="dataset" role="tab" aria-selected="false">Datasets</button>\n'
        "    </div>\n"
        '    <input type="search" id="search" placeholder="Search title, tags, keywords…" aria-label="Search projects">\n'
        '    <p class="result-count" id="result-count" aria-live="polite"></p>\n'
        "  </section>\n"
        f'  <section class="card-grid" id="card-grid">\n{cards}\n  </section>\n'
        '  <section class="about-strip">\n'
        "    <h2>Built for volume</h2>\n"
        "    <p>This platform is a publishing system, not a one-off showcase. Every project lives in "
        "<code>projects/&lt;slug&gt;/project.json</code> with a fixed metadata schema. The build script "
        "regenerates the catalog, per-project pages, <code>sitemap.xml</code>, <code>projects.json</code>, "
        "and <code>rss.xml</code> on every run, so hundreds or thousands of entries scale without manual page assembly.</p>\n"
        "  </section>\n"
        "</main>"
    )


def project_body(p, prev_link, next_link):
    content = read_markdown(p)
    authors = p.get("authors") or []
    author_html = "".join(
        f'<span class="author">{esc(a.get("name", ""))}'
        f'<span class="author-role">, {esc(a.get("role", ""))}</span></span>'
        for a in authors
    )
    figures = p.get("figures") or []
    figure_cards = "".join(
        f'<div class="figure-card"><strong>{esc(f.get("value", ""))}</strong><span>{esc(f.get("caption", ""))}</span></div>'
        for f in figures
    )
    figure_grid = f'<section class="figures-grid">{figure_cards}</section>' if figures else ""

    outline = p.get("chapterOutline") or []
    outline_rows = "".join(
        f'<tr><td class="chapter-no">{esc(c.get("chapter", ""))}</td>'
        f'<td class="chapter-title">{esc(c.get("title", ""))}</td>'
        f'<td class="chapter-focus">{esc(c.get("focus", ""))}</td></tr>'
        for c in outline
    )
    outline_html = (
        '<section class="outline">\n'
        "  <h2>Analytical structure</h2>\n"
        "  <div class=\"table-wrap\">\n"
        "  <table>\n"
        "    <thead><tr><th>Section</th><th>Chapter title</th><th>Core thematic focus</th></tr></thead>\n"
        f"    <tbody>{outline_rows}</tbody>\n"
        "  </table>\n"
        "  </div>\n"
        "</section>"
    ) if outline else ""

    files = p.get("files") or []
    file_links = "".join(
        f'<a class="file-link" href="{esc(f["path"])}" download>'
        f'<span class="file-label">{esc(f.get("label", f["path"]))}</span>'
        f'<span class="file-kind">{esc(f.get("kind", "").upper())}</span>'
        f'<span class="file-size">{esc(f.get("size", ""))}</span></a>'
        for f in files
    )
    files_html = (
        '<section class="downloads">\n'
        "  <h2>Download</h2>\n"
        f'  <div class="file-links">{file_links}</div>\n'
        "</section>"
    ) if files else ""

    spec_items = []
    if p.get("pages"):
        spec_items.append(f"<span><strong>Pages</strong>{esc(p['pages'])}</span>")
    if p.get("chapters"):
        spec_items.append(f"<span><strong>Chapters</strong>{esc(p['chapters'])}</span>")
    if p.get("exhibits"):
        spec_items.append(f"<span><strong>Exhibits</strong>{esc(p['exhibits'])}</span>")
    if p.get("tables"):
        spec_items.append(f"<span><strong>Tables</strong>{esc(p['tables'])}</span>")
    if p.get("citations"):
        spec_items.append(f"<span><strong>Citations</strong>{esc(p['citations'])}</span>")
    if p.get("license"):
        spec_items.append(f"<span><strong>License</strong>{esc(p['license'])}</span>")
    if p.get("language"):
        spec_items.append(f"<span><strong>Language</strong>{esc(p['language']).upper()}</span>")
    spec_html = f'<div class="spec-row">{"".join(spec_items)}</div>' if spec_items else ""

    prev_block = f'<a class="adjacent prev" href="{prev_link}"><span>Previous</span></a>' if prev_link else '<span class="adjacent prev disabled">Previous</span>'
    next_block = f'<a class="adjacent next" href="{next_link}"><span>Next project</span></a>' if next_link else '<span class="adjacent next disabled">Next project</span>'

    return (
        '<main class="project">\n'
        '  <nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">Home</a> '
        f'<span aria-hidden="true">/</span> <span class="crumb-type">{type_eyebrow(p)}</span> '
        f'<span aria-hidden="true">/</span> <span aria-current="page">{esc(p["title"])}</span></nav>\n'
        '  <article>\n'
        '    <header class="project-header">\n'
        f'      <p class="eyebrow">{esc(p.get("series") or type_eyebrow(p))}</p>\n'
        f'      <h1>{esc(p["title"])}</h1>\n'
        f'      <p class="subtitle">{esc(p.get("subtitle") or "")}</p>\n'
        f'      <p class="byline">{author_html} · {esc(p.get("dateLabel") or p["date"])}</p>\n'
        f'      {spec_html}\n'
        "    </header>\n"
        f'    {figure_grid}\n'
        '    <section class="abstract">\n'
        f'      <p class="eyebrow">Abstract</p>\n'
        f'      <p class="abstract-text first-para">{esc(p.get("abstract") or "")}</p>\n'
        "    </section>\n"
        f'    <section class="content">{content}</section>\n'
        f'    {outline_html}\n'
        f'    {files_html}\n'
        f'    {tags_html(p)}\n'
        "  </article>\n"
        f'  <nav class="adjacent-nav" aria-label="Project navigation">{prev_block}{next_block}</nav>\n'
        "</main>"
    )


# ---------------------------------------------------------------------------
# JSON-LD builders
# ---------------------------------------------------------------------------
def home_ld(projects):
    site = {
        "@type": "WebSite",
        "name": SITE_NAME,
        "url": SITE_URL,
        "publisher": organization_ld(),
        "potentialAction": {
            "@type": "SearchAction",
            "target": f"{SITE_URL}/?q={{search_term_string}}",
            "query-input": "required name=search_term_string",
        },
    }
    items = [
        {
            "@type": "ListItem",
            "position": i + 1,
            "item": {
                "@type": "CreativeWork",
                "name": p["title"],
                "url": f"{SITE_URL}/projects/{p['slug']}/",
                "description": p.get("description") or "",
                "datePublished": p["date"],
                "genre": TYPES.get(p["type"], "Project"),
            },
        }
        for i, p in enumerate(projects)
    ]
    return [site, {"@type": "ItemList", "itemListElement": items}]


def project_ld(p):
    url = f"{SITE_URL}/projects/{p['slug']}/"
    authors = [
        {
            "@type": "Person",
            "name": a.get("name", ""),
            "jobTitle": a.get("role", ""),
            "affiliation": {"@type": "Organization", "name": a.get("org") or ORG_NAME},
        }
        for a in (p.get("authors") or [])
    ]
    keywords = list(dict.fromkeys((p.get("keywords") or []) + (p.get("tags") or [])))
    report = {
        "@type": "Report",
        "headline": p["title"],
        "alternativeHeadline": p.get("subtitle") or "",
        "description": p.get("abstract") or p.get("description") or "",
        "datePublished": p["date"],
        "author": authors,
        "publisher": organization_ld(),
        "mainEntityOfPage": url,
        "url": url,
        "inLanguage": p.get("language", "en"),
        "keywords": ", ".join(keywords),
        "genre": p.get("series") or TYPES.get(p["type"]),
        "isAccessibleForFree": True,
        "license": p.get("license") or "",
    }
    if p.get("pages"):
        report["numberOfPages"] = p["pages"]
    breadcrumb = {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE_URL},
            {"@type": "ListItem", "position": 2, "name": TYPES.get(p["type"], "Project"),
             "item": f"{SITE_URL}/?type={p['type']}"},
            {"@type": "ListItem", "position": 3, "name": p["title"], "item": url},
        ],
    }
    return [report, breadcrumb]


# ---------------------------------------------------------------------------
# OG image generation (best-effort, no hard dependency)
# ---------------------------------------------------------------------------
def make_og_image(p, out_path):
    import os
    import tempfile
    os.environ.setdefault("MPLCONFIGDIR", tempfile.gettempdir())
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return False
    try:
        fig = plt.figure(figsize=(12, 6.3), dpi=100)
        fig.patch.set_facecolor("#f6f3ec")
        ax = fig.add_axes([0.06, 0.12, 0.88, 0.72])
        ax.set_facecolor("#f6f3ec")
        ax.axis("off")
        ax.text(0.01, 0.92, "H HEURISTICS · BONUS REPORTS PLATFORM",
                fontsize=13, color="#8a2f2f", weight="bold",
                transform=ax.transAxes, va="top")
        ax.text(0.01, 0.78, TYPES.get(p["type"], "Project").upper(),
                fontsize=14, color="#5b6470", transform=ax.transAxes, va="top")
        title = p["title"]
        if len(title) > 72:
            title = title[:69].rstrip() + "…"
        ax.text(0.01, 0.62, title, fontsize=34, color="#14202c", weight="bold",
                family="serif", transform=ax.transAxes, va="top", wrap=True)
        sub = p.get("subtitle") or ""
        if len(sub) > 110:
            sub = sub[:107].rstrip() + "…"
        ax.text(0.01, 0.28, sub, fontsize=15, color="#5b6470", family="sans-serif",
                transform=ax.transAxes, va="top", wrap=True)
        ax.text(0.01, 0.06, f"{p.get('dateLabel') or p['date']}  ·  {ORG_NAME}",
                fontsize=12, color="#14202c", transform=ax.transAxes, va="top")
        for spine in ax.spines.values():
            spine.set_visible(False)
        fig.savefig(out_path, facecolor="#f6f3ec")
        plt.close(fig)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Feeds & policy files
# ---------------------------------------------------------------------------
def write_sitemap(projects):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    lines.append(f"  <url><loc>{SITE_URL}/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>")
    for p in projects:
        url = f"{SITE_URL}/projects/{p['slug']}/"
        lines.append(f"  <url><loc>{url}</loc><lastmod>{p['date']}</lastmod>"
                     f"<changefreq>monthly</changefreq><priority>0.8</priority></url>")
    lines.append("</urlset>")
    (DIST / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_robots():
    (DIST / "robots.txt").write_text(
        "User-agent: *\nAllow: /\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n",
        encoding="utf-8",
    )


def write_headers():
    (DIST / "_headers").write_text(
        "/*\n"
        "  X-Content-Type-Options: nosniff\n"
        "  Referrer-Policy: strict-origin-when-cross-origin\n"
        "  X-Frame-Options: SAMEORIGIN\n"
        "  Permissions-Policy: geolocation=(), microphone=(), camera=()\n"
        "\n"
        "/*.pdf\n"
        "  Cache-Control: public, max-age=604800\n"
        "\n"
        "/projects.json\n"
        "  Content-Type: application/json; charset=utf-8\n"
        "  Access-Control-Allow-Origin: *\n"
        "\n"
        "/assets/*\n"
        "  Cache-Control: public, max-age=86400\n",
        encoding="utf-8",
    )


def write_index(projects):
    public = []
    for p in projects:
        item = {k: v for k, v in p.items() if k != "_dir"}
        item["url"] = f"{SITE_URL}/projects/{p['slug']}/"
        item["pageUrl"] = f"/projects/{p['slug']}/"
        public.append(item)
    (DIST / "projects.json").write_text(
        json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_rss(projects):
    items = []
    for p in projects:
        if p["type"] != "report":
            continue
        url = f"{SITE_URL}/projects/{p['slug']}/"
        items.append(
            "    <item>\n"
            f"      <title>{esc(p['title'])}</title>\n"
            f"      <link>{url}</link>\n"
            f"      <guid isPermaLink=\"true\">{url}</guid>\n"
            f"      <description>{esc(p.get('description') or '')}</description>\n"
            f"      <pubDate>{p['date']}</pubDate>\n"
            "    </item>"
        )
    feed = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "  <channel>\n"
        f"    <title>{esc(SITE_NAME)} — Reports</title>\n"
        f"    <link>{SITE_URL}</link>\n"
        f"    <description>{esc(SITE_TAGLINE)}</description>\n"
        + "\n".join(items)
        + "\n  </channel>\n</rss>\n"
    )
    (DIST / "rss.xml").write_text(feed, encoding="utf-8")


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def build(include_drafts=False, check_only=False):
    projects = load_projects(include_drafts)
    print(f"Loaded {len(projects)} published project(s)")

    if check_only:
        for p in projects:
            print(f"  ✓ {p['slug']} — {p['title']}")
        return

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    (DIST / "assets").mkdir(parents=True)

    # Homepage
    home = base_page(
        title=f"{SITE_NAME} — {SITE_TAGLINE}",
        description=(
            "Indexed catalog of H Heuristics research output: reports, dashboards, "
            "datasets, and experimental projects, each with full search metadata."
        ),
        canonical=f"{SITE_URL}/",
        body=home_body(projects, include_drafts),
        ld_objects=home_ld(projects),
    )
    (DIST / "index.html").write_text(home, encoding="utf-8")
    print("  ✓ index.html")

    # Project pages
    for i, p in enumerate(projects):
        prev_link = f"/projects/{projects[i - 1]['slug']}/" if i > 0 else ""
        next_link = f"/projects/{projects[i + 1]['slug']}/" if i < len(projects) - 1 else ""
        page = base_page(
            title=f"{p['title']} — {SITE_NAME}",
            description=(p.get("description") or p.get("abstract") or "")[:160],
            canonical=f"{SITE_URL}/projects/{p['slug']}/",
            body=project_body(p, prev_link, next_link),
            ld_objects=project_ld(p),
            og_type="article",
            nav_active=p["type"],
            extra_head=(
                f'    <meta property="og:image" content="{SITE_URL}/assets/og-{p["slug"]}.png">\n'
                f'    <meta name="twitter:image" content="{SITE_URL}/assets/og-{p["slug"]}.png">\n'
                f'    <meta property="article:published_time" content="{esc(p["date"])}">\n'
            ),
        )
        page_dir = DIST / "projects" / p["slug"]
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.html").write_text(page, encoding="utf-8")

        # Copy project files (PDFs, HTML embeds, images) next to the page
        for f in (p.get("files") or []):
            src = p["_dir"] / f["path"]
            if src.exists():
                shutil.copy2(src, page_dir / f["path"])
        og_ok = make_og_image(p, DIST / "assets" / f"og-{p['slug']}.png")
        if not og_ok:
            print(f"  ! og image skipped for {p['slug']} (matplotlib unavailable)")
        print(f"  ✓ projects/{p['slug']}/index.html")

    # 404
    not_found = base_page(
        title=f"Page not found — {SITE_NAME}",
        description="The requested page does not exist on the Bonus Reports Platform.",
        canonical=f"{SITE_URL}/404.html",
        body=(
            '<main class="notfound">\n'
            "  <p class=\"eyebrow\">404</p>\n"
            "  <h1>This page is not in the archive.</h1>\n"
            '  <p><a href="/">Return to the catalog</a> or use search above.</p>\n'
            "</main>"
        ),
        ld_objects=[{"@type": "WebSite", "name": SITE_NAME, "url": SITE_URL}],
    )
    (DIST / "404.html").write_text(not_found, encoding="utf-8")
    print("  ✓ 404.html")

    # Feeds & policy files
    write_sitemap(projects)
    write_robots()
    write_headers()
    write_index(projects)
    write_rss(projects)
    print("  ✓ sitemap.xml, robots.txt, _headers, projects.json, rss.xml")


if __name__ == "__main__":
    args = set(sys.argv[1:])
    build(include_drafts="--include-drafts" in args, check_only="--check" in args)
    print("Build complete.")
