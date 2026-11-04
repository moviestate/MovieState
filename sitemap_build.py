"""Single source of truth for sitemap.xml: hashed lastmod, no changefreq/priority,
excludes noindex pages and utility URLs. Run after any content change."""
import os, re, json, hashlib, sys
BASE="https://moviestate.github.io"
ROOT=sys.argv[1] if len(sys.argv)>1 else "/tmp/ms"
LM_FILE=os.path.join(ROOT,"data","lastmod.json")
EXCLUDE_PREFIX=("search","404","assets","data","tools","fonts","src")
def rel(url): return url.replace(BASE,"").strip("/")
def walk():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:]=[d for d in dirnames if d not in (".git","assets","data","fonts","src","tools",".github","node_modules")]
        if "index.html" in filenames: yield dirpath
def load_lm():
    try: return json.load(open(LM_FILE,encoding="utf-8"))
    except Exception: return {}
def content_hash(path):
    s=open(path,encoding="utf-8",errors="ignore").read()
    s=re.sub(r"<!--.*?-->","",s,flags=re.S)
    return hashlib.sha256(s.encode()).hexdigest()
def build():
    lm=load_lm(); rows=[]; skipped=0; changed=0
    for d in sorted(walk()):
        url_path=os.path.relpath(d,ROOT).replace("\\","/")
        if url_path==".": url_path=""
        if url_path.split("/")[0] in EXCLUDE_PREFIX: skipped+=1; continue
        f=os.path.join(d,"index.html")
        s=open(f,encoding="utf-8",errors="ignore").read()
        if re.search(r'name="robots"[^>]*content="[^"]*noindex', s): skipped+=1; continue
        canon=re.search(r'<link rel="canonical" href="([^"]+)"', s)
        loc=(canon.group(1) if canon else (BASE+"/"+url_path+("/" if url_path else ""))).rstrip("/")+"/"
        if not loc.startswith(BASE+"/"): skipped+=1; continue
        h=content_hash(f)
        rec=lm.get(loc)
        if not rec or rec.get("hash")!=h:
            lm[loc]={"hash":h,"date":__import__("datetime").date.today().isoformat()}; changed+=1
        rows.append((loc, lm[loc]["date"]))
    seen=set(); out=[]
    for loc,dt in rows:
        if loc in seen: continue
        seen.add(loc)
        out.append('  <url><loc>%s</loc><lastmod>%s</lastmod></url>' % (loc,dt))
    xml=('<?xml version="1.0" encoding="UTF-8"?>\n'
         '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+"\n".join(out)+"\n</urlset>\n")
    os.makedirs(os.path.dirname(LM_FILE),exist_ok=True)
    json.dump(lm,open(LM_FILE,"w",encoding="utf-8"))
    open(os.path.join(ROOT,"sitemap.xml"),"w",encoding="utf-8").write(xml)
    # assertions
    assert 'changefreq' not in xml and '<priority>' not in xml, "changefreq/priority must not ship"
    assert all("<loc>" in r for r in out)
    dates={r.split("<lastmod>")[1][:10] for r in out}
    print("sitemap urls:",len(out),"| skipped(noindex/utility):",skipped,"| lastmod updated:",changed,"| distinct lastmod dates:",len(dates))
    return len(out)
if __name__=="__main__": build()
