"""Zozo Lanka Sinhala WhatsApp starter. Python 3.9+, standard library only."""
import hashlib
import html
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
import sales_ai

ROOT = Path(__file__).resolve().parent
PRODUCT = json.loads((ROOT / 'product.json').read_text(encoding='utf-8'))
DB = os.environ.get('BOT_DB', str(ROOT / 'data' / 'messages.sqlite3'))

PRIVACY_NOTICE = "# Zozo Lanka WhatsApp Assistant — Privacy Notice\n\nLast updated: 4 November 2026.\n\nThis notice describes the automated WhatsApp assistant operated for Zozo Lanka. It covers this assistant, rather than all Zozo Lanka websites, sales records or other services.\n\n## Information processed and why\n\nWhen you message the assistant, it processes your WhatsApp phone number, message content, message identifier and message timestamp to provide product information and respond to enquiries. WhatsApp may include additional account or profile metadata in the delivery payload. The assistant does not intentionally store that additional metadata in its message queue.\n\nThe assistant uses OpenAI to generate replies. Message text and up to eight recent conversation messages may be sent to OpenAI. The WhatsApp routing number is not sent as an API user identifier; information you include in message text may still contain personal information. Do not include unnecessary private data. API response storage is disabled in requests; this does not mean all provider retention is disabled. Its replies do not confirm payment or acceptance of an order. Do not send card details, passwords or verification codes to the assistant.\n\n## Service providers\n\nMessages are transmitted through Meta's WhatsApp Business Platform. The assistant is hosted on Render, configured in its Singapore region. OpenAI processes conversation text to generate assistant replies. These providers process information according to their own services and privacy terms, and processing may involve countries outside Sri Lanka.\n\n## Temporary message storage\n\nThe assistant temporarily stores the sender number, message text, message identifier, timestamp and processing status in its server queue. The current software clears the sender number and message text after processing. Pending or interrupted messages can remain until processed or handled by an operator. Message identifiers and processing status are normally removed after seven days when the queue worker performs cleanup.\n\nIn addition, up to eight recent conversation messages are kept locally for context for up to 24 hours, with expiry cleanup while the worker runs. They are indexed by a keyed hash of the sender number. Send \"forget\" or \"delete my chat\" to clear this local conversation history. Usage counters contain the keyed hash and a daily count, and are removed after two days during subsequent requests. This describes the assistant's working queue and local history. It does not mean that the same information has been deleted from WhatsApp, provider logs or backups, your own device, or any records kept separately by Zozo Lanka staff. Separate sales, warranty and support records are outside this notice's description of queue retention.\n\n## Access and safeguards\n\nThe assistant uses HTTPS for its public webhook, verifies Meta's webhook signature, and keeps API credentials outside the public source repository. Authorized administrators and the hosting and messaging providers may access information as needed to operate the service. No system can guarantee absolute security.\n\n## Questions, human support and deletion requests\n\nYou can stop using the assistant at any time. To request human assistance, ask about your information, or request deletion of information held by Zozo Lanka through this assistant, contact:\n\n- Main WhatsApp / phone: **+94 77 297 7471**\n- Additional phone: **+94 74 264 9856**\n\nIdentify the number you used to contact the assistant and describe your request. Zozo Lanka may need to verify that the request comes from you. Requests affecting Meta or other providers' own records must also be made through those providers' applicable channels.\n\n## Changes\n\nThis notice should be updated when the assistant's features, providers or data handling change. The published notice should show its most recent update date.\n"

def reply(text, support=None):
    # Used only if AI is not configured. Never retain the superseded single-phone offer.
    return sales_ai.fallback(text) + ('\n' + support if support else '')

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
                if int(time.time()) % 60 == 0:
                    sales_ai.cleanup(DB)
                time.sleep(0.5)
                continue
            state = 'expired'
            if 0 <= time.time() - row[3] < 23 * 3600:
                try:
                    response = sales_ai.answer(row[2], row[1], DB) if os.environ.get('OPENAI_API_KEY') else reply(row[2])
                    send(row[1], response)
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

    def respond(self, code, body, content_type="text/plain; charset=utf-8"):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path == '/health':
            return self.respond(200, 'ok')
        if url.path in ('/privacy', '/data-deletion'):
            page = ('<!doctype html><html lang="en"><meta charset="utf-8">'
                    '<meta name="viewport" content="width=device-width, initial-scale=1">'
                    '<title>Zozo Lanka WhatsApp Privacy Notice</title>'
                    '<main style="max-width:760px;margin:40px auto;padding:20px;font:17px/1.7 system-ui">'
                    '<pre style="white-space:pre-wrap;font:inherit">' + html.escape(PRIVACY_NOTICE) + '</pre></main></html>')
            return self.respond(200, page, 'text/html; charset=utf-8')
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
