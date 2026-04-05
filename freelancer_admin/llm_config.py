"""LLM Configuration with automatic multi-key rotation for Gemini free tier."""

import os
import time
import logging
from openai import OpenAI
from dotenv import load_dotenv

logger = logging.getLogger("freelancer-admin")

# Load .env file automatically
pkg_dir = os.path.dirname(os.path.abspath(__file__))
r_dir = os.path.dirname(pkg_dir)
load_dotenv(os.path.join(r_dir, ".env"))

# ── Multi-Key Rotation State ────────────────────────────────────────
_gemini_keys = []
_current_key_index = 0


def _load_gemini_keys():
    """Load all available Gemini API keys from environment.
    Supports GEMINI_API_KEY, GEMINI_API_KEY_2, GEMINI_API_KEY_3, etc.
    """
    global _gemini_keys
    keys = []
    
    # Primary key
    primary = os.environ.get("GEMINI_API_KEY")
    if primary:
        keys.append(primary)
    
    # Additional rotation keys
    for i in range(2, 10):
        key = os.environ.get(f"GEMINI_API_KEY_{i}")
        if key:
            keys.append(key)
    
    _gemini_keys = keys
    if len(keys) > 1:
        logger.info(f"Loaded {len(keys)} Gemini API keys for rotation.")
    return keys


def _get_next_gemini_key():
    """Rotate to the next available Gemini API key."""
    global _current_key_index
    
    if not _gemini_keys:
        _load_gemini_keys()
    
    if not _gemini_keys:
        return os.environ.get("GEMINI_API_KEY", "")
    
    key = _gemini_keys[_current_key_index % len(_gemini_keys)]
    _current_key_index = (_current_key_index + 1) % len(_gemini_keys)
    return key


def get_llm_config():
    """Returns (client, model_name).
    Loads configuration from environment variables (powered by .env).
    Supports automatic key rotation for Gemini free tier.
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

    # If explicitly forcing Gemini / Gemma (via Google AI OpenAI-compatible API)
    elif os.environ.get("USE_GEMINI") == "true":
        model = os.environ.get("GEMINI_MODEL", "gemma-4-31b-it")
        api_key = _get_next_gemini_key()
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"

    client = OpenAI(base_url=base_url, api_key=api_key)
    return client, model


def safe_llm_call(func, *args, max_retries=3, **kwargs):
    """Wrapper that retries LLM calls with key rotation on rate limits.
    
    Usage:
        result = safe_llm_call(
            oai.chat.completions.create,
            model=MODEL, messages=[...], max_tokens=300
        )
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_str = str(e)
            last_error = e
            
            # Rate limit or quota exceeded — rotate key and retry
            if "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower():
                logger.warning(f"Rate limited (attempt {attempt + 1}/{max_retries}). Rotating key...")
                
                # Get a fresh client with a new key
                if os.environ.get("USE_GEMINI") == "true" and len(_gemini_keys) > 1:
                    new_key = _get_next_gemini_key()
                    new_client = OpenAI(
                        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                        api_key=new_key
                    )
                    # Update the client in the function's bound arguments
                    if hasattr(func, '__self__'):
                        # For bound methods like oai.chat.completions.create
                        # We need to retry with a new client
                        model = os.environ.get("GEMINI_MODEL", "gemma-4-31b-it")
                        try:
                            return new_client.chat.completions.create(*args, **kwargs)
                        except Exception:
                            pass
                
                # Wait before retry (exponential backoff)
                wait_time = min(2 ** attempt * 5, 30)
                logger.info(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                # Non-rate-limit error, don't retry
                raise e
    
    # All retries exhausted
    raise last_error
