#!/usr/bin/env python3
"""MovieState static site generator - v3 (black & royal blue)."""
import json, html, os, re, shutil
from datetime import date

BASE = "https://moviestate.github.io/MovieState"
MAIN = "https://moviestate.is-best.net"
BRAND = "MovieState"
TODAY = "2026-11-04"

D = json.load(open("data/movies.json"))
MOV = {m["tmdb_id"]: m for m in D["movies"]}
GEN = json.load(open("data/genres.json"))
PPL = json.load(open("data/people.json"))
PPL_BY_ID = {p["id"]: p for p in PPL}

def e(s): return html.escape(str(s or ""), quote=True)
def slug(s): return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", str(s).lower())).strip("-")
def mslug(m): return f"{slug(m['title'])}-{m['year']}"
def gslug(name): return slug(name)
def money(v): return f"${v/1_000_000:.1f}M" if v and v >= 1_000_000 else (f"${v:,}" if v else "")
def rtime(x): 
    if not x: return ""
    h, m = divmod(int(x), 60)
    return f"{h}h {m:02d}m" if h else f"{m}m"
def score(m): return f"{m['rating']:.1f}" if m.get("rating") else "NR"
def poster(p, size="w500"): return f"https://image.tmdb.org/t/p/{size}{p}" if p else ""
def backdrop(p, size="w1280"): return f"https://image.tmdb.org/t/p/{size}{p}" if p else ""
def main_url(m): return f"{MAIN}/movie/{m['tmdb_id']}/{slug(m['title'])}"
def esc_js(s): return json.dumps(s, ensure_ascii=False)

PAGES = []

