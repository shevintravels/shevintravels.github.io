# Shevin Family Travel Website: Handoff Brief for Claude Code

## 0. Paste-ready kickoff prompt

> I want to turn my family travel tracker into a website. Read `BRIEF.md` (this file) first, then look at the files in `/source`. The Excel workbook is the source of truth for data. The HTML dashboard shows the look and feel I want, plus map pin coordinates. Before building anything, fix the data issues in section 5 and ask me the open questions in section 6. Then build in the order given in section 10. Make it easy for me to keep adding trips over time.

---

## 1. What this is

A living record of everywhere the Shevin family has traveled, built from memory plus American Airlines flight history. Fun personal project, not a product. Data is incomplete on purpose and will keep growing. The owner is Daryl, who plans to add data after sitting down with his wife.

**People tracked (four travelers):** Daryl, Ivory (wife), Jaxon (son), Sloane (daughter). Home base is Miami, FL.

**Core idea:** every trip records which of the four traveled, so the site can show "all four of us", "Daryl + Ivory", and "[name] solo" views, and per-person stats.

---

## 2. Files to put in `/source`

| File | Use |
|---|---|
| `shevin_travel_tracker_v5.xlsx` | Source of truth. Tabs: Tracker, Trip Log, Recurring Destinations, Country Summary, Bucket List, How To Use. Trip Log and Tracker are current. The other three tabs were not refreshed and may be stale. |
| `shevin_travel_dashboard_v2.html` | Visual reference. Contains the `pins` array (lat/lng per destination), color palette, layout, and zoomable D3 map code. |
| `idiot_cup_tracker.xlsx` and `idiot_cup_dashboard.html` | First versions of the separate golf trip project (section 9). Use a newer Idiot Cup workbook if one exists. |

---

## 3. Data model

One row per trip in the Trip Log. Columns:

`year, timing, destination, country, daryl, ivory, jaxon, sloane, trip_type, travelers_label, confidence, notes`

- **year**: a year, or fuzzy like `~1988`, `Early 2000s`.
- **timing**: free text like `Summer`, `Spring Break`, `Feb`, `Dec`. Exact dates do not matter to the owner.
- **who columns**: `X` yes, `-` no, `?` unknown.
- **trip_type values in use:** Golf Trip, International, Couples, Family, Sports Trip, Teen Tour, Family/Personal.
- **confidence values:** Exact, Approximate, Fuzzy, Planned.

Recommended: convert to `data/trips.json` (or CSV) with a small script that reads the xlsx, so the owner can keep editing in Excel and rebuild. All counts and charts must be computed from this data, not hard coded.

The Tracker tab is a checklist: 7 continents, 195 countries, 50 states + DC, with X columns per person and an "Any Shevin" formula. Visited items are listed first alphabetically, then not-visited alphabetically.

---

## 4. Business rules the owner set (preserve these)

1. Florida intrastate trips are excluded everywhere (Tampa, Fort Lauderdale, etc.). Footnote this on the site.
2. States only driven through do not count.
3. Booking transactions in the airline data are not trips. Several false positives were deleted.
4. Denver and Keystone (CO), New York, Chicago, Boston, Las Vegas, New Orleans, Maine, and Asheville are "recurring destinations", listed once, not catalogued trip by trip.
5. Summers in Keystone (about 5 weeks) and a 4 day July visit to Sloane's camp in Bangor, ME are recurring patterns, not individual entries to chase.
6. Approximate dates are fine. "Spring Break 2026" beats a missing date.
7. US territories (Puerto Rico) are not counted as countries.
8. Annual summer golf trip and December Pebble Beach trips are tagged "Golf Trip". Daryl's golf trips are with buddies.

---

## 5. Data issues to fix before building

These were found at the end of the conversation. Fix in the xlsx first.

