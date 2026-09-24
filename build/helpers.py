import csv, json, re, math, datetime as dt, collections, unicodedata
from urllib.parse import unquote
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
