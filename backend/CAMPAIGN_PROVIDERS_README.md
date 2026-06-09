# Campaign Provider System

> How to add, swap, or configure outreach providers in MortgageSesame.

All campaign sends go through a **provider-neutral adapter layer**. The engine never talks to Lob, SendGrid, or SignalWire directly — it calls interface methods on `DirectMailProvider`, `EmailProvider`, etc. Swapping providers is a one-line env change.

---

## Architecture

```
CampaignEngine
    │
    ├── get_provider("email")  ──▶  registry.py  ──▶  CAMPAIGN_EMAIL_PROVIDER=resend
    │                                                      │
    │                                              ResendEmailProvider(api_key=...)
    │                                                      │
    │                                              send_email(payload) ──▶ Resend API
    │
    └── get_provider("direct_mail")  ──▶  LobDirectMailProvider  ──▶  Lob API
```

**Files:**
- `app/services/providers/base.py` — abstract interfaces + result types
- `app/services/providers/mock.py` — mock providers (dev/test) + real provider stubs
- `app/services/providers/registry.py` — env-driven factory

---

## Current Provider Status

| Channel | Mock | Real (stub) | Ready to use |
|---------|------|-------------|--------------|
| Direct mail | ✅ mock | Lob, PostGrid | Implement `create_mail_piece` |
| Email | ✅ mock | SendGrid, Resend | Implement `send_email` |
| SMS | ✅ mock | SignalWire (bridges existing), Twilio | SignalWire bridges existing service |
| Voice | ✅ mock | — | Provision via SignalWire manually |
| Address verify | ✅ mock | — | Implement via Lob or SmartyStreets |
| Property data | ✅ mock | ATTOM | Implement `search_properties` |

---

## Switching Providers

### Email → Resend

```bash
# .env
CAMPAIGN_EMAIL_PROVIDER=resend
RESEND_API_KEY=re_xxxxxxxxxxxx
CAMPAIGN_FROM_EMAIL=kevin@mortgagesesame.com
CAMPAIGN_FROM_NAME=Kevin at MortgageSesame
```

Install the SDK:
```bash
pip install resend
```

Implement `send_email` in `ResendEmailProvider` (`mock.py`):
```python
async def send_email(self, payload: dict) -> ProviderResult:
    import resend
    resend.api_key = self.api_key
    resp = resend.Emails.send({
        "from": f"{self.from_name} <{self.from_email}>",
        "to": [payload["to_email"]],
        "subject": payload["subject"],
        "html": payload["html_body"],
        "text": payload.get("text_body"),
        "tags": [{"name": k, "value": v} for k, v in (payload.get("tags") or {}).items()],
    })
    return ProviderResult(
        success=True,
        provider_id=resp["id"],
        status="sent",
        raw_response=resp,
    )
```

### Email → SendGrid

```bash
CAMPAIGN_EMAIL_PROVIDER=sendgrid
SENDGRID_API_KEY=SG.xxxxx
CAMPAIGN_FROM_EMAIL=kevin@mortgagesesame.com
```

Install:
```bash
pip install sendgrid
```

Implement `send_email` in `SendGridEmailProvider`:
```python
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

async def send_email(self, payload: dict) -> ProviderResult:
    sg = SendGridAPIClient(self.api_key)
    message = Mail(
        from_email=(self.from_email, self.from_name),
        to_emails=payload["to_email"],
        subject=payload["subject"],
        html_content=payload["html_body"],
        plain_text_content=payload.get("text_body"),
    )
    resp = sg.send(message)
    return ProviderResult(
        success=resp.status_code in (200, 202),
        provider_id=resp.headers.get("X-Message-Id"),
        status="sent",
    )
```

---

### Direct Mail → Lob

```bash
CAMPAIGN_DIRECT_MAIL_PROVIDER=lob
LOB_API_KEY=live_xxxxxxxxxxxxxxxx
```

Install:
```bash
pip install lob-python
```

Implement `create_mail_piece` in `LobDirectMailProvider`:
```python
import lob

async def create_mail_piece(self, payload: dict) -> ProviderResult:
    lob.api_key = self.api_key
    piece = lob.Postcard.create(
        to={
            "name": payload["to_name"],
            "address_line1": payload["to_address"]["line1"],
            "address_city": payload["to_address"]["city"],
            "address_state": payload["to_address"]["state"],
            "address_zip": payload["to_address"]["zip"],
        },
        front=payload["html_front"],
        back="<html>...</html>",   # required by Lob
        description=payload.get("description", "MortgageSesame campaign"),
        metadata=payload.get("metadata", {}),
    )
    return ProviderResult(
        success=True,
        provider_id=piece.id,
        status=piece.status,
        raw_response=dict(piece),
    )
```

**Lob sandbox:** Use test API keys (`test_xxx`) — pieces are never printed.
**Webhook:** Set in Lob dashboard → `https://yourdomain.com/api/v1/outreach/webhooks/lob`

---

### Direct Mail → PostGrid