1. **States count is off by two.** The Tracker has 27 visited rows (26 states + DC) and 22 not-visited rows, totaling 49 instead of 51. **Oregon and New Mexico were removed from visited and never added to the not-visited list.** Add both to not-visited. Note Oregon (Bend golf trip) is a planned 2026 trip, so confirm whether it has happened.
2. **Countries rows (197) do not match 195.** Most likely cause: Cayman Islands (visited) and Kosovo (not-visited) are not among the 195 UN recognized countries. Move them to a separate "territories / other" category, then re-audit the list against the official 195 (193 UN members plus Vatican City and Palestine as observers). Verify the final math: visited + not visited = 195.
3. **Puerto Rico 2009 trip is missing from the Trip Log.** Guys trip for Keith's bachelor party, Daryl plus friends. It appears on the dashboard map but not in the workbook. Add it, categorized as a territory.
4. **Philadelphia (May 2025, Daryl solo)** has trip_type "International" in the Trip Log by mistake. Should be domestic/solo.
5. **Rows in the dashboard or notes but not in the Trip Log:** Buffalo + Toronto (Dolphins away game), Mont Tremblant (with brother and parents), Savannah 2021 (stopover on the drive to Kiawah). Add them. Years for the Canada trips are unknown.
6. **Hard-coded numbers in the HTML dashboard are placeholders:** "80+ trips", per-person country counts (Daryl 24, Ivory 15, Jaxon 12, Sloane 8), and the timeline bars. None were computed from data. Recompute everything.
7. **The 2026 "Planned" rows are probably stale.** Father's Day 2026 (Duke, UNC, Pinehurst with Jaxon), 2026 golf trip to Bend OR, and October 2026 Lake Tahoe (Daryl + Ivory) may now have happened. Ask the owner.
8. **Stale tabs:** Recurring Destinations, Country Summary, Bucket List were not refreshed after the corrections. Regenerate them from the trip data.

---

## 6. Open questions for the owner (ask, do not guess)

1. **2021 Maui "Ivory's 45th birthday" is probably a phantom entry.** Daryl said the first Hawaii trip was Ivory's 40th (Feb 2016). The 2021 Maui row was never confirmed as a separate trip. Verify before keeping it.
2. 1993 Rome/Florence/Venice is labeled "High school trip" but that was an assumption. Confirm context.
3. The ~2002 Washington DC visit has no confirmed traveler list or trip type. Confirm who went.
4. Exact years for Buffalo/Toronto, Mont Tremblant, Indianapolis Final Four (confirmed April 2006), and the early 2000s Brazil Carnival trip.
5. Which ones should be shown publicly, if the site is shared (see section 8)?

---

## 7. Current stats (from the workbook, to be recomputed)

- Continents: 5 of 7 (missing Oceania and Antarctica)
- Countries: 28 per the Tracker (includes USA and Cayman Islands, excludes Puerto Rico). Expect this to change after the fixes in section 5.
- US states: 26 states + DC, out of 51
- Bucket list (never been): Asia, Australia and New Zealand, East Africa safari, Alaska, Eastern Europe (Daryl and Ivory), Scandinavia, Greece (Daryl and Ivory), Patagonia, Scotland, Japan (top family pick)

---

## 8. Website requirements

**Pages / sections**

1. **Dashboard home:** four metric cards in this order: Total trips, Continents (x of 7), Countries (x of 195), US states (x of 51). Each with a small progress bar.
2. **World map:** zoomable and pannable (scroll, pinch, drag, plus/minus/reset buttons). Color-coded pins by who traveled, a legend, filter buttons by traveler combo, hover tooltips listing trips for that place.
3. **US map:** state choropleth colored by who has visited (new, requested direction since the owner said states are where he has the most to add).
4. **Timeline:** trips per year, stacked by type (International, Domestic, Golf, Teen Tour).
5. **Countries:** visited list with a D / I / J / S dot per person, plus per-person counts.
6. **US states:** visited and not visited, with who visited.
7. **Trip log:** searchable, filterable table (by person, year, type).
8. **Recurring destinations** and **Bucket list** sections.
9. **Idiot Cup** golf page (section 9).

