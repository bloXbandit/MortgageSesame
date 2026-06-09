"""
Mock provider implementations — all channels.

Used when CAMPAIGN_*_PROVIDER=mock (the default).
Simulates realistic provider behavior: generates fake IDs, logs actions,
returns success results. Safe to use in development and testing.
"""

import uuid
import structlog
from app.services.providers.base import (
    DirectMailProvider, EmailProvider, SmsProvider,
    VoiceProvider, AddressVerificationProvider, PropertyDataProvider,
    ProviderResult, AddressResult, PropertyResult,
)

log = structlog.get_logger()


class MockDirectMailProvider(DirectMailProvider):
    name = "mock"

    async def validate_address(self, address: dict) -> AddressResult:
        log.info("mock.direct_mail.validate_address", address=address)
        return AddressResult(
            valid=True,
            deliverable=True,
            standardized_line1=address.get("line1", "123 Main St"),
            standardized_city=address.get("city", "Rockville"),
            standardized_state=address.get("state", "MD"),
            standardized_zip=address.get("zip", "20850"),
            dpv_match="Y",
        )

    async def create_mail_piece(self, payload: dict) -> ProviderResult:
        job_id = f"mock_mail_{uuid.uuid4().hex[:12]}"
        log.info("mock.direct_mail.create_mail_piece",
                 to=payload.get("to_name"), type=payload.get("mail_type"), job_id=job_id)
        return ProviderResult(
            success=True,
            provider_id=job_id,
            status="queued",
            raw_response={"id": job_id, "status": "queued", "provider": "mock"},
        )

    async def get_mail_status(self, provider_id: str) -> ProviderResult:
        return ProviderResult(success=True, provider_id=provider_id, status="mailed")

    async def handle_webhook(self, payload: dict) -> dict:
        event_type = payload.get("event_type", "mailed")
        return {"event": event_type, "provider_id": payload.get("id"), "provider": "mock"}


class MockEmailProvider(EmailProvider):
    name = "mock"

    async def send_email(self, payload: dict) -> ProviderResult:
        msg_id = f"mock_email_{uuid.uuid4().hex[:12]}"
        log.info("mock.email.send",
                 to=payload.get("to_email"), subject=payload.get("subject"), msg_id=msg_id)
        return ProviderResult(
            success=True,
            provider_id=msg_id,
            status="sent",
            raw_response={"id": msg_id, "status": "sent", "provider": "mock"},
        )

    async def add_suppression(self, email: str, reason: str) -> bool:
        log.info("mock.email.add_suppression", email=email, reason=reason)
        return True

    async def get_suppressions(self) -> list[str]:
        return []

    async def handle_webhook(self, payload: dict) -> dict:
        return {"event": payload.get("event", "delivered"), "provider": "mock"}


class MockSmsProvider(SmsProvider):
    name = "mock"

    async def send_sms(self, payload: dict) -> ProviderResult:
        msg_id = f"mock_sms_{uuid.uuid4().hex[:10]}"
        log.info("mock.sms.send",
                 to=payload.get("to_phone"), body_preview=payload.get("body", "")[:60], msg_id=msg_id)
        return ProviderResult(
            success=True,
            provider_id=msg_id,
            status="sent",
            raw_response={"id": msg_id, "status": "sent", "provider": "mock"},
        )

    async def handle_inbound(self, payload: dict) -> dict:
        return {"from": payload.get("From"), "body": payload.get("Body"), "provider": "mock"}

    async def handle_opt_out(self, phone: str) -> bool:
        log.info("mock.sms.opt_out", phone=phone)
        return True

    async def handle_webhook(self, payload: dict) -> dict:
        return {"event": payload.get("SmsStatus", "delivered"), "provider": "mock"}


class MockVoiceProvider(VoiceProvider):
    name = "mock"

    async def provision_tracking_number(self, label: str) -> ProviderResult:
        number = "+14435550100"
        log.info("mock.voice.provision_tracking_number", label=label, number=number)
        return ProviderResult(success=True, provider_id=number, status="active")

    async def handle_call_webhook(self, payload: dict) -> dict:
        return {"event": "call_completed", "from": payload.get("From"), "provider": "mock"}


