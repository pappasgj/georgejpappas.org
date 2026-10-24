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

## Monthly update

`tools/monthly_update.sh` refreshes the publication list from published sources only — no preprints:

1. `tools/sync_orcid.py` adds papers published on ORCID (with a non-arXiv DOI whose Crossref record is a journal article, proceedings paper, chapter or book) that the CV does not list yet, to `site-src/data/orcid-additions.json` (ids O1, O2, …). An addition disappears from the site automatically once the CV lists the same paper.
2. `tools/find_proceedings.py` links papers without a DOI to their PMLR or NeurIPS proceedings pages.
3. `tools/fetch_bibtex.py` fetches BibTeX for new DOIs.
4. `./build.sh`, then `tools/check_site.py` (links, ids, descriptions, menu order and the standing rules).

Review `git diff`, then commit and push. A scheduled task runs this on the first of each month.
