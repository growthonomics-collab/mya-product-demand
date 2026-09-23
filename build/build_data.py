"""Build the MYA Collection product demand dataset from GA4 / Search Console exports + the Shopify catalogue crawl.
Formula mirrors the FFJ dashboard (Demand Share / Popularity Ratio), adapted to a Shopify store.
"""
import csv, json, re, math, datetime as dt, collections, unicodedata
from urllib.parse import unquote

TODAY = dt.date(2026, 9, 23)
PERIOD_START, PERIOD_END = dt.date(2026, 6, 25), dt.date(2026, 9, 22)
WINDOW = 90
WEIGHTS = {'views': 0.35, 'users': 0.25, 'engs': 0.15, 'clicks': 0.15, 'atc': 0.10}
WEIGHTS_LONG = {'views': 0.45, 'users': 0.35, 'engs': 0.20}
PRIOR_RATIO, PRIOR_K = 1.5, 100
TIERS = [(3.0, 'Hero'), (1.5, 'Strong'), (0.5, 'Average'), (0.0, 'Low')]
BASE = 'https://myacollection.com'

# ---------- helpers
def read_ga(path):
    rows = [r for r in csv.reader(open(path, encoding='utf-8')) if r and not r[0].startswith('#')]
    hdr, rows = rows[0], rows[1:]
    return hdr, rows

def num(x):
    try: return float(x)
    except: return 0.0

LANG = re.compile(r'^/(en|el|de|fr|it|el-gr|en-gr)(?=/|$)')
def norm_path(p):
    p = unquote(p.split('?')[0].split('#')[0]).strip()
    p = LANG.sub('', p) or '/'
    if p.startswith('//myacollection.com'): p = p[len('//myacollection.com'):]
    if len(p) > 1 and p.endswith('/'): p = p[:-1]
    return p

def product_handle(p):
    m = re.match(r'^(?:/collections/[^/]+)?/products/([^/]+)$', p)
    return m.group(1) if m else None

def collection_handle(p):
    m = re.match(r'^/collections/([^/]+)$', p)
    return m.group(1) if m else None

def slugify(s):
    s = unicodedata.normalize('NFKD', str(s)).lower().replace('&', 'and')
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')

GREEK_TYPE = {'φόρεμα': 'dress', 'φορεμα': 'dress', 'τοπ': 'top', 'κιμονό': 'kimono', 'κιμονο': 'kimono', 'φούστα': 'skirt', 'φουστα': 'skirt',
              'παντελόνι': 'pants', 'παντελονι': 'pants', 'πουκάμισο': 'shirt', 'πουκαμισο': 'shirt', 'ολόσωμη': 'jumpsuit', 'φόρμα': '', 'φορμα': '',
              'κορμάκι': 'bodysuit', 'κάπα': 'cape', 'καπα': 'cape', 'σακάκι': 'blazer', 'μπουφάν': 'jacket', 'ζώνη': 'belt', 'σορτς': 'shorts',
              'σετ': 'set', 'μπολερό': 'bolero', 'παρεό': 'pareo', 'κολιέ': 'necklace', 'σκουλαρίκια': 'earrings', 'τσάντα': 'bag', 'στέκα': 'headband',
              'μαγιό': 'swimsuit', 'μπικίνι': 'bikini', 'γιλέκο': 'vest', 'ζακέτα': 'cardigan', 'πουλόβερ': 'sweater', 'κάλτσες': 'socks'}
