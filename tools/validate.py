"""Consistency checks on data/trips.json and data/geo.json. Run after every edit.

Prints FAIL lines for hard errors and WARN lines for gaps worth a look. Exit code 1 if any FAIL.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PEOPLE = ["daryl", "ivory", "jaxon", "sloane"]
TYPES = {"Golf Trip", "International", "Couples", "Family", "Sports Trip", "Teen Tour", "Family/Personal",
         "Personal", "Guys Trip", "Girls Trip"}
CONFIDENCE = {"Exact", "Approximate", "Fuzzy", "Planned"}


def load():
    d = json.loads((ROOT / "data" / "trips.json").read_text(encoding="utf-8"))
    g = json.loads((ROOT / "data" / "geo.json").read_text(encoding="utf-8"))
    return d, g


def check(d, g):
    fails, warns = [], []
    cnames = {c["name"] for c in g["countries"]}
    terr = {t["name"] for t in g["territories"]}
    abbrs = {s["abbr"] for s in g["states"]}
    if len(cnames) != 195:
        fails.append(f"geo.json has {len(cnames)} countries, expected 195")
    if len(abbrs) != 51:
        fails.append(f"geo.json has {len(abbrs)} states, expected 51 (50 + DC)")

    def check_places(label, places):
        if not places:
            fails.append(f"{label}: no places")
        for p in places:
            if not (-90 <= p.get("lat", 999) <= 90 and -180 <= p.get("lng", 999) <= 180):
                fails.append(f"{label}: {p['name']} has bad lat/lng")
            if p["country"] is None:
                if p.get("territory") not in terr:
                    fails.append(f"{label}: {p['name']} has no country and an unknown territory")
            elif p["country"] not in cnames:
                fails.append(f"{label}: {p['name']} country {p['country']!r} is not among the 195")
            if p["country"] == "United States" and p.get("state") not in abbrs:
                fails.append(f"{label}: {p['name']} needs a valid state code")

    def check_who(label, who):
        if set(who) != set(PEOPLE):
            fails.append(f"{label}: who must list exactly {PEOPLE}")
        for p, v in who.items():
            if v not in (True, False, None):
                fails.append(f"{label}: who.{p} must be true, false or null")
        if not any(who.values()):
            fails.append(f"{label}: nobody marked as traveling")
        if None in who.values():
            warns.append(f"{label}: unknown traveler(s) {[p for p, v in who.items() if v is None]}")

    ids = set()
    for t in d["trips"]:
        label = f"trip {t.get('id')} {t.get('year')} {t.get('destination')}"
        if t["id"] in ids:
            fails.append(f"{label}: duplicate id")
        ids.add(t["id"])
        if t["type"] not in TYPES:
            fails.append(f"{label}: unknown type {t['type']!r} (add it to TYPES in validate.py if intended)")
        if t["confidence"] not in CONFIDENCE:
            fails.append(f"{label}: unknown confidence {t['confidence']!r}")
        if t["confidence"] == "Planned":
            warns.append(f"{label}: still marked Planned")
        if not isinstance(t.get("yearSort"), int):
            fails.append(f"{label}: yearSort must be a number")
        check_who(label, t["who"])
        check_places(label, t["places"])
        if all(p.get("state") == "FL" for p in t["places"]) and t["type"] != "Golf Trip":
            warns.append(f"{label}: Florida-only trip (rule: Florida intrastate trips are not counted)")
    for r in d["recurring"]:
        check_who(f"recurring {r['name']}", r["who"])
        check_places(f"recurring {r['name']}", r["places"])
    for o in d["otherVisits"]:
        ok = o["name"] in (cnames if o["kind"] == "country" else abbrs)
        if not ok:
            fails.append(f"other visit {o['name']}: not a valid {o['kind']}")
    return fails, warns


if __name__ == "__main__":
    f, w = check(*load())
    for x in w:
        print("WARN", x)
    for x in f:
        print("FAIL", x)
    print(f"{len(f)} fail, {len(w)} warn")
    sys.exit(1 if f else 0)
