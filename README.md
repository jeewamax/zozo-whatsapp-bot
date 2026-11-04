# Zozo Lanka — සිංහල WhatsApp chatbot මුල් අනුවාදය

මෙය ක්‍රියාත්මක කළ හැකි මුල් කේත අනුවාදයකි. තවම WhatsApp වෙත සම්බන්ධ කර නැත; පැය 24 සේවාව ආරම්භ වී නැත.

## දැනට කළ හැකි දේ

- සිංහල පිළිගැනීම, අංක 1–4 මෙනුව සහ තෝරාගත් සිංහල/English වචන අනුව පිළිතුරු.
- vivo X300 Ultra, 12GB/256GB, රු. 280,000 සහ පෙර ඇණවුම් විස්තර.
- ඔබ ලබාදුන් වසර 2 දුරකථන / වසර 4 බැටරි / ජීවිත කාලීන මෘදුකාංග වගකීම් පිළිබඳ තොරතුරු; කොන්දේසි කණ්ඩායමෙන් තහවුරු කරගැනීමට යොමු කරයි.
- ගෙවීම් හෝ ඇණවුම් තහවුරු නොකරයි. අත්තිකාරම්, ගාස්තු සහ දින 15 ආරම්භ වන දිනය අනුමාන නොකරයි.
- සැබෑ සහාය සම්බන්ධතා මාර්ගයක් පෙන්වයි. සේවකයකුට දැනුම්දීමක් හෝ agent inbox එකක් මෙම අනුවාදයට ඇතුළත් නැත.

මෙය keyword/menu bot එකකි. නිදහස් සංවාද කරන AI, voice-note හඳුනාගැනීම, online stock, payment processing හෝ order management තවම නැත.

## දේශීය පරීක්ෂාව (WhatsApp හෝ රහස් යතුරු අවශ්‍ය නැත)

Python 3.9 හෝ ඉහළ අනුවාදයක් අවශ්‍යයි. අමතර packages අවශ්‍ය නැත.

```sh
python3 bot.py --demo
python3 -m unittest -v
```

## WhatsApp වෙත සම්බන්ධ කිරීම

1. Meta Business / Developer ගිණුමෙන් නිල WhatsApp Business Platform සකස් කරන්න. පළමුව test number එකක් භාවිතා කරන්න. දැනට තිබෙන WhatsApp Business අංකය ඉවත් නොකරන්න; පවතින අංකය සම්බන්ධ කිරීමේ හෝ coexistence හැකියාව Meta/නිල සැපයුම්කරු සමඟ පරීක්ෂා කරන්න.
2. `.env.example` හි ඇති අගයන් hosting provider එකේ environment/secret settings වෙත ඇතුළත් කරන්න. මෙම වැඩසටහන `.env` ගොනු ස්වයංක්‍රීයව කියවන්නේ නැත. සැබෑ customer support සම්බන්ධතාවයක් අවශ්‍යයි. API version එක Meta dashboard එකෙන් ලබාගන්න. Access token සහ app secret chat එකට එවන්න එපා.
3. Always-on Python hosting, public HTTPS URL සහ persistent disk සකස් කරන්න. එක් app instance එකක් පමණක් ධාවනය කරන්න. Start command: `python3 bot.py`. Health path: `/health`.
4. Meta webhook callback එක `https://YOUR-HOST/webhook` ලෙස සකසා verification token එක ගළපන්න. WhatsApp messages webhook field එකට subscribe කරන්න; අවශ්‍ය WABA/app subscription එකද Meta setup අනුව සම්පූර්ණ කරන්න.
5. Test customer number එකෙන් welcome, 1/2/3/4, price සහ warranty ප්‍රශ්න පරීක්ෂා කරන්න. Hosting restart කිරීමෙන් පසුවද පරීක්ෂා කරන්න.
6. සැබෑ භාවිතයට පෙර වගකීම්, මිල, නිශ්චිත model/variant, බෙදාහැරීමේ කොන්දේසි සහ customer support සම්බන්ධතාව Zozo Lanka විසින් තහවුරු කළ යුතුය.

## මෙහෙයුම් සීමා

Webhook signature පරීක්ෂා කරයි; duplicate message IDs නොසලකා හරියි; SQLite queue එකක් භාවිතා කරයි. Customer window ඉක්මවීම වැළැක්වීමට පැය 23කට වඩා පැරණි messages වෙත පිළිතුරු නොයවයි. Outbound marketing හෝ template follow-ups ක්‍රියාත්මක කර නැත.

Send එකක් අසාර්ථක හෝ අවිනිශ්චිත වුවහොත් queue state `review` ලෙස තබයි; duplicate replies වළක්වා ගැනීමට ස්වයංක්‍රීයව නැවත යවන්නේ නැත. Operator කෙනකු පරීක්ෂා කළ යුතුය. Monitoring/alerts සහ team inbox එක production භාවිතයට පෙර සම්බන්ධ කිරීම සුදුසුය. `/health` process එක පවතින බව පමණක් පෙන්වයි; token validity හෝ Meta availability තහවුරු නොකරයි.

Queue එකේ pending customer message/number තාවකාලිකව තබයි. සැකසූ පසු message/number ඉවත් කරයි; පැරණි message IDs queue වැඩ කරන විට දින 7කට පසු ඉවත් කරයි. Disk සහ backups වෙත ප්‍රවේශය සීමා කරන්න. Hosting, Meta සහ නඩත්තු ගාස්තු මෙයට ඇතුළත් නැත. පැය 24 සේවාවට hosting uptime, credentials සහ Meta availability අවශ්‍යයි.

## මූලාශ්‍ර

- [Meta webhook verification reference](https://whatsapp.github.io/WhatsApp-Nodejs-SDK/api-reference/webhooks/start/)
- [WhatsApp Business Platform](https://whatsappbusiness.com/products/business-platform/)
- [WhatsApp Business Messaging Policy](https://whatsappbusiness.com/policy/)

Meta onboarding සහ live API compatibility තවම සජීවී ගිණුමක් සමඟ පරීක්ෂා කර නැත.


## ZOZO AI upgrade — 4 November 2026

Responses API using gpt-4.1-mini, server-only OPENAI_API_KEY. Model may be overridden by OPENAI_MODEL. The key configured for this deployment expires after 30 days and must be replaced before expiry.

Catalog snapshot: user-approved Drive workbook 1zxzI2yfj631I7B3dOquJm5MmhdRy2d5z, dated 2026-11-04: 2,716 phone rows, 328 tablet rows, 171 laptop rows, consolidated into 2,679 exact variants. Each colour/configuration has separate prices; 324 variants have conflicting source amounts, shown with team confirmation required. Only LKR retail prices are included. This is a snapshot; editing Drive does not automatically update deployment. No stock or compatibility tests are implied by catalog entries. The old LKR280,000 offer is superseded.

History: eight messages per customer, keyed HMAC identifier, maximum 24 hours; forget/delete my chat clears history. API requests use store=false. Usage safeguards: 30 assistant requests per customer per UTC day and 200 total per UTC day, at most two model calls per request. These request limits are not a dollar spending guarantee. Provider errors/expired keys return human contacts. No human inbox/notification integration.

Privacy page updated for OpenAI processing and local history. All current technical specifications/compatibility must be verified separately. Full external warranty page contents not fetched; exact exclusions are referred to official page/team.
