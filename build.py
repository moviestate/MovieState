#!/usr/bin/env python3
"""MovieState static site generator - v3 (black & royal blue)."""
import json, html, os, re, shutil, hashlib
from urllib.parse import quote_plus
from datetime import date

BASE = "https://moviestate.github.io/MovieState"
BRAND = "MovieState"
TODAY = "2026-11-04"

# Optional analytics: set "ga4_id": "G-XXXXXXXXXX" in data/site.json to enable.
try:
    _SITE_CFG = json.load(open("data/site.json"))
except Exception:
    _SITE_CFG = {}
GA4_ID = str(_SITE_CFG.get("ga4_id") or "").strip()
GA_TAG = (f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA4_ID}"></script>'
          f'<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag("js",new Date());gtag("config","{GA4_ID}");</script>') if GA4_ID else '' 

D = json.load(open("data/movies.json"))
MOV = {m["tmdb_id"]: m for m in D["movies"]}
GEN = json.load(open("data/genres.json"))
PPL_ALL = json.load(open("data/people.json"))
PPL = [p for p in PPL_ALL if len(p.get("biography","")) > 200]
PPL_BY_ID = {p["id"]: p for p in PPL_ALL}
PPL_OK = {p["id"] for p in PPL}

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
MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
MONFULL = ["January","February","March","April","May","June","July","August","September","October","November","December"]
def _pd(iso):
    try: return tuple(int(x) for x in str(iso)[:10].split("-"))
    except Exception: return None
def fmt_date(iso, long=False):
    t = _pd(iso)
    if not t: return ""
    y, mo, d = t
    return f"{MON[mo-1]} {d}, {y}" if not long else f"{MONFULL[mo-1]} {d}, {y}"
def month_key(iso):
    t = _pd(iso)
    return f"{MONFULL[t[1]-1]} {t[0]}" if t else "TBA"
def days_until(iso):
    from datetime import date
    t = _pd(iso); n = _pd(TODAY)
    if not t or not n: return None
    return (date(*t) - date(*n)).days
def until_label(iso):
    d = days_until(iso)
    if d is None: return ""
    if d == 0: return "Out today"
    if d == 1: return "Out tomorrow"
    if d < 0: return "Released"
    if d < 14: return f"In {d} days"
    if d < 60: return f"In {round(d/7)} weeks"
    return f"In {round(d/30)} months"
def release_label(m):
    iso = m.get("release_date") or ""; st = (m.get("status") or "").strip()
    d = days_until(iso)
    if d is not None and d > 0:
        low = st.lower()
        if low in ("released", "", "in production", "post production", "planned", "rumored"):
            st = "In cinemas" if low == "released" else (st or "Announced")
        return {"date": fmt_date(iso), "phase": "upcoming", "note": until_label(iso), "status": st}
    return {"date": fmt_date(iso), "phase": "released", "note": "", "status": st or "Released"}
UPCOMING = lambda: sorted([m for m in D["movies"] if (days_until(m.get("release_date") or "") or -1) > 0], key=lambda m: m.get("release_date") or "")

def watch_url(m):
    """Official availability index (JustWatch). We never link to unlicensed streamers."""
    return "https://www.justwatch.com/us/search?q=" + quote_plus(f"{m['title']} {m['year']}")
def esc_js(s): return json.dumps(s, ensure_ascii=False)

def trim(s, n=155):
    """Cut at a real sentence end, else a clause, else a clean word boundary."""
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    if len(s) <= n: return s
    cut = s[:n]
    best = -1
    for m in re.finditer(r"[.!?]\s", cut):
        k = m.start()
        prev = cut[:k].split(" ")[-1]
        if len(prev.rstrip(".")) == 1:  # single-letter abbreviation, not a sentence end
            continue
        if k >= 70: best = max(best, k)
        break
    if best > 0: return cut[:best+1]
    for sep in (", ", "; ", ": ", " - ", " – "):
        k = cut.rfind(sep)
        if k >= 70: return cut[:k].rstrip(",;:- ") + "."
    cut = cut[:cut.rfind(" ")] if " " in cut else cut
    stop = {"a","an","the","and","or","of","in","on","for","to","with","by","his","her","their","its","as","at","from","is","are","was","best","known","who","that"}
    words = cut.split()
    while words and words[-1].lower().strip(",.;:") in stop: words.pop()
    return " ".join(words).rstrip(",;:- ") + "."

def article(word):
    return "an" if str(word or "")[:1].lower() in "aeiou" else "a"

def join_and(items):
    items = [str(i) for i in items if i]
    if len(items) <= 1: return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]

def clean_bio(s):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    s = re.sub(r"^[,;\s]+", "", s)
    return s

def split_bio(bio, lead_n=360):
    """Split a biography on a sentence boundary so no block starts mid-sentence."""
    bio = clean_bio(bio)
    if len(bio) <= lead_n: return bio, ""
    sents = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])", bio)
    lead = ""
    for s_ in sents:
        if len(lead) + len(s_) > lead_n + 120 and lead: break
        lead = (lead + " " + s_).strip()
        if len(lead) >= lead_n: break
    rest = bio[len(lead):].strip()
    return lead, rest[:1100]

# Outbound link attributes: monetised / affiliated destination
OUT_REL = "sponsored nofollow noopener"

PAGES = []

def _ver(path):
    try:
        return hashlib.md5(open(path, "rb").read()).hexdigest()[:8]
    except Exception:
        return "1"

CSSVER = _ver("assets/style.css")
JSVER = _ver("assets/app.js")

def head(title, desc, path, og_image=None, jsonld=None, extra_css="", preload_img=None, og_type="website", noindex=False, prev_url=None, next_url=None):
    clean = "" if path in ("", "index.html") else re.sub(r"index\.html$", "", path)
    url = f"{BASE}/{clean}" if clean else f"{BASE}/"
    og = og_image or f"{BASE}/assets/og-default.jpg"
    robots = "index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1" if not noindex else "noindex,follow"
    parts = [f"""<!doctype html><html lang="en" data-theme="light"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<script>try{{var t=localStorage.getItem("ms-theme");if(t==="dark"||t==="light"){{document.documentElement.dataset.theme=t}}}}catch(e){{}}</script>
<title>{e(title)}</title><meta name="description" content="{e(desc)}">{GA_TAG}
<link rel="canonical" href="{url}">{f'<link rel="prev" href="{prev_url}">' if prev_url else ""}{f'<link rel="next" href="{next_url}">' if next_url else ""}{f'<link rel="preload" as="image" href="{preload_img}" fetchpriority="high">' if preload_img else ""}
<meta name="robots" content="{robots}">
<meta name="theme-color" content="#FFFFFF">
<meta property="og:type" content="{og_type}"><meta property="og:site_name" content="{BRAND}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}"><meta property="og:image" content="{e(og)}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}"><meta name="twitter:image" content="{e(og)}">
<link rel="preconnect" href="https://image.tmdb.org" crossorigin>
<link rel="preload" href="{BASE}/assets/fonts/instrument-serif.woff2" as="font" type="font/woff2" crossorigin>
<link rel="icon" href="{BASE}/assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{BASE}/assets/style.css?v={CSSVER}">
<script src="{BASE}/assets/app.js?v={JSVER}" defer></script>"""]
    for block in (jsonld or []):
        parts.append(f'<script type="application/ld+json">{json.dumps(block, ensure_ascii=False)}</script>')
    parts.append("</head><body>")
    return "\n".join(parts)

ORG = {"@type": "Organization", "name": BRAND, "url": BASE + "/", "logo": {"@type": "ImageObject", "url": BASE + "/assets/favicon.svg"}}

def logo_svg(uid="a"):
    return ('<svg viewBox="0 0 44 44" role="img" aria-label="MovieState logo" xmlns="http://www.w3.org/2000/svg">'
      '<defs><linearGradient id="mb' + uid + '" x1="0" y1="0" x2="1" y2="1">'
      '<stop offset="0" stop-color="#7E97FF"/><stop offset=".5" stop-color="#2B4CFF"/><stop offset="1" stop-color="#0A1150"/></linearGradient>'
      '<linearGradient id="mf' + uid + '" x1="0" y1="1" x2="1" y2="0">'
      '<stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#BFD0FF"/></linearGradient></defs>'
      '<rect x=".8" y=".8" width="42.4" height="42.4" rx="13" fill="url(#mb' + uid + ')"/>'
      '<rect x="1.4" y="1.4" width="41.2" height="41.2" rx="12.4" fill="none" stroke="rgba(255,255,255,.26)" stroke-width="1"/>'
      '<g fill="#fff" opacity=".34">'
      '<rect x="5.4" y="9.4" width="3.1" height="3.5" rx="1.1"/><rect x="5.4" y="20.2" width="3.1" height="3.5" rx="1.1"/><rect x="5.4" y="31" width="3.1" height="3.5" rx="1.1"/>'
      '<rect x="35.5" y="9.4" width="3.1" height="3.5" rx="1.1"/><rect x="35.5" y="20.2" width="3.1" height="3.5" rx="1.1"/><rect x="35.5" y="31" width="3.1" height="3.5" rx="1.1"/></g>'
      '<path d="M14.6 31V13.4l7.4 9.6 7.4-9.6V31" fill="none" stroke="url(#mf' + uid + ')" stroke-width="3.2" '
      'stroke-linecap="round" stroke-linejoin="round"/></svg>')

def header(active=""):
    nav = [("Movies", "/movies/"), ("Categories", "/categories/"), ("People", "/people/"), ("Articles", "/articles/"), ("FAQ", "/faq/"), ("About", "/about/")]
    def one(t, h):
        mark = ' aria-current="page"' if h == active else ''
        return f'<a href="{BASE}{h}"{mark}>{e(t)}</a>'
    links = "".join(one(t, h) for t, h in nav)
    return f"""<a class="skip" href="#main">Skip to content</a>
<header class="header"><div class="header__inner">
<a class="logo" href="{BASE}/" aria-label="MovieState home">{logo_svg("a")}<span class="logo__word"><span class="logo__name">MovieState</span><span class="logo__tag">Premium Cinema Guide</span></span></a>
<nav class="nav" aria-label="Main">{links}</nav>
<button class="theme-toggle" type="button" aria-label="Switch to dark mode" aria-pressed="false" title="Switch theme">
<span class="theme-toggle__sun" aria-hidden="true"><svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><circle cx="12" cy="12" r="4.2"/><path d="M12 2.6v2.2M12 19.2v2.2M2.6 12h2.2M19.2 12h2.2M5.4 5.4l1.6 1.6M17 17l1.6 1.6M18.6 5.4L17 7M7 17l-1.6 1.6"/></svg></span>
<span class="theme-toggle__moon" aria-hidden="true"><svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M20.5 14.4A8.6 8.6 0 1 1 9.6 3.5a7 7 0 0 0 10.9 10.9z"/></svg></span>
</button>
<a class="btn btn--primary btn--sm header__cta" href="{BASE}/movies/">Browse movies</a>
</div></header>"""

