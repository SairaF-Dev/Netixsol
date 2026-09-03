from vapi_integration.metrics import MetricsRegistry


def test_metrics_snapshot_reports_counts_and_percentiles():
    registry = MetricsRegistry()
    registry.increment("booking_success", 2)
    for value in (10, 20, 30, 40, 50):
        registry.observe_ms("turn", value)
    result = registry.snapshot()
    assert result["counters"]["booking_success"] == 2
    assert result["latencies"]["turn"]["average_ms"] == 30
    assert result["latencies"]["turn"]["p95_ms"] == 50
