from __future__ import annotations

import pandas as pd


class MarketStructureEngine:
    def __init__(self) -> None:
        self.name = "MarketStructureEngine"

    def update(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        df = df.copy()
        df["swing_high"] = df["high"].rolling(5, center=True).max()
        df["swing_low"] = df["low"].rolling(5, center=True).min()
        df["support"] = df["low"].rolling(10).min()
        df["resistance"] = df["high"].rolling(10).max()
        df["equal_high"] = df["high"].diff().abs().lt(1e-6)
        df["equal_low"] = df["low"].diff().abs().lt(1e-6)
        return df
