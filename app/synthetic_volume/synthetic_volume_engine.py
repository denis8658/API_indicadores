from __future__ import annotations

import numpy as np
import pandas as pd


class SyntheticVolumeEngine:
    def __init__(self) -> None:
        self.name = "SyntheticVolumeEngine"

    def update(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        df = df.copy()
        df["tick_count"] = 1
        df["range"] = df["high"] - df["low"]
        df["body"] = (df["close"] - df["open"]).abs()
        df["upper_wick"] = (df["high"] - df[["open", "close"]].max(axis=1)).abs()
        df["lower_wick"] = (df[["open", "close"]].min(axis=1) - df["low"]).abs()
        df["atr"] = df["range"].rolling(14).mean()
        df["tick_weight"] = (df["body"] + df["range"]).clip(lower=1e-6)
        df["bollinger_width"] = (
            df["close"].rolling(20).std() * 2
        )
        df["tick_speed"] = df["close"].diff().abs().rolling(5).mean()
        df["tick_acceleration"] = df["tick_speed"].diff().abs()
        raw = (
            df["tick_count"]
            + df["tick_weight"]
            + df["atr"]
            + df["range"]
            + df["body"]
            + df["upper_wick"]
            + df["lower_wick"]
            + df["bollinger_width"]
            + df["tick_speed"]
            + df["tick_acceleration"]
        )
        df["synthetic_volume"] = (raw / raw.replace(0, np.nan).rolling(10).mean()).fillna(0)
        df["market_activity_score"] = df["synthetic_volume"].rolling(10).mean()
        return df
