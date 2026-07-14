import pandas as pd
from fastapi.testclient import TestClient

from app.cache.market_cache import MarketCache
from app.indicators.indicator_engine import IndicatorEngine
from app.market_structure.market_structure_engine import MarketStructureEngine
from app.price_action.price_action_engine import PriceActionEngine
from app.services.analysis_service import AnalysisService
from app.services.storage_service import StorageService
from app.main import app
from app.services.market_service import market_service


def test_bollinger_aliases_keep_lower_middle_upper_order():
    index = pd.RangeIndex(30)
    close = pd.Series([100 + index * 0.1 for index in range(30)], dtype=float)
    df = pd.DataFrame({"open": close - 0.1, "high": close + 1, "low": close - 1, "close": close, "volume": 1.0}, index=index)

    result = IndicatorEngine()._apply_compatibility_aliases(df)

    assert result.iloc[-1]["bb_lower"] < result.iloc[-1]["bb_middle"] < result.iloc[-1]["bb_upper"]
    assert pd.notna(result.iloc[-1]["sar"])


def test_market_structure_detects_breakout_and_dynamic_levels():
    close = [10, 10.2, 10.1, 10.3, 10.2, 10.4, 10.3, 10.5, 10.4, 10.6, 12.0]
    df = pd.DataFrame({"timestamp": range(len(close)), "open": close, "high": [value + 0.1 for value in close], "low": [value - 0.1 for value in close], "close": close, "volume": 1})

    result = MarketStructureEngine().update(df)

    assert result.iloc[-1]["bos"] == "bullish"
    assert result.iloc[-1]["market_structure"] == "bullish"
    assert result.iloc[-1]["resistance"] < result.iloc[-1]["close"]


def test_price_action_detects_engulfing_and_real_breakout():
    rows = []
    for index in range(22):
        rows.append({"open": 10.0, "high": 10.5, "low": 9.5, "close": 10.1})
    rows[-2] = {"open": 10.3, "high": 10.4, "low": 9.8, "close": 9.9}
    rows[-1] = {"open": 9.8, "high": 11.2, "low": 9.7, "close": 11.0}

    result = PriceActionEngine().update(pd.DataFrame(rows))

    assert bool(result.iloc[-1]["bullish_engulfing"])
    assert bool(result.iloc[-1]["breakout_up"])


def test_timeframes_are_isolated_in_cache():
    cache = MarketCache()
    cache.set_candles("EURUSD", pd.DataFrame({"close": [1]}), 60)
    cache.set_candles("EURUSD", pd.DataFrame({"close": [5]}), 300)

    assert cache.get_candles("EURUSD", 60).iloc[-1]["close"] == 1
    assert cache.get_candles("EURUSD", 300).iloc[-1]["close"] == 5


def test_signal_persistence_evaluates_result_and_statistics(tmp_path):
    storage = StorageService(str(tmp_path / "market.db"))
    signal = {"symbol": "EURUSD", "action": "CALL", "entryPrice": 1.0, "score": 50, "confidence": 0.5, "expiration": 60}
    storage.save_signal(signal, 60, 60)
    candles = pd.DataFrame([{"timestamp": 120, "close": 1.1}])

    assert storage.evaluate_pending("EURUSD", 60, candles) == 1
    statistics = storage.statistics("EURUSD", 60)
    assert statistics["wins"] == 1
    assert statistics["accuracy"] == 1.0


def test_analysis_service_returns_non_placeholder_payloads():
    df = pd.DataFrame([{"timestamp": 1, "open": 1.0, "high": 1.2, "low": 0.9, "close": 1.1, "ema_9": 1.08, "ema_21": 1.02, "rsi_14": 60, "macd": 0.1, "stoch_k": 65, "stoch_d": 45, "adx": 30, "atr": 0.02, "bb_upper": 1.2, "bb_lower": 1.0}])
    service = AnalysisService()

    assert service.trend(df, "EURUSD", 60)["direction"] == "bullish"
    assert service.momentum(df, "EURUSD", 60)["direction"] == "bullish"
    assert service.volatility(df, "EURUSD", 60)["regime"] in {"normal", "high"}


def test_analysis_endpoints_return_calculated_payloads_for_timeframe():
    symbol, timeframe = "ANALYSIS_ENDPOINT", 300
    rows = []
    for index in range(80):
        close = 100 + index * 0.05 + ((index % 5) - 2) * 0.1
        rows.append({"timestamp": index * timeframe, "open": close - 0.05, "high": close + 0.2, "low": close - 0.2, "close": close, "volume": index % 7 + 1})
    market_service.process_dataframe(symbol, timeframe, pd.DataFrame(rows))
    client = TestClient(app)

    expected = {
        "trend": "trend",
        "momentum": "momentum",
        "volatility": "volatility",
        "confluence": "confluence",
        "price-action": "priceAction",
        "order-blocks": "orderBlocks",
        "liquidity": "liquidity",
        "support-resistance": "supportResistance",
    }
    for endpoint, key in expected.items():
        response = client.get(f"/market/{endpoint}?symbol={symbol}&timeframe={timeframe}")
        assert response.status_code == 200
        assert key in response.json()
    assert client.get(f"/market/trend?symbol={symbol}&timeframe={timeframe}").json()["trend"]["timeframe"] == timeframe
