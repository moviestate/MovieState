#!/usr/bin/env python3
"""
MovieState GitHub Pages builder — Phase 1 (premium home page).
Generates index.html, 404.html, robots.txt, sitemap.xml.
Data lives in data/site.json so later phases (movie pages) reuse it.
"""
import json, os, html, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "https://moviestate.github.io/MovieState"
MAIN_SITE = "https://moviestate.is-best.net"

with open(os.path.join(ROOT, "data", "site.json"), encoding="utf-8") as f:
    S = json.load(f)

TODAY = datetime.date.today().strftime("%B %-d, %Y")

def esc(t):
    return html.escape(t, quote=True)

def card(m, rank=None, big=False):
    tone = m.get("tone", "#1b1b24")
    rating = m.get("rating")
    badge = f'<span class="chip chip--rating"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2l2.9 6.3 6.9.8-5.1 4.7 1.4 6.8L12 17.2 5.9 20.6l1.4-6.8L2.2 9.1l6.9-.8z"/></svg>{rating}</span>' if rating else ""
    cls = "card card--big" if big else "card"
    return f'''
        <article class="{cls}" style="--tone:{tone}">
          {f'<span class="card__rank">{rank}</span>' if rank else ''}
          <div class="card__poster" aria-hidden="true"><span>{esc(m["title"][0])}</span></div>
          <div class="card__body">
            <h3 class="card__title">{esc(m["title"])}</h3>
            <p class="card__meta">{esc(str(m["year"]))}{(" · " + esc(m["genre"])) if m.get("genre") else ""}</p>
            {badge}
          </div>
        </article>'''

trending = "".join(card(m, i + 1) for i, m in enumerate(S["trending"]))
popular = "".join(card(m) for m in S["popular"])
searched = "".join(
    f'<li><span class="rank">{i+1:02d}</span><span>{esc(t)}</span></li>'
    for i, t in enumerate(S["most_searched"])
)
genres = "".join(f'<li><span class="pill">{esc(g)}</span></li>' for g in S["genres"])

featured = S["featured"]

jsonld_website = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "MovieState",
    "url": BASE_URL + "/",
    "description": S["description"],
    "inLanguage": "en",
}
jsonld_org = {
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "MovieState",
    "url": BASE_URL + "/",
    "description": "MovieState is an independent movie discovery and watch-guide publication.",
}
jsonld_list = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    "name": "Popular movies on MovieState",
    "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": m["title"]}
        for i, m in enumerate(S["popular"])
    ],
}
jsonld_faq = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [
        {"@type": "Question", "name": q["q"],
         "acceptedAnswer": {"@type": "Answer", "text": q["a"]}}
        for q in S["faq"]
    ],
}

def ld(obj):
    return f'<script type="application/ld+json">{json.dumps(obj, ensure_ascii=False)}</script>'

faq_html = "".join(
    f'<details class="faq__item"><summary>{esc(q["q"])}</summary><p>{esc(q["a"])}</p></details>'
    for q in S["faq"]
)

NAV = "".join(f'<a href="{h}">{esc(l)}</a>' for l, h in S["nav"])

INDEX = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MovieState — Watch Movies Online in HD & Where to Watch</title>
<meta name="description" content="Discover trending and popular movies, release info, cast details and where to watch each film online in HD. Independent movie guides from MovieState.">
<link rel="canonical" href="{BASE_URL}/">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="theme-color" content="#0A0A0D">
<meta property="og:type" content="website">
<meta property="og:site_name" content="MovieState">
<meta property="og:title" content="MovieState — Watch Movies Online in HD & Where to Watch">
<meta property="og:description" content="Trending movies, release details and clear where-to-watch guides for film fans worldwide.">
<meta property="og:url" content="{BASE_URL}/">
<meta property="og:image" content="{BASE_URL}/assets/og-home.jpg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="MovieState — Watch Movies Online in HD">
<meta name="twitter:description" content="Trending movies, release details and clear where-to-watch guides.">
<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="assets/style.css">
{ld(jsonld_website)}
{ld(jsonld_org)}
{ld(jsonld_list)}
{ld(jsonld_faq)}
</head>
<body id="top">
<a class="skip" href="#main">Skip to content</a>

