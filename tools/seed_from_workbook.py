"""One-time seed: read source/shevin_travel_tracker_v5.xlsx, apply the BRIEF section 5 fixes and
OWNER_ANSWERS.md, and write data/trips.json and data/geo.json.

After this runs once, data/trips.json is the master record. New trips are added to that file
(see UPDATING.md), not the workbook. Rerunning this script overwrites data/trips.json.

Every fix below must match exactly once, or the script stops. Nothing is silently skipped.
"""
import json
import pathlib
import re
import sys

import openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
WB = ROOT / "source" / "shevin_travel_tracker_v5.xlsx"
PEOPLE = ["daryl", "ivory", "jaxon", "sloane"]

# ---------------------------------------------------------------- reference geography
# 195 = 193 UN members + Vatican City + Palestine (observers). Continent = 7-continent model.
CONTINENTS = {
    "Africa": """Algeria|Angola|Benin|Botswana|Burkina Faso|Burundi|Cabo Verde|Cameroon|Central African Republic|
        Chad|Comoros|Congo Dem. Rep.|Congo Rep.|Cote d'Ivoire|Djibouti|Egypt|Equatorial Guinea|Eritrea|Eswatini|
        Ethiopia|Gabon|Gambia|Ghana|Guinea|Guinea-Bissau|Kenya|Lesotho|Liberia|Libya|Madagascar|Malawi|Mali|
        Mauritania|Mauritius|Morocco|Mozambique|Namibia|Niger|Nigeria|Rwanda|Sao Tome and Principe|Senegal|
        Seychelles|Sierra Leone|Somalia|South Africa|South Sudan|Sudan|Tanzania|Togo|Tunisia|Uganda|Zambia|Zimbabwe""",
    "Asia": """Afghanistan|Armenia|Azerbaijan|Bahrain|Bangladesh|Bhutan|Brunei|Cambodia|China|Georgia|India|
        Indonesia|Iran|Iraq|Israel|Japan|Jordan|Kazakhstan|Kuwait|Kyrgyzstan|Laos|Lebanon|Malaysia|Maldives|
        Mongolia|Myanmar|Nepal|North Korea|Oman|Pakistan|Palestine|Philippines|Qatar|Saudi Arabia|Singapore|
        South Korea|Sri Lanka|Syria|Tajikistan|Thailand|Timor-Leste|Turkey|Turkmenistan|United Arab Emirates|
        Uzbekistan|Vietnam|Yemen""",
    "Europe": """Albania|Andorra|Austria|Belarus|Belgium|Bosnia and Herzegovina|Bulgaria|Croatia|Cyprus|
        Czech Republic|Denmark|Estonia|Finland|France|Germany|Greece|Hungary|Iceland|Ireland|Italy|Latvia|
        Liechtenstein|Lithuania|Luxembourg|Malta|Moldova|Monaco|Montenegro|Netherlands|North Macedonia|Norway|
        Poland|Portugal|Romania|Russia|San Marino|Serbia|Slovakia|Slovenia|Spain|Sweden|Switzerland|Ukraine|
        United Kingdom|Vatican City""",
    "North America": """Antigua and Barbuda|Bahamas|Barbados|Belize|Canada|Costa Rica|Cuba|Dominica|
        Dominican Republic|El Salvador|Grenada|Guatemala|Haiti|Honduras|Jamaica|Mexico|Nicaragua|Panama|
        Saint Kitts and Nevis|Saint Lucia|Saint Vincent and Grenadines|Trinidad and Tobago|United States""",
    "South America": """Argentina|Bolivia|Brazil|Chile|Colombia|Ecuador|Guyana|Paraguay|Peru|Suriname|
        Uruguay|Venezuela""",
    "Oceania": """Australia|Fiji|Kiribati|Marshall Islands|Micronesia|Nauru|New Zealand|Palau|Papua New Guinea|
        Samoa|Solomon Islands|Tonga|Tuvalu|Vanuatu""",
    "Antarctica": "",
}
# ISO 3166 numeric codes (world-atlas ids) for map shading. Needed for visited countries; build warns if missing.
ISO = {"Argentina": "032", "Austria": "040", "Bahamas": "044", "Belgium": "056", "Brazil": "076",
       "Canada": "124", "Costa Rica": "188", "Croatia": "191", "Czech Republic": "203",
       "Dominican Republic": "214", "France": "250", "Greece": "300", "Ireland": "372", "Israel": "376",
       "Italy": "380", "Jamaica": "388", "Mexico": "484", "Morocco": "504", "Netherlands": "528",
       "Portugal": "620", "Slovenia": "705", "South Africa": "710", "Spain": "724", "Switzerland": "756",
       "United Arab Emirates": "784", "United Kingdom": "826", "United States": "840",
       "Japan": "392", "Australia": "036", "New Zealand": "554", "Germany": "276", "Peru": "604",
       "Chile": "152", "Colombia": "170", "Norway": "578", "Sweden": "752", "Denmark": "208",
       "Iceland": "352", "Kenya": "404", "Tanzania": "834", "Rwanda": "646", "Thailand": "764",
       "Vietnam": "704", "Indonesia": "360", "Hungary": "348", "Poland": "616", "Turkey": "792"}