COLOUR = {'μαύρο': 'Black', 'μαυρο': 'Black', 'black': 'Black', 'λευκό': 'White', 'λευκο': 'White', 'άσπρο': 'White', 'white': 'White', 'ασημί': 'Silver', 'ασημι': 'Silver', 'silver': 'Silver',
          'χρυσό': 'Gold', 'χρυσο': 'Gold', 'gold': 'Gold', 'ροζ': 'Pink', 'pink': 'Pink', 'μπλε': 'Blue', 'blue': 'Blue', 'κόκκινο': 'Red', 'κοκκινο': 'Red', 'red': 'Red',
          'πράσινο': 'Green', 'πρασινο': 'Green', 'green': 'Green', 'μπεζ': 'Beige', 'beige': 'Beige', 'εκρού': 'Ecru', 'εκρου': 'Ecru', 'ecru': 'Ecru', 'λιλά': 'Lilac', 'λιλα': 'Lilac', 'lilac': 'Lilac',
          'μωβ': 'Purple', 'purple': 'Purple', 'κίτρινο': 'Yellow', 'κιτρινο': 'Yellow', 'yellow': 'Yellow', 'πορτοκαλί': 'Orange', 'orange': 'Orange', 'γκρι': 'Grey', 'grey': 'Grey', 'gray': 'Grey',
          'καφέ': 'Brown', 'καφε': 'Brown', 'brown': 'Brown', 'φούξια': 'Fuchsia', 'fuchsia': 'Fuchsia', 'σιέλ': 'Light blue', 'σιελ': 'Light blue', 'μπορντό': 'Bordeaux', 'μπορντο': 'Bordeaux', 'bordeaux': 'Bordeaux',
          'nude': 'Nude', 'πολύχρωμο': 'Multicolour', 'πολυχρωμο': 'Multicolour', 'multi': 'Multicolour', 'λαδί': 'Olive', 'λαδι': 'Olive', 'olive': 'Olive', 'σομόν': 'Salmon', 'βεραμάν': 'Mint', 'mint': 'Mint',
          'εμπριμέ': 'Printed', 'εμπριμε': 'Printed', 'φλοράλ': 'Floral', 'floral': 'Floral', 'ζαχαρί': 'Off-white', 'ζαχαρι': 'Off-white', 'κρεμ': 'Cream', 'cream': 'Cream', 'ivory': 'Ivory', 'ιβουάρ': 'Ivory',
          'σαμπανιζέ': 'Champagne', 'champagne': 'Champagne', 'χακί': 'Khaki', 'khaki': 'Khaki', 'μέντα': 'Mint', 'κοραλί': 'Coral', 'coral': 'Coral', 'τιρκουάζ': 'Turquoise', 'turquoise': 'Turquoise',
          'ναυτικό': 'Navy', 'navy': 'Navy', 'μπλε σκούρο': 'Navy', 'ταμπά': 'Tan', 'κεραμιδί': 'Terracotta', 'terracotta': 'Terracotta', 'ρουά': 'Royal blue', 'royal': 'Royal blue',
          'μελιτζανί': 'Aubergine', 'πετρόλ': 'Petrol', 'petrol': 'Petrol', 'ανθρακί': 'Charcoal', 'διάφανο': 'Sheer', 'λεοπάρ': 'Leopard', 'leopard': 'Leopard', 'ζέβρα': 'Zebra', 'animal': 'Animal print',
          'ριγέ': 'Striped', 'stripes': 'Striped', 'καρό': 'Checked', 'πουά': 'Polka dot', 'ροδακινί': 'Peach', 'peach': 'Peach', 'βυσσινί': 'Cherry', 'δαμασκηνί': 'Plum', 'plum': 'Plum'}

def colour_of(vals):
    out = []
    for v in vals:
        v0 = v.strip()
        key = v0.lower()
        hit = None
        for k, lab in COLOUR.items():
            if key == k or key.startswith(k + ' ') or key.startswith(k + '/') or (' ' + k) in key:
                hit = lab; break
        out.append(hit or v0)
    return out

def norm_type(pt, title):
    t = (pt or '').strip().lower()
    m = {'dresses': 'Dresses', 'dress': 'Dresses', 'tops': 'Tops', 'top': 'Tops', 'shirt': 'Tops', 'skirts': 'Skirts', 'skirt': 'Skirts', 'kimono': 'Kimono dresses',
         'kids': 'Kids', 'jumpsuit': 'Jumpsuits', 'jumpsuits': 'Jumpsuits', 'pants': 'Pants', 'accessories': 'Accessories', 'cape': 'Capes', 'jacket': 'Blazers & jackets', 'blazer': 'Blazers & jackets'}
    if t in m: return m[t]
    tl = title.lower()
    for g, e in GREEK_TYPE.items():
        if g in tl:
            return {'dress': 'Dresses', 'top': 'Tops', 'kimono': 'Kimono dresses', 'skirt': 'Skirts', 'pants': 'Pants', 'shirt': 'Tops', 'jumpsuit': 'Jumpsuits', 'bodysuit': 'Tops', 'cape': 'Capes', 'blazer': 'Blazers & jackets', 'jacket': 'Blazers & jackets'}.get(e, 'Other')
    return 'Other'

