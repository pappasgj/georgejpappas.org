import json, re, sys

src = open(sys.argv[1], encoding="utf-8").read()
lines = src.split("\n")


def clean(s):
    s = re.sub(r"\\url\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\emph\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\highlight\{([^}]*)\}", r"[[\1]]", s)
    s = s.replace("``", "\u201c").replace("''", "\u201d").replace("---", "\u2014").replace("--", "\u2013")
    s = s.replace("~", " ").replace("\\&", "&").replace("\\'e", "\u00e9").replace("\\`a", "\u00e0").replace("\\`e", "\u00e8")
    s = re.sub(r"\\[a-zA-Z]+\s*", "", s)
    s = s.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", s).strip()


def section(start_pat, end_pat):
    i = next(k for k, l in enumerate(lines) if re.search(start_pat, l))
    j = next(k for k in range(i + 1, len(lines)) if re.search(end_pat, lines[k]))
    return lines[i + 1 : j]


def items(block):
    text = "\n".join(block)
    parts = re.split(r"\n\\item(?:\[([^\]]*)\])?", "\n" + text)
    out = []
    for k in range(1, len(parts), 2):
        label = (parts[k] or "").rstrip(".")
        body = parts[k + 1]
        body = re.sub(r"\\end\{enumerate\}.*", "", body, flags=re.S)
        body = body.replace("\\looseness=-1", "").replace("\\fitpar", "")
        body = re.sub(r"%.*", "", body)
        out.append((label, clean(body)))
    return out


def pubs(start, end, kind):
    res = []
    for label, body in items(section(start, end)):
        m = re.match(r"(.*?), \u201c(.*?),\u201d (.*)", body)
        if not m:
            continue
        authors, title, rest = m.groups()
        awards = re.findall(r"\[\[(.*?)\]\]", rest)
        rest = re.sub(r"\s*\[\[.*?\]\];?", "", rest).strip()
        doi = re.search(r"DOI: ?(\S+?)\.?$", rest)
        doi = doi.group(1) if doi else None
        rest = re.sub(r"\s*DOI: ?\S+$", "", rest).rstrip(".")
        years = re.findall(r"(19|20)(\d\d)", rest)
        year = int("".join(years[-1])) if years else None
        res.append({"id": label, "type": kind, "authors": authors, "title": title, "rest": rest, "doi": doi, "awards": awards, "year": year})
    return res


data = {}
data["journal"] = pubs(r"cvsub\{Refereed Journal Publications", r"cvsub\{Refereed Book Chapters", "journal")
data["chapter"] = pubs(r"cvsub\{Refereed Book Chapters", r"cvsub\{Refereed Conference Proceedings", "chapter")
data["conf"] = pubs(r"cvsub\{Refereed Conference Proceedings", r"cvsub\{Editorials", "conf")
data["alumni"] = []
for _, body in items(section(r"cvsub\{Former Ph\.D\. Students and Postdocs", r"cvsub\{Former Masters")):
    m = re.match(r"(.*?), (.*?)\s*Now (.*)", body)
    if m:
        data["alumni"].append({"name": m.group(1), "role": m.group(2).strip(), "now": m.group(3).strip()})
data["lectures"] = [b for _, b in items(section(r"section\{Plenary, Keynote", r"section\{|%\\section"))]
data["press"] = [b for _, b in items(section(r"cvsub\{AI Safety, Jailbreaking", r"section\{Research Funding"))]
data["funding_current"] = [b for _, b in items(section(r"cvsub\{Current\}", r"cvsub\{Previous\}"))]
json.dump(data, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for k, v in data.items():
    print(k, len(v))