def head(title, desc, path, og_image=None, jsonld=None, extra_css=""):
    url = f"{BASE}/{path}" if path else f"{BASE}/"
    og = og_image or f"{BASE}/assets/og-default.jpg"
    parts = [f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
<meta name="theme-color" content="#05060A">
<meta property="og:type" content="website"><meta property="og:site_name" content="{BRAND}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}"><meta property="og:image" content="{e(og)}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}"><meta name="twitter:image" content="{e(og)}">
<link rel="preconnect" href="https://image.tmdb.org" crossorigin>
<link rel="preload" href="{BASE}/assets/fonts/instrument-serif.woff2" as="font" type="font/woff2" crossorigin>
<link rel="icon" href="{BASE}/assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{BASE}/assets/style.css">
<script src="{BASE}/assets/app.js" defer></script>"""]
    for block in (jsonld or []):
        parts.append(f'<script type="application/ld+json">{json.dumps(block, ensure_ascii=False)}</script>')
    parts.append("</head><body>")
    return "\n".join(parts)

ORG = {"@type": "Organization", "name": BRAND, "url": BASE + "/", "logo": {"@type": "ImageObject", "url": BASE + "/assets/favicon.svg"}}

def header(active=""):
    nav = [("Movies", "/movies/"), ("Categories", "/categories/"), ("People", "/people/"), ("FAQ", "/faq/"), ("About", "/about/")]
    def one(t, h):
        mark = ' aria-current="page"' if h == active else ''
        return f'<a href="{BASE}{h}"{mark}>{e(t)}</a>'
    links = "".join(one(t, h) for t, h in nav)
    return f"""<a class="skip" href="#main">Skip to content</a>
<header class="header"><div class="header__inner">
<a class="brand" href="{BASE}/"><span class="brand__mark">MS</span><span class="brand__name">MovieState</span></a>
<nav class="nav" aria-label="Main">{links}</nav>
<a class="btn btn--ghost btn--sm" href="{MAIN}/" target="_blank" rel="noopener">Watch Movies</a>
</div></header>"""

def footer():
    return f"""<footer class="footer"><div class="footer__inner">
<div class="footer__brand"><span class="brand__mark">MS</span><div><strong>{BRAND}</strong>
<p>An independent movie guide. We research films, cast, release details and where you can watch them — then send you to the right place.</p></div></div>
<div class="footer__cols">
<div><h3>Explore</h3><a href="{BASE}/movies/">All movies</a><a href="{BASE}/categories/">Categories</a><a href="{BASE}/people/">People</a></div>
<div><h3>Company</h3><a href="{BASE}/about/">About</a><a href="{BASE}/faq/">FAQ</a><a href="{BASE}/privacy-policy/">Privacy Policy</a><a href="{BASE}/terms/">Terms &amp; Conditions</a></div>
<div><h3>Watch</h3><a href="{MAIN}/" target="_blank" rel="noopener">MovieState streaming</a><span class="muted">Streaming and downloads are handled on our main site.</span></div>
</div>
<p class="footer__legal">© {date.today().year} {BRAND}. Movie metadata and images provided by TMDB. {BRAND} is not endorsed or certified by TMDB. This site publishes information only; we do not host or stream video files.</p>
</div></footer></body></html>"""

def crumbs(items):
    out = ['<nav class="crumbs" aria-label="Breadcrumb"><ol>']
    for i, (label, href) in enumerate(items):
        last = i == len(items) - 1
        if last or not href:
            out.append("<li><span>" + e(label) + "</span></li>")
        else:
            out.append('<li><a href="' + BASE + href + '">' + e(label) + "</a></li>")
    out.append("</ol></nav>")
    return "".join(out)

def crumb_ld(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": f"{BASE}{h}" if h else None}
        for i, (n, h) in enumerate(items)]}

def write(path, content):
    full = os.path.join("site", path)
    os.makedirs(os.path.dirname(full), exist_ok=True) if os.path.dirname(full) else None
    open(full, "w", encoding="utf-8").write(content)
    PAGES.append(path)

def card(m, href=None, rating=True, lazy=True):
    img = poster(m.get("poster"), "w342")
    t, y = m.get("title", ""), m.get("year", "")
    r = m.get("rating") or 0
    inner = f'''<div class="card__art"><img src="{img}" alt="{e(t)} poster" width="342" height="513" {'loading="lazy" ' if lazy else ''}decoding="async">
<span class="card__score">{r:.1f}</span><span class="card__fade" aria-hidden="true"></span></div>
<div class="card__body"><h3 class="card__title">{e(t)}</h3><p class="card__sub">{e(y)}{" · " + e(m.get("genres", [""])[0]) if m.get("genres") else ""}</p></div>'''
    if href:
        return f'<a class="card" href="{href}">{inner}</a>'
    return f'<div class="card card--static">{inner}</div>'

def person_card(p, href=None):
    img = poster(p.get("profile"), "w185")
    role = "Director" if "Director" in p.get("roles", []) else "Actor"
    body = f'''<span class="person__ring"><img src="{img}" alt="{e(p["name"])}" width="185" height="278" loading="lazy" decoding="async"></span>
<span class="person__name">{e(p["name"])}</span><span class="person__role">{role}</span>'''
    return f'<a class="person" href="{href}">{body}</a>' if href else f'<div class="person">{body}</div>'

def section_head(kicker, title, link=None):
    l = f'<a class="section__link" href="{link[1]}">{e(link[0])}<span aria-hidden="true"> →</span></a>' if link else ""
    return f'<div class="section__head"><p class="kicker">{e(kicker)}</p><h2 class="section__title">{e(title)}</h2>{l}</div>'

def person_path(p): return f"/person/{p['id']}-{slug(p['name'])}/"
def movie_path(m): return f"/movie/{mslug(m)}/"
def genre_path(g): return f"/category/{slug(g)}/"

FEATURED_ID = 969681
HOME_FAQ = [
 ("What is MovieState?", "MovieState is an independent movie guide. We research films — story, cast, crew, runtime, release details and availability — and publish clear, fact-checked pages so you can decide what to watch next."),
 ("How do I find where to watch a movie?", "Open any movie page and use the Watch on MovieState button. Availability changes by country and provider, so always confirm on the streaming page before you subscribe."),
 ("Is browsing MovieState free?", "Yes. Every page on this site is free to read, with no account and no paywall. We do not run pop-ups or forced sign-ups."),
 ("Where does the movie data come from?", "Posters, backdrops and core metadata come from TMDB. We combine that with editorial checks against official studio and streaming announcements before publishing."),
 ("Do you host or stream movie files?", "No. This site publishes information only. Playback and downloads are handled on our main site, moviestate.is-best.net."),
]

def page_home():
    f = MOV[FEATURED_ID]
    trend = [MOV[i] for i in [1423191, 1156593, 1311031, 1083381, 1368166, 1315985, 1232493, 1368316, 1300118, 1339713] if i in MOV][:10]
    popular = [MOV[i] for i in [155, 969681, 1368337, 354912, 1232493, 1316311, 1315985, 1368166, 1311031, 1339713, 1083381, 1315772] if i in MOV][:12]
    tick = "".join(f'<span>{e(m["title"])}</span><i aria-hidden="true">◆</i>' for m in trend)
    trend_cards = "".join(card(m, movie_path(m)) for m in trend)
    pop_cards = "".join(card(m, movie_path(m)) for m in popular)
    cats = "".join(f'''<a class="cat" href="{BASE}/category/{g['slug']}/">
<img src="{poster(g['movies'][0]['poster'], 'w342')}" alt="" width="342" height="513" loading="lazy" decoding="async">
<span class="cat__veil" aria-hidden="true"></span><span class="cat__label"><span class="cat__count">{len(g['movies'])} films</span>{e(g['name'])}</span></a>''' for g in GEN[:10])
    ppl = "".join(person_card(p, f"{BASE}{person_path(p)}") for p in PPL[:12])
    faq_html = "".join(f'<details class="faq__item"><summary><h3>{e(q)}</h3></summary><p>{e(a)}</p></details>' for q, a in HOME_FAQ)
    ld = [
      {"@context": "https://schema.org", "@type": "WebSite", "name": BRAND, "url": BASE + "/", "description": "Independent movie guide: trending films, cast and crew, release details and where to watch in HD.", "publisher": ORG},
      {"@context": "https://schema.org", **ORG},
      {"@context": "https://schema.org", "@type": "ItemList", "name": "Trending movies this week", "itemListElement": [
          {"@type": "ListItem", "position": i + 1, "url": BASE + movie_path(m), "name": m["title"]} for i, m in enumerate(trend)]},
      {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
          {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in HOME_FAQ]},
    ]
    h = head("MovieState — Watch Movies Online in HD & Where to Watch",
             "Explore trending and new-release movies with cast, runtime, release details and where to watch in HD. Free, ad-free movie guides updated daily.",
             "", og_image=backdrop(f["backdrop"], "w1280"), jsonld=ld)
    body = f"""{h}{header()}<main id="main">
<section class="hero">
<img class="hero__bg" src="{backdrop(f['backdrop'], 'w1280')}" alt="" width="1280" height="720" fetchpriority="high" decoding="async">
<span class="hero__veil" aria-hidden="true"></span>
<div class="hero__inner">
<p class="kicker">Featured this week</p>
<h1 class="hero__title">{e(f['title'])} <span>— where to watch in HD</span></h1>
<ul class="meta-row"><li class="meta-row__score">{score(f)}</li><li>{e(f['year'])}</li><li>{e(rtime(f.get('runtime')))}</li><li>{e(', '.join(f.get('genres', [])[:2]))}</li></ul>
<p class="hero__lede">{e(f.get('overview', '')[:210])}</p>
<div class="hero__cta"><a class="btn btn--primary" href="{main_url(f)}" target="_blank" rel="noopener">Watch on MovieState</a>
<a class="btn btn--ghost" href="{BASE}{movie_path(f)}">Movie details</a></div>
</div></section>
<div class="ticker" aria-hidden="true"><div class="ticker__track">{tick}{tick}</div></div>
<section class="section">{section_head("Now trending", "What everyone is watching this week", ("All movies", BASE + "/movies/"))}
<div class="rail"><div class="rail__track">{trend_cards}</div></div></section>
<section class="section">{section_head("Browse", "Categories built around how you actually choose films", ("All categories", BASE + "/categories/"))}
<div class="cat-grid">{cats}</div></section>
<section class="section">{section_head("Popular now", "Most-watched movies on MovieState", ("See all", BASE + "/movies/"))}
<div class="grid">{pop_cards}</div></section>
<section class="section">{section_head("Cast &amp; crew", "The people behind the films", ("All people", BASE + "/people/"))}
<div class="rail"><div class="rail__track rail__track--people">{ppl}</div></div></section>
<section class="section section--split">
<div class="panel"><h2 class="panel__title">Every page answers three questions</h2>
<p>What is this film? Who made it? Where can I watch it? We keep pages short to scan, add the facts that matter, and skip the filler.</p>
<ul class="ticks"><li>Real cast, crew and runtime data</li><li>Honest availability notes by region</li><li>No pop-ups, no forced sign-ups</li></ul>
<a class="btn btn--primary" href="{MAIN}/" target="_blank" rel="noopener">Open MovieState</a></div>
<div class="panel panel--faq"><h2 class="panel__title">Common questions</h2>{faq_html}</div>
</section>
</main>{footer()}"""
    write("index.html", body)

def movie_faq(m):
    t, y = m["title"], m["year"]
    qs = [(f"Who directed {t}?", (f"{t} was directed by {m['director']['name']}." if m.get("director") else f"{t} has no confirmed director on record yet.")),
          (f"How long is {t}?", (f"{t} runs {rtime(m['runtime'])}." if m.get("runtime") else f"The runtime of {t} has not been confirmed yet.")),
          (f"Where can I watch {t}?", f"Open the streaming page on MovieState to check current availability for {t}. Availability depends on your country and changes over time.")]
    return qs

def page_movie(m):
    t, y = m["title"], m["year"]
    path = movie_path(m).lstrip("/")
    title = f"{t} ({y}) — Cast, Runtime & Where to Watch"
    desc = (m.get("overview") or f"Everything about {t} ({y}): cast, director, runtime, release details and where to watch.")[:150]
    cast = "".join(person_card(PPL_BY_ID[c["id"]], f"{BASE}{person_path(PPL_BY_ID[c['id']])}") if c["id"] in PPL_BY_ID else
                   f'<div class="person"><span class="person__ring"><img src="{poster(c.get("profile"), "w185")}" alt="{e(c["name"])}" width="185" height="278" loading="lazy"></span><span class="person__name">{e(c["name"])}</span><span class="person__role">{e(c.get("character") or "Cast")}</span></div>'
                   for c in (m.get("cast") or [])[:8])
    d = m.get("director")
    dblock = ""
    if d:
        dp = PPL_BY_ID.get(d["id"])
        link = f"{BASE}{person_path(dp)}" if dp else None
        inner = f'<img src="{poster(d.get("profile"), "w185")}" alt="{e(d["name"])}" width="96" height="96" loading="lazy"><span><span class="kicker">Director</span><strong>{e(d["name"])}</strong></span>'
        dblock = f'<a class="director" href="{link}">{inner}</a>' if link else f'<div class="director">{inner}</div>'
    qs = movie_faq(m)
    faq_html = "".join(f'<details class="faq__item"><summary><h3>{e(q)}</h3></summary><p>{e(a)}</p></details>' for q, a in qs)
    rel = [x for x in D["movies"] if x["tmdb_id"] != m["tmdb_id"] and set(x.get("genres", [])) & set(m.get("genres", []))][:8]
    rel_cards = "".join(card(x, f"{BASE}{movie_path(x)}") for x in rel)
    facts = [(k, v) for k, v in [
        ("Release date", m.get("release_date")), ("Runtime", rtime(m.get("runtime"))), ("Status", m.get("status")),
        ("Language", (m.get("language") or "").upper()), ("Genres", ", ".join(m.get("genres", []))),
        ("Budget", money(m.get("budget"))), ("Box office", money(m.get("revenue")))] if v]
    facts_html = "".join(f'<div class="fact"><dt>{e(k)}</dt><dd>{e(v)}</dd></div>' for k, v in facts)
    ld = [
      {"@context": "https://schema.org", "@type": "Movie", "name": t, "url": f"{BASE}/{path}",
       "image": poster(m.get("poster"), "w500"), "description": m.get("overview", ""),
       "datePublished": m.get("release_date"), "genre": m.get("genres", []),
       "duration": f"PT{m['runtime']}M" if m.get("runtime") else None,
       "director": {"@type": "Person", "name": d["name"]} if d else None,
       "actor": [{"@type": "Person", "name": c["name"]} for c in (m.get("cast") or [])[:8]],
       "aggregateRating": {"@type": "AggregateRating", "ratingValue": round(m.get("rating", 0), 1), "bestRating": 10, "ratingCount": max(m.get("votes", 1), 1)} if m.get("rating") else None},
      crumb_ld([("Home", "/"), ("Movies", "/movies/"), (t, movie_path(m))]),
      {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
          {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qs]},
    ]
    ld = [{k: v for k, v in b.items() if v is not None} for b in ld]
    h = head(f"{title} | {BRAND}", desc, path, og_image=backdrop(m.get("backdrop"), "w1280"), jsonld=ld)
    body = f"""{h}{header("/movies/")}<main id="main">
<div class="wrap">{crumbs([("Home", "/"), ("Movies", "/movies/"), (t, None)])}</div>
<section class="hero hero--movie">
<img class="hero__bg" src="{backdrop(m.get('backdrop'), 'w1280')}" alt="" width="1280" height="720" fetchpriority="high" decoding="async">
<span class="hero__veil" aria-hidden="true"></span>
<div class="hero__inner hero__inner--split">
<div class="poster-lg"><img src="{poster(m.get('poster'), 'w500')}" alt="{e(t)} poster" width="500" height="750" fetchpriority="high" decoding="async"><span class="poster-lg__score">{score(m)}</span></div>
<div>
<p class="kicker">{e(', '.join(m.get('genres', [])[:2]))} · {e(y)}</p>
<h1 class="hero__title">{e(t)}</h1>
{f'<p class="tagline">“{e(m["tagline"])}”</p>' if m.get('tagline') else ''}
<ul class="meta-row"><li>{e(y)}</li><li>{e(rtime(m.get('runtime')))}</li><li>{e((m.get('language') or '').upper())}</li><li>{e(m.get('status') or '')}</li></ul>
<div class="hero__cta"><a class="btn btn--primary" href="{main_url(m)}" target="_blank" rel="noopener">Watch on MovieState</a>
<a class="btn btn--ghost" href="#where">Where to watch</a></div>
</div></div></section>
<section class="section section--narrow">
<div class="prose"><h2>What is {e(t)} about?</h2><p>{e(m.get('overview') or 'A full synopsis is being prepared for this title.')}</p></div>
<div class="facts"><h2 class="facts__title">Key facts</h2><dl>{facts_html}</dl></div>
</section>
<section class="section"><div class="section__head"><p class="kicker">Cast</p><h2 class="section__title">Who stars in {e(t)}</h2></div>
<div class="rail"><div class="rail__track rail__track--people">{cast or '<p class="muted">Cast list coming soon.</p>'}</div></div>{dblock}</section>
<section class="section section--split" id="where">
<div class="panel"><p class="kicker">Watch</p><h2 class="panel__title">Where to watch {e(t)}</h2>
<p>Streaming rights move between platforms and differ by country. Open the MovieState page for {e(t)} to see the current watch options, quality and availability for your region.</p>
<a class="btn btn--primary" href="{main_url(m)}" target="_blank" rel="noopener">Check availability</a>
<p class="note">We publish information only. Always confirm details on the provider's own page before paying.</p></div>
<div class="panel panel--faq"><h2 class="panel__title">Questions about {e(t)}</h2>{faq_html}</div>
</section>
<section class="section">{section_head("More like this", f"Films similar to {t}", ("All movies", BASE + "/movies/"))}
<div class="grid">{rel_cards or '<p class="muted">More recommendations coming soon.</p>'}</div></section>
</main>{footer()}"""
    write(path + "index.html", body)

def page_category(g):
    path = f"category/{g['slug']}/index.html"
    mine = [m for m in D["movies"] if g["name"] in m.get("genres", [])]
    mine_cards = "".join(card(m, f"{BASE}{movie_path(m)}") for m in mine)
    other_cards = "".join(card(x) for x in g["movies"][:18])
    chips = "".join(f'<a class="chip" href="{BASE}/category/{x["slug"]}/">{e(x["name"])}</a>' for x in GEN if x["slug"] != g["slug"])
    title = f"{g['name']} Movies — Watch Online in HD"
    desc = f"Best {g['name'].lower()} movies to watch, with cast, runtime and where to watch in HD. Hand-checked picks from MovieState."
    intro = (f"{g['name']} films reward a certain mood: the right one pulls you in within minutes. This page keeps a running shortlist of the "
             f"{g['name'].lower()} titles people are actually searching for right now, with the details you need before you press play: who is in it, "
             f"how long it runs, and where it is streaming. Start with our full guides below, or jump to any film that catches your eye.")
    ld = [
      crumb_ld([("Home", "/"), ("Categories", "/categories/"), (g["name"], f"/category/{g['slug']}/")]),
      {"@context": "https://schema.org", "@type": "CollectionPage", "name": f"{g['name']} Movies", "url": f"{BASE}/category/{g['slug']}/",
       "description": desc, "mainEntity": {"@type": "ItemList", "itemListElement": [
           {"@type": "ListItem", "position": i + 1, "name": x["title"], "url": f"{BASE}{movie_path(x)}"} for i, x in enumerate(mine)]}},
    ]
    h = head(f"{title} | {BRAND}", desc, f"category/{g['slug']}/", og_image=poster(g['movies'][0]['poster'], 'w780'), jsonld=ld)
    body = f"""{h}{header("/categories/")}<main id="main">
<div class="wrap">{crumbs([("Home", "/"), ("Categories", "/categories/"), (g["name"], None)])}</div>
<section class="page-head"><div class="wrap"><p class="kicker">Category</p><h1 class="page-title">{e(g['name'])} movies</h1><p class="page-lede">{e(intro)}</p></div></section>
{f'<section class="section"><div class="section__head"><p class="kicker">Editor picks</p><h2 class="section__title">{e(g["name"])} films with full guides</h2></div><div class="grid">{mine_cards}</div></section>' if mine else ''}
<section class="section"><div class="section__head"><p class="kicker">Popular right now</p><h2 class="section__title">More {e(g['name'].lower())} titles people are watching</h2></div><div class="grid">{other_cards}</div></section>
<section class="section section--narrow"><div class="panel"><h2 class="panel__title">Browse another category</h2><div class="chips">{chips}</div></div></section>
</main>{footer()}"""
    write(path, body)

def page_movies_hub():
    path = "movies/index.html"
    cards = "".join(card(m, f"{BASE}{movie_path(m)}") for m in sorted(D["movies"], key=lambda x: -(x.get("rating") or 0)))
    chips = "".join(f'<a class="chip" href="{BASE}/category/{x["slug"]}/">{e(x["name"])}</a>' for x in GEN)
    ld = [crumb_ld([("Home", "/"), ("Movies", "/movies/")]),
          {"@context": "https://schema.org", "@type": "CollectionPage", "name": "All movies", "url": f"{BASE}/movies/",
           "mainEntity": {"@type": "ItemList", "itemListElement": [
               {"@type": "ListItem", "position": i + 1, "name": m["title"], "url": f"{BASE}{movie_path(m)}"} for i, m in enumerate(D["movies"])]}}]
    h = head(f"All Movies — Guides, Cast & Where to Watch | {BRAND}",
             "Browse every movie we cover: cast, runtime, release details and where to watch in HD.", path, jsonld=ld)
    body = f"""{h}{header("/movies/")}<main id="main">
<div class="wrap">{crumbs([("Home", "/"), ("Movies", None)])}</div>
<section class="page-head"><div class="wrap"><p class="kicker">Library</p><h1 class="page-title">All movies</h1>
<p class="page-lede">Every film in the MovieState guide library, sorted by audience rating. Each page covers the story, the cast, technical details and where the film is streaming.</p></div></section>
<section class="section"><div class="grid">{cards}</div></section>
<section class="section section--narrow"><div class="panel"><h2 class="panel__title">Browse by category</h2><div class="chips">{chips}</div></div></section>
</main>{footer()}"""
    write(path, body)

def page_categories_hub():
    path = "categories/index.html"
    tiles = "".join(f'''<a class="cat" href="{BASE}/category/{g['slug']}/">
<img src="{poster(g['movies'][0]['poster'], 'w342')}" alt="" width="342" height="513" loading="lazy" decoding="async">
<span class="cat__veil" aria-hidden="true"></span><span class="cat__label"><span class="cat__count">{len(g['movies'])} films</span>{e(g['name'])}</span></a>''' for g in GEN)
    ld = [crumb_ld([("Home", "/"), ("Categories", "/categories/")]),
          {"@context": "https://schema.org", "@type": "CollectionPage", "name": "Movie categories", "url": f"{BASE}/categories/"}]
    h = head(f"Movie Categories — Browse by Genre | {BRAND}",
             "Browse movies by genre: action, horror, sci-fi, drama, comedy and more, with ratings and where to watch.", path, jsonld=ld)
    body = f"""{h}{header("/categories/")}<main id="main">
<div class="wrap">{crumbs([("Home", "/"), ("Categories", None)])}</div>
<section class="page-head"><div class="wrap"><p class="kicker">Browse</p><h1 class="page-title">Movie categories</h1>
<p class="page-lede">Genres are a shortcut, not a rule. Pick the mood you are in, and we will show you the films people are watching in that lane right now.</p></div></section>
<section class="section"><div class="cat-grid">{tiles}</div></section>
</main>{footer()}"""
    write(path, body)

def page_people_hub():
    path = "people/index.html"
    cards = "".join(person_card(p, f"{BASE}{person_path(p)}") for p in PPL)
    ld = [crumb_ld([("Home", "/"), ("People", "/people/")]),
          {"@context": "https://schema.org", "@type": "CollectionPage", "name": "Actors and directors", "url": f"{BASE}/people/"}]
    h = head(f"Actors & Directors — Profiles and Credits | {BRAND}",
             "Profiles of the actors and directors behind the films we cover, with credits and quick facts.", path, jsonld=ld)
    body = f"""{h}{header("/people/")}<main id="main">
<div class="wrap">{crumbs([("Home", "/"), ("People", None)])}</div>
<section class="page-head"><div class="wrap"><p class="kicker">People</p><h1 class="page-title">Actors &amp; directors</h1>
<p class="page-lede">The faces and filmmakers behind the movies in our library — with the credits that matter and the films worth starting with.</p></div></section>
<section class="section"><div class="grid grid--people">{cards}</div></section>
</main>{footer()}"""
    write(path, body)

def page_person(p):
    path = f"person/{p['id']}-{slug(p['name'])}/index.html"
    role = "Director" if "Director" in p.get("roles", []) else "Actor"
    films = "".join(card(MOV[x["id"]], f"{BASE}{movie_path(MOV[x['id']])}") if x["id"] in MOV else
                    f'<div class="card card--static"><div class="card__art"><img src="{poster(x.get("poster"), "w342")}" alt="{e(x["title"])}" width="342" height="513" loading="lazy"></div><div class="card__body"><h3 class="card__title">{e(x["title"])}</h3><p class="card__sub">{e(x.get("year"))}</p></div></div>'
                    for x in p["movies"][:16])
    bio = p.get("biography") or f"{p['name']} is a {role.lower()} known for work in the films listed below."
    desc = (bio[:150] if bio else f"{p['name']} — credits and biography.")
    facts = [(k, v) for k, v in [("Known for", p.get("dept")), ("Born", p.get("birthday")), ("Place of birth", p.get("place"))] if v]
    facts_html = "".join(f'<div class="fact"><dt>{e(k)}</dt><dd>{e(v)}</dd></div>' for k, v in facts)
    ld = [crumb_ld([("Home", "/"), ("People", "/people/"), (p["name"], person_path(p))]),
          {"@context": "https://schema.org", "@type": "Person", "name": p["name"], "url": f"{BASE}/{path}",
           "image": poster(p.get("profile"), "w500"), "description": bio[:300], "jobTitle": role}]
    h = head(f"{p['name']} — Movies, Credits & Biography | {BRAND}", desc, path, og_image=poster(p.get("profile"), "w500"), jsonld=ld)
    body = f"""{h}{header("/people/")}<main id="main">
<div class="wrap">{crumbs([("Home", "/"), ("People", "/people/"), (p["name"], None)])}</div>
<section class="page-head page-head--person"><div class="wrap wrap--person">
<img class="person-lg" src="{poster(p.get('profile'), 'w342')}" alt="{e(p['name'])}" width="342" height="513" fetchpriority="high" decoding="async">
<div><p class="kicker">{e(role)}</p><h1 class="page-title">{e(p['name'])}</h1><p class="page-lede">{e(bio[:420])}</p>
{f'<dl class="facts facts--inline">{facts_html}</dl>' if facts_html else ''}</div></div></section>
<section class="section"><div class="section__head"><p class="kicker">Credits</p><h2 class="section__title">Films with {e(p['name'])}</h2></div><div class="grid">{films}</div></section>
</main>{footer()}"""
    write(path, body)

def static_page(path, title, desc, kicker, h1, sections, active=""):
    body_html = "".join(f"<h2>{e(h)}</h2>" + "".join(f"<p>{e(p)}</p>" for p in paras) for h, paras in sections)
    ld = [crumb_ld([("Home", "/"), (h1, "/" + path.replace("index.html", ""))])]
    h = head(f"{title} | {BRAND}", desc, path, jsonld=ld)
    out = f"""{h}{header(active)}<main id="main">
<div class="wrap">{crumbs([("Home", "/"), (h1, None)])}</div>
<section class="page-head"><div class="wrap"><p class="kicker">{e(kicker)}</p><h1 class="page-title">{e(h1)}</h1></div></section>
<section class="section section--narrow"><div class="prose prose--page">{body_html}<p class="note">Last updated: 4 November 2026.</p></div></section>
</main>{footer()}"""
    write(path, out)

def page_about():
    static_page("about/index.html", "About MovieState", "Who runs MovieState, how we research movies, and the standards we follow before publishing a page.", "About", "About MovieState", [
      ("What this site is", [
        "MovieState is an independent movie guide. We publish plain-English pages about films: what the story is, who made it, how long it runs, when it came out, and where it can be watched right now.",
        "We are not a studio, a streaming service or a review aggregator. We are a small editorial project that reads primary sources, checks the details, and writes the page a person actually needs before deciding what to watch.",
      ]),
      ("How we research", [
        "Core metadata — titles, posters, backdrops, cast and crew, runtime and release dates — comes from TMDB. That data is the starting point, not the finish line. Every published page is checked against the studio's own announcements, official trailers and the provider pages where a film is listed.",
        "When a detail cannot be verified, we either leave it out or mark it as unconfirmed. We do not invent release dates, ratings, availability windows or 'official' claims to fill space.",
      ]),
      ("What we do not do", [
        "We do not host, stream or store movie files on this site. We do not use pop-ups, forced redirects or fake download buttons. We do not publish 'free download' promises, because those claims are usually false and frequently harmful.",
        "Where a film is available to stream or download, we link to the page that handles it — our main site — and we tell you to confirm the details with the provider before you pay for anything.",
      ]),
      ("Editorial independence", [
        "No studio pays us to write a page, rank a film higher, or soften a description. If that ever changes, it will be disclosed on the page itself in plain language.",
      ]),
      ("Corrections", [
        "Films change: release dates slip, streamers lose rights, runtimes move. When a reader tells us something is out of date, we verify it and update the page. If you spot an error, report it through the contact options on our main site and we will look at it.",
      ]),
    ], "/about/")

def page_privacy():
    static_page("privacy-policy/index.html", "Privacy Policy", "What MovieState does and does not collect when you browse our movie guides.", "Legal", "Privacy Policy", [
      ("The short version", [
        "This site is a set of static pages. We do not create accounts, we do not ask for your name or email, and we do not run advertising networks or cross-site trackers.",
      ]),
      ("What is collected", [
        "Hosting: this site is served by GitHub Pages. GitHub may record standard technical data such as IP address, browser type and requested URL in its own server logs, under GitHub's privacy statement.",
        "Images: posters and backdrops are loaded from TMDB's image service. That request carries the technical data any image request carries, such as your IP address and browser headers.",
        "Analytics: we do not currently run third-party analytics on this site. If that changes, this page will be updated before any tracking begins.",
      ]),
      ("Cookies", [
        "We do not set cookies for advertising or profiling. If you follow a link to another site, including our main site, that site's own cookie and privacy rules apply.",
      ]),
      ("Links to other sites", [
        "Movie pages link to streaming and download pages on our main site and, occasionally, to official studio pages. We do not control those sites and are not responsible for their content or data practices.",
      ]),
      ("Children", [
        "This site is general-audience information about films and is not directed at children under 13. We do not knowingly collect personal information from anyone.",
      ]),
      ("Changes and contact", [
        "If this policy changes, the update will appear here with a new date. For privacy questions or removal requests, contact us through the channels listed on our main site.",
      ]),
    ], "")

def page_terms():
    static_page("terms/index.html", "Terms & Conditions", "The terms that apply when you use the MovieState movie guide.", "Legal", "Terms & Conditions", [
      ("What you are using", [
        "MovieState publishes information about films. It is not a streaming service, a download service or a video host. By using this site you accept these terms.",
      ]),
      ("Accuracy", [
        "We work hard to keep pages accurate, but film information changes quickly. Ratings, runtimes, availability and release dates are provided for guidance and are not a guarantee. Always confirm with the official provider before making a purchase or a decision.",
      ]),
      ("Intellectual property", [
        "Movie titles, posters, backdrops and related marks belong to their respective studios and rights holders. Metadata and images on this site are provided by TMDB; MovieState is not endorsed or certified by TMDB. Our own written text may not be republished in bulk without permission.",
      ]),
      ("No hosting, no downloads", [
        "This site does not host movie files and does not provide direct download links. We publish information and point to pages that handle playback. You are responsible for complying with the laws of your own country when you stream or download anything.",
      ]),
      ("Acceptable use", [
        "Do not attempt to disrupt the site, scrape it at abusive volume, or reuse its content to build a competing site. Do not misrepresent our pages as official studio pages.",
      ]),
      ("External links", [
        "Links to other websites are provided for convenience. We are not responsible for their content, availability or practices.",
      ]),
      ("Liability", [
        "The site is provided as is. To the maximum extent permitted by law, MovieState is not liable for losses arising from use of the site or from reliance on information published here.",
      ]),
      ("Changes", [
        "We may update these terms as the site grows. The current version always applies, and the date below shows when it last changed.",
      ]),
    ], "")

FAQ_ITEMS = [
 ("What is MovieState?", "MovieState is an independent movie guide that explains what a film is, who made it, and where you can watch it."),
 ("Is MovieState free to use?", "Yes. Every page is free to read. There is no account, no paywall and no forced sign-up."),
 ("Do you host or stream the movies?", "No. We publish information only. Playback and download pages are handled on our main site, moviestate.is-best.net."),
 ("Where does your movie data come from?", "Core metadata and artwork come from TMDB. We check release details and availability against official announcements before publishing."),
 ("How often are pages updated?", "We refresh the library continuously, and we prioritise pages where a release date, runtime or streaming status has changed."),
 ("Why can availability differ from what I see?", "Streaming rights are sold country by country and change over time. A film available in one region may not be licensed in another."),
 ("Can I request a movie page?", "Yes. Send us the title through our main site's contact options and we will add it to the research queue."),
 ("Do you publish free download promises?", "No. Claims like 'free full movie download' are usually false, and we do not publish them. We link only to pages that explain availability honestly."),
 ("How do you handle errors?", "Report the page and the detail that is wrong. We verify it against a primary source and correct the page, noting significant changes."),
 ("Can I use your text on my site?", "Short quotations with a link are fine. Republishing full pages is not permitted."),
]

def page_faq():
    path = "faq/index.html"
    items = "".join(f'<details class="faq__item"><summary><h3>{e(q)}</h3></summary><p>{e(a)}</p></details>' for q, a in FAQ_ITEMS)
    ld = [crumb_ld([("Home", "/"), ("FAQ", "/faq/")]),
          {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
              {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ_ITEMS]}]
    h = head(f"FAQ — Common Questions About {BRAND}", "Answers about how MovieState works, where the data comes from, and how to watch the films we cover.", path, jsonld=ld)
    body = f"""{h}{header("/faq/")}<main id="main">
<div class="wrap">{crumbs([("Home", "/"), ("FAQ", None)])}</div>
<section class="page-head"><div class="wrap"><p class="kicker">Help</p><h1 class="page-title">Frequently asked questions</h1>
<p class="page-lede">Short, direct answers about the site, the data and the way we link to streaming pages.</p></div></section>
<section class="section section--narrow"><div class="panel panel--faq">{items}</div></section>
</main>{footer()}"""
    write(path, body)

def url_for(path):
    if path == "index.html": return BASE + "/"
    if path.endswith("/index.html"): return BASE + "/" + path[: -len("index.html")]
    return BASE + "/" + path

def priority(path):
    if path == "index.html": return "1.0", "daily"
    if path.startswith("movie/"): return "0.9", "weekly"
    if path.startswith("category/"): return "0.8", "weekly"
    if path.startswith(("movies/", "categories/", "people/")): return "0.8", "weekly"
    if path.startswith("person/"): return "0.6", "monthly"
    if path.startswith(("about/", "faq/")): return "0.5", "monthly"
    return "0.3", "yearly"

def write_sitemap():
    rows = []
    for p in sorted(set(PAGES)):
        pr, cf = priority(p)
        rows.append(f"<url><loc>{url_for(p)}</loc><lastmod>{TODAY}</lastmod><changefreq>{cf}</changefreq><priority>{pr}</priority></url>")
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemap.org/schemas/sitemap/0.9">\n'.replace("www.sitemap.org", "www.sitemaps.org")
    write_raw("sitemap.xml", sm + "\n".join(rows) + "\n</urlset>\n")
    write_raw("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")

def write_raw(path, content):
    full = os.path.join("site", path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w", encoding="utf-8").write(content)

def page_404():
    body = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Page not found | {BRAND}</title><meta name="robots" content="noindex,follow">
<link rel="stylesheet" href="{BASE}/assets/style.css"><meta name="theme-color" content="#05060A"></head>
<body>{header()}<main id="main" class="section section--narrow"><div class="panel">
<p class="kicker">404</p><h1 class="page-title">This page slipped out of the frame</h1>
<p>The page you wanted is not here. It may have moved, or it may not be published yet.</p>
<div class="hero__cta"><a class="btn btn--primary" href="{BASE}/">Back to home</a><a class="btn btn--ghost" href="{BASE}/movies/">Browse movies</a></div>
</div></main>{footer()}"""
    write_raw("404.html", body)

def main():
    if os.path.isdir("site"): shutil.rmtree("site")
    os.makedirs("site", exist_ok=True)
    page_home(); page_movies_hub(); page_categories_hub(); page_people_hub()
    for m in D["movies"]: page_movie(m)
    for g in GEN: page_category(g)
    for p in PPL: page_person(p)
    page_about(); page_privacy(); page_terms(); page_faq()
    page_404(); write_sitemap()
    for src in ["assets/style.css", "assets/app.js", "assets/favicon.svg", "assets/fonts/instrument-serif.woff2", "assets/fonts/inter-var.woff2"]:
        dst = os.path.join("site", src); os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(src, dst)
    print(f"pages: {len(set(PAGES))} | files: {sum(len(f) for _, _, f in os.walk('site'))}")

if __name__ == "__main__":
    main()
