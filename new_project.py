#!/usr/bin/env python3
"""
Scaffold a new project folder for the Bonus Reports Platform.

Usage:
    python3 new_project.py "Title of the project" [--type report] [--slug my-slug]
                           [--subtitle "..."] [--author "Name"] [--date 2026-10-29]

Creates projects/<slug>/project.json with the required fields and a stub
content.md. Fill in the remaining metadata, then run `python3 build.py`.
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TYPES = {"report", "dashboard", "project", "dataset"}


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:80]


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("title")
    parser.add_argument("--type", default="report", choices=sorted(TYPES))
    parser.add_argument("--slug", default=None)
    parser.add_argument("--subtitle", default="")
    parser.add_argument("--author", default="Hunter Hughes")
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()

    slug = args.slug or slugify(args.title)
    folder = ROOT / "projects" / slug
    if folder.exists():
        print(f"✗ {folder} already exists")
        sys.exit(1)

    folder.mkdir(parents=True)
    meta = {
        "slug": slug,
        "title": args.title,
        "subtitle": args.subtitle,
        "type": args.type,
        "series": "H Heuristics · Global Strategic Monograph Series",
        "status": "published",
        "featured": False,
        "date": args.date,
        "dateLabel": args.date,
        "authors": [{"name": args.author, "role": "Founder & CEO", "org": "H Heuristics"}],
        "org": {"name": "H Heuristics", "url": "https://hheuristics.com"},
        "description": "",
        "abstract": "",
        "keywords": [],
        "tags": [],
        "categories": [],
        "language": "en",
        "license": "Unrestricted Open Access · Institutional Standard",
        "pages": None,
        "chapters": None,
        "exhibits": None,
        "tables": None,
        "citations": None,
        "figures": [],
        "chapterOutline": [],
        "files": [],
        "external": [],
        "bindingTerm": "",
    }
    (folder / "project.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (folder / "content.md").write_text(
        f"# {args.title}\n\n"
        "State the analytical claim in one line, build the arc "
        "(framing → evidence → implication), and close on a binding term.\n\n"
        "**Binding term:** \n",
        encoding="utf-8",
    )
    print(f"✓ created {folder}")
    print("  Next: fill in description/abstract/tags, drop source files into the folder,")
    print("  reference them in project.json files[], then run: python3 build.py")


if __name__ == "__main__":
    main()
