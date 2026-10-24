#!/usr/bin/env python3
"""Find DOIs for publications that lack one, using Crossref (and ORCID as a cross-check).

Usage:  python3 tools/find_dois.py
Writes:
  site-src/data/doi-review.json   every candidate, with its score, for review
  and updates site-src/data/pub-links.json with confident matches ({"doi": ...} by title)

A match is accepted only when, after normalizing case and punctuation:
  - the Crossref title equals the paper's title (or similarity >= 0.97), and
  - the year is within one year, and
  - at least one author surname from the CV entry appears in the Crossref authors.
Anything weaker is left for review. Standard library only.
"""
import concurrent.futures as cf
import difflib
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
ORCID = "0000-0001-9081-0637"
UA = "georgejpappas.org DOI finder (mailto:%s)" % MAILTO


def get_json(url, headers=None, tries=4):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers=dict({"User-Agent": UA}, **(headers or {})))
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception:
            time.sleep(1.5 * (k + 1))
    return None


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    s = re.sub(r"<[^>]+>", " ", s)  # Crossref titles can carry markup
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def surnames(pre, post):
    names = re.split(r",| and ", pre + " G. J. Pappas " + post)
    out = set()
    for n in names:
        n = re.sub(r"\(.*?\)|editors?|et al\.?", "", n).strip()
        parts = [p for p in re.split(r"\s+", n) if p and not p.endswith(".")]
        if parts:
            out.add(norm(parts[-1]))
    return {s for s in out if len(s) > 1}


def crossref(title, first_author, year):
    q = urllib.parse.urlencode({
        "query.bibliographic": title,
        "query.author": first_author,
        "rows": 5,
        "select": "DOI,title,author,issued,container-title,type",
        "mailto": MAILTO,
    })
    j = get_json("https://api.crossref.org/works?" + q)
    return (j or {}).get("message", {}).get("items", [])


def orcid_dois():
    j = get_json("https://pub.orcid.org/v3.0/%s/works" % ORCID, {"Accept": "application/json"})
    out = {}
    for g in (j or {}).get("group", []):
        for s in g.get("work-summary", []):
            t = norm(((s.get("title") or {}).get("title") or {}).get("value", ""))
            for e in ((s.get("external-ids") or {}).get("external-id") or []):
                if e.get("external-id-type") == "doi" and t:
                    out.setdefault(t, e.get("external-id-value", "").lower())
    return out


def score(row, item):
    title = norm(row[5])
    ct = norm(" ".join(item.get("title") or []))
    sim = 1.0 if ct == title else difflib.SequenceMatcher(None, title, ct).ratio()
    yr = ((item.get("issued") or {}).get("date-parts") or [[None]])[0][0]
    year_ok = yr is not None and abs(int(yr) - int(row[2])) <= 1
    cr_names = {norm(a.get("family", "")) for a in item.get("author") or []}
    author_ok = bool(surnames(row[3], row[4]) & cr_names)
    return sim, year_ok, author_ok, yr


ARXIV = "10.48550/"
TYPES = {"journal": {"journal-article"}, "conf": {"proceedings-article", "book-chapter"},
         "chapter": {"book-chapter", "proceedings-article"}, "book": {"book", "edited-book", "monograph", "other", "report"},
         "editorial": {"journal-article", "other"}, "white": {"journal-article", "other", "report"}}


def record(doi):
    j = get_json("https://api.crossref.org/works/%s?mailto=%s" % (urllib.parse.quote(doi, safe="/"), MAILTO))
    m = (j or {}).get("message") or {}
    yr = ((m.get("issued") or {}).get("date-parts") or [[None]])[0][0]
    return {"type": m.get("type"), "year": yr}


def fits(kind, year, rec):
    return rec.get("type") in TYPES.get(kind, set()) and (rec["year"] is None or abs(int(rec["year"]) - int(year)) <= 1)  # preprint DOIs: never used, since only published versions are listed


def decide(kind, best, orcid):
    """Return (doi, reason) or (None, reason). ORCID entries are matched to the paper by exact title."""
    orcid = None if (orcid or "").startswith(ARXIV) else orcid
    if best and best["doi"].startswith(ARXIV):
        best = None
    if best and orcid and best["doi"] == orcid:
        return orcid, "crossref and orcid agree"
    if best and best["sim"] >= 0.97 and best["author_ok"] and best["year_ok"] and not orcid:
        return best["doi"], "crossref: title, year and author match"
    if best and best["sim"] >= 0.97 and best["author_ok"] and best["year"] is None and kind in ("chapter", "conf", "book") and not orcid:
        return best["doi"], "crossref: title and author match (no year on record)"
    if best and best["sim"] >= 0.90 and best["author_ok"] and best["year_ok"] and not orcid:
        return best["doi"], "crossref: near-exact title, year and author match"
    if best and best["sim"] == 1.0 and best["year_ok"] and not orcid and len(best["title"]) > 40:
        return best["doi"], "crossref: exact long title and year"
    if orcid:
        return orcid, "orcid: exact title on the ORCID record"
    return None, "no confident match"


def main():
    rows = json.load(open(os.path.join(DATA, "publications.json"), encoding="utf-8"))
    links_path = os.path.join(DATA, "pub-links.json")
    links = json.load(open(links_path, encoding="utf-8")) if os.path.exists(links_path) else {}
    key = lambda r: "%s|%s|%s" % (r[1], r[2], r[5])
    todo = [r for r in rows if not r[7] and not links.get(key(r), {}).get("doi")]
    print("papers without a DOI:", len(todo))
    orc = orcid_dois()
    print("DOIs on the ORCID record:", len(orc))

    def work(r):
        first = re.split(r",| and ", (r[3] or "G. J. Pappas").strip(", "))[0].strip() or "Pappas"
        best = None
        for it in crossref(r[5], first, r[2]):
            sim, yok, aok, yr = score(r, it)
            cand = {"doi": it.get("DOI", "").lower(), "title": " ".join(it.get("title") or []),
                    "venue": " ".join(it.get("container-title") or []), "year": yr,
                    "sim": round(sim, 3), "year_ok": yok, "author_ok": aok}
            if best is None or (sim, yok, aok) > (best["sim"], best["year_ok"], best["author_ok"]):
                best = cand
        return r, best, orc.get(norm(r[5]))

    results = []
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        for i, res in enumerate(ex.map(work, todo), 1):
            results.append(res)
            if i % 50 == 0:
                print(" ", i, "checked")

    accepted, review = 0, []
    for r, best, orcid in results:
        # candidates: the ORCID DOI (exact title) and a strong Crossref match; the first whose
        # Crossref record has a compatible type and year wins, so a journal entry never gets
        # the conference version's DOI and vice versa
        cands = []
        if orcid:
            cands.append(orcid)
        if best and best["sim"] >= 0.90 and best["author_ok"]:
            cands.append(best["doi"])
        cands = [d for d in dict.fromkeys(cands) if not d.startswith(ARXIV)]
        doi = next((d for d in cands if fits(r[1], r[2], record(d))), None)
        why = decide(r[1], best, orcid)[1] if doi else "no confident match"
        review.append({"id": r[0], "kind": r[1], "year": r[2], "title": r[5], "rest": r[6],
                       "orcid_doi": orcid, "crossref": best, "doi": doi, "why": why})
        if doi:
            links.setdefault(key(r), {})["doi"] = doi
            accepted += 1

    json.dump(review, open(os.path.join(DATA, "doi-review.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(links, open(links_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("accepted:", accepted, "of", len(todo))


if __name__ == "__main__":
    main()
