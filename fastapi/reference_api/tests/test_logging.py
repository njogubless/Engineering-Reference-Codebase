import json
import logging

from app.core.logging import REDACTED, JsonFormatter, RequestContextFilter


def test_json_logs_redact_sensitive_extras():
    record = logging.makeLogRecord(
        {"name": "t", "levelname": "INFO", "msg": "login", "password": "x", "user_id": 3}
    )
    RequestContextFilter().filter(record)
    output = json.loads(JsonFormatter().format(record))
    assert output["password"] == REDACTED
    assert output["user_id"] == 3
    assert output["request_id"] == "-"
