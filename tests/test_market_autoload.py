from fastapi.testclient import TestClient

from app.cache.market_cache import market_cache
from app.main import app


client = TestClient(app)


def test_indicators_autoload_market_when_cache_is_empty(monkeypatch):
    symbol = "AUTOLOAD_IND"
    market_cache.candles.pop(symbol, None)
    market_cache.indicators.pop(symbol, None)

    async def fake_refresh(symbol="EURUSD"):
        import pandas as pd

        df = pd.DataFrame([{"timestamp": 1, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 0, "rsi_14": 50}])
        market_cache.set_candles(symbol, df)
        market_cache.set_indicators(symbol, df[["rsi_14"]])
        return {"status": "ok"}

    monkeypatch.setattr("app.routers.market.market_service.refresh_market", fake_refresh)

    response = client.get(f"/market/indicators?symbol={symbol}")

    assert response.status_code == 200
    assert response.json()["indicators"][0]["rsi_14"] == 50


def test_signals_autoload_market_when_cache_is_empty(monkeypatch):
    symbol = "AUTOLOAD_SIG"
    market_cache.candles.pop(symbol, None)

    async def fake_refresh(symbol="EURUSD"):
        import pandas as pd

        df = pd.DataFrame(
            [
                {
                    "timestamp": 1,
                    "open": 1,
                    "high": 1,
                    "low": 1,
                    "close": 1.23,
                    "volume": 0,
                    "ema_9": 2,
                    "ema_21": 1,
                    "sma_20": 1,
                    "rsi_14": 60,
                    "macd": 0.1,
                    "stoch_k": 70,
                    "stoch_d": 50,
                    "adx": 30,
                    "atr": 0.01,
                    "bb_upper": 1.5,
                    "bb_middle": 1.1,
                    "bb_lower": 0.9,
                    "body_percent": 70,
                    "wick_percent": 30,
                    "breakout": True,
                    "compression": False,
                    "doji": False,
                    "support": 1,
                    "resistance": 1.5,
                    "synthetic_volume": 1,
                    "market_activity_score": 1,
                }
            ]
        )
        market_cache.set_candles(symbol, df)
        return {"status": "ok"}

    monkeypatch.setattr("app.routers.market.market_service.refresh_market", fake_refresh)

    response = client.get(f"/market/signals?symbol={symbol}")

    assert response.status_code == 200
    signal = response.json()["signals"][0]
    assert signal["action"] == "CALL"
    assert signal["entryPrice"] == 1.23
