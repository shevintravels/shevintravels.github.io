/* The Shevin Travels. Renders everything from window.ST (docs/data.js, built by tools/build.py). */
(function () {
  const D = window.ST;
  const S = D.stats;
  const PEOPLE = D.meta.people;                 // [{key, name, initial}]
  const PKEYS = PEOPLE.map(p => p.key);
  const css = n => getComputedStyle(document.documentElement).getPropertyValue('--' + n).trim();
  const PCOLOR = { daryl: css('dsolo'), ivory: css('isolo'), jaxon: css('jsolo'), sloane: css('ssolo') };
  const CATS = [
    ['all4', 'All four'], ['extended', 'Extended family'], ['couple', 'Daryl + Ivory'], ['dj', 'Daryl + Jaxon'],
    ['dsolo', 'Daryl solo'], ['isolo', 'Ivory solo'], ['jsolo', 'Jaxon solo'], ['ssolo', 'Sloane solo'],
    ['mixed', 'Other combos']
  ].filter(([k]) => D.trips.some(t => t.cat === k));
  const CATNAME = Object.fromEntries(CATS);
  const BUCKETS = [['intl', 'International'], ['domestic', 'Domestic'], ['golf', 'Golf'], ['teen', 'Teen tours']];
  const tripById = Object.fromEntries(D.trips.map(t => [t.id, t]));
  const $ = id => document.getElementById(id);
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const when = t => [t.timing, t.year].filter(Boolean).join(' ');
  const names = who => PEOPLE.filter(p => who[p.key]).map(p => p.name).join(', ');

  function whoDots(who) {
    return '<span class="who">' + PEOPLE.map(p => {
      const v = who[p.key];
      const cls = v ? 'y' : v === null ? 'q' : '';
      const style = v ? ` style="background:${PCOLOR[p.key]}"` : '';
      return `<b class="${cls}"${style} title="${p.name}${v ? '' : v === null ? ' (unknown)' : ' (no)'}">${p.initial}</b>`;
    }).join('') + '</span>';
  }

  /* ---------- header, footer ---------- */
  const upd = new Date(D.meta.updated + 'T12:00:00');
  const updText = upd.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  $('header-sub').innerHTML = `${esc(PEOPLE.map(p => p.name).join(' · '))}  ·  <span style="color:var(--gold)">Updated ${esc(updText)}</span>`;
  $('rules').innerHTML = D.meta.rules.map(esc).join(' ');
  $('footer-line').textContent = `The Shevin Travels · ${S.trips} trips logged since ${S.firstYear} · a work in progress`;

  /* ---------- metrics ---------- */
  const pct = (a, b) => Math.round(100 * a / b);
  const metrics = [
    { href: '#trips', label: 'Unique trips', val: S.trips, denom: '', sub: `${S.allFourTrips} unique trips with all four of us`, fill: pct(S.allFourTrips, S.trips), color: css('all4') },
    { href: '#countries', label: 'Continents', val: S.continents.length, denom: `of ${S.continentsTotal}`, sub: `Still to go: ${S.continentsMissing.join(', ')}`, fill: pct(S.continents.length, 7), color: css('dsolo') },
    { href: '#countries', label: 'Countries', val: S.countries, denom: `of ${S.countriesTotal}`, sub: '193 UN + Vatican City, Palestine', fill: pct(S.countries, 195), color: css('couple') },
    { href: '#states', label: 'US states', val: S.states, denom: `of ${S.statesTotal}`, sub: '50 states + DC', fill: pct(S.states, 51), color: css('ssolo') },
  ];
  $('metrics').innerHTML = metrics.map(m => `
    <a class="metric" href="${m.href}">
      <div class="m-label">${m.label}<span class="m-go">See list &rarr;</span></div>
      <div class="m-val">${m.val}<span class="m-denom">${m.denom}</span></div>
      <div class="m-sub">${esc(m.sub)}</div>
      <div class="bar"><div style="width:${m.fill}%;background:${m.color}"></div></div>
    </a>`).join('');
  $('people').innerHTML = D.people.map(p => `
    <div class="person" aria-label="${esc(p.name)}">
      <div class="avatar" style="background:${PCOLOR[p.key]}" title="${esc(p.name)}">${p.initial}</div>
      <dl class="person-stats">
        <dt>Trips</dt><dd>${p.trips}</dd>
        <dt>Countries</dt><dd>${p.countries}</dd>
        <dt>States</dt><dd>${p.states}</dd>
        <dt>Continents</dt><dd>${p.continents.length}</dd>
      </dl>
    </div>`).join('');

  /* ---------- tooltip ---------- */
  const tip = $('tip');
  function showTip(html, ev) {
    tip.innerHTML = html;
    tip.style.display = 'block';
    const r = tip.getBoundingClientRect();
    let x = ev.clientX + 14, y = ev.clientY + 14;
    if (x + r.width > innerWidth - 8) x = Math.max(8, ev.clientX - r.width - 14);
    if (y + r.height > innerHeight - 8) y = Math.max(8, ev.clientY - r.height - 14);
    tip.style.left = x + 'px';
    tip.style.top = y + 'px';
  }
  const hideTip = () => { tip.style.display = 'none'; };
  document.addEventListener('pointerdown', e => { if (!e.target.closest('.pin, .state')) hideTip(); });
  addEventListener('scroll', hideTip, { passive: true });
  const tripLine = t => `<div class="t-row"><i style="background:${css(t.cat)}"></i><span>${esc(when(t))}: ${esc(t.destination)} <span class="t-who">(${esc(t.travelers)})</span></span></div>`;

  /* ---------- places (one pin per destination) ---------- */
  function groupPlaces(filterUS) {
    const m = new Map();
    D.trips.forEach(t => t.places.forEach(p => {
      if (filterUS !== undefined && (p.country === 'United States') !== filterUS) return;
      if (!m.has(p.name)) m.set(p.name, { ...p, trips: [] });
      m.get(p.name).trips.push(t);
    }));
    return [...m.values()];
  }

  function zoomable(wrap, svg, g, onZoom) {
    const zoom = d3.zoom().scaleExtent([1, 14]).on('zoom', e => { g.attr('transform', e.transform); onZoom(e.transform.k); });
    svg.call(zoom).on('dblclick.zoom', null);
    wrap.querySelectorAll('[data-zoom]').forEach(b => b.addEventListener('click', () => {
      const a = b.dataset.zoom;
      if (a === 'reset') svg.transition().duration(400).call(zoom.transform, d3.zoomIdentity);
      else svg.transition().duration(250).call(zoom.scaleBy, a === 'in' ? 1.6 : 1 / 1.6);
    }));
  }

  function filterBar(el, items, onPick) {
    el.innerHTML = items.map(it => it.label
      ? `<span class="group-label">${it.label}</span>`
      : `<button type="button" class="fbtn${it.on ? ' on' : ''}" data-k="${it.k}">${it.color ? `<span class="dot" style="background:${it.color}"></span>` : ''}${esc(it.text)}</button>`).join('');
    el.addEventListener('click', e => {
      const b = e.target.closest('.fbtn');
      if (!b) return;
      el.querySelectorAll('.fbtn').forEach(x => x.classList.toggle('on', x === b));
      onPick(b.dataset.k);
    });
  }

  function matcher(k) {
    if (k === 'all') return () => true;
    if (k.startsWith('p:')) { const p = k.slice(2); return t => !!t.who[p]; }
    return t => t.cat === k;
  }

  const mapFail = (wrap, msg) => { wrap.insertAdjacentHTML('beforeend', `<div class="map-status">${msg}</div>`); };

  /* ---------- world map ---------- */
  (function world() {
    const wrap = $('world-map');
    let filt = 'all', k = 1;
    filterBar($('world-filters'), [
      { label: 'Who went' }, { k: 'all', text: 'All trips', on: true },
      ...CATS.map(([c, n]) => ({ k: c, text: n, color: css(c) })),
      { label: 'Anyone with' }, ...PEOPLE.map(p => ({ k: 'p:' + p.key, text: p.name }))
    ], v => { filt = v; draw(); });
    $('world-legend').innerHTML = CATS.map(([c, n]) => `<span><i style="background:${css(c)}"></i>${n}</span>`).join('') +
      `<span><i style="background:#fff;border:2px solid ${css('gold')}"></i>Gold ring: more than one trip</span>` +
      `<span><i class="sq" style="background:#f0dfae"></i>Country visited</span>`;

    const W = 960, H = 480;
    const svg = d3.select(wrap).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('preserveAspectRatio', 'xMidYMid meet');
    const g = svg.append('g');
    const proj = d3.geoNaturalEarth1().scale(175).translate([W / 2, H / 2 + 20]);
    const path = d3.geoPath(proj);
    const landG = g.append('g'), pinG = g.append('g');
    const visitedIso = new Set(D.countries.filter(c => c.visited && c.iso).map(c => c.iso));
    const all = groupPlaces();

    function draw() {
      const m = matcher(filt);
      const pts = all.filter(p => p.trips.some(m))
        .map(p => ({ ...p, hit: p.trips.filter(m) }))
        .sort((a, b) => b.hit.length - a.hit.length);
      const sel = pinG.selectAll('circle').data(pts, d => d.name);
      sel.exit().remove();
      sel.enter().append('circle').attr('class', 'pin')
        .on('pointerenter click', (e, d) => showTip(`<strong>${esc(d.name)}${d.territory ? ' (territory)' : ''}</strong>` + d.hit.map(tripLine).join(''), e))
        .on('pointerleave', e => { if (e.pointerType === 'mouse') hideTip(); })
        .merge(sel)
        .attr('cx', d => proj([d.lng, d.lat])[0]).attr('cy', d => proj([d.lng, d.lat])[1])
        .attr('fill', d => css(d.hit[d.hit.length - 1].cat))
        .classed('multi', d => d.hit.length > 1);
      resize();
    }
    function resize() {
      pinG.selectAll('circle')
        .attr('r', d => (d.country === 'United States' ? 3.2 : 4.6) / Math.sqrt(k))
        .attr('stroke-width', d => (d.hit.length > 1 ? 1.8 : 1) / Math.sqrt(k));
    }
    zoomable(wrap, svg, g, kk => { k = kk; resize(); landG.selectAll('path').attr('stroke-width', .5 / kk); });

    fetch('https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-110m.json').then(r => r.json()).then(w => {
      landG.selectAll('path').data(topojson.feature(w, w.objects.countries).features).enter().append('path')
        .attr('class', d => 'land' + (visitedIso.has(String(d.id).padStart(3, '0')) ? ' visited' : '')).attr('d', path);
      // faded world map behind the page header (visited countries tinted gold)
      const hw = d3.select('#header-map'), feats = topojson.feature(w, w.objects.countries).features.filter(f => f.id !== '010');
      const hp = d3.geoPath(d3.geoNaturalEarth1().fitSize([960, 440], { type: 'FeatureCollection', features: feats }));
      hw.selectAll('path').data(feats).enter().append('path').attr('d', hp)
        .attr('class', d => visitedIso.has(String(d.id).padStart(3, '0')) ? 'hm-v' : 'hm');
    }).catch(() => mapFail(wrap, 'Map outline could not load (offline?). Pins still work.'));
    draw();
  })();

  /* ---------- US map ---------- */
  (function usa() {
    const wrap = $('us-map');
    let mode = 'all', k = 1;
    const ramp = ['#e6e1d6', '#cad7ea', '#93b3da', '#5385c0', css('all4')];
    const stateBy = Object.fromEntries(D.states.map(s => [s.fips, s]));
    filterBar($('us-filters'), [
      { k: 'all', text: 'Everyone', on: true }, ...PEOPLE.map(p => ({ k: 'p:' + p.key, text: p.name, color: PCOLOR[p.key] }))
    ], v => { mode = v; paint(); });

    const W = 960, H = 600;
    const svg = d3.select(wrap).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('preserveAspectRatio', 'xMidYMid meet');
    const g = svg.append('g');
    const proj = d3.geoAlbersUsa().scale(1160).translate([W / 2, H / 2]);
    const path = d3.geoPath(proj);
    const stG = g.append('g'), pinG = g.append('g');
    const places = groupPlaces(true);
    const recur = [];
    D.recurring.forEach(r => r.places.forEach(p => recur.push({ ...p, rec: r })));

    function stateTip(s) {
      const trips = s.trips.map(id => tripById[id]);
      const rec = s.recurring.map(i => D.recurring[i].name);
      const other = s.other.map(i => D.otherVisits[i].note);
      return `<strong>${esc(s.name)}</strong>` +
        (s.visited ? `<div class="t-who">Been: ${esc(names(s.who)) || 'nobody yet'}</div>` : '<div class="t-who">Not yet visited</div>') +
        trips.slice(-8).map(tripLine).join('') + (trips.length > 8 ? `<div class="t-who">+ ${trips.length - 8} earlier trips</div>` : '') +
        (rec.length ? `<div class="t-who">Recurring: ${esc(rec.join(', '))}</div>` : '') +
        (other.length ? `<div class="t-who">Also: ${esc(other.join('; '))}</div>` : '');
    }
    function fill(s) {
      if (!s) return ramp[0];
      if (mode === 'all') return ramp[PKEYS.filter(p => s.who[p]).length];
      const p = mode.slice(2);
      return s.who[p] ? PCOLOR[p] : ramp[0];
    }
    function paint() {
      stG.selectAll('path').attr('fill', d => fill(stateBy[String(d.id).padStart(2, '0')]));
      const m = matcher(mode);
      const pts = places.map(p => ({ ...p, hit: p.trips.filter(m) })).filter(p => p.hit.length && proj([p.lng, p.lat]));
      const sel = pinG.selectAll('circle').data(pts, d => d.name);
      sel.exit().remove();
      sel.enter().append('circle').attr('class', 'pin')
        .on('pointerenter click', (e, d) => { e.stopPropagation(); showTip(`<strong>${esc(d.name)}</strong>` + d.hit.map(tripLine).join(''), e); })
        .on('pointerleave', e => { if (e.pointerType === 'mouse') hideTip(); })
        .merge(sel)
        .attr('cx', d => proj([d.lng, d.lat])[0]).attr('cy', d => proj([d.lng, d.lat])[1])
        .attr('fill', d => css(d.hit[d.hit.length - 1].cat)).classed('multi', d => d.hit.length > 1);
      const rp = recur.filter(r => mode === 'all' || r.rec.who[mode.slice(2)]).filter(r => proj([r.lng, r.lat]));
      const rs = pinG.selectAll('rect').data(rp, d => d.name);
      rs.exit().remove();
      rs.enter().append('rect').attr('class', 'pin')
        .on('pointerenter click', (e, d) => { e.stopPropagation(); showTip(`<strong>${esc(d.rec.name)} (recurring)</strong><div>${esc(d.rec.frequency)}</div><div class="t-who">Been: ${esc(names(d.rec.who))}</div>`, e); })
        .on('pointerleave', e => { if (e.pointerType === 'mouse') hideTip(); })
        .merge(rs).attr('fill', css('gold'));
      size();
      const counts = [1, 2, 3, 4].map(n => D.states.filter(s => PKEYS.filter(p => s.who[p]).length === n).length);
      $('us-legend').innerHTML = mode === 'all'
        ? ['Not yet', '1 of us', '2 of us', '3 of us', 'All 4'].map((l, i) => `<span><i class="sq" style="background:${ramp[i]}"></i>${l}${i ? ` (${counts[i - 1]})` : ''}</span>`).join('') +
          `<span><i style="background:${css('gold')};border-radius:2px;transform:rotate(45deg) scale(.8)"></i>Recurring</span>`
        : `<span><i class="sq" style="background:${PCOLOR[mode.slice(2)]}"></i>${PEOPLE.find(p => 'p:' + p.key === mode).name} has been (${D.states.filter(s => s.who[mode.slice(2)]).length})</span><span><i class="sq" style="background:${ramp[0]}"></i>Not yet</span>`;
    }
    function size() {
      const r = 4 / Math.sqrt(k), q = 9 / Math.sqrt(k);
      pinG.selectAll('circle').attr('r', r).attr('stroke-width', d => (d.hit.length > 1 ? 1.6 : 1) / Math.sqrt(k));
      pinG.selectAll('rect').attr('width', q).attr('height', q).attr('stroke-width', 1 / Math.sqrt(k))
        .attr('transform', d => { const [x, y] = proj([d.lng, d.lat]); return `translate(${x},${y}) rotate(45) translate(${-q / 2},${-q / 2})`; });
    }
    zoomable(wrap, svg, g, kk => { k = kk; size(); stG.selectAll('path').attr('stroke-width', .8 / kk); });

    fetch('https://cdn.jsdelivr.net/npm/us-atlas@3.0.1/states-10m.json').then(r => r.json()).then(us => {
      const feats = topojson.feature(us, us.objects.states).features.filter(f => stateBy[String(f.id).padStart(2, '0')]);
      stG.selectAll('path').data(feats).enter().append('path').attr('class', 'state').attr('d', path)
        .on('pointerenter click', (e, d) => showTip(stateTip(stateBy[String(d.id).padStart(2, '0')]), e))
        .on('pointerleave', e => { if (e.pointerType === 'mouse') hideTip(); });
      paint();
    }).catch(() => mapFail(wrap, 'State outlines could not load (offline?).'));
    paint();
  })();

  /* ---------- timeline ---------- */
  $('tl-legend').innerHTML = BUCKETS.map(([b, n]) => `<span><i class="sq" style="background:${css(b)}"></i>${n} (${D.trips.filter(t => t.bucket === b).length})</span>`).join('');
  const maxN = Math.max(...D.timeline.map(r => BUCKETS.reduce((a, [b]) => a + r[b], 0)));
  $('tl').innerHTML = [...D.timeline].sort((a, b) => b.year - a.year).map(r => {
    const n = BUCKETS.reduce((a, [b]) => a + r[b], 0);
    return `<div class="tl-row"><div class="tl-year">${r.year}</div><div class="tl-track">` +
      // one equal block per trip, grouped by kind
      BUCKETS.flatMap(([b, nm]) => D.trips.filter(t => t.yearSort === r.year && t.bucket === b).map(t =>
        `<div class="tl-seg" title="${esc(t.year)}: ${esc(t.destination)} (${nm})" style="width:calc((100% - ${maxN - 1} * 3px) / ${maxN});background:${css(b)}"></div>`)).join('') +
      `</div><div class="tl-count">${n}</div></div>`;
  }).join('');

  /* ---------- countries ---------- */
  const visitedC = D.countries.filter(c => c.visited);
  $('country-chips').innerHTML = `<span class="chip"><strong>${S.countries}</strong>of 195</span>` +
    D.people.map(p => `<span class="chip"><strong>${p.countries}</strong>${p.name}</span>`).join('');
  const conts = [...new Set(D.countries.map(c => c.continent))].sort();   // every continent with countries (Antarctica has none)
  const cRow = c => {
    const n = c.trips.length;
    return `<div class="item"><span>${esc(c.name)}</span><span class="meta">${n} trip${n === 1 ? '' : 's'}</span>${whoDots(c.who)}</div>`;
  };
  const EAST_EU = new Set(['Albania', 'Belarus', 'Bosnia and Herzegovina', 'Bulgaria', 'Croatia', 'Czech Republic', 'Estonia',
    'Hungary', 'Latvia', 'Lithuania', 'Moldova', 'Montenegro', 'North Macedonia', 'Poland', 'Romania', 'Russia', 'Serbia',
    'Slovakia', 'Slovenia', 'Ukraine']);
  $('country-list').innerHTML = conts.map(ct => {
    const list = visitedC.filter(c => c.continent === ct);
    let body = list.length ? list.map(cRow).join('') : '<div class="item"><span class="meta">None yet</span></div>';
    if (ct === 'Europe') {
      const euAll = D.countries.filter(c => c.continent === 'Europe');
      body = [['Western Europe', c => !EAST_EU.has(c.name)], ['Eastern Europe', c => EAST_EU.has(c.name)]]
        .map(([nm, f]) => [nm, list.filter(f), euAll.filter(f).length])
        .filter(([, l]) => l.length)
        .map(([nm, l, of]) => `<div class="sub-head">${nm} (${l.length} of ${of})</div>` + l.map(cRow).join('')).join('');
    }
    return `<div class="cont-head">${ct} (${list.length} of ${D.countries.filter(c => c.continent === ct).length})</div>` + body;
  }).join('');
  const notYet = D.countries.filter(c => !c.visited);
  $('country-extra').innerHTML =
    (S.territories.length ? `<div class="cont-head">Territories (not counted)</div>` + S.territories.map(t =>
      `<div class="item"><span>${esc(t.name)}</span><span class="meta">${esc(t.of)}</span>${whoDots(t.who)}</div>`).join('') : '') +
    `<details><summary>${notYet.length} countries still to go</summary><p>${notYet.map(c => esc(c.name)).join(', ')}</p></details>` +
    `<p class="footnote">Out of 195: the 193 UN members plus Vatican City and Palestine. ${D.notCounted.map(n => n.name).join(' and ')} are not counted.</p>`;

  /* ---------- states ---------- */
  const visitedS = D.states.filter(s => s.visited);
  $('state-chips').innerHTML = `<span class="chip"><strong>${S.states}</strong>of 51</span>` +
    D.people.map(p => `<span class="chip"><strong>${p.states}</strong>${p.name}</span>`).join('');
  $('state-list').innerHTML = `<div class="cont-head">Visited (${visitedS.length})</div>` +
    visitedS.map(s => {
      const bits = [];
      if (['CO', 'FL', 'NY', 'IL', 'ME', 'MA', 'NV', 'NC', 'LA'].includes(s.abbr)) bits.push('recurring');
      else {
        if (s.trips.length) bits.push(`${s.trips.length} trip${s.trips.length === 1 ? '' : 's'}`);
        if (s.recurring.length) bits.push('recurring');
      }
      if (!bits.length && s.other.length) bits.push(s.abbr === 'FL' ? 'home' : 'no trip logged');
      return `<div class="item"><span>${esc(s.name)}</span><span class="meta">${bits.join(', ')}</span>${whoDots(s.who)}</div>`;
    }).join('') +
    `<div class="cont-head" style="margin-top:16px">Not yet (${D.states.length - visitedS.length})</div>` +
    D.states.filter(s => !s.visited).map(s =>
      `<div class="item"><span>${esc(s.name)}</span><span class="meta"></span>${whoDots({})}</div>`).join('') +
    `<p class="footnote">Florida trips are not logged (home state). States only driven through do not count.</p>`;

  /* ---------- trip log ---------- */
  const fp = $('f-person'), fy = $('f-year'), ft = $('f-type'), q = $('q');
  fp.innerHTML = `<option value="">Anyone</option>` + PEOPLE.map(p => `<option value="${p.key}">${p.name}</option>`).join('') + `<option value="all4">All four</option>`;
  const years = [...new Set(D.trips.map(t => t.yearSort))].sort((a, b) => b - a);
  fy.innerHTML = `<option value="">All years</option>` + years.map(y => `<option>${y}</option>`).join('');
  const types = [...new Set(D.trips.map(t => t.type))].sort();
  ft.innerHTML = `<option value="">All types</option>` + types.map(t => `<option>${esc(t)}</option>`).join('');
  const hay = t => [t.year, t.timing, t.destination, t.travelers, t.type, t.notes, ...t.places.map(p => p.name + ' ' + (p.country || p.territory) + ' ' + (p.state || ''))].join(' ').toLowerCase();
  function renderLog() {
    const terms = q.value.toLowerCase().split(/\s+/).filter(Boolean);
    const rows = D.trips.filter(t =>
      (!fp.value || (fp.value === 'all4' ? PKEYS.every(p => t.who[p]) : t.who[fp.value])) &&
      (!fy.value || t.yearSort === +fy.value) && (!ft.value || t.type === ft.value) &&
      terms.every(w => hay(t).includes(w))).slice().reverse();
    $('log-count').textContent = `${rows.length} of ${D.trips.length} trips`;
    $('log').innerHTML = `<thead><tr><th>When</th><th>Where</th><th>Who</th><th>Type</th></tr></thead><tbody>` +
      rows.map(t => `<tr>
        <td class="yr">${esc(t.year)}${(() => {
          const sub = [t.timing, t.approxYear ? 'estimate' : t.confidence !== 'Exact' ? t.confidence.toLowerCase() : ''].filter(Boolean).join(' · ');
          return sub ? `<div class="note">${esc(sub)}</div>` : '';
        })()}</td>
        <td><div class="dest">${esc(t.destination)}</div>${t.notes ? `<div class="note">${esc(t.notes)}</div>` : ''}</td>
        <td>${whoDots(t.who)}${t.others ? `<div class="note">${esc(t.others)}</div>` : ''}</td>
        <td><span class="tag" style="background:${css(t.bucket)}">${esc(t.type)}</span>${t.idiotCup ? '<div class="conf">Idiot Cup</div>' : ''}</td>
      </tr>`).join('') + `</tbody>`;
    if (!rows.length) $('log').innerHTML += `<tbody><tr><td colspan="4" class="note">No trips match.</td></tr></tbody>`;
  }
  [q, fp, fy, ft].forEach(el => el.addEventListener('input', renderLog));
  renderLog();

  /* ---------- bucket ---------- */
  // one tile per person; an item shows on the tile of everyone listed in its `who`
  $('bucket-grid').innerHTML = PEOPLE.map(p => {
    const items = D.bucket.filter(b => b.who.includes(p.key));
    return `<div class="bl-tile" style="border-top-color:${PCOLOR[p.key]}">
      <div class="bl-head"><div class="avatar sm" style="background:${PCOLOR[p.key]}">${p.initial}</div><div class="bl-name">${esc(p.name)}</div></div>
      ${items.length ? `<ul class="bl-list">${items.map(b => `<li><div class="bl-item">${esc(b.title)}</div>` +
        (b.note ? `<div class="bl-note">${esc(b.note)}</div>` : '') +
        (b.doneBy[p.key] ? `<div class="warn">Already been: ${esc(b.doneBy[p.key].join(', '))}</div>` : '') + `</li>`).join('')}</ul>`
        : '<div class="bl-note">Coming soon</div>'}
    </div>`;
  }).join('');

  /* ---------- Idiot Cup ---------- */
  const ic = D.trips.filter(t => t.idiotCup).sort((a, b) => b.yearSort - a.yearSort);
  const icName = t => t.destination.includes('Casa de Campo') ? 'Casa de Campo'
    : t.destination.includes('Oconee') ? 'Oconee, GA'
    : t.destination.replace(/\s*\(.*\)$/, '').replace(', golf trip', '');
  $('ic-strip').innerHTML = ic.map(t => `<div class="ic-ed"><div class="y">${t.year}</div>${esc(icName(t))}</div>`).join('');

  /* ---------- nav highlight ---------- */
  const links = [...document.querySelectorAll('.nav a')];
  const io = new IntersectionObserver(es => es.forEach(e => {
    if (e.isIntersecting) links.forEach(a => a.classList.toggle('on', a.getAttribute('href') === '#' + e.target.id));
  }), { rootMargin: '-45% 0px -50% 0px' });
  links.forEach(a => { const s = document.querySelector(a.getAttribute('href')); if (s) io.observe(s); });
})();