def season_of(tags, colls):
    tg = ' '.join(tags).lower(); cs = ' '.join(colls)
    if 'house of peonies' in tg or 'house-of-peonies' in cs or 'peonies-' in cs: return 'House of Peonies FW27'
    if 'ss26 sirens' in tg or 'ss26-sirens' in cs: return 'Sirens SS26'
    if 'f25 lotus' in tg or 'f25-lotus' in cs: return 'Lotus F25'
    if 'ss25 swan' in tg or 'ss25-swan' in cs: return 'Swan SS25'
    if 'archive sale' in tg or 'archive-sale' in cs: return 'Archive'
    return 'Other / older'

def price_band(p):
    if p is None: return ''
    return 'Under €80' if p < 80 else 'From €80 to €129' if p < 130 else 'From €130 to €199' if p < 200 else 'From €200 to €299' if p < 300 else '€300 and over'

# ---------- catalogue
site = json.load(open('site.json'))
PRODUCTS = site['products']; MEMB = site['membership']; COLLS = {c['handle']: c for c in site['collections']}
NAV = [  # from the live site navigation, in menu order
    ('house-of-peonies-fw27', 'House of Peonies FW27', 'House of Peonies FW27', 'root'),
    ('peonies-dress', 'Peonies · Dresses', 'House of Peonies FW27', 'sub'), ('peonies-tops', 'Peonies · Tops', 'House of Peonies FW27', 'sub'), ('peonies-skirts', 'Peonies · Skirts', 'House of Peonies FW27', 'sub'),
    ('peonies-kimono-dress', 'Peonies · Kimono dresses', 'House of Peonies FW27', 'sub'), ('peonies-pants', 'Peonies · Pants', 'House of Peonies FW27', 'sub'), ('peonies-jumpsuits', 'Peonies · Jumpsuits', 'House of Peonies FW27', 'sub'),
    ('peonies-blazers', 'Peonies · Blazers', 'House of Peonies FW27', 'sub'), ('underdress', 'Peonies · Underdress', 'House of Peonies FW27', 'sub'),
    ('ss26-sirens', 'Sirens SS26', 'Sirens SS26', 'root'),
    ('ss26-sirens-dresses', 'Sirens · Dresses', 'Sirens SS26', 'sub'), ('ss26-sirens-kimono-dresses', 'Sirens · Kimono dresses', 'Sirens SS26', 'sub'), ('ss26-sirens-tops', 'Sirens · Tops', 'Sirens SS26', 'sub'),
    ('ss26-sirens-skirts', 'Sirens · Skirts', 'Sirens SS26', 'sub'), ('ss26-sirens-pants', 'Sirens · Pants', 'Sirens SS26', 'sub'), ('ss26-sirens-jumpsuits', 'Sirens · Jumpsuits', 'Sirens SS26', 'sub'),
    ('ss26-sirens-accessories', 'Sirens · Accessories', 'Sirens SS26', 'sub'), ('ss26-sirens-kids', 'Sirens · Kids', 'Sirens SS26', 'sub'),
    ('archive-sale', 'Archive Sale', 'Sale & archive', 'root'),
    ('monochrome', 'Ρούχα Περίστασης (Occasion wear)', 'Occasion wear', 'root'),
    ('all', 'All products (Shop now)', 'Shop', 'root'),
]
NAVIDX = {h: (lab, grp, kind) for h, lab, grp, kind in NAV}

# ---------- GA4 pages
def agg_pages(path):
    hdr, rows = read_ga(path)
    ix = {k: hdr.index(k) for k in hdr}
    prod = collections.defaultdict(lambda: collections.Counter()); coll = collections.defaultdict(lambda: collections.Counter()); site_tot = collections.Counter(); prod_paths = collections.defaultdict(set)
    for r in rows:
        p = norm_path(r[0]); vals = {'views': num(r[ix['Views']]), 'users': num(r[ix['Active users']]), 'sess': num(r[ix['Sessions']]), 'engs': num(r[ix['Engaged sessions']]), 'atc_pg': num(r[ix['Add to carts']]), 'purch_pg': num(r[ix['Ecommerce purchases']])}
        site_tot.update(vals)
        h = product_handle(p)
        if h: prod[h].update(vals); prod_paths[h].add(r[0]); continue
        c = collection_handle(p)
        if c: coll[c].update(vals)
    return prod, coll, site_tot, prod_paths, len(rows)

