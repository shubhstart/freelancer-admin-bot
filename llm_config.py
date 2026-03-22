import os
from openai import OpenAI
from dotenv import load_dotenv

# Load .env file automatically
root = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(root, ".env"))

def get_llm_config():
    """Returns (client, model_name).
    Loads configuration from environment variables (powered by .env).
    """
    # Defaults for local development (Ollama)
    base_url = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
    model = os.environ.get("LLM_MODEL", "llama3.2")
    api_key = os.environ.get("LLM_API_KEY", "ollama")

    # If explicitly forcing OpenAI
    if os.environ.get("USE_OPENAI") == "true":
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        api_key = os.environ.get("OPENAI_API_KEY")
        base_url = "https://api.openai.com/v1"

    client = OpenAI(base_url=base_url, api_key=api_key)
    return client, model

