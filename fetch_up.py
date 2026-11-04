import json, os, urllib.request, urllib.parse, time
from concurrent.futures import ThreadPoolExecutor
KEY=os.environ["TMDB_API_KEY"].strip(); API="https://api.themoviedb.org/3"
def get(p, **kw):
    kw["api_key"]=KEY; url=API+p+"?"+urllib.parse.urlencode(kw)
    for i in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as r: return json.load(r)
        except Exception: time.sleep(0.5*(i+1))
    return {}
APPEND="credits,release_dates,watch/providers,videos,keywords,reviews,similar,external_ids,alternative_titles"
D=json.load(open("data/movies.json")); GN={g["id"]:g["name"] for g in get("/genre/movie/list", language="en-US")["genres"]}
have={m["tmdb_id"] for m in D["movies"]}
TODAY="2026-11-04"
res=[]
for pg in (1,2,3):
    res += get("/discover/movie", sort_by="popularity.desc", language="en-US", include_adult="false", region="US", page=pg,
               **{"primary_release_date.gte":"2026-11-06","primary_release_date.lte":"2027-06-30","vote_count.gte":0}).get("results",[])
res += get("/movie/upcoming", language="en-US", region="US", page=1).get("results",[])
res += get("/movie/upcoming", language="en-US", region="US", page=2).get("results",[])
ids=[]
for r in res:
    rd=r.get("release_date") or ""
    if r["id"] in have or r["id"] in ids: continue
    if not rd or rd<=TODAY: continue
    if not r.get("poster_path"): continue
    ids.append(r["id"])
print("future candidates", len(ids))
def build(i):
    j=get(f"/movie/{i}", append_to_response=APPEND, language="en-US")
    if not j.get("id"): return None
    cr=j.get("credits",{}) or {}; crew=cr.get("crew",[]) or []
    def job(*names):
        for n in names:
            for c in crew:
                if c.get("job")==n and c.get("name"): return c["name"]
        return ""
    dirs=[c for c in crew if c.get("job")=="Director"]; writers=[]; prods=[]
    for c in crew:
        if c.get("job") in ("Screenplay","Writer","Story") and c.get("name") not in writers: writers.append(c["name"])
        if c.get("job")=="Producer" and c.get("name") not in prods: prods.append(c["name"])
    cast=[{"id":c["id"],"name":c["name"],"character":c.get("character") or "","profile":c.get("profile_path") or ""} for c in (cr.get("cast",[]) or [])[:12]]
    rels=[]
    for r in (j.get("release_dates",{}) or {}).get("results",[]) or []:
        dts=[d for d in r.get("release_dates",[]) if d.get("release_date")]
        if not dts: continue
        dts.sort(key=lambda d: d["release_date"]); rels.append({"country":r.get("iso_3166_1"),"cert":dts[0].get("certification") or "","date":dts[0]["release_date"][:10]})
    prov={}
    for cc in ["US","GB","CA","AU","IN","BD"]:
        v=(j.get("watch/providers",{}) or {}).get("results",{}).get(cc) or {}
        prov[cc]={k:[x["provider_name"] for x in v.get(k,[])][:4] for k in ("flatrate","rent","buy") if v.get(k)}
    tr=None
    for v in (j.get("videos",{}) or {}).get("results",[]) or []:
        if v.get("site")=="YouTube" and v.get("type") in ("Trailer","Teaser"): tr={"key":v["key"],"name":v.get("name") or "Official trailer"}; break
    rd=j.get("release_date") or ""
    return {"tmdb_id":j["id"],"title":j.get("title") or "","year":int(rd[:4]) if rd[:4].isdigit() else 0,"release_date":rd,
      "rating":round(j.get("vote_average") or 0,1),"votes":j.get("vote_count") or 0,"poster":j.get("poster_path") or "","backdrop":j.get("backdrop_path") or "",
      "overview":(j.get("overview") or "").strip(),"genres":[GN.get(g,"") for g in (j.get("genre_ids") or [x["id"] for x in j.get("genres",[])]) if GN.get(g)],
      "lang":(j.get("original_language") or "en"),"popularity":round(j.get("popularity") or 0,1),"runtime":j.get("runtime") or 0,
      "tagline":j.get("tagline") or "","status":j.get("status") or "Planned","budget":j.get("budget") or 0,"revenue":j.get("revenue") or 0,
      "language":j.get("original_language") or "en","director":({"id":dirs[0]["id"],"name":dirs[0]["name"]} if dirs else {}),
      "cast":cast,"writer_list":writers[:3],"producer_list":prods[:3],"composer":job("Original Music Composer"),"dop":job("Director of Photography"),
      "editor":job("Editor"),"releases":rels[:10],"providers":prov,"trailer":tr,"reviews":[],
      "keywords":[k["name"] for k in (j.get("keywords",{}) or {}).get("keywords",[])][:12],
      "imdb_id":(j.get("external_ids",{}) or {}).get("imdb_id") or "","alt_titles":[a["title"] for a in (j.get("alternative_titles",{}) or {}).get("titles",[])][:3],
      "spoken":[s.get("english_name") or s.get("name") for s in (j.get("spoken_languages") or [])][:3],
      "similar_ids":[s["id"] for s in (j.get("similar",{}) or {}).get("results",[])][:10],
      "studios":[c["name"] for c in (j.get("production_companies") or [])][:4],
      "country":", ".join(c["name"] for c in (j.get("production_countries") or [])[:3]),"homepage":j.get("homepage") or ""}
ids=ids[:22]
with ThreadPoolExecutor(max_workers=6) as ex: out=[m for m in ex.map(build, ids) if m and m["title"] and m["release_date"]> TODAY]
D["movies"]+=out
json.dump(D, open("data/movies.json","w"), ensure_ascii=False)
for m in sorted(out,key=lambda x:x["release_date"])[:24]: print(m["release_date"], m["title"][:44], "|", m["status"])
print("added",len(out),"total",len(D["movies"]))
