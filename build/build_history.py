"""MYA product demand, v2: monthly history for every product that ever had traffic (Aug 2023 to Sep 2026),
so the dashboard can score any period the viewer picks. Inputs: hist/*.csv (GA4 exports with Month), site.json (live catalogue),
not_live.json. Output: data2.json"""
import csv, json, re, glob, os, collections, datetime as dt, unicodedata
from urllib.parse import unquote
import helpers as B

TODAY = dt.date(2026, 9, 24)
MONTHS = []
y, m = 2023, 8
while (y, m) <= (2026, 9):
    MONTHS.append(f'{y}-{m:02d}'); m += 1
    if m == 13: y, m = y + 1, 1
MI = {k: i for i, k in enumerate(MONTHS)}
NM = len(MONTHS)

def norm(p):
    p = unquote(p)
    p = re.split(r'\?|%3F|%3f', p)[0]
    p = B.LANG.sub('', p.strip()) or '/'
    if len(p) > 1 and p.endswith('/'): p = p[:-1]
    return p

def num(x):
    try: return float(x)
    except: return 0.0

def read(path):
    rows = [r for r in csv.reader(open(path, encoding='utf-8')) if r and not r[0].startswith('#')]
    return rows[0], rows[1:]

def zeros(): return [0] * NM

# ---------------- catalogue
site = json.load(open('site.json'))
NOT_LIVE = set(json.load(open('not_live.json'))) if os.path.exists('not_live.json') else set()
LIVE = {h: p for h, p in site['products'].items() if h not in NOT_LIVE}
MEMB = {c: [h for h in hs if h in LIVE] for c, hs in site['membership'].items()}
COLLS = {c['handle']: c for c in site['collections']}
COLLS.setdefault('all', {'title': 'All products'})

# ---------------- GA4 pages: products and collections by month
P = collections.defaultdict(lambda: {k: zeros() for k in ('views', 'users', 'sess', 'engs', 'atc_pg', 'purch_pg')})
PC = collections.defaultdict(lambda: collections.defaultdict(zeros))       # product -> collection -> monthly views (observed membership)
C = collections.defaultdict(lambda: {k: zeros() for k in ('views', 'users', 'sess', 'engs')})
for f in sorted(glob.glob('hist/pages_products_*.csv')) + sorted(glob.glob('hist/pages_collections_*.csv')):
    year = re.search(r'_(\d{4})\d{4}_', f).group(1)
    hdr, rows = read(f); ix = {k: hdr.index(k) for k in hdr}
    is_coll_file = 'collections' in f
    for r in rows:
        key = f"{year}-{r[ix['Month']]}"
        if key not in MI: continue
        i = MI[key]; p = norm(r[0])
        h = B.product_handle(p)
        if h:
            if is_coll_file: continue          # product rows appear in both files: count them once, from the products file
            d = P[h]
            d['views'][i] += num(r[ix['Views']]); d['users'][i] += num(r[ix['Active users']]); d['sess'][i] += num(r[ix['Sessions']])
            d['engs'][i] += num(r[ix['Engaged sessions']]); d['atc_pg'][i] += num(r[ix['Add to carts']]); d['purch_pg'][i] += num(r[ix['Ecommerce purchases']])
            mc = re.match(r'^/collections/([^/]+)/products/', p)
            if mc: PC[h][mc.group(1)][i] += num(r[ix['Views']])
            continue
        c = B.collection_handle(p)
        if c and is_coll_file:
            d = C[c]; d['views'][i] += num(r[ix['Views']]); d['users'][i] += num(r[ix['Active users']]); d['sess'][i] += num(r[ix['Sessions']]); d['engs'][i] += num(r[ix['Engaged sessions']])

# ---------------- Search Console (GA4 link): one file per month
G = collections.defaultdict(lambda: {'clicks': zeros(), 'impr': zeros()})
GC = collections.defaultdict(lambda: {'clicks': zeros(), 'impr': zeros()})
GSC_MONTHS = set()
for f in sorted(glob.glob('hist/gsc_*.csv')):
    s = re.search(r'gsc_(\d{4})(\d{2})', f); key = f'{s.group(1)}-{s.group(2)}'
    if key not in MI: continue
    i = MI[key]; GSC_MONTHS.add(key)
    hdr, rows = read(f); ix = {k: hdr.index(k) for k in hdr}
    for r in rows:
        p = norm(r[0]); cl = num(r[ix['Organic Google Search clicks']]); im = num(r[ix['Organic Google Search impressions']])
        h = B.product_handle(p)
        if h: G[h]['clicks'][i] += cl; G[h]['impr'][i] += im; continue
        c = B.collection_handle(p)
        if c: GC[c]['clicks'][i] += cl; GC[c]['impr'][i] += im