class MockAddressVerificationProvider(AddressVerificationProvider):
    name = "mock"

    async def verify_address(self, address: dict) -> AddressResult:
        return AddressResult(valid=True, deliverable=True, dpv_match="Y",
                             standardized_line1=address.get("line1"),
                             standardized_city=address.get("city"),
                             standardized_state=address.get("state"),
                             standardized_zip=address.get("zip"))

    async def standardize_address(self, address: dict) -> AddressResult:
        return await self.verify_address(address)


class MockPropertyDataProvider(PropertyDataProvider):
    name = "mock"

    async def search_properties(self, payload: dict) -> list[PropertyResult]:
        return [PropertyResult(
            found=True,
            address=payload.get("address", "123 Demo St, Rockville MD 20850"),
            estimated_value=425_000,
            equity_pct=38.0,
            equity_dollars=161_500,
            loan_amount=263_500,
            origination_date="2022-08-15",
            loan_type="Conventional",
            rate_estimate=6.875,
            owner_name="Sample Owner",
            is_owner_occupied=True,
        )]

    async def enrich_property(self, address: str) -> PropertyResult:
        results = await self.search_properties({"address": address})
        return results[0] if results else PropertyResult(found=False, error="Not found")

    async def estimate_equity(self, address: str, loan_balance: float) -> PropertyResult:
        result = await self.enrich_property(address)
        if result.found and result.estimated_value:
            equity = result.estimated_value - loan_balance
            result.equity_dollars = equity
            result.equity_pct = round((equity / result.estimated_value) * 100, 1)
            result.loan_amount = loan_balance
        return result


# ── Provider stubs (real providers — keys required) ────────────────────────────

class LobDirectMailProvider(DirectMailProvider):
    """
    Lob.com — API-based direct mail, postcards, and letters.
    Auth: API key (Basic auth: api_key as username, empty password).
    Sandbox: Yes — test API keys print nothing, return mock responses.
    Docs: https://docs.lob.com
    """
    name = "lob"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def validate_address(self, address: dict) -> AddressResult:
        raise NotImplementedError("Lob address verification — install lob-python SDK and implement")

    async def create_mail_piece(self, payload: dict) -> ProviderResult:
        raise NotImplementedError("Lob mail piece creation — see CAMPAIGN_PROVIDERS_README.md")

    async def get_mail_status(self, provider_id: str) -> ProviderResult:
        raise NotImplementedError

    async def handle_webhook(self, payload: dict) -> dict:
        # Lob webhook event_type: "letter.created" / "letter.mailed" / "letter.in_transit"
        return {
            "event": payload.get("event_type", "unknown").split(".")[-1],
            "provider_id": payload.get("body", {}).get("id"),
            "provider": "lob",
        }


class PostGridDirectMailProvider(DirectMailProvider):
    """
    PostGrid — API-based mail, Canada + US.
    Auth: API key in header (x-api-key).
    Sandbox: Yes — test mode with test API keys.
    Docs: https://docs.postgrid.com
    """
    name = "postgrid"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def validate_address(self, address: dict) -> AddressResult:
        raise NotImplementedError("PostGrid address verification — see CAMPAIGN_PROVIDERS_README.md")

    async def create_mail_piece(self, payload: dict) -> ProviderResult:
        raise NotImplementedError

    async def get_mail_status(self, provider_id: str) -> ProviderResult:
        raise NotImplementedError

    async def handle_webhook(self, payload: dict) -> dict:
        return {"event": payload.get("type", "unknown"), "provider": "postgrid"}


