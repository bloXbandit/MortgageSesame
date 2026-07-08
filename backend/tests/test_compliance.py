"""
Regression tests for compliance guardrails.

These are the highest-leverage tests in the repo:
they pin exactly which phrases trigger which severity,
and guarantee a suppressed/DNC contact can never be messaged.

Run: pytest tests/test_compliance.py -v
"""

import pytest
from app.services.compliance import check_content, check_contact_sendable, Severity


class TestBlockedPhrases:
    """Phrases that must never reach a prospect under any channel."""

    @pytest.mark.parametrize("phrase", [
        "we offer guaranteed approval for everyone",
        "guaranteed loan for all applicants",
        "you are guaranteed financing",
    ])
    def test_guaranteed_approval_blocked(self, phrase):
        result = check_content(phrase)
        assert not result.passed
        assert any(f["rule"] == "guaranteed_approval" for f in result.flags)
        assert any(f["severity"] == Severity.BLOCKED.value for f in result.flags)

    @pytest.mark.parametrize("phrase", [
        "get 100% approval today",
        "100% guaranteed financing",
    ])
    def test_100pct_guaranteed_blocked(self, phrase):
        result = check_content(phrase)
        assert not result.passed
        assert any(f["rule"] == "guaranteed_100pct" for f in result.flags)

    @pytest.mark.parametrize("phrase", [
        "no credit check required",
        "no income verification needed",
        "no doc loan available",
    ])
    def test_no_verification_blocked(self, phrase):
        result = check_content(phrase)
        assert not result.passed
        assert any(f["rule"] == "no_verification_claim" for f in result.flags)

    @pytest.mark.parametrize("phrase", [
        "instant approval in 5 minutes",
        "get instant pre-approval now",
    ])
    def test_instant_approval_blocked(self, phrase):
        result = check_content(phrase)
        assert not result.passed
        assert any(f["rule"] == "instant_approval" for f in result.flags)

    @pytest.mark.parametrize("phrase", [
        "I will pay you for referrals",
        "i am paying you for sending leads",
        "kickback for every closed deal",
        "split my commission with you",
    ])
    def test_referral_fee_blocked(self, phrase):
        result = check_content(phrase)
        assert not result.passed
        assert any(
            f["rule"] in ("referral_fee_language", "kickback_language")
            for f in result.flags
        )

    def test_false_gov_affiliation_blocked(self):
        result = check_content("government approved mortgage program")
        assert not result.passed
        assert any(f["rule"] == "false_gov_affiliation" for f in result.flags)

    # FHA/VA/USDA are legitimate — should NOT trigger false gov claim
    def test_real_gov_programs_allowed(self):
        result = check_content("FHA government backed loan with VA benefits")
        assert result.passed
        assert not any(f["rule"] == "false_gov_affiliation" for f in result.flags)

    def test_fake_testimonial_blocked(self):
        result = check_content("here is a fabricated testimonial from a fake closing")
        assert not result.passed
        assert any(f["rule"] == "fake_testimonial" for f in result.flags)


class TestHighSeverityPatterns:
    """Warnings that require human review before sending."""

    def test_lowest_rate_superlative(self):
        result = check_content("we have the lowest rates in Maryland")
        assert any(f["rule"] == "lowest_rate_superlative" for f in result.flags)
        assert any(f["severity"] == Severity.HIGH.value for f in result.flags)

    def test_false_urgency(self):
        result = check_content("act now before rates go up tomorrow")
        assert any(f["rule"] == "false_urgency" for f in result.flags)

    def test_teaser_rate(self):
        result = check_content("rates as low as 3.5%")
        assert any(f["rule"] == "teaser_rate" for f in result.flags)

    def test_tax_claim(self):
        result = check_content("get tax exempt cash from your home")
        assert any(f["rule"] == "tax_claim" for f in result.flags)


class TestMediumSeverityPatterns:
    """Guidance-level flags."""

    def test_free_money_misleading(self):
        result = check_content("the government gives you free money for a down payment")
        assert any(f["rule"] == "misleading_free_money" for f in result.flags)
        assert any(f["severity"] == Severity.MEDIUM.value for f in result.flags)

    def test_no_down_payment_without_program(self):
        result = check_content("buy with no money down")
        assert any(f["rule"] == "no_down_payment" for f in result.flags)

    def test_va_usda_no_down_allowed(self):
        result = check_content("buy with no down payment with VA loan")
        assert not any(f["rule"] == "no_down_payment" for f in result.flags)

    def test_scare_tactic(self):
        result = check_content("your house is at risk if you don't refinance")
        assert any(f["rule"] == "scare_tactic" for f in result.flags)


class TestOptOutRequirement:
    """Email and SMS must carry unsubscribe language."""

    def test_email_missing_opt_out_flagged(self):
        result = check_content("Great rates available! Call today.", channel="email")
        assert any(f["rule"] == "missing_opt_out" for f in result.flags)

    def test_email_with_opt_out_passes(self):
        result = check_content(
            "Great rates available! Reply STOP to unsubscribe.", channel="email"
        )
        assert not any(f["rule"] == "missing_opt_out" for f in result.flags)

    def test_sms_missing_opt_out_flagged(self):
        result = check_content("Hi, want a lower rate?", channel="sms")
        assert any(f["rule"] == "missing_opt_out" for f in result.flags)

    def test_sms_with_opt_out_passes(self):
        result = check_content("Hi! Reply STOP to opt out.", channel="sms")
        assert not any(f["rule"] == "missing_opt_out" for f in result.flags)

    def test_general_channel_no_opt_out_required(self):
        result = check_content("Great rates available!", channel="direct_mail")
        assert not any(f["rule"] == "missing_opt_out" for f in result.flags)


class TestAdDisclaimer:
    """Ads need NMLS / Equal Housing / not-a-commitment language."""

    def test_ad_missing_disclaimer(self):
        result = check_content("Lock in today's low rate!", is_ad=True)
        assert any(f["rule"] == "missing_ad_disclaimer" for f in result.flags)

    def test_ad_with_nmls_passes(self):
        result = check_content(
            "Great rates! NMLS #1454510. Equal Housing Lender.", is_ad=True
        )
        assert not any(f["rule"] == "missing_ad_disclaimer" for f in result.flags)

    def test_ad_with_not_commitment_passes(self):
        result = check_content(
            "Rates subject to change. Not a commitment to lend.", is_ad=True
        )
        assert not any(f["rule"] == "missing_ad_disclaimer" for f in result.flags)


class TestContactSendable:
    """DNC and opted-out contacts must be hard-blocked at send time."""

    class FakeContact:
        def __init__(self, dnc=False, opted=False):
            self.is_dnc = dnc
            self.is_opted_out = opted

    def test_normal_contact_sendable(self):
        ok, reason = check_contact_sendable(self.FakeContact(dnc=False, opted=False))
        assert ok is True
        assert reason == ""

    def test_dnc_blocked(self):
        ok, reason = check_contact_sendable(self.FakeContact(dnc=True, opted=False))
        assert ok is False
        assert "Do-Not-Contact" in reason

    def test_opted_out_blocked(self):
        ok, reason = check_contact_sendable(self.FakeContact(dnc=False, opted=True))
        assert ok is False
        assert "opted out" in reason

    def test_both_flags_blocked(self):
        ok, reason = check_contact_sendable(self.FakeContact(dnc=True, opted=True))
        assert ok is False
