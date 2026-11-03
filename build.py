#!/usr/bin/env python3
"""MovieState — static site generator (Phase 2: cinematic home)."""
import json, html, os
from datetime import date

BASE = "https://moviestate.github.io/MovieState"
MAIN = "https://moviestate.is-best.net"
IMG = "https://image.tmdb.org/t/p/"
D = json.load(open("data/movies.json"))
CFG = json.load(open("data/site.json")) if os.path.exists("data/site.json") else {}
MOV = {m["tmdb_id"]: m for m in D["movies"]}
e = html.escape

def poster(m, size="w500"):
    return f"{IMG}{size}{m['poster']}" if m.get("poster") else ""

def backdrop(m, size="w1280"):
    return f"{IMG}{size}{m['backdrop']}" if m.get("backdrop") else ""

def meta(m):
    bits = []
    if m.get("year"): bits.append(str(m["year"]))
    if m.get("genres"): bits.append(m["genres"][0])
    if m.get("rating"): bits.append(f"{m['rating']}/10")
    return bits

def card(m, rank=None):
    p = poster(m)
    img = (f'<img class="card__img" src="{p}" alt="{e(m["title"])} poster" loading="lazy" decoding="async" width="500" height="750">'
           if p else '<span class="card__fallback" aria-hidden="true">' + e(m["title"][:1]) + "</span>")
    rk = f'<span class="card__rank">{rank:02d}</span>' if rank else ""
    rating = f'<span class="card__rating">★ {m["rating"]}</span>' if m.get("rating") else ""
    return f'''<article class="card">
  <div class="card__poster">{img}{rk}{rating}
    <div class="card__overlay"><span class="card__genre">{e((m.get("genres") or [""])[0])}</span><span class="card__cue">Read the guide</span></div>
  </div>
  <h3 class="card__title">{e(m["title"])}</h3>
  <p class="card__meta">{" · ".join(meta(m))}</p>
</article>'''

def rail(ids, ranks=True):
    out = []
    for i, mid in enumerate(ids, 1):
        m = MOV.get(mid)
        if not m: continue
        body = card(m, i if ranks else None)
        out.append(body)
    return "\n".join(out)

def mid(title):
    for m in D["movies"]:
        if m["title"].lower() == title.lower():
            return m["tmdb_id"]
    return None

FEATURED = mid("Spider-Man: Brand New Day")
TRENDING = [mid(t) for t in ["Resident Evil","Primetime","Beware Boiúna","Wildwood","Godzilla Minus Zero",
            "A Story of Derry","My Best Friend","Verity","Clayface","The Mongoose"]]
POPULAR = [mid(t) for t in ["The Dark Knight","Spider-Man: Brand New Day","The Odyssey","Coco","Fall 2: Deadpoint",
           "Insidious: Out of the Further","Pinocchio: Unstrung","Apocalypse Z: New World","Wildwood","Hope",
           "The Dog Stars","Buddy"]]
EDITORIAL = ["The Odyssey","Resident Evil","Spider-Man: Brand New Day"]

FAQ = [
 ("What is MovieState?", "MovieState is an independent movie discovery site. For each film we publish a detail guide — story, cast, runtime, ratings and where to watch — and link you to the MovieState streaming library when you are ready to watch."),
 ("How do I find where to watch a movie?", "Open any movie guide and read the where-to-watch section. Streaming availability changes by country and provider, so we point you to the library that keeps availability current instead of publishing a list that goes stale."),
 ("Is browsing MovieState free?", "Yes. Every guide on this site is free to read, with no account and no paywall. Watching happens on the MovieState streaming site."),
 ("How current is the information?", "Movie facts come from TMDB and are reviewed by our editors. Ratings and availability move constantly, so each guide shows its last update date — treat it as a snapshot, not a promise."),
 ("Can I request a movie guide?", "Yes. Tell us the title and we will queue it for a guide. Popular requests are prioritised in the publishing calendar."),
]

def genre_tiles():
    names = ["Action","Adventure","Animation","Comedy","Crime","Documentary","Drama","Family",
             "Fantasy","Horror","Mystery","Romance","Sci-Fi","Thriller","War","Western"]
    return "\n".join(f'<li class="genre"><span class="genre__name">{g}</span></li>' for g in names)

