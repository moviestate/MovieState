"""One-off post-processor: removes unlicensed-streaming links from the built HTML,
adds an Articles section, and refreshes sitemap.xml."""
import os, re, json, html, urllib.parse

BASE = "https://moviestate.github.io"
stats = {}


def bump(k, n=1):
    stats[k] = stats.get(k, 0) + n


def html_files():
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in (".git", "site", "node_modules")]
        for f in files:
            if f.endswith(".html"):
                yield os.path.join(root, f)


HEADER_OLD = re.compile(r'<a class="btn btn--primary btn--sm header__cta" href="https://moviestate\.is-best\.net/"[^>]*>MovieState Library</a>')
HEADER_NEW = '<a class="btn btn--primary btn--sm header__cta" href="%s/movies/">Browse movies</a>' % BASE
FOOTER_OLD = re.compile(r'<div><h3>Watch</h3><a href="https://moviestate\.is-best\.net/"[^>]*>MovieState library</a><span class="muted">[^<]*</span></div>')
FOOTER_NEW = ('<div><h3>Guides</h3><a href="%s/articles/">Articles</a>'
              '<a href="%s/movies/">All movie guides</a>'
              '<a href="%s/categories/">Categories</a>'
              '<a href="%s/people/">People</a></div>' % (BASE, BASE, BASE, BASE))
CTA_BAND = re.compile(r'<section class="section section--narrow"><div class="panel cta-band">.*?</section>', re.S)
SEE_MORE = re.compile(r'<a class="btn btn--ghost" href="https://moviestate\.is-best\.net/[^"]*"[^>]*>See more options for ([^<]+)</a>')
HERO_WATCH = re.compile(r'<a class="btn btn--primary" href="https://moviestate\.is-best\.net/[^"]*"[^>]*>Watch on MovieState</a>')
OTHER_BTN = re.compile(r'<a class="btn btn--primary" href="https://moviestate\.is-best\.net/[^"]*"[^>]*>(?:Check availability|Open MovieState(?: library)?)</a>')
NAV_ANCHOR = '<a href="%s/people/">People</a>' % BASE
FAQ_OLD = 'Our companion library site, moviestate.is-best.net, is a separate service, and every link to it is marked as sponsored.'
FAQ_NEW = ('We never host, embed or stream video files, and we do not link to unlicensed streaming services. '
           'Watch options point to official providers, or to a legitimate availability index such as JustWatch, '
           'where you can compare official services and current prices.')


def see_more(m):
    title = html.unescape(m.group(1)).strip()
    q = urllib.parse.quote_plus(title)
    return ('<a class="btn btn--ghost" href="https://www.justwatch.com/us/search?q=%s" target="_blank" '
            'rel="noopener">Compare all official providers for %s</a>' % (q, html.escape(title)))


def patch_pages():
    for path in html_files():
        s = open(path, encoding="utf-8").read()
        o = s
        s, n = HEADER_OLD.subn(HEADER_NEW, s); bump("header_cta", n)
        s, n = FOOTER_OLD.subn(FOOTER_NEW, s); bump("footer_col", n)
        s, n = CTA_BAND.subn("", s); bump("cta_band_removed", n)
        s, n = SEE_MORE.subn(see_more, s); bump("see_more", n)
        s, n = HERO_WATCH.subn('<a class="btn btn--primary" href="#watch">Where to watch</a>', s); bump("hero_watch", n)
        s, n = OTHER_BTN.subn('<a class="btn btn--ghost" href="%s/articles/">How we verify watch options</a>' % BASE, s); bump("other_btn", n)
        if NAV_ANCHOR in s and 'href="%s/articles/">Articles</a>' % BASE not in s.split("</header>")[0]:
            s = s.replace(NAV_ANCHOR, NAV_ANCHOR + '<a href="%s/articles/">Articles</a>' % BASE, 1); bump("nav_added", 1)
        if FAQ_OLD in s:
            s = s.replace(FAQ_OLD, FAQ_NEW); bump("faq_text", 1)
        if s != o:
            open(path, "w", encoding="utf-8").write(s); bump("files_changed", 1)


# ---------------------------------------------------------------- articles
def md_inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", t)

    def _link(mm):
        href = mm.group(2).strip()
        if not re.match(r"^(https?://|/|#)", href):
            return mm.group(0)
        href_full = (BASE + href) if href.startswith("/") else href
        rel = ' target="_blank" rel="noopener"' if href.startswith("http") else ""
        return '<a href="%s"%s>%s</a>' % (href_full, rel, mm.group(1))

    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", _link, t)


