import os
import json
from datetime import datetime, timedelta
from freelancer_admin import create_app, db
from freelancer_admin.database import Client, Project, Proposal, Invoice, Reminder

app = create_app()

def seed_data():
    with app.app_context():
        # Clear existing data if necessary (optional)
        # db.drop_all()
        # db.create_all()

        print("Seeding sample data...")

        # 1. TechCorp Solutions
        c1 = Client(name="TechCorp Solutions", email="billing@techcorp.com", company="TechCorp", contact_details="San Francisco, CA")
        db.session.add(c1)
        db.session.flush()

        p1 = Project(client_id=c1.id, name="E-commerce Migration", description="Migrating legacy store to Shopify")
        db.session.add(p1)
        db.session.flush()

        prop1 = Proposal(client_id=c1.id, project_id=p1.id, client_name=c1.name, project_title=p1.name, 
                         proposal_text="Comprehensive migration plan including SEO preservation.", 
                         budget="$5,000", freelancer_name="Shubham Kumar")
        db.session.add(prop1)

        inv1 = Invoice(invoice_number="INV-1001", client_id=c1.id, client_name=c1.name, client_email=c1.email, 
                       project_name=p1.name, subtotal=5000.0, tax_rate=0.08, tax_amount=400.0, grand_total=5400.0,
                       status="PAID", invoice_date="2026-03-01", due_date="2026-03-15")
        inv1.items = [{"desc": "Migration Service", "qty": 1, "price": 5000.0}]
        db.session.add(inv1)

        # 2. Creative Agency LLC
        c2 = Client(name="Creative Agency LLC", email="hello@creativeagency.io", company="Creative Agency", contact_details="New York, NY")
        db.session.add(c2)
        db.session.flush()

        p2 = Project(client_id=c2.id, name="Brand Identity Redesign", description="New logo and brand guidelines")
        db.session.add(p2)
        db.session.flush()

        inv2 = Invoice(invoice_number="INV-1002", client_id=c2.id, client_name=c2.name, client_email=c2.email, 
                       project_name=p2.name, subtotal=2500.0, grand_total=2500.0,
                       status="UNPAID", invoice_date="2026-03-10", due_date="2026-04-10")
        inv2.items = [{"desc": "Logo Design", "qty": 1, "price": 1500.0}, {"desc": "Brand Guide", "qty": 1, "price": 1000.0}]
        db.session.add(inv2)

        # 3. HealthFirst Health
        c3 = Client(name="HealthFirst", email="apps@healthfirst.org", company="HealthFirst")
        db.session.add(c3)
        db.session.flush()

        inv3 = Invoice(invoice_number="INV-1003", client_id=c3.id, client_name=c3.name, client_email=c3.email, 
                       project_name="Mobile App Consultation", subtotal=1200.0, grand_total=1200.0,
                       status="OVERDUE", invoice_date="2026-02-15", due_date="2026-03-01")
        inv3.items = [{"desc": "UX Workshop", "qty": 1, "price": 1200.0}]
        db.session.add(inv3)

        # 4. Global Logistics
        c4 = Client(name="Global Logistics", email="pete@globallogistics.com")
        db.session.add(c4)
        db.session.flush()

        inv4 = Invoice(invoice_number="INV-1004", client_id=c4.id, client_name=c4.name, client_email=c4.email, 
                       project_name="Dashboard Development", subtotal=4500.0, grand_total=4500.0,
                       status="UNPAID", invoice_date="2026-03-18", due_date="2026-03-25")
        inv4.items = [{"desc": "Core Dashboard", "qty": 1, "price": 4500.0}]
        db.session.add(inv4)

        # 5. Startup Ventures
        c5 = Client(name="Startup Ventures", email="founder@startupventures.com", contact_details="Remote")
        db.session.add(c5)
        db.session.flush()

        inv5 = Invoice(invoice_number="INV-1005", client_id=c5.id, client_name=c5.name, client_email=c5.email, 
                       project_name="Landing Page", subtotal=800.0, grand_total=800.0,
                       status="PAID", invoice_date="2026-01-20", due_date="2026-01-27")
        inv5.items = [{"desc": "Landing Page Design", "qty": 1, "price": 800.0}]
        db.session.add(inv5)

        db.session.commit()
        print("Successfully seeded 5 clients and 5 invoices!")

if __name__ == "__main__":
    seed_data()
