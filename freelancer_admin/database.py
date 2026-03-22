"""SQLAlchemy database layer for the Freelancer Admin Chatbot."""

from datetime import datetime
import json
from . import db

# ── Models ──────────────────────────────────────────────────────────

class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    company = db.Column(db.String(100))
    contact_details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    projects = db.relationship('Project', backref='client', lazy=True)
    proposals = db.relationship('Proposal', backref='client', lazy=True)
    invoices = db.relationship('Invoice', backref='client', lazy=True)
    reminders = db.relationship('Reminder', backref='client', lazy=True)

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Proposal(db.Model):
    __tablename__ = 'proposals'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    client_name = db.Column(db.String(100))
    project_title = db.Column(db.String(200))
    proposal_text = db.Column(db.Text)
    deliverables = db.Column(db.Text)
    timeline = db.Column(db.String(100))
    budget = db.Column(db.String(100))
    freelancer_name = db.Column(db.String(100))
    freelancer_skills = db.Column(db.Text)
    file_path_pdf = db.Column(db.String(255))
    file_path_docx = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    client_name = db.Column(db.String(100))
    client_email = db.Column(db.String(120))
    project_name = db.Column(db.String(200))
    items_json = db.Column(db.Text)  # Store as JSON string
    subtotal = db.Column(db.Float, default=0.0)
    tax_rate = db.Column(db.Float, default=0.0)
    tax_amount = db.Column(db.Float, default=0.0)
    grand_total = db.Column(db.Float, default=0.0)
    invoice_date = db.Column(db.String(50))
    due_date = db.Column(db.String(50))
    payment_details = db.Column(db.Text)
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='UNPAID')
    file_path_pdf = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def items(self):
        return json.loads(self.items_json) if self.items_json else []
    
    @items.setter
    def items(self, value):
        self.items_json = json.dumps(value)

class Reminder(db.Model):
    __tablename__ = 'reminders'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'))
    invoice_number = db.Column(db.String(50))
    client_name = db.Column(db.String(100))
    reminder_message = db.Column(db.Text)
    subject = db.Column(db.String(200))
    sent = db.Column(db.Integer, default=0)
    date_sent = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ── Initialization ──────────────────────────────────────────────────

def init_db():
    # In production, we'd use Flask-Migrate, but for local simple init:
    db.create_all()

# ── Client helpers ──────────────────────────────────────────────────

def get_or_create_client(name, email=None, company=None):
    client = Client.query.filter(db.func.lower(Client.name) == db.func.lower(name)).first()
    if client:
        if email and not client.email:
            client.email = email
            db.session.commit()
        return client.id
    
    new_client = Client(name=name, email=email, company=company)
    db.session.add(new_client)
    db.session.commit()
    return new_client.id

def get_client_by_name(name):
    client = Client.query.filter(db.func.lower(Client.name) == db.func.lower(name)).first()
    if client:
        return {
            "id": client.id,
            "name": client.name,
            "email": client.email,
            "company": client.company,
            "contact_details": client.contact_details
        }
    return None

# ── Proposal helpers ────────────────────────────────────────────────

def save_proposal(client_id, client_name, project_title, proposal_text,
                  deliverables="", timeline="", budget="",
                  freelancer_name="", freelancer_skills="",
                  file_path_pdf=None, file_path_docx=None):
    proposal = Proposal(
        client_id=client_id,
        client_name=client_name,
        project_title=project_title,
        proposal_text=proposal_text,
        deliverables=deliverables,
        timeline=timeline,
        budget=budget,
        freelancer_name=freelancer_name,
        freelancer_skills=freelancer_skills,
        file_path_pdf=file_path_pdf,
        file_path_docx=file_path_docx
    )
    db.session.add(proposal)
    db.session.commit()
    return proposal.id

def get_proposal(proposal_id):
    p = Proposal.query.get(proposal_id)
    if p:
        return {
            "id": p.id,
            "client_id": p.client_id,
            "client_name": p.client_name,
            "project_title": p.project_title,
            "proposal_text": p.proposal_text,
            "deliverables": p.deliverables,
            "timeline": p.timeline,
            "budget": p.budget,
            "freelancer_name": p.freelancer_name,
            "freelancer_skills": p.freelancer_skills,
            "file_path_pdf": p.file_path_pdf,
            "file_path_docx": p.file_path_docx
        }
    return None

# ── Invoice helpers ─────────────────────────────────────────────────

def next_invoice_number():
    max_inv = db.session.query(db.func.max(db.cast(Invoice.invoice_number, db.Integer))).scalar()
    if max_inv is None:
        return "1001"
    return str(max_inv + 1)

def save_invoice(invoice_number, client_id, client_name, project_name,
                 items, subtotal, tax_rate, tax_amount, grand_total,
                 invoice_date, due_date, payment_details="", notes="",
                 file_path_pdf=None, client_email=""):
    invoice = Invoice(
        invoice_number=invoice_number,
        client_id=client_id,
        client_name=client_name,
        client_email=client_email,
        project_name=project_name,
        subtotal=subtotal,
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        grand_total=grand_total,
        invoice_date=invoice_date,
        due_date=due_date,
        payment_details=payment_details,
        notes=notes,
        file_path_pdf=file_path_pdf
    )
    invoice.items = items
    db.session.add(invoice)
    db.session.commit()
    return invoice.id

def get_invoice_by_number(number):
    inv = Invoice.query.filter_by(invoice_number=str(number)).first()
    if inv:
        return {
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "client_id": inv.client_id,
            "client_name": inv.client_name,
            "client_email": inv.client_email,
            "project_name": inv.project_name,
            "items": inv.items,
            "subtotal": inv.subtotal,
            "tax_rate": inv.tax_rate,
            "tax_amount": inv.tax_amount,
            "grand_total": inv.grand_total,
            "invoice_date": inv.invoice_date,
            "due_date": inv.due_date,
            "payment_details": inv.payment_details,
            "notes": inv.notes,
            "status": inv.status,
            "file_path_pdf": inv.file_path_pdf
        }
    return None

def get_invoices_by_status(status=None):
    if status:
        query = Invoice.query.filter(db.func.upper(Invoice.status) == status.upper())
    else:
        query = Invoice.query.order_by(Invoice.created_at.desc())
    
    results = query.all()
    out = []
    for inv in results:
        out.append({
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "client_name": inv.client_name,
            "project_name": inv.project_name,
            "grand_total": inv.grand_total,
            "status": inv.status,
            "created_at": inv.created_at.isoformat() if inv.created_at else None
        })
    return out

def update_invoice_status(invoice_number, status):
    inv = Invoice.query.filter_by(invoice_number=str(invoice_number)).first()
    if inv:
        inv.status = status
        db.session.commit()

# ── Reminder helpers ────────────────────────────────────────────────

def save_reminder(client_id, invoice_id, invoice_number, client_name,
                  reminder_message, subject, sent=False):
    reminder = Reminder(
        client_id=client_id,
        invoice_id=invoice_id,
        invoice_number=invoice_number,
        client_name=client_name,
        reminder_message=reminder_message,
        subject=subject,
        sent=1 if sent else 0,
        date_sent=datetime.utcnow() if sent else None
    )
    db.session.add(reminder)
    db.session.commit()