def md_blocks(md):
    out, buf, lst = [], [], None

    def flush_p():
        if buf:
            out.append("<p>" + md_inline(" ".join(buf).strip()) + "</p>")
            del buf[:]

    def flush_l():
        nonlocal lst
        if lst:
            tag, items = lst
            out.append("<%s>%s</%s>" % (tag, "".join("<li>" + md_inline(i) + "</li>" for i in items), tag))
            lst = None

    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush_p(); flush_l(); continue
        if line.startswith("### "):
            flush_p(); flush_l(); out.append("<h3>" + md_inline(line[4:].strip()) + "</h3>"); continue
        if line.startswith("## "):
            flush_p(); flush_l(); out.append("<h2>" + md_inline(line[3:].strip()) + "</h2>"); continue
        if line.startswith("# "):
            flush_p(); flush_l(); continue
        if re.match(r"^---+\s*$", line):
            flush_p(); flush_l(); out.append("<hr>"); continue
        if line.startswith("> "):
            flush_p(); flush_l(); out.append("<blockquote><p>" + md_inline(line[2:].strip()) + "</p></blockquote>"); continue
        m = re.match(r"^[-*]\s+(.*)$", line)
        if m:
            flush_p()
            if not lst or lst[0] != "ul":
                flush_l(); lst = ("ul", [])
            lst[1].append(m.group(1)); continue
        m = re.match(r"^\d+\.\s+(.*)$", line)
        if m:
            flush_p()
            if not lst or lst[0] != "ol":
                flush_l(); lst = ("ol", [])
            lst[1].append(m.group(1)); continue
        buf.append(line.strip())
    flush_p(); flush_l()
    return "\n".join(out)


def front_matter(text):
    meta, body = {}, text.lstrip()
    if body.startswith("---"):
        end = body.find("\n---", 3)
        if end != -1:
            for line in body[3:end].splitlines():
                if ":" not in line:
                    continue
                k, v = line.split(":", 1)
                v = v.strip()
                if v.startswith("[") and v.endswith("]"):
                    v = [x.strip().strip('"').strip("'") for x in v[1:-1].split(",") if x.strip()]
                else:
                    v = v.strip('"').strip("'")
                meta[k.strip()] = v
            body = body[end + 4:]
    return meta, body.strip()


def load_articles():
    out = []
    for f in sorted(os.listdir("articles")):
        if not f.endswith(".md"):
            continue
        meta, body = front_matter(open(os.path.join("articles", f), encoding="utf-8").read())
        meta.setdefault("slug", f[:-3])
        if meta.get("title"):
            out.append({"meta": meta, "body": body})
    return out


def shell():
    s = open("index.html", encoding="utf-8").read()
    head = s.split("<main id=\"main\">")[0]
    tail = "<main id=\"main\">" + s.split("<main id=\"main\">", 1)[1]
    tail = "</main>" + tail.split("</main>", 1)[1]
    return head, tail


def set_head(head, title, desc, path, jsonld):
    h = re.sub(r"<title>.*?</title>", "<title>%s</title>" % html.escape(title), head, count=1, flags=re.S)
    h = re.sub(r'<meta name="description" content="[^"]*">',
               '<meta name="description" content="%s">' % html.escape(desc, quote=True), h, count=1)
    url = BASE + "/" + path
    h = re.sub(r'<link rel="canonical" href="[^"]*">', '<link rel="canonical" href="%s">' % url, h, count=1)
    h = re.sub(r'<meta property="og:title" content="[^"]*">', '<meta property="og:title" content="%s">' % html.escape(title, quote=True), h, count=1)
    h = re.sub(r'<meta property="og:description" content="[^"]*">', '<meta property="og:description" content="%s">' % html.escape(desc, quote=True), h, count=1)
    h = re.sub(r'<meta property="og:url" content="[^"]*">', '<meta property="og:url" content="%s">' % url, h, count=1)
    h = re.sub(r'<meta name="twitter:title" content="[^"]*">', '<meta name="twitter:title" content="%s">' % html.escape(title, quote=True), h, count=1)
    h = re.sub(r'<meta name="twitter:description" content="[^"]*">', '<meta name="twitter:description" content="%s">' % html.escape(desc, quote=True), h, count=1)
    h = re.sub(r'<script type="application/ld\+json">.*?</script>', "", h, flags=re.S)
    script = "".join('<script type="application/ld+json">%s</script>' % json.dumps(x, ensure_ascii=False) for x in jsonld)
    return h.replace("</head>", script + "</head>", 1)


def write(path, content):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    open(path, "w", encoding="utf-8").write(content)


