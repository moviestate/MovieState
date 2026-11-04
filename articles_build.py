"""Article builder for MovieState — renders /articles/ from markdown files."""
import os, re, html
import build as B

ART_DIR = "articles"


def _inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", t)

    def _link(mm):
        href = mm.group(2).strip()
        if not re.match(r"^(https?://|/|#)", href):
            return mm.group(0)
        if href.startswith("http"):
            return '<a href="%s" target="_blank" rel="noopener">%s</a>' % (href, mm.group(1))
        return '<a href="%s">%s</a>' % (href, mm.group(1))

    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", _link, t)


def md_to_html(md):
    out, buf, lst = [], [], None

    def flush_p():
        if buf:
            out.append("<p>" + _inline(" ".join(buf).strip()) + "</p>")
            del buf[:]

    def flush_l():
        nonlocal lst
        if lst:
            tag, items = lst
            out.append("<%s>%s</%s>" % (tag, "".join("<li>" + _inline(i) + "</li>" for i in items), tag))
            lst = None

    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush_p(); flush_l(); continue
        if line.startswith("### "):
            flush_p(); flush_l(); out.append("<h3>" + _inline(line[4:].strip()) + "</h3>"); continue
        if line.startswith("## "):
            flush_p(); flush_l(); out.append("<h2>" + _inline(line[3:].strip()) + "</h2>"); continue
        if line.startswith("# "):
            flush_p(); flush_l(); continue
        if re.match(r"^---+\s*$", line):
            flush_p(); flush_l(); out.append("<hr>"); continue
        if line.startswith("> "):
            flush_p(); flush_l(); out.append("<blockquote><p>" + _inline(line[2:].strip()) + "</p></blockquote>"); continue
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


def _front_matter(text):
    meta, body = {}, text
    if text.lstrip().startswith("---"):
        text = text.lstrip()
        end = text.find("\n---", 3)
        if end != -1:
            block = text[3:end]
            body = text[end + 4:]
            for line in block.splitlines():
                if ":" not in line:
                    continue
                k, v = line.split(":", 1)
                k, v = k.strip(), v.strip()
                if v.startswith("[") and v.endswith("]"):
                    v = [x.strip().strip('"').strip("'") for x in v[1:-1].split(",") if x.strip()]
                else:
                    v = v.strip('"').strip("'")
                meta[k] = v
    return meta, body.strip()


def load_articles():
    items = []
    if not os.path.isdir(ART_DIR):
        return items
    for f in sorted(os.listdir(ART_DIR)):
        if not f.endswith(".md"):
            continue
        meta, body = _front_matter(open(os.path.join(ART_DIR, f), encoding="utf-8").read())
        meta.setdefault("slug", f[:-3])
        if not meta.get("title"):
            continue
        items.append({"meta": meta, "body": body})
    items.sort(key=lambda a: str(a["meta"].get("date", "")), reverse=True)
    return items


def page_hub(items):
    cards = ""
    for a in items:
        meta = a["meta"]
        cards += (
            '<a class="card card--article" href="%s/articles/%s/">'
            '<div class="card__body"><span class="card__kicker">Guide</span>'
            '<h3 class="card__title">%s</h3>'
            '<p class="card__note">%s</p>'
            '<span class="card__meta">Updated %s</span></div></a>'
        ) % (B.BASE, meta["slug"], html.escape(meta.get("title", "")),
             html.escape((meta.get("description") or "")[:150]),
             html.escape(str(meta.get("lastmod", meta.get("date", B.TODAY)))))
    jsonld = {
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": "MovieState Guides and Articles", "url": B.BASE + "/articles/",
        "hasPart": [{"@type": "Article", "headline": a["meta"].get("title", ""),
                     "url": "%s/articles/%s/" % (B.BASE, a["meta"]["slug"])} for a in items],
    }
    body = (
        B.head("Movie Guides & Articles | MovieState",
               "Practical movie guides from MovieState: how to choose what to watch, how to check "
               "official availability, and what to know about ratings and reviews before you press play.",
               "articles/index.html", jsonld=jsonld)
        + B.header("/articles/")
        + '<main id="main"><div class="wrap">' + B.crumbs([("Home", "/"), ("Articles", "")]) +
        '<section class="section section--narrow"><div class="section__head"><div>'
        '<p class="kicker">Editorial</p><h1 class="section__title">Movie guides &amp; articles</h1>'
        '<p class="lede">Source-checked guides about choosing films, reading ratings and finding official ways to watch.</p>'
        '</div></div><div class="ed-grid">' + cards + "</div></section></div></main>" + B.footer()
    )
    B.write("articles/index.html", body)


def page_article(a):
    meta = a["meta"]
    slug = meta["slug"]
    title = meta.get("title", "")
    desc = meta.get("description", "")
    date_ = str(meta.get("date", B.TODAY))
    lastmod = str(meta.get("lastmod", date_))
    author = meta.get("author", "MovieState Editorial Team")
    tags = meta.get("tags") or []
    picks = sorted(B.D["movies"], key=lambda m: -(m.get("popularity") or 0))[:3]
    related = "".join(B.card(m, href=B.BASE + B.movie_path(m)) for m in picks)
    tag_html = "".join('<li class="chip">' + html.escape(t) + "</li>" for t in tags)
    jsonld = [
        {"@context": "https://schema.org", "@type": "Article", "headline": title, "description": desc,
         "author": {"@type": "Organization", "name": author},
         "publisher": {"@type": "Organization", "name": B.BRAND,
                       "logo": {"@type": "ImageObject", "url": B.BASE + "/assets/favicon.svg"}},
         "datePublished": date_, "dateModified": lastmod,
         "mainEntityOfPage": {"@type": "WebPage", "@id": "%s/articles/%s/" % (B.BASE, slug)}},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": B.BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Articles", "item": B.BASE + "/articles/"},
            {"@type": "ListItem", "position": 3, "name": title}]},
    ]
    body = (
        B.head(title, desc, "articles/%s/index.html" % slug, jsonld=jsonld)
        + B.header("/articles/")
        + '<main id="main"><div class="wrap">'
        + B.crumbs([("Home", "/"), ("Articles", "/articles/"), (title, "")])
        + '<article class="section section--narrow"><p class="kicker">Guide</p>'
        + '<h1 class="section__title">' + html.escape(title) + "</h1>"
        + '<p class="note">By ' + html.escape(author) + " &middot; Updated " + html.escape(lastmod) + "</p>"
        + '<div class="prose prose--lead">' + md_to_html(a["body"]) + "</div>"
        + (('<ul class="tags">' + tag_html + "</ul>") if tags else "")
        + "</article>"
        + '<section class="section"><div class="section__head"><div><p class="kicker">Keep exploring</p>'
        + '<h2 class="section__title">Popular guides this week</h2></div>'
        + '<a class="section__link" href="' + B.BASE + '/movies/">All movies<span aria-hidden="true"> &rarr;</span></a></div>'
        + '<div class="ed-grid">' + related + "</div></section></div></main>" + B.footer()
    )
    B.write("articles/%s/index.html" % slug, body)


def build_articles():
    items = load_articles()
    if not items:
        return
    page_hub(items)
    for a in items:
        page_article(a)
