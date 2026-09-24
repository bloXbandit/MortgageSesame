"""
Campaign scheduler — one tick of the outreach/content engine.

Responsibilities:
  1. Sequence advancement — for each ACTIVE campaign, find prospects whose
     previous step was sent long enough ago (CampaignStep.delay_days is
     cumulative days since step 1) and generate the NEXT step as a draft.
     Nothing auto-sends: new items land in the approval flow.
  2. Scheduled social posts — SocialPost rows marked SCHEDULED whose
     scheduled_date has passed get published via the publisher registry.
     Scheduling IS the approval, so this does not bypass the gate.
  3. Callback resurfacing — CallTask rows in CALLBACK_SCHEDULED whose
     callback_scheduled_at has passed flip back to PENDING.

Entry points:
  - POST /outreach/scheduler/run   (admin JWT or agent key)
  - background loop in main.py lifespan (SCHEDULER_ENABLED / SCHEDULER_INTERVAL_MINUTES)
"""

from datetime import datetime, timedelta
from typing import Optional

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.campaign import Campaign, CampaignStep, CampaignStatus, MessageTemplate
from app.models.content import SocialPost, ApprovalStatus
from app.models.outreach import (
    CampaignOutreach, CallTask, Prospect,
    OutreachChannel, OutreachStatus, CallTaskStatus,
)
from app.services.campaign_writer import get_writer
from app.services.compliance import check_content
from app.middleware.audit import log_event

log = structlog.get_logger()

# Statuses that count as "step was actually sent"
SENT_STATUSES = {
    OutreachStatus.SENT, OutreachStatus.DELIVERED, OutreachStatus.OPENED,
    OutreachStatus.CLICKED, OutreachStatus.REPLIED, OutreachStatus.QR_SCANNED,
    OutreachStatus.IN_PRODUCTION, OutreachStatus.MAILED, OutreachStatus.QUEUED,
    OutreachStatus.CONVERTED,
}

# Terminal signals — never drip on these prospects again
STOP_STATUSES = {
    OutreachStatus.REPLIED, OutreachStatus.OPTED_OUT, OutreachStatus.CONVERTED,
    OutreachStatus.REJECTED, OutreachStatus.COMPLIANCE_BLOCKED,
}

PENDING_STATUSES = {
    OutreachStatus.DRAFT, OutreachStatus.PENDING_COMPLIANCE,
    OutreachStatus.COMPLIANCE_PASSED, OutreachStatus.PENDING_APPROVAL,
    OutreachStatus.APPROVED, OutreachStatus.QUEUED,
}


async def run_scheduler_tick(db: AsyncSession) -> dict:
    """One pass over all due work. Returns a summary dict."""
    summary = {
        "ran_at": datetime.utcnow().isoformat(),
        "steps_generated": 0,
        "posts_published": 0,
        "posts_failed": 0,
        "callbacks_resurfaced": 0,
        "details": [],
    }

    await _advance_sequences(db, summary)
    await _publish_due_posts(db, summary)
    await _resurface_callbacks(db, summary)

    await db.commit()
    log.info("scheduler.tick", **{k: v for k, v in summary.items() if k != "details"})
    return summary


# ── 1. Sequence advancement ─────────────────────────────────────────────────

async def _advance_sequences(db: AsyncSession, summary: dict) -> None:
    campaigns = (await db.execute(
        select(Campaign).where(Campaign.status == CampaignStatus.ACTIVE)
    )).scalars().all()

    for campaign in campaigns:
        steps = (await db.execute(
            select(CampaignStep)
            .where(CampaignStep.campaign_id == campaign.id)
            .order_by(CampaignStep.step_order)
        )).scalars().all()
        if len(steps) < 2:
            continue  # nothing to advance to

        # All outreach for this campaign that has a prospect attached
        items = (await db.execute(
            select(CampaignOutreach)
            .where(CampaignOutreach.campaign_id == campaign.id)
            .where(CampaignOutreach.prospect_id.isnot(None))
        )).scalars().all()

        # Group by prospect
        by_prospect: dict = {}
        for it in items:
            by_prospect.setdefault(it.prospect_id, []).append(it)

        for prospect_id, prospect_items in by_prospect.items():
            try:
                await _advance_prospect(db, campaign, steps, prospect_id, prospect_items, summary)
            except Exception as e:
                log.error("scheduler.advance_failed", campaign=campaign.id,
                          prospect=prospect_id, error=str(e))
                summary["details"].append(
                    f"advance failed for prospect {prospect_id}: {e}")