P90, C90, S90, PATHS90, N90 = agg_pages('data/pages90.csv')
P30, C30, S30, _, _ = agg_pages('data/pages30.csv')
P12, C12, S12, _, N12 = agg_pages('data/pages12m.csv')

# ---------- Search Console (via GA4 organic landing page report)
hdr, rows = read_ga('data/gsc.csv'); ix = {k: hdr.index(k) for k in hdr}
G = collections.defaultdict(lambda: collections.Counter()); GC = collections.defaultdict(lambda: collections.Counter()); gsc_tot = collections.Counter(); gsc_rows = len(rows); gsc_prod_rows = 0
for r in rows:
    p = norm_path(r[0]); v = {'clicks': num(r[ix['Organic Google Search clicks']]), 'impr': num(r[ix['Organic Google Search impressions']])}
    gsc_tot.update(v)
    h = product_handle(p)
    if h: G[h].update(v); gsc_prod_rows += 1; continue
    c = collection_handle(p)
    if c: GC[c].update(v)

# ---------- Ecommerce items (item name -> handle)
hdr, rows = read_ga('data/items.csv'); ix = {k: hdr.index(k) for k in hdr}
title_map = {}
for h, p in PRODUCTS.items():
    title_map[p['title'].strip().lower()] = h
    title_map[slugify(p['title'])] = h
    # english variant of the greek title: translate the type word
    words = p['title'].strip().lower().split()
    en = ' '.join(GREEK_TYPE.get(w, w) for w in words).replace('  ', ' ').strip()
    title_map[en] = h; title_map[slugify(en)] = h
handles = set(PRODUCTS)
first_word = collections.defaultdict(set)
for h in handles: first_word[h.split('-')[0]].add(h)
ITEMS = collections.defaultdict(lambda: collections.Counter()); items_total = collections.Counter(); items_matched = items_unmatched = 0; unmatched_names = []
for r in rows:
    name = r[0].strip(); v = {'item_views': num(r[1]), 'atc': num(r[2]), 'purch': num(r[3]), 'revenue': num(r[4])}
    items_total.update(v); items_total['n'] += 1
    key = name.lower(); h = title_map.get(key) or title_map.get(slugify(name))
    if not h:
        sl = slugify(' '.join(GREEK_TYPE.get(w, w) for w in key.split()))
        h = title_map.get(sl) or (sl if sl in handles else None)
    if not h:
        cands = first_word.get(slugify(key.split()[0]), set())
        if len(cands) == 1: h = next(iter(cands))
        else:
            # e.g. "Maeva LIMITED Dress" -> maeva-limited-dress / maeva-dress-limited
            sl2 = slugify(' '.join(GREEK_TYPE.get(w, w) for w in key.split()))
            for c in cands:
                if set(c.split('-')) == set(sl2.split('-')): h = c; break
    if h: ITEMS[h].update(v); items_matched += 1
    else: items_unmatched += 1; unmatched_names.append((name, v['item_views']))
items_matched_views = sum(ITEMS[h]['item_views'] for h in ITEMS)

