import logging
from flask import Blueprint, request, jsonify, send_file, current_app
from .. import db
from ..database import Client, Project, Proposal, Invoice, Reminder
from datetime import datetime as dt
from ..llm_config import get_llm_config

api_bp = Blueprint('api', __name__, url_prefix='/api')
logger = logging.getLogger("freelancer-admin")

@api_bp.route("/proposals")
def api_proposals():
    rows = Proposal.query.order_by(Proposal.created_at.desc()).all()
    # Manual serialization to dict for JSON compatibility
    data = []
    for r in rows:
        data.append({
            "id": r.id,
            "client_name": r.client_name,
            "project_title": r.project_title,
            "budget": r.budget,
            "timeline": r.timeline,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else None,
            "file_path_pdf": r.file_path_pdf,
            "file_path_docx": r.file_path_docx
        })
    return jsonify(data)


@api_bp.route("/invoices")
def api_invoices():
    try:
        invs = Invoice.query.all()
        today = dt.now().strftime("%Y-%m-%d")
        data = []
        needs_commit = False
        
        for inv in invs:
            # Auto-detect overdue
            if (inv.status or "").upper() == "UNPAID" and (inv.due_date or "") < today:
                inv.status = "OVERDUE"
                needs_commit = True
            
            data.append({
                "id": inv.id,
                "invoice_number": str(inv.invoice_number or "N/A"),
                "client_name": str(inv.client_name or "N/A"),
                "client_email": str(inv.client_email or "N/A"),
                "project_name": str(inv.project_name or "N/A"),
                "grand_total": float(inv.grand_total or 0.0), # CRITICAL: Ensure serializable
                "due_date": str(inv.due_date or "N/A"),
                "status": str(inv.status or "UNPAID"),
                "file_path_pdf": str(inv.file_path_pdf or "")
            })
        
        if needs_commit:
            db.session.commit()
            
        return jsonify(data)
    except Exception as e:
        logger.error(f"API Invoices failure: {str(e)}")
        # Fallback to an empty list to prevent frontend crash
        return jsonify([])


@api_bp.route("/invoice/<int:iid>/mark-paid", methods=["POST"])
def mark_paid(iid):
    inv = Invoice.query.get(iid)
    if not inv:
        return jsonify({"ok": False, "error": "Invoice not found."}), 404
    inv.status = "PAID"
    db.session.commit()
    return jsonify({"ok": True, "message": f"Invoice #{inv.invoice_number} marked as PAID."})


@api_bp.route("/reminders")
def api_reminders():
    rows = Reminder.query.order_by(Reminder.created_at.desc()).all()
    data = []
    for r in rows:
        data.append({
            "id": r.id,
            "client_name": r.client_name,
            "invoice_number": r.invoice_number,
            "subject": r.subject,
            "reminder_message": r.reminder_message,
            "sent": r.sent,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else None
        })
    return jsonify(data)


@api_bp.route("/send-reminder/<inv_number>", methods=["POST"])
def api_send_reminder(inv_number):
    """Send a reminder email for a specific invoice directly."""
    from ..agents.reminder import send_email, _detect_tone, _generate_reminder
    oai, MODEL = get_llm_config()
    sender = current_app.config.get("GMAIL_SENDER")
    app_pass = current_app.config.get("GMAIL_APP_PASS")

    invoice = Invoice.query.filter_by(invoice_number=str(inv_number)).first()
    if not invoice:
        return jsonify({"ok": False, "error": f"Invoice #{inv_number} not found."}), 404

    email = invoice.client_email
    if not email:
        client = Client.query.filter_by(name=invoice.client_name).first()
        email = client.email if client else None
    
    if not email:
        return jsonify({"ok": False, "error": "No email address found for this client."}), 400

    try:
        due = dt.strptime(invoice.due_date, "%Y-%m-%d")
        days_overdue = max((dt.now() - due).days, 1)
    except Exception:
        days_overdue = 1

    tone = _detect_tone(days_overdue)

    try:
        # Convert model to dict for reminder agent
        inv_dict = {
            "client_name": invoice.client_name,
            "invoice_number": invoice.invoice_number,
            "due_date": invoice.due_date,
            "grand_total": invoice.grand_total
        }
        reminder = _generate_reminder(oai, inv_dict, tone, days_overdue, MODEL)
        send_email(sender or "", app_pass or "", email, reminder["subject"], reminder["body"])

        cid = Client.query.filter_by(name=invoice.client_name).first().id
        rem = Reminder(
            client_id=cid,
            invoice_id=invoice.id,
            invoice_number=invoice.invoice_number,
            client_name=invoice.client_name,
            reminder_message=reminder["body"],
            subject=reminder["subject"],
            sent=True
        )
        db.session.add(rem)
        db.session.commit()
        return jsonify({"ok": True, "message": f"Reminder sent to {email}!"})
    except Exception as e:
        logger.error(f"Failed to send direct reminder: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@api_bp.route("/download/proposal/<int:pid>/<fmt>")
def download_proposal(pid, fmt):
    prop = Proposal.query.get(pid)
    if not prop:
        return "Not found", 404
    if fmt == "pdf" and prop.file_path_pdf:
        return send_file(prop.file_path_pdf, as_attachment=True, download_name=f"proposal_{pid}.pdf")
    elif fmt == "docx" and prop.file_path_docx:
        return send_file(prop.file_path_docx, as_attachment=True, download_name=f"proposal_{pid}.docx")
    return "File not found", 404


@api_bp.route("/download/invoice/<int:iid>")
def download_invoice(iid):
    inv = Invoice.query.get(iid)
    if not inv:
        return "Not found", 404
    if inv.file_path_pdf:
        return send_file(inv.file_path_pdf, as_attachment=True,
                         download_name=f"invoice_{inv.invoice_number}.pdf")
    return "File not found", 404