TERRITORIES = [  # visited or listed places that are not among the 195
    {"name": "Cayman Islands", "of": "United Kingdom (overseas territory)", "continent": "North America"},
    {"name": "Puerto Rico", "of": "United States (territory)", "continent": "North America"},
]
NOT_COUNTED = [  # appeared in the workbook country list but are not among the 195
    {"name": "Kosovo", "why": "Not a UN member or observer"},
    {"name": "Taiwan", "why": "Not a UN member or observer"},
]
STATES = """AL 01 Alabama|AK 02 Alaska|AZ 04 Arizona|AR 05 Arkansas|CA 06 California|CO 08 Colorado|
    CT 09 Connecticut|DE 10 Delaware|DC 11 Washington DC|FL 12 Florida|GA 13 Georgia|HI 15 Hawaii|ID 16 Idaho|
    IL 17 Illinois|IN 18 Indiana|IA 19 Iowa|KS 20 Kansas|KY 21 Kentucky|LA 22 Louisiana|ME 23 Maine|
    MD 24 Maryland|MA 25 Massachusetts|MI 26 Michigan|MN 27 Minnesota|MS 28 Mississippi|MO 29 Missouri|
    MT 30 Montana|NE 31 Nebraska|NV 32 Nevada|NH 33 New Hampshire|NJ 34 New Jersey|NM 35 New Mexico|
    NY 36 New York|NC 37 North Carolina|ND 38 North Dakota|OH 39 Ohio|OK 40 Oklahoma|OR 41 Oregon|
    PA 42 Pennsylvania|RI 44 Rhode Island|SC 45 South Carolina|SD 46 South Dakota|TN 47 Tennessee|TX 48 Texas|
    UT 49 Utah|VT 50 Vermont|VA 51 Virginia|WA 53 Washington|WV 54 West Virginia|WI 55 Wisconsin|WY 56 Wyoming"""


def split(s):
    return [x.strip() for x in s.split("|") if x.strip()]


countries = [{"name": n, "continent": c, "iso": ISO.get(n)} for c, s in CONTINENTS.items() for n in split(s)]
states = [{"abbr": a, "fips": f, "name": n} for a, f, n in (re.match(r"(\w\w) (\d\d) (.+)", x).groups()
                                                           for x in split(STATES))]
assert len(countries) == 195, len(countries)
assert len(states) == 51, len(states)
CNAMES = {c["name"] for c in countries}
SBY = {s["name"]: s["abbr"] for s in states}

