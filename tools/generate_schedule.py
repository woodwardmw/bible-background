#!/usr/bin/env python3
"""Rebuild schedule.tsv from a Bible reading schedule PDF (LibreOffice Calc export).

Usage: generate.py <schedule.pdf> [output.tsv]

Writes two files: the display form (one field per track, ranges collapsed to
"Job 18-20") used by the desktop notification, and chapters.tsv alongside it,
which expands every range so each field is a single chapter. The site builder
wants one page per chapter, and every day is exactly 3 chapters.

The PDF prints a start chapter per track per day; the actual reading runs to the
chapter before the next day's start, crossing book boundaries. Every day works
out to exactly 3 chapters, which is asserted as a self-test.
"""
import collections
import datetime
import pathlib
import re
import subprocess
import sys

CHAPTERS = {
    'Genesis': 50, 'Exodus': 40, 'Leviticus': 27, 'Numbers': 36, 'Deuteronomy': 34,
    'Joshua': 24, 'Judges': 21, 'Ruth': 4, '1 Samuel': 31, '2 Samuel': 24,
    '1 Kings': 22, '2 Kings': 25, '1 Chronicles': 29, '2 Chronicles': 36,
    'Ezra': 10, 'Nehemiah': 13, 'Esther': 10, 'Job': 42, 'Psalm': 150,
    'Proverbs': 31, 'Ecclesiastes': 12, 'Song of Songs': 8, 'Isaiah': 66,
    'Jeremiah': 52, 'Lamentations': 5, 'Ezekiel': 48, 'Daniel': 12, 'Hosea': 14,
    'Joel': 3, 'Amos': 9, 'Obadiah': 1, 'Jonah': 4, 'Micah': 7, 'Nahum': 3,
    'Habakkuk': 3, 'Zephaniah': 3, 'Haggai': 2, 'Zechariah': 14, 'Malachi': 4,
    'Matthew': 28, 'Mark': 16, 'Luke': 24, 'John': 21, 'Acts': 28, 'Romans': 16,
    '1 Corinthians': 16, '2 Corinthians': 13, 'Galatians': 6, 'Ephesians': 6,
    'Philippians': 4, 'Colossians': 4, '1 Thessalonians': 5, '2 Thessalonians': 3,
    '1 Timothy': 6, '2 Timothy': 4, 'Titus': 3, 'Philemon': 1, 'Hebrews': 13,
    'James': 5, '1 Peter': 5, '2 Peter': 3, '1 John': 5, '2 John': 1, '3 John': 1,
    'Jude': 1, 'Revelation': 22,
}

# The spreadsheet clips long book names to the column width, and misspells two.
UNTRUNCATE = {
    'Deuterenom': 'Deuteronomy', 'Ecclesias': 'Ecclesiastes', 'Song of': 'Song of Songs',
    'Lamentati': 'Lamentations', 'Zephania': 'Zephaniah', '1 Corinthia': '1 Corinthians',
    '2 Corinthia': '2 Corinthians', 'Philipians': 'Philippians',
    '1 Thessalo': '1 Thessalonians', '2 Thessalo': '2 Thessalonians',
}

# Cell boundaries by xMin, in PDF points. Chapter numbers are right-aligned, so
# a three-digit Psalm starts further left than a two-digit one; the book/chapter
# splits sit clear of both.
COLUMNS = [(112, 178, 'b1'), (178, 196, 'c1'), (196, 280, 'b2'),
           (280, 302, 'c2'), (302, 368, 'b3'), (368, 999, 'c3')]

MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
WORD = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="[\d.]+" yMax="[\d.]+">(.*?)</word>')
DATE = re.compile(r'\w{3}, (\w{3}) (\d+), (\d\d)$')