# ---------------- items by month (name -> handle)
all_handles = set(LIVE) | set(P)
title_map = {}
for h, p in LIVE.items():
    t = p['title'].strip().lower(); title_map[t] = h; title_map[B.slugify(t)] = h
    en = ' '.join(B.GREEK_TYPE.get(w, w) for w in t.split()).replace('  ', ' ').strip(); title_map[en] = h; title_map[B.slugify(en)] = h
first_word = collections.defaultdict(set)
for h in all_handles: first_word[h.split('-')[0]].add(h)
SIZE_SUFFIX = re.compile(r'\s*[-–/]\s*(xs|s|m|l|xl|xxl|xxs|s/m|m/l|l/xl|one size|onesize|x-?small|small|medium|large|x-?large|\d{1,2}|pre.?order)\b.*$', re.I)
def match_item(name):
    name = SIZE_SUFFIX.sub('', name.strip())
    key = name.strip().lower()
    h = title_map.get(key) or title_map.get(B.slugify(name))
    if h: return h
    sl = B.slugify(' '.join(B.GREEK_TYPE.get(w, w) for w in key.split()))
    if sl in all_handles: return sl
    if sl in title_map: return title_map[sl]
    parts = set(sl.split('-'))
    cands = first_word.get(sl.split('-')[0] if sl else '', set())
    exact = [c for c in cands if set(c.split('-')) == parts]
    if len(exact) == 1: return exact[0]
    if len(cands) == 1 and len(parts) > 1: return next(iter(cands))
    return None
IT = collections.defaultdict(lambda: {k: zeros() for k in ('item_views', 'atc', 'purch', 'revenue')})
ITEM_NAMES = collections.defaultdict(collections.Counter)
items_total = collections.Counter(); items_matched = 0; items_rows = 0
for f in sorted(glob.glob('hist/items_*.csv')):
    year = re.search(r'items_(\d{4})', f).group(1)
    hdr, rows = read(f); ix = {k: hdr.index(k) for k in hdr}
    for r in rows:
        key = f"{year}-{r[ix['Month']]}"
        if key not in MI: continue
        i = MI[key]; items_rows += 1; v = num(r[ix['Items viewed']]); items_total['views'] += v
        h = match_item(r[0])
        if not h: continue
        items_matched += 1; items_total['matched_views'] += v
        d = IT[h]; d['item_views'][i] += v; d['atc'][i] += num(r[ix['Items added to cart']]); d['purch'][i] += num(r[ix['Items purchased']]); d['revenue'][i] += num(r[ix['Item revenue']])
        ITEM_NAMES[h][SIZE_SUFFIX.sub('', r[0].strip())] += v

# ---------------- product table
def handle_name(h):
    return ' '.join(w.capitalize() for w in h.split('-') if not w.isdigit())
def type_from_handle(h):
    words = set(h.split('-'))
    for k, t in [('dress', 'Dresses'), ('top', 'Tops'), ('shirt', 'Tops'), ('blouse', 'Tops'), ('bodysuit', 'Tops'), ('skirt', 'Skirts'), ('kimono', 'Kimono dresses'), ('jumpsuit', 'Jumpsuits'), ('jumsuit', 'Jumpsuits'), ('pants', 'Pants'), ('trousers', 'Pants'), ('shorts', 'Pants'), ('cape', 'Capes'), ('blazer', 'Blazers & jackets'), ('jacket', 'Blazers & jackets'), ('kids', 'Kids'), ('belt', 'Accessories'), ('bag', 'Accessories'), ('scarf', 'Accessories'), ('turban', 'Accessories'), ('set', 'Sets'), ('bikini', 'Swimwear'), ('swimsuit', 'Swimwear')]:
        if k in words: return t
    return 'Other'