<header class="header">
  <div class="wrap header__in">
    <a class="brand" href="#top" aria-label="MovieState home">
      <span class="brand__mark" aria-hidden="true">MS</span>
      <span class="brand__name">Movie<span>State</span></span>
    </a>
    <nav class="nav" aria-label="Primary">{NAV}</nav>
    <a class="btn btn--ghost btn--sm header__cta" href="{MAIN_SITE}" target="_blank" rel="noopener">Open MovieState</a>
  </div>
</header>

<main id="main">

  <section class="hero">
    <div class="hero__glow" aria-hidden="true"></div>
    <div class="wrap">
      <p class="eyebrow">Independent movie discovery · Updated {TODAY}</p>
      <h1>Watch Movies Online in HD —<br><span class="grad">Trending Picks &amp; Where to Watch</span></h1>
      <p class="lead">MovieState tracks what people are actually watching, then tells you what each film is, who is in it, and where you can stream it. No noise, no dead ends.</p>
      <div class="hero__actions">
        <a class="btn btn--primary" href="#trending">Explore trending movies</a>
        <a class="btn btn--ghost" href="{MAIN_SITE}" target="_blank" rel="noopener">Watch on MovieState</a>
      </div>

      <aside class="spotlight" aria-labelledby="spotlight-title">
        <div class="spotlight__poster" aria-hidden="true"><span>{esc(featured["title"][0])}</span></div>
        <div class="spotlight__body">
          <p class="spotlight__label">🔥 Featured this week</p>
          <h2 id="spotlight-title">{esc(featured["title"])} <span>({esc(str(featured["year"]))})</span></h2>
          <p class="spotlight__text">{esc(featured["blurb"])}</p>
          <ul class="facts">
            {''.join(f'<li><strong>{esc(k)}</strong><span>{esc(v)}</span></li>' for k, v in featured["facts"])}
          </ul>
          <p class="spotlight__cta">
            <a class="btn btn--primary btn--sm" href="{MAIN_SITE}/movie/{esc(featured["main_id"])}/{esc(featured["slug"])}" target="_blank" rel="noopener">Watch {esc(featured["title"])} in HD</a>
            <span class="muted">Full where-to-watch guide publishing soon.</span>
          </p>
        </div>
      </aside>
    </div>
  </section>

  <section class="section" id="trending">
    <div class="wrap">
      <div class="section__head">
        <h2>Trending now</h2>
        <p class="section__sub">What film fans searched for most this week.</p>
      </div>
      <div class="grid grid--trend">{trending}</div>
    </div>
  </section>

  <section class="section section--alt" id="popular">
    <div class="wrap">
      <div class="section__head">
        <h2>Popular movies</h2>
        <p class="section__sub">The titles holding the top of the chart right now.</p>
      </div>
      <div class="grid">{popular}</div>
    </div>
  </section>

  <section class="section" id="searched">
    <div class="wrap two-col">
      <div>
        <div class="section__head section__head--left">
          <h2>Most searched on MovieState</h2>
          <p class="section__sub">Live demand, not guesswork. This list mirrors what visitors look for most.</p>
        </div>
        <ol class="ranklist">{searched}</ol>
      </div>
      <div class="panel">
        <h2 class="panel__title">Why people use MovieState</h2>
        <ul class="checklist">
          <li><strong>Facts first.</strong> Plot, cast, runtime and studio details for every title.</li>
          <li><strong>Clear watch routes.</strong> One place to see where a film is available in HD.</li>
          <li><strong>No dead links.</strong> If a page does not help, it does not get published.</li>
          <li><strong>Guides, not filler.</strong> Practical answers to “is it worth watching?”</li>
        </ul>
        <a class="btn btn--ghost btn--sm" href="{MAIN_SITE}" target="_blank" rel="noopener">Browse the full library →</a>
      </div>
    </div>
  </section>

  <section class="section section--alt" id="genres">
    <div class="wrap">
      <div class="section__head">
        <h2>Browse by genre</h2>
        <p class="section__sub">From horror nights to family Sundays — pick a lane.</p>
      </div>
      <ul class="pills">{genres}</ul>
    </div>
  </section>

  <section class="section" id="how">
    <div class="wrap">
      <div class="section__head">
        <h2>How MovieState works</h2>
        <p class="section__sub">Three steps from “what should I watch?” to pressing play.</p>
      </div>
      <div class="steps">
        <div class="step"><span class="step__num">01</span><h3>Find the film</h3><p>Search by title, genre or what everyone is talking about this week.</p></div>
        <div class="step"><span class="step__num">02</span><h3>Read the real details</h3><p>Plot, cast, runtime, ratings and honest notes — no recycled filler.</p></div>
        <div class="step"><span class="step__num">03</span><h3>Watch in HD</h3><p>Jump straight to the film on MovieState and pick your server.</p></div>
      </div>
    </div>
  </section>

  <section class="section section--alt" id="faq">
    <div class="wrap wrap--narrow">
      <div class="section__head">
        <h2>MovieState — frequently asked questions</h2>
      </div>
      <div class="faq">{faq_html}</div>
    </div>
  </section>

