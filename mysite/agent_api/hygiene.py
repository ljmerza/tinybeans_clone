"""Clean family-written text before it goes to an agent.

The agent API returns this text under an ``untrusted`` key: it may hold
instructions aimed at the model reading it. Cleaning can't make it safe;
it only strips characters that hide text and caps lengths.
"""

from __future__ import annotations

import re

TITLE_MAX = 300
CAPTION_MAX = 2000
MEDIA_CAPTION_MAX = 300
COMMENT_MAX = 300
TAG_MAX = 100
NAME_MAX = 150
LABEL_MAX = 80

# C0/C1 control characters except tab and newline, plus the bidi overrides and
# isolates that can make text read differently from what it says.
_HIDDEN_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]")


def strip_hidden(value) -> str:
    return _HIDDEN_RE.sub("", value or "")


class TextCleaner:
    """Cleans strings for one response item and remembers whether any was cut short."""

    def __init__(self):
        self.truncated = False

    def clean(self, value, limit: int) -> str:
        text = strip_hidden(value)
        if len(text) > limit:
            self.truncated = True
            text = text[:limit]
        return text


def mask_mentions(text: str, member_names) -> str:
    """Replace every ``@<member display name>`` with ``@member``, longest name first.

    The comment composer writes mentions as ``@Display Name`` (the email for
    members without a name); this keeps both out of the response.
    """
    names = sorted({name for name in member_names if name}, key=len, reverse=True)
    if not names or "@" not in text:
        return text
    pattern = re.compile("@(?:" + "|".join(re.escape(name) for name in names) + ")", re.IGNORECASE)
    return pattern.sub("@member", text)