async def _advance_prospect(
    db: AsyncSession,
    campaign: Campaign,
    steps: list,
    prospect_id: str,
    items: list,
    summary: dict,
) -> None:
    # Stop conditions — prospect replied, opted out, or is suppressed
    if any(i.status in STOP_STATUSES for i in items):
        return
    prospect = (await db.execute(
        select(Prospect).where(Prospect.id == prospect_id))).scalar_one_or_none()
    if not prospect or prospect.is_do_not_contact or prospect.is_suppressed:
        return

    sent = [i for i in items if i.status in SENT_STATUSES and i.sent_at and i.step_number]
    if not sent:
        return  # step 1 hasn't been sent yet — nothing to advance from

    last_step_num = max(i.step_number for i in sent)
    last_sent_at = max(i.sent_at for i in sent if i.step_number == last_step_num)

    # Next campaign step after the last one sent
    next_step = next((s for s in steps if s.step_order > last_step_num), None)
    if not next_step:
        return  # sequence complete

    # Already have an item for the next step (drafted/approved/queued/sent)?
    if any(i.step_number == next_step.step_order for i in items):
        return

    prev_step = next((s for s in steps if s.step_order == last_step_num), None)
    wait_days = next_step.delay_days - (prev_step.delay_days if prev_step else 0)
    if datetime.utcnow() < last_sent_at + timedelta(days=max(wait_days, 0)):
        return  # not due yet

    # Due — generate the next step
    channel = _map_channel(next_step.channel)
    if channel is None:
        summary["details"].append(
            f"campaign {campaign.id} step {next_step.step_order}: "
            f"unsupported channel {next_step.channel} — skipped")
        return

    outreach = CampaignOutreach(
        campaign_id=campaign.id,
        prospect_id=prospect.id,
        channel=channel,
        step_number=next_step.step_order,
        status=OutreachStatus.DRAFT,
        approval_status="pending",
    )

    campaign_type = campaign.campaign_type.value if campaign.campaign_type else "refi_rate_reduction"
    writer = get_writer()

    # Prefer the step's own MessageTemplate (AI-written for this campaign);
    # fall back to the campaign_writer per-prospect generator.
    template = None
    if next_step.template_id:
        template = (await db.execute(
            select(MessageTemplate).where(MessageTemplate.id == next_step.template_id)
        )).scalar_one_or_none()

    def _merge(text):
        """Resolve [Name]/{first_name} merge fields for this prospect."""
        import re as _re
        if not text:
            return text
        first = prospect.first_name or (prospect.full_name or "").split()[0] or "there"
        return _re.sub(r"\[(name|first\s*name|first_name)\]|\{(name|first_name)\}",
                       first, text, flags=_re.IGNORECASE)

    if channel == OutreachChannel.EMAIL:
        if template and template.body:
            outreach.subject = _merge(template.subject or f"{campaign.name} — Step {next_step.step_order}")
            outreach.body_text = _merge(template.body)
            outreach.body_html = "<p>" + outreach.body_text.replace("\n\n", "</p><p>").replace("\n", "<br>") + "</p>"
            outreach.template_name = template.name
        else:
            draft = await writer.generate_email(
                prospect, campaign_type=campaign_type, step=next_step.step_order)
            outreach.subject = draft.subject
            outreach.body_html = draft.body_html
            outreach.body_text = draft.body_text
            outreach.merge_data = draft.merge_data
            outreach.template_name = f"{campaign_type} email step {next_step.step_order}"
    elif channel == OutreachChannel.SMS:
        if template and template.body:
            outreach.body_text = _merge(template.body)
            outreach.template_name = template.name
        else:
            draft = await writer.generate_sms(
                prospect, campaign_type=campaign_type, step=next_step.step_order)
            outreach.body_text = draft.body
            outreach.template_name = f"{campaign_type} sms step {next_step.step_order}"
    elif channel == OutreachChannel.DIRECT_MAIL:
        merge = await writer.generate_mail_merge_data(prospect, template_key="equity_voucher")
        from app.services.mail_templates import render_mail_template
        outreach.body_html = render_mail_template("equity_voucher", merge)
        outreach.merge_data = merge
        outreach.template_key = "equity_voucher"
        outreach.template_name = f"step {next_step.step_order} mail"
    elif channel == OutreachChannel.CALL_TASK:
        script = await writer.generate_call_script(prospect, campaign_type=campaign_type)
        outreach.call_script = script.pitch
        outreach.merge_data = {
            "opener": script.opener, "pitch": script.pitch,
            "talking_points": script.talking_points,
            "objection_handlers": script.objection_handlers,
            "close": script.close, "voicemail": script.voicemail,
        }
        outreach.template_name = f"{campaign_type} call step {next_step.step_order}"

    # Compliance gate — same check the manual path would face
    text = outreach.body_text or outreach.body_html or outreach.call_script or ""
    if text:
        result = check_content(text, channel=channel.value)
        outreach.compliance_status = "blocked" if not result.passed else ("warning" if result.flags else "pass")
        outreach.compliance_flags = result.flags
        if not result.passed:
            outreach.status = OutreachStatus.COMPLIANCE_BLOCKED

    db.add(outreach)
    summary["steps_generated"] += 1
    summary["details"].append(
        f"campaign '{campaign.name}' → {prospect.full_name or prospect.id} "
        f"step {next_step.step_order} ({channel.value}) drafted")
    log.info("scheduler.step_drafted", campaign=campaign.id, prospect=prospect.id,
             step=next_step.step_order, channel=channel.value,
             compliance=outreach.compliance_status)

    await log_event(db, "scheduler.step_drafted", actor_type="system",
                    resource_type="campaign_outreach", resource_id=outreach.id,
                    details={"campaign_id": campaign.id, "prospect_id": prospect.id,
                             "step": next_step.step_order, "channel": channel.value})


