import asyncio
import json
import math
import time
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Query
from fastapi.responses import ORJSONResponse, StreamingResponse

from app.cache.market_cache import market_cache
from app.collectors.data_collector import collector
from app.services.market_service import market_service
from app.services.signal_service import signal_service
from app.services.analysis_service import analysis_service
from app.services.backtest_service import backtest_service
from app.services.storage_service import storage_service

router = APIRouter(prefix="/market", tags=["market"])


async def _refresh_market(symbol: str, timeframe: int) -> Dict[str, Any]:
    # Calling M1 with the legacy signature also keeps integrations that monkeypatch
    # or wrap refresh_market(symbol) working.
    if timeframe == 60:
        return await market_service.refresh_market(symbol=symbol)
    return await market_service.refresh_market(symbol=symbol, timeframe=timeframe)


@router.get("/assets", response_class=ORJSONResponse)
async def get_assets():
    return {"assets": await collector.get_assets()}


@router.get("/candles", response_class=ORJSONResponse)
async def get_candles(symbol: str = Query(default="EURUSD"), timeframe: int = Query(default=60, ge=5, le=86400)):
    await _refresh_market(symbol, timeframe)
    df = market_cache.get_candles(symbol, timeframe)
    if df is None:
        return {"candles": []}
    return {"candles": _safe_json_value(df.tail(20).to_dict(orient="records"))}


def _safe_json_value(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "item"):
        try:
            return _safe_json_value(value.item())
        except Exception:
            pass
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, dict):
        return {key: _safe_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_safe_json_value(item) for item in value]
    return value


def _latest_tick(ticks: List[Dict[str, Any]], symbol: str) -> Optional[Dict[str, Any]]:
    for tick in reversed(ticks):
        if not isinstance(tick, dict):
            continue
        asset = tick.get("asset") or tick.get("symbol")
        price = tick.get("price") or tick.get("close")
        if (asset in {None, symbol}) and isinstance(price, (int, float)):
            return tick
    return None


def _tick_timestamp(tick: Dict[str, Any]) -> int:
    raw_timestamp = tick.get("timestamp") or tick.get("time")
    if isinstance(raw_timestamp, (int, float)):
        return int(raw_timestamp)
    return int(time.time())


def _update_stream_candle(symbol: str, tick: Dict[str, Any], timeframe: int) -> Dict[str, Any]:
    price = float(tick.get("price") or tick.get("close"))
    tick_timestamp = _tick_timestamp(tick)
    candle_timestamp = tick_timestamp - (tick_timestamp % timeframe)
    df = market_cache.get_candles(symbol, timeframe)

    if df is None or df.empty:
        df = pd.DataFrame(
            [
                {
                    "asset": symbol,
                    "timeframe": timeframe,
                    "timestamp": candle_timestamp,
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                    "volume": 1.0,
                }
            ]
        )
    else:
        df = df.copy()
        if "asset" not in df.columns:
            df["asset"] = symbol
        if "timeframe" not in df.columns:
            df["timeframe"] = timeframe
        df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
        last_index = df.index[-1]
        last_timestamp = int(df.loc[last_index, "timestamp"])
        if last_timestamp == candle_timestamp:
            df.loc[last_index, "asset"] = symbol
            df.loc[last_index, "timeframe"] = timeframe
            df.loc[last_index, "high"] = max(float(df.loc[last_index, "high"]), price)
            df.loc[last_index, "low"] = min(float(df.loc[last_index, "low"]), price)
            df.loc[last_index, "close"] = price
            df.loc[last_index, "volume"] = float(df.loc[last_index].get("volume", 0.0) or 0.0) + 1.0
        elif candle_timestamp > last_timestamp:
            df = pd.concat(
                [
                    df,
                    pd.DataFrame(
                        [
                            {
                                "asset": symbol,
                                "timeframe": timeframe,
                                "timestamp": candle_timestamp,
                                "open": price,
                                "high": price,
                                "low": price,
                                "close": price,
                                "volume": 1.0,
                            }
                        ]
                    ),
                ],
                ignore_index=True,
            )

    market_cache.set_candles(symbol, df.tail(500).reset_index(drop=True), timeframe)
    candle = market_cache.get_candles(symbol, timeframe).iloc[-1].to_dict()
    return _safe_json_value(candle)


def _stream_candles_payload(df: Optional[pd.DataFrame]) -> List[Dict[str, Any]]:
    if df is None or df.empty:
        return []
    columns = [column for column in ["asset", "timeframe", "timestamp", "open", "high", "low", "close", "volume"] if column in df.columns]
    return _safe_json_value(df.tail(40)[columns].to_dict(orient="records"))


def _stream_candle_payload(candle: Dict[str, Any]) -> Dict[str, Any]:
    keys = ["asset", "timeframe", "timestamp", "open", "high", "low", "close", "volume"]
    return _safe_json_value({key: candle.get(key) for key in keys if key in candle})


def _sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(_safe_json_value(data), ensure_ascii=False)}\n\n"