def read_rows(pdf):
    xml = subprocess.run(['pdftotext', '-bbox', pdf, '-'],
                         capture_output=True, text=True, check=True).stdout
    rows = []
    for page in xml.split('<page ')[1:]:
        lines = collections.defaultdict(list)
        for x, y, word in WORD.findall(page):
            lines[round(float(y))].append((float(x), word))
        for y in sorted(lines):
            cells, date = collections.defaultdict(list), []
            for x, word in sorted(lines[y]):
                if x < 112:
                    date.append(word)
                    continue
                for lo, hi, key in COLUMNS:
                    if lo <= x < hi:
                        cells[key].append(word)
                        break
            match = DATE.match(' '.join(date))
            if not match:
                continue
            day = datetime.date(2000 + int(match.group(3)),
                                MONTHS.index(match.group(1)) + 1, int(match.group(2)))
            rows.append((day, {k: ' '.join(v) for k, v in cells.items()}))
    return rows


def track_readings(rows, track):
    """Expand one track's start chapters into (date, "Book c-c") readings."""
    starts, book = [], None
    for day, cells in rows:
        if cells.get('b' + track):
            book = UNTRUNCATE.get(cells['b' + track], cells['b' + track])
        if cells.get('c' + track):
            starts.append((day, book, int(cells['c' + track])))
    if not starts:
        return {}

    order = list(dict.fromkeys(b for _, b, _ in starts))
    unknown = [b for b in order if b not in CHAPTERS]
    if unknown:
        sys.exit(f'unknown book(s) in track {track}: {unknown}')

    offset, total = {}, 0
    for b in order:
        offset[b] = total
        total += CHAPTERS[b]

    def locate(pos):
        b = [x for x in order if offset[x] <= pos][-1]
        return b, pos - offset[b] + 1

    positions = [offset[b] + ch - 1 for _, b, ch in starts]
    if positions != sorted(set(positions)):
        sys.exit(f'track {track} chapters are not strictly increasing')

    out = {}
    for i, (day, book, chapter) in enumerate(starts):
        end = positions[i + 1] - 1 if i + 1 < len(positions) else total - 1
        end_book, end_chapter = locate(end)
        if end_book != book:
            span = f'{book} {chapter} - {end_book} {end_chapter}'
        elif end_chapter == chapter:
            span = f'{book} {chapter}'
        else:
            span = f'{book} {chapter}-{end_chapter}'
        each = [f'{b} {c}' for b, c in (locate(p) for p in range(positions[i], end + 1))]
        out[day] = (span, end - positions[i] + 1, each)
    return out


def main():
    pdf = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else 'schedule.tsv'
    rows = read_rows(pdf)
    if not rows:
        sys.exit('no dated rows found; check the column boundaries')

    # The PDF holds the live schedule plus printings for earlier years. Split the
    # dates into contiguous runs and keep the one covering today, else the latest.
    runs, run = [], [sorted({d for d, _ in rows})[0]]
    for day in sorted({d for d, _ in rows})[1:]:
        if (day - run[-1]).days == 1:
            run.append(day)
        else:
            runs.append(run)
            run = [day]
    runs.append(run)
    today = datetime.date.today()
    current = [r for r in runs if r[0] <= today <= r[-1]]
    days = current[0] if current else max(runs, key=lambda r: r[-1])
    if len(runs) > 1:
        print(f'{len(runs)} date runs in PDF; using {days[0]} to {days[-1]}')
    rows = [(d, c) for d, c in rows if days[0] <= d <= days[-1]]

    tracks = [track_readings(rows, t) for t in '123']
    chapters_path = pathlib.Path(out_path).with_name('chapters.tsv')
    with open(out_path, 'w') as f, open(chapters_path, 'w') as g:
        for day in days:
            spans = [t[day][0] for t in tracks if day in t]
            each = [c for t in tracks if day in t for c in t[day][2]]
            # Every day is 3 chapters; only the final day of the plan falls short.
            if len(each) != 3 and day != days[-1]:
                sys.exit(f'{day}: {len(each)} chapters, expected 3 -- parse is wrong')
            f.write('\t'.join([day.isoformat()] + spans) + '\n')
            g.write('\t'.join([day.isoformat()] + each) + '\n')
    print(f'{len(days)} days written to {out_path} and {chapters_path} ({days[0]} to {days[-1]})')


main()
