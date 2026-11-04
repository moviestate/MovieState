"""Per-genre editorial copy, generated from the live dataset.

Provides EDIT: {genre_name: {"intro": "...{top}...", "faq": [(q, a), ...]}}
`{top}` is replaced by the builder with a data line about the films on that page.
"""
import json, os

BLURB = {
    "Action": "Action lives on momentum: chases, fights and set pieces that keep escalating. The strongest entries pair practical stunt craft with a reason to care about who is running.",
    "Adventure": "Adventure sells scale - new worlds, long journeys, stakes that grow with the map. It works when the location feels like a character and the crew has a reason to keep moving.",
    "Animation": "Animation spans hand-drawn craft, stop motion and modern CG. Design and timing decide quality: expressive character work and jokes that land for adults as well as children.",
    "Comedy": "Comedy is the hardest genre to recommend blind, because tone and timing decide everything. The keepers pair a clear comic premise with a cast trusted to improvise inside it.",
    "Crime": "Crime trades in procedure, motive and consequence, from heist precision to slow-burn character study. The tension should sit in the choices, not in the body count.",
    "Documentary": "Documentaries turn research into story. The best earn trust with verifiable sourcing, give subjects room to speak, and resist flattening complicated evidence.",
    "Drama": "Drama is about consequence: what a character does when the cost is real. Range runs from intimate two-handers to ensemble pieces, and the best keep the pressure on the relationships.",
    "Family": "Family films have to work for two audiences at once - the child watching and the adult in the next seat. The ones that last avoid talking down to either.",
    "Fantasy": "Fantasy earns belief through internal rules. Worlds feel real when the magic has cost, the geography stays consistent, and the story cares about the people living inside it.",
    "History": "Historical films are an interpretation, not a record. The strongest separate documented fact from dramatic invention and stay honest about which is which.",
    "Horror": "Horror runs on anticipation more than gore. Sound design, framing and what the film withholds do the work - which is why the genre travels so well across countries.",
    "Music": "Music films live or die on performance. Whether it is a concert picture, a biopic or a musical, the camera has to make the sound feel like an event.",
    "Mystery": "Mystery is a contract with the viewer: clues on the table, fair play, a solution that holds. The best entries make the puzzle matter emotionally, not just logically.",
    "Romance": "Romance works on chemistry and timing. Structure matters less than whether the two leads feel like people who would choose each other when nothing forces them to.",
    "Science Fiction": "Science fiction uses a changed premise to look at the present. The memorable ones keep the ideas grounded in a specific, believable human cost.",
    "Thriller": "Thriller is engineered tension. Suspense, not shock, does the heavy lifting, and the best entries keep the audience a step ahead of the hero and a step behind the danger.",
    "TV Movie": "Made-for-television films are built for shorter attention windows and tighter budgets, which pushes them toward clear premises and fast setups.",
    "War": "War films carry responsibility: they depict organised violence and its aftermath. The strongest focus on what the people inside the conflict lose, not only on the battle.",
    "Western": "Westerns are frontier stories about law, land and who gets to decide. The genre survives by reworking those questions for each new era.",
}

FAQ = {
    "default": [
        ("How are the ratings decided?", "Scores on this page are audience ratings reported by TMDB, shown with their vote counts so you can judge how well supported each number is. They change as new votes arrive."),
        ("Where can I watch these films?", "Open any film guide and see the Where to watch section. Official streaming, rental and purchase options are grouped by country, with a link to compare current prices on an availability index."),
    ]
}

def _load():
    try:
        return json.load(open(os.path.join("data", "genres.json"), encoding="utf-8"))
    except Exception:
        return []

GENRES = _load()

EDIT = {}
for g in GENRES:
    name = g.get("name") if isinstance(g, dict) else str(g)
    if not name:
        continue
    blurb = BLURB.get(name, "%s films differ by era, budget and intent, so the useful question is what each one is trying to do." % name)
    EDIT[name] = {
        "intro": blurb + " {top}. Each guide covers the story, cast, crew, ratings and every official way to watch in your region, and states clearly where a detail is unconfirmed.",
        "faq": list(FAQ["default"]),
    }