# ---------- build product table
prods = {}
NAVSET = set(NAVIDX)
for h, p in PRODUCTS.items():
    colls = [c for c, hs in MEMB.items() if h in hs and c != 'all']
    pub = dt.datetime.fromisoformat(p['published_at']).date() if p.get('published_at') else None
    created = dt.datetime.fromisoformat(p['created_at']).date() if p.get('created_at') else None
    a = P90.get(h, collections.Counter()); b = P30.get(h, collections.Counter()); c12 = P12.get(h, collections.Counter()); g = G.get(h, collections.Counter()); it = ITEMS.get(h, collections.Counter())
    views_raw = a['views']
    # launch date: the publish date, unless GA4 shows history before the window (republished product)
    days_live = (TODAY - pub).days if pub else 9999
    hist_before = c12['views'] - a['views']
    if days_live < WINDOW and hist_before > max(50, 0.2 * a['views']):
        days_live = 9999  # has real history: treat as established (republished or re-tagged)
    status = 'New' if days_live < 30 else 'Ramping' if days_live < WINDOW else 'Established'
    if views_raw == 0 and status == 'Established': status = 'No data'
    # recency: last 30 days weighted 2, days 31-90 weighted 1, normalised to the 90-day scale
    views_w = (a['views'] + b['views']) / (4 / 3); users_w = (a['users'] + b['users']) / (4 / 3)
    engs = a['engs']; sess = a['sess']
    clicks = g['clicks']; impr = g['impr']
    atc = it['atc'] if it else a['atc_pg']; purch = it['purch'] if it else a['purch_pg']; revenue = it['revenue']
    # ramping products: scale signals to a full window
    scale = 1.0
    if status == 'Ramping' and days_live > 0:
        scale = WINDOW / days_live
    prices = [float(v['price']) for v in p['variants'] if v.get('price')]
    avail = [bool(v.get('available')) for v in p['variants']]
    colours = colour_of(next((o['values'] for o in p['options'] if o['name'].lower() in ('color', 'colour', 'χρώμα')), []))
    price = min(prices) if prices else None
    prods[h] = dict(pid=h, name=p['title'].strip(), slug=h, url=f'{BASE}/products/{h}', img=(p['images'][0]['src'] if p['images'] else ''),
                    type=norm_type(p.get('product_type'), p['title']), season=season_of(p.get('tags', []), colls), colour=colours[0] if len(colours) == 1 else ('Multiple' if len(colours) > 1 else ''),
                    colours=colours, price=price, price_band=price_band(price), limited=('limited' in p['title'].lower()), instock=(sum(avail) / len(avail) * 100 if avail else 0), n_var=len(avail),
                    published=pub.isoformat() if pub else '', days_live=(days_live if days_live < 9999 else 0), status=status, colls=colls, listed=bool(colls),
                    views_raw=int(views_raw), views=int(round(views_w * scale)), users=int(round(users_w * scale)), sess=int(sess), engs=int(round(engs * scale)), er=(engs / sess * 100 if sess else 0),
                    clicks=int(round(clicks * scale)), impr=int(impr), atc=int(round(atc * scale)), purch=int(purch), revenue=round(revenue), atc_raw=int(atc), clicks_raw=int(clicks),
                    views12=int(c12['views']), users12=int(c12['users']), engs12=int(c12['engs']))

# products with traffic that are no longer in the catalogue (discontinued / unpublished)
ghost = [(h, int(P90[h]['views'])) for h in P90 if h not in prods and P90[h]['views'] >= 20]
ghost.sort(key=lambda x: -x[1])

def tier_of(r):
    for th, name in TIERS:
        if r >= th: return name
    return 'Low'

def score_hub(members):
    rows = [prods[h] for h in members]
    n = max(len(rows), 1)
    scored = {}
    for k in ['score', 'score12']: pass
    tot = {k: sum(r[k] for r in rows) for k in WEIGHTS}
    used = sum(w for k, w in WEIGHTS.items() if tot[k] > 0) or 1
    tot12 = {k: sum(r[k + '12'] for r in rows) for k in WEIGHTS_LONG}
    used12 = sum(w for k, w in WEIGHTS_LONG.items() if tot12[k] > 0) or 1
    out = []
    for r in rows:
        s = sum(w * r[k] / tot[k] * 100 for k, w in WEIGHTS.items() if tot[k] > 0) / used
        ratio = s * n / 100
        prov = False
        if r['status'] in ('New', 'Ramping'):
            v = r['views_raw']
            ratio = (v * ratio + PRIOR_K * PRIOR_RATIO) / (v + PRIOR_K)
            prov = v < PRIOR_K
        s12 = sum(w * r[k + '12'] / tot12[k] * 100 for k, w in WEIGHTS_LONG.items() if tot12[k] > 0) / used12
        ratio12 = s12 * n / 100
        out.append([r['pid'], ratio, ratio12, prov, s, s12])
    out.sort(key=lambda x: -x[1])
    res = []
    rank = 0
    for pid, ratio, ratio12, prov, s, s12 in out:
        r = prods[pid]
        nodata = r['status'] == 'No data'
        if not nodata: rank += 1
        res.append([pid, 0 if nodata else rank, round(ratio * 100 / n, 4), round(ratio12 * 100 / n, 4), 1 if prov else 0])  # stored as score (share %), page recomputes ratio
    return res, tot, n

