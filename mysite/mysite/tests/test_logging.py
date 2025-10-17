from __future__ import annotations

import json
import logging

import pytest

from mysite import logging as project_logging
from mysite.audit import AuditEvent, log_audit_event
from mysite.logging import JsonLogFormatter, LoggingContextFilter


def test_json_formatter_includes_context():
    token = project_logging.push_context(request_id='req-123', user_id='42', custom='value')
    try:
        record = logging.LogRecord(
            name='test.logger',
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg='hello world',
            args=(),
            exc_info=None,
        )
        LoggingContextFilter(service_name='test-service', environment='test').filter(record)
        payload = json.loads(JsonLogFormatter().format(record))

        assert payload['message'] == 'hello world'
        assert payload['request_id'] == 'req-123'
        assert payload['user_id'] == '42'
        assert payload['context']['custom'] == 'value'
        assert payload['service'] == 'test-service'
        assert payload['environment'] == 'test'
    finally:
        project_logging.pop_context(token)


@pytest.mark.django_db
def test_request_context_middleware_sets_request_id(client):
    response = client.get('/health/?format=json')

    assert response.status_code in {200, 500, 503}
    request_id = response.headers.get('X-Request-ID')
    assert request_id
    assert len(request_id) >= 8  # UUID hex string


def test_log_audit_event_records_event(caplog):
    event = AuditEvent(
        action='user.test_event',
        actor_id='123',
        target_id='456',
        status='success',
        metadata={'example': 'value'},
    )

    audit_logger = logging.getLogger('mysite.audit')
    previous_propagate = audit_logger.propagate
    audit_logger.propagate = True
    try:
        with caplog.at_level(logging.INFO, logger='mysite.audit'):
            log_audit_event(event)
    finally:
        audit_logger.propagate = previous_propagate

    matching = [record for record in caplog.records if record.name == 'mysite.audit']
    assert matching, 'expected audit log record'
    record = matching[-1]
    assert record.event == 'audit.user.test_event'
    assert record.extra['action'] == 'user.test_event'
    assert record.extra['metadata']['example'] == 'value'