def editorial_cards():
    out = []
    for t in EDITORIAL:
        m = MOV.get(mid(t))
        if not m: continue
        out.append(f'''<article class="editorial__card">
  <img class="editorial__img" src="{backdrop(m)}" alt="{e(m["title"])} still" loading="lazy" decoding="async" width="1280" height="720">
  <div class="editorial__body">
    <p class="eyebrow">{(m.get("genres") or ["Film"])[0]}</p>
    <h3>{e(m["title"])}</h3>
    <p class="editorial__text">{e((m.get("overview") or "")[:150])}…</p>
  </div>
</article>''')
    return "\n".join(out)

def faq_html():
    items = []
    for q, a in FAQ:
        items.append(f'<details class="faq"><summary>{e(q)}</summary><p>{e(a)}</p></details>')
    return "\n".join(items)

def jsonld():
    f = MOV[FEATURED]
    site = {"@context":"https://schema.org","@type":"WebSite","name":"MovieState",
            "url":BASE+"/","description":"Movie guides, cast details and where to watch — curated by MovieState.",
            "inLanguage":"en"}
    org = {"@context":"https://schema.org","@type":"Organization","name":"MovieState","url":BASE+"/"}
    lst = {"@context":"https://schema.org","@type":"ItemList","name":"Popular movies on MovieState",
           "itemListElement":[{"@type":"ListItem","position":i+1,"name":MOV[x]["title"],"url":MAIN}
                              for i,x in enumerate([p for p in POPULAR if p][:10])]}
    faq = {"@context":"https://schema.org","@type":"FAQPage",
           "mainEntity":[{"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}} for q,a in FAQ]}
    return "\n".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in [site,org,lst,faq])

def page_home():
    f = MOV[FEATURED]
    tick = "".join(f'<span>{e(MOV[x]["title"])}</span><i aria-hidden="true">◆</i>' for x in TRENDING if MOV.get(x))
    meta_row = "".join(f'<li>{e(str(v))}</li>' for v in [f.get("year"), (f.get("genres") or [""])[0], "PG-13", "2h 25m"])
    stars = f'<span class="hero__score">★ {f["rating"]}<small>/10</small></span>' if f.get("rating") else ""
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MovieState — Watch Movies Online in HD &amp; Where to Watch</title>
<meta name="description" content="Discover trending and popular movies with full guides: story, cast, runtime, ratings and where to watch online in HD. MovieState — your cinema companion.">
<link rel="canonical" href="{BASE}/">
<meta name="robots" content="index,follow,max-image-preview:large">
<meta name="theme-color" content="#08080A">
<meta property="og:type" content="website">
<meta property="og:site_name" content="MovieState">
<meta property="og:title" content="MovieState — Watch Movies Online in HD &amp; Where to Watch">
<meta property="og:description" content="Trending movies, full film guides and where to watch each one online in HD.">
<meta property="og:url" content="{BASE}/">
<meta property="og:image" content="{backdrop(f)}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://image.tmdb.org" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/style.css">
{jsonld()}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<div class="grain" aria-hidden="true"></div>

<header class="header" id="top">
  <div class="header__inner">
    <a class="brand" href="{BASE}/">
      <span class="brand__mark">MS</span>
      <span class="brand__name">Movie<em>State</em></span>
    </a>
    <nav class="nav" aria-label="Sections">
      <a href="#trending">Trending</a>
      <a href="#popular">Popular</a>
      <a href="#genres">Genres</a>
      <a href="#faq">FAQ</a>
    </nav>
    <a class="btn btn--line btn--sm" href="{MAIN}/" target="_blank" rel="noopener">Open MovieState<svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M7 17 17 7M9 7h8v8" stroke="currentColor" stroke-width="2"/></svg></a>
  </div>
</header>

<main id="main">
  <section class="hero" aria-labelledby="hero-title">
    <img class="hero__bg" src="{IMG}original{f['backdrop']}" alt="" fetchpriority="high" decoding="async">
    <div class="hero__scrim" aria-hidden="true"></div>
    <div class="hero__inner">
      <p class="eyebrow eyebrow--line">Featured this week</p>
      <h1 class="hero__title" id="hero-title">{e(f["title"])}<span>Dive into the story — and find where to watch in HD</span></h1>
      <ul class="meta__row">{meta_row}</ul>
      <p class="hero__lede">{e((f.get("overview") or "")[:190])}…</p>
      <div class="hero__actions">
        <a class="btn btn--gold" href="{MAIN}/" target="_blank" rel="noopener">Watch on MovieState</a>
        <a class="btn btn--line" href="#trending">Explore trending</a>
      </div>
      {stars}
    </div>
    <div class="hero__edge" aria-hidden="true"></div>
  </section>

  <div class="ticker" role="presentation"><div class="ticker__track">{tick}{tick}</div></div>

  <section class="section" id="trending" aria-labelledby="h-trending">
    <div class="section__head">
      <p class="eyebrow">What people are watching</p>
      <h2 id="h-trending">Trending movies this week</h2>
      <p class="section__sub">Real search interest, refreshed as the week moves. Every title below has a full guide.</p>
    </div>
    <div class="rail" tabindex="0">{rail(TRENDING)}</div>
  </section>

  <section class="section" id="popular" aria-labelledby="h-popular">
    <div class="section__head">
      <p class="eyebrow">The heavy hitters</p>
      <h2 id="h-popular">Popular movies to watch online</h2>
      <p class="section__sub">Films audiences keep coming back to — from new 2026 releases to modern classics.</p>
    </div>
    <div class="grid">{rail(POPULAR, ranks=False)}</div>
  </section>

  <section class="section section--editorial" aria-labelledby="h-editorial">
    <div class="section__head">
      <p class="eyebrow">Go deeper</p>
      <h2 id="h-editorial">Guides worth your evening</h2>
    </div>
    <div class="editorial">{editorial_cards()}</div>
  </section>

  <section class="section" id="genres" aria-labelledby="h-genres">
    <div class="section__head">
      <p class="eyebrow">Follow a mood</p>
      <h2 id="h-genres">Browse movies by genre</h2>
    </div>
    <ul class="genres">{genre_tiles()}</ul>
  </section>

  <section class="strip" aria-label="About MovieState">
    <div class="strip__item"><strong>Free to read</strong><span>Every guide, no account</span></div>
    <div class="strip__item"><strong>Updated weekly</strong><span>New films and fresh facts</span></div>
    <div class="strip__item"><strong>Region-aware</strong><span>Where to watch near you</span></div>
    <div class="strip__item"><strong>TMDB data</strong><span>Reviewed by our editors</span></div>
  </section>

  <section class="section" id="faq" aria-labelledby="h-faq">
    <div class="section__head">
      <p class="eyebrow">Good to know</p>
      <h2 id="h-faq">Frequently asked questions</h2>
    </div>
    <div class="faq__list">{faq_html()}</div>
  </section>
</main>

<footer class="footer">
  <div class="footer__inner">
    <div class="footer__brand">
      <a class="brand" href="{BASE}/"><span class="brand__mark">MS</span><span class="brand__name">Movie<em>State</em></span></a>
      <p>Independent movie guides — story, cast, ratings and where to watch, kept honest.</p>
    </div>
    <nav class="footer__col" aria-label="Explore"><h2>Explore</h2>
      <a href="#trending">Trending</a><a href="#popular">Popular</a><a href="#genres">Genres</a><a href="#faq">FAQ</a>
    </nav>
    <nav class="footer__col" aria-label="MovieState"><h2>MovieState</h2>
      <a href="{MAIN}/" target="_blank" rel="noopener">Streaming library</a>
      <a href="{MAIN}/category/popular" target="_blank" rel="noopener">Popular on MovieState</a>
    </nav>
  </div>
  <div class="footer__legal">
    <p>© {date.today().year} MovieState. Movie information and imagery provided by TMDB. MovieState is not endorsed or certified by TMDB.</p>
    <p>Streaming availability varies by region and provider. Confirm details with the official service before subscribing.</p>
  </div>
</footer>
<script src="assets/app.js" defer></script>
</body>
</html>'''

def page_404():
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Page not found — MovieState</title><meta name="robots" content="noindex,follow">
<link rel="canonical" href="{BASE}/"><link rel="stylesheet" href="assets/style.css"></head>
<body><div class="grain" aria-hidden="true"></div><main class="lost">
<p class="eyebrow">404</p><h1>This reel is missing</h1>
<p class="lost__text">The page you were looking for is not here — yet. Guides are publishing continuously.</p>
<a class="btn btn--gold" href="{BASE}/">Back to MovieState</a></main></body></html>'''

write = lambda p, s: (open(p, "w", encoding="utf-8").write(s), print("wrote", p, len(s), "bytes"))
write("index.html", page_home())
write("404.html", page_404())
write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")
write("sitemap.xml", f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>{BASE}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>
</urlset>''')
write("assets/favicon.svg", '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#08080A"/><text x="32" y="42" font-family="Georgia,serif" font-size="26" fill="#D8B26A" text-anchor="middle">MS</text></svg>')