def footer():
    return f"""<footer class="footer"><div class="footer__inner">
<div class="footer__brand">{logo_svg("b")}<div><strong>{BRAND}</strong>
<p>An independent movie guide. We research films, cast, release details and where you can watch them — then send you to the right place.</p></div></div>
<div class="footer__cols">
<div><h3>Explore</h3><a href="{BASE}/movies/">All movies</a><a href="{BASE}/categories/">Categories</a><a href="{BASE}/people/">People</a></div>
<div><h3>Company</h3><a href="{BASE}/about/">About</a><a href="{BASE}/faq/">FAQ</a><a href="{BASE}/privacy-policy/">Privacy Policy</a><a href="{BASE}/terms/">Terms &amp; Conditions</a></div>
<div><h3>Guides</h3><a href="{BASE}/articles/">Articles</a><a href="{BASE}/movies/">All movie guides</a><a href="{BASE}/categories/">Categories</a><a href="{BASE}/people/">People</a></div>
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

NOINDEX_PATHS = set()

def apply_noindex():
    """Make the robots meta match the sitemap: every path in NOINDEX_PATHS is noindex,follow."""
    for p in NOINDEX_PATHS:
        f = os.path.join("site", p)
        if not os.path.exists(f): continue
        s = open(f, encoding="utf-8").read()
        s2 = re.sub(r'<meta name="robots" content="index,follow[^"]*">', '<meta name="robots" content="noindex,follow">', s, count=1)
        if s2 != s: open(f, "w", encoding="utf-8").write(s2)

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
<span class="card__score">{r:.1f}</span><span class="card__fade" aria-hidden="true"></span><span class="card__cta">View guide <i>&#8594;</i></span></div>
<div class="card__body"><h3 class="card__title">{e(t)}</h3><p class="card__sub">{e(y)}{" · " + e(m.get("genres", [""])[0]) if m.get("genres") else ""}</p></div>'''
    if href:
        if href.startswith('/'): href = BASE + href
        return f'<a class="card" href="{href}">{inner}</a>'
    return f'<div class="card card--static">{inner}</div>'

def ROLE_OF(p):
    d = (p.get("dept") or "").lower()
    if d == "directing": return "Director"
    if d == "writing": return "Writer"
    if d == "production": return "Producer"
    if d == "acting": return "Actor"
    return "Director" if "Director" in p.get("roles", []) and not p.get("dept") else "Actor"

def person_card(p, href=None):
    if href and href.startswith('/'): href = BASE + href
    if href and href.startswith("/"): href = BASE + href
    img = poster(p.get("profile"), "w185")
    role = ROLE_OF(p)
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
HOME_FAQ = []  # filled from FAQ_ITEMS below

def page_home():
    f = MOV[FEATURED_ID]
    trend = [MOV[i] for i in [1423191, 1156593, 1311031, 1083381, 1368166, 1315985, 1232493, 1368316, 1300118, 1339713] if i in MOV][:10]
    popular = [MOV[i] for i in [155, 969681, 1368337, 354912, 1232493, 1316311, 1315985, 1368166, 1311031, 1339713, 1083381, 1315772] if i in MOV][:12]
    tick = "".join(f'<span>{e(m["title"])}</span><i aria-hidden="true">◆</i>' for m in trend)
    trend_cards = "".join(card(m, movie_path(m)) for m in trend)
    pop_cards = "".join(card(m, movie_path(m)) for m in popular)
    cats = "".join(f'''<a class="cat" href="{BASE}/category/{g['slug']}/">
<img src="{poster(g['cover'], 'w342')}" alt="{e(g['name'])} movies" width="342" height="513" loading="lazy" decoding="async">
<span class="cat__veil" aria-hidden="true"></span><span class="cat__label"><span class="cat__count">{CAT_COUNT.get(g["slug"], 0)} {"guide" if CAT_COUNT.get(g["slug"], 0) == 1 else "guides"}</span>{e(g['name'])}</span></a>''' for g in GEN[:10])
    ppl = "".join(person_card(p, f"{BASE}{person_path(p)}") for p in PPL[:12])
    faq_html = "".join(f'<details class="faq__item"><summary><h3>{e(q)}</h3></summary><p>{e(a)}</p></details>' for q, a in HOME_FAQ)
    guides = "".join(f'<a class="ed-card" href="{BASE}{movie_path(m)}"><span class="kicker">{e(", ".join(m.get("genres", [])[:1]))}</span><h3>{e(m["title"])}</h3><p>Story, full cast, crew, ratings, box office and the streaming, rent and buy options reported for six regions.</p></a>' for m in popular[:3])
    provs = {}
    for mm in D["movies"]:
        for cc, v in (mm.get("providers") or {}).items():
            for key in ("flatrate", "rent", "buy"):
                for name in v.get(key, []):
                    provs[name] = provs.get(name, 0) + 1
    top_provs = sorted(provs.items(), key=lambda x: -x[1])[:14]
    prov_html = "".join(f'<li>{e(n)}</li>' for n, _ in top_provs)
    ld = [
      {"@context": "https://schema.org", "@type": "WebSite", "name": BRAND, "url": BASE + "/", "description": "Independent movie guide: trending films, cast and crew, release details and where to watch in HD.", "publisher": ORG},
      {"@context": "https://schema.org", **ORG},
      {"@context": "https://schema.org", "@type": "ItemList", "name": "Trending movies this week", "itemListElement": [
          {"@type": "ListItem", "position": i + 1, "url": BASE + movie_path(m), "name": m["title"]} for i, m in enumerate(trend)]},
      {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
          {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in HOME_FAQ]},
    ]
    h = head("MovieState: Movie Guide, Cast, Ratings & Where to Watch",
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
<div class="hero__cta"><a class="btn btn--primary" href="{watch_url(f)}" target="_blank" rel="noopener">Where to watch</a>
<a class="btn btn--ghost" href="{BASE}{movie_path(f)}">Movie details</a></div>
</div></section>
<div class="ticker" aria-hidden="true"><div class="ticker__track">{tick}{tick}</div></div>
<section class="section">{section_head("Now trending", "What everyone is watching this week", ("All movies", BASE + "/movies/"))}
<div class="rail"><div class="rail__track">{trend_cards}</div></div></section>
<section class="section">{section_head("Browse", "Categories built around how you actually choose films", ("All categories", BASE + "/categories/"))}
<div class="cat-grid">{cats}</div></section>
<section class="section">{section_head("Popular now", "Most-watched movies on MovieState", ("See all", BASE + "/movies/"))}
<div class="grid">{pop_cards}</div></section>
<section class="section">{section_head("Start here", "Three guides worth opening first", ("All guides", BASE + "/movies/"))}
<div class="ed-grid">{guides}</div></section>
<section class="section section--narrow">{section_head("How to watch", "Find where a film streams, rents or sells in HD")}
<div class="cols"><div class="panel"><h3 class="panel__title">Read the availability table, not the hype</h3>
<p>Every film page lists the services reported for the United States, United Kingdom, Canada, Australia, India and Bangladesh, split into streaming, rental and purchase. If a region shows nothing, that means no listing was reported — not that the film is impossible to watch.</p>
<div class="bar"><span style="width:100%"></span></div>
<p class="note">Streaming rights move weekly. A title can leave a service and return months later, and rental prices differ by store and quality tier.</p></div>
<div class="panel"><h3 class="panel__title">Services we check most often</h3><ul class="tags">{prov_html}</ul>
<p class="note">Aggregated from the provider listings on our film pages. Availability is verified on the provider page at the moment of watching.</p></div></div></section>
<section class="section">{section_head("Cast &amp; crew", "The people behind the films", ("All people", BASE + "/people/"))}
<div class="rail"><div class="rail__track rail__track--people">{ppl}</div></div></section>
<section class="section section--split">
<div class="panel"><h2 class="panel__title">What goes into every page</h2>
<p>Titles, cast, crew, runtimes, certifications, release dates by country, provider listings, budgets and grosses come from live movie data. Each page then adds plain-language context: what the film is, who made it, how it has been received, and how to watch it in your region.</p>
<ul class="ticks"><li>Full cast and crew, not a truncated five-name list</li><li>Release dates and age ratings split by country</li><li>Streaming, rent and buy options for six major markets</li><li>Box office and budget figures labelled as reported</li><li>No pop-ups, no forced sign-ups, no fake players</li></ul>
<a class="btn btn--primary" href="{BASE}/articles/">Read our viewing guides</a></div>
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
<div class="wrap">{crumbs(([("Home", "/"), ("Movies", "/movies/")] + ([((m.get("genres") or [""])[0], "/category/" + slug((m.get("genres") or [""])[0]) + "/")] if (m.get("genres") or [""])[0] else []) + [(t, None)]))}</div>
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
<div class="hero__cta"><a class="btn btn--primary" href="{watch_url(m)}" target="_blank" rel="noopener">Where to watch</a>
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
<a class="btn btn--primary" href="{watch_url(m)}" target="_blank" rel="{OUT_REL}">Check availability</a>
<p class="note">We publish information only. Always confirm details on the provider's own page before paying.</p></div>
<div class="panel panel--faq"><h2 class="panel__title">Questions about {e(t)}</h2>{faq_html}</div>
</section>
<section class="section">{section_head("More like this", f"Films similar to {t}", ("All movies", BASE + "/movies/"))}
<div class="grid">{rel_cards or '<p class="muted">More recommendations coming soon.</p>'}</div></section>
</main>{footer()}"""
    write(path + "index.html", body)

import sys as _sys
_sys.path.insert(0, "data")
from genre_editorial import EDIT as GENRE_EDIT
from editor_note import note as editor_note

GENRE_NOTES = {
 "Action": "Action films are built on movement: chase construction, fight choreography and set pieces that escalate. The genre covers everything from grounded thrillers to superhero spectacle, and the best entries balance practical stunts with a story worth caring about.",
 "Adventure": "Adventure movies sell a sense of scale — new worlds, long journeys, and stakes that grow with the map. They work best when the location feels like a character and the crew has a reason to keep moving.",
 "Animation": "Animated features span hand-drawn classics, stop-motion craft and modern CG pipelines. What separates the strongest ones is design and timing: expressive character work and jokes that land for adults as well as children.",
 "Comedy": "Comedy is the hardest genre to recommend blind, because humour depends on tone, timing and culture. The films worth your evening usually combine a clear comic premise with a cast that can improvise inside it.",
 "Crime": "Crime stories trade in procedure, motive and consequence. The genre ranges from heist precision to slow-burn character studies, and the strongest entries keep the tension in the choices rather than the body count.",
 "Documentary": "Documentaries turn research into narrative. The best ones earn trust through verifiable sourcing, give subjects room to speak, and resist the urge to flatten complicated evidence into a tidy conclusion.",
 "Drama": "Drama is the widest category here: family stories, courtroom battles, quiet character pieces. What holds it together is performance-driven writing, where small decisions carry the weight normally given to plot twists.",
 "Family": "Family films have to work for two audiences at once — children following the action and adults reading the jokes underneath. The genre's best entries respect both, which is why they stay in rotation for years.",
 "Fantasy": "Fantasy builds rules and then tests them. World-building matters, but the films that endure use magic as a way to talk about power, loyalty and loss rather than as pure decoration.",
 "History": "Historical films sit between research and drama. Production design and casting carry the period, while the script decides how much to compress. Treat on-screen timelines as interpretation, not record.",
 "Horror": "Horror runs on restraint and release: what the camera withholds, how long a shot holds, and when the sound drops out. Subgenres shift constantly, from haunted-house slow burns to splatter comedy.",
 "Music": "Music films live on performance. Concert footage, biopics and musicals all depend on how honestly the camera captures a voice, and on whether the soundtrack earns its place in the story.",
 "Mystery": "Mystery rewards attention. Clues, alibis and unreliable narrators are the toolkit, and the genre's pleasure is the gap between what the audience knows and what the detective can prove.",
 "Romance": "Romance depends on chemistry and structure: two people, an obstacle, and a reason to keep watching after the meet-cute. The genre's range runs from sweeping period drama to small, sharp modern stories.",
 "Science Fiction": "Science fiction uses speculative premises to test ideas about technology, identity and power. The best entries keep the concept legible and let character decisions, not exposition, carry the argument.",
 "Thriller": "Thrillers are engineered for tension: a clock, a threat and someone with too little information. Pacing does most of the work, which is why editing and sound design matter as much as the plot.",
 "War": "War films carry a documentary weight even when fictional. The strongest avoid triumphalism, focus on the people inside the machinery, and are honest about how little control individuals have.",
 "Western": "The western is a study of frontier rules: land, law, violence and who gets to start over. Modern entries often invert the classics, but the genre still trades on wide landscapes and hard choices.",
 "TV Movie": "TV movies cover a wide quality range, from network thrillers to prestige limited productions. They are worth checking for cast, running time and whether the story was built for a single sitting.",
}

def _cat_movies(g):
    """Movies in the library that truly belong to this genre."""
    return [m for m in D["movies"] if g["name"] in m.get("genres", [])]

def _cat_extra(g, limit=12):
    """Popular titles in the same genre from the TMDB shortlist, excluding anything already in the library
    and anything that is not actually tagged with this genre."""
    mine_ids = {m["tmdb_id"] for m in D["movies"]}
    out = []
    for x in g.get("movies", []):
        gids = x.get("genre_ids") or x.get("genres")
        if gids is not None and g["id"] not in gids: continue
        if x.get("id") in mine_ids or x.get("tmdb_id") in mine_ids: continue
        out.append(x)
    return out[:limit]

def _cat_intro(g, mine):
    n = g["name"]; low = n.lower()
    ed = GENRE_EDIT.get(n, {})
    top = sorted(mine, key=lambda m: -(m.get("rating") or 0))
    if mine:
        t3 = join_and([m["title"] for m in top[:3]])
        avg = round(sum((m.get("rating") or 0) for m in mine) / len(mine), 1)
        topline = f"Our {len(mine)} {low} {'guide' if len(mine)==1 else 'guides'} average {avg}/10, led by {t3}"
    else:
        topline = ""
    return ed.get("intro", "").replace("{top}", topline).replace(". .", ".").strip() or f"{n} guides will appear here once they are researched."

def weighted(m, C=6.8, mv=400):
    v = m.get("votes") or 0; r = m.get("rating") or 0
    return (v / (v + mv)) * r + (mv / (v + mv)) * C

def is_rated(m):
    return (m.get("votes") or 0) >= 30 and (m.get("rating") or 0) > 0 and (days_until(m.get("release_date") or "") or -1) <= 0

def page_category(g):
    path = f"category/{g['slug']}/index.html"
    mine = sorted(_cat_movies(g), key=lambda m: (-(1 if is_rated(m) else 0), -weighted(m)))
    extra = _cat_extra(g)
    mine_cards = "".join(card(m, f"{BASE}{movie_path(m)}") for m in mine)
    other_cards = "".join(card(x) for x in extra)
    title = f"{g['name']} Movies: Cast, Ratings & Where to Watch"
    if len(title) > 58: title = f"{g['name']} Movies: Ratings & Where to Watch"
    n_ = len(mine)
    desc = trim(f"{g['name']} movies with cast, ratings and where to watch. " + (f"{n_} guide{'s' if n_ != 1 else ''} including {join_and([m['title'] for m in mine[:3]])}." if mine else "Guides are coming soon."), 158)
    intro = _cat_intro(g, mine)
    note = GENRE_NOTES.get(g["name"], "")
    best = [x for x in mine if (x.get("votes") or 0) >= 300 and is_rated(x)][:3]
    best_line = (join_and([x["title"] for x in best]) + " are the highest rated " + g["name"].lower() + " guides here.") if best else "No guide is published for this genre yet."
    ed = GENRE_EDIT.get(g["name"], {})
    gfaq = [(f"What are the best {g['name'].lower()} movies here?", best_line + (" Ratings are TMDB user scores and change over time." if best else ""))] + list(ed.get("faq", []))
    if mine:
        gfaq.append((f"Where can I watch {g['name'].lower()} movies online?", "Open a film guide and see Where to watch. Streaming, rental and purchase options are listed by region."))
    faq_html = "".join(f'<details class="faq__item"><summary><h3>{e(q)}</h3></summary><p>{e(a)}</p></details>' for q, a in gfaq)
    ld = [
      crumb_ld([("Home", "/"), ("Categories", "/categories/"), (g["name"], f"/category/{g['slug']}/")]),
      {"@context": "https://schema.org", "@type": "CollectionPage", "name": f"{g['name']} Movies", "url": f"{BASE}/category/{g['slug']}/",
       "description": desc, "mainEntity": {"@type": "ItemList", "itemListElement": [
           {"@type": "ListItem", "position": i + 1, "name": x["title"], "url": BASE + movie_path(x)} for i, x in enumerate(mine)]}},
      {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
          {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in gfaq]},
    ]
    og = poster((mine[0].get("poster") if mine else g["cover"]), "w780")
    h = head(f"{title} | {BRAND}", desc, f"category/{g['slug']}/", og_image=og, jsonld=ld, noindex=(n_ == 0))
    picks = (f'<section class="section"><div class="section__head"><div><p class="kicker">Full guides</p>'
             f'<h2 class="section__title">{e(g["name"])} films with full guides</h2></div></div>'
             f'<div class="grid">{mine_cards}</div></section>') if mine else ""
    more = (f'<section class="section"><div class="section__head"><div><p class="kicker">Also popular</p><h2 class="section__title">More {e(g["name"].lower())} titles on TMDB</h2></div></div><div class="grid">{other_cards}</div></section>') if extra else ""
    lens_ = ed.get("lens", ""); starter_ = ed.get("starter", "")
    prose = (f'<section class="section section--narrow"><div class="section__head"><div><p class="kicker">How to choose</p><h2 class="section__title">What to look for in {e(g["name"].lower())} films</h2></div></div>'
             f'<div class="prose"><p>{e(note)}</p>' + (f'<p>{e(lens_)}</p>' if lens_ else '') + (f'<p><strong>Where to start:</strong> {e(starter_)}</p>' if starter_ else '') + '</div>')
    body = (h + header("/categories/") + '<main id="main"><div class="wrap">'
      + crumbs([("Home", "/"), ("Categories", "/categories/"), (g["name"], None)]) + '</div>'
      + f'<section class="page-head"><div class="wrap"><p class="kicker">Category</p><h1 class="page-title">{e(g["name"])} movies</h1><p class="page-lede">{e(intro)}</p></div></section>'
      + picks + more + prose
      + f'<div class="panel" style="margin-top:16px"><h2 class="panel__title">Frequently asked questions</h2><div class="faq">{faq_html}</div></div></section></main>' + footer())
    write(path, body)
    if n_ == 0: NOINDEX_PATHS.add(path)

