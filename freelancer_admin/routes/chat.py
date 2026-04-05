import logging
from flask import Blueprint, request, jsonify, render_template, current_app
from ..agents import classify_intent, handle_proposal, handle_invoice, handle_reminder
from .. import database as db
from ..llm_config import get_llm_config

chat_bp = Blueprint('chat', __name__)
logger = logging.getLogger("freelancer-admin")

# In-memory session store (keyed by session_id sent from frontend)
sessions: dict[str, dict] = {}

def _session(sid: str) -> dict:
    if sid not in sessions:
        sessions[sid] = {"intent": None}
    return sessions[sid]

@chat_bp.route("/")
def index():
    return render_template("index.html")

@chat_bp.route("/api/reset", methods=["POST"])
def reset_session():
    data = request.get_json(force=True)
    sid = data.get("session_id", "default")
    if sid in sessions:
        del sessions[sid]
    return jsonify({"ok": True, "message": "Session reset."})

@chat_bp.route("/api/chat", methods=["POST"])
def chat():
    # Initialize the LLM client once for the request
    oai, MODEL = get_llm_config()
    
    data = request.get_json(force=True)
    msg = (data.get("message") or "").strip()
    sid = data.get("session_id", "default")
    if not msg:
        return jsonify({"reply": "Please type a message.", "type": "text"})

    sess = _session(sid)
    current_intent = sess.get("intent")
    lang = data.get("language", "English")
    sess["language"] = lang

    # If no active flow, classify intent
    if not current_intent:
        number_map = {"1": "PROPOSAL", "2": "INVOICE", "3": "REMINDER", "4": "QUERY"}
        shortcut_intent = number_map.get(msg.strip(), None)
        if shortcut_intent:
            intent = shortcut_intent
            msg_map = {
                "1": "I want to create a proposal",
                "2": "I want to create an invoice",
                "3": "I want to send a payment reminder",
                "4": "Show me my invoices",
            }
            msg = msg_map.get(msg.strip(), msg)
        else:
            intent = classify_intent(oai, msg, MODEL)
        
        if intent in ("PROPOSAL", "INVOICE", "REMINDER"):
            sess["intent"] = intent
            current_intent = intent
        elif intent == "QUERY":
            reply = _handle_query(msg, lang)
            return jsonify({"reply": reply, "type": "text"})
        else:
            reply = _handle_general(oai, MODEL, msg, lang)
            return jsonify({"reply": reply, "type": "text"})

    # Dispatch to agent
    if current_intent == "PROPOSAL":
        reply, pid, done = handle_proposal(oai, sess, msg, MODEL)
        rtype = "proposal" if done else "text"
        resp = {"reply": reply, "type": rtype}
        if done and pid:
            resp["proposal_id"] = pid
            sess["intent"] = None
        return jsonify(resp)

    elif current_intent == "INVOICE":
        reply, iid, done = handle_invoice(oai, sess, msg, MODEL)
        rtype = "invoice" if done else "text"
        resp = {"reply": reply, "type": rtype}
        if done and iid:
            resp["invoice_id"] = iid
            sess["intent"] = None
        return jsonify(resp)

    elif current_intent == "REMINDER":
        sender = current_app.config.get("GMAIL_SENDER")
        app_pass = current_app.config.get("GMAIL_APP_PASS")
        reply, draft, needs_confirm = handle_reminder(
            oai, sess, msg, sender or "", app_pass or "", MODEL
        )
        rtype = "reminder" if needs_confirm else "text"
        resp = {"reply": reply, "type": rtype}
        if not needs_confirm and not draft:
            sess["intent"] = None
        return jsonify(resp)

    # Fallback
    return jsonify({"reply": _handle_general(oai, MODEL, msg, lang), "type": "text"})

def _handle_query(msg: str, lang: str = "English") -> str:
    lower = msg.lower()
    if "unpaid" in lower:
        invs = db.get_invoices_by_status("UNPAID")
    elif "paid" in lower and "unpaid" not in lower:
        invs = db.get_invoices_by_status("PAID")
    elif "overdue" in lower:
        invs = db.get_invoices_by_status("OVERDUE")
    else:
        invs = db.get_invoices_by_status()

    if not invs:
        no_inv_msg = {"English": "No invoices found matching your query.",
                      "Hindi": "आपकी क्वेरी से मेल खाने वाला कोई इनवॉइस नहीं मिला।"}
        return no_inv_msg.get(lang, no_inv_msg["English"])

    header_msg = {"English": "Here are the invoices I found:\n",
                  "Hindi": "ये रहे मिले हुए इनवॉइस:\n"}
    lines = [header_msg.get(lang, header_msg["English"]),
             "| # | Client | Project | Amount | Due | Status |",
             "|---|--------|---------|-------:|-----|--------|"]
    for inv in invs:
        lines.append(
            f"| {inv['invoice_number']} | {inv['client_name']} | "
            f"{inv['project_name']} | ${inv['grand_total']:.2f} | "
            f"{inv.get('due_date','N/A')} | {inv['status']} |"
        )
    return "\n".join(lines)

def _handle_general(oai, model, msg: str, lang: str = "English") -> str:
    lang_instruction = ""
    if lang != "English":
        lang_instruction = f" You MUST respond in {lang} language."

    resp = oai.chat.completions.create(
        model=model, temperature=0.7, max_tokens=300,
        messages=[
            {"role": "system", "content": (
                "You are a friendly freelancer admin assistant chatbot for Hallucination Hunters. "
                "You help freelancers create proposals, invoices, and payment reminders. "
                "Keep responses concise." + lang_instruction
            )},
            {"role": "user", "content": msg},
        ],
    )
    return resp.choices[0].message.content.strip()
