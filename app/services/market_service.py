from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from app.cache.market_cache import market_cache
from app.collectors.data_collector import collector
from app.indicators.indicator_engine import IndicatorEngine
from app.market_structure.market_structure_engine import MarketStructureEngine
from app.price_action.price_action_engine import PriceActionEngine
from app.synthetic_volume.synthetic_volume_engine import SyntheticVolumeEngine
from app.services.analysis_service import analysis_service
from app.services.storage_service import storage_service


class MarketService:
    def __init__(self) -> None:
        self.indicator_engine = IndicatorEngine()
        self.structure_engine = MarketStructureEngine()
        self.price_action_engine = PriceActionEngine()
        self.synthetic_volume_engine = SyntheticVolumeEngine()

    def process_dataframe(self, symbol: str, timeframe: int, source: pd.DataFrame, persist: bool = False) -> pd.DataFrame:
        df = source.copy()
        required = {"timestamp", "open", "high", "low", "close"}
        if df.empty or not required.issubset(df.columns):
            return pd.DataFrame()
        if "volume" not in df.columns:
            df["volume"] = 0.0
        for column in ["timestamp", "open", "high", "low", "close", "volume"]:
            df[column] = pd.to_numeric(df[column], errors="coerce")
        df = df.dropna(subset=list(required)).sort_values("timestamp").drop_duplicates("timestamp", keep="last").tail(500).reset_index(drop=True)
        df = self.synthetic_volume_engine.update(df)
        df = self.indicator_engine.update(df)
        df = self.structure_engine.update(df)
        df = self.price_action_engine.update(df)
        market_cache.set_candles(symbol, df, timeframe)
        excluded = {"timestamp", "open", "high", "low", "close", "volume", "asset", "timeframe"}
        market_cache.set_indicators(symbol, df[[column for column in df.columns if column not in excluded]].copy(), timeframe)
        market_cache.set_features(symbol, analysis_service.features(df, symbol, timeframe), timeframe)
        market_cache.set_structures(symbol, analysis_service.structure(df, symbol, timeframe), timeframe)
        if persist:
            storage_service.save_candles(symbol, timeframe, df)
        storage_service.evaluate_pending(symbol, timeframe, df)
        return df

    async def refresh_market(self, symbol: str = "EURUSD", timeframe: int = 60) -> Dict[str, Any]:
        try:
            candles = await collector.get_candles(symbol=symbol, limit=500, timeframe=timeframe)
        except Exception:
            candles = []
            stored = storage_service.load_candles(symbol, timeframe)
            if stored.empty:
                raise
        if not candles:
            stored = storage_service.load_candles(symbol, timeframe)
            if stored.empty:
                return {"symbol": symbol, "timeframe": timeframe, "status": "empty"}
            df = self.process_dataframe(symbol, timeframe, stored)
        else:
            df = self.process_dataframe(symbol, timeframe, pd.DataFrame(candles), persist=True)
        if df.empty:
            return {"symbol": symbol, "timeframe": timeframe, "status": "empty"}
        latest = df.iloc[-1].to_dict()
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "status": "ok",
            "latest": latest,
            "rows": len(df),
            "columns": len(df.columns),
        }

    def get_latest_snapshot(self, symbol: str = "EURUSD", timeframe: int = 60) -> Dict[str, Any]:
        df = market_cache.get_candles(symbol, timeframe)
        if df is None or df.empty:
            return {"symbol": symbol, "status": "empty"}
        latest = df.iloc[-1].to_dict()
        indicators = market_cache.get_indicators(symbol, timeframe)
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "status": "ok",
            "latest": latest,
            "indicator_count": len(indicators.columns) if indicators is not None else 0,
            "cache": market_cache.snapshot(),
        }


market_service = MarketService()
