import json
import urllib.parse
import urllib.request

query = '[out:json][timeout:60];(node["name"~"Canal",i](6.0,-0.2,11.2,1.9););out center tags;'
data = urllib.parse.urlencode({"data": query}).encode()
req = urllib.request.Request("https://overpass-api.de/api/interpreter", data=data,
                             headers={"User-Agent": "TogoTelecomChallenge/1.0"})
with urllib.request.urlopen(req, timeout=90) as r:
    payload = json.loads(r.read().decode("utf-8"))

print("elements:", len(payload["elements"]))
for e in payload["elements"]:
    print(e.get("lat"), e.get("lon"), "|", e["tags"].get("name"))

with open(r"D:\PROJECTS\Togo Lab 2\togo_telecom_dashboard\togo_telecom_dashboard\data\external\canal_osm_points_2026.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False)
print("saved to temp")