def _map_channel(step_channel) -> Optional[OutreachChannel]:
    """Campaign Channel enum → OutreachChannel enum."""
    name = step_channel.value if hasattr(step_channel, "value") else str(step_channel)
    return {
        "email": OutreachChannel.EMAIL,
        "sms": OutreachChannel.SMS,
        "direct_mail": OutreachChannel.DIRECT_MAIL,
        "call_task": OutreachChannel.CALL_TASK,
    }.get(name)


# ── 2. Scheduled social posts ────────────────────────────────────────────────

async def _publish_due_posts(db: AsyncSession, summary: dict) -> None:
    due = (await db.execute(
        select(SocialPost)
        .where(SocialPost.approval_status == ApprovalStatus.SCHEDULED)
        .where(SocialPost.scheduled_date.isnot(None))
        .where(SocialPost.scheduled_date <= datetime.utcnow())
    )).scalars().all()

    for post in due:
        try:
            video_url = None
            for m in reversed(post.media_asset_ids or []):
                if m.get("type") in ("video_final", "video_raw") and m.get("url"):
                    video_url = m["url"]
                    break

            if not video_url:
                summary["details"].append(f"post {post.id} due but has no video asset — skipped")
                continue

            from app.services.publishers.registry import get_publisher
            from app.services.publishers.base import PublishPayload

            publisher = get_publisher(post.platform.value if post.platform else "")
            result = await publisher.publish(PublishPayload(
                video_url=video_url,
                caption=post.caption or "",
                platform=post.platform.value if post.platform else "",
                post_id=post.id,
            ))

            if result.success:
                post.approval_status = ApprovalStatus.PUBLISHED
                post.published_at = datetime.utcnow()
                post.external_post_id = result.external_post_id
                summary["posts_published"] += 1
                summary["details"].append(f"post {post.id} published to {post.platform}")
                await log_event(db, "content.published", actor_type="system",
                                resource_type="social_post", resource_id=post.id,
                                details={"platform": str(post.platform),
                                         "external_id": result.external_post_id,
                                         "via": "scheduler"})
                log.info("scheduler.post_published", post=post.id)
            else:
                summary["posts_failed"] += 1
                summary["details"].append(f"post {post.id} publish failed: {result.error}")
                log.error("scheduler.publish_failed", post=post.id, error=result.error)
        except Exception as e:
            summary["posts_failed"] += 1
            summary["details"].append(f"post {post.id} publish error: {e}")
            log.error("scheduler.publish_error", post=post.id, error=str(e))


# ── 3. Callback resurfacing ─────────────────────────────────────────────────

async def _resurface_callbacks(db: AsyncSession, summary: dict) -> None:
    due = (await db.execute(
        select(CallTask)
        .where(CallTask.status == CallTaskStatus.CALLBACK_SCHEDULED)
        .where(CallTask.callback_scheduled_at.isnot(None))
        .where(CallTask.callback_scheduled_at <= datetime.utcnow())
    )).scalars().all()

    for task in due:
        task.status = CallTaskStatus.PENDING
        summary["callbacks_resurfaced"] += 1
        summary["details"].append(
            f"callback for {task.prospect_name or task.phone} resurfaced to queue")
        log.info("scheduler.callback_resurfaced", task=task.id)


# ── Background loop ──────────────────────────────────────────────────────────

async def scheduler_loop():
    """Runs run_scheduler_tick on an interval while the server is up."""
    import asyncio
    from app.database import AsyncSessionLocal

    interval = max(settings.scheduler_interval_minutes, 1) * 60
    log.info("scheduler.loop_started", interval_minutes=settings.scheduler_interval_minutes)
    while True:
        await asyncio.sleep(interval)
        try:
            async with AsyncSessionLocal() as db:
                await run_scheduler_tick(db)
        except Exception as e:
            log.error("scheduler.tick_failed", error=str(e))