PER_PAGE = 36

def pager(base_path, page, pages):
    if pages <= 1: return ""
    def u(p): return f"{BASE}/{base_path}/" if p == 1 else f"{BASE}/{base_path}/page/{p}/"
    items = []
    if page > 1: items.append(f'<a class="pager__a" rel="prev" href="{u(page-1)}">&#8592; Previous</a>')
    for p in range(1, pages + 1):
        items.append(f'<span class="pager__a is-current" aria-current="page">{p}</span>' if p == page else f'<a class="pager__a" href="{u(p)}">{p}</a>')
    if page < pages: items.append(f'<a class="pager__a" rel="next" href="{u(page+1)}">Next &#8594;</a>')
    return f'<nav class="pager" aria-label="Pagination">{"".join(items)}</nav>'

def page_movies_hub():
    ranked = sorted(D["movies"], key=lambda x: (-(1 if is_rated(x) else 0), -weighted(x)))
    pages = max(1, -(-len(ranked) // PER_PAGE))
    chips = "".join(f'<a class="chip" href="{BASE}/category/{x["slug"]}/">{e(x["name"])}</a>' for x in GEN)
    for pg in range(1, pages + 1):
        chunk = ranked[(pg-1)*PER_PAGE: pg*PER_PAGE]
        path = "movies/index.html" if pg == 1 else f"movies/page/{pg}/index.html"
        cards = "".join(card(m, f"{BASE}{movie_path(m)}") for m in chunk)
        ld = [crumb_ld([("Home", "/"), ("Movies", "/movies/")] + ([(f"Page {pg}", f"/movies/page/{pg}/")] if pg > 1 else [])),
              {"@context": "https://schema.org", "@type": "CollectionPage", "name": "All movies" + (f" - page {pg}" if pg > 1 else ""),
               "url": f"{BASE}/movies/" if pg == 1 else f"{BASE}/movies/page/{pg}/",
               "mainEntity": {"@type": "ItemList", "itemListElement": [
                   {"@type": "ListItem", "position": (pg-1)*PER_PAGE + i + 1, "name": m["title"], "url": f"{BASE}{movie_path(m)}"} for i, m in enumerate(chunk)]}}]
        ttl = "All Movies: Guides, Cast & Where to Watch" if pg == 1 else f"All Movies, Page {pg}: Guides, Cast & Where to Watch"
        h = head(ttl + f" | {BRAND}", "Browse every movie we cover: cast, runtime, release details and where to watch by region." + (f" Page {pg} of {pages}." if pg > 1 else ""),
                 path, jsonld=ld, prev_url=(None if pg == 1 else (f"{BASE}/movies/" if pg == 2 else f"{BASE}/movies/page/{pg-1}/")),
                 next_url=(None if pg == pages else f"{BASE}/movies/page/{pg+1}/"))
        ups_html = ""
        if pg == 1:
            _rows = ""
            for _m in UPCOMING()[:12]:
                _rl = release_label(_m); _t = _pd(_m.get("release_date")) or (0,1,1)
                _mon = MON[_t[1]-1] if 1 <= _t[1] <= 12 else ""
                _meta = join_and((_m.get("genres") or ["Film"])[:2])
                _rows += ('<a class="cal__row" href="%s%s"><span class="cal__date"><b>%s</b><i>%s</i></span>'
                          '<span class="cal__body"><strong>%s</strong><span>%s &middot; %s</span></span>'
                          '<span class="cal__when">%s</span></a>') % (BASE, movie_path(_m), _t[2], e(_mon), e(_m["title"]), e(_meta), e(_rl["status"]), e(_rl["note"]))
            if _rows:
                ups_html = (f'<section class="section" id="upcoming"><div class="section__head"><div><p class="kicker">Coming up</p>'
                            f'<h2 class="section__title">Upcoming releases</h2><p class="section__lede">Announced US dates for the next six months. '
                            f'Schedules move, so check the film page for the latest listed date.</p></div></div><div class="panel cal">{_rows}</div></section>')
        extra = ""
        if pg == 1:
            extra = (f'<section class="section section--narrow"><div class="section__head"><div><p class="kicker">How to use this list</p><h2 class="section__title">Ranked by weighted audience rating</h2></div></div>'
                     f'<div class="prose"><p>Films are ranked by a weighted TMDB score, so a title with thousands of votes outranks one with a handful of perfect ratings. Films that have not been released, or have too few votes, are listed after the rated titles.</p></div></section>')
        body = f"""{h}{header("/movies/")}<main id="main">
<div class="wrap">{crumbs([("Home", "/"), ("Movies", "/movies/" if pg > 1 else None)] + ([(f"Page {pg}", None)] if pg > 1 else []))}</div>
<section class="page-head"><div class="wrap"><p class="kicker">Library</p><h1 class="page-title">All movies{f" (page {pg})" if pg > 1 else ""}</h1>
<p class="page-lede">{len(ranked)} films in the MovieState guide library. Each page covers the story, the cast, technical details and where the film is streaming.</p></div></section>
{ups_html}<section class="section"><div class="grid">{cards}</div>{pager("movies", pg, pages)}</section>
{extra}<section class="section section--narrow"><div class="panel"><h2 class="panel__title">Browse by category</h2><div class="chips">{chips}</div></div></section>
</main>{footer()}"""
        write(path, body)

def _cat_counts():
    return {g["slug"]: sum(1 for m in D["movies"] if g["name"] in m.get("genres", [])) for g in GEN}
CAT_COUNT = _cat_counts()
def page_categories_hub():
    path = "categories/index.html"
    tiles = "".join(f'''<a class="cat" href="{BASE}/category/{g['slug']}/">
<img src="{poster(g['cover'], 'w342')}" alt="{e(g['name'])} movies" width="342" height="513" loading="lazy" decoding="async">
<span class="cat__veil" aria-hidden="true"></span><span class="cat__label"><span class="cat__count">{CAT_COUNT.get(g["slug"],0)} {"guide" if CAT_COUNT.get(g["slug"],0)==1 else "guides"}</span>{e(g['name'])}</span></a>''' for g in GEN if CAT_COUNT.get(g["slug"], 0) > 0)
    ld = [crumb_ld([("Home", "/"), ("Categories", "/categories/")]),
          {"@context": "https://schema.org", "@type": "CollectionPage", "name": "Movie categories", "url": f"{BASE}/categories/"}]
    h = head(f"Movie Categories — Browse by Genre | {BRAND}",
             "Browse movies by genre: action, horror, sci-fi, drama, comedy and more, with ratings and where to watch.", path, jsonld=ld)
    body = f"""{h}{header("/categories/")}<main id="main">
<div class="wrap">{crumbs([("Home", "/"), ("Categories", None)])}</div>
<section class="page-head"><div class="wrap"><p class="kicker">Browse</p><h1 class="page-title">Movie categories</h1>
<p class="page-lede">Genres are a shortcut, not a rule. Pick the mood you are in, and we will show you the films people are watching in that lane right now.</p></div></section>
<section class="section"><div class="cat-grid">{tiles}</div></section>
<section class="section section--narrow"><div class="section__head"><div><p class="kicker">How to use categories</p><h2 class="section__title">Pick by mood, then by evidence</h2></div></div>
<div class="prose"><p>A genre tells you the shape of the evening, not the quality of the film. Two horror movies can be nothing alike: one is a slow burn built on sound, another is a crowd-pleaser with jump scares every ten minutes. That is why every category page mixes a shortlist of films we cover in depth with a wider row of titles that are popular right now, so you can compare rather than guess.</p>
<p>Each category page also answers the practical question most lists skip: where the film is actually available. Availability is regional, so our guides separate streaming, rental and purchase for the United States, United Kingdom, Canada, Australia, India and Bangladesh instead of offering a single link that may not work in your country.</p>
<p>If you already know the title, the fastest route is the movie index, where every guide is listed with its rating, runtime and cast. If you are browsing, start with the genre closest to your mood and work outward.</p></div>
<div class="panel" style="margin-top:16px"><h2 class="panel__title">Common questions</h2><div class="faq">
<details class="faq__item"><summary><h3>How are categories built?</h3></summary><p>Titles are grouped by their official genre metadata, then ordered by current popularity and search demand. A film can sit in more than one category, which is normal for hybrids like horror-thrillers or sci-fi action.</p></details>
<details class="faq__item"><summary><h3>Why do some categories have fewer guides?</h3></summary><p>We publish guides in order of demand. Categories with more search interest get deeper coverage first, and the rest fill in as new pages go live.</p></details>
<details class="faq__item"><summary><h3>Can I watch every film listed here?</h3></summary><p>Every title links to a page that lists the options reported for your region. Some films are between licenses, so availability can change week to week.</p></details>
</div></div></section>
</main>{footer()}"""
    write(path, body)

def page_people_hub():
    pool = sorted([p for p in PPL if len([x for x in p["movies"] if x["id"] in MOV]) >= 2], key=lambda p: p["name"].lower())
    pages = max(1, -(-len(pool) // 48))
    for pg in range(1, pages + 1):
        chunk = pool[(pg-1)*48: pg*48]
        path = "people/index.html" if pg == 1 else f"people/page/{pg}/index.html"
        cards = "".join(person_card(p, f"{BASE}{person_path(p)}") for p in chunk)
        ld = [crumb_ld([("Home", "/"), ("People", "/people/")] + ([(f"Page {pg}", f"/people/page/{pg}/")] if pg > 1 else [])),
              {"@context": "https://schema.org", "@type": "CollectionPage", "name": "Actors and directors" + (f" - page {pg}" if pg > 1 else ""), "url": f"{BASE}/people/" if pg == 1 else f"{BASE}/people/page/{pg}/"}]
        h = head("Actors & Directors: Profiles and Credits" + (f", Page {pg}" if pg > 1 else "") + f" | {BRAND}",
                 "Profiles of the actors and directors behind the films we cover, with credits and quick facts." + (f" Page {pg} of {pages}." if pg > 1 else ""), path, jsonld=ld,
                 prev_url=(None if pg == 1 else (f"{BASE}/people/" if pg == 2 else f"{BASE}/people/page/{pg-1}/")),
                 next_url=(None if pg == pages else f"{BASE}/people/page/{pg+1}/"))
        body = f"""{h}{header("/people/")}<main id="main">
<div class="wrap">{crumbs([("Home", "/"), ("People", "/people/" if pg > 1 else None)] + ([(f"Page {pg}", None)] if pg > 1 else []))}</div>
<section class="page-head"><div class="wrap"><p class="kicker">People</p><h1 class="page-title">Actors &amp; directors{f" (page {pg})" if pg > 1 else ""}</h1>
<p class="page-lede">{len(pool)} actors and filmmakers with two or more credits in our library, listed A to Z. Each profile links to their films and where to watch them.</p></div></section>
<section class="section"><div class="grid grid--people">{cards}</div>{pager("people", pg, pages)}</section>
</main>{footer()}"""
        write(path, body)

def page_person(p):
    path = f"person/{p['id']}-{slug(p['name'])}/index.html"
    role = ROLE_OF(p)
    bio = (p.get("biography") or "").strip()
    films_rows = [(MOV[x["id"]], x.get("character") or "") for x in p["movies"] if x["id"] in MOV]
    films = "".join(card(MOV[x["id"]], f"{BASE}{movie_path(MOV[x['id']])}") if x["id"] in MOV else
                    f'<div class="card card--static"><div class="card__art"><img src="{poster(x.get("poster"), "w342")}" alt="{e(x["title"])}" width="342" height="513" loading="lazy"></div><div class="card__body"><h3 class="card__title">{e(x["title"])}</h3><p class="card__sub">{e(x.get("year"))}</p></div></div>'
                    for x in p["movies"][:16])
    facts = [(k, v) for k, v in [("Known for", p.get("dept")), ("Born", p.get("birthday")), ("Place of birth", p.get("place"))] if v and str(v).strip()]
    facts_html = "".join(f'<div class="fact"><dt>{e(k)}</dt><dd>{e(v)}</dd></div>' for k, v in facts)
    lead, rest = split_bio(bio, 360)
    if not lead:
        lead = f"{p['name']} works in film as {article(role)} {role.lower()}. This page tracks every title we cover in which they appear, with cast, runtime and availability for each film."
    known = sorted(films_rows, key=lambda z: -(z[0].get("votes") or 0))[:3]
    known_html = "".join(f'<li><a href="{BASE}{movie_path(m)}">{e(m["title"])} ({m["year"]})</a> — {e(m.get("rating") or "—")}/10 · {e(rtime(m.get("runtime")))}</li>' for m, _ in known)
    count = len(films_rows)
    gfaq = [
      (f"What is {p['name']} known for?", (f"{p['name']} is credited on {count} film{'s' if count != 1 else ''} covered by MovieState" + (f", including {known[0][0]['title']} ({known[0][0]['year']})." if known else "."))),
      (f"Which films has {p['name']} appeared in?", ("The credits grid on this page lists every title we cover, with the character played where the film's credits confirm it." if role in ("Actor",) else "The credits grid on this page lists every title we cover that this person directed.")),
      (f"Where can I watch {p['name']}'s films?", "Open any film on MovieState to see streaming, rental and purchase options reported for your region."),
    ]
    faq_html = "".join(f'<details class="faq__item"><summary><h3>{e(q)}</h3></summary><p>{e(a)}</p></details>' for q, a in gfaq)
    sents = [x for x in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])", clean_bio(bio)) if x.strip()]
    core = " ".join(sents[:2]) if sents else lead
    if not core.lower().startswith(p["name"].split()[0].lower()):
        core = p["name"] + ". " + core
    if len(core) < 95:
        core += f" See every {role.lower()} credit and the films they appear in."
    desc = trim(core, 156)
    ld = [crumb_ld([("Home", "/"), ("People", "/people/"), (p["name"], person_path(p))]),
          {"@context": "https://schema.org", "@type": "Person", "name": p["name"], "url": f"{BASE}/{path}",
           "image": poster(p.get("profile"), "w500"), "description": trim(lead, 300), "jobTitle": role, **({"birthDate": p["birthday"]} if p.get("birthday") else {}), **({"birthPlace": p["place"]} if p.get("place") else {}), "sameAs": ([f"https://www.themoviedb.org/person/{p['id']}"])},
          {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
              {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in gfaq]}]
    rich = len(films_rows) >= 2
    h = head(f"{p['name']}: Movies, Credits & Biography", desc, path, og_image=poster(p.get("profile"), "w500"), jsonld=ld, og_type="profile", noindex=not rich)
    body = (h + header("/people/") + '<main id="main"><div class="wrap">'
      + crumbs([("Home", "/"), ("People", "/people/"), (p["name"], None)]) + '</div>'
      + f'<section class="page-head page-head--person"><div class="wrap wrap--person"><img class="person-lg" src="{poster(p.get("profile"),"w342")}" alt="{e(p["name"])}" width="342" height="513" fetchpriority="high" decoding="async">'
      + f'<div><p class="kicker">{e(role)}</p><h1 class="page-title">{e(p["name"])}</h1><p class="page-lede">{e(lead)}</p>'
      + (f'<dl class="facts facts--inline">{facts_html}</dl>' if facts_html else '') + '</div></div></section>'
      + (f'<section class="section section--narrow"><div class="section__head"><div><p class="kicker">Biography</p><h2 class="section__title">About {e(p["name"])}</h2></div></div><div class="prose"><p>{e(rest)}</p></div></section>' if rest else '')
      + (f'<section class="section section--narrow"><div class="panel"><h2 class="panel__title">Known for</h2><ul class="prose prose--tight">{known_html}</ul></div></section>' if known_html else '')
      + f'<section class="section"><div class="section__head"><div><p class="kicker">Credits</p><h2 class="section__title">Films with {e(p["name"])}</h2></div></div><div class="grid">{films}</div></section>'
      + f'<section class="section section--narrow"><div class="panel"><h2 class="panel__title">Frequently asked questions</h2><div class="faq">{faq_html}</div></div></section>'
      + '</main>' + footer())
    write(path, body)
    if not rich: NOINDEX_PATHS.add(path)

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
    static_page("about/index.html", "About MovieState — Our Editorial Standards", "Who runs MovieState, how we research movies, and the standards we follow before publishing a page.", "About", "About MovieState", [
      ("What this site is", [
        "MovieState is an independent movie guide. We publish plain-English pages about films: what the story is, who made it, how long it runs, when it came out, and where it can be watched right now.",
        "We are not a studio, a streaming service or a review aggregator. We are a small independent project that turns structured film data into a readable page and adds editorial notes for the films we cover most closely.",
      ]),
      ("How we research", [
        "Core metadata (titles, posters, backdrops, cast and crew, runtime, release dates, age ratings and streaming availability) comes from TMDB and is refreshed when we rebuild the site. Most film pages are generated from that data, so each one shows its last update date. Editorial notes on individual films are marked as auto-generated unless a person has reviewed and rewritten them.",
        "When a field is missing from the data, we leave it out or say it is unavailable. We do not invent release dates, ratings, availability or 'official' claims to fill space. Streaming availability reflects what TMDB reports for each country and can be out of date, so confirm it with the provider.",
      ]),
      ("What we do not do", [
        "We do not host, stream or store movie files on this site. We do not use pop-ups or forced redirects. We do not make 'free full movie' promises, because those claims are usually false and frequently harmful.",
        "Legal options for each film are listed first, by country. We also link to a companion library site, which is a separate service. Those links are marked as sponsored, and you should check that service's terms and your local rules before using it.",
      ]),
      ("Editorial independence", [
        "No studio pays us to write a page, rank a film higher, or soften a description. If that ever changes, it will be disclosed on the page itself in plain language.",
      ]),
      ("Corrections", [
        "Films change: release dates slip, streamers lose rights, runtimes move. When a reader tells us something is out of date, we verify it and update the page. If you spot an error, report it through the contact options on our main site and we will look at it.",
      ]),
    ], "/about/")

def page_privacy():
    static_page("privacy-policy/index.html", "Privacy Policy — What We Collect and Why", "What MovieState does and does not collect when you browse our movie guides.", "Legal", "Privacy Policy", [
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
    static_page("terms/index.html", "Terms & Conditions", "The terms that apply when you use the MovieState movie guide: what the site covers, how linked streaming pages work, accuracy limits and your responsibilities.", "Legal", "Terms & Conditions", [
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
 ("What is MovieState?", "MovieState is an independent movie guide. Each page covers the story, cast, crew, runtime, ratings and release dates, plus where the film streams, rents or sells in major regions."),
 ("Is MovieState free to use?", "Yes. Every guide on this site is free to read, with no account and no paywall."),
 ("Do you host or stream movies?", "No. MovieState is an information guide. We never host, embed or stream video files and we do not link to unlicensed streaming services. Watch options point to official providers, or to a legitimate availability index such as JustWatch where you can compare official services."),
 ("How do I find where to watch a movie?", "Open a movie page and go to Where to watch. Availability is split into stream, rent and buy for the US, UK, Canada, Australia, India and Bangladesh. Confirm price and quality on the provider page."),
 ("Where does the movie data come from?", "Posters, backdrops, cast, crew and ratings come from TMDB. Availability comes from TMDB provider data, so it can lag behind a service's own catalogue."),
 ("Why can availability differ from what I see?", "Streaming rights are sold country by country and change over time. A film available in one region may not be licensed in another."),
 ("How often is the site updated?", "Pages are rebuilt from live data, so ratings, box office and watch options change as the sources change. Each movie page shows the date it was last rebuilt."),
 ("Can I request a movie page?", "Yes. Send us the title and we will add it to the research queue."),
 ("Do you offer free full-movie downloads?", "No. Claims like \"free full movie download\" are usually unsafe or illegal, and we do not publish them. We point to legal ways to watch."),
 ("How do you handle errors?", "Report the page and the detail that is wrong. We verify it against a primary source and correct the page."),
]
HOME_FAQ = FAQ_ITEMS[:6]

def page_faq():
    path = "faq/index.html"
    half = 6
    def block(pairs): return "".join(f'<details class="faq__item"><summary><h3>{e(q)}</h3></summary><p>{e(a)}</p></details>' for q, a in pairs)
    items_a = block(FAQ_ITEMS[:half]); items_b = block(FAQ_ITEMS[half:])
    ld = [crumb_ld([("Home", "/"), ("FAQ", "/faq/")]),
          {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
              {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ_ITEMS]}]
    h = head(f"FAQ — Common Questions About {BRAND}", "Answers about how MovieState works, where the data comes from, and how to watch the films we cover.", path, jsonld=ld)
    body = f"""{h}{header("/faq/")}<main id="main">
<div class="wrap">{crumbs([("Home", "/"), ("FAQ", None)])}</div>
<section class="page-head"><div class="wrap"><p class="kicker">Help</p><h1 class="page-title">Frequently asked questions</h1>
<p class="page-lede">Short, direct answers about the site, the data and the way we link to streaming pages.</p></div></section>
<section class="section section--narrow"><div class="section__head"><div><p class="kicker">The basics</p><h2 class="section__title">About the guide</h2></div></div><div class="panel panel--faq">{items_a}</div></section>
<section class="section section--narrow"><div class="section__head"><div><p class="kicker">Watching</p><h2 class="section__title">Availability and playback</h2></div></div><div class="panel panel--faq">{items_b}</div></section>
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
    if path.startswith("articles/"): return "0.7", "weekly"
    if path.startswith(("about/", "faq/")): return "0.5", "monthly"
    return "0.3", "yearly"

def write_sitemap():
    rows = []
    for p in sorted(set(PAGES) - NOINDEX_PATHS):
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
<link rel="stylesheet" href="{BASE}/assets/style.css?v={CSSVER}"><meta name="theme-color" content="#FFFFFF"></head>
<body>{header()}<main id="main" class="section section--narrow"><div class="panel">
<p class="kicker">404</p><h1 class="page-title">This page slipped out of the frame</h1>
<p>The page you wanted is not here. It may have moved, or it may not be published yet.</p>
<div class="hero__cta"><a class="btn btn--primary" href="{BASE}/">Back to home</a><a class="btn btn--ghost" href="{BASE}/movies/">Browse movies</a><a class="btn btn--ghost" href="{BASE}/categories/">Categories</a></div>
<h2 class="panel__title" style="margin-top:22px">Popular right now</h2><ul class="prose prose--tight">{"".join(f'<li><a href="{BASE}{movie_path(x)}">{e(x["title"])} ({x["year"]})</a></li>' for x in sorted(D["movies"], key=lambda z: -(z.get("votes") or 0))[:6])}</ul>
</div></main>{footer()}"""
    write_raw("404.html", body)


def page_movie_flagship(m):
    t, y = m["title"], m["year"]
    path = movie_path(m).lstrip("/")
    d = m.get("director")
    dname = d["name"] if d else "the film's director"
    title = f"{t} ({y}): Cast & Where to Watch"
    desc = f"{t} ({y}): the full story, cast, director, runtime, ratings and box office, plus where to watch it online in HD."
    qs = [
        (f"Who directed {t}?", f"{t} was directed by {dname}."),
        (f"Who stars in {t}?", "The cast includes " + ", ".join(c["name"] for c in m.get("cast", [])[:5]) + "."),
        (f"How long is {t}?", f"{t} runs {rtime(m.get('runtime'))} ({m.get('runtime')} minutes)."),
        (f"When was {t} released?", f"{t} was released on {m.get('release_date')}."),
        (f"Is {t} suitable for children?", f"{t} carries a {m.get('certification', 'PG-13')} rating in the United States. Age ratings differ between countries, so check your local rating before watching with children."),
        (f"Where can I watch {t}?", f"Streaming rights for {t} change by country and platform. The MovieState page for {t} shows the current watch options and availability for your region."),
    ]
    faq_html = "".join(f'<details class="faq__item"><summary><h3>{e(q)}</h3></summary><p>{e(a)}</p></details>' for q, a in qs)

    def ccard(c):
        p = PPL_BY_ID.get(c["id"])
        inner = f'<img src="{poster(c.get("profile"), "w185")}" alt="{e(c["name"])}" width="185" height="278" loading="lazy" decoding="async"><span class="cast-card__name">{e(c["name"])}</span><span class="cast-card__role">{e(c.get("character") or "Cast")}</span>'
        return f'<a class="cast-card" href="{BASE}{person_path(p)}">{inner}</a>' if p else f'<div class="cast-card">{inner}</div>'
    cast_html = "".join(ccard(c) for c in m.get("cast", [])[:8])

    dp = PPL_BY_ID.get(d["id"]) if d else None
    dlink = f"{BASE}{person_path(dp)}" if dp else None
    dphoto = poster(d.get("profile"), "w185") if d else ""
    dbio = (dp or {}).get("biography", "")
    dbio = (dbio[:260].rsplit(". ", 1)[0] + ".") if len(dbio) > 260 else dbio
    dinner = f'<img class="director-spot__photo" src="{dphoto}" alt="{e(dname)}" width="120" height="120" loading="lazy"><div><p class="kicker">Director</p><h3 class="director-spot__name">{e(dname)}</h3><p class="muted">{e(dbio) if dbio else "Biography details are being prepared."}</p></div>'
    dblock = f'<a class="director-spot panel" href="{dlink}">{dinner}</a>' if dlink else f'<div class="director-spot panel">{dinner}</div>'

    facts = [(k, v) for k, v in [
        ("Release date", m.get("release_date")), ("Runtime", rtime(m.get("runtime"))),
        ("Certification", m.get("certification")), ("Language", (m.get("language") or "").upper()),
        ("Status", m.get("status")), ("Genres", ", ".join(m.get("genres", []))),
        ("Director", dname), ("Writers", ", ".join(m.get("writers", []))),
        ("Studios", ", ".join(m.get("studios", []))),
        ("Budget", money(m.get("budget"))), ("Box office", money(m.get("revenue")))] if v]
    facts_html = "".join(f'<div class="fact"><dt>{e(k)}</dt><dd>{e(str(v))}</dd></div>' for k, v in facts)

    rel = [x for x in D["movies"] if x["tmdb_id"] != m["tmdb_id"] and set(x.get("genres", [])) & set(m.get("genres", []))][:8]
    rel_cards = "".join(card(x, f"{BASE}{movie_path(x)}") for x in rel)

    rated = m.get("rating") or 0
    votes = m.get("votes") or 0
    pct = int(round(rated * 10))
    ld = [
      {"@context": "https://schema.org", "@type": "Movie", "name": t, "url": f"{BASE}/{path}",
       "image": poster(m.get("poster"), "w500"), "description": m.get("overview", ""),
       "datePublished": m.get("release_date"), "genre": m.get("genres", []),
       "contentRating": m.get("certification"), "duration": f"PT{m['runtime']}M" if m.get("runtime") else None,
       "director": {"@type": "Person", "name": dname, "url": dlink} if d else None,
       "actor": [{"@type": "Person", "name": c["name"]} for c in (m.get("cast") or [])[:8]],
       "productionCompany": [{"@type": "Organization", "name": s} for s in m.get("studios", [])],
       "aggregateRating": {"@type": "AggregateRating", "ratingValue": round(rated, 1), "bestRating": 10, "ratingCount": max(votes, 1)} if rated else None},
      crumb_ld([("Home", "/"), ("Movies", "/movies/"), (t, movie_path(m))]),
      {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
          {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qs]},
    ]
    ld = [{k: v for k, v in b.items() if v is not None} for b in ld]
    h = head(title, desc[:155], path, og_image=backdrop(m.get("backdrop"), "w1280"), jsonld=ld)
    chips = "".join(f'<li class="chip">{e(x)}</li>' for x in [str(y), rtime(m.get("runtime")), m.get("certification") or "", (m.get("language") or "").upper(), m.get("status") or ""] if x)
    body = f"""{h}{header("/movies/")}<main id="main">
<div class="wrap">{crumbs(([("Home", "/"), ("Movies", "/movies/")] + ([((m.get("genres") or [""])[0], "/category/" + slug((m.get("genres") or [""])[0]) + "/")] if (m.get("genres") or [""])[0] else []) + [(t, None)]))}</div>
<section class="film">
<img class="film__bg" src="{backdrop(m.get('backdrop'), 'w1280')}" alt="" width="1280" height="720" fetchpriority="high" decoding="async">
<span class="film__veil" aria-hidden="true"></span>
<div class="film__inner wrap">
<div class="poster-xl"><img src="{poster(m.get('poster'), 'w500')}" alt="{e(t)} ({e(str(y))}) movie poster" width="500" height="750" fetchpriority="high" decoding="async"><span class="score-ring" style="--pct:{pct}"><b>{score(m)}</b><i>/10</i></span></div>
<div class="film__head">
<p class="kicker">{e(' · '.join(m.get('genres', [])))}</p>
<h1 class="film__title">{e(t)}</h1>
{f'<p class="film__tag">“{e(m["tagline"])}”</p>' if m.get("tagline") else ''}
<ul class="chips">{chips}</ul>
<div class="hero__cta"><a class="btn btn--primary" href="{watch_url(m)}" target="_blank" rel="noopener">Where to watch</a>
<a class="btn btn--ghost" href="#watch">Where to watch</a></div>
</div></div>
<div class="quickbar wrap"><div><span>Release</span><strong>{e(str(m.get('release_date','')).replace('-', '.'))}</strong></div><div><span>Runtime</span><strong>{e(rtime(m.get('runtime')))}</strong></div><div><span>Director</span><strong>{e(dname)}</strong></div><div><span>Rating</span><strong>{score(m)} / 10</strong></div></div>
</section>

<nav class="subnav" aria-label="On this page"><div class="wrap"><a href="#overview">Overview</a><a href="#cast">Cast</a><a href="#details">Details</a><a href="#reception">Reception</a><a href="#watch">Where to watch</a><a href="#faq">FAQ</a></div></nav>

<section class="section section--narrow" id="overview">
<div class="section__head"><div><p class="kicker">The story</p><h2 class="section__title">What is {e(t)} about?</h2></div></div>
<div class="prose prose--lead"><p>{e(m.get('overview',''))}</p>
<p>{e(t)} is the latest Spider-Man film to star Tom Holland, directed by {e(dname)} and produced by {e(', '.join(m.get('studios', [])[:2]))}. It runs {e(rtime(m.get('runtime')))} and carries a {e(m.get('certification','PG-13'))} rating in the United States. The screenplay is by {e(', '.join(m.get('writers', [])))}.</p></div>
<div class="callout"><p class="kicker">Why it matters</p><p>Audiences have rated {e(t)} <strong>{score(m)} out of 10</strong> on TMDB from {votes:,} ratings, and the film has taken roughly <strong>{e(money(m.get('revenue')))}</strong> worldwide against a <strong>{e(money(m.get('budget')))}</strong> production budget.</p></div>
</section>

<section class="section" id="cast">
<div class="section__head"><div><p class="kicker">Top billed</p><h2 class="section__title">Cast of {e(t)}</h2></div><a class="section__link" href="{BASE}/people/">All people</a></div>
<div class="rail"><div class="rail__track rail__track--cast">{cast_html or '<p class="muted">Cast details coming soon.</p>'}</div></div>
</section>

<section class="section section--split" id="details">
{dblock}
<div class="panel"><p class="kicker">Key details</p><h2 class="panel__title">Everything on record</h2><dl class="facts">{facts_html}</dl></div>
</section>

<section class="section section--narrow" id="reception">
<div class="reception panel">
<div class="reception__score"><span class="score-ring score-ring--lg" style="--pct:{pct}"><b>{score(m)}</b><i>/10</i></span><span class="reception__votes">{votes:,} TMDB ratings</span></div>
<div class="reception__body"><h2 class="panel__title">How audiences rate it</h2>
<div class="bar" role="img" aria-label="Average rating {score(m)} out of 10"><span style="width:{pct}%"></span></div>
<p class="muted">Scores are user ratings collected by TMDB and move up or down over time. Treat them as a snapshot, not a verdict.</p></div>
</div>
</section>

<section class="section section--split" id="watch">
<div class="panel"><p class="kicker">Watch</p><h2 class="panel__title">Where to watch {e(t)}</h2>
<ol class="steps"><li>Open the {e(t)} page on MovieState.</li><li>Check the watch options shown for your region.</li><li>Confirm price, quality and subtitles on the provider page before paying.</li></ol>
<a class="btn btn--primary" href="{watch_url(m)}" target="_blank" rel="{OUT_REL}">Check availability</a>
<p class="note">Availability differs by country and changes without notice. This page publishes information only and does not host or stream video.</p></div>
<div class="panel panel--faq" id="faq"><p class="kicker">FAQ</p><h2 class="panel__title">Questions about {e(t)}</h2>{faq_html}</div>
</section>

<section class="section"><div class="section__head"><div><p class="kicker">More like this</p><h2 class="section__title">Films similar to {e(t)}</h2></div><a class="section__link" href="{BASE}/movies/">All movies</a></div>
<div class="grid">{rel_cards or '<p class="muted">More recommendations coming soon.</p>'}</div></section>
</main>{footer()}"""
    write(path + "index.html", body)
    # thin by definition: not out yet or no audience data -> keep out of the index until it has some
    if (not is_rated(m)) and (m.get("votes") or 0) < 30 and (days_until(m.get("release_date") or "") or -1) > 30:
        NOINDEX_PATHS.add(path)


NO_LISTING_CLASSIC = {
 "BD": "TMDB lists no streaming, rental or purchase service for Bangladesh for this film. Check Apple TV, Google Play and the studio's official channels, and avoid unlicensed sites.",
 "IN": "TMDB lists no streaming, rental or purchase service for India for this film right now. Check JioHotstar, Prime Video and Apple TV, since catalogues change often.",
 "_": "TMDB lists no streaming, rental or purchase service for this region right now. Library titles move between catalogues often, so check the official provider pages.",
}
NO_LISTING = {
 "BD": "No streaming service has reported this title for Bangladesh yet. Your legal options are to check back after the official release window, look for a digital rental or purchase on Apple TV, Google Play or YouTube Movies if your account region supports it, or wait for the licensed streaming debut. Cinema releases are listed on the cinema chains' own sites.",
 "IN": "No streaming service has reported this title for India yet. Check JioHotstar, Prime Video and Apple TV for a rental or purchase as the release window opens, and look for the official digital release date before paying for any access.",
 "_": "No streaming, rental or purchase listing has been reported for this region yet. New titles usually reach digital stores a few weeks after cinemas, so check the official provider pages again later.",
}
CC = {"US":"United States","GB":"United Kingdom","CA":"Canada","AU":"Australia","IN":"India","BD":"Bangladesh"}
COUNTRY_NAME = {"US":"United States","GB":"United Kingdom","CA":"Canada","AU":"Australia","IN":"India","BD":"Bangladesh","DE":"Germany","FR":"France","ES":"Spain","IT":"Italy",
 "JP":"Japan","KR":"South Korea","BR":"Brazil","MX":"Mexico","AR":"Argentina","NL":"Netherlands","SE":"Sweden","DK":"Denmark","NO":"Norway","FI":"Finland","PL":"Poland","RU":"Russia",
 "TR":"Turkey","CN":"China","HK":"Hong Kong","TW":"Taiwan","SG":"Singapore","NZ":"New Zealand","IE":"Ireland","PT":"Portugal","BE":"Belgium","AT":"Austria","CH":"Switzerland",
 "CZ":"Czechia","EE":"Estonia","HU":"Hungary","GR":"Greece","IL":"Israel","ZA":"South Africa","AE":"United Arab Emirates","SA":"Saudi Arabia","EG":"Egypt","ID":"Indonesia",
 "TH":"Thailand","PH":"Philippines","MY":"Malaysia","VN":"Vietnam","PK":"Pakistan","LK":"Sri Lanka","NP":"Nepal","UA":"Ukraine","RO":"Romania","BG":"Bulgaria","HR":"Croatia",
 "RS":"Serbia","SK":"Slovakia","SI":"Slovenia","LT":"Lithuania","LV":"Latvia","IS":"Iceland","CL":"Chile","CO":"Colombia","PE":"Peru","VE":"Venezuela","UY":"Uruguay"}
PRIORITY = ["US","GB","IN","BD","CA","AU"]
def order_releases(rels):
    seen = {}
    for r in rels:
        if r["country"] not in seen: seen[r["country"]] = r
    pri = [seen[c] for c in PRIORITY if c in seen]
    rest = sorted([r for c, r in seen.items() if c not in PRIORITY], key=lambda r: COUNTRY_NAME.get(r["country"], r["country"]))
    return pri + rest
def cname(c): return COUNTRY_NAME.get(c, c)

def page_movie_v2(m):
    t, y = m["title"], m["year"]
    path = movie_path(m).lstrip("/")
    file_path = path + "index.html"
    d = m.get("director") or {}
    dn = d.get("name") or "not confirmed"
    prov = m.get("providers") or {}
    rels = m.get("releases") or []
    title = f"{t} ({y}): Cast, Ratings & Where to Watch"
    if len(title) > 66: title = f"{t} ({y}): Cast & Where to Watch"
    if len(title) > 66: title = f"{t} ({y}) Movie Guide"
    desc = f"{t} ({y}): story, cast, crew, ratings and release dates, plus where to stream, rent or buy it in the US, UK, India and Bangladesh."
    if len(desc) > 158: desc = f"{t} ({y}): cast, crew, ratings, release dates and where to stream, rent or buy it by region."
    cert_map = {r["country"]: r["cert"] for r in rels if r.get("cert")}
    _cm = [(k, cert_map[k]) for k in ["US","GB","IN","BD"] if k in cert_map]
    if not _cm: _cm = list(cert_map.items())[:2]
    cert_line = ", ".join(f"{c} in {cname(k)}" for k, c in _cm) or "not listed yet"

    # ---- watch rows ----
    rl = release_label(m)
    wrows = []
    if rl["phase"] == "upcoming":
        wrows.append(f'<div class="watch__row"><span class="watch__cc">US</span><div><p class="watch__line"><b>Scheduled</b>{e(t)} is dated for {e(rl["date"])} in the United States ({e(rl["note"])}). Streaming and rental listings appear after the cinema window, usually a few weeks to a few months later.</p></div></div>')
        wrows.append('<div class="watch__row"><span class="watch__cc">All</span><div><p class="watch__line"><b>Now</b>No legal stream, rental or purchase exists before the release date. Cinemas and the distributor\'s own site are the only official options until then.</p></div></div>')
    for cc in ["US","GB","CA","AU","IN","BD"]:
        if rl["phase"] == "upcoming" and cc == "US": continue
        v = prov.get(cc) or {}
        if not (v.get("flatrate") or v.get("free") or v.get("rent") or v.get("buy")):
            _old = (m.get("year") or 0) and (int(m.get("year")) <= 2024)
            _txt = NO_LISTING_CLASSIC.get(cc, NO_LISTING_CLASSIC["_"]) if _old else NO_LISTING.get(cc, NO_LISTING["_"])
            wrows.append(f'<div class="watch__row"><span class="watch__cc">{cc}</span><div><p class="watch__line"><b>{CC.get(cc, cc)}</b>{e(_txt)}</p></div></div>')
            continue
        lines = []
        if v.get("free"): lines.append(f'<p class="watch__line"><b>Free</b>{e(", ".join(v["free"][:4]))}</p>')
        if v.get("flatrate"): lines.append(f'<p class="watch__line"><b>Stream</b>{e(", ".join(v["flatrate"][:4]))}</p>')
        if v.get("rent"): lines.append(f'<p class="watch__line"><b>Rent</b>{e(", ".join(v["rent"][:4]))}</p>')
        if v.get("buy"): lines.append(f'<p class="watch__line"><b>Buy</b>{e(", ".join(v["buy"][:4]))}</p>')
        wrows.append(f'<div class="watch__row"><span class="watch__cc">{cc}</span><div>{"".join(lines)}</div></div>')
    watch_html = "".join(wrows)

    # ---- crew ----
    crew_items = [(("Director"), dn)]
    if m.get("writer_list"): crew_items.append(("Writers", ", ".join(m["writer_list"][:2])))
    if m.get("producer_list"): crew_items.append(("Producers", ", ".join(m["producer_list"][:2])))
    if m.get("composer"): crew_items.append(("Music", m["composer"]))
    if m.get("dop"): crew_items.append(("Cinematography", m["dop"]))
    if m.get("editor"): crew_items.append(("Editing", m["editor"]))
    crew_html = "".join(f'<div class="crew__item"><span class="crew__role">{e(r)}</span><span class="crew__name">{e(n)}</span></div>' for r, n in crew_items)

    cast_html = "".join(
        (f'<a class="cast-card" href="{BASE}{person_path(PPL_BY_ID[c["id"]])}"><img src="{poster(c.get("profile"),"w185")}" alt="{e(c["name"])}" width="185" height="278" loading="lazy" decoding="async"><span class="cast-card__name">{e(c["name"])}</span><span class="cast-card__role">{e(c.get("character") or "Cast")}</span></a>'
         if c["id"] in PPL_OK else
         f'<div class="cast-card"><img src="{poster(c.get("profile"),"w185")}" alt="{e(c["name"])}" width="185" height="278" loading="lazy" decoding="async"><span class="cast-card__name">{e(c["name"])}</span><span class="cast-card__role">{e(c.get("character") or "Cast")}</span></div>')
        for c in (m.get("cast") or [])[:12])

    rev_html = "".join(
        f'<article class="review"><div class="review__meta"><span>{e(r["author"] or "TMDB member")}</span><span>{("Score " + str(r["rating"]) + "/10") if r.get("rating") else "User review"}</span></div><p>{e(r["content"][:320].strip())}…</p></article>'
        for r in (m.get("reviews") or [])[:2]) or '<p class="note">No public user reviews have been posted for this title yet. Ratings below come from TMDB user scores.</p>'

    rel_rows = "".join(f'<tr><td>{e(cname(r["country"]))}</td><td>{e(fmt_date(r["date"]))}</td><td>{e(r["cert"] or "NR")}</td></tr>' for r in order_releases(rels)[:10]) or '<tr><td colspan="3">Release dates are not broken down by country for this title.</td></tr>'

    facts = [("Original title", m.get("title")), ("Status", m.get("status") or "—"),
             ("Release date", m.get("release_date") or "—"), ("Runtime", rtime(m.get("runtime"))),
             ("Certification", cert_line), ("Original language", (m.get("language") or "en").upper()),
             ("Spoken languages", ", ".join(m.get("spoken") or [])),
             ("Country", m.get("country")),
             ("Budget", money(m.get("budget")) or "Not disclosed"),
             ("Worldwide gross", money(m.get("revenue")) or "Not reported"),
             ("Studios", ", ".join(m.get("studios") or [])),
             ("Also known as", ", ".join((m.get("alt_titles") or [])[:3]))]
    facts_html = "".join(f"<tr><th>{e(k)}</th><td>{e(str(v))}</td></tr>" for k, v in facts if v and str(v).strip() not in ("—", "-"))

    fq = [
      (f"Who directed {t}?", f"{t} was directed by {dn}."),
      (f"Who is in the cast of {t}?", f"The main cast includes {', '.join(c['name'] for c in (m.get('cast') or [])[:5])}."),
      (f"How long is {t}?", f"{t} runs {rtime(m.get('runtime'))}."),
      (f"When was {t} released?", f"It was released on {m.get('release_date')}. Release dates vary by country — see the table above."),
      (f"What is {t} rated?", f"Certification depends on the country: {cert_line}. Always check your local rating before watching with family."),
      (f"Where can I watch {t} online?", f"Availability changes by region and by week. The table above lists the streaming, rental and purchase services reported for major markets. Check the provider page for today's price and quality."),
      (f"Can I watch {t} in HD or 4K?", f"Most digital stores offer {t} in HD, and newer releases are often available in 4K. Check the quality label on the provider's page before you pay."),
      (f"How much did {t} earn?", f"Reported worldwide gross is {money(m.get('revenue'))} against a budget of {money(m.get('budget'))}. Box office figures update over time.")]
    faq_html = "".join(f'<details class="faq__item"><summary><h3>{e(q)}</h3></summary><p>{e(a)}</p></details>' for q, a in fq)

    chips = "".join(f'<li class="chip">{e(x)}</li>' for x in [str(y), rtime(m.get("runtime")), (cert_map.get("US") or ""), (m.get("language") or "").upper(), m.get("status") or ""] if x)
    trailer = m.get("trailer")
    trailer_html = ""
    if trailer:
        trailer_html = (f'<div class="trailer"><img src="https://i.ytimg.com/vi/{trailer["key"]}/hqdefault.jpg" alt="Trailer thumbnail for {e(t)}" width="320" height="180" loading="lazy" decoding="async">'
                        f'<div><h3>Official trailer</h3><p class="note">{e(trailer["name"])} — opens on YouTube.</p>'
                        f'<a class="btn btn--ghost btn--sm" href="https://www.youtube.com/watch?v={trailer["key"]}" target="_blank" rel="noopener nofollow">Watch trailer</a></div></div>')

    def _rel_score(x):
        s = 0
        a = set(w for w in re.findall(r"[a-z0-9]+", m["title"].lower()) if len(w) > 3)
        c = set(w for w in re.findall(r"[a-z0-9]+", x["title"].lower()) if len(w) > 3)
        if a & c: s += 6
        if (m.get("director") or {}).get("id") and (m.get("director") or {}).get("id") == (x.get("director") or {}).get("id"): s += 5
        s += 2 * len(set(m.get("genres", [])) & set(x.get("genres", [])))
        if m.get("year") and x.get("year") and abs(int(m["year"]) - int(x["year"])) <= 10: s += 1
        if x["tmdb_id"] in (m.get("similar_ids") or []): s += 2
        if not is_rated(x): s -= 4
        return s
    rel_movies = sorted([x for x in D["movies"] if x["tmdb_id"] != m["tmdb_id"] and set(m.get("genres", [])) & set(x.get("genres", []))], key=lambda x: (-_rel_score(x), -(x.get("votes") or 0)))
    _mgs = set(m.get("genres", []))
    rel_movies = [x for x in rel_movies if (len(_mgs & set(x.get("genres", []))) >= min(2, len(_mgs)) and (x.get("votes") or 0) >= 200 and is_rated(x))][:8]
    if len(rel_movies) < 4:
        _fill = [x for x in D["movies"] if x["tmdb_id"] != m["tmdb_id"] and x not in rel_movies and (set(x.get("genres", [])) & _mgs) and (x.get("votes") or 0) >= 500 and is_rated(x)]
        _fill.sort(key=lambda x: (-len(_mgs & set(x.get("genres", []))), -(x.get("votes") or 0)))
        rel_movies = (rel_movies + _fill)[:6]
    _unused_rel = [MOV[i] for i in (m.get("similar_ids") or []) if i in MOV][:10]
    if not rel_movies:
        rel_movies = sorted([x for x in D["movies"] if x["tmdb_id"] != m["tmdb_id"] and set(x.get("genres", [])) & set(m.get("genres", []))], key=lambda x: -len(set(x.get("genres", [])) & set(m.get("genres", []))))[:10]

    ld_list = [{"@context":"https://schema.org","@type":"Movie","name":t,"url":BASE+movie_path(m),
      "description":m.get("overview",""),"image":poster(m.get("poster"),"w500"),
      "datePublished":m.get("release_date"),"duration":f"PT{int(m.get('runtime') or 0)}M",
      "genre":m.get("genres",[]),"contentRating":cert_map.get("US") or "",
      "productionCompany":[{"@type":"Organization","name":s} for s in (m.get("studios") or [])],
      "director":[{"@type":"Person","name":dn}],
      "actor":[{"@type":"Person","name":c["name"]} for c in (m.get("cast") or [])[:8]],
      "aggregateRating":{"@type":"AggregateRating","ratingValue":m.get("rating") or 0,"bestRating":10,"ratingCount":m.get("votes") or 0}}]
    if trailer: ld_list[0]["trailer"] = {"@type":"VideoObject","name":trailer["name"],"embedUrl":f"https://www.youtube.com/embed/{trailer['key']}"}
    ld_list.append(crumb_ld([("Home","/"),("Movies","/movies/")] + ([((m.get("genres") or [""])[0], "/category/" + slug((m.get("genres") or [""])[0]) + "/")] if (m.get("genres") or [""])[0] else []) + [(t,movie_path(m))]))
    ld_list.append({"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}} for q,a in fq]})
    page_head = head(title, desc, path, og_image=backdrop(m.get("backdrop"),"w1280"), jsonld=ld_list, og_type="video.movie", preload_img=backdrop(m.get("backdrop"),"w780"))

    H = []
    H.append(page_head + header())
    H.append('<main id="main"><div class="wrap crumbs-wrap">' + crumbs([("Home","/"),("Movies","/movies/")] + ([((m.get("genres") or [""])[0], "/category/" + slug((m.get("genres") or [""])[0]) + "/")] if (m.get("genres") or [""])[0] else []) + [(t,None)]) + '</div>')
    H.append(f'''<section class="film"><img class="film__bg" src="{backdrop(m.get("backdrop"),"w780")}" srcset="{backdrop(m.get("backdrop"),"w780")} 780w, {backdrop(m.get("backdrop"),"w1280")} 1280w" sizes="100vw" alt="" width="1280" height="720" fetchpriority="high" decoding="async"><span class="film__veil" aria-hidden="true"></span>
<div class="film__inner wrap"><div class="poster-xl"><img src="{poster(m.get("poster"),"w500")}" alt="{e(t)} poster" width="500" height="750" fetchpriority="high"><span class="score-ring" style="--pct:{int((m.get('rating') or 0)*10)}"><b>{m.get('rating') or '—'}</b><i>/10</i></span></div>
<div class="film__head"><p class="kicker">{e(" · ".join(m.get("genres",[])))}</p><h1 class="film__title">{e(t)}</h1>
<p class="film__tag">&ldquo;{e((m.get('tagline') or '').strip() or ('A ' + str(y) + ' release'))}&rdquo;</p>
<ul class="chips">{chips}</ul>
<div class="hero__cta"><a class="btn btn--primary" href="#watch">Where to watch</a><a class="btn btn--ghost" href="#cast">Cast &amp; crew</a></div></div></div>
<div class="quickbar wrap"><div><span>Release</span><strong>{e(m.get("release_date") or "—")}</strong></div><div><span>Director</span><strong>{e(dn)}</strong></div><div><span>Rating</span><strong>{m.get("rating") or "—"}/10 · {m.get("votes") or 0} votes</strong></div><div><span>Worldwide gross</span><strong>{e(money(m.get("revenue")) or "Not reported")}</strong></div></div></section>''')
    H.append('''<nav class="subnav" aria-label="Sections"><div class="wrap"><a href="#overview">Overview</a><a href="#editor-note">Should you watch</a><a href="#watch">Where to watch</a><a href="#cast">Cast</a><a href="#crew">Crew</a><a href="#reception">Reception</a><a href="#details">Details</a><a href="#releases">Release dates</a><a href="#faq">FAQ</a></div></nav>''')

    kws = "".join(f"<li>{e(k)}</li>" for k in (m.get("keywords") or [])[:10])
    tags_html = ('<ul class="tags">' + kws + "</ul>") if kws else ""
    H.append(f'''<section id="overview" class="section section--narrow"><div class="section__head"><div><p class="kicker">The story</p><h2 class="section__title">What {e(t)} is about</h2></div></div>
<div class="prose prose--lead">{("<p>" + e(m.get("overview","")) + "</p>") if m.get("overview") else ""}
<p>{e(t)} is {article((m.get("genres") or ["film"])[0])} {e(join_and([g_.lower() for g_ in m.get("genres",[])]))} film from {e(str(y))}, directed by {e(dn)}. It runs {e(rtime(m.get("runtime")))}{(" and is rated " + e(cert_map.get("US",""))+" in the US") if cert_map.get("US") else ""}{(". It was produced by " + e(join_and((m.get("studios") or [])[:3]))) if m.get("studios") else ""}{(", with production in " + e(m.get("country"))) if m.get("country") else ""}.</p>
<p>The main cast is led by {e(", ".join(c["name"] for c in (m.get("cast") or [])[:4]))}{(". The screenplay was written by " + e(", ".join(m["writer_list"][:2])) + ".") if m.get("writer_list") else "."} Reported worldwide gross stands at {e(money(m.get("revenue")) or "an amount that has not been disclosed")}.</p></div>
{tags_html}
<div class="callout"><strong>Why it matters:</strong> {e(t)} currently holds {m.get('rating') or '—'}/10 from {m.get('votes') or 0} TMDB user ratings and has taken {e(money(m.get('revenue')) or 'no reported gross')} worldwide against a {e(money(m.get('budget')) or 'undisclosed')} budget. Figures move as more ratings and box-office updates arrive.</div></section>''')
    _mg = set(m.get("genres", []))
    _sim = [x for x in D["movies"] if x["tmdb_id"] != m["tmdb_id"] and len(_mg & set(x.get("genres", []))) >= 2]
    _sim = sorted(_sim, key=lambda x: (-len(_mg & set(x.get("genres", []))), -(x.get("votes") or 0)))[:3]
    en = editor_note(m, cert_map.get("US", ""), [x["title"] for x in _sim])
    note_items = "".join(f"<p>{e(en[k])}</p>" for k in ("who","audience","themes","parental","similar") if en.get(k))
    H.append(f'''<section id="editor-note" class="section section--narrow"><div class="section__head"><div><p class="kicker">Editor&#8217;s note</p><h2 class="section__title">Should you watch {e(t)}?</h2></div></div><div class="panel prose">{note_items}<p class="note">Auto-generated from TMDB data (runtime, cast, ratings, keywords, certification). Last updated {TODAY}.</p></div></section>''')
    H.append(f'''<section id="watch" class="section"><div class="section__head"><div><p class="kicker">Availability</p><h2 class="section__title">Where to watch {e(t)}</h2></div></div>
<div class="cols"><div class="panel"><h3 class="panel__title">Streaming, rent or buy by region</h3><div class="watch">{watch_html}</div>
<p class="note">Listings come from TMDB provider data and change without notice. No price or quality is guaranteed here — confirm on the provider page before paying.</p></div>
<div class="panel"><h3 class="panel__title">How to watch in a few steps</h3><ol class="steps"><li>Find your country in the table and note which services list <strong>{e(t)}</strong>.</li><li>Pick streaming if it is included in a service you already pay for, otherwise compare rent and buy.</li><li>Check the quality label (HD or 4K) and the audio/subtitle languages on the provider page.</li><li>Still unavailable? Save the title and check again in a week — new deals appear often.</li></ol>
<a class="btn btn--ghost" href="{watch_url(m)}" target="_blank" rel="noopener">Compare all official providers for {e(t)}</a></div></div></section>''')

    H.append(f'''<section id="cast" class="section"><div class="section__head"><div><p class="kicker">Who is in it</p><h2 class="section__title">{e(t)} cast</h2></div></div><div class="rail"><div class="rail__track rail__track--cast">{cast_html}</div></div>
<p class="note">Character names follow the film's credits. Open a name to see that person's other work on MovieState.</p></section>''')
    H.append(f'''<section id="crew" class="section section--narrow"><div class="section__head"><div><p class="kicker">Behind the camera</p><h2 class="section__title">Direction and crew</h2></div></div><div class="crew">{crew_html}</div></section>''')
    H.append(f'''<section id="reception" class="section section--narrow"><div class="section__head"><div><p class="kicker">Audience reaction</p><h2 class="section__title">Ratings and reviews</h2></div></div>
<div class="panel"><div class="reception"><div class="reception__score"><span class="score-ring score-ring--lg" style="--pct:{int((m.get('rating') or 0)*10)}"><b>{m.get('rating') or '—'}</b><i>/10</i></span><span class="reception__votes">{m.get('votes') or 0} ratings</span></div>
<div><p>{e(t)} sits at <strong>{m.get('rating') or '—'} out of 10</strong> from {m.get('votes') or 0} user ratings. For context, the film's worldwide gross is {e(money(m.get('revenue')) or 'not yet reported')}.</p><div class="bar"><span style="width:{int((m.get('rating') or 0)*10)}%"></span></div><p class="note">Scores show TMDB user ratings at the time of publishing and shift as new votes arrive.</p></div></div>
<div class="reviews" style="margin-top:16px">{rev_html}</div></div></section>''')

    H.append(f'''<section id="details" class="section section--narrow"><div class="section__head"><div><p class="kicker">The facts</p><h2 class="section__title">{e(t)} key details</h2></div></div><div class="panel"><table class="tbl"><tbody>{facts_html}</tbody></table></div></section>''')
    H.append(f'''<section id="releases" class="section section--narrow"><div class="section__head"><div><p class="kicker">Release information</p><h2 class="section__title">Release dates by country</h2></div></div><div class="panel"><table class="tbl"><thead><tr><th>Country</th><th>Date</th><th>Cert</th></tr></thead><tbody>{rel_rows}</tbody></table>{trailer_html}</div></section>''')
    H.append(f'''<section id="faq" class="section section--narrow"><div class="section__head"><div><p class="kicker">Quick answers</p><h2 class="section__title">Frequently asked questions</h2></div></div><div class="faq">{faq_html}</div></section>''')
    dir_more = [x for x in D["movies"] if (m.get("director") and x.get("director") and x["director"]["id"] == m["director"]["id"] and x["tmdb_id"] != m["tmdb_id"])]
    if dir_more:
        H.append(f'''<section class="section"><div class="section__head"><div><p class="kicker">Director filmography</p><h2 class="section__title">More from {e(dn)}</h2></div></div><div class="rail"><div class="rail__track">{"".join(card(x, BASE + movie_path(x)) for x in dir_more)}</div></div></section>''')
    rel_cards = "".join(card(x, BASE + movie_path(x)) for x in rel_movies)
    H.append(f'''<section class="section"><div class="section__head"><div><p class="kicker">Keep watching</p><h2 class="section__title">More films like {e(t)}</h2></div><a class="section__link" href="{BASE}/movies/">All movies</a></div><div class="rail"><div class="rail__track">{rel_cards}</div></div></section>''')
    H.append(f'<section class="section section--narrow"><p class="note">Data sources: TMDB (titles, cast, crew, release dates, provider listings and user ratings). Availability and box office figures change over time; this page was last rebuilt on {date.today().isoformat()}. We publish information only; we do not host or stream video files.</p></section></main>')
    H.append(footer())
    write(file_path, "".join(H))


def page_home_v2():
    f = MOV[FEATURED_ID]
    trend = [MOV[i] for i in [1423191,1156593,1311031,1083381,1368166,1315985,1232493,1368316,1300118,1339713,1316311,1368337] if i in MOV]
    top = sorted([m for m in D["movies"] if (m.get("votes") or 0) > 400], key=lambda m: -(m.get("rating") or 0))[:6]
    editors = [MOV[i] for i in [969681, 1368337, 1423191] if i in MOV]
    scores = "".join(f'<li class="chip">{e(s)}</li>' for s in sorted({n for m in D["movies"] for cc in (m.get("providers") or {}).values() for k in ("flatrate","rent","buy") for n in (cc.get(k) or [])})[:10])
    H = [head("MovieState: Movie Guide, Cast, Ratings & Where to Watch",
              "Independent movie guide: what to watch now, full cast and crew, ratings, box office and exactly where to stream, rent or buy each film in HD.",
              "index.html", og_image=backdrop(f.get("backdrop"),"w1280"),
              jsonld=[
                {"@context":"https://schema.org","@type":"WebSite","name":BRAND,"url":BASE+"/","publisher":ORG,
                 "description":"Movie guides, cast and crew, release details and streaming availability for popular films."},
                {"@context":"https://schema.org",**ORG},
                {"@context":"https://schema.org","@type":"ItemList","name":"Trending movies","itemListElement":[{"@type":"ListItem","position":i+1,"url":BASE+movie_path(m),"name":m["title"]} for i,m in enumerate(trend)]},
                {"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}} for q,a in HOME_FAQ]}
              ])]
    H.append(header(""))
    H.append('<main id="main">')
    H.append(f'''<section class="hero hero--spot"><img class="hero__bg" src="{backdrop(f.get("backdrop"),"w1280")}" alt="" width="1280" height="720" fetchpriority="high" decoding="async">
<span class="hero__veil" aria-hidden="true"></span>
<div class="hero__inner wrap">
 <div class="hero__copy">
  <p class="kicker">Featured this week</p>
  <h1 class="hero__title">{e(f["title"])}<span>Where to watch, who is in it, and whether it is worth your night</span></h1>
  <p class="hero__lede">{e(f.get("tagline") or "")}</p>
  <ul class="chips"><li class="chip">{f["year"]}</li><li class="chip">{e(rtime(f.get("runtime")))}</li><li class="chip">{e(f.get("certification") or "")}</li><li class="chip">{e(f.get("genres",[""])[0])}</li></ul>
  <div class="hero__cta"><a class="btn btn--primary" href="{BASE}{movie_path(f)}">Open the full guide</a><a class="btn btn--ghost" href="{BASE}/movies/">Browse all movies</a></div>
 </div>
 <a class="hero__poster" href="{BASE}{movie_path(f)}" aria-label="{e(f["title"])} guide"><img src="{poster(f.get("poster"),"w500")}" alt="{e(f["title"])} poster" width="500" height="750" fetchpriority="high" decoding="async"><span class="score-ring" style="--pct:{int((f.get('rating') or 0)*10)}"><b>{f.get('rating')}</b><i>/10</i></span></a>
</div>
<div class="quickbar wrap"><div><span>Release</span><strong>{e(f.get("release_date") or "—")}</strong></div><div><span>Runtime</span><strong>{e(rtime(f.get("runtime")))}</strong></div><div><span>Director</span><strong>{e((f.get("director") or {}).get("name") or "—")}</strong></div><div><span>Worldwide</span><strong>{e(money(f.get("revenue")) or "—")}</strong></div></div>
</section>''')
    tick = "".join(f'<span>{e(m["title"])}</span><i aria-hidden="true">◆</i>' for m in trend)
    H.append(f'<div class="ticker" aria-hidden="true"><div class="ticker__track">{tick}{tick}</div></div>')
    H.append(f'''<section class="section">{section_head("Now trending","What everyone is watching this week",("All movies",BASE+"/movies/"))}
<div class="rail"><div class="rail__track">{"".join(card(m, movie_path(m)) for m in trend)}</div></div></section>''')
    ed = "".join(f'''<a class="ed-pick" href="{BASE}{movie_path(m)}"><img src="{backdrop(m.get("backdrop"),"w780")}" alt="{e(m["title"])} ({m["year"]}) backdrop" width="780" height="439" loading="lazy" decoding="async"><span class="ed-pick__veil" aria-hidden="true"></span><span class="ed-pick__body"><span class="ed-pick__meta">{m.get('rating')}/10 · {m['year']} · {e(m.get("genres",[""])[0])}</span><strong>{e(m["title"])}</strong><span class="ed-pick__line">{e((m.get("overview") or "")[:110])}…</span></span></a>''' for m in editors)
    H.append(f'''<section class="section"><div class="section__head"><div><p class="kicker">Editor picks</p><h2 class="section__title">Three films worth clearing an evening for</h2></div></div><div class="ed-grid">{ed}</div></section>''')
    rows = "".join(f'''<a class="rank" href="{BASE}{movie_path(m)}"><span class="rank__n">{i+1}</span><img src="{poster(m.get("poster"),"w185")}" alt="{e(m["title"])} poster" width="92" height="138" loading="lazy" decoding="async"><span class="rank__txt"><strong>{e(m["title"])}</strong><span>{m["year"]} · {e(", ".join(m.get("genres",[])[:2]))}</span></span><span class="rank__score">{m.get("rating")}</span></a>''' for i,m in enumerate(top))
    H.append(f'''<section class="section"><div class="section__head"><div><p class="kicker">Top rated</p><h2 class="section__title">Highest rated films in the library</h2></div><a class="section__link" href="{BASE}/movies/">See all</a></div><div class="ranklist">{rows}</div></section>''')
    cats = "".join(f'''<a class="cat" href="{BASE}/category/{g['slug']}/"><img src="{poster(g['cover'],'w342')}" alt="{e(g['name'])} movies" width="342" height="513" loading="lazy" decoding="async"><span class="cat__veil" aria-hidden="true"></span><span class="cat__label"><span class="cat__count">{CAT_COUNT.get(g["slug"],0)} {"guide" if CAT_COUNT.get(g["slug"],0)==1 else "guides"}</span>{e(g['name'])}</span></a>''' for g in GEN[:10])
    H.append(f'''<section class="section">{section_head("Browse","Categories built around how you actually choose films",("All categories",BASE+"/categories/"))}<div class="cat-grid">{cats}</div></section>''')
    H.append(f'''<section class="section"><div class="section__head"><div><p class="kicker">Where to watch</p><h2 class="section__title">How to find the right stream in under a minute</h2></div></div>
<div class="cols"><div class="panel"><ol class="steps"><li><strong>Open the film's guide.</strong> Every page lists streaming, rental and purchase options reported for the US, UK, Canada, Australia, India and Bangladesh.</li>
<li><strong>Check your region.</strong> Rights change per country, so the same film can be included with one service and pay-per-view on another.</li>
<li><strong>Confirm quality and price on the provider.</strong> We link out to the service; the final price, HD/4K availability and subtitle tracks are set there.</li></ol>
<a class="btn btn--primary" href="{BASE}/articles/">How we verify watch options</a></div>
<div class="panel"><h3 class="panel__title">Services we track</h3><ul class="chips">{scores}</ul><p class="note">Provider names are pulled from live availability data and change as licensing deals move. If a service is missing, the film is not listed there for the regions we check.</p></div></div></section>''')
    H.append(f'''<section class="section">{section_head("Cast & crew","The people behind the films",("All people",BASE+"/people/"))}<div class="rail"><div class="rail__track rail__track--people">{"".join(person_card(p, person_path(p)) for p in PPL[:14])}</div></div></section>''')
    faq_html = "".join(f'<details class="faq__item"><summary><h3>{e(q)}</h3></summary><p>{e(a)}</p></details>' for q,a in HOME_FAQ)
    H.append(f'''<section class="section"><div class="section__head"><div><p class="kicker">How we work</p><h2 class="section__title">Editorial standards, not scraped trivia</h2></div></div>
<div class="ed-grid"><div class="ed-card"><h3>Data with a source</h3><p>Titles, cast, crew, release dates and box office come from TMDB and are re-checked every time a page is rebuilt. When a figure is not reported, we say so instead of guessing.</p></div>
<div class="ed-card"><h3>Availability we verify</h3><p>Watch options are grouped by country because streaming rights are regional. Each film page names the services reported for that market and links you to the provider to confirm price.</p></div>
<div class="ed-card"><h3>Written for decisions</h3><p>Every guide answers three questions in order: what the film is, whether it fits your taste, and how to watch it. No autoplay, no pop-ups, no fake download buttons.</p></div></div></section>
<section id="faq" class="section section--narrow"><div class="section__head"><div><p class="kicker">FAQ</p><h2 class="section__title">Questions people ask before pressing play</h2></div></div><div class="panel panel--faq">{faq_html}</div></section>''')
    H.append('</main>' + footer())
    write("index.html", "".join(H))


def home3():
    import json as _j
    from datetime import date as _d
    allm = D["movies"]
    cnt = len(allm)
    ppl = len(PPL)
    gcnt = len(GEN)
    avg = round(sum(m.get("rating") or 0 for m in allm) / max(1, cnt), 1)
    slides = sorted([m for m in allm if m.get("backdrop") and (m.get("votes") or 0) > 300], key=lambda m: -(m.get("rating") or 0))[:5]
    top10 = sorted([m for m in allm if (m.get("votes") or 0) > 200], key=lambda m: -(m.get("rating") or 0))[:10]
    upc = sorted([m for m in allm if (m.get("release_date") or "") >= "2026-11-04"], key=lambda m: m.get("release_date") or "")[:6]
    trend = [MOV[i] for i in [1423191,1156593,1311031,1083381,1368166,1315985,1232493,1368316,1300118,1339713,1316311,1368337] if i in MOV]
    idx = [{"t": m["title"], "y": m["year"], "u": BASE + movie_path(m), "p": poster(m.get("poster"), "w92"), "g": " ".join(m.get("genres", []))} for m in allm]
    H = [head("MovieState: Movie Guide, Cast, Ratings & Where to Watch",
              "Independent movie guide: cast and crew, ratings, release dates and where to stream, rent or buy each film in the US, UK, Canada, India and Bangladesh.",
              "index.html", og_image=backdrop(slides[0].get("backdrop"), "w1280"), preload_img=backdrop(slides[0].get("backdrop"), "w780"),
              jsonld=[
                {"@context":"https://schema.org","@type":"WebSite","name":BRAND,"url":BASE+"/","publisher":ORG,
                 "potentialAction":{"@type":"SearchAction","target":BASE+"/movies/?q={search_term_string}","query-input":"required name=search_term_string"}},
                {"@context":"https://schema.org",**ORG},
                {"@context":"https://schema.org","@type":"ItemList","name":"Top rated movies","itemListElement":[{"@type":"ListItem","position":i+1,"url":BASE+movie_path(m),"name":m["title"]} for i,m in enumerate(top10)]},
                {"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}} for q,a in HOME_FAQ]}])]
    H.append(header(""))
    H.append('<main id="main"><h1 class="sr-only">MovieState: Your Independent Movie Guide</h1>')
    sl = ""
    for i, m in enumerate(slides):
        tag = "h2"
        chips = "".join(f'<li>{e(x)}</li>' for x in [str(m["year"]), rtime(m.get("runtime")), m.get("certification") or "NR", (m.get("genres") or ["Film"])[0]])
        sl += f'''<article class="slide{' is-on' if i==0 else ''}" data-i="{i}" {'inert' if i else ''}>
<img class="slide__bg" {'src="' + backdrop(m.get("backdrop"),"w780") + '" srcset="' + backdrop(m.get("backdrop"),"w780") + ' 780w, ' + backdrop(m.get("backdrop"),"w1280") + ' 1280w" fetchpriority="high"' if i==0 else 'data-src="' + backdrop(m.get("backdrop"),"w1280") + '"'} sizes="100vw" alt="{e(m["title"])} ({m["year"]}) backdrop" width="1280" height="720" decoding="async">
<span class="slide__veil" aria-hidden="true"></span>
<div class="slide__in wrap"><div class="slide__copy">
<p class="kicker"><span class="live" aria-hidden="true"></span>Popular right now</p>
<{tag} class="slide__title">{e(m["title"])}</{tag}>
<ul class="slide__chips">{chips}</ul>
<p class="slide__line">{e((m.get("overview") or "")[:140])}…</p>
<div class="slide__cta"><a class="btn btn--primary" href="{BASE}{movie_path(m)}">Where to watch</a><a class="btn btn--ghost" href="{BASE}{movie_path(m)}#cast">Cast &amp; details</a></div>
</div>
<a class="slide__poster" href="{BASE}{movie_path(m)}" aria-label="View {e(m["title"])} guide"><img {'src="' + poster(m.get("poster"),"w500") + '" fetchpriority="high"' if i==0 else 'data-src="' + poster(m.get("poster"),"w500") + '"'} alt="{e(m["title"])} poster" width="500" height="750" decoding="async"><span class="score-ring" style="--pct:{int((m.get('rating') or 0)*10)}"><b>{m.get('rating')}</b><i>/10</i></span></a>
</div></article>'''
    dots = "".join(f'<button class="hdot{" is-on" if i==0 else ""}" type="button" data-goto="{i}" aria-label="Show {e(m["title"])}"></button>' for i, m in enumerate(slides))
    H.append(f'''<section class="hero" id="hero" aria-roledescription="carousel" aria-label="Popular movies">
<div class="hero__stage">{sl}</div>
<div class="hero__bar wrap"><div class="hdots">{dots}</div><div class="hero__arrows"><button class="arrow" type="button" data-prev aria-label="Previous movie">&#8249;</button><button class="arrow" type="button" data-next aria-label="Next movie">&#8250;</button></div></div>
<div class="hero__progress" aria-hidden="true"><span></span></div>
</section>''')
    H.append(f'''<div class="quickbar wrap"><div><span>Film guides</span><strong data-count="{cnt}">{cnt}</strong></div><div><span>Genres</span><strong data-count="{gcnt}">{gcnt}</strong></div><div><span>Profiles</span><strong data-count="{ppl}">{ppl}</strong></div><div><span>Avg rating</span><strong>{avg}</strong></div></div>''')
    H.append(f'''<section class="searchbar wrap"><form class="search" role="search" autocomplete="off" id="sf"><label class="sr-only" for="q">Search movies</label><input id="q" name="q" type="search" placeholder="Search movies, actors, genres or years…" aria-describedby="qhelp"><button class="btn btn--primary" type="submit">Search</button><div class="search__res" id="qres" role="listbox" aria-label="Suggestions"></div><p id="qhelp" class="sr-only">Type at least two characters to see suggestions, then press Enter.</p></form><div class="qres" id="qgrid" aria-live="polite"></div></section>''')
    t10 = "".join(f'''<a class="t10__item" href="{BASE}{movie_path(m)}"><span class="t10__num">{i+1}</span><img src="{poster(m.get("poster"),"w342")}" alt="{e(m["title"])} poster" width="342" height="513" loading="{'eager' if i<3 else 'lazy'}" decoding="async"><span class="t10__cap"><strong>{e(m["title"])}</strong><span>{m["year"]} · {m.get('rating')}/10</span></span></a>''' for i,m in enumerate(top10[:5]))
    t10b = "".join(f'''<a class="t10__item" href="{BASE}{movie_path(m)}"><span class="t10__num">{i+6}</span><img src="{poster(m.get("poster"),"w342")}" alt="{e(m["title"])} poster" width="342" height="513" loading="lazy" decoding="async"><span class="t10__cap"><strong>{e(m["title"])}</strong><span>{m["year"]} · {m.get('rating')}/10</span></span></a>''' for i,m in enumerate(top10[5:10]))
    H.append(f'''<section class="section"><div class="section__head"><div><p class="kicker">Top 10 this week</p><h2 class="section__title">The highest rated films in our library</h2></div><a class="section__link" href="{BASE}/movies/">See all {cnt}</a></div><div class="t10">{t10}</div><div class="t10 t10--b">{t10b}</div></section>''')
    ups = UPCOMING()[:8]
    cal = ""
    if ups:
        groups = {}
        for m in ups: groups.setdefault(month_key(m.get("release_date")), []).append(m)
        for mk, rows in groups.items():
            items = ""
            for m in rows:
                rl = release_label(m)
                _t = _pd(m.get("release_date")) or (0, 1, 1)
                _day = str(_t[2])
                _mon = MON[_t[1] - 1] if 1 <= _t[1] <= 12 else ""
                _meta = join_and((m.get("genres") or ["Film"])[:2])
                if rl["status"]: _meta = _meta + " \u00b7 " + rl["status"]
                items += ('<a class="cal__row" href="%s%s">'
                          '<span class="cal__date"><b>%s</b><i>%s</i></span>'
                          '<span class="cal__body"><strong>%s</strong><span>%s</span></span>'
                          '<span class="cal__when">%s</span></a>') % (
                          BASE, movie_path(m), e(_day), e(_mon), e(m["title"]), e(_meta), e(rl["note"]))
            cal += f'<div class="cal__group"><h3 class="cal__month">{e(mk)}</h3>{items}</div>'
    if cal:
        H.append(f'''<section class="section" id="calendar"><div class="section__head"><div><p class="kicker">Coming up</p><h2 class="section__title">Release calendar</h2><p class="section__lede">Dated releases in the next six months, from studio schedules and TMDB. Dates are the announced US date and can move.</p></div><a class="section__link" href="{BASE}/movies/#upcoming">All upcoming</a></div><div class="panel cal">{cal}</div></section>''')
    H.append(f'''<section class="section">{section_head("Now trending","What everyone is watching this week",("All movies",BASE+"/movies/"))}<div class="rail"><div class="rail__track">{"".join(card(m, movie_path(m)) for m in trend)}</div></div></section>''')
    editors = [MOV[i] for i in [969681, 1368337, 1423191] if i in MOV]
    ed = "".join(f'''<a class="ed-pick" href="{BASE}{movie_path(m)}"><img src="{backdrop(m.get("backdrop"),"w780")}" alt="{e(m['title'])} ({m['year']}) backdrop" width="780" height="439" loading="lazy" decoding="async"><span class="ed-pick__veil" aria-hidden="true"></span><span class="ed-pick__body"><span class="ed-pick__meta">{m.get('rating')}/10 · {m['year']} · {e(m.get("genres",[""])[0])}</span><strong>{e(m["title"])}</strong><span class="ed-pick__line">{e((m.get("overview") or "")[:110])}…</span></span></a>''' for m in editors)
    H.append(f'''<section class="section"><div class="section__head"><div><p class="kicker">Editor picks</p><h2 class="section__title">Three films worth clearing an evening for</h2></div></div><div class="ed-grid">{ed}</div></section>''')
    cats = "".join(f'''<a class="cat" href="{BASE}/category/{g['slug']}/"><img src="{poster(g['cover'],'w342')}" alt="{e(g['name'])} movies" width="342" height="513" loading="lazy" decoding="async"><span class="cat__veil" aria-hidden="true"></span><span class="cat__label"><span class="cat__count">{CAT_COUNT.get(g["slug"],0)} {"guide" if CAT_COUNT.get(g["slug"],0)==1 else "guides"}</span>{e(g['name'])}</span></a>''' for g in GEN[:12])
    H.append(f'''<section class="section">{section_head("Browse","Categories built around how you actually choose films",("All categories",BASE+"/categories/"))}<div class="cat-grid">{cats}</div></section>''')
    prov = sorted({n for m in allm for cc in (m.get("providers") or {}).values() for k in ("flatrate","rent","buy") for n in (cc.get(k) or [])})
    pc = "".join(f'<li class="chip chip--prov">{e(s)}</li>' for s in prov[:12])
    H.append(f'''<section class="section"><div class="section__head"><div><p class="kicker">Where to watch</p><h2 class="section__title">Find the right stream in under a minute</h2></div></div>
<div class="cols"><div class="panel"><ol class="steps"><li><strong>Open the film guide.</strong> Streaming, rental and purchase options are listed for the US, UK, Canada, Australia, India and Bangladesh.</li><li><strong>Check your region.</strong> Rights change per country, so a title can be included with one service and pay-per-view on another.</li><li><strong>Confirm quality on the provider.</strong> We link out; price, HD/4K and subtitles are set there.</li></ol><a class="btn btn--primary" href="{BASE}/articles/">How we verify watch options</a></div>
<div class="panel"><h3 class="panel__title">Services we track</h3><ul class="chips">{pc}</ul><p class="note">Provider names come from live availability data. If a service is missing, the film is not listed there for the regions we check.</p></div></div></section>''')
    H.append(f'''<section class="section">{section_head("Cast & crew","The people behind the films",("All people",BASE+"/people/"))}<div class="rail"><div class="rail__track rail__track--people">{"".join(person_card(p, person_path(p)) for p in PPL[:14])}</div></div></section>''')
    faq_html = "".join(f'<details class="faq__item"><summary><h3>{e(q)}</h3></summary><p>{e(a)}</p></details>' for q,a in HOME_FAQ)
    H.append(f'''<section class="section"><div class="section__head"><div><p class="kicker">How we work</p><h2 class="section__title">Editorial standards, not scraped trivia</h2></div></div>
<div class="ed-grid"><div class="ed-card"><h3>Data with a source</h3><p>Titles, cast, crew, release dates and box office come from TMDB and are re-checked every time a page is rebuilt. When a figure is not reported, we say so.</p></div>
<div class="ed-card"><h3>Availability we verify</h3><p>Watch options are grouped by country because rights are regional. Each guide names the services reported for that market and links to the provider to confirm price.</p></div>
<div class="ed-card"><h3>Written for decisions</h3><p>Every guide answers three questions in order: what the film is, whether it fits your taste, and how to watch it. No autoplay, no pop-ups, no fake buttons.</p></div></div></section>
<section id="faq" class="section section--narrow"><div class="section__head"><div><p class="kicker">FAQ</p><h2 class="section__title">Questions people ask before pressing play</h2></div></div><div class="panel panel--faq">{faq_html}</div></section>''')
    H.append('</main>' + footer())
    idx_json = _j.dumps(idx, ensure_ascii=False).replace("</", "<" + "/")
    out = "".join(H).replace("</body>", '<script type="application/json" id="siteIndex">' + idx_json + '</script></body>')
    write("index.html", out)

def main():
    if os.path.isdir("site"): shutil.rmtree("site")
    os.makedirs("site", exist_ok=True)
    home3(); page_movies_hub(); page_categories_hub(); page_people_hub()
    for m in D["movies"]: page_movie_v2(m)
    for g in GEN: page_category(g)
    for p in PPL: page_person(p)
    page_about(); page_privacy(); page_terms(); page_faq()
    import articles_build; articles_build.build_articles()
    apply_noindex(); page_404(); write_sitemap()
    if os.path.isdir("static_extra"):
        for _f in sorted(os.listdir("static_extra")):
            _s = os.path.join("static_extra", _f)
            if os.path.isfile(_s): shutil.copyfile(_s, os.path.join("site", _f))
    for src in ["assets/og-default.jpg", "assets/style.css", "assets/app.js", "assets/favicon.svg", "assets/fonts/instrument-serif.woff2", "assets/fonts/inter-var.woff2"]:
        dst = os.path.join("site", src); os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(src, dst)
    print(f"pages: {len(set(PAGES))} | files: {sum(len(f) for _, _, f in os.walk('site'))}")

if __name__ == "__main__":
    main()
