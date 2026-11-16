"""Prometheus metrics exporter for the Platform Operations Automation Engine."""

import logging
import time
from typing import Optional
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
    start_http_server,
)

logger = logging.getLogger("operations_engine.reporting.metrics")

_GLOBAL_EXPORTER: Optional["MetricsExporter"] = None


class MetricsExporter:
    """Manages SRE telemetry counters, histograms, and HTTP scrape endpoints."""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()

        self.checks_total = Counter(
            "automation_checks_total",
            "Total number of automated operations and health checks executed",
            ["check_type", "status"],
            registry=self.registry,
        )

        self.failures_total = Counter(
            "automation_failures_total",
            "Total number of pod and service failures detected",
            ["service", "failure_type"],
            registry=self.registry,
        )

        self.rollbacks_total = Counter(
            "deployment_rollbacks_total",
            "Total number of deployment rollback operations attempted or simulated",
            ["deployment", "status"],
            registry=self.registry,
        )

        self.execution_seconds = Histogram(
            "automation_execution_seconds",
            "Time spent executing automation and diagnostic operations in seconds",
            ["operation"],
            registry=self.registry,
        )

    def record_check(self, check_type: str, success: bool = True):
        status = "success" if success else "failure"
        self.checks_total.labels(check_type=check_type, status=status).inc()

    def record_failure(self, service: str, failure_type: str):
        self.failures_total.labels(service=service, failure_type=failure_type).inc()

    def record_rollback(self, deployment: str, status: str = "success"):
        self.rollbacks_total.labels(deployment=deployment, status=status).inc()

    def observe_duration(self, operation: str, seconds: float):
        self.execution_seconds.labels(operation=operation).observe(seconds)

    def track_duration(self, operation: str):
        """Context manager to observe execution duration."""
        return _DurationContext(self, operation)

    def get_metrics_text(self) -> str:
        """Serializes current metrics to Prometheus text format."""
        return generate_latest(self.registry).decode("utf-8")

    def start_server(self, port: int = 9102):
        """Starts background HTTP server for Prometheus scraping."""
        try:
            start_http_server(port, registry=self.registry)
            logger.info(f"Prometheus metrics HTTP server listening on port {port}")
        except Exception as e:
            logger.error(f"Failed to start Prometheus metrics HTTP server: {e}")
            raise


class _DurationContext:
    def __init__(self, exporter: MetricsExporter, operation: str):
        self.exporter = exporter
        self.operation = operation
        self.start = 0.0

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start
        self.exporter.observe_duration(self.operation, duration)


def get_metrics_exporter(registry: Optional[CollectorRegistry] = None) -> MetricsExporter:
    global _GLOBAL_EXPORTER
    if _GLOBAL_EXPORTER is None or registry is not None:
        _GLOBAL_EXPORTER = MetricsExporter(registry=registry)
    return _GLOBAL_EXPORTER
