import json, re, sys

src = open(sys.argv[1], encoding="utf-8").read()


def block(name):
    a = src.index("\\cvsub{%s" % name)
    b = src.index("\\begin{enumerate}", a)
    c = src.index("\\end{enumerate}", b)
    body = src[b + len("\\begin{enumerate}"):c]
    out = []
    for part in re.split(r"\n(?=\\item\[)", "\n" + body):
        m = re.match(r"\s*\\item\[([A-Za-z]+\d+)\.?\]\s*(.*)", part, re.S)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


ACCENTS = [("\\'e", "\u00e9"), ("\\'E", "\u00c9"), ("\\`a", "\u00e0"), ("\\`e", "\u00e8"), ('\\"o', "\u00f6"), ('\\"u', "\u00fc"), ('\\"a', "\u00e4"),
           ("\\'a", "\u00e1"), ("\\'o", "\u00f3"), ("\\'i", "\u00ed"), ("\\'\\i", "\u00ed"), ("\\c{c}", "\u00e7"), ("\\~a", "\u00e3"), ("\\o ", "\u00f8"),
           ("\\'{e}", "\u00e9"), ("\\`{e}", "\u00e8"), ('\\"{o}', "\u00f6"), ('\\"{u}', "\u00fc"), ('\\"{a}', "\u00e4"), ("\\'{a}", "\u00e1"), ("\\'{o}", "\u00f3"), ("\\'{i}", "\u00ed")]


def tex(s):
    s = re.sub(r"(?<!\\)%[^\n]*", "", s)
    s = s.replace("\\looseness=-1", "").replace("\\fitpar", "")
    s = re.sub(r"\\href\{[^}]*\}\{\\nolinkurl\{([^}]*)\}\}", r"\1", s)  # DOI:~\href{https://doi.org/x}{\nolinkurl{x}} -> x
    s = re.sub(r"\\url\{([^}]*)\}", r"\1", s)
    for a, b in ACCENTS:  # before quotes, so \`e and \'e are not turned into curly quotes first
        s = s.replace(a, b)
    s = s.replace("``", "\u201c").replace("''", "\u201d").replace("`", "\u2018").replace("'", "\u2019")
    s = s.replace("---", "\u2014").replace("--", "\u2013").replace("~", " ").replace("\\&", "&").replace("\\%", "%")
    s = s.replace("\\ ", " ").replace("\\,", " ")
    return s


def plain(s):
    s = re.sub(r"\\highlight\{([^}]*)\}", r"[[\1]]", s)
    s = re.sub(r"\\emph\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\[a-zA-Z]+\s*", "", s)
    s = s.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", s).strip()


TYPES = [("Books and Edited Volumes", "book"), ("Refereed Journal Publications", "journal"), ("Refereed Book Chapters", "chapter"),
         ("Refereed Conference Proceedings", "conf"), ("Editorials", "editorial"), ("White Papers and Essays", "white")]
out, bad = [], []
for sec, kind in TYPES:
    for pid, raw in block(sec):
        raw = tex(raw)
        body = plain(raw)
        awards = re.findall(r"\[\[(.*?)\]\]", body)
        body = re.sub(r"\s*\[\[.*?\]\];?", "", body).strip().rstrip("}").strip()
        doi = re.search(r"DOI: ?(\S+?)\.?$", body)
        doi = doi.group(1) if doi else ""
        body = re.sub(r"\s*DOI: ?\S+$", "", body).rstrip(".").strip()
        m = re.match(r"(.*?), \u201c(.*?),?\u201d,? (.*)", body)
        if m:
            authors, title, rest = m.groups()
            title = title.rstrip(",")
        else:  # books: authors, Title (emph), rest
            em = re.search(r"\\emph\{([^}]*)\}", raw)
            if not em:
                bad.append(pid); continue
            title = plain(em.group(1))
            i = body.find(title)
            authors, rest = body[:i].rstrip(", "), body[i + len(title):].lstrip(", ")
        ys = re.findall(r"\b(19\d\d|20\d\d)\b", rest)
        year = int(ys[-1]) if ys else 0
        if "G. J. Pappas" in authors:
            pre, post = authors.split("G. J. Pappas", 1)
        else:
            pre, post = authors + (", " if authors else ""), ""
        rest = rest.replace("in Proceedings of the ", "in Proc. ").replace("in Proceedings of ", "in Proc. ")
        out.append([pid, kind, year, pre, post, title, rest, doi, "; ".join(awards)])
print(len(out), "entries; unparsed:", bad, file=sys.stderr)
from collections import Counter
print(Counter(x[1] for x in out), file=sys.stderr)
print("no year:", [x[0] for x in out if not x[2]], file=sys.stderr)
print("awards:", [(x[0], x[8]) for x in out if x[8]], file=sys.stderr)
json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
