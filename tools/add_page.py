#!/usr/bin/env python3
"""
Add or update a book/chapter page and regenerate MkDocs nav for bible-background.

Usage examples:
  python tools/add_page.py --book genesis --chapter 2 --source content/genesis/2.md
  cat /path/to/new.md | python tools/add_page.py --book exodus --chapter 1 --source -
  python tools/add_page.py --update-nav-only  # just rebuild nav
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
from typing import Dict, List

import yaml


def slugify_book(raw: str) -> str:
    slug = raw.strip().lower()
    slug = slug.replace(" ", "-")
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if not slug:
        raise ValueError("Book slug is empty after normalization")
    return slug


def display_book_name(slug: str) -> str:
    # Turn "1-samuel" -> "1 Samuel"
    return slug.replace("-", " ").title()


def natural_key(value: str) -> List:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", value)]


def write_content(content_root: pathlib.Path, book: str, chapter: str, text: str) -> pathlib.Path:
    book_dir = content_root / book
    book_dir.mkdir(parents=True, exist_ok=True)
    dest = book_dir / f"{chapter}.md"
    dest.write_text(text.rstrip() + "\n", encoding="utf-8")
    return dest


def generate_nav(content_root: pathlib.Path) -> List[Dict]:
    nav: List[Dict] = [{"Home": "index.md"}]
    if not content_root.exists():
        return nav

    for book_dir in sorted([p for p in content_root.iterdir() if p.is_dir()], key=lambda p: natural_key(p.name)):
        book_slug = book_dir.name
        book_name = display_book_name(book_slug)

        items: List[Dict[str, str]] = []
        index_md = book_dir / "index.md"
        if index_md.exists():
            items.append({"Overview": f"{book_slug}/index.md"})

        chapters = [p for p in book_dir.glob("*.md") if p.name != "index.md"]
        for chapter_md in sorted(chapters, key=lambda p: natural_key(p.stem)):
            items.append({f"Chapter {chapter_md.stem}": f"{book_slug}/{chapter_md.name}"})

        if items:
            nav.append({book_name: items})

    return nav


def update_mkdocs_nav(root: pathlib.Path, nav: List[Dict]) -> None:
    mkdocs_path = root / "mkdocs.yml"
    if not mkdocs_path.exists():
        raise FileNotFoundError(f"mkdocs.yml not found at {mkdocs_path}")
    config = yaml.safe_load(mkdocs_path.read_text()) or {}
    config["nav"] = nav
    mkdocs_path.write_text(
        yaml.safe_dump(config, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add/update a Bible Background page and rebuild nav")
    parser.add_argument("--root", default=".", help="Path to site root (default: current directory)")
    parser.add_argument("--book", help="Book name (will be normalized to lowercase slug)")
    parser.add_argument("--chapter", help="Chapter identifier (e.g., 2)")
    parser.add_argument(
        "--source",
        help="Path to Markdown source file, or '-' to read from stdin. Required unless --update-nav-only is set.",
    )
    parser.add_argument(
        "--update-nav-only",
        action="store_true",
        help="Skip writing content; just regenerate nav from existing files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = pathlib.Path(args.root).resolve()
    content_root = root / "content"

    if not args.update_nav_only:
        if not (args.book and args.chapter and args.source):
            sys.exit("Error: --book, --chapter, and --source are required unless --update-nav-only is used.")
        book_slug = slugify_book(args.book)
        chapter = args.chapter.strip()

        if args.source == "-":
            text = sys.stdin.read()
        else:
            text = pathlib.Path(args.source).read_text(encoding="utf-8")

        write_content(content_root, book_slug, chapter, text)

    nav = generate_nav(content_root)
    update_mkdocs_nav(root, nav)


if __name__ == "__main__":
    main()
