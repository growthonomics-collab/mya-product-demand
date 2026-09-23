# Ταξινόμηση κατά δημοτικότητα (sort by popularity) για το myacollection.com

Αυτός ο φάκελος περιέχει όλα όσα χρειάζονται για να ταξινομηθούν οι συλλογές του Shopify με βάση το Popularity Ratio του dashboard. Δεδομένα: 25 Ιουνίου έως 22 Σεπτεμβρίου 2026, κατάλογος και απόθεμα της 23 Σεπτεμβρίου 2026.

## Τι περιέχει

| Αρχείο | Τι είναι |
|---|---|
| `popularity_products.csv` | Ένα προϊόν ανά γραμμή (459). Handle, Shopify product ID, κύρια συλλογή, Popularity Ratio, tier (Hero / Strong / Average / Low / New), trend, ηλικία, θέση στην κύρια συλλογή, sold out, προβολές, καλάθι, αγορές. |
| `collection_order_all.csv` | Η σειρά εμφάνισης για κάθε συλλογή, όλες μαζί (24 συλλογές: μενού + σελίδες γάμου/βάπτισης). Στήλη `position` = η θέση που πρέπει να πάρει το προϊόν. |
| `collection_order/<handle>.csv` | Το ίδιο, ένα αρχείο ανά συλλογή, για χειροκίνητη ταξινόμηση. |
| `popularity_payload.json` | Τα ίδια δεδομένα σε μορφή για το script. |
| `apply_popularity.py` | Script που γράφει τα metafields σε κάθε προϊόν και βάζει κάθε συλλογή σε manual sort με τη σειρά δημοτικότητας, μέσω Shopify Admin API. |
| `popular-badge.liquid` | Snippet για το θέμα (Be Yours) που δείχνει ετικέτα «Popular» στα Hero και «New in» στα νέα προϊόντα. |

## Κανόνες σειράς

1. Μέσα σε κάθε συλλογή τα προϊόντα κατεβαίνουν κατά Popularity Ratio (υψηλότερο πρώτο). Το ratio είναι το ratio του προϊόντος μέσα στη συγκεκριμένη συλλογή, όχι το γενικό.
2. Τα sold out προϊόντα (κανένα διαθέσιμο μέγεθος στις 23/9) πηγαίνουν στο τέλος της συλλογής, με τη δική τους σειρά δημοτικότητας. Αν προτιμάτε να μείνουν στη θέση τους, το `build/build_shopify.py` ξανατρέχει με `SOLD_OUT_LAST = False`.
3. Τα νέα προϊόντα (κάτω από 30 ημέρες ή κάτω από 100 προβολές) έχουν προσωρινό ratio 1.50 και ετικέτα New, οπότε μπαίνουν στις πρώτες σειρές αλλά όχι πάνω από τα Hero.
4. Η συλλογή `/collections/all` δεν μπορεί να ταξινομηθεί χειροκίνητα στο Shopify, γι' αυτό δεν περιλαμβάνεται.

## Τρόπος Α: αυτόματα με το script (προτείνεται)

1. Shopify admin → Settings → Apps and sales channels → Develop apps → Create an app. Στα Admin API scopes δώστε `read_products` και `write_products`. Install app και αντιγράψτε το Admin API access token (ξεκινά με `shpat_`). Μην το βάλετε ποτέ σε αυτό το repo.
2. Δοκιμή χωρίς αλλαγές:
   `python apply_popularity.py --shop myacollection.myshopify.com --token shpat_xxx`
3. Εφαρμογή:
   `python apply_popularity.py --shop myacollection.myshopify.com --token shpat_xxx --apply`

Το script γράφει σε κάθε προϊόν τα metafields `custom.popularity_ratio`, `custom.merch_tier`, `custom.popularity_trend`, `custom.popularity_updated`, και σε κάθε συλλογή αλλάζει το sort σε Manual και εφαρμόζει τη σειρά. Χρειάζεται Python 3, χωρίς επιπλέον βιβλιοθήκες.

Προσοχή: αν κάποια συλλογή είναι automated (με κανόνες, π.χ. «tag = SS26 SIRENS»), το Shopify δεν επιτρέπει manual sort. Το script το αναφέρει και την παραλείπει. Δύο επιλογές: να γίνει manual collection (Products → Collections → η συλλογή → αλλαγή σε manual και προσθήκη των προϊόντων της) ή να χρησιμοποιηθεί app ταξινόμησης που διαβάζει metafield (τα metafields γράφονται κανονικά σε όλα τα προϊόντα).

## Τρόπος Β: χειροκίνητα στο admin

Products → Collections → επιλέξτε τη συλλογή → Sort: Manually → σύρετε τα προϊόντα στη σειρά του `collection_order/<handle>.csv`. Πρακτικό μόνο για μικρές συλλογές (Peonies Tops, Sirens Skirts). Για Sirens SS26 (234 προϊόντα) χρησιμοποιήστε το script.

## Ετικέτα Popular στο θέμα

Online Store → Themes → Edit code → Snippets → Add a new snippet με όνομα `popular-badge`, επικολλήστε το περιεχόμενο του `popular-badge.liquid`. Μετά, στο snippet της κάρτας προϊόντος (στο Be Yours συνήθως `snippets/product-card.liquid` ή `card-product.liquid`), μέσα στο wrapper της εικόνας, προσθέστε `{% render 'popular-badge', product: card_product %}` (ή το όνομα της μεταβλητής προϊόντος που χρησιμοποιεί το snippet). Δείχνει «Popular» μόνο στα 13 Hero και «New in» στα νέα.

## Ανανέωση

Κάθε μήνα όσο τρέχει η House of Peonies, κάθε τρίμηνο μετά: νέες εξαγωγές GA4 (βλ. Formula στο dashboard), `python build/crawl.py`, `python build/build_data.py`, `python build/build_page.py`, `python build/build_shopify.py`, και ξανά `apply_popularity.py --apply`. Το script ξαναγράφει τα metafields και τη σειρά, δεν χρειάζεται καθάρισμα.
