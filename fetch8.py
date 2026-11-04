import json, os, urllib.request, urllib.parse, time
KEY=os.environ["TMDB_API_KEY"].strip(); API="https://api.themoviedb.org/3"
def get(p, **kw):
    kw["api_key"]=KEY
    for _ in range(3):
        try: return json.load(urllib.request.urlopen(API+p+"?"+urllib.parse.urlencode(kw), timeout=25))
        except Exception: time.sleep(1.2)
    return {}
D=json.load(open("data/movies.json")); G=json.load(open("data/genres.json"))
mine={m["tmdb_id"] for m in D["movies"]}
used_cover=set()
for g in G:
    res=[]
    for page in (1,2):
        j=get("/discover/movie", with_genres=g["id"], sort_by="popularity.desc", language="en-US",
              include_adult="false", **{"vote_count.gte":150, "primary_release_date.lte":"2026-11-04", "page":page})
        res+= j.get("results",[])
    seen=set(); lst=[]
    for r in res:
        if not r.get("poster_path") or r["id"] in seen: continue
        seen.add(r["id"])
        if g["id"] not in (r.get("genre_ids") or []): continue
        lst.append({"id":r["id"],"title":r["title"],"year":(r.get("release_date") or "")[:4],"poster":r["poster_path"],"rating":round(r.get("vote_average") or 0,1),"genre_ids":r.get("genre_ids",[])})
    g["movies"]=lst[:18]
    # unique cover: first poster not used by an earlier category
    cover=None
    inlib=[m for m in D["movies"] if g["name"] in m.get("genres",[]) and m.get("poster")]
    pool=[m["poster"] for m in sorted(inlib,key=lambda x:-(x.get("votes") or 0))]+[x["poster"] for x in g["movies"]]
    for p in pool:
        if p not in used_cover: cover=p; break
    g["cover"]=cover or (pool[0] if pool else None)
    used_cover.add(g["cover"])
    print(g["name"].ljust(16), len(g["movies"]), "extras | in-lib:", len(inlib), "| cover:", g["cover"])
json.dump(G, open("data/genres.json","w"), ensure_ascii=False)
