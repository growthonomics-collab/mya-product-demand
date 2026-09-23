"""Turn data.json into the Shopify sort-by-popularity package: metafield values per product and the manual
product order per collection. Sold-out products (no available variant at build time) go to the end of each
collection by default, in their own popularity order; set SOLD_OUT_LAST = False to sort purely by popularity."""
import json, csv, os, datetime as dt

SOLD_OUT_LAST = True
OUT = 'repo/shopify'
os.makedirs(f'{OUT}/collection_order', exist_ok=True)
D = json.load(open('data.json')); site = json.load(open('site.json'))
C = D['product_cols']; PL = [dict(zip(C, a)) for a in D['products']]; P = {o['pid']: o for o in PL}
PID = {h: p['id'] for h, p in site['products'].items()}
CID = {c['handle']: c['id'] for c in site['collections']}
CTITLE = {c['handle']: c['title'] for c in site['collections']}
HUB = {h['id']: h for h in D['hubs']}
stamp = D['period']['crawled']

def tier_of(x): return 'Hero' if x >= 3 else 'Strong' if x >= 1.5 else 'Average' if x >= 0.5 else 'Low'

# ---- 1. one row per product: the metafield values (main collection)
rows = []
for o in sorted(PL, key=lambda o: (-o['ratio'], o['name'])):
    rows.append(dict(handle=o['pid'], product_id=PID[o['pid']], title=o['name'], main_collection=o['hub'], main_collection_title=o['hub_label'],
                     popularity_ratio=f"{o['ratio']:.2f}", merch_tier=o['tier'], popularity_trend=o['trend'], age_status=o['status'], rank_in_main_collection=o['rank'] or '',
                     sold_out='yes' if o['instock'] == 0 else 'no', views_90d=o['views_raw'], add_to_cart=o['atc'], purchased=o['purch'], popularity_updated=stamp,
                     url='https://myacollection.com/products/' + o['pid']))
with open(f'{OUT}/popularity_products.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

# ---- 2. manual order per collection (menu collections + wedding landing collections; 'all' cannot be reordered)
TARGET = [h for h in D['hubs'] if h['id'] != 'all' and h['n_products'] > 0 and h['kind'] in ('root', 'sub', 'landing')]
orders = {}; allrows = []
for h in TARGET:
    nl = max(h['n_products'] - (h['n_nodata'] or 0), 1)
    items = []
    for pid, rank, score, score12, prov in h['all']:
        o = P[pid]; ratio = round(score * nl / 100, 2)
        tier = 'No data' if rank == 0 else 'New' if (prov or o['status'] == 'New') else tier_of(ratio)
        items.append(dict(handle=pid, product_id=PID[pid], title=o['name'], ratio_in_collection=f'{ratio:.2f}', tier=tier, sold_out='yes' if o['instock'] == 0 else 'no', views_90d=o['views_raw']))
    # h['all'] is already sorted by ratio (no-data products last); move sold-out to the end keeping their relative order
    if SOLD_OUT_LAST:
        items = [x for x in items if x['sold_out'] == 'no'] + [x for x in items if x['sold_out'] == 'yes']
    for i, x in enumerate(items, 1): x['position'] = i
    orders[h['id']] = items
    with open(f"{OUT}/collection_order/{h['id']}.csv", 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=['position', 'handle', 'product_id', 'title', 'ratio_in_collection', 'tier', 'sold_out', 'views_90d']); w.writeheader(); w.writerows(items)
    for x in items: allrows.append(dict(collection_handle=h['id'], collection_id=CID.get(h['id'], ''), collection_title=CTITLE.get(h['id'], h['label']), **x))
with open(f'{OUT}/collection_order_all.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=list(allrows[0])); w.writeheader(); w.writerows(allrows)

# ---- 3. machine-readable payload for apply_popularity.py
json.dump(dict(updated=stamp, sold_out_last=SOLD_OUT_LAST,
               products=[dict(id=r['product_id'], handle=r['handle'], popularity_ratio=r['popularity_ratio'], merch_tier=r['merch_tier'], popularity_trend=r['popularity_trend'], age_status=r['age_status'], main_collection=r['main_collection']) for r in rows],
               collections=[dict(id=CID[h], handle=h, title=CTITLE.get(h, ''), order=[dict(id=x['product_id'], handle=x['handle']) for x in orders[h]]) for h in orders if h in CID]),
          open(f'{OUT}/popularity_payload.json', 'w'), ensure_ascii=False, indent=1)
print('products', len(rows), 'collections', len(orders), [(h, len(v)) for h, v in orders.items()])
