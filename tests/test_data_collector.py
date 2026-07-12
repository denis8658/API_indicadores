import asyncio

from app.collectors.data_collector import DataCollector


class DummyResponse:
    def __init__(self, data=None):
        self.data = [] if data is None else data

    def raise_for_status(self):
        return None

    def json(self):
        return self.data


class DummyClient:
    def __init__(self):
        self.calls = []

    async def post(self, url, json=None, headers=None):
        self.calls.append({"url": url, "json": json, "headers": headers})
        return DummyResponse()

    async def get(self, url, headers=None):
        self.calls.append({"url": url, "headers": headers})
        return DummyResponse({"connected": True, "client_initialized": True})


def test_get_candles_uses_upstream_payload_shape():
    collector = DataCollector()
    collector.connected = True
    collector.client = DummyClient()

    asyncio.run(collector.get_candles("EURUSD", 3))

    assert len(collector.client.calls) == 1
    payload = collector.client.calls[0]["json"]
    assert payload["asset"] == "EURUSD"
    assert payload["timeframe"] == 60
    assert payload["count"] == 3


def test_connect_without_ssid_reuses_initialized_upstream():
    collector = DataCollector()
    collector.raw_ssid = None
    collector.ssid = None
    collector.client = DummyClient()

    data = asyncio.run(collector.connect())

    assert collector.connected is True
    assert data["connected"] is True
    assert len(collector.client.calls) == 1
    assert collector.client.calls[0]["url"].endswith("/health")