# ---------------------------------------------------------------- places (lat, lng, country, state/territory)
US = "United States"
P = {
    # USA
    "Tempe, AZ": (33.43, -111.94, US, "AZ"), "Washington DC": (38.91, -77.04, US, "DC"),
    "San Francisco, CA": (37.77, -122.42, US, "CA"), "Myrtle Beach, SC": (33.69, -78.89, US, "SC"),
    "Tunica, MS": (34.69, -90.38, US, "MS"), "Charleston, SC": (32.78, -79.93, US, "SC"),
    "Austin, TX": (30.27, -97.74, US, "TX"), "Indianapolis, IN": (39.77, -86.16, US, "IN"),
    "Keystone, CO": (39.60, -105.95, US, "CO"), "New Orleans, LA": (29.95, -90.07, US, "LA"),
    "Milwaukee, WI": (43.04, -87.91, US, "WI"), "New Jersey": (40.06, -74.41, US, "NJ"),
    "Michigan": (44.30, -85.60, US, "MI"), "Pinehurst, NC": (35.20, -79.47, US, "NC"),
    "Napa Valley, CA": (38.30, -122.29, US, "CA"), "Whistling Straits, WI": (43.85, -87.73, US, "WI"),
    "Maui, HI": (20.80, -156.33, US, "HI"), "Big Island, HI": (19.60, -155.52, US, "HI"),
    "Vail, CO": (39.64, -106.37, US, "CO"), "San Diego, CA": (32.72, -117.16, US, "CA"),
    "Durham, NC": (35.99, -78.90, US, "NC"), "Chapel Hill, NC": (35.91, -79.06, US, "NC"),
    "Jackson Hole, WY": (43.48, -110.76, US, "WY"), "Nashville, TN": (36.16, -86.78, US, "TN"),
    "Blackberry Mountain, TN": (35.66, -83.86, US, "TN"), "TPC Sawgrass, FL": (30.20, -81.39, US, "FL"),
    "Beech Mountain, NC": (36.21, -81.88, US, "NC"), "Cashiers, NC": (35.11, -83.10, US, "NC"),
    "Pebble Beach, CA": (36.57, -121.95, US, "CA"), "Bangor, ME": (44.80, -68.77, US, "ME"),
    "Kiawah Island, SC": (32.61, -80.08, US, "SC"), "Big Cedar, MO": (36.59, -93.33, US, "MO"),
    "Savannah, GA": (32.08, -81.09, US, "GA"), "San Antonio, TX": (29.42, -98.49, US, "TX"),
    "Oconee, SC": (34.75, -83.07, US, "SC"), "Lake Norman, NC": (35.55, -80.93, US, "NC"),
    "Buena Vista, CO": (38.84, -106.13, US, "CO"), "Boulder, CO": (40.01, -105.27, US, "CO"),
    "Yellowstone, WY": (44.43, -110.59, US, "WY"), "Park City, UT": (40.65, -111.50, US, "UT"),
    "Lake Tahoe, CA": (39.10, -120.03, US, "CA"), "Santa Barbara, CA": (34.42, -119.70, US, "CA"),
    "Los Angeles, CA": (34.05, -118.24, US, "CA"), "Las Vegas, NV": (36.17, -115.14, US, "NV"),
    "Zion, UT": (37.30, -113.03, US, "UT"), "Bryce Canyon, UT": (37.59, -112.19, US, "UT"),
    "Grand Canyon, AZ": (36.11, -112.11, US, "AZ"), "Sedona, AZ": (34.87, -111.76, US, "AZ"),
    "Scottsdale, AZ": (33.49, -111.93, US, "AZ"), "Philadelphia, PA": (39.95, -75.17, US, "PA"),
    "Arcadia Bluffs, MI": (44.49, -86.24, US, "MI"), "Bend, OR": (44.06, -121.31, US, "OR"),
    "Buffalo, NY": (42.89, -78.88, US, "NY"),
    # recurring
    "Denver, CO": (39.74, -104.99, US, "CO"), "New York, NY": (40.71, -74.01, US, "NY"),
    "Chicago, IL": (41.88, -87.63, US, "IL"), "Boston, MA": (42.36, -71.06, US, "MA"),
    "Portland, ME": (43.66, -70.26, US, "ME"), "Bar Harbor, ME": (44.39, -68.20, US, "ME"),
    "Asheville, NC": (35.60, -82.55, US, "NC"),
    # territories
    "San Juan, Puerto Rico": (18.47, -66.11, None, "Puerto Rico"),
    "Grand Cayman": (19.29, -81.37, None, "Cayman Islands"),
    # international
    "Israel": (31.77, 35.21, "Israel", None), "Rome": (41.90, 12.50, "Italy", None),
    "Florence": (43.77, 11.26, "Italy", None), "Venice": (45.44, 12.32, "Italy", None),
    "Tuscany": (43.32, 11.33, "Italy", None), "Barcelona": (41.39, 2.17, "Spain", None),
    "Madrid": (40.42, -3.70, "Spain", None), "San Sebastian": (43.32, -1.98, "Spain", None),
    "Marbella": (36.51, -4.88, "Spain", None), "Paris": (48.86, 2.35, "France", None),
    "Amsterdam": (52.37, 4.90, "Netherlands", None), "Brussels": (50.85, 4.35, "Belgium", None),
    "Portugal": (39.60, -8.00, "Portugal", None), "Morocco": (31.80, -7.10, "Morocco", None),
    "Salvador": (-12.97, -38.50, "Brazil", None), "Morro de Sao Paulo": (-13.38, -38.91, "Brazil", None),
    "Mendoza": (-32.89, -68.83, "Argentina", None), "Salta": (-24.78, -65.41, "Argentina", None),
    "Buenos Aires": (-34.60, -58.38, "Argentina", None), "Kruger": (-23.99, 31.55, "South Africa", None),
    "Cape Town": (-33.92, 18.42, "South Africa", None), "Stellenbosch": (-33.93, 18.86, "South Africa", None),
    "Grootbos": (-34.54, 19.43, "South Africa", None), "Dubai": (25.20, 55.27, "United Arab Emirates", None),
    "Montreal": (45.50, -73.57, "Canada", None), "Toronto": (43.65, -79.38, "Canada", None),
    "Mont Tremblant": (46.21, -74.58, "Canada", None),
    "Casa de Campo": (18.41, -68.95, "Dominican Republic", None),
    "Punta Cana": (18.58, -68.40, "Dominican Republic", None), "Negril": (18.27, -78.35, "Jamaica", None),
    "Nassau": (25.07, -77.40, "Bahamas", None), "Guanacaste": (10.50, -85.60, "Costa Rica", None),
    "Rio Celeste": (10.71, -84.99, "Costa Rica", None), "La Fortuna": (10.47, -84.64, "Costa Rica", None),
    "Ireland": (52.95, -8.20, "Ireland", None), "London": (51.51, -0.13, "United Kingdom", None),
    "Switzerland": (46.80, 8.20, "Switzerland", None), "Austria": (47.50, 13.30, "Austria", None),
    "Tulum": (20.21, -87.47, "Mexico", None), "Dubrovnik": (42.65, 18.09, "Croatia", None),
    "Split": (43.51, 16.44, "Croatia", None), "Hvar": (43.17, 16.44, "Croatia", None),
    "Ljubljana": (46.06, 14.51, "Slovenia", None), "Salzburg": (47.81, 13.06, "Austria", None),
    "Vienna": (48.21, 16.37, "Austria", None), "Prague": (50.08, 14.44, "Czech Republic", None),
    "Greek Islands": (37.00, 25.40, "Greece", None),
}


