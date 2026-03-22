import logging
from flask import Blueprint, request, jsonify, send_file, current_app
from .. import database as db
from datetime import datetime as dt
from ..llm_config import get_llm_config

api_bp = Blueprint('api', __name__, url_prefix='/api')
logger = logging.getLogger("freelancer-admin")

@api_bp.route("/proposals")
def api_proposals():
    from ..database import get_conn
    conn = get_conn()
    rows = conn.execute("SELECT * FROM proposals ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@api_bp.route("/invoices")
def api_invoices():
    invs = db.get_invoices_by_status()
    today = dt.now().strftime("%Y-%m-%d")
    # Auto-detect overdue: if status is UNPAID and due_date < today
    for inv in invs:
        if inv.get("status", "").upper() == "UNPAID" and inv.get("due_date", "") < today:
            inv["status"] = "OVERDUE"
            # Update in the database
            from ..database import get_conn
            conn = get_conn()
            conn.execute("UPDATE invoices SET status='OVERDUE' WHERE id=?", (inv["id"],))
            conn.commit()
            conn.close()
    return jsonify(invs)


@api_bp.route("/invoice/<int:iid>/mark-paid", methods=["POST"])
def mark_paid(iid):
    from ..database import get_conn
    conn = get_conn()
    row = conn.execute("SELECT * FROM invoices WHERE id=?", (iid,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Invoice not found."}), 404
    conn.execute("UPDATE invoices SET status='PAID' WHERE id=?", (iid,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "message": f"Invoice #{row['invoice_number']} marked as PAID."})


@api_bp.route("/reminders")
def api_reminders():
    from ..database import get_conn
    conn = get_conn()
    rows = conn.execute("SELECT * FROM reminders ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@api_bp.route("/send-reminder/<inv_number>", methods=["POST"])
def api_send_reminder(inv_number):
    """Send a reminder email for a specific invoice directly."""
    from ..agents.reminder import send_email, _detect_tone, _generate_reminder
    oai, MODEL = get_llm_config()
    sender = current_app.config.get("GMAIL_SENDER")
    app_pass = current_app.config.get("GMAIL_APP_PASS")

    invoice = db.get_invoice_by_number(str(inv_number))
    if not invoice:
        return jsonify({"ok": False, "error": f"Invoice #{inv_number} not found."}), 404

    email = invoice.get("client_email")
    if not email:
        client = db.get_client_by_name(invoice["client_name"])
        email = client.get("email") if client else None
    if not email:
        return jsonify({"ok": False, "error": "No email address found for this client."}), 400

    try:
        due = dt.strptime(invoice["due_date"], "%Y-%m-%d")
        days_overdue = max((dt.now() - due).days, 1)
    except Exception:
        days_overdue = 1

    tone = _detect_tone(days_overdue)

    try:
        reminder = _generate_reminder(oai, invoice, tone, days_overdue, MODEL)
        send_email(sender or "", app_pass or "", email, reminder["subject"], reminder["body"])

        cid = db.get_or_create_client(invoice["client_name"])
        db.save_reminder(
            client_id=cid,
            invoice_id=invoice["id"],
            invoice_number=invoice["invoice_number"],
            client_name=invoice["client_name"],
            reminder_message=reminder["body"],
            subject=reminder["subject"],
            sent=True,
        )
        return jsonify({"ok": True, "message": f"Reminder sent to {email}!"})
    except Exception as e:
        logger.error(f"Failed to send direct reminder: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@api_bp.route("/download/proposal/<int:pid>/<fmt>")
def download_proposal(pid, fmt):
    prop = db.get_proposal(pid)
    if not prop:
        return "Not found", 404
    if fmt == "pdf" and prop.get("file_path_pdf"):
        return send_file(prop["file_path_pdf"], as_attachment=True, download_name=f"proposal_{pid}.pdf")
    elif fmt == "docx" and prop.get("file_path_docx"):
        return send_file(prop["file_path_docx"], as_attachment=True, download_name=f"proposal_{pid}.docx")
    return "File not found", 404


@api_bp.route("/download/invoice/<int:iid>")
def download_invoice(iid):
    from ..database import get_conn
    conn = get_conn()
    row = conn.execute("SELECT * FROM invoices WHERE id=?", (iid,)).fetchone()
    conn.close()
    if not row:
        return "Not found", 404
    if row["file_path_pdf"]:
        return send_file(row["file_path_pdf"], as_attachment=True,
                         download_name=f"invoice_{row['invoice_number']}.pdf")
    return "File not found", 404
