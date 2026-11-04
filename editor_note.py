"""Data-grounded editorial note for movie pages.

note(movie, us_cert, similar_titles) -> {"who", "audience", "themes", "parental", "similar"}
Everything is derived from the movie record; no invented facts.
"""


def _names(cast, n=3):
    out = [c.get("name") for c in (cast or [])[:n] if c.get("name")]
    if not out:
        return ""
    if len(out) == 1:
        return out[0]
    return ", ".join(out[:-1]) + " and " + out[-1]


def _hours(runtime):
    try:
        rt = int(runtime)
    except Exception:
        return ""
    h, m = divmod(rt, 60)
    return ("%dh %02dm" % (h, m)) if h else ("%dm" % m)


def note(m, us_cert="", similar=None):
    similar = similar or []
    out = {}
    title = m.get("title", "This film")
    year = m.get("year", "")
    genres = [g.lower() for g in (m.get("genres") or [])]
    dname = (m.get("director") or {}).get("name", "")
    cast = _names(m.get("cast"))
    rt = _hours(m.get("runtime"))
    rating = m.get("rating")
    votes = m.get("votes") or 0

    who = []
    if dname:
        who.append("%s is directed by %s" % (title, dname))
    if cast:
        who.append(("and stars " if who else "%s stars " % title) + cast)
    if rt:
        who.append("It runs %s" % rt)
    if who:
        out["who"] = ". ".join(who) + "."

    if genres:
        lead = genres[0]
        aud = "It is a %s film first" % lead
        if len(genres) > 1:
            aud += ", with %s alongside" % " and ".join(genres[1:3])
        if rating and votes >= 200:
            aud += ". The audience score sits at %s/10 across %s ratings" % (rating, votes)
            try:
                r = float(rating)
                if r >= 7.5:
                    aud += ", which puts it among the better received titles on this site"
                elif r >= 6.5:
                    aud += ", a solid but not unanimous reception"
                else:
                    aud += ", so go in with measured expectations"
            except Exception:
                pass
        out["audience"] = aud + "."

    tagline = (m.get("tagline") or "").strip()
    overview = (m.get("overview") or "").strip()
    themes = ""
    if tagline:
        themes = "The film sells itself on the line \"%s\"" % tagline
    if overview:
        first = overview.split(". ")[0].strip()
        if first:
            themes = (themes + ". The premise: " + first + ".") if themes else "The premise: " + first + "."
    if themes:
        out["themes"] = themes

    if us_cert:
        cert_notes = {
            "G": "General audiences: nothing in the rating suggests content that needs supervision.",
            "PG": "PG in the US means parental guidance is suggested; some scenes may unsettle very young children.",
            "PG-13": "A PG-13 rating in the US signals material unsuitable for children under 13 without a parent.",
            "R": "R in the US restricts viewers under 17 without an accompanying adult.",
            "NC-17": "An NC-17 rating in the US bars viewers under 18.",
        }
        base = cert_notes.get(str(us_cert).strip().upper(), "%s is the reported US certificate." % us_cert)
        out["parental"] = base + " Certificates differ by country, so check the local rating before a family screening."

    if similar:
        if len(similar) == 1:
            out["similar"] = "If you want the same register, %s is the closest match on this site." % similar[0]
        else:
            out["similar"] = "If you want the same register, try %s or %s." % (", ".join(similar[:-1]), similar[-1])

    return out
