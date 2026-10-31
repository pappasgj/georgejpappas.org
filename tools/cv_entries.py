#!/usr/bin/env python3
"""Write ready-to-paste resume.tex entries for papers the monthly ORCID sync found
that the CV does not list yet (George updates the CV first; the site follows it).

Each entry uses the CV's format: the next free number in its section, the title linked
to its DOI (\\href{https://doi.org/...}{``Title,''}), and the venue in \\emph{}.
Numbers are counted from the CV ids on the site, so if several papers go into one
section they are numbered in a row. Check authors, venue and month before pasting.

Usage: python3 tools/cv_entries.py [OUT]   (default OUT: cv-new-entries.tex, not in git)
Prints how many entries it wrote; writes nothing if there are none.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site-src", "data")
PREFIX = {"journal": "J", "conf": "C", "chapter": "Ch", "book": "B"}
SECTION = {"journal": "Refereed Journal Publications", "conf": "Refereed Conference Proceedings",
           "chapter": "Refereed Book Chapters", "book": "Books and Edited Volumes"}


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def esc(s):
    return re.sub(r"(?<!\\)([&%#_$])", r"\\\1", s).replace("\u2013", "--")


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "cv-new-entries.tex")
    rows = json.load(open(os.path.join(DATA, "publications.json"), encoding="utf-8"))
    path = os.path.join(DATA, "orcid-additions.json")
    adds = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else []
    dois = {(r[7] or "").lower() for r in rows}
    titles = {norm(r[5]) for r in rows}
    nxt = {}
    for k, p in PREFIX.items():
        nums = [int(r[0][len(p):]) for r in rows if r[1] == k and re.fullmatch(p + r"\d+", r[0])]
        nxt[k] = max(nums, default=0) + 1
    lines = {}
    for a in sorted(adds, key=lambda a: (a["row"][2], a["row"][0])):
        r = a["row"]
        if r[7].lower() in dois or norm(r[5]) in titles or r[1] not in PREFIX:
            continue
        k = r[1]
        authors = (r[3] + "G. J. Pappas" + r[4]).strip()
        venue = a.get("venue", "")
        after = a.get("after", r[6])
        title = "\\href{https://doi.org/%s}{``%s,''}" % (r[7], esc(r[5]))
        if venue:
            where = ("in " if k in ("conf", "chapter") else "") + "\\emph{%s}" % esc(venue) + (", " + esc(after) if after else "")
        else:
            where = esc(after)
        cid = "%s%d" % (PREFIX[k], nxt[k]); nxt[k] += 1
        lines.setdefault(k, []).append("%% %s on the site; ORCID, added %s\n\\item[%s.]\\looseness=-1 \\fitpar{%s, %s %s.}"
                                       % (r[0], a.get("added", ""), cid, esc(authors), title, where.rstrip(".")))
    n = sum(len(v) for v in lines.values())
    if not n:
        print("no new CV entries")
        return
    with open(out, "w", encoding="utf-8") as f:
        f.write("% New papers for resume.tex, from ORCID. Paste each group at the top of its section\n"
                "% (newest first), then send the updated resume.tex to a website session.\n")
        for k in PREFIX:
            if k in lines:
                f.write("\n%% ---- %s ----\n" % SECTION[k] + "\n\n".join(reversed(lines[k])) + "\n")
    print("wrote", n, "CV entries to", out)


if __name__ == "__main__":
    main()
