# Build scripts

- `crawl.py`: reads the live Shopify catalogue (collections.json, products.json) into site.json.
- `build_data.py` + `build_page.py` + `template.html`: the first, 90-day version of the dashboard (still used by build_shopify.py for the store sort order).
- `build_history.py` + `build_page2.py` + `body2.html` + `app2.js` + `helpers.py`: the current dashboard, monthly history since Aug 2023, scored client-side for any period.
- `build_shopify.py`: the Shopify sort-by-popularity package in ../shopify.
- `not_live.json`: product handles that answered 404 on the live site at build time.

The GA4 / Search Console exports (hist/*.csv, ~60 MB) are not in the repo; a copy is in Downloads/MYA product demand/exports_history on the Growth-onomics Mac mini. File naming: pages_products_YYYYMMDD_YYYYMMDD.csv, pages_collections_..., items_..., gsc_YYYYMMDD_YYYYMMDD.csv.
