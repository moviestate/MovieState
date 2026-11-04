import json, os, urllib.request, urllib.parse, time
KEY=os.environ["TMDB_API_KEY"].strip(); API="https://api.themoviedb.org/3"
def get(p, **kw):
    kw["api_key"]=KEY
    for _ in range(3):
        try:
            return json.load(urllib.request.urlopen(API+p+"?"+urllib.parse.urlencode(kw), timeout=25))
        except Exception as ex:
            time.sleep(1.2)
    return {}
D=json.load(open("data/movies.json"))
for m in D["movies"]:
    j=get(f"/movie/{m['tmdb_id']}", language="en-US")
    m["studios"]=[c["name"] for c in j.get("production_companies",[]) if c.get("name")][:4]
    m["country"]=", ".join(c["name"] for c in j.get("production_countries",[])[:3])
    m["homepage"]=j.get("homepage") or ""
    print(m["title"][:30].ljust(31), "|", m["country"] or "-", "|", ", ".join(m["studios"][:2]) or "-")
json.dump(D, open("data/movies.json","w"), ensure_ascii=False)
