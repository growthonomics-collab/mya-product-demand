import json, os, base64, hashlib, sys
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
PW = sys.argv[1] if len(sys.argv) > 1 else 'MYA2026'
OUT = 'repo'
os.makedirs(OUT, exist_ok=True)
data = open('data.json', 'rb').read()
salt, iv = os.urandom(16), os.urandom(12)
key = hashlib.pbkdf2_hmac('sha256', PW.encode(), salt, 200000, 32)
ct = AESGCM(key).encrypt(iv, data, None)
b = base64.b64encode(ct).decode()
open(f'{OUT}/data.js', 'w').write('window.__ENC=' + json.dumps(b) + ';\n')
html = open('template.html', encoding='utf-8').read().replace('{{SALT}}', base64.b64encode(salt).decode()).replace('{{IV}}', base64.b64encode(iv).decode())
open(f'{OUT}/index.html', 'w', encoding='utf-8').write(html)
open(f'{OUT}/README.md', 'w').write('# MYA Collection product demand dashboard\n\nPassword-protected dashboard built by Growth-onomics.\n')
open(f'{OUT}/.nojekyll', 'w').write('')
print('ok', len(data), len(b))
