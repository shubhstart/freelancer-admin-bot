"""LLM-based intent detection for the Freelancer Admin Chatbot."""

from openai import OpenAI

INTENT_SYSTEM = """You are an intent classifier for a freelancer assistant chatbot for Hallucination Hunters.
Given the user's message, reply with EXACTLY ONE of these labels (nothing else):

PROPOSAL    – user wants to create a new project proposal
INVOICE     – user wants to create a new invoice
REMINDER    – user wants to send a payment reminder email
QUERY       – user asks to see invoices, status, clients, or data
GENERAL     – greeting, general questions, or chat

CRITICAL: Return ONLY THE LABEL. Do not explain your choice. If unsure, return GENERAL."""


def classify_intent(client: OpenAI, message: str, model: str = "gpt-4o-mini") -> str:
    """Return one of: PROPOSAL, INVOICE, REMINDER, QUERY, GENERAL."""
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=0,
            max_tokens=10,
            messages=[
                {"role": "system", "content": INTENT_SYSTEM},
                {"role": "user", "content": message},
            ],
        )
        label = resp.choices[0].message.content.strip().upper()
        if label in ("PROPOSAL", "INVOICE", "REMINDER", "QUERY", "GENERAL"):
            return label
        return "GENERAL"
    except Exception:
        return "GENERAL"
