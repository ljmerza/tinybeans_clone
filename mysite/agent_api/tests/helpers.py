"""Builders shared by the agent API tests."""

import logging
from contextlib import contextmanager

from rest_framework.test import APIClient

from mysite.agent_api import services
from mysite.keeps.models import KeepPerson, Person
from mysite.users.models import ChildProfile


def create_token(circle, user, **kwargs):
    kwargs.setdefault("name", "Laptop")
    kwargs.setdefault("can_suggest", False)
    kwargs.setdefault("expires_at", None)
    return services.create_token(circle_id=circle.id, user=user, **kwargs)


def bearer_client(raw):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}")
    return client


def make_child(circle, name="Sophia", birthdate=None):
    child = ChildProfile.objects.create(circle=circle, display_name=name, birthdate=birthdate)
    person, _ = Person.objects.get_or_create(circle=circle, child=child, defaults={"name": name})
    return child, person


def tag(keep, person):
    KeepPerson.objects.get_or_create(keep=keep, person=person)


@contextmanager
def captured_logs(caplog, *names):
    """Capture records from loggers that don't propagate outside tests (``mysite.audit``, ``django.request``)."""
    loggers = [logging.getLogger(name) for name in names]
    previous = [logger.propagate for logger in loggers]
    for logger in loggers:
        logger.propagate = True
    try:
        with caplog.at_level(logging.DEBUG):
            yield caplog
    finally:
        for logger, value in zip(loggers, previous, strict=True):
            logger.propagate = value


def audit_actions(caplog):
    return [record.extra["action"] for record in caplog.records if record.name == "mysite.audit"]
