import json,urllib.request,time,sys
def get(u):
    for i in range(4):
        try:
            r=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=40);return json.load(r)
        except Exception as e:
            time.sleep(2*(i+1)); err=e
    print('FAIL',u,err); return None
cols=json.load(open('collections.json'))['collections']
prods={}; memb={}
for c in cols:
    h=c['handle']; page=1; memb[h]=[]
    while True:
        d=get(f'https://myacollection.com/collections/{h}/products.json?limit=250&page={page}')
        if not d or not d.get('products'): break
        for p in d['products']:
            memb[h].append(p['handle']); prods[p['handle']]=p
        if len(d['products'])<250: break
        page+=1
    print(h,len(memb[h]),flush=True)
# all products
page=1
while True:
    d=get(f'https://myacollection.com/products.json?limit=250&page={page}')
    if not d or not d.get('products'): break
    for p in d['products']: prods.setdefault(p['handle'],p)
    if len(d['products'])<250: break
    page+=1
json.dump({'collections':cols,'membership':memb,'products':prods},open('site.json','w'))
print('products',len(prods))
