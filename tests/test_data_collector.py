import asyncio

from app.collectors.data_collector import DataCollector


class DummyResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return []


class DummyClient:
    def __init__(self):
        self.calls = []

    async def post(self, url, json=None, headers=None):
        self.calls.append({"url": url, "json": json, "headers": headers})
        return DummyResponse()


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
