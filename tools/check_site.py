#!/usr/bin/env python3
"""Site checks run after every build: links, ids, descriptions, menu order and the standing rules
(no Bode Prize, no full-CV link, no bold name, no counts or dollars, nothing 'to appear').
Exits 1 if anything is found. The book's publication date is allowed to say forthcoming."""
import sys
import os,re,html,json,glob,collections
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pages=[p for p in glob.glob(R+'/**/index.html',recursive=True) if '/site-src/' not in p and '/node_modules/' not in p]
issues=[]
navexp=['Home','Bio','Research','Group','Publications','Book','Teaching','Press']
for p in pages:
    s=open(p,encoding='utf-8').read(); rel=os.path.relpath(p,R)
    if 'http-equiv="refresh"' in s: continue
    if not re.search(r'<meta name="description" content="[^"]{50,}"',s): issues.append((rel,'description'))
    if 'name="viewport"' not in s: issues.append((rel,'viewport'))
    nav=re.search(r'class="nav-full"(.*?)</nav>',s,re.S)
    if nav:
        labels=[html.unescape(x).strip() for x in re.findall(r'<a [^>]*>([^<]+)</a>',nav.group(1))]
        labels=[l for l in labels if l in navexp]
        if labels!=navexp: issues.append((rel,'nav',labels))
    for pat,why in [(r'Bode','Bode'),(r'resume\.pdf','full CV link'),(r'<(b|strong)>[^<]*Pappas','bold name'),
                    (r'\b\d[\d,]*\+?\s+(papers|publications|citations|students|Ph\.?D\.? students|journal|conference|patents)\b','count'),
                    (r'\$\s?\d','dollars'),(r'to appear|forthcoming|in press|submitted|under review','not in print'),(r'\[(Your|Project|Story)[^\]]*\]','placeholder'),(r'\{\{','template leak'),(r'<sc-','template leak')]:
        for m in re.finditer(pat,s,re.I): issues.append((rel,why,s[max(0,m.start()-60):m.end()+40].replace('\n',' ')))
    ids=collections.Counter(re.findall(r'\sid="([^"]+)"',s))
    for k,v in ids.items():
        if v>1: issues.append((rel,'dup id',k))
    for a in re.findall(r'(?:href|src)="([^"#:?]+?)([?#][^"]*)?"',s):
        u=a[0]
        if u.startswith(('http','mailto','//','data')): continue
        t=os.path.normpath(os.path.join(os.path.dirname(p),u))
        if os.path.isdir(t): t=os.path.join(t,'index.html')
        if not os.path.exists(t): issues.append((rel,'broken',u))
    for a in re.findall(r'href="#([^"]+)"',s):
        if a not in ids: issues.append((rel,'anchor',a))
    for img in re.findall(r'<img [^>]*>',s):
        if 'alt=' not in img: issues.append((rel,'no alt',img[:80]))
book = lambda i: i[1] == 'not in print' and ('Linear Systems Theory' in i[2] or 'Pella Press' in i[2] or 'January 1, 2027' in i[2])
price = lambda i: i[1] == 'dollars' and 'on Amazon' in i[2]  # the book's list price is fine
issues = [i for i in issues if not book(i) and not price(i)]
for i in issues: print(i)
print(len(pages), 'pages', len(issues), 'issues')
sys.exit(1 if issues else 0)
