"""Builds a film-specific editor's note from real fields. No invented facts: every sentence is conditional on data."""
import re
from datetime import date

TODAY = "2026-11-04"
MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

def fmt_date(iso):
    try:
        y, mo, d = [int(x) for x in str(iso)[:10].split("-")]
        return f"{MON[mo-1]} {d}, {y}"
    except Exception:
        return str(iso or "")

PARENT = {
 "G": "suitable for all ages", "PG": "suitable for most viewers, with some parental guidance for younger children",
 "PG-13": "may include intense action or themes that are unsuitable for younger children",
 "R": "restricted: it contains material intended for adults, including strong language or violence",
 "NC-17": "for adults only", "TV-MA": "for mature audiences only", "TV-14": "not recommended for children under 14",
 "NR": "not rated in the US, so check the content before watching with children",
}
MOOD = {
 "Horror": "an atmospheric night in with the lights low", "Thriller": "an evening when you want to stay on the edge of your seat",
 "Action": "a high energy night", "Science Fiction": "viewers who like big ideas", "Animation": "a family evening",
 "Family": "a family evening", "Comedy": "a relaxed night", "Drama": "a slower, character-led evening",
 "Crime": "fans of procedural tension", "Adventure": "a big-screen journey", "Fantasy": "viewers who like invented worlds",
 "Mystery": "viewers who like to piece clues together", "Romance": "a warm evening", "War": "a serious, reflective watch",
}

def _fmt_votes(v):
    return f"{v:,}"

def note(m, cert_us, similar_titles):
    t = m["title"]; y = m["year"]; votes = m.get("votes") or 0; rating = m.get("rating") or 0
    genres = m.get("genres") or []
    cast = [c["name"] for c in (m.get("cast") or [])[:3]]
    d = (m.get("director") or {}).get("name")
    rt = m.get("runtime") or 0
    out = {}

    # --- Who it's for ---
    mood = next((MOOD[g] for g in genres if g in MOOD), "a film night")
    who = f"{t} is best suited to {mood}."
    if rt:
        who += (" At " + (f"{rt//60}h {rt%60:02d}m" if rt >= 60 else f"{rt} minutes") + ", it " +
                ("fits a single evening without a break." if rt <= 110 else "is a long sitting, so plan the evening around it." if rt >= 140 else "is a standard feature length."))
    if cast and d:
        who += f" The draw is {cast[0]}{(' and ' + cast[1]) if len(cast) > 1 else ''}, directed by {d}."
    out["who"] = who

    # --- What the audience says (honest about sample size) ---
    _du = None
    try:
        from datetime import date
        y_, m_, d_ = [int(x) for x in (m.get("release_date") or "")[:10].split("-")]
        _du = (date(y_, m_, d_) - date(*[int(x) for x in TODAY.split("-")])).days
    except Exception:
        _du = None
    if _du is not None and _du > 0:
        out["audience"] = f"{t} has not been released yet. It is dated for {fmt_date(m.get('release_date'))}, so there are no audience ratings to judge it by. Use the cast, the director and the trailer to decide whether it is for you."
    elif votes >= 5000:
        out["audience"] = f"With {_fmt_votes(votes)} TMDB ratings averaging {rating}/10, this is one of the most widely seen titles in our library, so the score is a reliable signal."
    elif votes >= 300:
        out["audience"] = f"{_fmt_votes(votes)} TMDB users have rated it {rating}/10. That is a solid sample, though scores can still move as more people watch."
    elif votes >= 30:
        out["audience"] = f"It currently holds {rating}/10 from {_fmt_votes(votes)} ratings. That is a small sample, so treat the score as an early indication."
    else:
        out["audience"] = f"Only {votes} ratings have been recorded so far, which is too few to judge the film by its score. Read the overview and cast to decide."

    # --- Themes from real keywords ---
    kws = [k for k in (m.get("keywords") or []) if len(k) < 28][:4]
    if kws:
        out["themes"] = f"TMDB tags the film with themes including {', '.join(kws[:-1]) + (' and ' if len(kws) > 1 else '') + kws[-1]}."

    # --- Parental note ---
    if cert_us:
        out["parental"] = f"The US certification is {cert_us}: {PARENT.get(cert_us, 'check the content details before watching with children')}."
    else:
        out["parental"] = "No US certification is listed for this title yet, so check the content before watching with children."

    # --- Similar ---
    if similar_titles:
        out["similar"] = "If you like this, try " + (", ".join(similar_titles[:-1]) + " or " + similar_titles[-1] if len(similar_titles) > 1 else similar_titles[0]) + "."
    return out