def build_articles():
    arts = load_articles()
    if not arts:
        return []
    head, tail = shell()
    crumb = ('<nav class="crumbs" aria-label="Breadcrumb"><ol><li><a href="%s/">Home</a></li>'
             '<li><a href="%s/articles/">Articles</a></li><li><span>%%s</span></li></ol></nav>' % (BASE, BASE))
    # hub
    cards = ""
    for a in arts:
        m = a["meta"]
        cards += ('<article class="panel" style="margin-bottom:18px"><h3 style="margin:0 0 6px">'
                  '<a href="%s/articles/%s/">%s</a></h3><p style="margin:0 0 6px">%s</p>'
                  '<p class="note" style="margin:0">Updated %s</p></article>') % (
            BASE, m["slug"], html.escape(m.get("title", "")), html.escape(m.get("description", "")),
            html.escape(str(m.get("lastmod", m.get("date", "")))))
    hub_head = set_head(head, "Movie Guides & Articles | MovieState",
                        "Practical movie guides from MovieState: choosing what to watch, reading ratings honestly, and finding official ways to watch.",
                        "articles/", [{"@context": "https://schema.org", "@type": "CollectionPage",
                                       "name": "MovieState Guides", "url": BASE + "/articles/"}])
    hub_body = ('<main id="main"><div class="wrap">'
                '<nav class="crumbs" aria-label="Breadcrumb"><ol><li><a href="%s/">Home</a></li><li><span>Articles</span></li></ol></nav>'
                '<section class="section section--narrow"><div class="section__head"><div><p class="kicker">Editorial</p>'
                '<h1 class="section__title">Movie guides &amp; articles</h1>'
                '<p class="lede">Source-checked guides about choosing films, reading ratings and finding official ways to watch.</p>'
                '</div></div>%s</section></div></main>') % (BASE, cards)
    write("articles/index.html", hub_head + hub_body + tail)
    # articles
    urls = []
    for a in arts:
        m = a["meta"]
        slug = m["slug"]
        title = m.get("title", "")
        desc = m.get("description", "")
        path = "articles/%s/" % slug
        jsonld = [
            {"@context": "https://schema.org", "@type": "Article", "headline": title, "description": desc,
             "author": {"@type": "Organization", "name": m.get("author", "MovieState Editorial Team")},
             "publisher": {"@type": "Organization", "name": "MovieState",
                           "logo": {"@type": "ImageObject", "url": BASE + "/assets/favicon.svg"}},
             "datePublished": str(m.get("date", "")), "dateModified": str(m.get("lastmod", m.get("date", ""))),
             "mainEntityOfPage": {"@type": "WebPage", "@id": BASE + "/" + path}},
            {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE + "/"},
                {"@type": "ListItem", "position": 2, "name": "Articles", "item": BASE + "/articles/"},
                {"@type": "ListItem", "position": 3, "name": title}]},
        ]
        body = ('<main id="main"><div class="wrap">' + (crumb % html.escape(title)) +
                '<article class="section section--narrow"><p class="kicker">Guide</p>'
                '<h1 class="section__title">%s</h1>'
                '<p class="note">By %s &middot; Updated %s</p>'
                '<div class="prose prose--lead">%s</div></article></div></main>') % (
            html.escape(title), html.escape(m.get("author", "MovieState Editorial Team")),
            html.escape(str(m.get("lastmod", m.get("date", "")))), md_blocks(a["body"]))
        write(path + "index.html", set_head(head, title, desc, path, jsonld) + body + tail)
        urls.append((path, str(m.get("lastmod", m.get("date", "")))))
    # sitemap - single generator (hashed lastmod, noindex-safe)
    import sitemap_build
    sitemap_build.build(".")
    sm = open("sitemap.xml", encoding="utf-8").read()
    if False:
    have = set(re.findall(r"<loc>([^<]+)</loc>", sm))
    rows = []
    if BASE + "/articles/" not in have:
        rows.append("<url><loc>%s/articles/</loc><lastmod>%s</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>" % (BASE, "2026-11-04"))
    for p, lm in urls:
        u = BASE + "/" + p
        if u not in have:
            rows.append("<url><loc>%s</loc><lastmod>%s</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>" % (u, lm or "2026-11-04"))
    if rows:
        sm = sm.replace("</urlset>", "\n".join(rows) + "\n</urlset>")
        open("sitemap.xml", "w", encoding="utf-8").write(sm)
        bump("sitemap_rows", len(rows))
    return urls


if __name__ == "__main__":
    patch_pages()
    arts = build_articles()
    print("stats:", json.dumps(stats, ensure_ascii=False))
    print("articles:", [a[0] for a in arts])
