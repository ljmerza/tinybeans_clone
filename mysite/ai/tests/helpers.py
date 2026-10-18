"""Builders shared by the in-app AI tests."""

import json
from unittest.mock import Mock

from mysite.ai.models import CircleAiSettings
from mysite.albums.models import MilestoneAlbum
from mysite.albums.tests.helpers import make_album

BASE_URL = "http://ai.test:11434/v1"
MODEL = "qwen3:14b"


def chat_response(content, status_code=200, finish_reason="stop"):
    """A fake ``requests`` response carrying ``content`` as the model's answer (a dict is JSON-encoded)."""
    if isinstance(content, dict):
        content = json.dumps(content)
    response = Mock(status_code=status_code)
    response.json.return_value = {
        "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": finish_reason}]
    }
    return response


def status_response(status_code, body=None):
    response = Mock(status_code=status_code)
    response.json.return_value = body or {}
    return response


def verdict(is_milestone=True, label="First steps", reason="The caption describes first steps."):
    return chat_response({"is_milestone": is_milestone, "label": label, "reason": reason})


def turn_on(circle, user=None):
    ai_settings, _ = CircleAiSettings.objects.get_or_create(circle=circle)
    ai_settings.enabled = True
    ai_settings.acknowledged_by = user
    ai_settings.save()
    return ai_settings


def sent_posts(post_mock):
    """The ``<post>`` user message of every call made through ``post_mock``."""
    return [call.kwargs["json"]["messages"][-1]["content"] for call in post_mock.call_args_list]


def link_milestones_album(circle, user, *keeps):
    album = make_album(circle, user, name="Milestones", keeps=keeps)
    MilestoneAlbum.objects.create(circle=circle, album=album)
    return album
