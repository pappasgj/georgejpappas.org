#!/usr/bin/env python3
"""Link papers that have no DOI to their open proceedings page (PMLR and NeurIPS).

PMLR covers ICML, L4DC, CoRL, AISTATS, COLT and UAI. For each paper without a DOI or link,
the script finds the PMLR volume(s) of that conference and year, reads the volume page, and
accepts a match only when the normalized title is identical and an author surname from the
CV appears in the PMLR author list. NeurIPS papers are matched the same way against the
NeurIPS proceedings index for that year.

Writes {"url": abstract page, "pdf": PDF} into site-src/data/pub-links.json ("kind|year|title").
Usage: python3 tools/find_proceedings.py
"""
import html
import json
import os
import re
import unicodedata
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site-src", "data")
UA = {"User-Agent": "georgejpappas.org proceedings finder (mailto:pappasg@engineering.upenn.edu)"}
PMLR = [  # (pattern in the CV venue, words that identify the PMLR volume name)
    (r"International Conference on Machine Learning|\(ICML\)", ["icml", "international conference on machine learning"]),
    (r"Learning for Dynamics|L4DC", ["l4dc", "learning for dynamics"]),
    (r"Robot Learning|\(CoRL\)", ["corl", "conference on robot learning"]),
    (r"AISTATS|Artificial Intelligence and Statistics", ["aistats", "artificial intelligence and statistics"]),
    (r"Learning Theory|\(COLT\)", ["colt", "conference on learning theory"]),
    (r"Uncertainty in Artificial Intelligence|\(UAI\)", ["uai", "uncertainty in artificial intelligence"]),
]
_cache = {}


def get(url):
    if url not in _cache:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=120) as r:
            _cache[url] = r.read().decode("utf-8", "ignore")
    return _cache[url]


def norm(s):
    s = unicodedata.normalize("NFKD", html.unescape(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def surnames(r):
    names = re.split(r",| and ", r[3] + " G. J. Pappas " + r[4])
    out = set()
    for n in names:
        parts = [p for p in re.split(r"\s+", re.sub(r"\(.*?\)|et al\.?", "", n).strip()) if p and not p.endswith(".")]
        if parts:
            out.add(norm(parts[-1]))
    return {s for s in out if len(s) > 1}


def pmlr_volumes():
    s = get("https://proceedings.mlr.press/")
    return [(v, html.unescape(name).lower()) for v, name in re.findall(r'<a href="(v\d+)"><b>Volume \d+</b></a>\s*([^<]+)', s)]


def pmlr_papers(vol):
    s = get("https://proceedings.mlr.press/%s/" % vol)
    out = []
    for block in re.findall(r'<div class="paper">(.*?)</div>', s, re.S):
        t = re.search(r'<p class="title">(.*?)</p>', block, re.S)
        a = re.search(r'<span class="authors">(.*?)</span>', block, re.S)
        abs_ = re.search(r'href="(https://proceedings\.mlr\.press/%s/[^"]+\.html)"' % vol, block)
        pdf = re.search(r'href="(https://proceedings\.mlr\.press/%s/[^"]+\.pdf)"' % vol, block)
        if t and abs_:
            out.append({"title": norm(re.sub(r"<[^>]+>", "", t.group(1))),
                        "authors": norm(re.sub(r"<[^>]+>", " ", a.group(1) if a else "")),
                        "url": abs_.group(1), "pdf": pdf.group(1) if pdf else ""})
    return out


def neurips_papers(year):
    s = get("https://proceedings.neurips.cc/paper_files/paper/%d" % year)
    out = []
    for href, title, authors in re.findall(r'<a title="paper title" href="([^"]+)">(.*?)</a>.*?<i>(.*?)</i>', s, re.S):
        url = "https://proceedings.neurips.cc" + href
        out.append({"title": norm(title), "authors": norm(authors), "url": url,
                    "pdf": url.replace("/hash/", "/file/").replace("-Abstract", "-Paper").replace(".html", ".pdf")})
    return out


def main():
    rows = json.load(open(os.path.join(DATA, "publications.json"), encoding="utf-8"))
    path = os.path.join(DATA, "pub-links.json")
    links = json.load(open(path, encoding="utf-8"))
    key = lambda r: "%s|%s|%s" % (r[1], r[2], r[5])
    todo = [r for r in rows if not r[7] and not links.get(key(r), {}).get("doi") and not links.get(key(r), {}).get("url")]
    vols = pmlr_volumes()
    found, missed = [], []
    for r in todo:
        cands = []
        for pat, words in PMLR:
            if re.search(pat, r[6]):
                for yr in (r[2], r[2] - 1, r[2] + 1):
                    for v, name in vols:
                        if str(yr) in name and any(w in name for w in words) and "workshop" not in name:
                            cands.append(("pmlr", v))
                m = re.search(r"PMLR vol\. (\d+)|vol\. (\d+) of Proceedings of Machine Learning Research", r[6])
                if m:
                    cands.insert(0, ("pmlr", "v" + (m.group(1) or m.group(2))))
        if re.search(r"Neural Information Processing Systems|NeurIPS", r[6]):
            cands.append(("neurips", r[2]))
        hit = None
        for src, ref in dict.fromkeys(cands):
            try:
                papers = pmlr_papers(ref) if src == "pmlr" else neurips_papers(ref)
            except Exception as e:
                print("  could not read", src, ref, e)
                continue
            names = surnames(r)
            for p in papers:
                if p["title"] == norm(r[5]) and any(n in p["authors"] for n in names):
                    hit = p
                    break
            if hit:
                break
        if hit:
            e = links.setdefault(key(r), {})
            e["url"] = hit["url"]
            if hit["pdf"]:
                e["pdf"] = hit["pdf"]
            found.append((r[0], r[5], hit["url"]))
        elif cands:
            missed.append((r[0], r[5]))
    json.dump(links, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for f in found:
        print("linked", f[0], f[1][:60], f[2])
    for m in missed:
        print("not found", m[0], m[1][:70])
    print("linked:", len(found), "| searched but not found:", len(missed))


if __name__ == "__main__":
    main()
