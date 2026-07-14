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
        volume = pd.to_numeric(df.get("volume", 0), errors="coerce").fillna(0)
        df["tick_count"] = volume.where(volume.gt(0), 1.0)
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
        components = ["tick_count", "tick_weight", "atr", "range", "body", "upper_wick", "lower_wick", "bollinger_width", "tick_speed", "tick_acceleration"]
        normalized = []
        for column in components:
            baseline = df[column].replace(0, np.nan).rolling(20, min_periods=5).mean()
            normalized.append(df[column].div(baseline).replace([np.inf, -np.inf], np.nan))
        df["synthetic_volume"] = pd.concat(normalized, axis=1).mean(axis=1, skipna=True).fillna(0)
        df["market_activity_score"] = df["synthetic_volume"].rolling(10).mean()
        return df
