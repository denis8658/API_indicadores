from __future__ import annotations

import pandas as pd


class PriceActionEngine:
    def __init__(self) -> None:
        self.name = "PriceActionEngine"

    def update(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        df = df.copy()
        df["body"] = (df["close"] - df["open"]).abs()
        df["range"] = df["high"] - df["low"]
        df["body_percent"] = (df["body"] / df["range"].replace(0, 1e-6)) * 100
        df["wick_percent"] = ((df["high"] - df[["open", "close"]].max(axis=1)) + (df[["open", "close"]].min(axis=1) - df["low"])) / df["range"].replace(0, 1e-6) * 100
        df["doji"] = df["body_percent"].lt(10)
        previous_open = df["open"].shift(1)
        previous_close = df["close"].shift(1)
        df["bullish_engulfing"] = (df["close"] > df["open"]) & (previous_close < previous_open) & (df["open"] <= previous_close) & (df["close"] >= previous_open)
        df["bearish_engulfing"] = (df["close"] < df["open"]) & (previous_close > previous_open) & (df["open"] >= previous_close) & (df["close"] <= previous_open)
        previous_high = df["high"].shift(1).rolling(20, min_periods=5).max()
        previous_low = df["low"].shift(1).rolling(20, min_periods=5).min()
        df["breakout_up"] = df["close"].gt(previous_high)
        df["breakout_down"] = df["close"].lt(previous_low)
        df["breakout"] = df["breakout_up"]
        df["compression"] = df["range"].rolling(5).mean().lt(df["range"].rolling(20).mean())
        return df