def trend_of(status, ratio, ratio12):
    if status in ('New', 'Ramping'): return 'New'
    if not ratio and not ratio12: return ''
    if not ratio12: return 'New'
    q = ratio / ratio12
    return 'Rising' if q >= 1.25 else 'Fading' if q <= 0.8 else 'Steady'

# hubs = every collection with live members and either nav or traffic
hubs = []; TIERCOUNT = {}
MEMB.setdefault('all', list(PRODUCTS)); COLLS.setdefault('all', {'title': 'All products'})
for c, members in MEMB.items():
    if c == 'all': members = list(PRODUCTS)
    members = [h for h in members if h in prods]
    cv = C90.get(c, collections.Counter()); gc = GC.get(c, collections.Counter())
    if not members and cv['views'] < 5 and gc['clicks'] == 0: continue
    LANDING = {'wedding': ('Φορέματα για γάμο (wedding dresses)', 'Wedding & occasion landing pages'), 'events': ('Φορέματα για βάπτιση (christening dresses)', 'Wedding & occasion landing pages'),
               'wedding-baptism': ('Ρούχα για Γάμο & Βάπτιση (wedding & christening)', 'Wedding & occasion landing pages'), 'dresses-wedding': ('Dresses Wedding', 'Wedding & occasion landing pages')}
    if c in LANDING: lab, grp, kind = LANDING[c][0], LANDING[c][1], 'landing'
    else: lab, grp, kind = NAVIDX.get(c, (COLLS[c]['title'], 'Not in the menu (tag, drop or older collection)', 'other'))
    if c == 'all': pass
    res, tot, n = score_hub(members) if members else ([], {k: 0 for k in WEIGHTS}, 0)
    nl = max(n - sum(1 for h in members if prods[h]['status'] == 'No data'), 1)
    tc = collections.Counter()
    for pid, rank, s, s12, prov in res:
        r = prods[pid]
        if rank == 0: tc['No data'] += 1
        elif prov or r['status'] == 'New': tc['New'] += 1
        else: tc[tier_of(s * nl / 100)] += 1
    TIERCOUNT[c] = dict(tc)
    hubs.append(dict(id=c, label=lab, title=COLLS[c]['title'], group=grp, kind=kind, nav=c in NAVSET, url=f'{BASE}/collections/{c}', n_products=n, n_nodata=tc.get('No data', 0), all=res,
                     tot=dict(views=int(sum(prods[h]['views'] for h in members)), users=int(sum(prods[h]['users'] for h in members)), engs=int(sum(prods[h]['engs'] for h in members)),
                              clicks=int(sum(prods[h]['clicks'] for h in members)), impr=int(sum(prods[h]['impr'] for h in members)), atc=int(sum(prods[h]['atc'] for h in members)), purch=int(sum(prods[h]['purch'] for h in members))),
                     hub_pages=dict(views=int(cv['views']), users=int(cv['users']), engs=int(cv['engs']), clicks=int(gc['clicks']), impr=int(gc['impr']), views12=int(C12.get(c, collections.Counter())['views']))))
HUB = {h['id']: h for h in hubs}

# main hub per product: nav sub-collection first, then nav root, then the largest other collection it belongs to
nav_order = [h for h, *_ in NAV if h != 'all']
def main_hub(r):
    subs = [c for c in nav_order if NAVIDX[c][2] == 'sub' and c in r['colls'] and c in HUB]
    if subs: return subs[0]
    roots = [c for c in nav_order if NAVIDX[c][2] == 'root' and c in r['colls'] and c in HUB]
    if roots: return roots[0]
    others = sorted([c for c in r['colls'] if c in HUB], key=lambda c: -HUB[c]['n_products'])
    return others[0] if others else 'all'

