from __future__ import annotations

import pandas as pd


class MarketStructureEngine:
    def __init__(self) -> None:
        self.name = "MarketStructureEngine"

    def update(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        df = df.copy()
        rolling_high = df["high"].rolling(5, center=True).max()
        rolling_low = df["low"].rolling(5, center=True).min()
        df["pivot_high"] = df["high"].eq(rolling_high)
        df["pivot_low"] = df["low"].eq(rolling_low)
        df["swing_high"] = df["high"].where(df["pivot_high"]).ffill()
        df["swing_low"] = df["low"].where(df["pivot_low"]).ffill()
        df["support"] = df["low"].shift(1).rolling(20, min_periods=5).min()
        df["resistance"] = df["high"].shift(1).rolling(20, min_periods=5).max()
        tolerance = df["close"].abs().mul(0.00005).clip(lower=1e-9)
        df["equal_high"] = df["high"].diff().abs().le(tolerance)
        df["equal_low"] = df["low"].diff().abs().le(tolerance)
        df["bos"] = None
        df.loc[df["close"].gt(df["resistance"]), "bos"] = "bullish"
        df.loc[df["close"].lt(df["support"]), "bos"] = "bearish"
        direction = df["bos"].ffill()
        df["choch"] = direction.where(direction.ne(direction.shift(1)) & direction.shift(1).notna())
        df["market_structure"] = direction.fillna("range")
        return df
