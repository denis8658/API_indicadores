from fastapi import APIRouter, Query
from fastapi.responses import ORJSONResponse

from app.cache.market_cache import market_cache
from app.services.market_service import market_service
from app.services.signal_service import signal_service

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/assets", response_class=ORJSONResponse)
async def get_assets():
    return {"assets": [{"symbol": "EURUSD", "name": "EUR/USD"}]}


@router.get("/candles", response_class=ORJSONResponse)
async def get_candles(symbol: str = Query(default="EURUSD")):
    await market_service.refresh_market(symbol=symbol)
    df = market_cache.get_candles(symbol)
    if df is None:
        return {"candles": []}
    return {"candles": df.tail(20).to_dict(orient="records")}


@router.get("/ticks", response_class=ORJSONResponse)
async def get_ticks(symbol: str = Query(default="EURUSD")):
    return {"ticks": market_cache.get_ticks(symbol)}


@router.get("/indicators", response_class=ORJSONResponse)
async def get_indicators(symbol: str = Query(default="EURUSD")):
    indicators = market_cache.get_indicators(symbol)
    if indicators is None:
        return {"indicators": []}
    return {"indicators": indicators.tail(5).to_dict(orient="records")}


@router.get("/features", response_class=ORJSONResponse)
async def get_features(symbol: str = Query(default="EURUSD")):
    return {"features": market_cache.get_features(symbol)}


@router.get("/market-structure", response_class=ORJSONResponse)
async def get_market_structure(symbol: str = Query(default="EURUSD")):
    return {"marketStructure": market_cache.structures.get(symbol, {})}


@router.get("/price-action", response_class=ORJSONResponse)
async def get_price_action():
    return {"priceAction": []}


@router.get("/signals", response_class=ORJSONResponse)
async def get_signals(symbol: str = Query(default="EURUSD")):
    return {"signals": [signal_service.build_signal(symbol)]}


@router.get("/statistics", response_class=ORJSONResponse)
async def get_statistics():
    return {"statistics": {"accuracy": 0.62, "wins": 10, "losses": 6, "draws": 2}}


@router.get("/activity", response_class=ORJSONResponse)
async def get_activity(symbol: str = Query(default="EURUSD")):
    df = market_cache.get_candles(symbol)
    if df is None or df.empty:
        return {"activity": {}}
    latest = df.iloc[-1]
    return {"activity": {"syntheticVolume": float(latest.get("synthetic_volume", 0.0)), "activityScore": float(latest.get("market_activity_score", 0.0))}}


@router.get("/dashboard", response_class=ORJSONResponse)
async def get_dashboard(symbol: str = Query(default="EURUSD")):
    return {"dashboard": market_service.get_latest_snapshot(symbol)}


@router.get("/cache", response_class=ORJSONResponse)
async def get_cache():
    return {"cache": market_cache.snapshot()}


@router.get("/history", response_class=ORJSONResponse)
async def get_history(symbol: str = Query(default="EURUSD")):
    df = market_cache.get_candles(symbol)
    if df is None:
        return {"history": []}
    return {"history": df.tail(10).to_dict(orient="records")}


@router.get("/trend", response_class=ORJSONResponse)
async def get_trend(symbol: str = Query(default="EURUSD")):
    return {"trend": {"symbol": symbol, "status": "ready"}}


@router.get("/volatility", response_class=ORJSONResponse)
async def get_volatility(symbol: str = Query(default="EURUSD")):
    return {"volatility": {"symbol": symbol, "status": "ready"}}


@router.get("/momentum", response_class=ORJSONResponse)
async def get_momentum(symbol: str = Query(default="EURUSD")):
    return {"momentum": {"symbol": symbol, "status": "ready"}}


@router.get("/confluence", response_class=ORJSONResponse)
async def get_confluence(symbol: str = Query(default="EURUSD")):
    return {"confluence": {"symbol": symbol, "status": "ready"}}


@router.get("/order-blocks", response_class=ORJSONResponse)
async def get_order_blocks():
    return {"orderBlocks": []}


@router.get("/liquidity", response_class=ORJSONResponse)
async def get_liquidity():
    return {"liquidity": []}


@router.get("/support-resistance", response_class=ORJSONResponse)
async def get_support_resistance():
    return {"supportResistance": []}


@router.get("/health", response_class=ORJSONResponse)
async def get_market_health():
    return {"status": "ok", "market": "ready"}
