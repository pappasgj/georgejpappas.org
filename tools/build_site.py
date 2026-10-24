#!/usr/bin/env python3
"""Build georgejpappas.org from site-src/ into static HTML at the repository root.

Standard library only. Templates use the same small syntax as the approved design:
  {{name.field}}                         value, HTML-escaped
  <sc-for list="{{items}}" as="x"> ... </sc-for>
  <sc-if value="{{flag}}"> ... </sc-if>   rendered when the value is truthy

Usage: python3 tools/build_site.py            (run from anywhere)
"""
import datetime
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "site-src")
DATA = os.path.join(SRC, "data")

SITE_URL = "https://www.georgejpappas.org/"
SCHOLAR = "https://scholar.google.com/citations?user=Kia-4B0AAAAJ"

# (key, menu label, output folder, title, search description)
PAGES = [
    ("home", "Home", "", "George J. Pappas — Home",
     "George J. Pappas, UPS Foundation Professor of Electrical and Systems Engineering at the University of Pennsylvania. Research on safe physical AI, trustworthy AI, learning and control, layered control, formal methods and multi-robot systems."),
    ("bio", "Bio", "bio", "George J. Pappas — Bio",
     "Biography, appointments, education and honors of George J. Pappas, University of Pennsylvania."),
    ("research", "Research", "research", "George J. Pappas — Research",
     "Research of George J. Pappas: safe physical AI, trustworthy AI, learning and control, layered control, formal methods for safe autonomy and multi-robot systems."),
    ("group", "Group", "group", "George J. Pappas — Group",
     "Current members and alumni of George J. Pappas’s research group at the University of Pennsylvania."),
    ("publications", "Publications", "publications", "George J. Pappas — Publications",
     "All publications of George J. Pappas, newest first, with links to PDFs, DOIs and Google Scholar."),
    ("book", "Book", "book", "George J. Pappas — Book",
     "Linear Systems Theory: From Linear Algebra to the Kalman Filter by George J. Pappas. Pella Press, January 2027. Paperback and free PDF."),
    ("teaching", "Teaching", "teaching", "George J. Pappas — Teaching",
     "Courses taught by George J. Pappas at the University of Pennsylvania, including ESE 5000 Linear Systems Theory."),
    ("news", "News & Press", "news", "George J. Pappas — News & Press",
     "Awards, press coverage and news about George J. Pappas and his research group."),
]

# ---------------------------------------------------------------- template engine

_TAG = re.compile(r"<(/?)(sc-for|sc-if)\b([^>]*)>")
_VAR = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")


def _attr(attrs, name):
    m = re.search(r'\b%s="([^"]*)"' % name, attrs)
    return m.group(1) if m else None


def parse(src):
    root = []
    stack = [("root", None, root)]
    pos = 0
    for m in _TAG.finditer(src):
        stack[-1][2].append(src[pos:m.start()])
        pos = m.end()
        closing, tag, attrs = m.group(1), m.group(2), m.group(3)
        if closing:
            kind, info, children = stack.pop()
            if kind != tag:
                raise ValueError("mismatched </%s>" % tag)
            stack[-1][2].append((kind, info, children))
        else:
            if tag == "sc-for":
                info = (_VAR.fullmatch(_attr(attrs, "list")).group(1), _attr(attrs, "as"))
            else:
                info = _VAR.fullmatch(_attr(attrs, "value")).group(1)
            stack.append((tag, info, []))
    if len(stack) != 1:
        raise ValueError("unclosed <%s>" % stack[-1][0])
    root.append(src[pos:])
    return root


def lookup(expr, ctx):
    parts = expr.split(".")
    if parts[0] in ("true", "false"):
        return parts[0] == "true"
    val = ctx.get(parts[0])
    for p in parts[1:]:
        val = val.get(p) if isinstance(val, dict) else None
    return val


def _text(val):
    if val is None:
        return ""
    if val is True:
        return "true"
    if val is False:
        return "false"
    return str(val)


def render_nodes(nodes, ctx):
    out = []
    for n in nodes:
        if isinstance(n, str):
            out.append(_VAR.sub(lambda m: html.escape(_text(lookup(m.group(1), ctx)), quote=True), n))
        elif n[0] == "sc-for":
            expr, var = n[1]
            for item in lookup(expr, ctx) or []:
                out.append(render_nodes(n[2], dict(ctx, **{var: item})))
        else:
            if lookup(n[1], ctx):
                out.append(render_nodes(n[2], ctx))
    return "".join(out)