```bash
CAMPAIGN_DIRECT_MAIL_PROVIDER=postgrid
POSTGRID_API_KEY=test_sk_xxxxx
```

Implement using `httpx`:
```python
import httpx

async def create_mail_piece(self, payload: dict) -> ProviderResult:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.postgrid.com/print-mail/v1/postcards",
            headers={"x-api-key": self.api_key},
            json={
                "to": {"firstName": payload["to_name"], "addressLine1": payload["to_address"]["line1"], ...},
                "from": {...},
                "front": payload["html_front"],
                "back": "...",
            }
        )
    data = resp.json()
    return ProviderResult(success=resp.status_code == 200, provider_id=data.get("id"), status=data.get("status", "created"))
```

---

### SMS → SignalWire (bridges existing service)

The `SignalWireSmsProvider` already bridges to `app/services/integrations/signalwire.py`.

```bash
CAMPAIGN_SMS_PROVIDER=signalwire
# (uses existing SIGNALWIRE_* env vars)
```

⚠️ **TCPA requirement:** SMS campaigns require express written consent. The outreach engine's send endpoint checks `is_suppressed` before sending. STOP/opt-out responses update the suppression list automatically via the webhook endpoint.

Webhook endpoint: `https://yourdomain.com/api/v1/outreach/webhooks/signalwire`

---

### Property Data → ATTOM

```bash
CAMPAIGN_PROPERTY_PROVIDER=attom
ATTOM_API_KEY=xxxxxxxxxxxxxxxx
```

Implement `search_properties` using ATTOM's address endpoint:
```python
import httpx

async def search_properties(self, payload: dict) -> list[PropertyResult]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.developer.attomdata.com/propertyapi/v1.0.0/property/basicprofile",
            headers={"apikey": self.api_key, "Accept": "application/json"},
            params={"address1": payload["address"], "address2": payload.get("city_state_zip", "")},
        )
    if resp.status_code != 200:
        return [PropertyResult(found=False, error=f"ATTOM {resp.status_code}")]
    data = resp.json()
    # Map ATTOM response fields to PropertyResult
    ...
```

ATTOM docs: https://api.developer.attomdata.com/docs

---

## Adding a New Provider

1. **Create the class** in `mock.py` (or a new file for complex providers):
   ```python
   class MyNewEmailProvider(EmailProvider):
       name = "mynew"
       def __init__(self, api_key: str, from_email: str, from_name: str):
           ...
       async def send_email(self, payload: dict) -> ProviderResult:
           ...  # implement
       async def add_suppression(self, email: str, reason: str) -> bool: ...
       async def get_suppressions(self) -> list[str]: ...
       async def handle_webhook(self, payload: dict) -> dict: ...
   ```

2. **Register it** in `registry.py`:
   ```python
   if name == "mynew":
       return MyNewEmailProvider(
           api_key=os.getenv("MYNEW_API_KEY", ""),
           from_email=os.getenv("CAMPAIGN_FROM_EMAIL", ""),
           from_name=os.getenv("CAMPAIGN_FROM_NAME", "MortgageSesame"),
       )
   ```

3. **Add env vars** to `.env.example`.

4. **Set the env var** and restart:
   ```bash
   CAMPAIGN_EMAIL_PROVIDER=mynew
   MYNEW_API_KEY=xxx
   ```

No other code changes required. The engine will use your new provider automatically.

---

## Webhook Endpoints

All provider webhooks route to:
```
POST /api/v1/outreach/webhooks/{provider_name}
```

Examples:
- `POST /api/v1/outreach/webhooks/sendgrid`
- `POST /api/v1/outreach/webhooks/resend`
- `POST /api/v1/outreach/webhooks/lob`
- `POST /api/v1/outreach/webhooks/signalwire`

The handler normalizes events and:
- Updates `CampaignOutreach` delivery status timestamps
- Creates `SuppressionEntry` records for unsubscribes/bounces/spam reports
- Marks prospects as suppressed

---

## QR Tracking

Every direct mail piece and email gets a unique QR code:

```
https://yourdomain.com/r/AB12CD34EF
```

Scanning → `GET /r/{code}` → records event + creates CallTask → redirects to booking URL.

The call task appears immediately in the warm-lead call queue at:
```
GET /api/v1/outreach/call-tasks
```

Priority 1 = highest (QR scan from a mailer = hottest signal possible).

---

## Compliance Notes

- **Direct mail:** All templates include ADVERTISEMENT disclosure, NOT A CHECK disclaimer, NMLS#, Equal Housing Lender.
- **Email:** All templates include unsubscribe link placeholder `{{unsubscribe_url}}`. Wire this to your ESP's unsubscribe URL before sending.
- **SMS:** Must have express written consent before sending. Use consent gate in contact intake flow. STOP handling is provider-managed.
- **DNC check:** `is_do_not_contact` blocks sends at the engine level, not the provider level.
- **Suppression:** `SuppressionEntry` table checked before every email/SMS send.
