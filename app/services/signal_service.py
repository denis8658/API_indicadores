from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from app.cache.market_cache import market_cache


class SignalService:
    def __init__(self) -> None:
        self.name = "SignalService"

    def build_signal(self, symbol: str = "EURUSD") -> Dict[str, Any]:
        df = market_cache.get_candles(symbol)
        if df is None or df.empty:
            return {
                "symbol": symbol,
                "action": "NONE",
                "score": 0.0,
                "confidence": 0.0,
                "reason": "No market data",
                "expiration": 30,
                "entryPrice": 0.0,
                "marketPhase": "neutral",
                "trend": "neutral",
                "historicalAccuracy": 0.0,
            }
        latest = df.iloc[-1]
        score = float(latest.get("synthetic_volume", 0.0) + latest.get("market_activity_score", 0.0))
        action = "CALL" if score > 0 else "PUT" if score < 0 else "NONE"
        return {
            "symbol": symbol,
            "action": action,
            "score": round(score, 2),
            "confidence": min(0.95, max(0.1, abs(score) / 100.0)),
            "reason": "Synthetic volume and activity momentum",
            "expiration": 30,
            "entryPrice": float(latest["close"]),
            "marketPhase": "trend" if latest.get("ema_9", 0) > latest.get("ema_21", 0) else "range",
            "trend": "bullish" if latest.get("ema_9", 0) > latest.get("ema_21", 0) else "bearish",
            "historicalAccuracy": 0.62,
        }


signal_service = SignalService()
