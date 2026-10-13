"""Mirror the PX 0.8.0 wiki (MediaWiki) as raw wikitext into scratchpad/pxwiki/."""
import os, json, urllib.request, urllib.parse, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "pxwiki")
os.makedirs(OUT, exist_ok=True)
BASE = "https://px.worms2d.info/px080wiki/"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 pxdoc-mirror"})
    return urllib.request.urlopen(req, timeout=40).read()


pages = []
cont = {}
while True:
    q = {"action": "query", "list": "allpages", "aplimit": "500", "format": "json", "apnamespace": "0"}
    q.update(cont)
    d = json.loads(get(BASE + "api.php?" + urllib.parse.urlencode(q)))
    pages += [p["title"] for p in d["query"]["allpages"]]
    if "continue" in d:
        cont = {"apcontinue": d["continue"]["apcontinue"]}
    else:
        break
print("pages", len(pages))
for t in pages:
    fn = os.path.join(OUT, re.sub(r"[^\w\-.]+", "_", t) + ".wiki")
    if os.path.exists(fn):
        continue
    try:
        b = get(BASE + "index.php?" + urllib.parse.urlencode({"title": t, "action": "raw"}))
        open(fn, "wb").write(b)
    except Exception as e:
        print("FAIL", t, e)
json.dump(pages, open(os.path.join(OUT, "_pages.json"), "w"), indent=0)
print("done")
