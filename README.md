# Bible Background

Static MkDocs site for `https://woodwardmw.github.io/bible-background/`. Content is Markdown per book/chapter with predictable lowercase URLs (e.g., `/genesis/2/`).

## Content model
- Markdown lives in `content/`.
- Use lowercase book folders and numeric chapter files: `content/<book>/<chapter>.md` (e.g., `content/genesis/2.md`).
- Add an `index.md` inside each book folder for overview pages.
- Update `mkdocs.yml` nav as you add books/chapters so they appear in the sidebar.

## Local preview
```bash
cd /home/mark/projects/bible-background
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdocs serve
```
Site will be at http://127.0.0.1:8000/; links remain relative so deploy under `/bible-background/` works.

## Deploys
- GitHub Actions builds on every push to `main` and publishes to GitHub Pages.
- In the repo’s GitHub settings, set Pages → Source to “GitHub Actions” (the workflow is included).

## Adding new content
Use the helper to write the file and regenerate nav:
```bash
python tools/add_page.py --book genesis --chapter 2 --source content/genesis/2.md
# or pipe new content:
cat new.md | python tools/add_page.py --book exodus --chapter 1 --source -
# nav-only refresh:
python tools/add_page.py --update-nav-only
```

Manual path (if you prefer):
1) Create `content/<book>/<chapter>.md` (lowercase book).  
2) (Optional) Create/extend `content/<book>/index.md`.  
3) Run `python tools/add_page.py --update-nav-only` to rebuild `nav:` in `mkdocs.yml`.  
4) Commit and push to `main`; Pages auto-deploys.

## TODO
- Add a small script/skill to ingest tool output into the `content/` structure and update nav automatically.
