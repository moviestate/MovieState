import json, os, urllib.request, urllib.parse, time, re
from concurrent.futures import ThreadPoolExecutor
KEY=os.environ["TMDB_API_KEY"].strip(); API="https://api.themoviedb.org/3"
def get(p, **kw):
    kw["api_key"]=KEY
    url=API+p+"?"+urllib.parse.urlencode(kw)
    for i in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as r: return json.load(r)
        except Exception: time.sleep(0.5*(i+1))
    return {}
APPEND="credits,release_dates,providers,videos,keywords,reviews,similar,external_ids,alternative_titles"
D=json.load(open("data/movies.json")); GN={g["id"]:g["name"] for g in get("/genre/movie/list", language="en-US")["genres"]}
have={m["tmdb_id"] for m in D["movies"]}
# ---- candidate ids: popular + top rated + recent, enough volume
cands=[]
for ep,pg in [("/movie/popular",1),("/movie/popular",2),("/movie/popular",3),("/movie/popular",4),
              ("/movie/top_rated",1),("/movie/top_rated",2),("/movie/top_rated",3),("/movie/now_playing",1),("/movie/upcoming",1)]:
    cands += get(ep, page=pg, language="en-US", region="US").get("results", [])
for pg in (1,2):
    cands += get("/discover/movie", sort_by="popularity.desc", language="en-US", include_adult="false",
                 **{"vote_count.gte":400,"vote_average.gte":6.5,"primary_release_date.lte":"2026-11-04","page":pg}).get("results",[])
seen=set(); ids=[]
for c in cands:
    i=c["id"]
    if i in seen or i in have: continue
    if not c.get("poster_path") or not c.get("overview"): continue
    if (c.get("vote_count") or 0) < 300: continue
    if (c.get("original_language") or "en") not in ("en","ja","ko","es","fr","hi","bn","de","it","pt","zh","ru","sv","da","no","fa","tr","id","th","pl","nl","cs","uk","he","ta","te","ml"): continue
    seen.add(i); ids.append(i)
print("candidates",len(ids))
def build(i):
    j=get(f"/movie/{i}", append_to_response=APPEND, language="en-US")
    if not j.get("id"): return None
    cr=j.get("credits",{}) or {}; crew=cr.get("crew",[]) or []
    def job(*names):
        for n in names:
            for c in crew:
                if c.get("job")==n and c.get("name"): return c["name"]
        return ""
    dirs=[c for c in crew if c.get("job")=="Director"]
    writers=[]
    for c in crew:
        if c.get("job") in ("Screenplay","Writer","Story") and c.get("name") not in writers: writers.append(c["name"])
    prods=[]
    for c in crew:
        if c.get("job")=="Producer" and c.get("name") not in prods: prods.append(c["name"])
    cast=[{"id":c["id"],"name":c["name"],"character":c.get("character") or "","profile":c.get("profile_path") or ""} for c in (cr.get("cast",[]) or [])[:12]]
    rels=[]
    for r in (j.get("release_dates",{}) or {}).get("results",[]) or []:
        dts=[d for d in r.get("release_dates",[]) if d.get("release_date")]
        if not dts: continue
        dts.sort(key=lambda d: d["release_date"])
        rels.append({"country":r.get("iso_3166_1"),"cert":(dts[0].get("certification") or ""),"date":dts[0]["release_date"][:10]})
    prov={}
    for cc in ["US","GB","CA","AU","IN","BD"]:
        v=(j.get("providers",{}) or {}).get("results",{}).get(cc) or {}
        prov[cc]={k:[x["provider_name"] for x in v.get(k,[])][:4] for k in ("flatrate","rent","buy") if v.get(k)}
    tr=None
    for v in (j.get("videos",{}) or {}).get("results",[]) or []:
        if v.get("site")=="YouTube" and v.get("type")=="Trailer": tr={"key":v["key"],"name":v.get("name") or "Official trailer"}; break
    revs=[{"author":r.get("author") or "","content":(r.get("content") or "").strip(),"rating":r.get("author_details",{}).get("rating")} for r in ((j.get("reviews",{}) or {}).get("results",[]) or [])[:2] if (r.get("content") or "").strip()]
    rd=j.get("release_date") or ""
    return {"tmdb_id":j["id"],"title":j.get("title") or "","year":int(rd[:4]) if rd[:4].isdigit() else 0,
      "release_date":rd,"rating":round(j.get("vote_average") or 0,1),"votes":j.get("vote_count") or 0,
      "poster":j.get("poster_path") or "","backdrop":j.get("backdrop_path") or "","overview":(j.get("overview") or "").strip(),
      "genres":[GN.get(g,"") for g in (j.get("genre_ids") or [x["id"] for x in j.get("genres",[])]) if GN.get(g)],
      "lang":(j.get("original_language") or "en"),"popularity":round(j.get("popularity") or 0,1),
      "runtime":j.get("runtime") or 0,"tagline":j.get("tagline") or "","status":j.get("status") or "",
      "budget":j.get("budget") or 0,"revenue":j.get("revenue") or 0,"language":j.get("original_language") or "en",
      "director":({"id":dirs[0]["id"],"name":dirs[0]["name"]} if dirs else {}),
      "cast":cast,"writer_list":writers[:3],"producer_list":prods[:3],"composer":job("Original Music Composer"),
      "dop":job("Director of Photography"),"editor":job("Editor"),"releases":rels[:10],"providers":prov,"trailer":tr,
      "reviews":revs,"keywords":[k["name"] for k in (j.get("keywords",{}) or {}).get("keywords",[])][:12],
      "imdb_id":(j.get("external_ids",{}) or {}).get("imdb_id") or "","alt_titles":[a["title"] for a in (j.get("alternative_titles",{}) or {}).get("titles",[])][:3],
      "spoken":[s.get("english_name") or s.get("name") for s in (j.get("spoken_languages") or [])][:3],
      "similar_ids":[s["id"] for s in (j.get("similar",{}) or {}).get("results",[])][:10],
      "studios":[c["name"] for c in (j.get("production_companies") or [])][:4],
      "country":", ".join(c["name"] for c in (j.get("production_countries") or [])[:3]),
      "homepage":j.get("homepage") or ""}