class SendGridEmailProvider(EmailProvider):
    """
    SendGrid — transactional/bulk email.
    Auth: API key (Bearer token).
    Sandbox: Yes — sandbox mode available.
    Unsubscribe: Built-in groups or custom unsubscribe links.
    Webhooks: Event Webhook for opens, clicks, bounces, unsubscribes, spam reports.
    Docs: https://docs.sendgrid.com
    """
    name = "sendgrid"

    def __init__(self, api_key: str, from_email: str, from_name: str):
        self.api_key = api_key
        self.from_email = from_email
        self.from_name = from_name

    async def send_email(self, payload: dict) -> ProviderResult:
        raise NotImplementedError("SendGrid — install sendgrid-python and implement")

    async def add_suppression(self, email: str, reason: str) -> bool:
        raise NotImplementedError

    async def get_suppressions(self) -> list[str]:
        raise NotImplementedError

    async def handle_webhook(self, payload: dict) -> dict:
        # SendGrid sends a list of events
        events = payload if isinstance(payload, list) else [payload]
        results = []
        for ev in events:
            results.append({
                "event": ev.get("event"),
                "email": ev.get("email"),
                "provider_id": ev.get("sg_message_id"),
                "provider": "sendgrid",
            })
        return {"events": results}


class ResendEmailProvider(EmailProvider):
    """
    Resend — developer-focused transactional email. Simple API, good deliverability.
    Auth: API key (Authorization: Bearer).
    Sandbox: No formal sandbox, but test mode doesn't deliver.
    Webhooks: Yes — email.sent, email.delivered, email.bounced, email.opened, email.clicked.
    Docs: https://resend.com/docs
    """
    name = "resend"

    def __init__(self, api_key: str, from_email: str, from_name: str):
        self.api_key = api_key
        self.from_email = from_email
        self.from_name = from_name

    async def send_email(self, payload: dict) -> ProviderResult:
        """Send via Resend API using httpx. No extra SDK required."""
        import httpx

        if not self.api_key:
            return ProviderResult(success=False, error="RESEND_API_KEY not set")

        from_field = f"{self.from_name} <{self.from_email}>" if self.from_name else self.from_email
        to_email = payload.get("to_email")
        if not to_email:
            return ProviderResult(success=False, error="to_email is required")

        body: dict = {
            "from": from_field,
            "to": [to_email],
            "subject": payload.get("subject", "(no subject)"),
        }
        if payload.get("html_body"):
            body["html"] = payload["html_body"]
        if payload.get("text_body"):
            body["text"] = payload["text_body"]
        if payload.get("reply_to"):
            body["reply_to"] = payload["reply_to"]

        # Tags (Resend format: list of {name, value})
        tags = payload.get("tags", {})
        if isinstance(tags, dict) and tags:
            body["tags"] = [{"name": k, "value": str(v)[:255]} for k, v in tags.items()]

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )

            if resp.status_code in (200, 201):
                data = resp.json()
                log.info("resend.sent", to=to_email, id=data.get("id"))
                return ProviderResult(
                    success=True,
                    provider_id=data.get("id"),
                    status="sent",
                    raw_response=data,
                )
            else:
                err = resp.json().get("message", resp.text)
                log.error("resend.send_failed", to=to_email, status=resp.status_code, error=err)
                return ProviderResult(success=False, error=f"Resend {resp.status_code}: {err}")

        except Exception as e:
            log.error("resend.exception", error=str(e))
            return ProviderResult(success=False, error=str(e))

    async def add_suppression(self, email: str, reason: str) -> bool:
        """Add email to Resend suppression list."""
        import httpx
        if not self.api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    "https://api.resend.com/audiences",  # suppression in Resend is contact-level
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"email": email},
                )
            return resp.status_code in (200, 201, 409)
        except Exception:
            return False

    async def get_suppressions(self) -> list[str]:
        """Resend doesn't have a direct suppression list API — return empty."""
        return []

    async def handle_webhook(self, payload: dict) -> dict:
        return {
            "event": payload.get("type"),
            "email": payload.get("data", {}).get("to", [None])[0],
            "provider_id": payload.get("data", {}).get("email_id"),
            "provider": "resend",
        }


