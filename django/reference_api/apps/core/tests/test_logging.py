import json
import logging

from apps.core.logging import REDACTED, JsonFormatter, RequestContextFilter, redact
from apps.core.request_context import request_id_var


def make_record(**extra) -> logging.LogRecord:
    record = logging.makeLogRecord({"name": "test", "levelname": "INFO", "msg": "event", **extra})
    RequestContextFilter().filter(record)
    return record


def test_json_output_has_core_fields_and_extras():
    token = request_id_var.set("rid-1")
    try:
        output = json.loads(JsonFormatter().format(make_record(order_id=7)))
    finally:
        request_id_var.reset(token)
    assert output["message"] == "event"
    assert output["request_id"] == "rid-1"
    assert output["order_id"] == 7
    assert output["timestamp"].endswith("+00:00")


def test_sensitive_extras_are_redacted_recursively():
    output = json.loads(
        JsonFormatter().format(
            make_record(password="hunter2", payload={"user": "a", "refresh_token": "t"})
        )
    )
    assert output["password"] == REDACTED
    assert output["payload"] == {"user": "a", "refresh_token": REDACTED}


def test_request_id_placeholder_outside_requests():
    assert json.loads(JsonFormatter().format(make_record()))["request_id"] == "-"


def test_unserialisable_values_do_not_break_logging():
    output = json.loads(JsonFormatter().format(make_record(obj=object())))
    assert output["obj"].startswith("<object object")


def test_redact_handles_lists():
    assert redact([{"api_key": "k"}, "plain"]) == [{"api_key": REDACTED}, "plain"]


def test_exceptions_are_included():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        record = make_record(exc_info=sys.exc_info())
    assert "ValueError: boom" in json.loads(JsonFormatter().format(record))["exception"]
