# Kickoff prompt (paste into a new Claude Code session opened on this folder)

Build my family travel website in this folder. Read BRIEF.md (full spec), OWNER_ANSWERS.md (my answers to the open questions; they override the brief), and the files in source/ (the xlsx is the data source; the HTML dashboard is the visual reference and has pin lat/lng).

Model it on my Idiot Cup site at C:\Users\DShevin\Desktop\Idiot Cup (read-only reference; don't change it): own git repo here, master data in data/ built from the xlsx by a script in tools/, static site in docs/ for GitHub Pages, and UPDATING.md with the edit, rebuild and publish workflow. For the Idiot Cup section, link to that existing site instead of rebuilding from the stale workbook.

Steps:
1. git init. Convert the xlsx to data/trips.json with code and apply every fix in BRIEF section 5 plus OWNER_ANSWERS.
2. Compute all stats from the data and hard-code nothing. Check that visited + not visited = 195 countries and 51 states.
3. Build the BRIEF section 8 pages: dashboard cards, a zoomable world map with one pin per destination and traveler filters, a US states map, a timeline, countries, states, a searchable trip log, recurring destinations, the bucket list, and an Idiot Cup link. Use the navy/gold/cream design, keep it mobile friendly, and use no em dashes.
4. Preview it in the browser and verify that the maps, filters and numbers work.
5. Public is fine, but no birth dates or addresses. Ask me before the first GitHub push.
Batch any remaining data questions for me.
