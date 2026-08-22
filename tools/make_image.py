#!/usr/bin/env python3
"""Generate a photo-realistic header image for a chapter page.

Usage: make_image.py --book judges --chapter 15 --prompt prompt.txt [--quality medium]

Reads OPENAI_API_KEY from .env in the repo root. Writes
content/images/<book>-<chapter>.webp and prints the token usage and cost.

The API returns ~2 MB PNGs. At three chapters a day that would push the repo
past the GitHub Pages size limit, so each image is converted to WebP and the
PNG is discarded.
"""
import argparse
import base64
import os
import pathlib
import subprocess
import sys

from openai import OpenAI

# gpt-image-2 standard rates, dollars per 1M tokens.
RATES = {"text_in": 5.00, "image_in": 8.00, "image_out": 30.00}


def load_env(root):
    env = root / ".env"
    if not env.exists():
        sys.exit(f"no .env at {env}")
    for line in env.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--book", required=True)
    ap.add_argument("--chapter", required=True)
    ap.add_argument("--prompt", required=True, help="path to prompt file, or - for stdin")
    ap.add_argument("--quality", default="medium", choices=["low", "medium", "high"])
    ap.add_argument("--size", default="1024x1024")
    args = ap.parse_args()

    root = pathlib.Path(args.root).resolve()
    load_env(root)
    prompt = sys.stdin.read() if args.prompt == "-" else pathlib.Path(args.prompt).read_text()

    result = OpenAI().images.generate(
        model="gpt-image-2",
        prompt=prompt.strip(),
        size=args.size,
        quality=args.quality,
    )

    slug = args.book.strip().lower().replace(" ", "-")
    dest = root / "content" / "images" / f"{slug}-{args.chapter}.webp"
    dest.parent.mkdir(parents=True, exist_ok=True)
    raw = dest.with_suffix(".png")
    raw.write_bytes(base64.b64decode(result.data[0].b64_json))
    subprocess.run(["magick", str(raw), "-quality", "80",
                    "-define", "webp:method=6", str(dest)], check=True)
    raw.unlink()

    u = result.usage
    detail = getattr(u, "input_tokens_details", None)
    text_in = getattr(detail, "text_tokens", u.input_tokens) if detail else u.input_tokens
    image_in = getattr(detail, "image_tokens", 0) if detail else 0
    cost = (text_in * RATES["text_in"] + image_in * RATES["image_in"]
            + u.output_tokens * RATES["image_out"]) / 1_000_000
    print(f"{dest.relative_to(root)}  {dest.stat().st_size // 1024} KB")
    print(f"tokens: text_in={text_in} image_in={image_in} output={u.output_tokens}")
    print(f"cost: ${cost:.4f}")


main()