def render(src, ctx):
    return render_nodes(parse(src), ctx)


# ---------------------------------------------------------------- data helpers

def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def flags(rows, **extra):
    out = []
    for r in rows:
        r = dict(r)
        r["hasUrl"], r["noUrl"] = bool(r.get("url")), not r.get("url")
        r["hasLabel"] = bool(r.get("label"))
        r["hasLabelUrl"] = bool(r.get("label") and r.get("labelUrl"))
        r["plainLabel"] = bool(r.get("label") and not r.get("labelUrl"))
        r["hasAward"] = bool(r.get("award"))
        r["hasNote"] = bool(r.get("note"))
        r.update(extra)
        out.append(r)
    return out


def initials(name):
    words = [w for w in re.split(r"[\s.]+", name) if w and w[0].isalpha()]
    return (words[0][0] + words[-1][0]).upper() if len(words) > 1 else name[:2].upper()


MONTHS = {m: i + 1 for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split())}
VENUE_MONTH = [
    (r"NeurIPS|Neural Information Processing|\(CDC\)|Decision and Control", 12),
    (r"CoRL|Robot Learning|IJCNLP|AACL", 11),
    (r"IROS|Intelligent Robots and Systems", 10),
    (r"ICML|Machine Learning \(ICML\)|IFAC World Congress|\(RSS\)", 7),
    (r"L4DC|Learning for Dynamics|\(ACC\)|American Control|\(ECC\)", 6),
    (r"ICRA|Robotics and Automation|AISTATS|ICLR|Learning Representations", 5),
    (r"SaTML|HSCC|ICCPS", 4),
    (r"AAAI|Artificial Intelligence, pp", 2),
]
_MONTH_RE = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December|"
                       r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\.?(?:\s*[-–]\s*[A-Za-z]+\.?)?\s+\d{4}\s*$")


def month_of(rest):
    m = _MONTH_RE.search(rest or "")
    if m:
        return MONTHS[m.group(1)[:3].lower()]
    for pat, mon in VENUE_MONTH:
        if re.search(pat, rest or ""):
            return mon
    return 6.5


PUB_KIND = {"journal": "journal", "conf": "conf", "chapter": "chapter", "book": "book", "editorial": "other", "white": "other"}


def publications():
    rows = load("publications.json")
    links = load("pub-links.json") if os.path.exists(os.path.join(DATA, "pub-links.json")) else {}
    for r in rows:  # PDFs and publisher pages kept by title in pub-links.json
        extra = links.get(r[5], {})
        r[9:] = [extra.get("pdf", r[9] if len(r) > 9 else ""), extra.get("url", r[10] if len(r) > 10 else "")]
    order = {r[0]: i for i, r in enumerate(rows)}
    rows = sorted(rows, key=lambda r: (-r[2], -month_of(r[6]), order[r[0]]))
    years = []
    for r in rows:
        pid, kind, year, pre, post, title, rest, doi, award = r[:9]
        pdf = r[9] if len(r) > 9 else ""
        url = r[10] if len(r) > 10 else ""
        doi_url = "https://doi.org/" + doi if doi else ""
        scholar = "https://scholar.google.com/scholar?q=" + _quote('"' + title + '"')
        item = {
            "id": pid, "pre": pre, "me": "G. J. Pappas", "post": post, "title": title, "rest": rest,
            "award": award, "hasAward": bool(award), "pdf": pdf, "hasPdf": bool(pdf),
            "doiUrl": doi_url, "hasDoi": bool(doi), "url": url, "hasUrl": bool(url),
            "scholar": scholar, "titleUrl": pdf or doi_url or url or scholar,
            "kind": PUB_KIND.get(kind, "other"), "awardFlag": "1" if award else "",
            "search": " ".join([pid, pre, "G. J. Pappas", post, title, rest]).lower(),
        }
        if years and years[-1]["year"] == year:
            years[-1]["items"].append(item)
        else:
            years.append({"year": year, "items": [item]})
    for i, y in enumerate(years):
        y["open"] = i < 2
        y["openAttr"] = "open" if i < 2 else ""
    return years


def _quote(s):
    from urllib.parse import quote
    return quote(s, safe="")


