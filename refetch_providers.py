import json, os, urllib.request, time
from concurrent.futures import ThreadPoolExecutor
K=os.environ["TMDB_API_KEY"].strip()
D=json.load(open("data/movies.json"))
def get(u):
    for i in range(4):
        try: return json.load(urllib.request.urlopen(u, timeout=30))
        except Exception: time.sleep(0.6*(i+1))
    return {}
def fix(m):
    r=get(f"https://api.themoviedb.org/3/movie/{m['tmdb_id']}/watch/providers?api_key={K}").get("results",{}) or {}
    out={}
    for cc in ["US","GB","CA","AU","IN","BD"]:
        v=r.get(cc) or {}
        out[cc]={k:[x["provider_name"] for x in v.get(k,[])][:5] for k in ("flatrate","free","rent","buy") if v.get(k)}
        if v.get("link"): out[cc]["_link"]=v["link"]
    m["providers"]=out
    # full release list incl. certification, all countries, keep for ordering later
    rd=get(f"https://api.themoviedb.org/3/movie/{m['tmdb_id']}/release_dates?api_key={K}").get("results",[]) or []
    rels=[]
    for x in rd:
        dts=[d for d in x.get("release_dates",[]) if d.get("release_date")]
        if not dts: continue
        dts.sort(key=lambda d:d["release_date"])
        cert=next((d.get("certification") for d in dts if d.get("certification")),"")
        rels.append({"country":x.get("iso_3166_1"),"cert":cert,"date":dts[0]["release_date"][:10]})
    m["releases"]=rels
    return m
with ThreadPoolExecutor(max_workers=8) as ex: list(ex.map(fix, D["movies"]))
json.dump(D, open("data/movies.json","w"), ensure_ascii=False)
has=lambda m: any(any(k in v for k in ("flatrate","free","rent","buy")) for v in m["providers"].values())
print("films with any provider data:",sum(1 for m in D["movies"] if has(m)),"/",len(D["movies"]))
print("US data:",sum(1 for m in D["movies"] if any(k in m["providers"].get("US",{}) for k in ("flatrate","free","rent","buy"))),
      "| IN:",sum(1 for m in D["movies"] if any(k in m["providers"].get("IN",{}) for k in ("flatrate","free","rent","buy"))),
      "| BD:",sum(1 for m in D["movies"] if any(k in m["providers"].get("BD",{}) for k in ("flatrate","free","rent","buy"))))
