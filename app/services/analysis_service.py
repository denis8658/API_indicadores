from __future__ import annotations

import math
from typing import Any, Dict, List

import pandas as pd


def _number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


class AnalysisService:
    def _latest(self, df: pd.DataFrame) -> pd.Series:
        return df.iloc[-1] if df is not None and not df.empty else pd.Series(dtype=object)

    def trend(self, df: pd.DataFrame, symbol: str, timeframe: int) -> Dict[str, Any]:
        row = self._latest(df)
        close = _number(row.get("close"))
        ema9 = _number(row.get("ema_9"))
        ema21 = _number(row.get("ema_21"))
        adx = _number(row.get("adx"))
        slope = _number(df["close"].tail(10).pct_change().mean()) if not df.empty else 0.0
        direction = "bullish" if ema9 > ema21 and close >= ema9 else "bearish" if ema9 < ema21 and close <= ema9 else "neutral"
        strength = "strong" if adx >= 25 else "moderate" if adx >= 18 else "weak"
        return {"symbol": symbol, "timeframe": timeframe, "direction": direction, "strength": strength, "adx": adx, "ema9": ema9, "ema21": ema21, "slope": slope}

    def momentum(self, df: pd.DataFrame, symbol: str, timeframe: int) -> Dict[str, Any]:
        row = self._latest(df)
        rsi = _number(row.get("rsi_14"), 50.0)
        macd = _number(row.get("macd"))
        stoch_k = _number(row.get("stoch_k"), 50.0)
        stoch_d = _number(row.get("stoch_d"), 50.0)
        direction = "bullish" if rsi > 52 and macd >= 0 else "bearish" if rsi < 48 and macd <= 0 else "neutral"
        state = "overbought" if rsi >= 70 else "oversold" if rsi <= 30 else "balanced"
        return {"symbol": symbol, "timeframe": timeframe, "direction": direction, "state": state, "rsi": rsi, "macd": macd, "stochK": stoch_k, "stochD": stoch_d}

    def volatility(self, df: pd.DataFrame, symbol: str, timeframe: int) -> Dict[str, Any]:
        row = self._latest(df)
        close = _number(row.get("close"))
        atr = _number(row.get("atr"))
        upper = _number(row.get("bb_upper"))
        lower = _number(row.get("bb_lower"))
        atr_percent = atr / close * 100 if close else 0.0
        width_percent = abs(upper - lower) / close * 100 if close else 0.0
        recent = df["close"].pct_change().tail(30).std() * 100 if len(df) > 1 else 0.0
        realized = _number(recent)
        regime = "high" if atr_percent >= 0.15 or realized >= 0.15 else "normal" if atr_percent >= 0.05 or realized >= 0.05 else "low"
        return {"symbol": symbol, "timeframe": timeframe, "regime": regime, "atr": atr, "atrPercent": atr_percent, "bollingerWidthPercent": width_percent, "realizedVolatility": realized}

    def price_action(self, df: pd.DataFrame, symbol: str, timeframe: int, limit: int = 20) -> List[Dict[str, Any]]:
        if df is None or df.empty:
            return []
        events: List[Dict[str, Any]] = []
        for _, row in df.tail(limit).iterrows():
            patterns = []
            if bool(row.get("doji", False)):
                patterns.append("doji")
            if bool(row.get("bullish_engulfing", False)):
                patterns.append("bullish_engulfing")
            if bool(row.get("bearish_engulfing", False)):
                patterns.append("bearish_engulfing")
            if bool(row.get("breakout_up", False)):
                patterns.append("breakout_up")
            if bool(row.get("breakout_down", False)):
                patterns.append("breakout_down")
            if bool(row.get("compression", False)):
                patterns.append("compression")
            if patterns:
                events.append({"symbol": symbol, "timeframe": timeframe, "timestamp": int(_number(row.get("timestamp"))), "close": _number(row.get("close")), "patterns": patterns})
        return events

    def support_resistance(self, df: pd.DataFrame, symbol: str, timeframe: int, max_levels: int = 8) -> List[Dict[str, Any]]:
        if df is None or df.empty:
            return []
        close = _number(df.iloc[-1].get("close"))
        atr = max(_number(df.iloc[-1].get("atr")), close * 0.0001, 1e-9)
        candidates: List[tuple[float, str, int]] = []
        for _, row in df.iterrows():
            if bool(row.get("pivot_high", False)):
                candidates.append((_number(row.get("high")), "resistance", int(_number(row.get("timestamp")))))
            if bool(row.get("pivot_low", False)):
                candidates.append((_number(row.get("low")), "support", int(_number(row.get("timestamp")))))
        levels: List[Dict[str, Any]] = []
        for price, kind, timestamp in candidates:
            existing = next((level for level in levels if abs(level["price"] - price) <= atr * 0.35), None)
            if existing:
                existing["touches"] += 1
                existing["price"] = (existing["price"] * (existing["touches"] - 1) + price) / existing["touches"]
                existing["lastTimestamp"] = max(existing["lastTimestamp"], timestamp)
            else:
                levels.append({"symbol": symbol, "timeframe": timeframe, "type": kind, "price": price, "touches": 1, "lastTimestamp": timestamp})
        for level in levels:
            level["distancePercent"] = abs(close - level["price"]) / close * 100 if close else 0.0
            level["strength"] = min(1.0, level["touches"] / 4)
        return sorted(levels, key=lambda item: (-item["touches"], item["distancePercent"]))[:max_levels]

    def liquidity(self, df: pd.DataFrame, symbol: str, timeframe: int) -> List[Dict[str, Any]]:
        if df is None or df.empty:
            return []
        close = _number(df.iloc[-1].get("close"))
        atr = max(_number(df.iloc[-1].get("atr")), close * 0.0001, 1e-9)
        zones: List[Dict[str, Any]] = []
        for _, row in df.tail(100).iterrows():
            for column, side in (("high", "buy_side"), ("low", "sell_side")):
                price = _number(row.get(column))
                prior = [zone for zone in zones if zone["side"] == side and abs(zone["price"] - price) <= atr * 0.2]
                if prior:
                    prior[0]["touches"] += 1
                    prior[0]["lastTimestamp"] = int(_number(row.get("timestamp")))
                else:
                    zones.append({"symbol": symbol, "timeframe": timeframe, "side": side, "price": price, "touches": 1, "lastTimestamp": int(_number(row.get("timestamp")))})
        return sorted([zone for zone in zones if zone["touches"] >= 2], key=lambda item: (-item["touches"], abs(item["price"] - close)))[:8]

    def order_blocks(self, df: pd.DataFrame, symbol: str, timeframe: int) -> List[Dict[str, Any]]:
        if df is None or len(df) < 3:
            return []
        blocks: List[Dict[str, Any]] = []
        for index in range(1, len(df) - 1):
            row = df.iloc[index]
            nxt = df.iloc[index + 1]
            atr = max(_number(row.get("atr")), _number(row.get("range")), 1e-9)
            bullish = row["close"] < row["open"] and nxt["close"] > nxt["open"] and (nxt["close"] - nxt["open"]) >= atr * 0.8
            bearish = row["close"] > row["open"] and nxt["close"] < nxt["open"] and (nxt["open"] - nxt["close"]) >= atr * 0.8
            if bullish or bearish:
                blocks.append({"symbol": symbol, "timeframe": timeframe, "type": "bullish" if bullish else "bearish", "low": _number(row.get("low")), "high": _number(row.get("high")), "timestamp": int(_number(row.get("timestamp"))), "mitigated": False})
        close = _number(df.iloc[-1].get("close"))
        for block in blocks:
            block["mitigated"] = block["low"] <= close <= block["high"]
        return blocks[-10:]

    def confluence(self, df: pd.DataFrame, symbol: str, timeframe: int, signal: Dict[str, Any]) -> Dict[str, Any]:
        return {"symbol": symbol, "timeframe": timeframe, "action": signal.get("action", "NONE"), "score": signal.get("score", 0.0), "confidence": signal.get("confidence", 0.0), **signal.get("confluence", {})}

    def features(self, df: pd.DataFrame, symbol: str, timeframe: int) -> Dict[str, Any]:
        if df is None or df.empty:
            return {}
        return {"trend": self.trend(df, symbol, timeframe), "momentum": self.momentum(df, symbol, timeframe), "volatility": self.volatility(df, symbol, timeframe), "priceAction": self.price_action(df, symbol, timeframe, 5)}

    def structure(self, df: pd.DataFrame, symbol: str, timeframe: int) -> Dict[str, Any]:
        row = self._latest(df)
        state = row.get("market_structure", "range")
        bos = row.get("bos", None)
        choch = row.get("choch", None)
        state = "range" if state is None or pd.isna(state) else str(state)
        bos = None if bos is None or pd.isna(bos) else str(bos)
        choch = None if choch is None or pd.isna(choch) else str(choch)
        return {"symbol": symbol, "timeframe": timeframe, "state": state, "bos": bos, "choch": choch, "support": _number(row.get("support")), "resistance": _number(row.get("resistance")), "levels": self.support_resistance(df, symbol, timeframe), "liquidity": self.liquidity(df, symbol, timeframe), "orderBlocks": self.order_blocks(df, symbol, timeframe)}


analysis_service = AnalysisService()