for h, r in prods.items():
    mh = main_hub(r); r['hub'] = mh; r['hub_label'] = HUB[mh]['label']
    hb = HUB[mh]; nl = max(hb['n_products'] - hb['n_nodata'], 1)
    row = next((x for x in hb['all'] if x[0] == h), None)
    if row:
        pid, rank, s, s12, prov = row
        r['rank'] = rank; r['score'] = round(s, 3); r['ratio'] = round(s * nl / 100, 2); r['ratio12'] = round(s12 * nl / 100, 2); r['prov'] = bool(prov)
    else:
        r['rank'] = 0; r['score'] = 0; r['ratio'] = 0; r['ratio12'] = 0; r['prov'] = False
    r['tier'] = 'No data' if r['status'] == 'No data' else 'New' if (r['prov'] or r['status'] == 'New') else tier_of(r['ratio'])
    r['trend'] = trend_of(r['status'], r['ratio'], r['ratio12'])

# ---------- attribute demand (share of product views)
def attr_table(key, filt=lambda r: True):
    agg = collections.defaultdict(lambda: collections.Counter())
    for r in prods.values():
        if not filt(r): continue
        vals = r[key] if isinstance(r[key], list) else [r[key]]
        for v in vals:
            if not v: continue
            a = agg[v]; a['views'] += r['views_raw']; a['users'] += r['users']; a['clicks'] += r['clicks_raw']; a['atc'] += r['atc_raw']; a['purch'] += r['purch']; a['n'] += 1
    return sorted([dict(label=k, **{kk: int(v) for kk, v in a.items()}) for k, a in agg.items()], key=lambda x: -x['views'])
ATTR = {'type': attr_table('type'), 'season': attr_table('season'), 'colours': attr_table('colours'), 'price_band': attr_table('price_band'),
        'stock': attr_table('stock_band')} if False else {}
for r in prods.values():
    r['stock_band'] = 'Sold out' if r['instock'] == 0 else 'Low stock (under half of sizes)' if r['instock'] < 50 else 'Mostly in stock' if r['instock'] < 100 else 'Fully in stock'
ATTR = {'type': attr_table('type'), 'season': attr_table('season'), 'colours': attr_table('colours'), 'price_band': attr_table('price_band'), 'stock_band': attr_table('stock_band'),
        'type_dresses_colour': attr_table('colours', lambda r: r['type'] == 'Dresses')}

# ---------- hub families (collection page demand)
FAM = {'House of Peonies FW27': lambda c: c.startswith('peonies-') or c == 'house-of-peonies-fw27' or c == 'underdress',
       'Sirens SS26': lambda c: c.startswith('ss26-sirens'),
       'Wedding, baptism & events': lambda c: c in ('wedding', 'wedding-baptism', 'events', 'dresses-wedding', 'monochrome'),
       'Sale & archive': lambda c: 'sale' in c or 'offers' in c or c == 'archive-sale' or 'blackfriday' in c or 'black-fr' in c,
       'Shop all': lambda c: c == 'all'}
hub_pages = []
allc = set(C90) | set(GC)
assigned = set()
for fam, fn in FAM.items():
    cs = [c for c in allc if fn(c)]; assigned |= set(cs)
    pages = sorted([dict(path='/collections/' + c, views=int(C90.get(c, collections.Counter())['views']), clicks=int(GC.get(c, collections.Counter())['clicks']), impr=int(GC.get(c, collections.Counter())['impr'])) for c in cs], key=lambda x: -x['views'])
    hub_pages.append(dict(label=fam, views=sum(p['views'] for p in pages), clicks=sum(p['clicks'] for p in pages), impr=sum(p['impr'] for p in pages), pages=pages))
rest = [c for c in allc if c not in assigned]
pages = sorted([dict(path='/collections/' + c, views=int(C90.get(c, collections.Counter())['views']), clicks=int(GC.get(c, collections.Counter())['clicks']), impr=int(GC.get(c, collections.Counter())['impr'])) for c in rest], key=lambda x: -x['views'])
hub_pages.append(dict(label='Older collections & other pages', views=sum(p['views'] for p in pages), clicks=sum(p['clicks'] for p in pages), impr=sum(p['impr'] for p in pages), pages=pages))