@router.get("/candles/stream")
async def stream_candles(
    symbol: str = Query(default="EURUSD"),
    timeframe: int = Query(default=60, ge=1, le=3600),
    interval: float = Query(default=1.0, ge=0.2, le=10.0),
):
    async def events():
        try:
            if market_cache.get_candles(symbol, timeframe) is None:
                await _refresh_market(symbol, timeframe)
            yield _sse(
                "ready",
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "interval": interval,
                    "message": "streaming started",
                },
            )
            while True:
                ticks = await collector.get_ticks(symbol)
                market_cache.set_ticks(symbol, ticks)
                tick = _latest_tick(ticks, symbol)
                if tick is not None:
                    candle = _update_stream_candle(symbol, tick, timeframe)
                    raw_df = market_cache.get_candles(symbol, timeframe)
                    df = market_service.process_dataframe(symbol, timeframe, raw_df) if raw_df is not None else raw_df
                    signal = signal_service.build_signal(symbol, timeframe)
                    market_cache.set_signal(symbol, signal, timeframe)
                    yield _sse(
                        "candle",
                        {
                            "symbol": symbol,
                            "timeframe": timeframe,
                            "tick": tick,
                            "candle": _stream_candle_payload(candle),
                            "candles": _stream_candles_payload(df),
                            "signal": signal,
                            "serverTime": int(time.time()),
                        },
                    )
                else:
                    yield _sse("heartbeat", {"symbol": symbol, "serverTime": int(time.time())})
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            return

    return StreamingResponse(events(), media_type="text/event-stream")


@router.get("/ticks", response_class=ORJSONResponse)
async def get_ticks(symbol: str = Query(default="EURUSD")):
    ticks = await collector.get_ticks(symbol)
    market_cache.set_ticks(symbol, ticks)
    return {"ticks": ticks}


@router.get("/indicators", response_class=ORJSONResponse)
async def get_indicators(symbol: str = Query(default="EURUSD"), timeframe: int = Query(default=60, ge=5, le=86400)):
    indicators = market_cache.get_indicators(symbol, timeframe)
    if indicators is None or indicators.empty:
        await _refresh_market(symbol, timeframe)
        indicators = market_cache.get_indicators(symbol, timeframe)
    if indicators is None or indicators.empty:
        return {"indicators": []}
    return {"indicators": _safe_json_value(indicators.tail(5).to_dict(orient="records"))}


@router.get("/features", response_class=ORJSONResponse)
async def get_features(symbol: str = Query(default="EURUSD"), timeframe: int = Query(default=60, ge=5, le=86400)):
    if market_cache.get_candles(symbol, timeframe) is None:
        await _refresh_market(symbol, timeframe)
    return {"features": _safe_json_value(market_cache.get_features(symbol, timeframe))}


@router.get("/market-structure", response_class=ORJSONResponse)
async def get_market_structure(symbol: str = Query(default="EURUSD"), timeframe: int = Query(default=60, ge=5, le=86400)):
    if market_cache.get_candles(symbol, timeframe) is None:
        await _refresh_market(symbol, timeframe)
    return {"marketStructure": _safe_json_value(market_cache.get_structures(symbol, timeframe))}


@router.get("/price-action", response_class=ORJSONResponse)
async def get_price_action(symbol: str = Query(default="EURUSD"), timeframe: int = Query(default=60, ge=5, le=86400)):
    df = await _ensure_market(symbol, timeframe)
    return {"priceAction": _safe_json_value(analysis_service.price_action(df, symbol, timeframe))}


@router.get("/signals", response_class=ORJSONResponse)
async def get_signals(symbol: str = Query(default="EURUSD"), timeframe: int = Query(default=60, ge=5, le=86400)):
    df = market_cache.get_candles(symbol, timeframe)
    if df is None or df.empty:
        await _refresh_market(symbol, timeframe)
        df = market_cache.get_candles(symbol, timeframe)
    signal = signal_service.build_signal(symbol, timeframe)
    market_cache.set_signal(symbol, signal, timeframe)
    if df is not None and not df.empty:
        storage_service.save_signal(signal, timeframe, int(df.iloc[-1]["timestamp"]))
    return {"signals": [_safe_json_value(signal)]}


@router.get("/statistics", response_class=ORJSONResponse)
async def get_statistics(symbol: Optional[str] = Query(default=None), timeframe: Optional[int] = Query(default=None, ge=5, le=86400)):
    return {"statistics": storage_service.statistics(symbol, timeframe)}


@router.get("/activity", response_class=ORJSONResponse)
async def get_activity(symbol: str = Query(default="EURUSD"), timeframe: int = Query(default=60, ge=5, le=86400)):
    df = market_cache.get_candles(symbol, timeframe)
    if df is None or df.empty:
        await _refresh_market(symbol, timeframe)
        df = market_cache.get_candles(symbol, timeframe)
    if df is None or df.empty:
        return {"activity": {}}
    latest = df.iloc[-1]
    return {
        "activity": _safe_json_value(
            {
                "syntheticVolume": float(latest.get("synthetic_volume", 0.0) or 0.0),
                "activityScore": float(latest.get("market_activity_score", 0.0) or 0.0),
            }
        )
    }


