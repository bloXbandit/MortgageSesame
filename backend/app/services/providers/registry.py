"""
Provider registry — returns the active provider for each channel based on env config.

Priority order:
  1. CAMPAIGN_{CHANNEL}_PROVIDER env var
  2. ProviderConfig table (UI-editable)
  3. Default: mock

Env var examples:
  CAMPAIGN_EMAIL_PROVIDER=resend
  CAMPAIGN_DIRECT_MAIL_PROVIDER=lob
  CAMPAIGN_SMS_PROVIDER=signalwire
"""

import os
from app.services.providers.base import (
    DirectMailProvider, EmailProvider, SmsProvider,
    VoiceProvider, AddressVerificationProvider, PropertyDataProvider,
)
from app.services.providers.mock import (
    MockDirectMailProvider, MockEmailProvider, MockSmsProvider,
    MockVoiceProvider, MockAddressVerificationProvider, MockPropertyDataProvider,
    LobDirectMailProvider, PostGridDirectMailProvider,
    SendGridEmailProvider, ResendEmailProvider,
    SignalWireSmsProvider, TwilioSmsProvider,
    AttomPropertyDataProvider,
)
from app.services.providers.gmail import GmailEmailProvider


def _env(key: str, default: str = "mock") -> str:
    return os.getenv(key, default).lower().strip()


def get_direct_mail_provider() -> DirectMailProvider:
    name = _env("CAMPAIGN_DIRECT_MAIL_PROVIDER")
    if name == "lob":
        key = os.getenv("LOB_API_KEY", "")
        if not key:
            raise ValueError("LOB_API_KEY not set. Set it or use CAMPAIGN_DIRECT_MAIL_PROVIDER=mock")
        return LobDirectMailProvider(api_key=key)
    if name == "postgrid":
        key = os.getenv("POSTGRID_API_KEY", "")
        if not key:
            raise ValueError("POSTGRID_API_KEY not set.")
        return PostGridDirectMailProvider(api_key=key)
    return MockDirectMailProvider()


def get_email_provider() -> EmailProvider:
    name = _env("CAMPAIGN_EMAIL_PROVIDER")
    if name == "gmail":
        return GmailEmailProvider(
            smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_user=os.getenv("SMTP_USER", ""),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            from_email=os.getenv("CAMPAIGN_FROM_EMAIL", os.getenv("SMTP_USER", "")),
            from_name=os.getenv("CAMPAIGN_FROM_NAME", ""),
        )
    if name == "sendgrid":
        return SendGridEmailProvider(
            api_key=os.getenv("SENDGRID_API_KEY", ""),
            from_email=os.getenv("CAMPAIGN_FROM_EMAIL", os.getenv("SMTP_USER", "")),
            from_name=os.getenv("CAMPAIGN_FROM_NAME", "MortgageSesame"),
        )
    if name == "resend":
        return ResendEmailProvider(
            api_key=os.getenv("RESEND_API_KEY", ""),
            from_email=os.getenv("CAMPAIGN_FROM_EMAIL", os.getenv("SMTP_USER", "")),
            from_name=os.getenv("CAMPAIGN_FROM_NAME", "MortgageSesame"),
        )
    return MockEmailProvider()


def get_sms_provider() -> SmsProvider:
    name = _env("CAMPAIGN_SMS_PROVIDER")
    if name == "signalwire":
        return SignalWireSmsProvider(
            account_sid=os.getenv("SIGNALWIRE_ACCOUNT_SID", ""),
            auth_token=os.getenv("SIGNALWIRE_AUTH_TOKEN", ""),
            space=os.getenv("SIGNALWIRE_SPACE", ""),
            from_number=os.getenv("SIGNALWIRE_FROM_NUMBER", ""),
        )
    if name == "twilio":
        return TwilioSmsProvider(
            account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
            auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
            from_number=os.getenv("TWILIO_FROM_NUMBER", ""),
        )
    return MockSmsProvider()


def get_voice_provider() -> VoiceProvider:
    return MockVoiceProvider()


def get_address_provider() -> AddressVerificationProvider:
    return MockAddressVerificationProvider()


def get_property_provider() -> PropertyDataProvider:
    name = _env("CAMPAIGN_PROPERTY_PROVIDER")
    if name == "attom":
        return AttomPropertyDataProvider(api_key=os.getenv("ATTOM_API_KEY", ""))
    return MockPropertyDataProvider()


def get_provider(channel: str):
    """
    Convenience dispatcher.
    channel: 'direct_mail' | 'email' | 'sms' | 'voice' | 'address' | 'property'
    """
    dispatch = {
        "direct_mail": get_direct_mail_provider,
        "email": get_email_provider,
        "sms": get_sms_provider,
        "voice": get_voice_provider,
        "address": get_address_provider,
        "address_verify": get_address_provider,
        "property": get_property_provider,
    }
    fn = dispatch.get(channel)
    if not fn:
        raise ValueError(f"Unknown provider channel: {channel}")
    return fn()