# ---------- coverage
PL = list(prods.values())
prod_views_total = sum(r['views_raw'] for r in PL)
all_prod_views_ga = sum(v['views'] for v in P90.values())
cov = dict(products=len(PL), product_views=int(prod_views_total), ga_rows=N90, ga_rows12=N12, ga_product_paths=len(P90), ga_product_views=int(all_prod_views_ga),
           ghost=len(ghost), ghost_views=int(sum(v for _, v in ghost)), items_n=int(items_total['n']), items_matched=items_matched, item_views_total=int(items_total['item_views']), item_views_matched=int(items_matched_views),
           gsc_rows=gsc_rows, gsc_product_rows=gsc_prod_rows, gsc_clicks_total=int(gsc_tot['clicks']), gsc_product_clicks=int(sum(G[h]['clicks'] for h in G)),
           newcomers=sum(1 for r in PL if r['status'] in ('New', 'Ramping')), new_lt30=sum(1 for r in PL if r['status'] == 'New'), ramping=sum(1 for r in PL if r['status'] == 'Ramping'),
           provisional=sum(1 for r in PL if r['tier'] == 'New'), nodata=sum(1 for r in PL if r['status'] == 'No data'), hubs=len(hubs), nav_hubs=sum(1 for h in hubs if h['nav']),
           listed=sum(1 for r in PL if r['listed']), unlisted_with_views=sum(1 for r in PL if not r['listed'] and r['views_raw'] > 0), collections_crawled=len(MEMB),
           soldout=sum(1 for r in PL if r['instock'] == 0), soldout_views=int(sum(r['views_raw'] for r in PL if r['instock'] == 0)))
site_er = S90['engs'] / S90['sess'] * 100 if S90['sess'] else 0
pe = sum(r['engs'] for r in PL); ps = sum(r['sess'] for r in PL); product_er = pe / ps * 100 if ps else 0

cols = ['pid', 'name', 'slug', 'img', 'type', 'season', 'colour', 'colours', 'price', 'price_band', 'limited', 'instock', 'stock_band', 'n_var', 'published', 'days_live', 'status', 'colls', 'listed', 'hub', 'hub_label',
        'views_raw', 'views', 'users', 'sess', 'engs', 'er', 'clicks', 'impr', 'atc', 'purch', 'revenue', 'views12', 'rank', 'score', 'ratio', 'ratio12', 'prov', 'tier', 'trend']
D = dict(product_cols=cols, products=[[r[c] if not isinstance(r[c], float) else round(r[c], 2) for c in cols] for r in PL], hubs=hubs, tiers=TIERCOUNT, hub_pages=hub_pages, attr=ATTR, coverage=cov,
         site_totals=dict(views=int(S90['views']), users=int(S90['users']), sess=int(S90['sess']), engs=int(S90['engs']), gsc_clicks=int(gsc_tot['clicks']), gsc_impr=int(gsc_tot['impr']), atc=int(items_total['atc']), purch=int(items_total['purch']), revenue=round(items_total['revenue'])),
         site_er=round(site_er, 1), product_er=round(product_er, 1), ghost=ghost[:40], unmatched_items=sorted(unmatched_names, key=lambda x: -x[1])[:40],
         period=dict(start=PERIOD_START.isoformat(), end=PERIOD_END.isoformat(), start12='2025-09-23', crawled=TODAY.isoformat()))
json.dump(D, open('data.json', 'w'), ensure_ascii=False)
print('products', len(PL), 'hubs', len(hubs), 'ghost', len(ghost), 'items matched', items_matched, '/', items_total['n'], f"({items_matched_views/items_total['item_views']*100:.0f}% of item views)")
print('coverage', cov)
print('tiers', collections.Counter(r['tier'] for r in PL), 'status', collections.Counter(r['status'] for r in PL), 'trend', collections.Counter(r['trend'] for r in PL))
print('top', [(r['name'], r['hub'], r['ratio'], r['tier']) for r in sorted(PL, key=lambda r: -r['views_raw'])[:8]])
print('unmatched items', unmatched_names[:15])
print('ghost', ghost[:10])
