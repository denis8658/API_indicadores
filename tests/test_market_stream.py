from app.cache.market_cache import market_cache
from app.routers.market import _update_stream_candle


def test_stream_tick_updates_current_candle():
    symbol = "TEST_STREAM"
    market_cache.candles.pop(symbol, None)

    first = _update_stream_candle(symbol, {"asset": symbol, "price": 10.0, "timestamp": 120}, 60)
    second = _update_stream_candle(symbol, {"asset": symbol, "price": 12.0, "timestamp": 130}, 60)

    assert first["timestamp"] == 120
    assert second["timestamp"] == 120
    assert second["open"] == 10.0
    assert second["high"] == 12.0
    assert second["low"] == 10.0
    assert second["close"] == 12.0


def test_stream_tick_creates_next_candle():
    symbol = "TEST_STREAM_NEXT"
    market_cache.candles.pop(symbol, None)

    _update_stream_candle(symbol, {"asset": symbol, "price": 10.0, "timestamp": 120}, 60)
    candle = _update_stream_candle(symbol, {"asset": symbol, "price": 11.0, "timestamp": 180}, 60)

    df = market_cache.get_candles(symbol)
    assert len(df) == 2
    assert candle["timestamp"] == 180
    assert candle["open"] == 11.0
    assert candle["close"] == 11.0