def place(name):
    lat, lng, country, sub = P[name]
    d = {"name": name, "lat": lat, "lng": lng, "country": country}
    if country == US:
        d["state"] = sub
    elif country is None:
        d["territory"] = sub
    return d


# Trip destination text (after fixes) -> places. Matched on destination substring + year.
TEEN_WEST = ["Boulder, CO", "Jackson Hole, WY", "Yellowstone, WY", "Park City, UT", "San Francisco, CA",
             "Lake Tahoe, CA", "Santa Barbara, CA", "Los Angeles, CA", "San Diego, CA", "Las Vegas, NV",
             "Zion, UT", "Bryce Canyon, UT", "Grand Canyon, AZ", "Sedona, AZ", "Scottsdale, AZ"]
TEEN_EUROPE = ["Dubrovnik", "Split", "Hvar", "Ljubljana", "Salzburg", "Vienna", "Prague", "Greek Islands"]
PLACES_FOR = [  # (year or None, destination contains, places)
    (1988, "Israel", ["Israel"]), (1993, "Rome", ["Rome", "Florence", "Venice"]),
    (1993, "Israel", ["Israel"]), (1996, "Study Abroad", ["Barcelona", "Madrid", "San Sebastian", "Marbella"]),
    (1996, "Paris", ["Paris"]), (1996, "Amsterdam", ["Amsterdam"]), (1996, "Brussels", ["Brussels"]),
    (1996, "Portugal", ["Portugal"]), (1996, "Morocco", ["Morocco"]), (1997, "Tempe", ["Tempe, AZ"]),
    (2002, "Washington DC", ["Washington DC"]), (2003, "San Francisco", ["San Francisco, CA"]),
    (2000, "Salvador", ["Salvador", "Morro de Sao Paulo"]), (2003, "Myrtle", ["Myrtle Beach, SC"]),
    (2004, "Tunica", ["Tunica, MS"]), (2004, "Cayman", ["Grand Cayman"]),
    (2005, "Charleston", ["Charleston, SC"]), (2006, "Argentina", ["Mendoza", "Salta", "Buenos Aires"]),
    (2006, "Austin", ["Austin, TX"]), (2006, "Indianapolis", ["Indianapolis, IN"]),
    (2007, "Keystone", ["Keystone, CO"]), (2007, "South Africa", ["Kruger", "Cape Town", "Stellenbosch"]),
    (2007, "New Orleans", ["New Orleans, LA"]), (2008, "Montreal", ["Montreal"]),
    (2009, "Milwaukee", ["Milwaukee, WI"]), (2010, "New Jersey", ["New Jersey"]),
    (2011, "Michigan", ["Michigan"]), (None, "Casa de Campo", ["Casa de Campo"]),
    (None, "Pinehurst, NC", ["Pinehurst, NC"]), (None, "Napa", ["Napa Valley, CA"]),
    (2014, "Whistling", ["Whistling Straits, WI"]), (2016, "Maui", ["Maui, HI"]), (2016, "Vail", ["Vail, CO"]),
    (2017, "Jamaica", ["Negril"]), (2017, "San Diego", ["San Diego, CA"]),
    (2017, "Durham", ["Durham, NC", "Chapel Hill, NC"]), (2018, "Jackson Hole", ["Jackson Hole, WY"]),
    (2019, "Nashville", ["Nashville, TN", "Blackberry Mountain, TN"]), (2019, "Sawgrass", ["TPC Sawgrass, FL"]),
    (2019, "Dubai", ["Dubai", "Kruger", "Cape Town", "Grootbos"]),
    (2020, "Beech", ["Beech Mountain, NC", "Cashiers, NC"]), (None, "Pebble", ["Pebble Beach, CA"]),
    (None, "Keystone, CO", ["Keystone, CO"]), (None, "Bangor", ["Bangor, ME"]),
    (2021, "Kiawah", ["Kiawah Island, SC"]), (2021, "Tuscany", ["Tuscany", "Florence"]),
    (2021, "Big Cedar", ["Big Cedar, MO"]), (2021, "Savannah", ["Savannah, GA"]),
    (2022, "Baha Mar", ["Nassau"]), (2022, "San Antonio", ["San Antonio, TX"]),
    (2022, "Costa Rica", ["Guanacaste"]), (2022, "Oconee", ["Oconee, SC"]),
    (2023, "San Sebastian", ["San Sebastian", "Paris"]), (2023, "Ireland", ["Ireland"]),
    (2023, "Rome", ["Rome", "Florence", "Venice"]), (2023, "Punta Cana", ["Punta Cana"]),
    (2024, "Paris", ["Paris", "London"]), (2024, "Lake Norman", ["Lake Norman, NC"]),
    (2024, "Buena Vista", ["Buena Vista, CO"]), (2024, "American West", TEEN_WEST),
    (2024, "Switzerland", ["Switzerland", "Austria"]), (2025, "Tulum", ["Tulum"]),
    (2025, "Maui", ["Maui, HI", "Big Island, HI"]), (2025, "Philadelphia", ["Philadelphia, PA"]),
    (2025, "Central Europe", TEEN_EUROPE), (2025, "Arcadia", ["Arcadia Bluffs, MI"]),
    (2026, "Costa Rica", ["Rio Celeste", "La Fortuna"]),
    (2026, "Durham", ["Durham, NC", "Chapel Hill, NC", "Pinehurst, NC"]), (2026, "Bend", ["Bend, OR"]),
    (2026, "Lake Tahoe", ["Lake Tahoe, CA"]), (2009, "Puerto Rico", ["San Juan, Puerto Rico"]),
    (2008, "Buffalo", ["Buffalo, NY", "Toronto"]), (2000, "Mont Tremblant", ["Mont Tremblant"]),
]


