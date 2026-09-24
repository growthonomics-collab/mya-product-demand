# MYA Collection product demand dashboard

Password-protected dashboard built by Growth-onomics: https://growthonomics-collab.github.io/mya-product-demand/

- `index.html`, `data1.js`, `data2.js`: the dashboard. Every product with traffic since August 2023 (live and past), monthly GA4 and Search Console data, scored in the browser for any period chosen in the period bar. Data AES-encrypted; password held by Growth-onomics and MYA.
- `shopify/`: sort-by-popularity package for the store, built on the last 90 days (metafield values, manual order per collection, Admin API script, badge snippet). Instructions in Greek in `shopify/README.md`.
- `build/`: scripts that rebuild everything from the GA4 / Search Console exports and the live catalogue.