products = {}
for h in sorted(all_handles):
    pg = P.get(h); g = G.get(h); it = IT.get(h)
    views = pg['views'] if pg else zeros()
    if not pg and h not in LIVE: continue
    live = h in LIVE
    first = next((i for i, v in enumerate(views) if v > 0), None)
    rec = dict(pid=h, slug=h, live=live, first=first,
               v=[int(x) for x in views], u=[int(x) for x in (pg['users'] if pg else zeros())], s=[int(x) for x in (pg['sess'] if pg else zeros())], e=[int(x) for x in (pg['engs'] if pg else zeros())],
               k=[int(x) for x in (g['clicks'] if g else zeros())], im=[int(x) for x in (g['impr'] if g else zeros())],
               a=[int(round(x)) for x in (it['atc'] if it else (pg['atc_pg'] if pg else zeros()))], b=[int(round(x)) for x in (it['purch'] if it else (pg['purch_pg'] if pg else zeros()))], r=[int(round(x)) for x in (it['revenue'] if it else zeros())],
               atc_src='items' if it else 'page')
    obs = {c: [int(x) for x in arr] for c, arr in PC.get(h, {}).items() if sum(arr) >= 5}
    rec['obs'] = obs
    if live:
        p = LIVE[h]
        colls = [c for c, hs in MEMB.items() if h in hs and c != 'all']
        prices = [float(v['price']) for v in p['variants'] if v.get('price')]; avail = [bool(v.get('available')) for v in p['variants']]
        colours = B.colour_of(next((o['values'] for o in p['options'] if o['name'].lower() in ('color', 'colour', 'χρώμα')), []))
        pub = dt.datetime.fromisoformat(p['published_at']).date() if p.get('published_at') else None
        rec.update(name=p['title'].strip(), img=(p['images'][0]['src'] if p['images'] else ''), type=B.norm_type(p.get('product_type'), p['title']), season=B.season_of(p.get('tags', []), colls),
                   colour=colours[0] if len(colours) == 1 else ('Multiple' if len(colours) > 1 else ''), colours=colours, price=min(prices) if prices else None, price_band=B.price_band(min(prices) if prices else None),
                   limited=('limited' in p['title'].lower()), instock=(sum(avail) / len(avail) * 100 if avail else 0), published=pub.isoformat() if pub else '', colls=colls)
    else:
        names = ITEM_NAMES.get(h)
        nm = names.most_common(1)[0][0] if names else handle_name(h)
        if nm.upper() == nm: nm = nm.title()
        rec.update(name=nm, img='', type=type_from_handle(h), season='', colour='', colours=[], price=None, price_band='', limited='limited' in h, instock=None, published='', colls=[])
    rec['stock_band'] = '' if rec['instock'] is None else ('Sold out' if rec['instock'] == 0 else 'Low stock (under half of sizes)' if rec['instock'] < 50 else 'Mostly in stock' if rec['instock'] < 100 else 'Fully in stock')
    products[h] = rec

# ---------------- hubs (collections): live membership from the crawl + observed membership from GA4 paths
NAVIDX = {h: (lab, grp, kind) for h, lab, grp, kind in B.NAV}
LANDING = {'wedding': ('Φορέματα για γάμο (wedding dresses)', 'Wedding & occasion landing pages'), 'events': ('Φορέματα για βάπτιση (christening dresses)', 'Wedding & occasion landing pages'),
           'wedding-baptism': ('Ρούχα για Γάμο & Βάπτιση (wedding & christening)', 'Wedding & occasion landing pages'), 'dresses-wedding': ('Dresses Wedding', 'Wedding & occasion landing pages')}
hubs = {}
all_colls = set(MEMB) | set(C) | {c for h in PC for c in PC[h]} | set(GC)
for c in all_colls:
    if c == 'all': continue
    members_live = [h for h in MEMB.get(c, []) if h in products]
    observed = [h for h in products if c in products[h]['obs']]
    if not members_live and not observed and sum(C.get(c, {'views': zeros()})['views']) < 20: continue
    if c in LANDING: lab, grp, kind = LANDING[c][0], LANDING[c][1], 'landing'
    else: lab, grp, kind = NAVIDX.get(c, (COLLS.get(c, {}).get('title') or handle_name(c), 'Not in the menu (tag, drop or older collection)', 'other'))
    cv = C.get(c); gc = GC.get(c)
    hubs[c] = dict(id=c, label=lab, title=COLLS.get(c, {}).get('title', ''), group=grp, kind=kind, nav=c in NAVIDX, live_members=members_live, n_live=len(members_live), n_observed=len(observed),
                   pv=[int(x) for x in cv['views']] if cv else zeros(), pu=[int(x) for x in cv['users']] if cv else zeros(), pk=[int(x) for x in gc['clicks']] if gc else zeros(), pim=[int(x) for x in gc['impr']] if gc else zeros())
