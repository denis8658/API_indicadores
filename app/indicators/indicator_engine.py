from __future__ import annotations

import pandas as pd


class IndicatorEngine:
    def __init__(self) -> None:
        self.name = "IndicatorEngine"

    def update(self, df: pd.DataFrame) -> pd.DataFrame:
        import pandas_ta as ta

        if df.empty:
            return df
        df = df.copy()
        df["ema_9"] = ta.ema(df["close"], length=9)
        df["ema_21"] = ta.ema(df["close"], length=21)
        df["sma_20"] = ta.sma(df["close"], length=20)
        df["rsi_14"] = ta.rsi(df["close"], length=14)
        df["macd"] = ta.macd(df["close"])["MACD_12_26_9"]
        df["bb_upper"] = ta.bbands(df["close"]).iloc[:, 0]
        df["bb_middle"] = ta.bbands(df["close"]).iloc[:, 1]
        df["bb_lower"] = ta.bbands(df["close"]).iloc[:, 2]
        df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)
        df["stoch_k"] = ta.stoch(df["high"], df["low"], df["close"]).iloc[:, 0]
        df["stoch_d"] = ta.stoch(df["high"], df["low"], df["close"]).iloc[:, 1]
        df["adx"] = ta.adx(df["high"], df["low"], df["close"]).iloc[:, 0]
        vwap = ta.vwap(df["high"], df["low"], df["close"], df["volume"])
        df["vwap"] = vwap if vwap is not None else pd.NA
        psar = ta.psar(df["high"], df["low"], df["close"], af0=0.02, af=0.02, max_af=0.2)
        df["sar"] = psar.iloc[:, 0] if psar is not None and not psar.empty else pd.NA
        return df