ids=ids[:95]
with ThreadPoolExecutor(max_workers=8) as ex: out=[m for m in ex.map(build, ids) if m and m["title"]]
print("fetched",len(out))
D["movies"]=D["movies"]+out
json.dump(D, open("data/movies.json","w"), ensure_ascii=False)
# ---- people from every cast list
allm=D["movies"]; lib={m["tmdb_id"] for m in allm}
cred={}
for m in allm:
    for c in (m.get("cast") or [])[:12]:
        e=cred.setdefault(c["id"], {"id":c["id"],"name":c["name"],"profile":c.get("profile") or "","movies":[],"chars":set()})
        e["movies"].append({"id":m["tmdb_id"],"title":m["title"],"year":m["year"],"poster":m.get("poster") or "","rating":m.get("rating"),"character":c.get("character") or ""})
for e in cred.values(): e["movies"]=e["movies"][:20]
ranked=sorted(cred.values(), key=lambda e:(-len(e["movies"]), e["name"]))
pick=ranked[:100]
def pbuild(e):
    j=get(f"/person/{e['id']}", append_to_response="movie_credits", language="en-US")
    roles=["Actor"]
    if any(c.get("job")=="Director" for c in (j.get("movie_credits",{}) or {}).get("crew",[]) or []): roles.append("Director")
    return {"id":e["id"],"name":e["name"],"profile":e["profile"],"roles":roles,"movies":e["movies"],
      "biography":(j.get("biography") or "").strip(),"birthday":j.get("birthday") or "","place":j.get("place_of_birth") or "",
      "dept":j.get("known_for_department") or "Acting","deathday":j.get("deathday") or "","also_known":j.get("also_known_as") or [],
      "gender":j.get("gender") or 0}
with ThreadPoolExecutor(max_workers=8) as ex: P=[p for p in ex.map(pbuild, pick) if p and p["biography"]]
old={p["id"] for p in P}
for p in json.load(open("data/people.json")):
    if p["id"] not in old: P.append(p)
json.dump(P, open("data/people.json","w"), ensure_ascii=False)
print("people",len(P),"with bio",sum(1 for p in P if len(p.get('biography',''))>200),"| library",len(allm))
