"""
Abstract provider interfaces.

Every real provider adapter must implement one of these base classes.
The campaign engine calls only these interface methods — swap providers
by registering a new adapter in registry.py without touching engine code.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


# ── Shared result types ────────────────────────────────────────────────────────

@dataclass
class ProviderResult:
    success: bool
    provider_id: Optional[str] = None       # provider-assigned ID (message_id, job_id, etc.)
    status: str = "unknown"
    raw_response: Optional[dict] = None
    error: Optional[str] = None


@dataclass
class AddressResult:
    valid: bool
    deliverable: bool = False
    standardized_line1: Optional[str] = None
    standardized_city: Optional[str] = None
    standardized_state: Optional[str] = None
    standardized_zip: Optional[str] = None
    dpv_match: Optional[str] = None     # Y / S / D / N
    vacancy: Optional[str] = None
    error: Optional[str] = None


@dataclass
class PropertyResult:
    found: bool
    address: Optional[str] = None
    estimated_value: Optional[float] = None
    equity_pct: Optional[float] = None
    equity_dollars: Optional[float] = None
    loan_amount: Optional[float] = None
    origination_date: Optional[str] = None
    loan_type: Optional[str] = None
    rate_estimate: Optional[float] = None
    owner_name: Optional[str] = None
    is_owner_occupied: Optional[bool] = None
    raw_data: Optional[dict] = None
    error: Optional[str] = None


# ── Direct Mail Provider ───────────────────────────────────────────────────────

class DirectMailProvider(ABC):
    """
    Abstract interface for direct mail APIs (Lob, PostGrid, Click2Mail, etc.)
    """
    name: str = "base"

    @abstractmethod
    async def validate_address(self, address: dict) -> AddressResult:
        """Validate and standardize a mailing address."""
        ...

    @abstractmethod
    async def create_mail_piece(self, payload: dict) -> ProviderResult:
        """
        Submit a mail piece for printing and mailing.
        payload keys: to_name, to_address, from_name, from_address,
                      html_front, html_back, mail_type (postcard/letter),
                      metadata, description
        """
        ...

    @abstractmethod
    async def get_mail_status(self, provider_id: str) -> ProviderResult:
        """Get the current status of a submitted mail piece."""
        ...

    @abstractmethod
    async def handle_webhook(self, payload: dict) -> dict:
        """Parse an inbound provider webhook and return normalized event dict."""
        ...


# ── Email Provider ─────────────────────────────────────────────────────────────

class EmailProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def send_email(self, payload: dict) -> ProviderResult:
        """
        Send a single email.
        payload keys: to_email, to_name, from_email, from_name,
                      subject, html_body, text_body, reply_to,
                      tags, metadata, unsubscribe_url
        """
        ...

    @abstractmethod
    async def add_suppression(self, email: str, reason: str) -> bool:
        """Add an email address to the provider suppression list."""
        ...

    @abstractmethod
    async def get_suppressions(self) -> list[str]:
        """Return all suppressed email addresses from this provider."""
        ...

    @abstractmethod
    async def handle_webhook(self, payload: dict) -> dict:
        """Parse provider webhook (bounce, complaint, open, click, unsubscribe)."""
        ...


# ── SMS Provider ───────────────────────────────────────────────────────────────

class SmsProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def send_sms(self, payload: dict) -> ProviderResult:
        """
        Send an SMS. Should only be called after consent verification.
        payload keys: to_phone, from_phone, body, media_url (optional)
        """
        ...

    @abstractmethod
    async def handle_inbound(self, payload: dict) -> dict:
        """Handle an inbound SMS reply."""
        ...

    @abstractmethod
    async def handle_opt_out(self, phone: str) -> bool:
        """Process a STOP/opt-out from a phone number."""
        ...

    @abstractmethod
    async def handle_webhook(self, payload: dict) -> dict:
        """Parse provider delivery status / inbound webhooks."""
        ...


# ── Voice / Call Provider ──────────────────────────────────────────────────────

class VoiceProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def provision_tracking_number(self, label: str) -> ProviderResult:
        """Provision a trackable local or toll-free number for a campaign."""
        ...

    @abstractmethod
    async def handle_call_webhook(self, payload: dict) -> dict:
        """Parse inbound call or voicemail webhook."""
        ...


# ── Address Verification Provider ──────────────────────────────────────────────

class AddressVerificationProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def verify_address(self, address: dict) -> AddressResult:
        ...

    @abstractmethod
    async def standardize_address(self, address: dict) -> AddressResult:
        ...


# ── Property Data Provider ─────────────────────────────────────────────────────

class PropertyDataProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def search_properties(self, payload: dict) -> list[PropertyResult]:
        """Search properties by address, owner, ZIP, etc."""
        ...

    @abstractmethod
    async def enrich_property(self, address: str) -> PropertyResult:
        """Get full property + mortgage details for a known address."""
        ...

    @abstractmethod
    async def estimate_equity(self, address: str, loan_balance: float) -> PropertyResult:
        """Estimate current equity based on AVM + loan balance."""
        ...
