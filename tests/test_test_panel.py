from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_test_panel_page_loads():
    response = client.get("/test-panel")

    assert response.status_code == 200
    assert "Painel de Testes da API" in response.text


def test_usage_panel_page_loads():
    response = client.get("/usage-panel")

    assert response.status_code == 200
    assert "Painel de Uso da API" in response.text


def test_test_panel_results_requires_json_shape(monkeypatch):
    async def fake_run_check(client, check):
        return {
            "group": check.group,
            "name": check.name,
            "method": check.method,
            "url": check.url,
            "status_code": 200,
            "elapsed_ms": 1,
            "passed": True,
            "expected": check.expected,
            "detail": "mock",
            "summary": "mock",
        }

    monkeypatch.setattr("app.routers.panel.run_check", fake_run_check)
    monkeypatch.setattr("app.routers.panel.settings.pocket_ssid", "mock-ssid")

    response = client.get("/test-panel/results?asset=USDJPY_otc")

    assert response.status_code == 200
    payload = response.json()
    assert payload["asset"] == "USDJPY_otc"
    assert payload["summary"]["failed"] == 0
    assert payload["results"]


def test_usage_panel_data_shape(monkeypatch):
    class FakeResponse:
        def __init__(self, payload):
            self.status_code = 200
            self._payload = payload

        def json(self):
            return self._payload

    async def fake_get(self, url, *args, **kwargs):
        payloads = {
            "/market/assets": {"assets": [{"symbol": "USDJPY_otc", "name": "USDJPY OTC"}]},
            "/market/candles?symbol=USDJPY_otc": {
                "candles": [{"timestamp": 1, "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 0}]
            },
            "/market/ticks?symbol=USDJPY_otc": {"ticks": [{"asset": "USDJPY_otc", "price": 1.5, "source": "mock"}]},
            "/market/indicators?symbol=USDJPY_otc": {"indicators": [{"rsi_14": 55}]},
            "/market/features?symbol=USDJPY_otc": {"features": {}},
            "/market/market-structure?symbol=USDJPY_otc": {"marketStructure": {}},
            "/market/signals?symbol=USDJPY_otc": {"signals": [{"action": "CALL", "score": 1}]},
            "/market/statistics": {"statistics": {"wins": 1}},
            "/market/activity?symbol=USDJPY_otc": {"activity": {"activityScore": 1}},
            "/market/dashboard?symbol=USDJPY_otc": {"dashboard": {"status": "ok"}},
            "/market/history?symbol=USDJPY_otc": {"history": []},
            "/market/trend?symbol=USDJPY_otc": {"trend": {"status": "ready"}},
            "/market/volatility?symbol=USDJPY_otc": {"volatility": {"status": "ready"}},
            "/market/momentum?symbol=USDJPY_otc": {"momentum": {"status": "ready"}},
            "/market/confluence?symbol=USDJPY_otc": {"confluence": {"status": "ready"}},
            "/market/order-blocks": {"orderBlocks": []},
            "/market/liquidity": {"liquidity": []},
            "/market/support-resistance": {"supportResistance": []},
            "/market/health": {"status": "ok", "market": "ready"},
        }
        return FakeResponse(payloads[url])

    monkeypatch.setattr("httpx.AsyncClient.get", fake_get)

    response = client.get("/usage-panel/data?asset=USDJPY_otc")

    assert response.status_code == 200
    payload = response.json()
    assert payload["asset"] == "USDJPY_otc"
    assert payload["latest"]["price"] == 1.5
    assert payload["latest"]["signal"]["action"] == "CALL"
