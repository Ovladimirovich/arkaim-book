"""Observability tests: structured logging format."""

import logging
from observability.logging import log_event, StructuredFormatter, setup_logger


class TestStructuredLogging:

    def test_log_event_format(self, caplog):
        caplog.set_level(logging.INFO)
        logger = logging.getLogger("test_structured")
        log_event(logger, "test_event", provider="gigachat", latency_ms=412, trace_id="abc123", intent="chat")
        assert "event=test_event" in caplog.text
        assert "provider=gigachat" in caplog.text
        assert "latency_ms=412" in caplog.text
        assert "trace_id=abc123" in caplog.text

    def test_log_event_float_format(self, caplog):
        caplog.set_level(logging.INFO)
        logger = logging.getLogger("test_float")
        log_event(logger, "latency", latency_ms=1234.5678)
        assert "latency_ms=1234.57" in caplog.text

    def test_log_event_skips_none(self, caplog):
        caplog.set_level(logging.INFO)
        logger = logging.getLogger("test_none")
        log_event(logger, "skip_test", provider=None, trace_id="t1")
        assert "provider=" not in caplog.text
        assert "trace_id=t1" in caplog.text

    def test_structured_formatter_has_timestamp(self):
        formatter = StructuredFormatter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "hello", (), None)
        output = formatter.format(record)
        assert " INFO " in output
        assert "test: hello" in output

    def test_setup_logger_creates_logger(self):
        logger = setup_logger("test_setup")
        assert logger.name == "test_setup"
        assert logger.level == logging.INFO
