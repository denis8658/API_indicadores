from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from app.cache.market_cache import market_cache
from app.collectors.data_collector import collector
from app.indicators.indicator_engine import IndicatorEngine
from app.market_structure.market_structure_engine import MarketStructureEngine
from app.price_action.price_action_engine import PriceActionEngine
from app.synthetic_volume.synthetic_volume_engine import SyntheticVolumeEngine


class MarketService:
    def __init__(self) -> None:
        self.indicator_engine = IndicatorEngine()
        self.structure_engine = MarketStructureEngine()
        self.price_action_engine = PriceActionEngine()
        self.synthetic_volume_engine = SyntheticVolumeEngine()

    async def refresh_market(self, symbol: str = "EURUSD") -> Dict[str, Any]:
        candles = await collector.get_candles(symbol=symbol, limit=500)
        if not candles:
            return {"symbol": symbol, "status": "empty"}
        df = pd.DataFrame(candles)
        df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
        df = df.sort_values("timestamp")
        df = df.reset_index(drop=True)
        df = self.synthetic_volume_engine.update(df)
        df = self.indicator_engine.update(df)
        df = self.structure_engine.update(df)
        df = self.price_action_engine.update(df)
        market_cache.set_candles(symbol, df)
        market_cache.set_indicators(symbol, df[[c for c in df.columns if c not in {"timestamp", "open", "high", "low", "close", "volume"}]].copy())
        latest = df.iloc[-1].to_dict()
        return {
            "symbol": symbol,
            "status": "ok",
            "latest": latest,
            "rows": len(df),
            "columns": len(df.columns),
        }

    def get_latest_snapshot(self, symbol: str = "EURUSD") -> Dict[str, Any]:
        df = market_cache.get_candles(symbol)
        if df is None or df.empty:
            return {"symbol": symbol, "status": "empty"}
        latest = df.iloc[-1].to_dict()
        indicators = market_cache.get_indicators(symbol)
        return {
            "symbol": symbol,
            "status": "ok",
            "latest": latest,
            "indicator_count": len(indicators.columns) if indicators is not None else 0,
            "cache": market_cache.snapshot(),
        }


market_service = MarketService()