def clean(v):
    if v is None:
        return ""
    s = str(v).strip()
    return s.replace(" — ", ", ").replace("—", ", ").replace("–", "-").replace("→", " to ")


def who(v):
    v = clean(v).upper()
    return True if v == "X" else (None if v == "?" else False)


def year_sort(y):
    m = re.search(r"(\d{4})", y)
    if m:
        return int(m.group(1))
    if y.lower().startswith("early 2000"):
        return 2000
    sys.exit(f"cannot sort year {y!r}")


wb = openpyxl.load_workbook(WB, data_only=True)

# ---------------------------------------------------------------- Trip Log
rows = []
for r in wb["Trip Log"].iter_rows(min_row=4, values_only=True):
    if not r[0] and not r[2]:
        continue
    rows.append({
        "year": clean(r[0]), "timing": clean(r[1]), "destination": clean(r[2]), "countryText": clean(r[3]),
        "who": {p: who(r[4 + i]) for i, p in enumerate(PEOPLE)}, "type": clean(r[8]),
        "travelers": clean(r[9]), "confidence": clean(r[10]), "notes": clean(r[11]),
    })
print(f"read {len(rows)} trip rows from workbook")
fixlog = []


def find(year, text):
    hits = [t for t in rows if t["year"].endswith(str(year)) and text in t["destination"]]
    if len(hits) != 1:
        sys.exit(f"fix target {year} {text!r} matched {len(hits)} rows")
    return hits[0]


def fix(year, text, why, **changes):
    t = find(year, text)
    t.update(changes)
    fixlog.append(f"{year} {text}: {why}")


def add(why, **t):
    base = {"timing": "", "countryText": "", "notes": "", "confidence": "Approximate"}
    base.update(t)
    rows.append(base)
    fixlog.append(f"added {t['year']} {t['destination']}: {why}")


