# georgejpappas.org

Personal website of George J. Pappas, served by GitHub Pages from the root of `main`.

## Update the site

    ./build.sh        # refreshes the web CV and publications (if cv/resume.tex is here), then rebuilds every page
    python3 tools/find_dois.py && python3 tools/fetch_bibtex.py   # after new papers: DOIs and BibTeX
    git add -A && git commit -m "Update site" && git push

Needs only Python 3 (standard library). Preview locally with `python3 -m http.server 8000`.

## Layout

| Path | What it is |
|---|---|
| `index.html`, `bio/`, `research/`, `group/`, `publications/`, `book/`, `teaching/`, `press/` | Generated pages — do not edit by hand (`news/` only forwards to `press/`) |
| `site-src/layout.html` | Shared header, footer and page head |
| `site-src/pages/*.html` | Page bodies (`{{field}}`, `<sc-for>`, `<sc-if>`, as in the approved design) |
| `site-src/data/*.json` | Page content; `publications.json` is generated from the CV |
| `site-src/design/` | The approved design (October 23, 2026), for reference |
| `assets/` | Stylesheet, script, favicon |
| `images/` | Photos, book cover, Penn logo |
| `cv/resume_web.pdf` | The web CV — the only CV the site links to |
| `tools/` | `build_site.py` (site), `allpubs.py` (CV → publications), `find_dois.py` (Crossref/ORCID DOIs → `pub-links.json`), `fetch_bibtex.py` (BibTeX for every paper), `extract.py` |

## Standing rules

Penn Navy palette; Source Serif 4 headings, Source Sans 3 body. Menu order Home, Bio, Research,
Group, Publications, Book, Teaching, Press. No volume numbers (papers, citations, students, dollars).
George's name is never bold in author lists. Unannounced honors (the 2027 Bode Prize) stay off the
site and out of the web CV. Link only to the web CV. Award names start with the giving body. Only
papers in print. The Press page holds press coverage only (awards are on the Bio page). Every page
keeps its search description and works on phones.
