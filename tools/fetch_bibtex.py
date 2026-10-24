#!/usr/bin/env python3
"""Build a BibTeX entry for every publication.

Papers with a DOI get Crossref's BibTeX (cached in site-src/data/bibtex.json, so reruns only
fetch new DOIs). Papers without a DOI get an entry built from the CV fields.
The cite key is normalized to <FirstAuthorSurname><Year><FirstTitleWord>, e.g. Girard2007Approximation.

Usage: python3 tools/fetch_bibtex.py
"""
import concurrent.futures as cf
import json
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site-src", "data")
MAILTO = "pappasg@engineering.upenn.edu"
STOP = {"a", "an", "the", "on", "of", "for", "in", "to", "and", "with", "from", "via", "towards", "toward"}


def ascii_word(s):
    return re.sub(r"[^A-Za-z0-9]", "", unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode())


def cite_key(authors, year, title):
    first = re.split(r",| and ", authors.strip(", "))[0].strip() if authors.strip(", ") else "Pappas"
    surname = ascii_word(re.split(r"\s+", re.sub(r"\(.*?\)", "", first).strip())[-1]) or "Pappas"
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9-]*", title) if w.lower() not in STOP]
    return "%s%s%s" % (surname, year, ascii_word(words[0]).capitalize() if words else "")


def crossref_bibtex(doi):
    url = "https://api.crossref.org/works/%s/transform/application/x-bibtex?mailto=%s" % (urllib.parse.quote(doi, safe="/"), MAILTO)
    for k in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "georgejpappas.org BibTeX (mailto:%s)" % MAILTO})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8").strip()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(1.5 * (k + 1))
        except Exception:
            time.sleep(1.5 * (k + 1))
    return None


def tidy(bib, key):
    """Crossref returns one line; give it our key and one field per line."""
    bib = re.sub(r"^\s*@(\w+)\{[^,]*,", lambda m: "@%s{%s," % (m.group(1).lower(), key), bib, count=1)
    head, _, body = bib.partition(",")
    body = body.strip().rstrip("}").strip()
    fields, depth, cur = [], 0, ""
    for ch in body:
        if ch == "," and depth == 0:
            fields.append(cur.strip())
            cur = ""
            continue
        depth += ch == "{"
        depth -= ch == "}"
        cur += ch
    if cur.strip():
        fields.append(cur.strip())
    keep = []
    for f in fields:
        name = f.split("=", 1)[0].strip().lower()
        if name in ("issn", "isbn", "publisher", "url", "month"):
            continue  # noise for a citation; the DOI is kept
        keep.append("  " + f)
    return head + ",\n" + ",\n".join(keep) + "\n}"


def from_cv(r, key):
    pid, kind, year, pre, post, title, rest = r[:7]
    authors = (pre + "G. J. Pappas" + post).strip().rstrip(",")
    authors = re.sub(r",?\s*(editors?|Committee Chair)\)?$", "", authors)
    names = [n.strip(" ()") for n in re.split(r",\s*| and ", authors) if n.strip(" ()")]
    typ, venue = {"journal": ("article", "journal"), "conf": ("inproceedings", "booktitle"),
                  "chapter": ("incollection", "booktitle"), "book": ("book", "publisher")}.get(kind, ("misc", "howpublished"))
    rest = re.sub(r"^in (Proc\.\s*)?", lambda m: "Proc. " if m.group(1) else "", rest)
    esc = lambda s: s.replace("&", r"\&").replace("%", r"\%")
    if pre.rstrip().endswith("("):  # an organization, e.g. the National Academies (G. J. Pappas, Committee Chair)
        names = ["{%s}" % pre.rstrip(" (")]
    return "@%s{%s,\n  author = {%s},\n  title = {%s},\n  %s = {%s},\n  year = {%s}\n}" % (
        typ, key, " and ".join(names), esc(title), venue, esc(rest), year)


def main():
    rows = json.load(open(os.path.join(DATA, "publications.json"), encoding="utf-8"))
    links = json.load(open(os.path.join(DATA, "pub-links.json"), encoding="utf-8"))
    path = os.path.join(DATA, "bibtex.json")
    cache = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}  # doi -> raw crossref bibtex
    doi_of = {}
    for r in rows:
        doi = r[7] or links.get("%s|%s|%s" % (r[1], r[2], r[5]), {}).get("doi", "")
        if doi:
            doi_of[r[0]] = doi.lower()
    todo = sorted({d for d in doi_of.values() if d not in cache})
    print("DOIs to fetch:", len(todo))
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        for d, b in zip(todo, ex.map(crossref_bibtex, todo)):
            if b:
                cache[d] = b
    json.dump(cache, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True)

    out, keys = {}, {}
    for r in rows:
        key = cite_key(r[3] + "G. J. Pappas" + r[4], r[2], r[5])
        keys[key] = keys.get(key, 0) + 1
        if keys[key] > 1:
            key += "abcdefghij"[keys[key] - 2]
        raw = cache.get(doi_of.get(r[0], ""))
        bib = tidy(raw, key) if raw else from_cv(r, key)
        if raw and re.search(r"author=\{\s*(and\s*)*\}", bib) and r[3].rstrip().endswith("("):
            bib = re.sub(r"author=\{[^}]*\}", "author={{%s}}" % r[3].rstrip(" ("), bib)  # an organization as author
        if raw and re.search(r"author=\{\s*(and\s*)*\}", bib):  # Crossref has no usable authors
            names = [n.strip(" ()") for n in re.split(r",\s*| and ", re.sub(r",?\s*(editors?|Committee Chair)\)?$", "", (r[3] + "G. J. Pappas" + r[4]).strip().rstrip(","))) if n.strip(" ()")]
            bib = re.sub(r"  author=\{[^}]*\}", "  author={%s}" % " and ".join(names), bib) if "author=" in bib else bib.replace(",\n", ",\n  author={%s},\n" % " and ".join(names), 1)
        bib = re.sub(r"(pages=\{[^}]*?)\s*[–—]\s*", r"\1--", bib)
        out[r[0]] = bib
    json.dump(out, open(os.path.join(DATA, "bibtex-by-id.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print("BibTeX entries:", len(out), "| from Crossref:", sum(1 for r in rows if cache.get(doi_of.get(r[0], ""))))


if __name__ == "__main__":
    main()