# BRIEF 5.3 Puerto Rico 2009
add("BRIEF 5.3, missing from Trip Log", year="2009", destination="San Juan, Puerto Rico",
    countryText="Puerto Rico (US territory)", who={"daryl": True, "ivory": False, "jaxon": False, "sloane": False},
    type="Guys Trip", travelers="Daryl + friends", confidence="Exact",
    notes="Guys trip for Keith's bachelor party. US territory, not counted as a country.")
# BRIEF 5.4 Philadelphia
fix(2025, "Philadelphia", "BRIEF 5.4, was typed International", type="Personal")
# BRIEF 5.5 rows missing from the Trip Log
add("BRIEF 5.5; year unknown per owner. 2008 is an estimate (first Bills Toronto Series game was Dolphins v Bills, Dec 2008)",
    year="~2008", timing="", destination="Buffalo, NY + Toronto, Canada (Dolphins away game)", countryText="USA / Canada",
    who={"daryl": True, "ivory": False, "jaxon": False, "sloane": False}, type="Sports Trip",
    travelers="Daryl + others", confidence="Fuzzy",
    notes="Dolphins away game. Year is an estimate; confirm.")
add("BRIEF 5.5; year 2000 per owner", year="2000", destination="Mont Tremblant, Canada", countryText="Canada",
    who={"daryl": True, "ivory": False, "jaxon": False, "sloane": False}, type="Family",
    travelers="Daryl + brother + parents", confidence="Approximate", notes="With brother Brandon and parents.")
add("BRIEF 5.5", year="2021", destination="Savannah, GA", countryText="USA (Domestic)",
    who={p: True for p in PEOPLE}, type="Family", travelers="All four", confidence="Exact",
    notes="Stopover on the drive to Kiawah.")
# OWNER_ANSWERS 1: 2026 planned trips happened
for y, t in [(2026, "Durham"), (2026, "Bend"), (2026, "Lake Tahoe")]:
    r = find(y, t)
    fix(y, t, "OWNER_ANSWERS 1, planned trip happened", confidence="Exact",
        notes=re.sub(r",?\s*UPCOMING$", "", r["notes"]).strip())
fix(2026, "Bend", "tidy destination", destination="Bend, OR")
# OWNER_ANSWERS 2: Hawaii is two trips (2016 couples, 2025 all four). The 2021 row is a phantom.
phantom = find(2021, "Maui")
rows.remove(phantom)
fixlog.append("removed 2021 Maui: OWNER_ANSWERS 2, phantom (all-four Hawaii trip is the 2025 row)")
# OWNER_ANSWERS 3, 4, 5
fix(1993, "Rome", "OWNER_ANSWERS 3, confirmed", confidence="Exact", notes="High school trip")
fix(2002, "Washington DC", "OWNER_ANSWERS 4, Daryl only", type="Personal")
r =[t for t in rows if t["year"] == "Early 2000s" and "Salvador" in t["destination"]]
assert len(r) == 1
r[0]["year"] = "~2000"
fixlog.append("Early 2000s Brazil: OWNER_ANSWERS 5, year ~2000 (estimate)")
# privacy hygiene: drop a child's age from a note
fix(2023, "Rome", "drop age detail", notes="With grandma and cousin Keaton. Daryl and Ivory not on this trip.")

# ---------------------------------------------------------------- attach places, ids, flags
TIMING_ORDER = {"jan": 1, "feb": 2, "mar": 3, "spring break": 3.5, "apr": 4, "may": 5, "father's day": 6,
                "jun": 6, "summer": 7, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12, "": 13}
for t in rows:
    ys = year_sort(t["year"])
    hits = [pl for (y, s, pl) in PLACES_FOR if y == ys and s in t["destination"]] or \
           [pl for (y, s, pl) in PLACES_FOR if y is None and s in t["destination"]]
    if len(hits) != 1:
        sys.exit(f"place lookup for {t['year']} {t['destination']!r} matched {len(hits)}")
    t["places"] = [place(n) for n in hits[0]]
    t["yearSort"] = ys
    t["approxYear"] = not re.fullmatch(r"\d{4}", t["year"])
    t["idiotCup"] = t["type"] == "Golf Trip" and "Annual golf trip" in t["notes"]
    t.pop("countryText", None)
rows.sort(key=lambda t: (t["yearSort"], TIMING_ORDER.get(t["timing"].lower(), 13), t["destination"]))
for i, t in enumerate(rows, 1):
    t["id"] = i

