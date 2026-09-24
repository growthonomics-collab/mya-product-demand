async function boot(){
const D = JSON.parse(document.getElementById('data').textContent);
const M = D.months, NM = M.length;
const fmt = n => Math.round(n).toLocaleString('en-GB');
const eur = n => '€' + fmt(n);
const pct = n => n.toFixed(n >= 10 ? 1 : 2);
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const mlabel = k => { const [y, m] = k.split('-'); return MON[+m - 1] + ' ' + y; };
const W = D.weights;
const PL = D.products; const P = {}; PL.forEach(o => { P[o.pid] = o; o.url = 'https://myacollection.com/products/' + o.slug; });
const HUBS = D.hubs.slice(); const HUB = {}; HUBS.forEach(h => HUB[h.id] = h);
D.type_hubs.forEach(t => { const h = {id: 'type:' + t, label: 'All ' + t.toLowerCase(), title: t, group: 'Product types (live and past products)', kind: 'type', nav: false, live_members: [], n_live: 0, pv: new Array(NM).fill(0), pu: new Array(NM).fill(0), pk: new Array(NM).fill(0), pim: new Array(NM).fill(0)}; HUBS.push(h); HUB[h.id] = h; });
const sum = (arr, a, b) => { let s = 0; for (let i = a; i <= b; i++) s += arr[i] || 0; return s; };
const tierOf = x => x >= 3 ? 'Hero' : x >= 1.5 ? 'Strong' : x >= 0.5 ? 'Average' : 'Low';
const img = (o, w) => o.img ? o.img + (o.img.includes('?') ? '&' : '?') + 'width=' + w : '';
const thumb = o => o.img ? `<img class="thumb" src="${esc(img(o, 120))}" alt="" loading="lazy" width="44" height="56">` : `<span class="thumb thumb-x" aria-hidden="true">${esc((o.name||'?')[0])}</span>`;
const tierPill = t => `<span class="tier tier-${t.replace(' ','-')}">${t}</span>`;
const trendPill = tr => tr ? `<span class="trend trend-${tr}">${tr === 'Rising' ? '↑ ' : tr === 'Fading' ? '↓ ' : tr === 'New' ? '✦ ' : '→ '}${tr}</span>` : '';
const liveChip = o => o.live ? '' : '<span class="chip gone">Not on site</span>';
const stockChip = o => !o.live ? '' : o.instock === 0 ? '<span class="chip out">Sold out</span>' : o.instock < 50 ? `<span class="chip">${Math.round(o.instock)}% of sizes in stock</span>` : '';
function chips(o){ return [o.type, o.season, o.colour, o.price ? eur(o.price) : '', o.limited ? 'Limited' : ''].filter(Boolean).map(v => `<span class="chip">${esc(v)}</span>`).join('') + stockChip(o) + liveChip(o); }

// ---------- period state
let A = M.indexOf('2026-07'), Bi = NM - 1;
const preset = $('#preset'); D.seasons.forEach(s => { const o = document.createElement('option'); o.value = s.id; o.textContent = s.label; preset.appendChild(o); });
const custom = document.createElement('option'); custom.value = 'custom'; custom.textContent = 'Custom range'; preset.appendChild(custom);
[$('#mfrom'), $('#mto')].forEach(sel => M.forEach((k, i) => { const o = document.createElement('option'); o.value = i; o.textContent = mlabel(k); sel.appendChild(o); }));
function setRange(a, b, fromPreset){ if (a > b) [a, b] = [b, a]; A = a; Bi = b; $('#mfrom').value = a; $('#mto').value = b; if (!fromPreset) { const s = D.seasons.find(s => M.indexOf(s.a) === a && M.indexOf(s.b) === b); preset.value = s ? s.id : 'custom'; } try { localStorage.setItem('mya-range', a + ',' + b); } catch(e) {} renderAll(); }
preset.addEventListener('change', () => { const s = D.seasons.find(x => x.id === preset.value); if (s) setRange(M.indexOf(s.a), M.indexOf(s.b), true); });
$('#mfrom').addEventListener('change', () => setRange(+$('#mfrom').value, Bi)); $('#mto').addEventListener('change', () => setRange(A, +$('#mto').value));
try { const r = localStorage.getItem('mya-range'); if (r) { const [a, b] = r.split(',').map(Number); if (a >= 0 && b < NM) { A = a; Bi = b; } } } catch(e) {}

// ---------- scoring for a range
function metrics(o, a, b){
  const hasK = M.slice(a, b + 1).some(k => k >= D.coverage.gsc_from && k <= D.coverage.gsc_to);
  let V = sum(o.v, a, b), U = sum(o.u, a, b), S = sum(o.s, a, b), E = sum(o.e, a, b), K = hasK ? sum(o.k, a, b) : 0, IM = sum(o.im, a, b), Aa = sum(o.a, a, b), Bp = sum(o.b, a, b), R = sum(o.r, a, b);
  const len = b - a + 1; let status = 'Established', scale = 1, active = len;
  if (o.first !== null && o.first > a && o.first <= b) { active = b - o.first + 1; scale = len / active; status = 'New in period'; }
  return {V, U, S, E, K, IM, A: Aa, B: Bp, R, Vraw: V, status, scale, active, sV: V * scale, sU: U * scale, sE: E * scale, sK: K * scale, sA: Aa * scale};
}
function members(h, a, b, MX){
  const includesNow = b === NM - 1;
  const set = new Set();
  if (h.id === 'all') { PL.forEach(o => { if (MX[o.pid].V > 0 || (includesNow && o.live)) set.add(o.pid); }); return [...set]; }
  if (h.kind === 'type') { PL.forEach(o => { if (o.type === h.title && (MX[o.pid].V > 0 || (includesNow && o.live))) set.add(o.pid); }); return [...set]; }
  h.live_members.forEach(pid => { if (MX[pid] && (MX[pid].V > 0 || includesNow)) set.add(pid); });
  PL.forEach(o => { const ob = o.obs[h.id]; if (ob && sum(ob, a, b) > 0) set.add(o.pid); });
  return [...set];
}
function scoreHub(h, a, b, MX){
  const mem = members(h, a, b, MX); const n = mem.length; if (!n) return {n: 0, rows: [], tot: {}};
  const keys = [['sV','views'],['sU','users'],['sE','engs'],['sK','clicks'],['sA','atc']];
  const tot = {}; keys.forEach(([k]) => tot[k] = mem.reduce((s, pid) => s + MX[pid][k], 0));
  const used = keys.reduce((s, [k, w]) => s + (tot[k] > 0 ? W[w] : 0), 0) || 1;
  const rows = mem.map(pid => { const m = MX[pid]; let sc = 0; keys.forEach(([k, w]) => { if (tot[k] > 0) sc += W[w] * m[k] / tot[k] * 100; }); sc /= used; let ratio = sc * n / 100, prov = false;
    if (m.status !== 'Established') { ratio = (m.Vraw * ratio + 100 * 1.5) / (m.Vraw + 100); prov = m.Vraw < 100; }
    return {pid, score: sc, ratio, prov}; });
  rows.sort((x, y) => y.ratio - x.ratio); rows.forEach((r, i) => r.rank = i + 1);
  const T = {V: 0, U: 0, E: 0, K: 0, A: 0, B: 0, R: 0, IM: 0, S: 0}; mem.forEach(pid => { const m = MX[pid]; Object.keys(T).forEach(k => T[k] += m[k]); });
  return {n, rows, tot: T, nodata: mem.filter(pid => MX[pid].V === 0).length};
}
function compute(a, b){
  const MX = {}; PL.forEach(o => MX[o.pid] = metrics(o, a, b));
  const HS = {}; HUBS.forEach(h => HS[h.id] = scoreHub(h, a, b, MX));
  return {MX, HS};
}
let CUR = null, PREV = null;
function mainHubId(o){ return HUB[o.hub] ? o.hub : (HUB['type:' + o.type] ? 'type:' + o.type : 'all'); }
function renderAll(){
  const a = A, b = Bi, len = b - a + 1;
  CUR = compute(a, b);
  PREV = (a - len >= 0) ? compute(a - len, a - 1) : null;
  // per-product summary for the period
  PL.forEach(o => { const m = CUR.MX[o.pid]; const hid = mainHubId(o); const hs = CUR.HS[hid]; const row = hs.rows.find(r => r.pid === o.pid);
    o.m = m; o.hubId = hid; o.hub_label = HUB[hid].label; o.ratio = row ? row.ratio : 0; o.rank = row ? row.rank : 0; o.score = row ? row.score : 0; o.prov = row ? row.prov : false; o.nhub = hs.n;
    o.tier = !row || m.V === 0 ? 'No data' : (o.prov ? 'New' : tierOf(o.ratio));
    let rp = 0; if (PREV) { const prow = PREV.HS[hid].rows.find(r => r.pid === o.pid); if (prow && PREV.MX[o.pid].V > 0) rp = prow.ratio; }
    o.ratio_prev = rp; o.mom = rp ? o.ratio / rp : null;
    o.trend = m.V === 0 ? '' : m.status !== 'Established' ? 'New' : !rp ? 'New' : o.mom >= 1.25 ? 'Rising' : o.mom <= 0.8 ? 'Fading' : 'Steady';
    o.placements = HUBS.filter(h => h.id !== 'all' && h.kind !== 'type' && h.id !== hid).map(h => { const r = CUR.HS[h.id].rows.find(r => r.pid === o.pid); return r ? [h.id, r.rank, r.ratio, CUR.HS[h.id].n] : null; }).filter(Boolean).sort((x, y) => x[1] - y[1]);
  });
  const active = PL.filter(o => o.m.V > 0);
  $('#pbsum').innerHTML = `<b>${mlabel(M[a])}${a !== b ? ' to ' + mlabel(M[b]) : ''}</b> · ${len} month${len > 1 ? 's' : ''} · ${fmt(active.reduce((s, o) => s + o.m.V, 0))} product views · ${fmt(active.length)} products with traffic${PREV ? ` · momentum vs ${mlabel(M[a - len])}${len > 1 ? ' to ' + mlabel(M[a - 1]) : ''}` : ' · no earlier period for momentum'}`;
  renderPeriodChart();
  const hasK = M.slice(a, b + 1).some(k => k >= D.coverage.gsc_from && k <= D.coverage.gsc_to);
  $('#totals').innerHTML = [['Product page views', active.reduce((s, o) => s + o.m.V, 0)], ['Products with traffic', active.length], ['Not on site any more', active.filter(o => !o.live).length], [hasK ? 'Organic clicks (products)' : 'Organic clicks', hasK ? active.reduce((s, o) => s + o.m.K, 0) : 'n/a'], ['Add-to-cart', active.reduce((s, o) => s + o.m.A, 0)], ['Purchases (items)', active.reduce((s, o) => s + o.m.B, 0)]]
    .map(([l, v]) => `<div><b class="num">${typeof v === 'number' ? fmt(v) : v}</b><span>${l}</span></div>`).join('');
  const nnew = PL.filter(o => o.m.status !== 'Established' && o.m.V > 0).length;
  $('#newstats').textContent = `In this period: ${fmt(active.length)} products with traffic, ${fmt(nnew)} of them first seen inside the period (scaled and blended with the 1.50 prior), ${fmt(active.filter(o => !o.live).length)} no longer on the store.`;
  renderHub(); renderBCG(); renderTable(); renderMap(); renderColls(); renderAttr(); renderMethod(); renderSeasons();
}

// ---------- period bar chart
function renderPeriodChart(){
  const el = $('#pbchart'); const max = Math.max(...D.monthly_total); const Wd = 1100, H = 54, bw = Wd / NM;
  let s = `<svg viewBox="0 0 ${Wd} ${H + 16}" preserveAspectRatio="none" style="height:70px">`;
  D.monthly_total.forEach((v, i) => { const h = Math.max(1, v / max * H); const inr = i >= A && i <= Bi; s += `<rect class="pbar${inr ? ' in' : ''}" data-i="${i}" x="${(i * bw + 1).toFixed(1)}" y="${(H - h).toFixed(1)}" width="${(bw - 2).toFixed(1)}" height="${h.toFixed(1)}"/>`; if (M[i].endsWith('-01')) s += `<text class="tick" x="${(i * bw + 2).toFixed(1)}" y="${H + 13}">${M[i].slice(0, 4)}</text>`; });
  s += '</svg>'; el.innerHTML = s;
  let pending = null;
  el.querySelectorAll('.pbar').forEach(r => { r.addEventListener('click', () => { const i = +r.dataset.i; if (pending === null) { pending = i; setRange(i, i); } else { setRange(pending, i); pending = null; } });
    r.addEventListener('mousemove', e => showTT(e, `<b>${mlabel(M[+r.dataset.i])}</b>${fmt(D.monthly_total[+r.dataset.i])} product page views<br>Click to start a range, click a second month to end it`)); r.addEventListener('mouseleave', hideTT); });
}

// ---------- tabs, tooltip, bar chart
document.querySelectorAll('nav.tabs button').forEach(b => b.addEventListener('click', () => { document.querySelectorAll('nav.tabs button').forEach(x => x.setAttribute('aria-selected', x === b)); document.querySelectorAll('section[role=tabpanel]').forEach(s => s.hidden = s.id !== b.getAttribute('aria-controls')); try { localStorage.setItem('mya-tab', b.id); } catch(e) {} }));
try { const t = localStorage.getItem('mya-tab'); if (t && $('#' + t)) $('#' + t).click(); } catch(e) {}
const tt = $('#tt');
function showTT(e, html){ tt.innerHTML = html; tt.style.display = 'block'; const w = tt.offsetWidth, h = tt.offsetHeight; let x = e.clientX + 14, y = e.clientY + 14; if (x + w > innerWidth - 8) x = e.clientX - w - 14; if (y + h > innerHeight - 8) y = e.clientY - h - 14; tt.style.left = x + 'px'; tt.style.top = y + 'px'; }
function hideTT(){ tt.style.display = 'none'; }
function hbar(el, rows, opts){
  const {label, value, valueText, tip, hi} = opts; const rowH = 30, labelW = opts.labelW || 215, valW = 64, Wd = 640, x0 = labelW, plotW = Wd - labelW - valW; const max = Math.max(...rows.map(value)) || 1; const H = rows.length * rowH + 6;
  let s = `<svg viewBox="0 0 ${Wd} ${H}" role="img" aria-label="${esc(opts.aria || 'bar chart')}">`;
  rows.forEach((r, i) => { const y = i * rowH + 3, w = Math.max(2, plotW * value(r) / max); const name = label(r), short = name.length > 28 ? name.slice(0, 27) + '…' : name;
    s += `<g class="row" data-i="${i}"><text class="lbl" x="${x0 - 10}" y="${y + 18}" text-anchor="end">${esc(short)}</text><rect class="bar-bg" x="${x0}" y="${y + 5}" width="${plotW}" height="16" rx="3"/><rect class="bar${hi && hi(r) ? ' hi' : ''}" x="${x0}" y="${y + 5}" width="${w}" height="16" rx="3"/><text class="val num" x="${x0 + w + 8}" y="${y + 18}">${esc(valueText(r))}</text><rect class="hit" x="0" y="${y}" width="${Wd}" height="${rowH}"/></g>`; });
  s += '</svg>'; el.innerHTML = s;
  el.querySelectorAll('.row').forEach(g => { const r = rows[+g.dataset.i]; g.addEventListener('mousemove', e => showTT(e, tip(r))); g.addEventListener('mouseleave', hideTT); });
}

// ---------- rankings
const sel = $('#hubsel');
const groupOrder = ['House of Peonies FW27', 'Sirens SS26', 'Sale & archive', 'Occasion wear', 'Shop', 'Product types (live and past products)', 'Wedding & occasion landing pages', 'Not in the menu (tag, drop or older collection)'];
const groups = [...new Set(HUBS.map(h => h.group))].sort((x, y) => groupOrder.indexOf(x) - groupOrder.indexOf(y));
function fillSel(q){ q = (q || '').toLowerCase(); const keep = sel.value;
  const match = h => !q || h.label.toLowerCase().includes(q) || h.id.includes(q) || (h.title || '').toLowerCase().includes(q);
  const opt = h => { const n = CUR ? CUR.HS[h.id].n : h.n_live; return `<option value="${h.id}">${h.nav ? '★ ' : ''}${esc(h.label)} (${n ? n + ' products' : 'nothing in this period'})</option>`; };
  sel.innerHTML = groups.map(g => { const hs = HUBS.filter(h => h.group === g && match(h) && (!CUR || CUR.HS[h.id].n > 0 || h.nav)).sort((x, y) => (y.nav - x.nav) || ((CUR ? CUR.HS[y.id].n : y.n_live) - (CUR ? CUR.HS[x.id].n : x.n_live))); return hs.length ? `<optgroup label="${esc(g)}">` + hs.map(opt).join('') + '</optgroup>' : ''; }).join('');
  if ([...sel.options].some(o => o.value === keep)) sel.value = keep; else if ([...sel.options].some(o => o.value === 'ss26-sirens-dresses')) sel.value = 'ss26-sirens-dresses'; }
$('#hubq').addEventListener('input', () => { fillSel($('#hubq').value); renderHub(); });
sel.addEventListener('change', () => { try { localStorage.setItem('mya-hub', sel.value); } catch(e) {} renderHub(); });
$('#topn').addEventListener('change', renderHub);
const COLS = ['#1A1B18', '#C9A99B', '#8A5F4E', '#5B7C99', '#7A9E7E', '#D4A24C', '#B36A6A', '#8C8C8C'];
function timeline(el, legendEl, pids){
  const Wd = 640, H = 220, ml = 40, mr = 10, mt = 10, mb = 26, iw = Wd - ml - mr, ih = H - mt - mb;
  const series = pids.map(pid => P[pid].v); const max = Math.max(1, ...series.flat());
  const X = i => ml + i / (NM - 1) * iw, Y = v => mt + ih - v / max * ih;
  let s = `<svg viewBox="0 0 ${Wd} ${H}" role="img" aria-label="Monthly page views of the top products">`;
  s += `<rect x="${X(A)}" y="${mt}" width="${Math.max(2, X(Bi) - X(A))}" height="${ih}" fill="var(--blush)"/>`;
  M.forEach((k, i) => { if (k.endsWith('-01')) s += `<line x1="${X(i)}" x2="${X(i)}" y1="${mt}" y2="${mt + ih}" class="axis"/><text class="tick" x="${X(i) + 3}" y="${H - 8}">${k.slice(0, 4)}</text>`; });
  [0.5, 1].forEach(f => s += `<text class="tick" x="${ml - 4}" y="${Y(max * f) + 3}" text-anchor="end">${fmt(max * f)}</text>`);
  series.forEach((arr, si) => { let d = ''; arr.forEach((v, i) => { d += (i ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(v).toFixed(1) + ' '; }); s += `<path d="${d}" fill="none" stroke="${COLS[si % COLS.length]}" stroke-width="1.8" stroke-linejoin="round"/>`; });
  s += '</svg>'; el.innerHTML = s;
  legendEl.innerHTML = pids.map((pid, i) => `<span style="--c:${COLS[i % COLS.length]}" class="l-c">${esc(P[pid].name)}</span>`).join('');
}
function renderHub(){
  fillSel($('#hubq').value);
  const h = HUB[sel.value] || HUB['ss26-sirens-dresses'] || HUBS[0]; const hs = CUR.HS[h.id];
  const n0 = +$('#topn').value; const n = n0 || hs.n;
  const rows = hs.rows.slice(0, n).map(r => Object.assign({}, P[r.pid], {score: r.score, rank: r.rank, ratioH: r.ratio, provH: r.prov, mm: CUR.MX[r.pid], tierH: CUR.MX[r.pid].V === 0 ? 'No data' : r.prov ? 'New' : tierOf(r.ratio)}));
  const note = !hs.n ? 'No product of this collection had traffic in the chosen period.' : h.id === 'all' ? 'The whole catalogue (live and past) ranked against itself for this period.' : h.kind === 'type' ? `Every ${h.title.toLowerCase()} product, live or not, ranked for this period. Type of past products is read from the URL.` : '';
  $('#hubnote').textContent = note; $('#hubnote').hidden = !note;
  const nObs = hs.rows.filter(r => !h.live_members.includes(r.pid)).length;
  $('#hubsrc').textContent = hs.n ? `Members in this period: ${fmt(hs.n)} products (${fmt(hs.n - nObs)} listed on the store today${nObs ? `, ${fmt(nObs)} seen opened from this collection page in the period but not listed today` : ''}).` : '';
  const t = hs.tot;
  $('#hubtiles').innerHTML = [['Products in collection', hs.n, `${fmt(rows.filter(r => !r.live).length)} of the shown not on site`], ['Product views', t.V, `${fmt(t.U)} users (monthly sum)`], ['Organic clicks', t.K, `${fmt(t.IM)} impressions`], ['Add-to-cart', t.A, `${fmt(t.B)} purchased · ${eur(t.R)}`], ['Engagement rate', (t.E / Math.max(t.S, 1) * 100).toFixed(1) + '%', 'engaged ÷ sessions'], ['Collection page views', sum(h.pv, A, Bi), sum(h.pk, A, Bi) ? `${fmt(sum(h.pk, A, Bi))} organic clicks to the page` : 'no organic clicks recorded']]
    .map(([l, v, s]) => `<div><span>${l}</span><b class="num">${typeof v === 'number' ? fmt(v) : v}</b>${s ? `<small>${s}</small>` : ''}</div>`).join('');
  $('#chart-title').textContent = `Demand Share, ${h.label}` + (n > 25 ? ' (chart shows top 25)' : '');
  hbar($('#chart'), rows.slice(0, 25), {aria: 'Top products by demand share', label: r => r.name, value: r => r.score, valueText: r => pct(r.score) + '%', hi: r => r.mm.B > 0,
    tip: r => `<b>${esc(r.name)}</b>Demand share ${pct(r.score)}%<br>${fmt(r.mm.V)} views · ${fmt(r.mm.U)} users<br>${fmt(r.mm.K)} organic clicks · ${fmt(r.mm.A)} add-to-cart${r.mm.B ? ` · ${r.mm.B} purchased` : ''}${r.live ? '' : '<br>Not on site any more'}`});
  timeline($('#timeline'), $('#tlegend'), rows.slice(0, 8).map(r => r.pid));
  $('#topcards').innerHTML = rows.filter(r => r.mm.V > 0).slice(0, 8).map(r => `<a class="card" href="${esc(r.url)}" target="_blank" rel="noopener"><div class="img">${r.img ? `<img src="${esc(img(r, 480))}" alt="" loading="lazy">` : `<span class="noimg">${esc(r.name)}</span>`}<span class="badge b-${r.tierH}">${r.tierH === 'Hero' ? 'Popular' : r.tierH === 'New' ? 'New in' : r.tierH}</span><span class="rankno num">#${r.rank}</span>${!r.live ? '<span class="soldout gone">Not on site</span>' : r.instock === 0 ? '<span class="soldout">Sold out</span>' : ''}</div><div class="cname">${esc(r.name)}</div><div class="cmeta">${r.price ? eur(r.price) + ' · ' : ''}${pct(r.score)}% of collection demand</div><div class="cratio">Ratio <b>${r.ratioH.toFixed(2)}</b>${r.trend && r.trend !== 'Steady' ? ' · ' + r.trend : ''}</div></a>`).join('');
  $('#ranktable').innerHTML = `<thead><tr><th>#</th><th>Product</th><th class="n">Demand share</th><th class="n">Ratio</th><th>Tier</th><th class="n">Ratio before</th><th>Momentum</th><th class="n">Views</th><th class="n">Users</th><th class="n">Eng. rate</th><th class="n">Organic clicks</th><th class="n">Add-to-cart</th><th class="n">Purchased</th><th class="n">Revenue</th><th>First seen</th></tr></thead><tbody>` +
    rows.map(r => `<tr><td class="num">${r.mm.V ? r.rank : ''}</td><td><div class="pcell">${thumb(r)}<div><a class="name" href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.name)}</a><div class="chips">${chips(r)}</div><div class="pl">${plist(r, h.id)}</div></div></div></td><td class="n num"><span class="sharebar" style="width:${Math.max(2, 60 * r.score / (rows[0].score || 1))}px"></span><span class="share">${pct(r.score)}%</span></td><td class="n num">${r.mm.V ? r.ratioH.toFixed(2) : ''}</td><td>${tierPill(r.tierH)}${r.mm.status !== 'Established' ? `<div class="small muted">${r.mm.active} of ${Bi - A + 1} months</div>` : ''}</td><td class="n num">${r.ratio_prev ? r.ratio_prev.toFixed(2) : ''}</td><td>${trendPill(r.trend)}</td><td class="n num">${fmt(r.mm.V)}</td><td class="n num">${fmt(r.mm.U)}</td><td class="n num">${r.mm.S ? (r.mm.E / r.mm.S * 100).toFixed(1) + '%' : ''}</td><td class="n num">${fmt(r.mm.K)}</td><td class="n num">${fmt(r.mm.A)}</td><td class="n num">${r.mm.B ? '<span class="flag">' + r.mm.B + '</span>' : '0'}</td><td class="n num">${r.mm.R ? eur(r.mm.R) : ''}</td><td class="small muted">${r.first !== null ? mlabel(M[r.first]) : ''}</td></tr>`).join('') + '</tbody>';
}
function plist(o, skip){ const xs = (o.placements || []).filter(x => x[0] !== skip); if (!xs.length) return '<span class="muted">main collection only</span>'; const f = x => `${esc(HUB[x[0]].label)} <b>#${x[1]}</b> of ${x[3]}`; return xs.slice(0, 5).map(f).join('<br>') + (xs.length > 5 ? `<details class="more"><summary>+${xs.length - 5} more</summary>${xs.slice(5).map(f).join('<br>')}</details>` : ''); }

// ---------- BCG
const QUAD = {Stars: {label: 'Stars', rule: 'Ratio ≥ 1.00 and momentum ≥ 1.00', act: 'Protect and push: hero slots, first rows, internal links, paid and social creative. Restock first if sold out.'}, Cash: {label: 'Cash cows', rule: 'Ratio ≥ 1.00 and momentum < 1.00', act: 'Keep visible, spend little. Refresh imagery and check price before they slide.'}, Question: {label: 'Question marks', rule: 'Ratio < 1.00 and momentum ≥ 1.00, plus everything new in the period', act: 'Test: a "New in" or trial slot for one cycle. Rising ones become Stars.'}, Dogs: {label: 'Dogs', rule: 'Ratio < 1.00 and momentum < 1.00', act: 'Back of the grid or Archive Sale. No links, no ads.'}};
const quadOf = o => { if (!o.ratio || o.m.V === 0) return null; if (o.m.status !== 'Established') return 'Question'; const m = o.mom || 1; return o.ratio >= 1 ? (m >= 1 ? 'Stars' : 'Cash') : (m >= 1 ? 'Question' : 'Dogs'); };
const bcgHub = $('#bcghub'); let bcgFilled = false;
function renderBCG(){
  PL.forEach(o => o.quad = quadOf(o));
  if (!bcgFilled) { [...new Set(PL.map(o => o.hub_label))].sort().forEach(t => { const op = document.createElement('option'); op.value = t; op.textContent = t; bcgHub.appendChild(op); }); bcgFilled = true; }
  const hub = bcgHub.value, sz = $('#bcgsize').value; const rows = PL.filter(o => o.quad && (!hub || o.hub_label === hub)); const tot = rows.reduce((s, o) => s + o.m.V, 0) || 1;
  $('#quads').innerHTML = ['Stars', 'Question', 'Cash', 'Dogs'].map(q => { const list = rows.filter(o => o.quad === q).sort((x, y) => y.m.V - x.m.V); const v = list.reduce((s, o) => s + o.m.V, 0);
    return `<div class="quad q-${q}"><h3>${QUAD[q].label}<small>${fmt(list.length)} products · ${(v / tot * 100).toFixed(0)}% of views</small></h3><div class="rule">${QUAD[q].rule}</div><div class="act">${QUAD[q].act}</div><ol>${list.slice(0, 6).map(o => `<li>${thumb(o)}<a href="${esc(o.url)}" target="_blank" rel="noopener" title="${esc(o.name)}">${esc(o.name)}${!o.live ? ' <span class="chip gone">Not on site</span>' : o.instock === 0 ? ' <span class="chip out">Sold out</span>' : ''}</a><span class="qn num">${o.ratio.toFixed(2)}${o.mom ? ' · ×' + o.mom.toFixed(2) : ' · new'}</span></li>`).join('')}</ol></div>`; }).join('');
  const Wd = 640, H = 460, ml = 52, mr = 16, mt = 18, mb = 44, iw = Wd - ml - mr, ih = H - mt - mb;
  const lx = r => Math.max(-2, Math.min(2, Math.log10(r))), ly = m => Math.max(-1, Math.min(1, Math.log10(m))); const X = r => ml + (lx(r) + 2) / 4 * iw, Y = m => mt + (1 - (ly(m) + 1) / 2) * ih;
  const pts = rows.filter(o => o.mom); const maxS = Math.max(...pts.map(o => sz === 'none' ? 1 : o.m[sz]), 1); const col = {Stars: '#1A1B18', Cash: '#C9A99B', Question: '#ECD7CD', Dogs: '#D2D5D9'};
  const dots = pts.map(o => { const r = sz === 'none' ? 3 : 2 + 9 * Math.sqrt((o.m[sz] || 0) / maxS); return `<circle class="dot" cx="${X(o.ratio).toFixed(1)}" cy="${Y(o.mom).toFixed(1)}" r="${r.toFixed(1)}" fill="${col[o.quad]}" data-i="${o.pid}"/>`; }).join('');
  const xt = [0.01, 0.1, 1, 10, 100].map(v => `<line x1="${X(v)}" x2="${X(v)}" y1="${mt}" y2="${mt + ih}" class="axis"/><text class="tick" x="${X(v)}" y="${mt + ih + 14}" text-anchor="middle">${v}</text>`).join('');
  const yt = [0.1, 0.5, 1, 2, 10].map(v => `<line y1="${Y(v)}" y2="${Y(v)}" x1="${ml}" x2="${ml + iw}" class="axis"/><text class="tick" x="${ml - 6}" y="${Y(v) + 3}" text-anchor="end">×${v}</text>`).join('');
  $('#bcgplot').innerHTML = `<svg viewBox="0 0 ${Wd} ${H}" role="img" aria-label="Growth share matrix"><rect x="${ml}" y="${mt}" width="${iw}" height="${ih}" fill="var(--surface-2)"/>${xt}${yt}<line x1="${X(1)}" x2="${X(1)}" y1="${mt}" y2="${mt + ih}" stroke="var(--ink)"/><line y1="${Y(1)}" y2="${Y(1)}" x1="${ml}" x2="${ml + iw}" stroke="var(--ink)"/><text class="qlab" x="${ml + iw - 8}" y="${mt + 18}" text-anchor="end">Stars</text><text class="qlab" x="${ml + 8}" y="${mt + 18}">Question marks</text><text class="qlab" x="${ml + iw - 8}" y="${mt + ih - 8}" text-anchor="end">Cash cows</text><text class="qlab" x="${ml + 8}" y="${mt + ih - 8}">Dogs</text>${dots}<text class="axl" x="${ml + iw / 2}" y="${H - 6}" text-anchor="middle">Share: popularity ratio in main collection (log)</text><text class="axl" transform="translate(12 ${mt + ih / 2}) rotate(-90)" text-anchor="middle">Momentum: this period ÷ period before (log)</text></svg>`;
  $('#bcgnote').textContent = `${fmt(pts.length)} products plotted${hub ? ' in ' + hub : ''}; ${fmt(rows.filter(o => !o.mom).length)} without a previous-period ratio are counted as question marks but not drawn.${PREV ? '' : ' No earlier period exists for this range, so momentum is unavailable.'}`;
  $('#bcgplot').querySelectorAll('.dot').forEach(c => { c.addEventListener('mousemove', e => { const o = P[c.dataset.i]; showTT(e, `<b>${esc(o.name)}</b>${QUAD[o.quad].label} · ${esc(o.hub_label)}<br>Ratio ${o.ratio.toFixed(2)} · before ${o.ratio_prev.toFixed(2)} · momentum ×${o.mom.toFixed(2)}<br>${fmt(o.m.V)} views · ${fmt(o.m.A)} add-to-cart · ${fmt(o.m.B)} purchased${o.live ? (o.instock === 0 ? '<br>Sold out today' : '') : '<br>Not on site any more'}`); }); c.addEventListener('mouseleave', hideTT); });
}
bcgHub.addEventListener('change', renderBCG); $('#bcgsize').addEventListener('change', renderBCG);

// ---------- seasons
const seahub = $('#seahub'); let seaFilled = false;
function renderSeasons(){
  if (!seaFilled) { const opts = HUBS.filter(h => h.nav || h.kind === 'type' || h.kind === 'landing').sort((x, y) => groupOrder.indexOf(x.group) - groupOrder.indexOf(y.group)); opts.forEach(h => { const o = document.createElement('option'); o.value = h.id; o.textContent = h.label; seahub.appendChild(o); }); seahub.value = 'type:Dresses'; seaFilled = true; seahub.addEventListener('change', renderSeasons); $('#seatop').addEventListener('change', renderSeasons); }
  const h = HUB[seahub.value]; const top = +$('#seatop').value;
  const seasons = D.seasons.filter(s => !['last90', 'last12', 'all', 'bf25'].includes(s.id)).slice().sort((x, y) => M.indexOf(x.a) - M.indexOf(y.a));
  $('#seasons').innerHTML = seasons.map(s => { const a = M.indexOf(s.a), b = M.indexOf(s.b); const R = compute(a, b); const hs = R.HS[h.id]; const rows = hs.rows.filter(r => R.MX[r.pid].V > 0).slice(0, top);
    return `<figure class="season"><figcaption><h3><a href="#" data-a="${a}" data-b="${b}" class="sealink">${esc(s.label.replace(/ \(.*\)/, ''))}</a></h3><span>${mlabel(s.a)} to ${mlabel(s.b)} · ${fmt(hs.tot.V || 0)} views · ${fmt(hs.n)} products</span></figcaption><ol>${rows.map(r => { const o = P[r.pid], m = R.MX[r.pid]; return `<li>${thumb(o)}<a href="${esc(o.url)}" target="_blank" rel="noopener" title="${esc(o.name)}">${esc(o.name)}${!o.live ? ' <span class="chip gone">Not on site</span>' : ''}</a><span class="qn num">${r.ratio.toFixed(2)} · ${fmt(m.V)} views${m.B ? ' · ' + m.B + ' sold' : ''}</span></li>`; }).join('') || '<li class="muted">No traffic in this season</li>'}</ol></figure>`; }).join('');
  $('#seasons').querySelectorAll('.sealink').forEach(a => a.addEventListener('click', e => { e.preventDefault(); setRange(+a.dataset.a, +a.dataset.b); window.scrollTo({top: 0, behavior: 'smooth'}); }));
  // season chart
  const Wd = 1100, H = 200, ml = 46, mr = 10, mt = 10, mb = 40, iw = Wd - ml - mr, ih = H - mt - mb; const max = Math.max(...D.monthly_total); const X = i => ml + i / (NM - 1) * iw, Y = v => mt + ih - v / max * ih;
  let s = `<svg viewBox="0 0 ${Wd} ${H}">`;
  seasons.forEach((se, i) => { const a = M.indexOf(se.a), b = M.indexOf(se.b); s += `<rect x="${X(a) - iw / (NM - 1) / 2}" y="${mt}" width="${X(b) - X(a) + iw / (NM - 1)}" height="${ih}" fill="${i % 2 ? 'var(--blush)' : 'var(--surface-2)'}"/><text class="tick" x="${(X(a) + X(b)) / 2}" y="${H - 22}" text-anchor="middle">${esc(se.label.split(' ')[0])}</text>`; });
  let d = ''; D.monthly_total.forEach((v, i) => d += (i ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(v).toFixed(1) + ' '); s += `<path d="${d}" fill="none" stroke="var(--ink)" stroke-width="1.8"/>`;
  M.forEach((k, i) => { if (k.endsWith('-01')) s += `<text class="tick" x="${X(i)}" y="${H - 6}" text-anchor="middle">${k.slice(0, 4)}</text>`; });
  [0.5, 1].forEach(f => s += `<text class="tick" x="${ml - 4}" y="${Y(max * f) + 3}" text-anchor="end">${fmt(max * f)}</text>`);
  $('#seasonchart').innerHTML = s + '</svg>';
}

// ---------- products table
const fkeys = ['hub_label', 'type', 'season', 'colour', 'price_band', 'stock_band']; let fFilled = false;
const bandOrder = ['Under €80', 'From €80 to €129', 'From €130 to €199', 'From €200 to €299', '€300 and over', 'Sold out', 'Low stock (under half of sizes)', 'Mostly in stock', 'Fully in stock'];
let sortKey = 'ratio', sortDir = 'desc', page = 1; const PAGE = 100; const trendOrder = {Rising: 0, New: 1, Steady: 2, Fading: 3, '': 4}; const tierOrder = {Hero: 0, Strong: 1, Average: 2, Low: 3, New: 4, 'No data': 5};
const allCols = [['name', 'Product', false], ['hub_label', 'Main collection', false], ['tier', 'Tier', false], ['ratio', 'Ratio', true], ['rank', 'Rank', true], ['ratio_prev', 'Ratio before', true], ['trend', 'Momentum', false], ['V', 'Views', true], ['U', 'Users', true], ['er', 'Eng. rate', true], ['K', 'Organic clicks', true], ['A', 'Add-to-cart', true], ['B', 'Purchased', true], ['R', 'Revenue', true], ['first', 'First seen', true], ['instock', 'In stock today', true]];
const val = (o, k) => ['V', 'U', 'K', 'A', 'B', 'R'].includes(k) ? o.m[k] : k === 'er' ? (o.m.S ? o.m.E / o.m.S : 0) : o[k];
function filtered(){
  const q = $('#q').value.trim().toLowerCase(); const f = {}; fkeys.forEach(k => f[k] = $('#f-' + k).value); const ft = $('#f-tier').value, ftr = $('#f-trend').value, fl = $('#f-live').value;
  let rows = PL.filter(o => o.m.V > 0 && (!q || o.name.toLowerCase().includes(q) || o.slug.includes(q)) && (!ft || o.tier === ft) && (!ftr || o.trend === ftr) && (!fl || (fl === 'yes') === o.live) && fkeys.every(k => !f[k] || o[k] === f[k]));
  rows.sort((x, y) => { let a = val(x, sortKey), b = val(y, sortKey); if (sortKey === 'tier') { a = tierOrder[a]; b = tierOrder[b]; } if (sortKey === 'trend') { a = trendOrder[a]; b = trendOrder[b]; } if (typeof a === 'string') return sortDir === 'asc' ? a.localeCompare(b) : b.localeCompare(a); a = a ?? -1; b = b ?? -1; return sortDir === 'asc' ? a - b : b - a; });
  return rows;
}
function renderTable(){
  if (!fFilled) { fkeys.forEach(k => { const vals = [...new Set(PL.map(o => o[k]).filter(Boolean))].sort((x, y) => (bandOrder.indexOf(x) - bandOrder.indexOf(y)) || x.localeCompare(y)); const s = $('#f-' + k); vals.forEach(v => { const o = document.createElement('option'); o.value = v; o.textContent = v; s.appendChild(o); }); }); fFilled = true;
    $('#q').addEventListener('input', () => { page = 1; renderTable(); }); ['tier', 'trend', 'live', ...fkeys].forEach(k => $('#f-' + k).addEventListener('change', () => { page = 1; renderTable(); })); }
  const rows = filtered(); const pages = Math.max(1, Math.ceil(rows.length / PAGE)); if (page > pages) page = pages; const slice = rows.slice((page - 1) * PAGE, page * PAGE);
  $('#allcount').textContent = `${fmt(rows.length)} products with traffic in the period` + (rows.length > PAGE ? `, showing ${(page - 1) * PAGE + 1} to ${Math.min(page * PAGE, rows.length)}` : '');
  $('#alltable').innerHTML = '<thead><tr>' + allCols.map(([k, l, num]) => `<th class="sort${num ? ' n' : ''}" data-k="${k}" ${k === sortKey ? `data-dir="${sortDir}"` : ''}>${l}</th>`).join('') + '<th>Also seen in (rank)</th></tr></thead><tbody>' +
    slice.map(o => `<tr><td><div class="pcell">${thumb(o)}<div><a class="name" href="${esc(o.url)}" target="_blank" rel="noopener">${esc(o.name)}</a><div class="chips">${chips(o)}</div></div></div></td><td>${esc(o.hub_label)}<div class="small muted">${o.rank ? '#' + o.rank + ' of ' + o.nhub : ''}</div></td><td>${tierPill(o.tier)}${o.m.status !== 'Established' ? `<div class="small muted">${o.m.active} of ${Bi - A + 1} months</div>` : ''}</td><td class="n num">${o.ratio.toFixed(2)}</td><td class="n num">${o.rank || ''}</td><td class="n num">${o.ratio_prev ? o.ratio_prev.toFixed(2) : ''}</td><td>${trendPill(o.trend)}</td><td class="n num">${fmt(o.m.V)}</td><td class="n num">${fmt(o.m.U)}</td><td class="n num">${o.m.S ? (o.m.E / o.m.S * 100).toFixed(1) + '%' : ''}</td><td class="n num">${fmt(o.m.K)}</td><td class="n num">${fmt(o.m.A)}</td><td class="n num">${o.m.B ? '<span class="flag">' + o.m.B + '</span>' : '0'}</td><td class="n num">${o.m.R ? eur(o.m.R) : ''}</td><td class="small muted">${o.first !== null ? mlabel(M[o.first]) : ''}</td><td class="n num">${!o.live ? '<span class="chip gone">Not on site</span>' : o.instock === 0 ? '<span class="chip out">Sold out</span>' : Math.round(o.instock) + '%'}</td><td class="pl">${plist(o, null)}</td></tr>`).join('') + '</tbody>';
  $('#alltable').querySelectorAll('th.sort').forEach(th => th.addEventListener('click', () => { const k = th.dataset.k; if (sortKey === k) sortDir = sortDir === 'asc' ? 'desc' : 'asc'; else { sortKey = k; sortDir = ['name', 'hub_label', 'tier', 'rank', 'first'].includes(k) ? 'asc' : 'desc'; } page = 1; renderTable(); }));
  let pg = ''; if (pages > 1) { const around = [...new Set([1, 2, page - 1, page, page + 1, pages - 1, pages].filter(x => x >= 1 && x <= pages))].sort((x, y) => x - y); let prev = 0; around.forEach(x => { if (x - prev > 1) pg += '<span>…</span>'; pg += `<button data-p="${x}" ${x === page ? 'aria-current="true"' : ''}>${x}</button>`; prev = x; }); }
  $('#pager').innerHTML = pg; $('#pager').querySelectorAll('button').forEach(b => b.addEventListener('click', () => { page = +b.dataset.p; renderTable(); window.scrollTo({top: $('#allcount').offsetTop - 80}); }));
}

// ---------- placement map
function renderMap(){
  const tiers = {}; HUBS.forEach(h => { const t = {}; CUR.HS[h.id].rows.forEach(r => { const k = CUR.MX[r.pid].V === 0 ? 'No data' : r.prov ? 'New' : tierOf(r.ratio); t[k] = (t[k] || 0) + 1; }); tiers[h.id] = t; });
  $('#mapgroups').innerHTML = '<div class="legend"><span class="l-Hero">Hero (3.00+)</span><span class="l-Strong">Strong (1.50 to 2.99)</span><span class="l-Average">Average (0.50 to 1.49)</span><span class="l-Low">Low (under 0.50)</span><span class="l-New">New (provisional 1.50)</span></div>' + groups.map(g => { const hs = HUBS.filter(h => h.group === g && CUR.HS[h.id].n > 0).sort((x, y) => CUR.HS[y.id].n - CUR.HS[x.id].n); if (!hs.length) return '';
    return `<details class="mapgroup" ${g.startsWith('Not in') ? '' : 'open'}><summary><h3 style="display:inline">${esc(g)}</h3> <span class="muted small">${hs.length} collections with products in the period</span></summary>` + hs.map(h => { const t = tiers[h.id]; const n = CUR.HS[h.id].n; return `<div class="stack" data-h="${h.id}"><span>${esc(h.label)}</span><div class="bar-row">${['Hero', 'Strong', 'Average', 'Low', 'New', 'No data'].map(k => t[k] ? `<div class="seg seg-${k.replace(' ', '-')}" style="width:${t[k] / n * 100}%"></div>` : '').join('')}</div><span class="num muted">${fmt(n)}</span></div>`; }).join('') + '</details>'; }).join('');
  $('#mapgroups').querySelectorAll('.stack').forEach(el => { const h = HUB[el.dataset.h], t = tiers[h.id]; el.addEventListener('mousemove', e => showTT(e, `<b>${esc(h.label)}</b>Hero ${t.Hero || 0} · Strong ${t.Strong || 0} · Average ${t.Average || 0} · Low ${t.Low || 0} · New ${t.New || 0}<br>${fmt(CUR.HS[h.id].n)} products, ${fmt(CUR.HS[h.id].tot.V)} views`)); el.addEventListener('mouseleave', hideTT); });
}

// ---------- collections
function renderColls(){
  const rows = HUBS.filter(h => h.kind !== 'type').map(h => ({h, v: sum(h.pv, A, Bi), u: sum(h.pu, A, Bi), k: sum(h.pk, A, Bi), im: sum(h.pim, A, Bi), n: CUR.HS[h.id].n, pv: CUR.HS[h.id].tot.V || 0})).filter(r => r.v > 0 || r.k > 0).sort((x, y) => y.v - x.v);
  hbar($('#hubchart'), rows.slice(0, 25), {aria: 'Collection page views', labelW: 260, label: r => r.h.label, value: r => r.v, valueText: r => fmt(r.v), tip: r => `<b>${esc(r.h.label)}</b>${fmt(r.v)} collection page views<br>${fmt(r.k)} organic clicks · ${fmt(r.im)} impressions<br>${fmt(r.n)} products in the period, ${fmt(r.pv)} product views`});
  $('#navtable').innerHTML = '<thead><tr><th>Collection page</th><th>Group</th><th class="n">Products in period</th><th class="n">Product views</th><th class="n">Page views</th><th class="n">Organic clicks</th><th class="n">Impressions</th></tr></thead><tbody>' + rows.map(r => `<tr><td>${r.h.nav ? '★ ' : ''}<a href="https://myacollection.com/collections/${esc(r.h.id)}" target="_blank" rel="noopener">${esc(r.h.label)}</a><div class="small muted">/collections/${esc(r.h.id)}</div></td><td class="small">${esc(r.h.group)}</td><td class="n num">${r.n ? fmt(r.n) : '<span class="flag">none</span>'}</td><td class="n num">${fmt(r.pv)}</td><td class="n num">${fmt(r.v)}</td><td class="n num">${fmt(r.k)}</td><td class="n num">${fmt(r.im)}</td></tr>`).join('') + '</tbody>';
}

// ---------- attributes
function renderAttr(){
  const labels = {type: 'Product type (all products)', season: 'Season tag (live products)', colours: 'Colour (live products)', price_band: 'Price band (live products)', stock_band: 'Stock today (live products)', live: 'Live vs no longer on site'};
  const agg = key => { const m = {}; PL.forEach(o => { if (o.m.V === 0) return; const vals = key === 'live' ? [o.live ? 'Live on the store' : 'Not on site any more'] : Array.isArray(o[key]) ? o[key] : [o[key]]; vals.forEach(v => { if (!v) return; const a = m[v] || (m[v] = {label: v, views: 0, users: 0, atc: 0, purch: 0, n: 0}); a.views += o.m.V; a.users += o.m.U; a.atc += o.m.A; a.purch += o.m.B; a.n++; }); }); return Object.values(m).sort((x, y) => y.views - x.views); };
  $('#attrgrid').innerHTML = Object.keys(labels).map(k => `<figure><figcaption><h3>${labels[k]}</h3><span>share of product views</span></figcaption><div id="attr-${k}"></div></figure>`).join('');
  Object.keys(labels).forEach(k => { const rows = agg(k); const tot = rows.reduce((s, r) => s + r.views, 0) || 1; hbar($('#attr-' + k), rows.slice(0, 12), {aria: labels[k], labelW: 170, label: r => r.label, value: r => r.views, valueText: r => (r.views / tot * 100).toFixed(0) + '%', tip: r => `<b>${esc(r.label)}</b>${fmt(r.views)} views across ${fmt(r.n)} products<br>${fmt(r.users)} users · ${fmt(r.atc)} add-to-cart · ${fmt(r.purch)} purchased`}); });
  const so = PL.filter(o => o.live && o.instock === 0 && o.m.V > 0); const sov = so.reduce((s, o) => s + o.m.V, 0); const tv = PL.reduce((s, o) => s + o.m.V, 0) || 1;
  $('#stocknote').innerHTML = `<b>Stock today, demand in this period.</b> ${fmt(so.length)} products that are sold out in every size right now took ${(sov / tv * 100).toFixed(0)}% of the period's product page views (${fmt(sov)}). For the last 90 days that is the restock list; for an older season it shows which pieces still draw attention after selling through.`;
}
function renderMethod(){
  const c = D.coverage;
  $('#stocktext').textContent = `Stock status was read from the live store on ${D.crawled}: a product counts as sold out when no size or colour variant is available. ${fmt(c.soldout)} of the ${fmt(c.live)} live products are sold out today. The score never penalises sold-out pieces: their views and users count in full, and add-to-cart has only a 10% weight precisely because a sold-out product cannot be added to cart. A sold-out Hero is a restock or re-cut candidate, not a product to hide.`;
  $('#coverage').innerHTML = [`GA4 Pages and screens by month, ${mlabel(M[0])} to ${mlabel(M[NM - 1])}: ${fmt(c.product_views)} product page views on ${fmt(c.products)} distinct products (${fmt(c.live)} live on the store today, ${fmt(c.old)} no longer on it). Language prefixes (/en/) and collection paths (/collections/x/products/y) are merged into one product; the collection in the path is kept as membership evidence.`,
    `GA4 Ecommerce items by month: ${fmt(c.items_rows)} item-month rows, ${fmt(c.items_matched)} matched to a product (${(c.item_views_matched / c.item_views * 100).toFixed(0)}% of item views). Greek and English names and size variants of the same item are merged. Unmatched names are products whose URL never appeared in GA4.`,
    `Search Console through the GA4 link: one export per month from ${mlabel(c.gsc_from)} to ${mlabel(c.gsc_to)} (Search Console keeps 16 months). Periods before June 2025 have no organic click signal and the weight is redistributed.`,
    `Catalogue: ${fmt(c.collections_crawled)} collections and ${fmt(c.live)} live products read from the store on ${D.crawled}, each URL checked live; images, prices, colour options and per-size stock are for live products only.`,
    `Known gap: ${c.truncated_2023}. Every other export is complete (no "(other)" rows).`].map(s => `<li>${s}</li>`).join('');
}

fillSel(''); try { const v = localStorage.getItem('mya-hub'); if (v && HUB[v]) sel.value = v; } catch(e) {}
setRange(A, Bi);
}
const b64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
document.body.classList.add('locked');
document.getElementById('lockform').addEventListener('submit', async ev => {
  ev.preventDefault(); const el = document.getElementById('enc'); const err = document.getElementById('lockerr'); err.textContent = 'Checking…';
  try {
    const km = await crypto.subtle.importKey('raw', new TextEncoder().encode(document.getElementById('pw').value), 'PBKDF2', false, ['deriveKey']);
    const key = await crypto.subtle.deriveKey({name: 'PBKDF2', salt: b64(el.dataset.salt), iterations: +el.dataset.iter, hash: 'SHA-256'}, km, {name: 'AES-GCM', length: 256}, false, ['decrypt']);
    const pt = await crypto.subtle.decrypt({name: 'AES-GCM', iv: b64(el.dataset.iv)}, key, b64(window.__ENC));
    document.getElementById('data').textContent = new TextDecoder().decode(pt);
    el.remove(); document.getElementById('lock').remove(); document.body.classList.remove('locked');
    await boot();
  } catch(e) { err.textContent = e.name === 'OperationError' ? 'Wrong password, try again.' : 'Error: ' + e.message; console.error(e); }
});
