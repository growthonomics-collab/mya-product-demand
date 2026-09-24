"""Assemble the v2 page: CSS from template.html, body2.html, app2.js; encrypt data2.json with the password."""
import json, os, base64, hashlib, sys, re
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
PW = sys.argv[1] if len(sys.argv) > 1 else 'MYA2026'
OUT = 'repo'; os.makedirs(OUT, exist_ok=True)
t = open('template.html', encoding='utf-8').read()
head = t[:t.index('</head>')]
head = head.replace('<title>MYA Product Demand</title>', '<title>MYA Product Demand</title>')
extra_css = """
.periodbar{background:var(--surface-2);border-bottom:1px solid var(--line);position:sticky;top:64px;z-index:29}
.pb-row{display:flex;gap:14px;align-items:flex-end;flex-wrap:wrap;padding:12px 0 6px}
.pb-summary{font-size:13px;color:var(--ink-2);align-self:center;margin-left:auto;text-align:right}
.pb-summary b{color:var(--ink);font-weight:500}
.pb-chart{padding-bottom:8px}
.pb-chart svg{width:100%;height:70px}
.pbar{fill:var(--line-strong);cursor:pointer}.pbar.in{fill:var(--taupe)}.pbar:hover{fill:var(--accent-ink)}
.thumb-x{display:inline-flex;align-items:center;justify-content:center;font-family:var(--serif);font-size:18px;color:var(--ink-3)}
.noimg{display:flex;align-items:center;justify-content:center;height:100%;padding:12px;text-align:center;font-family:var(--serif);font-size:18px;color:var(--ink-3)}
.chip.gone{background:var(--surface-2);color:var(--ink-3);border-style:dashed}
.soldout.gone{background:var(--ink);color:var(--bg)}
.legend .l-c::before{background:var(--c)}
.seasons{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}
.season ol{margin:0;padding:0;list-style:none}
.season li{display:flex;align-items:center;gap:9px;padding:5px 0;border-bottom:1px dashed var(--line);font-size:12.5px}
.season li:last-child{border-bottom:0}
.season li .thumb{width:32px;height:40px}
.season li a{font-family:var(--serif);font-size:14px;text-decoration:none;flex:1;min-width:0;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;line-height:1.2}
.season li .qn{color:var(--ink-2);white-space:nowrap;font-size:11.5px}
.season figcaption{flex-direction:column;align-items:flex-start;gap:2px}
.season figcaption h3 a{text-decoration:none}.season figcaption h3 a:hover{text-decoration:underline}
@media (max-width:700px){.periodbar{position:static}.pb-summary{margin-left:0;text-align:left}}
"""
head = head.replace('body.locked > :not(#lock){visibility:hidden}\n</style>', 'body.locked > :not(#lock){visibility:hidden}\n' + extra_css + '</style>')
body = open('body2.html', encoding='utf-8').read()
js = open('app2.js', encoding='utf-8').read()
data = open('data2.json', 'rb').read()
salt, iv = os.urandom(16), os.urandom(12)
key = hashlib.pbkdf2_hmac('sha256', PW.encode(), salt, 200000, 32)
ct = AESGCM(key).encrypt(iv, data, None)
b = base64.b64encode(ct).decode()
# split the data into two files to stay well under GitHub's 25 MB web-upload limit and keep each request small
half = len(b) // 2
open(f'{OUT}/data1.js', 'w').write('window.__ENC=(window.__ENC||"")+' + json.dumps(b[:half]) + ';\n')
open(f'{OUT}/data2.js', 'w').write('window.__ENC=(window.__ENC||"")+' + json.dumps(b[half:]) + ';\n')
if os.path.exists(f'{OUT}/data.js'): os.remove(f'{OUT}/data.js')
html = head + '</head><body>\n' + body + f'\n<script id="data" type="application/json"></script>\n<script id="enc" type="application/octet-stream" data-salt="{base64.b64encode(salt).decode()}" data-iv="{base64.b64encode(iv).decode()}" data-iter="200000"></script>\n<script src="data1.js"></script><script src="data2.js"></script>\n<script>\n' + js + '\n</script></body></html>\n'
open(f'{OUT}/index.html', 'w', encoding='utf-8').write(html)
print('ok', len(data), len(b), len(html))
