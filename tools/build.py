"""Validate the data, compute every stat, and write docs/data.js for the website.

Nothing on the site is typed in by hand: every count comes from data/trips.json and data/geo.json.
Usage:  py tools/build.py
"""
import json
import pathlib
import sys
from collections import Counter, defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from validate import PEOPLE, ROOT, check, load  # noqa: E402

d, g = load()
fails, warns = check(d, g)
for x in warns:
    print("WARN", x)
if fails:
    for x in fails:
        print("FAIL", x)
    sys.exit("Validation failed; site not rebuilt.")

COUNTRY = {c["name"]: c for c in g["countries"]}
STATE = {s["abbr"]: s for s in g["states"]}
TERR = {t["name"]: t for t in g["territories"]}
CONTINENTS = ["Africa", "Antarctica", "Asia", "Europe", "North America", "Oceania", "South America"]


def category(t):
    w = {p for p in PEOPLE if t["who"][p]}
    if w == set(PEOPLE):
        return "extended" if "extended" in t["travelers"].lower() else "all4"
    if w == {"daryl", "ivory"}:
        return "couple"
    if w == {"daryl", "jaxon"}:
        return "dj"
    if len(w) == 1:
        return w.pop()[0] + "solo"
    return "mixed"


def bucket(t):
    if t["type"] == "Golf Trip":
        return "golf"
    if t["type"] == "Teen Tour":
        return "teen"
    if any(p["country"] != "United States" for p in t["places"]):
        return "intl"
    return "domestic"


def blank():
    return {p: False for p in PEOPLE}


countries = defaultdict(lambda: {"who": blank(), "trips": [], "recurring": [], "other": []})
states = defaultdict(lambda: {"who": blank(), "trips": [], "recurring": [], "other": []})
territories = defaultdict(lambda: {"who": blank(), "trips": []})


def mark(rec, who, key, ref):
    for p in PEOPLE:
        rec["who"][p] = rec["who"][p] or bool(who[p])
    if ref not in rec[key]:
        rec[key].append(ref)


for t in d["trips"]:
    t["cat"] = category(t)
    t["bucket"] = bucket(t)
    for p in t["places"]:
        if p["country"]:
            mark(countries[p["country"]], t["who"], "trips", t["id"])
        else:
            mark(territories[p["territory"]], t["who"], "trips", t["id"])
        if p.get("state"):
            mark(states[p["state"]], t["who"], "trips", t["id"])
for i, r in enumerate(d["recurring"]):
    for p in r["places"]:
        mark(countries[p["country"]], r["who"], "recurring", i)
        mark(states[p["state"]], r["who"], "recurring", i)
for i, o in enumerate(d["otherVisits"]):
    mark((countries if o["kind"] == "country" else states)[o["name"]], o["who"], "other", i)

# ---- countries, states, continents
country_rows = []
for c in g["countries"]:
    v = countries.get(c["name"])
    country_rows.append({"name": c["name"], "continent": c["continent"], "iso": c["iso"],
                         "visited": bool(v), **(v or {"who": blank(), "trips": [], "recurring": [], "other": []})})
state_rows = []
for s in g["states"]:
    v = states.get(s["abbr"])
    state_rows.append({**s, "visited": bool(v),
                       **(v or {"who": blank(), "trips": [], "recurring": [], "other": []})})
visited_c = [c for c in country_rows if c["visited"]]
visited_s = [s for s in state_rows if s["visited"]]
assert len(visited_c) + len([c for c in country_rows if not c["visited"]]) == 195
assert len(visited_s) + len([s for s in state_rows if not s["visited"]]) == 51
for c in visited_c:
    if not c["iso"]:
        warns.append(f"visited country {c['name']} has no ISO code; it will not shade on the map")
unknown = set(countries) - set(COUNTRY)
if unknown:
    sys.exit(f"countries not in geo.json: {unknown}")


def continents_for(person=None):
    return sorted({c["continent"] for c in visited_c if person is None or c["who"][person]})


people = []
for m in d["meta"]["people"]:
    p = m["key"]
    people.append({**m,
                   "trips": sum(1 for t in d["trips"] if t["who"][p]),
                   "countries": sum(1 for c in visited_c if c["who"][p]),
                   "states": sum(1 for s in visited_s if s["who"][p]),
                   "continents": continents_for(p)})

# ---- timeline: trips per year, stacked by bucket
timeline = defaultdict(Counter)
for t in d["trips"]:
    timeline[t["yearSort"]][t["bucket"]] += 1
timeline = [{"year": y, **{b: timeline[y][b] for b in ("intl", "domestic", "golf", "teen")},
             "approx": all(t["approxYear"] for t in d["trips"] if t["yearSort"] == y)}
            for y in sorted(timeline)]

# ---- bucket list: flag items someone has now done
# each item lists who wants it; doneBy[person] = places on it that person has already been to
for b in d["bucket"]:
    chk = b.get("check", {})
    b["doneBy"] = {}
    for p in b["who"]:
        done = [c["name"] for c in visited_c if c["name"] in chk.get("countries", []) and c["who"][p]]
        done += [s["name"] for s in visited_s if s["abbr"] in chk.get("states", []) and s["who"][p]]
        if done:
            b["doneBy"][p] = done
            warns.append(f"bucket list '{b['title']}' ({p}): already visited {done}; update or remove it")

stats = {
    "trips": len(d["trips"]),
    "countries": len(visited_c), "countriesTotal": 195,
    "states": len(visited_s), "statesTotal": 51,
    "continents": continents_for(), "continentsTotal": 7,
    "continentsMissing": [c for c in CONTINENTS if c not in continents_for()],
    "territories": [{"name": k, **TERR[k], **v} for k, v in sorted(territories.items())],
    "intlTrips": sum(1 for t in d["trips"] if t["bucket"] == "intl"),
    "firstYear": min(t["yearSort"] for t in d["trips"]),
    "lastYear": max(t["yearSort"] for t in d["trips"]),
    "allFourTrips": sum(1 for t in d["trips"] if t["cat"] in ("all4", "extended")),
    "idiotCupTrips": sum(1 for t in d["trips"] if t["idiotCup"]),
}

out = {**d, "countries": country_rows, "states": state_rows, "people": people, "timeline": timeline,
       "stats": stats, "notCounted": g["notCounted"]}
target = ROOT / "docs" / "data.js"
target.write_text("window.ST = " + json.dumps(out, ensure_ascii=False) + ";\n", encoding="utf-8")

# Stamp each asset link in index.html with a hash of the file, so browsers never mix
# a new page with stale cached CSS/JS (GitHub Pages caches files for 10 minutes).
import hashlib, re  # noqa: E401,E402
index = ROOT / "docs" / "index.html"
html = index.read_text(encoding="utf-8")
for name in ("styles.css", "data.js", "app.js"):
    v = hashlib.md5((ROOT / "docs" / name).read_bytes()).hexdigest()[:8]
    html = re.sub(r'(["\'])' + re.escape(name) + r'(\?v=[0-9a-f]+)?\1', rf'\g<1>{name}?v={v}\g<1>', html)
index.write_text(html, encoding="utf-8", newline="\n")

for x in warns[len(check(d, g)[1]):]:
    print("WARN", x)
print(f"trips {stats['trips']} | continents {len(stats['continents'])}/7 | countries {stats['countries']}/195 "
      f"| states {stats['states']}/51 | territories {len(stats['territories'])}")
for p in people:
    print(f"  {p['name']:7} trips {p['trips']:3}  countries {p['countries']:3}  states {p['states']:3}  "
          f"continents {len(p['continents'])}")
print("wrote", target)
