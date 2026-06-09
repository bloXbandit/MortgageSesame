"""
SignalWire SMS connector — consent-gated only.

SMS is never sent unless:
1. contact.consent_sms == True
2. contact.is_dnc == False
3. contact.is_opted_out == False
4. The message passes compliance check

The agent's SignalWire number is the outbound caller ID for any voice flows.
"""

from app.config import settings
from app.services.compliance import check_contact_sendable
import httpx


async def send_sms(to_number: str, body: str, contact=None) -> dict:
    if contact:
        can_send, reason = check_contact_sendable(contact)
        if not can_send:
            raise PermissionError(f"Cannot send SMS: {reason}")
        if not contact.consent_sms:
            raise PermissionError("Contact has not consented to SMS.")

    if not settings.signalwire_account_sid or not settings.signalwire_auth_token:
        raise RuntimeError("SignalWire not configured. Set SIGNALWIRE_ACCOUNT_SID and SIGNALWIRE_AUTH_TOKEN in .env")

    url = f"https://{settings.signalwire_space}.signalwire.com/api/laml/2010-04-01/Accounts/{settings.signalwire_account_sid}/Messages.json"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            url,
            auth=(settings.signalwire_account_sid, settings.signalwire_auth_token),
            data={"To": to_number, "From": settings.signalwire_from_number, "Body": body},
        )
        response.raise_for_status()
        return response.json()
