#!/usr/bin/env python3
"""
Add or update a book/chapter page and regenerate MkDocs nav for bible-background.

Usage examples:
  python tools/add_page.py --book genesis --chapter 2 --source content/genesis/2.md
  cat /path/to/new.md | python tools/add_page.py --book exodus --chapter 1 --source -
  cat day.md | python tools/add_page.py --day 2026-08-21 --source -
  python tools/add_page.py --update-nav-only  # just rebuild nav
"""
from __future__ import annotations

import argparse
import datetime
import pathlib
import re
import sys
from typing import Dict, List

import yaml


# Canonical order, so nav reads Genesis -> Revelation rather than alphabetically.
BOOK_ORDER = [
    "genesis", "exodus", "leviticus", "numbers", "deuteronomy", "joshua", "judges",
    "ruth", "1-samuel", "2-samuel", "1-kings", "2-kings", "1-chronicles",
    "2-chronicles", "ezra", "nehemiah", "esther", "job", "psalm", "proverbs",
    "ecclesiastes", "song-of-songs", "isaiah", "jeremiah", "lamentations", "ezekiel",
    "daniel", "hosea", "joel", "amos", "obadiah", "jonah", "micah", "nahum",
    "habakkuk", "zephaniah", "haggai", "zechariah", "malachi", "matthew", "mark",
    "luke", "john", "acts", "romans", "1-corinthians", "2-corinthians", "galatians",
    "ephesians", "philippians", "colossians", "1-thessalonians", "2-thessalonians",
    "1-timothy", "2-timothy", "titus", "philemon", "hebrews", "james", "1-peter",
    "2-peter", "1-john", "2-john", "3-john", "jude", "revelation",
]
BOOK_INDEX = {slug: i for i, slug in enumerate(BOOK_ORDER)}

# Dated pages tying together one day's readings; kept out of the book sequence.
DAYS_DIR = "days"
DAYS_TITLE = "Reading days"


def book_sort_key(slug: str) -> tuple:
    # Unknown books sort after the canon, alphabetically.
    return (BOOK_INDEX.get(slug, len(BOOK_ORDER)), slug)


def display_day_name(stem: str) -> str:
    try:
        return datetime.date.fromisoformat(stem).strftime("%a %-d %b %Y")
    except ValueError:
        return stem


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

    book_dirs = [p for p in content_root.iterdir() if p.is_dir() and p.name != DAYS_DIR]
    for book_dir in sorted(book_dirs, key=lambda p: book_sort_key(p.name)):
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

    days_dir = content_root / DAYS_DIR
    if days_dir.exists():
        days = sorted(days_dir.glob("*.md"), key=lambda p: p.stem, reverse=True)
        if days:
            nav.append({DAYS_TITLE: [{display_day_name(p.stem): f"{DAYS_DIR}/{p.name}"} for p in days]})

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
    parser.add_argument("--day", help="Reading-day date as YYYY-MM-DD; writes content/days/<date>.md")
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
        if args.day:
            if not args.source:
                sys.exit("Error: --day requires --source.")
            try:
                datetime.date.fromisoformat(args.day)
            except ValueError:
                sys.exit(f"Error: --day must be YYYY-MM-DD, got {args.day!r}")
            target = (DAYS_DIR, args.day)
        else:
            if not (args.book and args.chapter and args.source):
                sys.exit("Error: --book and --chapter (or --day), plus --source, are required "
                         "unless --update-nav-only is used.")
            target = (slugify_book(args.book), args.chapter.strip())

        if args.source == "-":
            text = sys.stdin.read()
        else:
            text = pathlib.Path(args.source).read_text(encoding="utf-8")

        write_content(content_root, target[0], target[1], text)

    nav = generate_nav(content_root)
    update_mkdocs_nav(root, nav)


if __name__ == "__main__":
    main()
