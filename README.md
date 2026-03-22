---
title: Freelancer Admin Bot
emoji: 💼
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: true
---

# Freelancer Admin Automation Bot

This is a production-ready AI agent designed to help freelancers manage their business. 
Generated and deployed via **Antigravity AI**.

## 🚀 Features
- **Project Proposal Generation** (PDF/DOCX)
- **Invoice Creation** (Automated calculations)
- **Payment Reminders** (Tone-aware email drafts)
- **Client & Project CRM** (SQLite + SQLAlchemy)

## 🛠️ Tech Stack
- **Backend**: Flask + SQLAlchemy
- **AI**: Google Gemini 1.5 Flash (via OpenAI API)
- **Production**: Gunicorn + Docker
- **Email**: Gmail SMTP Integration

## 📦 Local Setup
1. Clone this repo.
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in your keys.
4. `python run.py`
