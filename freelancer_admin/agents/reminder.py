"""Reminder agent — generates tone-appropriate payment reminders and sends via Gmail."""

import smtplib
import ssl
import json
from email.message import EmailMessage
from datetime import datetime
from openai import OpenAI
from .. import database as db


TONE_GENTLE = "gentle"
TONE_FIRM = "firm"
TONE_URGENT = "urgent"

REMINDER_SYSTEM = """You are a professional email writer for a freelancer company called "Hallucination Hunters".
Write a payment reminder email using the data and tone below.

Required sections:
- Subject line
- Greeting
- Invoice reference
- Outstanding amount
- Original due date
- Days overdue
- Polite request for payment
- Payment instructions (if provided)
- Company signature: Hallucination Hunters | hallucination_hunters@gmail.com | 08043672418 | hallucination_hunters.com

Tone: {tone_desc}

Return JSON with two keys: "subject" (string) and "body" (string, plain text email body).
Reply with valid JSON only."""

TONE_DESC = {
    TONE_GENTLE: "Friendly reminder, assumes the client simply forgot. Warm, non-pressuring tone.",
    TONE_FIRM: "Polite but direct. Makes clear the payment is overdue and expected promptly.",
    TONE_URGENT: "Professional but firm. States consequences such as work pause or late fees if applicable.",
}

EXTRACT_SYSTEM = """You are a data-extraction assistant.
Given the user message about sending a payment reminder, extract:
  invoice_number – string or number
  client_name    – string (optional if invoice number is given)
  client_email   – string (optional)
Return valid JSON only. Omit fields not mentioned."""


def _detect_tone(days_overdue: int) -> str:
    """1-7 days: Gentle, 8-21 days: Firm, 22+ days: Urgent."""
    if days_overdue <= 7:
        return TONE_GENTLE
    elif days_overdue <= 21:
        return TONE_FIRM
    return TONE_URGENT  # 22+ days


def _extract_info(client: OpenAI, message: str, model="gpt-4o-mini") -> dict:
    resp = client.chat.completions.create(
        model=model, temperature=0, max_tokens=200,
        messages=[
            {"role": "system", "content": EXTRACT_SYSTEM},
            {"role": "user", "content": message},
        ],
    )
    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:])
    if raw.endswith("```"):
        raw = "\n".join(raw.split("\n")[:-1])
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _generate_reminder(client: OpenAI, invoice: dict, tone: str, days_overdue: int, model="gpt-4o-mini"):
    data = {
        "invoice_number": invoice.get("invoice_number"),
        "client_name": invoice.get("client_name"),
        "amount": invoice.get("grand_total"),
        "due_date": invoice.get("due_date"),
        "days_overdue": days_overdue,
        "payment_details": invoice.get("payment_details", ""),
    }
    sys_prompt = REMINDER_SYSTEM.format(tone_desc=TONE_DESC[tone])
    resp = client.chat.completions.create(
        model=model, temperature=0.6, max_tokens=800,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": json.dumps(data)},
        ],
    )
    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:])
    if raw.endswith("```"):
        raw = "\n".join(raw.split("\n")[:-1])
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"subject": f"Payment Reminder — Invoice #{invoice.get('invoice_number','')}", "body": raw}


def send_email(sender: str, app_pass: str, to_email: str, subject: str, body: str):
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
        smtp.login(sender, app_pass)
        smtp.send_message(msg)


# ── Public API ──────────────────────────────────────────────────────

def handle_reminder(oai_client: OpenAI, session: dict, user_message: str,
                    gmail_sender: str, gmail_pass: str, model="gpt-4o-mini"):
    """Returns (reply_text, reminder_draft_or_None, needs_confirm).

    When needs_confirm is True, the frontend should show a "Send Email" button.
    """
    # If we already have a draft waiting for confirmation
    draft = session.get("reminder_draft")
    lower = user_message.strip().lower()
    if draft and lower in ("yes", "send", "confirm", "send it", "send email"):
        # Pull email from invoice record first
        inv = db.get_invoice_by_number(draft.get("invoice_number", ""))
        email = inv.get("client_email") if inv else None
        # Fallback: client record, then session
        if not email:
            client_row = db.get_client_by_name(draft["client_name"])
            email = client_row.get("email") if client_row else None
        if not email:
            email = session.get("reminder_email")
        if not email:
            session["reminder_awaiting_email"] = True
            return "I need the client's email address to send the reminder. What is it?", None, False

        try:
            send_email(gmail_sender, gmail_pass, email, draft["subject"], draft["body"])
        except Exception as e:
            return f"❌ Failed to send email: {e}", None, False

        # Log it
        inv = db.get_invoice_by_number(draft.get("invoice_number", ""))
        cid = db.get_or_create_client(draft["client_name"])
        db.save_reminder(
            client_id=cid,
            invoice_id=inv["id"] if inv else None,
            invoice_number=draft.get("invoice_number", ""),
            client_name=draft["client_name"],
            reminder_message=draft["body"],
            subject=draft["subject"],
            sent=True,
        )
        session.pop("reminder_draft", None)
        return f"✅ Reminder email sent to **{email}** successfully!", None, False

    # If we're waiting for an email address
    if session.get("reminder_awaiting_email"):
        session["reminder_email"] = user_message.strip()
        session.pop("reminder_awaiting_email", None)
        # Update client record
        if draft:
            cid = db.get_or_create_client(draft["client_name"], email=user_message.strip())
        return ("Got it! Type **send** to confirm sending the reminder, "
                "or **cancel** to discard."), draft, True

    if draft and lower in ("no", "cancel", "discard"):
        session.pop("reminder_draft", None)
        return "Reminder discarded.", None, False

    # Extract info from user message
    info = _extract_info(oai_client, user_message, model)
    inv_num = info.get("invoice_number")
    if not inv_num:
        return "Which invoice number should I create a reminder for?", None, False

    invoice = db.get_invoice_by_number(str(inv_num))
    if not invoice:
        return f"I couldn't find invoice **#{inv_num}** in the system. Please check the number.", None, False

    # Capture email from the user message if provided
    extracted_email = info.get("client_email")
    if extracted_email:
        session["reminder_email"] = extracted_email
        # Also update the client record
        db.get_or_create_client(invoice["client_name"], email=extracted_email)

    # Calculate days overdue
    try:
        due = datetime.strptime(invoice["due_date"], "%Y-%m-%d")
        days_overdue = max((datetime.now() - due).days, 1)
    except Exception:
        days_overdue = 1

    tone = _detect_tone(days_overdue)
    reminder = _generate_reminder(oai_client, invoice, tone, days_overdue, model)

    session["reminder_draft"] = {
        **reminder,
        "invoice_number": invoice["invoice_number"],
        "client_name": invoice["client_name"],
    }

    tone_label = {"gentle": "Gentle", "firm": "Firm", "urgent": "Urgent"}
    reply = (
        f"**Payment Reminder Draft** ({tone_label.get(tone, tone)} tone -- {days_overdue} days overdue)\n\n"
        f"**Subject:** {reminder['subject']}\n\n"
        f"{reminder['body']}\n\n"
        "---\n"
        "Type **send** to email this reminder, or **cancel** to discard."
    )
    return reply, reminder, True
