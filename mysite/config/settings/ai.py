"""In-app AI (milestone suggestions): the one OpenAI-compatible endpoint the server operator set up.

Circle admins only turn the feature on or off; they never see or set the URL,
key or model. Empty ``AI_BASE_URL`` or ``AI_MODEL`` turns it off everywhere.

Only raw values are read here and nothing raises: the Tinybeans sync service
imports these settings under its own env. ``mysite.ai.providers`` checks them
when they are used and treats a bad value as "AI off".
"""

import os


def _ai_positive_int(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name) or default)
    except ValueError:
        return default
    return value if value > 0 else default


# e.g. http://192.168.1.76:11434/v1 (local Ollama). http only without a key.
AI_BASE_URL = os.environ.get("AI_BASE_URL", "").strip()
# Sent as a bearer token; empty for local Ollama. Never stored in the database.
AI_API_KEY = os.environ.get("AI_API_KEY", "").strip()
AI_MODEL = os.environ.get("AI_MODEL", "").strip()
# Most model calls per circle per scan.
AI_MAX_CALLS_PER_RUN = _ai_positive_int("AI_MAX_CALLS_PER_RUN", 200)
AI_REQUEST_TIMEOUT_SECONDS = _ai_positive_int("AI_REQUEST_TIMEOUT_SECONDS", 120)
# Title and caption are cut to this many characters before they're sent.
AI_MAX_CAPTION_CHARS = _ai_positive_int("AI_MAX_CAPTION_CHARS", 1500)
