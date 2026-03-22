"""Invoice conversation agent — collects fields, calculates totals, generates PDF."""

import os
import json
from datetime import datetime, timedelta
from openai import OpenAI
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)
from .. import database as db


OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_docs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

REQUIRED_FIELDS = [
    "client_name", "client_email", "project_name", "items", "due_date",
    "payment_details",
]

EXTRACT_SYSTEM = """You are a data-extraction assistant.
Given the conversation about an invoice, extract any of these fields if mentioned:

  client_name         - string (who is being billed)
  client_email        - string (the client's email address)
  project_name        - string (what project the invoice is for)
  items               - array of objects with keys: description, hours, rate
  invoice_number      - string (optional, auto-generated if missing)
  invoice_date        - string ISO date (default today)
  due_date            - string ISO date (payment due date)
  payment_details     - string (freelancer bank / payment details)
  tax_rate            - number (percentage, e.g. 18 means 18%)
  notes               - string (any additional message)

Return valid JSON only.
For "items", each item MUST have "description" (string), "hours" (number), "rate" (number).
If the user says something like "12 hours at $80/hr", create one item with those values.
If the user gives a single description with hours and rate, create one item.
Omit fields not mentioned."""


def _extract(client: OpenAI, conv: list, model="gpt-4o-mini") -> dict:
    text = "\n".join(f"{m['role']}: {m['content']}" for m in conv)
    resp = client.chat.completions.create(
        model=model, temperature=0, max_tokens=800,
        messages=[
            {"role": "system", "content": EXTRACT_SYSTEM},
            {"role": "user", "content": text},
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


def _missing(fields: dict) -> list:
    out = []
    for f in REQUIRED_FIELDS:
        val = fields.get(f)
        if not val:
            out.append(f)
        elif f == "items" and (not isinstance(val, list) or len(val) == 0):
            out.append(f)
    return out


def _ask(missing):
    # Always show the full template so the user can fill everything in one shot
    today = datetime.now().strftime("%Y-%m-%d")
    template = (
        "Client Name: \n\n"
        "Client Email: \n\n"
        "Project Name: \n\n"
        "Invoice Number: (leave blank for auto)\n\n"
        f"Invoice Date: {today}\n\n"
        "Due Date: \n\n"
        "Work Items: (e.g. Web Development)\n\n"
        "Hours per Item: \n\n"
        "Rate: ($ per hour)\n\n"
        "Tax / GST: (% or leave blank for none)\n\n"
        "Freelancer Bank / Payment Details: \n\n"
        "Notes: From Hallucination Hunters | hallucination_hunters@gmail.com | 08043672418"
    )
    return (
        "Please fill in the details below and send it back:\n\n"
        f"{template}"
    )


def _calc(fields: dict):
    items = fields.get("items", [])
    subtotal = 0.0
    for it in items:
        h = float(it.get("hours", 0))
        r = float(it.get("rate", 0))
        it["amount"] = round(h * r, 2)
        subtotal += it["amount"]
    tax_rate = float(fields.get("tax_rate", 0))
    tax_amount = round(subtotal * tax_rate / 100, 2)
    grand = round(subtotal + tax_amount, 2)
    return items, round(subtotal, 2), tax_rate, tax_amount, grand


def _build_pdf(fields: dict, path: str):
    items, subtotal, tax_rate, tax_amount, grand = _calc(fields)
    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    title_s = ParagraphStyle("T", parent=styles["Title"], fontSize=20, spaceAfter=4)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, spaceAfter=6)
    body = ParagraphStyle("B", parent=styles["BodyText"], fontSize=10, leading=14)

    story = []
    story.append(Paragraph("INVOICE", title_s))
    story.append(Spacer(1, 6))

    inv_num = fields.get("invoice_number", "---")
    inv_date = fields.get("invoice_date", datetime.now().strftime("%Y-%m-%d"))
    due = fields.get("due_date", "---")

    meta = (
        f"<b>Invoice #:</b> {inv_num} &nbsp;&nbsp; "
        f"<b>Date:</b> {inv_date} &nbsp;&nbsp; "
        f"<b>Due:</b> {due}"
    )
    story.append(Paragraph(meta, body))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"<b>Client:</b> {fields.get('client_name','')}", body))
    story.append(Paragraph(f"<b>Project:</b> {fields.get('project_name','')}", body))
    story.append(Spacer(1, 14))

    # Work items table
    data = [["#", "Work Item", "Hours", "Rate", "Amount"]]
    for i, it in enumerate(items, 1):
        data.append([
            str(i), it.get("description", ""),
            str(it.get("hours", "")), f"${it.get('rate', '')}",
            f"${it.get('amount', 0):.2f}",
        ])
    data.append(["", "", "", "Subtotal", f"${subtotal:.2f}"])
    if tax_rate:
        data.append(["", "", "", f"Tax ({tax_rate}%)", f"${tax_amount:.2f}"])
    data.append(["", "", "", "Grand Total", f"${grand:.2f}"])

    tbl = Table(data, colWidths=[1.2*cm, 8*cm, 2.5*cm, 2.5*cm, 3*cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 16))

    if fields.get("payment_details"):
        story.append(Paragraph("<b>Payment Instructions</b>", h2))
        pd = fields["payment_details"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        story.append(Paragraph(pd, body))
    if fields.get("notes"):
        story.append(Spacer(1, 8))
        nt = fields["notes"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        story.append(Paragraph(f"<b>Notes:</b> {nt}", body))

    doc.build(story)


# ── Public API ──────────────────────────────────────────────────────

def handle_invoice(client: OpenAI, session: dict, user_message: str, model="gpt-4o-mini"):
    """Returns (reply, invoice_id_or_None, is_complete)."""
    conv = session.setdefault("invoice_conv", [])
    conv.append({"role": "user", "content": user_message})

    fields = _extract(client, conv, model)
    stored = session.get("invoice_fields", {})
    # Merge items specially
    if "items" in fields and isinstance(fields["items"], list) and len(fields["items"]):
        stored["items"] = fields["items"]
    stored.update({k: v for k, v in fields.items() if v and k != "items"})
    session["invoice_fields"] = stored

    missing = _missing(stored)
    if missing:
        q = _ask(missing)
        conv.append({"role": "assistant", "content": q})
        return q, None, False

    # Fill defaults
    inv_num = stored.get("invoice_number")
    if not inv_num or db.get_invoice_by_number(str(inv_num)):
        stored["invoice_number"] = db.next_invoice_number()
    if not stored.get("invoice_date"):
        stored["invoice_date"] = datetime.now().strftime("%Y-%m-%d")
    if not stored.get("due_date"):
        stored["due_date"] = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    items, subtotal, tax_rate, tax_amount, grand = _calc(stored)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_path = os.path.join(OUTPUT_DIR, f"invoice_{stored['invoice_number']}_{ts}.pdf")
    _build_pdf(stored, pdf_path)

    cid = db.get_or_create_client(stored["client_name"], email=stored.get("client_email"))
    iid = db.save_invoice(
        invoice_number=stored["invoice_number"],
        client_id=cid,
        client_name=stored["client_name"],
        client_email=stored.get("client_email", ""),
        project_name=stored.get("project_name", ""),
        items=items,
        subtotal=subtotal,
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        grand_total=grand,
        invoice_date=stored.get("invoice_date", ""),
        due_date=stored.get("due_date", ""),
        payment_details=stored.get("payment_details", ""),
        notes=stored.get("notes", ""),
        file_path_pdf=pdf_path,
    )

    # Build preview
    lines = [
        f"Invoice #{stored['invoice_number']} Generated!\n",
        f"**Client:** {stored['client_name']}",
        f"**Project:** {stored.get('project_name','')}",
        f"**Date:** {stored.get('invoice_date','')} -- **Due:** {stored.get('due_date','')}\n",
        "| # | Work Item | Hours | Rate | Amount |",
        "|---|-----------|------:|-----:|-------:|",
    ]
    for i, it in enumerate(items, 1):
        lines.append(
            f"| {i} | {it.get('description','')} | {it.get('hours','')} "
            f"| ${it.get('rate','')} | ${it.get('amount',0):.2f} |"
        )
    lines.append(f"\n**Subtotal:** ${subtotal:.2f}")
    if tax_rate:
        lines.append(f"**Tax ({tax_rate}%):** ${tax_amount:.2f}")
    lines.append(f"**Grand Total: ${grand:.2f}**")
    lines.append("\n---\nUse the download button below to get the PDF.")

    session.pop("invoice_conv", None)
    session.pop("invoice_fields", None)
    return "\n".join(lines), iid, True
