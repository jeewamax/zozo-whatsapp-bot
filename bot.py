"""Zozo Lanka Sinhala WhatsApp starter. Python 3.9+, standard library only."""
import hashlib
import hmac
import json
import os
import sqlite3
import sys
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PRODUCT = json.loads((ROOT / 'product.json').read_text(encoding='utf-8'))
DB = os.environ.get('BOT_DB', str(ROOT / 'data' / 'messages.sqlite3'))

def reply(text, support=None):
    support = support or os.environ.get('SUPPORT_CONTACT', '[Zozo Lanka සහාය අංකය සැකසිය යුතුය]')
    text = text.strip().lower()
    p = PRODUCT
    contact = '\nසහාය සඳහා: ' + support
    if text == '4' or any(w in text for w in ('human', 'agent', 'නියෝජිත', 'කතා කරන්න', 'complaint', 'පැමිණිලි')):
        return 'අපගේ කණ්ඩායමේ සහාය ලබාගැනීමට පහත සම්බන්ධතා මාර්ගය භාවිතා කරන්න. සේවා වේලාවෙන් පිටත ලැබෙන ඉල්ලීම් සඳහා පිළිතුරු ලැබීමට කාලයක් ගතවිය හැකියි.' + contact
    if text == '3' or any(w in text for w in ('warranty', 'වගකී', 'battery', 'බැටරි', 'software', 'මෘදුකාංග')):
        return ('Zozo Lanka ලබාදුන් වගකීම් තොරතුරු:\n• දුරකථනයට වසර 2යි\n• බැටරියට වසර 4යි\n• ජීවිත කාලීන මෘදුකාංග වගකීම\n\nආවරණය, කොන්දේසි සහ වගකීම සපයන ආයතනය පිළිබඳ විස්තර ඇණවුමට පෙර අපගේ කණ්ඩායමෙන් තහවුරු කරගන්න.' + contact)
    if text == '1' or any(w in text for w in ('order', 'delivery', 'ගෙන්වා', 'ඇණවු', 'බෙදා', 'payment', 'ගෙව', 'deposit', 'අත්තිකාර')):
        return (f'{p["name"]} සඳහා පෙර ඇණවුම් විමසීම් පිළිගනිමු.\nමිල: රු. {p["price_lkr"]:,}\nශ්‍රී ලංකාවට බෙදාහැරීම: Zozo Lanka සඳහන් කරන කාලය දින 15ක් ඇතුළතයි.\n\nදින ගණනය ආරම්භ වන දිනය, බෙදාහැරීමේ ගාස්තු සහ අත්තිකාරම අපගේ කණ්ඩායමෙන් තහවුරු කරගන්න. මෙම පණිවිඩයෙන් ඇණවුමක් හෝ ගෙවීමක් තහවුරු නොවේ.' + contact)
    if text == '2' or any(w in text for w in ('vivo', 'x300', 'price', 'මිල', '280', 'stock', 'තොග', 'ram', 'storage')):
        return (f'📱 {p["name"]}\nඅලුත්ම දුරකථනයක්\nRAM: {p["ram"]} | Storage: {p["storage"]}\nමිල: රු. {p["price_lkr"]:,}\nපෙර ඇණවුම් සඳහා පමණි.\n\n1 — පෙර ඇණවුම් / බෙදාහැරීම\n3 — වගකීම්\n4 — කණ්ඩායමේ සහාය')
    return ('ආයුබෝවන්! 👋 Zozo Lanka තාක්ෂණ සමාගම වෙත සාදරයෙන් පිළිගනිමු. මම ස්වයංක්‍රීය සහායකයායි.\n\nකරුණාකර අංකයක් හෝ ඔබගේ ප්‍රශ්නය එවන්න:\n1 — පෙර ඇණවුම් සහ බෙදාහැරීම\n2 — vivo X300 Ultra මිල සහ විස්තර\n3 — වගකීම්\n4 — අපගේ කණ්ඩායමේ සහාය\n\nස්වයංක්‍රීය පිළිතුරු පැය 24ම ලබාදීමට සකස් කර ඇත.')

def signature_valid(body, signature, secret):
    expected = 'sha256=' + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or '')

def connect():
    db = sqlite3.connect(DB, timeout=15)
    return db

def initialize():
    Path(DB).parent.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS inbox (id TEXT PRIMARY KEY, recipient TEXT, body TEXT, stamp INTEGER, state TEXT DEFAULT "pending")')
        # An interrupted send may already have reached Meta. Never blindly resend.
        db.execute('UPDATE inbox SET state="review" WHERE state="sending"')

