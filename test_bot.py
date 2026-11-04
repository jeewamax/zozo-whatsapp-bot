import hashlib
import hmac
import os
import tempfile
import time
import unittest
from unittest.mock import patch
import bot

class BotTests(unittest.TestCase):
    def test_signature_rejects_tampering(self):
        body = b'{"object":"whatsapp_business_account"}'
        signature = 'sha256=' + hmac.new(b'secret', body, hashlib.sha256).hexdigest()
        self.assertTrue(bot.signature_valid(body, signature, 'secret'))
        self.assertFalse(bot.signature_valid(body + b' ', signature, 'secret'))
        self.assertFalse(bot.signature_valid(body, '', 'secret'))

    def test_durable_dedup_and_wrong_number_filter(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(bot, 'DB', directory + '/queue.db'), patch.dict(os.environ, {'WHATSAPP_PHONE_NUMBER_ID': 'correct'}):
                bot.initialize()
                value = {'metadata': {'phone_number_id': 'correct'}, 'messages': [{'id': 'unique', 'from': 'test', 'type': 'text', 'text': {'body': '2'}, 'timestamp': str(int(time.time()))}]}
                payload = {'object': 'whatsapp_business_account', 'entry': [{'changes': [{'value': value}]}]}
                bot.enqueue(payload)
                bot.enqueue(payload)
                value['metadata']['phone_number_id'] = 'wrong'
                value['messages'][0]['id'] = 'wrong-number'
                bot.enqueue(payload)
                with bot.connect() as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM inbox').fetchone()[0], 1)
                    db.execute('UPDATE inbox SET state="sending"')
                bot.initialize()
                with bot.connect() as db:
                    self.assertEqual(db.execute('SELECT state FROM inbox').fetchone()[0], 'review')

if __name__ == '__main__':
    unittest.main()
