import asyncio

import httpx

from web_api.services import AppointmentGateway


def test_gateway_returns_service_unavailable_on_connect_timeout(monkeypatch):
    async def timeout_request(self, *args, **kwargs):
        raise httpx.ConnectTimeout("appointment service is unreachable")

    monkeypatch.setattr(httpx.AsyncClient, "request", timeout_request)
    gateway = AppointmentGateway("http://day4.internal", "test-api-key")

    status, body = asyncio.run(gateway.request("POST", "/appointments", {}))

    assert status == 503
    assert body == {
        "detail": "Appointment scheduling service is temporarily unavailable"
    }