def enqueue(payload):
    if payload.get('object') != 'whatsapp_business_account':
        return
    with connect() as db:
        for entry in payload.get('entry', []):
            for change in entry.get('changes', []):
                value = change.get('value', {})
                if value.get('metadata', {}).get('phone_number_id') != os.environ['WHATSAPP_PHONE_NUMBER_ID']:
                    continue
                for message in value.get('messages', []):
                    if message.get('type') == 'text':
                        content = message.get('text', {}).get('body', '')
                    else:
                        content = 'unsupported media'
                    if message.get('id') and message.get('from'):
                        db.execute('INSERT OR IGNORE INTO inbox (id, recipient, body, stamp) VALUES (?, ?, ?, ?)',
                                   (message['id'], message['from'], content[:8000], int(message.get('timestamp', 0))))

def send(recipient, body):
    version = os.environ['GRAPH_API_VERSION']
    phone = os.environ['WHATSAPP_PHONE_NUMBER_ID']
    data = json.dumps({'messaging_product': 'whatsapp', 'to': recipient, 'type': 'text', 'text': {'body': body}}).encode()
    req = urllib.request.Request(f'https://graph.facebook.com/{version}/{phone}/messages', data=data,
                                 headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + os.environ['WHATSAPP_ACCESS_TOKEN']})
    with urllib.request.urlopen(req, timeout=20) as response:
        result = json.load(response)
        if not result.get('messages'):
            raise RuntimeError('No message acknowledgment')

def worker():
    while True:
        try:
            with connect() as db:
                row = db.execute('SELECT id, recipient, body, stamp FROM inbox WHERE state="pending" ORDER BY rowid LIMIT 1').fetchone()
                if row:
                    db.execute('UPDATE inbox SET state="sending" WHERE id=?', (row[0],))
            if not row:
                time.sleep(0.5)
                continue
            state = 'expired'
            if 0 <= time.time() - row[3] < 23 * 3600:
                try:
                    send(row[1], reply(row[2]))
                    state = 'sent'
                except Exception:
                    # Do not log tokens, phone numbers, or private message content.
                    state = 'review'
                    print('Message send needs operator review; check queue status.', flush=True)
            with connect() as db:
                db.execute('UPDATE inbox SET state=?, body="", recipient="" WHERE id=?', (state, row[0]))
                db.execute('DELETE FROM inbox WHERE stamp < ?', (int(time.time()) - 7 * 86400,))
        except Exception:
            print('Queue error: check storage availability.', flush=True)
            time.sleep(2)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Verification tokens and customer details must not enter access logs.

    def respond(self, code, body):
        self.send_response(code)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path == '/health':
            return self.respond(200, 'ok')
        q = urllib.parse.parse_qs(url.query)
        if url.path == '/webhook' and q.get('hub.mode') == ['subscribe'] and hmac.compare_digest(q.get('hub.verify_token', [''])[0], os.environ['WHATSAPP_VERIFY_TOKEN']):
            return self.respond(200, q.get('hub.challenge', [''])[0])
        self.respond(403, 'Forbidden')

    def do_POST(self):
        if urllib.parse.urlparse(self.path).path != '/webhook':
            return self.respond(404, 'Not found')
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 1024 * 1024:
                return self.respond(413, 'Invalid body size')
            raw = self.rfile.read(size)
            if not signature_valid(raw, self.headers.get('X-Hub-Signature-256'), os.environ['META_APP_SECRET']):
                return self.respond(401, 'Invalid signature')
            enqueue(json.loads(raw))
        except (ValueError, TypeError, AttributeError):
            return self.respond(400, 'Invalid payload')
        except Exception:
            return self.respond(503, 'Storage unavailable')
        self.respond(200, 'EVENT_RECEIVED')

if __name__ == '__main__':
    if '--demo' in sys.argv:
        print('Zozo Lanka offline demo. Type exit to close. No WhatsApp connection.\n')
        print(reply('hello'))
        while True:
            try:
                text = input('\nCustomer: ')
            except (EOFError, KeyboardInterrupt):
                break
            if text.lower() == 'exit':
                break
            print('\nZozo Lanka: ' + reply(text))
    else:
        keys = ('WHATSAPP_VERIFY_TOKEN', 'META_APP_SECRET', 'WHATSAPP_PHONE_NUMBER_ID', 'WHATSAPP_ACCESS_TOKEN', 'GRAPH_API_VERSION', 'SUPPORT_CONTACT')
        missing = [key for key in keys if not os.environ.get(key)]
        if missing:
            sys.exit('Configure environment variables: ' + ', '.join(missing))
        initialize()
        threading.Thread(target=worker, daemon=True).start()
        print('Zozo Lanka webhook server started.', flush=True)
        ThreadingHTTPServer(('0.0.0.0', int(os.environ.get('PORT', '8080'))), Handler).serve_forever()