hubs['all'] = dict(id='all', label='All products (Shop now)', title='All products', group='Shop', kind='root', nav=True, live_members=sorted(products), n_live=len([h for h in products if products[h]['live']]), n_observed=0,
                   pv=[int(x) for x in C['all']['views']] if 'all' in C else zeros(), pu=zeros(), pk=[int(x) for x in GC['all']['clicks']] if 'all' in GC else zeros(), pim=zeros())

# type hubs (virtual): every product of a type, live or not
TYPE_HUBS = sorted({p['type'] for p in products.values()} - {'Other'})

# main hub for live products (same rule as v1); for old products the observed collection with most views
nav_order = [h for h, *_ in B.NAV if h != 'all']
def main_hub(r):
    if r['live']:
        subs = [c for c in nav_order if NAVIDX[c][2] == 'sub' and c in r['colls'] and c in hubs]
        if subs: return subs[0]
        roots = [c for c in nav_order if NAVIDX[c][2] == 'root' and c in r['colls'] and c in hubs]
        if roots: return roots[0]
        others = sorted([c for c in r['colls'] if c in hubs], key=lambda c: -hubs[c]['n_live'])
        if others: return others[0]
    obs = sorted(r['obs'].items(), key=lambda kv: -sum(kv[1]))
    for c, _ in obs:
        if c in hubs: return c
    return 'type:' + r['type'] if r['type'] != 'Other' else 'all'
for r in products.values():
    r['hub'] = main_hub(r)

# seasons (presets)
SEASONS = [
    dict(id='last90', label='Last 90 days (Jul to Sep 2026)', a='2026-07', b='2026-09'),
    dict(id='last12', label='Last 12 months (Oct 2025 to Sep 2026)', a='2025-10', b='2026-09'),
    dict(id='fw26', label='FW26/27 so far (Sep 2026, House of Peonies launch)', a='2026-09', b='2026-09'),
    dict(id='ss26', label='SS26 Sirens (Mar to Aug 2026)', a='2026-03', b='2026-08'),
    dict(id='fw25', label='FW25/26 Lotus (Sep 2025 to Feb 2026)', a='2025-09', b='2026-02'),
    dict(id='bf25', label='Black Friday month (Nov 2025)', a='2025-11', b='2025-11'),
    dict(id='ss25', label='SS25 Swan (Mar to Aug 2025)', a='2025-03', b='2025-08'),
    dict(id='fw24', label='FW24/25 Reflections (Sep 2024 to Feb 2025)', a='2024-09', b='2025-02'),
    dict(id='ss24', label='SS24 Butterfly (Mar to Aug 2024)', a='2024-03', b='2024-08'),
    dict(id='fw23', label='FW23/24 Wild Love (Aug 2023 to Feb 2024)', a='2023-08', b='2024-02'),
    dict(id='all', label='All time (Aug 2023 to Sep 2026)', a='2023-08', b='2026-09'),
]

cov = dict(products=len(products), live=sum(1 for p in products.values() if p['live']), old=sum(1 for p in products.values() if not p['live']),
           product_views=int(sum(sum(p['v']) for p in products.values())), months=NM, gsc_from=min(GSC_MONTHS) if GSC_MONTHS else '', gsc_to=max(GSC_MONTHS) if GSC_MONTHS else '',
           items_rows=items_rows, items_matched=items_matched, item_views=int(items_total['views']), item_views_matched=int(items_total['matched_views']),
           hubs=len(hubs), collections_crawled=len(MEMB), soldout=sum(1 for p in products.values() if p['live'] and p['instock'] == 0),
           truncated_2023='2023 product export capped at 100,000 rows by GA4 (115,553 existed): the lowest-traffic product URL rows of Aug to Dec 2023 are missing')
monthly_total = [int(sum(p['v'][i] for p in products.values())) for i in range(NM)]
D = dict(months=MONTHS, products=list(products.values()), hubs=list(hubs.values()), type_hubs=TYPE_HUBS, seasons=SEASONS, coverage=cov, monthly_total=monthly_total,
         crawled=TODAY.isoformat(), weights=dict(views=0.35, users=0.25, engs=0.15, clicks=0.15, atc=0.10))
json.dump(D, open('data2.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('products', len(products), 'live', cov['live'], 'old', cov['old'], 'hubs', len(hubs), 'views', cov['product_views'])
print('monthly', list(zip(MONTHS, monthly_total)))
print('items matched', items_matched, '/', items_rows, f"{items_total['matched_views']/max(items_total['views'],1)*100:.0f}% of item views", 'size', os.path.getsize('data2.json'))
print('top old', sorted([(p['name'], sum(p['v'])) for p in products.values() if not p['live']], key=lambda x: -x[1])[:10])