**Pin colors (from the dashboard):**

| Category | Hex |
|---|---|
| All four | `#1a5fa5` |
| Daryl + Ivory | `#7b5ea7` |
| Daryl solo | `#1a8c5f` |
| Ivory solo | `#c4416b` |
| Jaxon solo | `#d4830a` |
| Sloane solo | `#c04a1a` |
| Extended family | `#2a9d8f` |

**Known map limitation to improve:** the current map has one pin per country, so a country visited by different combinations shows only one color. Better: one pin per destination or trip, with a filter that shows a place if any trip matches. Add Daryl + Jaxon as a category if desired. US destinations (Pebble Beach, Napa, Keystone, etc.) are mostly missing from the world map and should appear on the US map.

**Design direction:** the travel dashboard uses navy (`#1a2744`), gold (`#c9a84c`), cream (`#f8f4ee`), Playfair Display for headings, DM Sans for body. Clean, editorial, not corporate. Mobile responsive. The Idiot Cup page uses forest green (`#1b3a2d`) and gold with Bebas Neue headings.

**Privacy:** this contains family and minor children's travel history. Do not put birth dates or home addresses anywhere. Host behind a password or private link (Vercel/Netlify password protection, Cloudflare Access, or basic auth). Ask the owner before making anything public.

---

## 9. Idiot Cup (separate golf trip project)

"The Idiot Cup" is the owner's name for his annual summer golf trip with buddies, since 2003. The Excel has tabs for Trip Log, Attendees, Winners & Stats, How To Use. Attendee names, winners, scores, and formats are still empty and will be added later. The dashboard has a header, zoomable map (International in gold, USA in green, upcoming lighter green), a card grid of editions, and a destination strip.

Editions:

| Year | Destination |
|---|---|
| 2003 | Myrtle Beach, SC |
| 2004 | Tunica, MS |
| 2005 | Charleston, SC |
| 2006 | Austin, TX |
| 2007 | New Orleans, LA |
| 2008 | Montreal, Canada |
| 2009 | Milwaukee, WI |
| 2010 | New Jersey |
| 2011 | Michigan |
| 2012 | Casa de Campo, Dominican Republic (CDC #1) |
| 2013 | Pinehurst, NC |
| 2014 | Whistling Straits, WI |
| 2015 | Casa de Campo, DR (CDC #2) |
| 2016 | Vail, CO |
| 2017 | San Diego, CA |
| 2018 | Pinehurst, NC |
| 2019 | TPC Sawgrass, FL |
| 2020 | Pinehurst, NC |
| 2021 | Big Cedar, MO |
| 2022 | Oconee, SC |
| 2023 | Ireland |
| 2024 | Casa de Campo, DR (CDC #3) |
| 2025 | Arcadia Bluffs, MI |
| 2026 | Bend, OR (planned, August) |

Separate from the Idiot Cup: Pebble Beach in December (2021 with Ivory, 2024 and 2025 Daryl solo). Course names in the first workbook version were partly inferred, not confirmed by the owner. Treat as "to confirm". Design the Idiot Cup page so winners, attendee leaderboards, win streaks, and attendance counts can be added once the data exists.

---

## 10. Suggested build order

1. Clean the data (section 5), convert xlsx to `trips.json`, write a script that recomputes all stats.
2. Static site (Astro or Vite) with a shared data layer. D3 or MapLibre for maps.
3. Dashboard home plus world map with filters and zoom.
4. US states map and lists.
5. Timeline, countries, trip log table.
6. Idiot Cup page.
7. Password protection and deploy.
8. Document the update workflow: edit Excel, run one command, site rebuilds.

---

## 11. Out of scope for now

The owner is also planning Spring Break 2027 (leading option: Mexico City plus Chileno Bay in Cabo). That is trip planning, not part of the travel record. A future "upcoming trip" card on the site could be nice, but do not build it unless asked.