class SignalWireSmsProvider(SmsProvider):
    """
    SignalWire — SMS/voice. Compatible with Twilio SDK.
    Auth: Account SID + Auth Token (Basic auth).
    Sandbox: Yes — sandbox relay numbers available.
    Opt-out: STOP keyword handling built-in.
    Docs: https://developer.signalwire.com
    Note: Already configured in existing signalwire.py service — this is the campaign adapter.
    """
    name = "signalwire"

    def __init__(self, account_sid: str, auth_token: str, space: str, from_number: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.space = space
        self.from_number = from_number

    async def send_sms(self, payload: dict) -> ProviderResult:
        # Reuse existing signalwire integration service
        try:
            from app.services.integrations.signalwire import send_sms as sw_send
            result = await sw_send(payload["to_phone"], payload["body"])
            return ProviderResult(success=result, status="sent" if result else "failed")
        except Exception as e:
            return ProviderResult(success=False, error=str(e))

    async def handle_inbound(self, payload: dict) -> dict:
        return {"from": payload.get("From"), "body": payload.get("Body"), "provider": "signalwire"}

    async def handle_opt_out(self, phone: str) -> bool:
        return True  # SignalWire handles STOP automatically

    async def handle_webhook(self, payload: dict) -> dict:
        return {"event": payload.get("SmsStatus", "delivered"), "provider": "signalwire"}


class TwilioSmsProvider(SmsProvider):
    """
    Twilio — SMS/voice. Grandfathered users or future swap target.
    Auth: Account SID + Auth Token.
    Docs: https://www.twilio.com/docs
    """
    name = "twilio"

    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number

    async def send_sms(self, payload: dict) -> ProviderResult:
        """Send SMS via Twilio REST API using httpx — no Twilio SDK required."""
        import httpx, base64

        if not self.account_sid or not self.auth_token:
            return ProviderResult(success=False, error="TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN not configured")

        to_phone = payload.get("to_phone")
        body = payload.get("body", "")
        if not to_phone or not body:
            return ProviderResult(success=False, error="to_phone and body are required")
        if not self.from_number:
            return ProviderResult(success=False, error="TWILIO_FROM_NUMBER not configured")

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        creds = base64.b64encode(f"{self.account_sid}:{self.auth_token}".encode()).decode()

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    url,
                    headers={"Authorization": f"Basic {creds}"},
                    data={"From": self.from_number, "To": to_phone, "Body": body},
                )
            if resp.status_code in (200, 201):
                data = resp.json()
                log.info("twilio.sms.sent", to=to_phone, sid=data.get("sid"))
                return ProviderResult(
                    success=True,
                    provider_id=data.get("sid"),
                    status=data.get("status", "queued"),
                    raw_response=data,
                )
            else:
                err = resp.json().get("message", resp.text)
                log.error("twilio.sms.failed", to=to_phone, status=resp.status_code, error=err)
                return ProviderResult(success=False, error=f"Twilio {resp.status_code}: {err}")
        except Exception as e:
            log.error("twilio.sms.exception", error=str(e))
            return ProviderResult(success=False, error=str(e))

    async def handle_inbound(self, payload: dict) -> dict:
        return {"from": payload.get("From"), "body": payload.get("Body"), "provider": "twilio"}

    async def handle_opt_out(self, phone: str) -> bool:
        return True

    async def handle_webhook(self, payload: dict) -> dict:
        return {"event": payload.get("SmsStatus"), "provider": "twilio"}


class AttomPropertyDataProvider(PropertyDataProvider):
    """
    ATTOM Data Solutions — property + mortgage data, AVM, ownership history.
    Auth: apikey header.
    Coverage: US nationwide, deep mortgage/lien history.
    Pricing: Per-call or subscription — check attomdata.com/products/property-data-api
    Docs: https://api.developer.attomdata.com/docs
    """
    name = "attom"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def search_properties(self, payload: dict) -> list[PropertyResult]:
        raise NotImplementedError("ATTOM — use httpx with apikey header")

    async def enrich_property(self, address: str) -> PropertyResult:
        raise NotImplementedError

    async def estimate_equity(self, address: str, loan_balance: float) -> PropertyResult:
        raise NotImplementedError