# ---------------------------------------------------------------- recurring destinations
Y, N, Q = True, False, None
recurring = [
    {"name": "Denver, CO", "places": ["Denver, CO"], "who": [Y, Y, Y, Y], "firstVisit": "~2008",
     "frequency": "1 to 2 times a year for about 15 years. Brother Brandon lives there. Gateway to Keystone."},
    {"name": "Keystone, CO", "places": ["Keystone, CO"], "who": [Y, Y, Y, Y], "firstVisit": "2007",
     "frequency": "About 5 weeks every summer since COVID; regular before that. Wedding venue in 2007."},
    {"name": "New York, NY", "places": ["New York, NY"], "who": [Y, Y, Y, Q], "firstVisit": "~2000s",
     "frequency": "Many times, in various combinations. Never all four together. Sloane to confirm."},
    {"name": "Chicago, IL", "places": ["Chicago, IL"], "who": [Y, Y, N, N], "firstVisit": "~2000s",
     "frequency": "Daryl about 6 times; Daryl and Ivory together twice. Kids have not been."},
    {"name": "Boston, MA", "places": ["Boston, MA"], "who": [Y, Y, Y, N], "firstVisit": "~2000s",
     "frequency": "Several couples trips; one included Jaxon."},
    {"name": "Las Vegas, NV", "places": ["Las Vegas, NV"], "who": [Y, Y, Y, N], "firstVisit": "~2000s",
     "frequency": "Couples trips over the years. Jaxon on his 2024 teen tour."},
    {"name": "New Orleans, LA", "places": ["New Orleans, LA"], "who": [Y, Y, N, N], "firstVisit": "~1990s",
     "frequency": "Jazz Fest, Mardi Gras, bowl games, the 2007 golf trip. Both many times."},
    {"name": "Maine", "places": ["Bangor, ME", "Portland, ME", "Bar Harbor, ME"], "who": [Y, Y, Y, Y],
     "firstVisit": "~2019",
     "frequency": "July visit to Sloane's camp in Bangor most summers; also Portland and Bar Harbor."},
    {"name": "Asheville, NC", "places": ["Asheville, NC"], "who": [Y, Y, Y, N], "firstVisit": "~2018",
     "frequency": "A few trips. Sloane has not been."},
]
for r in recurring:
    r["who"] = dict(zip(PEOPLE, r["who"]))
    r["places"] = [place(n) for n in r["places"]]

# ---------------------------------------------------------------- Tracker: per-person marks
ws = wb["Tracker"]
section = None
tracker = {"continent": {}, "country": {}, "state": {}}
for r in ws.iter_rows(min_row=1, values_only=True):
    label = clean(r[0])
    if "CONTINENTS" in label:
        section = "continent"
    elif "COUNTRIES" in label:
        section = "country"
    elif "US STATES" in label:
        section = "state"
    elif not label or "not yet visited" in label or label.endswith(":") or label.startswith("Mark X") \
            or label.startswith("Shevin Family"):
        continue
    elif section:
        tracker[section][label] = {"who": {p: clean(r[1 + i]).upper() == "X" for i, p in enumerate(PEOPLE)},
                                   "note": clean(r[6])}
print("tracker rows:", {k: len(v) for k, v in tracker.items()})

# Country list audit against the official 195
tc = set(tracker["country"])
fixlog.append(f"workbook country rows: {len(tc)}")
fixlog.append("in workbook, not among the 195: " + ", ".join(sorted(tc - CNAMES)))
fixlog.append("among the 195, missing from workbook: " + ", ".join(sorted(CNAMES - tc)))
ts = set(tracker["state"])
fixlog.append("states missing from workbook: " + ", ".join(sorted(set(SBY) - ts)))

# What the trips + recurring imply, per person
implied = {"country": {}, "state": {}}
for src in rows + recurring:
    for pl in src["places"]:
        keys = []
        if pl["country"]:
            keys.append(("country", pl["country"]))
        if pl.get("state"):
            keys.append(("state", [s["name"] for s in states if s["abbr"] == pl["state"]][0]))
        for k in keys:
            d = implied[k[0]].setdefault(k[1], {p: False for p in PEOPLE})
            for p in PEOPLE:
                d[p] = d[p] or bool(src["who"][p])