</main>

<footer class="footer">
  <div class="wrap footer__in">
    <div class="footer__brand">
      <span class="brand__name">Movie<span>State</span></span>
      <p class="muted">Independent movie discovery, release coverage and watch guides for film fans worldwide.</p>
    </div>
    <nav class="footer__nav" aria-label="Footer">
      <a href="#trending">Trending</a>
      <a href="#popular">Popular</a>
      <a href="#genres">Genres</a>
      <a href="{MAIN_SITE}" target="_blank" rel="noopener">Main site</a>
    </nav>
  </div>
  <div class="wrap footer__legal">
    <p>© 2026 MovieState. Movie information and images are provided by TMDB; MovieState is not endorsed or certified by TMDB.</p>
    <p class="muted">Page last updated {TODAY}.</p>
  </div>
</footer>

<script src="assets/app.js" defer></script>
</body>
</html>
'''

NOTFOUND = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Page not found — MovieState</title>
<meta name="robots" content="noindex, follow">
<link rel="icon" href="/MovieState/assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/MovieState/assets/style.css">
</head>
<body>
<header class="header"><div class="wrap header__in">
  <a class="brand" href="/MovieState/"><span class="brand__mark" aria-hidden="true">MS</span><span class="brand__name">Movie<span>State</span></span></a>
</div></header>
<main class="wrap" style="padding:80px 20px;text-align:center">
  <p class="eyebrow">404</p>
  <h1 style="font-size:clamp(2rem,5vw,3.2rem)">This page slipped off the reel</h1>
  <p class="lead" style="margin-inline:auto">The movie page you tried to open does not exist yet — our guides are publishing one by one.</p>
  <p><a class="btn btn--primary" href="/MovieState/">Back to the homepage</a></p>
</main>
</body>
</html>
'''

ROBOTS = f"""User-agent: *
Allow: /

Sitemap: {BASE_URL}/sitemap.xml
"""

SITEMAP = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{BASE_URL}/</loc>
    <lastmod>{datetime.date.today().isoformat()}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
'''

FAVICON = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect width="64" height="64" rx="14" fill="#0A0A0D"/>
<text x="32" y="42" font-family="Arial,Helvetica,sans-serif" font-size="26" font-weight="700" fill="#E9B44C" text-anchor="middle">MS</text>
</svg>'''

files = {
    "index.html": INDEX,
    "404.html": NOTFOUND,
    "robots.txt": ROBOTS,
    "sitemap.xml": SITEMAP,
    "assets/favicon.svg": FAVICON,
}
for path, content in files.items():
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True) if os.path.dirname(full) else None
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    print("wrote", path, len(content), "bytes")