# ---------------------------------------------------------------- page contexts

def ctx_home():
    d = load("home.json")
    return {"selected": flags(d["selected"]), "latest": flags(d["latest"]), "feed": flags(d["feed"])}


def ctx_bio():
    return load("bio.json")


def ctx_research():
    d = load("research.json")
    areas = []
    for i, a in enumerate(d["areas"]):
        projects = [f for f in d["funding"] if i in f["areas"]]
        areas.append(dict(a, index=i, first=i == 0, hidden=i != 0, selected="true" if i == 0 else "false",
                          projects=projects, hasProjects=bool(projects), hasImg=bool(a.get("img")),
                          noImg=not a.get("img"), papers=flags(a["papers"])))
    funding = [dict(f, areaChips=[{"label": d["areas"][i]["short"], "id": d["areas"][i]["id"], "index": i}
                                  for i in f["areas"]]) for f in d["funding"]]
    return {"areas": areas, "funding": funding}


def ctx_group():
    d = load("group.json")
    current = [dict(m, initials=initials(m["name"]), noUrl=not m.get("url"), noPhoto=not m.get("photo")) for m in d["current"]]
    mark = lambda rows: [dict(a, noUrl=not a.get("url")) for a in rows]
    groups = [dict(g, items=mark(g["items"])) for g in d["alumniGroups"]]
    return {"current": current, "alumniGroups": groups, "masters": mark(d["masters"])}


def ctx_publications():
    return {"years": publications()}


def ctx_book():
    return load("book.json")


def ctx_teaching():
    return load("teaching.json")


def ctx_news():
    d = load("news.json")
    labels = {"press": "Press", "honor": "Award", "lab": "Lab"}
    items = flags(sorted(d["items"], key=lambda n: -n["k"]))  # newest first; stable within a month
    for n in items:
        n["kindLabel"] = labels[n["kind"]]
    stories = [dict(s, hasImg=bool(s.get("img"))) for s in sorted(d["stories"], key=lambda s: -s.get("k", 0))]
    return {"items": items, "stories": stories}


# ---------------------------------------------------------------- build

def nav_items(active, root):
    items = []
    for key, label, folder, _, _ in PAGES:
        on = key == active
        items.append({
            "label": label,
            "href": root + (folder + "/" if folder else ""),
            "current": "page" if on else "false",
            "style": ("color: #011F5B; border-bottom: 3px solid #990000; padding: 6px 0" if on
                      else "color: #1B1F2A; padding: 6px 0"),
            "mstyle": "padding: 10px 18px; color: " + ("#011F5B" if on else "#1B1F2A"),
            "inFooter": key != "home",
        })
    return items


def main():
    with open(os.path.join(SRC, "layout.html"), encoding="utf-8") as f:
        layout = f.read()
    today = datetime.date.today()
    updated = today.strftime("%B ") + str(today.day) + today.strftime(", %Y")
    for key, label, folder, title, desc in PAGES:
        root = "../" if folder else "./"
        with open(os.path.join(SRC, "pages", key + ".html"), encoding="utf-8") as f:
            body_src = f.read()
        ctx = globals()["ctx_" + key]()
        ctx["root"] = root
        body = render(body_src, ctx)
        page = render(layout, {
            "root": root, "title": title, "description": desc, "isHome": key == "home",
            "canonical": SITE_URL + (folder + "/" if folder else ""), "nav": nav_items(key, root),
            "updated": updated, "year": today.year, "scholar": SCHOLAR, "page": key,
        })
        page = page.replace("<!--BODY-->", body)
        assert "{{" not in page and "<sc-" not in page, key
        out_dir = os.path.join(ROOT, folder)
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(page)
        print("built", (folder or ".") + "/index.html")
    write_sitemap(today)


def write_sitemap(today):
    urls = "".join("  <url><loc>%s</loc><lastmod>%s</lastmod></url>\n" % (SITE_URL + (p[2] + "/" if p[2] else ""), today.isoformat())
                   for p in PAGES)
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "</urlset>\n")
    with open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write("User-agent: *\nDisallow: /site-src/\nDisallow: /tools/\nSitemap: %ssitemap.xml\n" % SITE_URL)
    print("built sitemap.xml, robots.txt")


if __name__ == "__main__":
    sys.exit(main())