# Residual: marked in the Tracker but not backed by any trip or recurring entry -> otherVisits
other_visits = []
diffs = []
for kind in ("country", "state"):
    for name, rec in tracker[kind].items():
        if kind == "country" and name not in CNAMES:
            continue
        imp = implied[kind].get(name, {p: False for p in PEOPLE})
        extra = [p for p in PEOPLE if rec["who"][p] and not imp[p]]
        missing = [p for p in PEOPLE if imp[p] and not rec["who"][p]]
        if extra:
            other_visits.append({"kind": kind, "name": name if kind == "country" else SBY[name],
                                 "who": {p: p in extra for p in PEOPLE}, "note": rec["note"],
                                 "source": "Workbook Tracker tab; no trip on record"})
        if missing:
            diffs.append(f"{kind} {name}: trips show {', '.join(missing)} but the Tracker did not mark them")
for d in diffs:
    fixlog.append("Tracker correction from trips: " + d)
for o in other_visits:
    fixlog.append(f"kept from Tracker without a trip: {o['kind']} {o['name']} "
                  f"({', '.join(p for p in PEOPLE if o['who'][p])}) {o['note']}")

# ---------------------------------------------------------------- bucket list (regenerated)
bucket = [
    {"title": "Japan", "for": "Whole family", "note": "Top family pick.", "check": {"countries": ["Japan"]}},
    {"title": "East and Southeast Asia", "for": "Daryl + Ivory",
     "note": "Thailand, Vietnam, Bali and more. Our only Asian stops so far are Israel and Dubai.",
     "check": {"countries": ["China", "Thailand", "Vietnam", "Indonesia", "South Korea"]}},
    {"title": "Australia + New Zealand", "for": "Daryl + Ivory", "note": "Would open up continent number 6.",
     "check": {"countries": ["Australia", "New Zealand"]}},
    {"title": "East Africa safari", "for": "Daryl + Ivory",
     "note": "Serengeti, Kenya, Rwanda. South Africa done twice.",
     "check": {"countries": ["Tanzania", "Kenya", "Rwanda"]}},
    {"title": "Alaska", "for": "Whole family", "note": "None of us have been.", "check": {"states": ["AK"]}},
    {"title": "Eastern Europe", "for": "Daryl + Ivory", "note": "Jaxon has been on his 2025 teen tour.",
     "check": {"countries": ["Croatia", "Slovenia", "Czech Republic", "Hungary", "Poland"],
               "who": ["daryl", "ivory"]}},
    {"title": "Greece", "for": "Daryl + Ivory", "note": "Jaxon did the Greek Islands in 2025.",
     "check": {"countries": ["Greece"], "who": ["daryl", "ivory"]}},
    {"title": "Scandinavia", "for": "Daryl + Ivory", "note": "Norway, Sweden, Denmark, Iceland.",
     "check": {"countries": ["Norway", "Sweden", "Denmark", "Iceland"]}},
    {"title": "Patagonia and the rest of South America", "for": "Daryl",
     "note": "Peru, Colombia, Chile. Argentina and Brazil done.",
     "check": {"countries": ["Peru", "Colombia", "Chile"]}},
    {"title": "Scotland", "for": "Daryl + Ivory", "note": "UK beyond London.", "check": {}},
]

data = {
    "meta": {"title": "The Shevin Travels", "updated": "2026-11-15", "home": "Miami, FL",
             "people": [{"key": "daryl", "name": "Daryl", "initial": "D"},
                        {"key": "ivory", "name": "Ivory", "initial": "I"},
                        {"key": "jaxon", "name": "Jaxon", "initial": "J"},
                        {"key": "sloane", "name": "Sloane", "initial": "S"}],
             "rules": [
                 "Florida intrastate trips are not counted.",
                 "States only driven through do not count.",
                 "Recurring destinations (Denver, Keystone, New York, Chicago, Boston, Las Vegas, New Orleans, "
                 "Maine, Asheville) are listed once, not trip by trip.",
                 "US territories (Puerto Rico) and non-UN places (Cayman Islands) are not counted as countries.",
                 "Countries are out of 195: 193 UN members plus Vatican City and Palestine.",
                 "Years marked ~ are estimates.",
             ],
             "idiotCupUrl": "https://idiotcup.github.io/"},
    "trips": rows,
    "recurring": recurring,
    "otherVisits": other_visits,
    "bucket": bucket,
}
geo = {"countries": countries, "territories": TERRITORIES, "notCounted": NOT_COUNTED, "states": states}
(ROOT / "data" / "trips.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
(ROOT / "data" / "geo.json").write_text(json.dumps(geo, indent=1, ensure_ascii=False), encoding="utf-8")
(ROOT / "data" / "seed_log.txt").write_text("\n".join(fixlog) + "\n", encoding="utf-8")
print(f"wrote {len(rows)} trips, {len(other_visits)} tracker-only visits")
print("\n".join(fixlog))