@router.get("/dashboard", response_class=ORJSONResponse)
async def get_dashboard(symbol: str = Query(default="EURUSD"), timeframe: int = Query(default=60, ge=5, le=86400)):
    df = market_cache.get_candles(symbol, timeframe)
    if df is None or df.empty:
        await _refresh_market(symbol, timeframe)
    return {"dashboard": _safe_json_value(market_service.get_latest_snapshot(symbol, timeframe))}


@router.get("/cache", response_class=ORJSONResponse)
async def get_cache():
    return {"cache": market_cache.snapshot()}


@router.get("/history", response_class=ORJSONResponse)
async def get_history(symbol: str = Query(default="EURUSD"), timeframe: int = Query(default=60, ge=5, le=86400)):
    df = market_cache.get_candles(symbol, timeframe)
    if df is None or df.empty:
        await _refresh_market(symbol, timeframe)
        df = market_cache.get_candles(symbol, timeframe)
    if df is None or df.empty:
        return {"history": []}
    return {"history": _safe_json_value(df.tail(10).to_dict(orient="records"))}


@router.get("/trend", response_class=ORJSONResponse)
async def get_trend(symbol: str = Query(default="EURUSD"), timeframe: int = Query(default=60, ge=5, le=86400)):
    df = await _ensure_market(symbol, timeframe)
    return {"trend": _safe_json_value(analysis_service.trend(df, symbol, timeframe))}


@router.get("/volatility", response_class=ORJSONResponse)
async def get_volatility(symbol: str = Query(default="EURUSD"), timeframe: int = Query(default=60, ge=5, le=86400)):
    df = await _ensure_market(symbol, timeframe)
    return {"volatility": _safe_json_value(analysis_service.volatility(df, symbol, timeframe))}


@router.get("/momentum", response_class=ORJSONResponse)
async def get_momentum(symbol: str = Query(default="EURUSD"), timeframe: int = Query(default=60, ge=5, le=86400)):
    df = await _ensure_market(symbol, timeframe)
    return {"momentum": _safe_json_value(analysis_service.momentum(df, symbol, timeframe))}


@router.get("/confluence", response_class=ORJSONResponse)
async def get_confluence(symbol: str = Query(default="EURUSD"), timeframe: int = Query(default=60, ge=5, le=86400)):
    df = await _ensure_market(symbol, timeframe)
    signal = signal_service.build_signal(symbol, timeframe)
    return {"confluence": _safe_json_value(analysis_service.confluence(df, symbol, timeframe, signal))}


@router.get("/order-blocks", response_class=ORJSONResponse)
async def get_order_blocks(symbol: str = Query(default="EURUSD"), timeframe: int = Query(default=60, ge=5, le=86400)):
    df = await _ensure_market(symbol, timeframe)
    return {"orderBlocks": _safe_json_value(analysis_service.order_blocks(df, symbol, timeframe))}


@router.get("/liquidity", response_class=ORJSONResponse)
async def get_liquidity(symbol: str = Query(default="EURUSD"), timeframe: int = Query(default=60, ge=5, le=86400)):
    df = await _ensure_market(symbol, timeframe)
    return {"liquidity": _safe_json_value(analysis_service.liquidity(df, symbol, timeframe))}


@router.get("/support-resistance", response_class=ORJSONResponse)
async def get_support_resistance(symbol: str = Query(default="EURUSD"), timeframe: int = Query(default=60, ge=5, le=86400)):
    df = await _ensure_market(symbol, timeframe)
    return {"supportResistance": _safe_json_value(analysis_service.support_resistance(df, symbol, timeframe))}


async def _ensure_market(symbol: str, timeframe: int) -> pd.DataFrame:
    df = market_cache.get_candles(symbol, timeframe)
    if df is None or df.empty:
        await _refresh_market(symbol, timeframe)
        df = market_cache.get_candles(symbol, timeframe)
    return df if df is not None else pd.DataFrame()


@router.get("/signal-history", response_class=ORJSONResponse)
async def get_signal_history(symbol: Optional[str] = Query(default=None), timeframe: Optional[int] = Query(default=None, ge=5, le=86400), limit: int = Query(default=100, ge=1, le=1000)):
    return {"history": storage_service.signal_history(symbol, timeframe, limit)}


@router.get("/backtest", response_class=ORJSONResponse)
async def get_backtest(symbol: str = Query(default="EURUSD"), timeframe: int = Query(default=60, ge=5, le=86400), warmup: int = Query(default=40, ge=20, le=300)):
    df = await _ensure_market(symbol, timeframe)
    return {"backtest": _safe_json_value(backtest_service.run(df, symbol, timeframe, warmup))}


@router.get("/health", response_class=ORJSONResponse)
async def get_market_health():
    return {"status": "ok", "market": "ready"}
