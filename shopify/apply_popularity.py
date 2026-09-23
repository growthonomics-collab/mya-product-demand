"""Apply the popularity sort to the MYA Shopify store.

What it does (Admin GraphQL API):
  1. writes four metafields on every product (namespace "custom"):
       popularity_ratio (number_decimal), merch_tier, popularity_trend, popularity_updated (single_line_text_field)
  2. for every collection in popularity_payload.json: sets the collection sort order to MANUAL and reorders its
     products into the popularity order (sold-out products last, unless the payload was built otherwise).

Usage:
  python apply_popularity.py --shop myacollection.myshopify.com --token shpat_xxx            # dry run: prints what it would do
  python apply_popularity.py --shop myacollection.myshopify.com --token shpat_xxx --apply    # writes to the store
  add --metafields-only or --collections-only to do one half.

Token: Shopify admin > Settings > Apps and sales channels > Develop apps > create app > Admin API scopes
  write_products, read_products  (write_products covers collections and product metafields) > install > copy the
  Admin API access token. Never commit the token to this repo.

Limits handled: 25 metafields per metafieldsSet call, 250 moves per collectionReorderProducts call, retry on throttle.
Automated (smart) collections cannot be sorted manually by Shopify: the script reports them and skips them.
"""
import argparse, json, sys, time, urllib.request

API = '2025-07'

def gql(shop, token, query, variables):
    body = json.dumps({'query': query, 'variables': variables}).encode()
    for attempt in range(6):
        req = urllib.request.Request(f'https://{shop}/admin/api/{API}/graphql.json', data=body, headers={'Content-Type': 'application/json', 'X-Shopify-Access-Token': token})
        try:
            with urllib.request.urlopen(req, timeout=60) as r: out = json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(2 * (attempt + 1)); continue
            raise
        if 'errors' in out and any('THROTTLED' in str(e.get('extensions', {}).get('code', '')) for e in out['errors']):
            time.sleep(2 * (attempt + 1)); continue
        if 'errors' in out: raise SystemExit('GraphQL error: ' + json.dumps(out['errors'], ensure_ascii=False))
        return out['data']
    raise SystemExit('throttled too many times')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shop', required=True); ap.add_argument('--token', required=True)
    ap.add_argument('--payload', default='popularity_payload.json')
    ap.add_argument('--apply', action='store_true', help='write to the store (default is dry run)')
    ap.add_argument('--metafields-only', action='store_true'); ap.add_argument('--collections-only', action='store_true')
    a = ap.parse_args()
    pay = json.load(open(a.payload, encoding='utf-8'))
    dry = not a.apply
    print(('DRY RUN: ' if dry else 'APPLYING: ') + f"{len(pay['products'])} products, {len(pay['collections'])} collections, data of {pay['updated']}, sold-out last = {pay['sold_out_last']}")

    # ---- 1. metafields
    if not a.collections_only:
        mf = []
        for p in pay['products']:
            gid = f"gid://shopify/Product/{p['id']}"
            mf += [dict(ownerId=gid, namespace='custom', key='popularity_ratio', type='number_decimal', value=str(p['popularity_ratio'])),
                   dict(ownerId=gid, namespace='custom', key='merch_tier', type='single_line_text_field', value=p['merch_tier']),
                   dict(ownerId=gid, namespace='custom', key='popularity_trend', type='single_line_text_field', value=p['popularity_trend'] or 'n/a'),
                   dict(ownerId=gid, namespace='custom', key='popularity_updated', type='single_line_text_field', value=pay['updated'])]
        print(f'metafields to set: {len(mf)} ({len(mf)//25 + 1} calls)')
        if not dry:
            Q = 'mutation($m:[MetafieldsSetInput!]!){metafieldsSet(metafields:$m){userErrors{field message code}}}'
            done = 0
            for i in range(0, len(mf), 25):
                d = gql(a.shop, a.token, Q, {'m': mf[i:i+25]})
                errs = d['metafieldsSet']['userErrors']
                if errs: print('  metafield errors:', errs)
                done += 25;
                if done % 500 == 0: print(f'  {min(done, len(mf))}/{len(mf)}')
            print('metafields written')

    # ---- 2. collection order
    if not a.metafields_only:
        QS = 'mutation($input:CollectionInput!){collectionUpdate(input:$input){collection{id handle sortOrder ruleSet{rules{column}}} userErrors{field message}}}'
        QG = 'query($id:ID!){collection(id:$id){id handle sortOrder productsCount{count} ruleSet{rules{column}}}}'
        QR = 'mutation($id:ID!,$moves:[MoveInput!]!){collectionReorderProducts(id:$id,moves:$moves){job{id done} userErrors{field message}}}'
        for c in pay['collections']:
            gid = f"gid://shopify/Collection/{c['id']}"
            moves = [dict(id=f"gid://shopify/Product/{x['id']}", newPosition=str(i)) for i, x in enumerate(c['order'])]
            head = ', '.join(x['handle'] for x in c['order'][:5])
            if dry:
                print(f"  {c['handle']}: {len(moves)} products -> set MANUAL, order starts {head} ..."); continue
            info = gql(a.shop, a.token, QG, {'id': gid})['collection']
            if info is None: print(f"  {c['handle']}: collection not found, skipped"); continue
            if info.get('ruleSet') and info['ruleSet'].get('rules'):
                print(f"  {c['handle']}: AUTOMATED collection (rules: {[r['column'] for r in info['ruleSet']['rules']]}). Shopify does not allow a manual order here. Convert it to a manual collection in the admin, or sort it with a metafield-based sorting app, then rerun."); continue
            if info['sortOrder'] != 'MANUAL':
                d = gql(a.shop, a.token, QS, {'input': {'id': gid, 'sortOrder': 'MANUAL'}})
                if d['collectionUpdate']['userErrors']: print(f"  {c['handle']}: could not set MANUAL:", d['collectionUpdate']['userErrors']); continue
            for i in range(0, len(moves), 250):
                d = gql(a.shop, a.token, QR, {'id': gid, 'moves': moves[i:i+250]})
                if d['collectionReorderProducts']['userErrors']: print(f"  {c['handle']}: reorder errors:", d['collectionReorderProducts']['userErrors'])
                time.sleep(1.5)  # reorder runs as a background job; give it room
            print(f"  {c['handle']}: {len(moves)} products reordered (starts {head})")
    print('done' if not dry else 'dry run finished, nothing written. Rerun with --apply to write.')

if __name__ == '__main__':
    main()
