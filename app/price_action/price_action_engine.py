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
        df["breakout"] = df["close"].gt(df["close"].shift(1))
        df["compression"] = df["range"].rolling(5).mean().lt(df["range"].rolling(20).mean())
        return df
