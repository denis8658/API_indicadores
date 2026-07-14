from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from app.services.signal_service import signal_service


class BacktestService:
    def run(self, df: pd.DataFrame, symbol: str, timeframe: int, warmup: int = 40) -> Dict[str, Any]:
        if df is None or len(df) <= warmup + 1:
            return {"symbol": symbol, "timeframe": timeframe, "trades": [], "statistics": {"total": 0, "wins": 0, "losses": 0, "draws": 0, "accuracy": 0.0}}
        trades: List[Dict[str, Any]] = []
        for index in range(warmup, len(df) - 1):
            signal = signal_service.build_signal(symbol, timeframe, df.iloc[: index + 1], include_history=False)
            if signal["action"] not in {"CALL", "PUT"}:
                continue
            entry = float(df.iloc[index]["close"])
            exit_price = float(df.iloc[index + 1]["close"])
            outcome = "DRAW" if exit_price == entry else "WIN" if (signal["action"] == "CALL" and exit_price > entry) or (signal["action"] == "PUT" and exit_price < entry) else "LOSS"
            trades.append({"timestamp": int(df.iloc[index]["timestamp"]), "action": signal["action"], "entryPrice": entry, "exitPrice": exit_price, "score": signal["score"], "confidence": signal["confidence"], "outcome": outcome})
        wins = sum(item["outcome"] == "WIN" for item in trades)
        losses = sum(item["outcome"] == "LOSS" for item in trades)
        draws = sum(item["outcome"] == "DRAW" for item in trades)
        total = len(trades)
        return {"symbol": symbol, "timeframe": timeframe, "trades": trades[-100:], "statistics": {"total": total, "wins": wins, "losses": losses, "draws": draws, "accuracy": wins / total if total else 0.0}}


backtest_service = BacktestService()
