#!/usr/bin/env python3
"""Monthly update: add newly published papers from ORCID that are not yet in the CV.

Only published work is added: an ORCID record with a DOI (not an arXiv DOI) whose Crossref
record is a journal article, proceedings paper, book chapter or book with a publication date.
Preprints, posted content and works without a DOI are skipped.

Each new paper is written to site-src/data/orcid-additions.json in the same row format as
publications.json, with a stable id ("O" + running number) and its Crossref BibTeX. The build
shows these alongside the CV entries and drops any addition once the CV lists the same paper
(same DOI or same title), so nothing appears twice after the CV is updated.

Usage: python3 tools/sync_orcid.py        (prints what it added; exits 0 either way)
"""
import datetime
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site-src", "data")
ORCID = "0000-0001-9081-0637"
MAILTO = "pappasg@engineering.upenn.edu"
UA = {"User-Agent": "georgejpappas.org monthly ORCID sync (mailto:%s)" % MAILTO}
KINDS = {"journal-article": "journal", "proceedings-article": "conf", "book-chapter": "chapter", "book": "book"}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]


def get(url, accept="application/json", tries=4):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers=dict(UA, Accept=accept))
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read().decode("utf-8")
                return json.loads(data) if accept == "application/json" else data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 * (k + 1))
        except Exception:
            time.sleep(2 * (k + 1))
    return None


def norm(s):
    s = unicodedata.normalize("NFKD", html.unescape(re.sub(r"<[^>]+>", "", s or ""))).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def known():
    """DOIs and normalized titles already on the site (CV rows and their found DOIs)."""
    rows = json.load(open(os.path.join(DATA, "publications.json"), encoding="utf-8"))
    links = json.load(open(os.path.join(DATA, "pub-links.json"), encoding="utf-8"))
    dois = {(r[7] or "").lower() for r in rows} | {(v.get("doi") or "").lower() for v in links.values()}
    return dois - {""}, {norm(r[5]) for r in rows}


def initials(given):
    parts = re.split(r"[\s]+", (given or "").strip())
    out = []
    for p in parts:
        if not p:
            continue
        out.append("-".join(q[0] + "." for q in p.split("-") if q))
    return " ".join(out)


def row_from_crossref(m, pid):
    kind = KINDS.get(m.get("type"))
    date = (m.get("published-print") or m.get("published-online") or m.get("issued") or {}).get("date-parts", [[None]])[0]
    if not kind or not date or not date[0]:
        return None
    authors = [(initials(a.get("given")) + " " + a.get("family", "")).strip() for a in m.get("author", []) if a.get("family")]
    me = next((i for i, a in enumerate(m.get("author", [])) if norm(a.get("family")) == "pappas"), None)
    if me is None:
        return None
    authors[me] = "G. J. Pappas"
    full = ", ".join(authors[:-1]) + " and " + authors[-1] if len(authors) > 1 else authors[0]
    pre, _, post = full.partition("G. J. Pappas")
    venue = (m.get("container-title") or [""])[0]
    bits = [("in Proc. " if kind == "conf" else "in " if kind == "chapter" else "") + venue] if venue else []
    if m.get("volume"):
        bits.append("vol. " + m["volume"])
    if m.get("issue"):
        bits.append("no. " + m["issue"])
    if m.get("page"):
        bits.append(("pp. " if "-" in m["page"] else "p. ") + m["page"].replace("-", "–"))
    when = (MONTHS[date[1] - 1] + " " if len(date) > 1 and date[1] else "") + str(date[0])
    bits.append(when)
    title = html.unescape(re.sub(r"<[^>]+>", "", (m.get("title") or [""])[0])).strip()
    row = [pid, kind, int(date[0]), pre, post, title, ", ".join(b for b in bits if b), m["DOI"], ""]
    row_from_crossref.parts = {"venue": venue, "after": ", ".join(b for b in bits[1 if venue else 0:] if b)}
    return row


def main():
    path = os.path.join(DATA, "orcid-additions.json")
    adds = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else []
    have_dois, have_titles = known()
    have_dois |= {a["row"][7].lower() for a in adds}
    have_titles |= {norm(a["row"][5]) for a in adds}
    works = get("https://pub.orcid.org/v3.0/%s/works" % ORCID)
    if not works:
        print("ORCID unreachable; nothing changed")
        return
    this_year = datetime.date.today().year
    added = []
    for g in works.get("group", []):
        s = g["work-summary"][0]
        ids = (s.get("external-ids") or {}).get("external-id", [])
        doi = next((e["external-id-value"].lower() for e in ids if e["external-id-type"] == "doi"), "")
        year = ((s.get("publication-date") or {}).get("year") or {}).get("value")
        title = s["title"]["title"]["value"]
        if not doi or doi.startswith("10.48550") or "arxiv" in doi or not year or int(year) < this_year - 1:
            continue
        if doi in have_dois or norm(title) in have_titles:
            continue
        m = (get("https://api.crossref.org/works/%s?mailto=%s" % (urllib.parse.quote(doi, safe="/"), MAILTO)) or {}).get("message")
        if not m or m.get("type") in ("posted-content", "peer-review", "component"):
            continue
        pid = "O%d" % (len(adds) + 1)
        row = row_from_crossref(m, pid)
        if not row:
            continue
        bib = get("https://api.crossref.org/works/%s/transform/application/x-bibtex" % urllib.parse.quote(doi, safe="/"),
                  accept="application/x-bibtex") or ""
        adds.append({"row": row, "bib": bib.strip(), "added": datetime.date.today().isoformat(), **row_from_crossref.parts})
        have_dois.add(doi)
        have_titles.add(norm(row[5]))
        added.append(row)
    json.dump(adds, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for r in added:
        print("added", r[0], r[2], r[5], "|", r[7])
    print("new published papers from ORCID:", len(added), "| total additions on file:", len(adds))


if __name__ == "__main__":
    sys.exit(main())
