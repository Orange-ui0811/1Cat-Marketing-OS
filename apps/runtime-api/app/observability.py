"""OpenTelemetry bootstrap and small, stable runtime metric surface."""

from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": os.getenv("OTEL_SERVICE_NAME", "1cat-runtime"),
        }
        for field in (
            "correlation_id", "run_id", "attempt_id", "hermes_run_id", "tool_call_id", "worker_id",
            "case_id", "stage_key", "status", "outcome", "operation", "failure_count", "retry_seconds",
        ):
            value = getattr(record, field, None)
            if value:
                payload[field] = value
        try:
            from opentelemetry import trace

            context = trace.get_current_span().get_span_context()
            if context.is_valid:
                payload["trace_id"] = format(context.trace_id, "032x")
                payload["span_id"] = format(context.span_id, "016x")
        except ImportError:
            pass
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_json_logging() -> None:
    root = logging.getLogger()
    root.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.handlers[:] = [handler]


class RuntimeMetrics:
    def __init__(self) -> None:
        self.run_created = None
        self.run_terminal = None
        self.run_duration = None
        self.claim_delay = None
        self.heartbeat_lag = None
        self.lease_expired = None
        self.recovery = None
        self.mcp_calls = None
        self.queue_depth = None
        self.queue_age = None
        self.database_unavailable = None
        self.case_created = None
        self.case_completed = None
        self.case_blocked = None
        self.case_stage_duration = None
        self.case_command_rejected = None
        self.case_active = None

    @staticmethod
    def add(instrument, amount: int = 1, **attributes: str) -> None:
        if instrument is not None:
            instrument.add(amount, attributes)

    @staticmethod
    def record(instrument, value: float, **attributes: str) -> None:
        if instrument is not None:
            instrument.record(value, attributes)


metrics = RuntimeMetrics()
_configured = False


def configure_observability(*, service_name: str, app=None, engine=None) -> bool:
    """Configure OTLP only when an endpoint is present; local tests remain deterministic."""
    global _configured
    configure_json_logging()
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").rstrip("/")
    if not endpoint or _configured:
        return False
    from opentelemetry import metrics as otel_metrics, trace
    from opentelemetry.metrics import Observation
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create({"service.name": service_name, "service.namespace": "1cat"})
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")))
    trace.set_tracer_provider(tracer_provider)
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics"), export_interval_millis=5000,
    )
    otel_metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))

    HTTPXClientInstrumentor().instrument()
    if engine is not None:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        SQLAlchemyInstrumentor().instrument(engine=engine)
    if app is not None:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)

    meter = otel_metrics.get_meter("onecat.runtime")
    metrics.run_created = meter.create_counter("onecat.run.created", description="Created Agent Runs")
    metrics.run_terminal = meter.create_counter("onecat.run.terminal", description="Terminal Run outcomes")
    metrics.run_duration = meter.create_histogram("onecat.run.duration", unit="s")
    metrics.claim_delay = meter.create_histogram("onecat.run.claim.delay", unit="s")
    metrics.heartbeat_lag = meter.create_histogram("onecat.run.heartbeat.lag", unit="s")
    metrics.lease_expired = meter.create_counter("onecat.lease.expired")
    metrics.recovery = meter.create_counter("onecat.run.recovery")
    metrics.database_unavailable = meter.create_counter(
        "onecat.worker.database.unavailable",
        description="Worker database operations that failed while the coordinator database was unavailable",
    )
    metrics.mcp_calls = meter.create_counter("onecat.mcp.call")
    metrics.case_created = meter.create_counter("onecat.marketing.case.created")
    metrics.case_completed = meter.create_counter("onecat.marketing.case.completed")
    metrics.case_blocked = meter.create_counter("onecat.marketing.case.blocked")
    metrics.case_stage_duration = meter.create_histogram("onecat.marketing.stage.duration", unit="s")
    metrics.case_command_rejected = meter.create_counter("onecat.marketing.command.rejected")
    if engine is not None and service_name == "1cat-runtime-api":
        def queue_snapshot() -> tuple[int, float]:
            from sqlalchemy import text

            with engine.connect() as connection:
                depth = int(connection.execute(text(
                    "SELECT COUNT(*) FROM collaboration_agent_runs WHERE status = 'queued'"
                )).scalar_one())
                if not depth:
                    return 0, 0.0
                if connection.dialect.name == "postgresql":
                    age = connection.execute(text(
                        "SELECT COALESCE(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - MIN(created_at))), 0) "
                        "FROM collaboration_agent_runs WHERE status = 'queued'"
                    )).scalar_one()
                else:
                    age = connection.execute(text(
                        "SELECT COALESCE((julianday('now') - julianday(MIN(created_at))) * 86400, 0) "
                        "FROM collaboration_agent_runs WHERE status = 'queued'"
                    )).scalar_one()
                return depth, max(0.0, float(age or 0.0))

        def observe_queue_depth(_options):
            try:
                depth, _ = queue_snapshot()
                return [Observation(depth)]
            except Exception:
                logging.getLogger("1cat.runtime.metrics").exception("queue depth observation failed")
                return []

        def observe_queue_age(_options):
            try:
                _, age = queue_snapshot()
                return [Observation(age)]
            except Exception:
                logging.getLogger("1cat.runtime.metrics").exception("queue age observation failed")
                return []

        metrics.queue_depth = meter.create_observable_gauge(
            "onecat.run.queue.depth",
            callbacks=[observe_queue_depth],
            description="Current queued Agent Runs",
        )
        metrics.queue_age = meter.create_observable_gauge(
            "onecat.run.queue.age",
            callbacks=[observe_queue_age],
            unit="s",
            description="Age of the oldest queued Agent Run",
        )
        def observe_active_cases(_options):
            try:
                from sqlalchemy import text

                with engine.connect() as connection:
                    count = int(connection.execute(text(
                        "SELECT COUNT(*) FROM marketing_cases "
                        "WHERE status IN ('active','running','awaiting_human','blocked')"
                    )).scalar_one())
                return [Observation(count)]
            except Exception:
                return []

        metrics.case_active = meter.create_observable_gauge(
            "onecat.marketing.case.active",
            callbacks=[observe_active_cases],
            description="Current non-terminal Marketing Cases",
        )
    _configured = True
    return True


def current_trace_headers() -> tuple[str | None, str | None]:
    try:
        from opentelemetry.propagate import inject

        carrier: dict[str, str] = {}
        inject(carrier)
        return carrier.get("traceparent"), carrier.get("tracestate")
    except ImportError:
        return None, None


@contextmanager
def attempt_span(run, attempt):
    """Restore the API trace context when a Worker consumes a persisted Run."""
    try:
        from opentelemetry import trace
        from opentelemetry.propagate import extract

        carrier = {key: value for key, value in {
            "traceparent": run.traceparent, "tracestate": run.tracestate,
        }.items() if value}
        parent = extract(carrier)
        tracer = trace.get_tracer("onecat.runtime.worker")
        with tracer.start_as_current_span(
            "agent.run.attempt",
            context=parent,
            attributes={
                "onecat.run.id": run.id,
                "onecat.attempt.id": attempt.id,
                "onecat.worker.id": attempt.worker_id,
                "onecat.profile.id": run.profile_id,
                "onecat.case.id": run.case_id or "",
                "onecat.stage.key": run.stage_key or "",
                "onecat.execution.mode": run.execution_mode or "legacy",
            },
        ):
            yield
    except ImportError:
        yield
