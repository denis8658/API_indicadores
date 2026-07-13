from __future__ import annotations

import re
from typing import Any

import pandas as pd


class IndicatorEngine:
    def __init__(self) -> None:
        self.name = "IndicatorEngine"

    def _normalize_name(self, name: Any) -> str:
        text = str(name).strip().lower()
        text = re.sub(r"[^a-z0-9]+", "_", text)
        return re.sub(r"_+", "_", text).strip("_")

    def _assign_output(self, df: pd.DataFrame, name: str, output: Any) -> pd.DataFrame:
        if output is None:
            return df
        prefix = f"pta_{self._normalize_name(name)}"
        if isinstance(output, tuple):
            for index, item in enumerate(output):
                df = self._assign_output(df, f"{prefix}_{index}", item)
            return df
        if isinstance(output, pd.DataFrame):
            for column in output.columns:
                normalized = self._normalize_name(column)
                target = f"pta_{normalized}" if not normalized.startswith("pta_") else normalized
                if target in {"pta_open", "pta_high", "pta_low", "pta_close", "pta_volume"}:
                    target = f"{prefix}_{target}"
                df[target] = output[column]
            return df
        if isinstance(output, pd.Series):
            column = output.name if output.name else prefix
            normalized = self._normalize_name(column)
            target = f"pta_{normalized}" if not normalized.startswith("pta_") else normalized
            if target in {"pta_open", "pta_high", "pta_low", "pta_close", "pta_volume"}:
                target = prefix
            df[target] = output
            return df
        return df

    def _apply(self, df: pd.DataFrame, name: str, func: Any, *args: Any, **kwargs: Any) -> pd.DataFrame:
        try:
            return self._assign_output(df, name, func(*args, **kwargs))
        except Exception:
            df[f"pta_error_{self._normalize_name(name)}"] = pd.NA
            return df

    def _apply_all_pandas_ta(self, df: pd.DataFrame) -> pd.DataFrame:
        import pandas_ta as ta

        open_ = df["open"]
        high = df["high"]
        low = df["low"]
        close = df["close"]
        volume = df["volume"]

        close_only = [
            "ebsw",
            "reflex",
            "apo",
            "bias",
            "cfo",
            "cg",
            "cmo",
            "coppock",
            "crsi",
            "cti",
            "er",
            "kst",
            "macd",
            "mom",
            "ppo",
            "psl",
            "qqe",
            "roc",
            "rsi",
            "rsx",
            "slope",
            "smi",
            "stc",
            "stochrsi",
            "trix",
            "tsi",
            "alma",
            "dema",
            "ema",
            "fwma",
            "hma",
            "hwma",
            "jma",
            "kama",
            "linreg",
            "mama",
            "mcgd",
            "midpoint",
            "pwma",
            "rma",
            "sinwma",
            "sma",
            "smma",
            "ssf",
            "ssf3",
            "swma",
            "t3",
            "tema",
            "trima",
            "vidya",
            "wma",
            "zlma",
            "drawdown",
            "log_return",
            "percent_return",
            "entropy",
            "kurtosis",
            "mad",
            "median",
            "quantile",
            "skew",
            "stdev",
            "tos_stdevall",
            "variance",
            "zscore",
            "amat",
            "decay",
            "decreasing",
            "dpo",
            "ht_trendline",
            "increasing",
            "trendflex",
            "vhf",
            "nvi",
            "pvi",
            "pvo",
        ]
        for name in close_only:
            df = self._apply(df, name, getattr(ta, name), close)

        high_low = ["fisher", "hl2", "midprice", "aroon"]
        for name in high_low:
            df = self._apply(df, name, getattr(ta, name), high, low)

        high_low_close = [
            "ao",
            "cci",
            "dm",
            "kdj",
            "pgo",
            "squeeze",
            "squeeze_pro",
            "stoch",
            "stochf",
            "uo",
            "willr",
            "hlc3",
            "hilo",
            "supertrend",
            "wcp",
            "adx",
            "alphatrend",
            "chop",
            "cksp",
            "rwi",
            "ttm_trend",
            "vortex",
            "aberration",
            "accbands",
            "atr",
            "atrts",
            "bbands",
            "chandelier_exit",
            "donchian",
            "hwc",
            "kc",
            "massi",
            "natr",
            "pdist",
            "rvi",
            "thermo",
            "true_range",
            "ui",
        ]
        for name in high_low_close:
            df = self._apply(df, name, getattr(ta, name), high, low, close)

        open_high_low_close = [
            "cdl_doji",
            "cdl_inside",
            "cdl_z",
            "ha",
            "bop",
            "brar",
            "rvgi",
            "ohlc4",
        ]
        for name in open_high_low_close:
            df = self._apply(df, name, getattr(ta, name), open_, high, low, close)

        open_close = ["qstick"]
        for name in open_close:
            df = self._apply(df, name, getattr(ta, name), open_, close)

        high_low_close_volume = [
            "mfi",
            "ad",
            "adosc",
            "cmf",
            "eom",
            "kvo",
            "vhm",
            "vwap",
        ]
        for name in high_low_close_volume:
            df = self._apply(df, name, getattr(ta, name), high, low, close, volume)

        close_volume = ["aobv", "efi", "obv", "pvol", "pvr", "pvt", "tsv", "vwma"]
        for name in close_volume:
            df = self._apply(df, name, getattr(ta, name), close, volume)

        df = self._apply(df, "eri", ta.eri, high, low, close)
        df = self._apply(df, "inertia", ta.inertia, close)
        df = self._apply(df, "tmo", ta.tmo, open_, close)
        df = self._apply(df, "alligator", ta.alligator, high, low, close)
        df = self._apply(df, "ichimoku", ta.ichimoku, high, low, close)
        df = self._apply(df, "pivots", ta.pivots, high, low, close)
        df = self._apply(df, "psar", ta.psar, high, low, close, af0=0.02, af=0.02, max_af=0.2)
        df = self._apply(df, "zigzag", ta.zigzag, high, low, close)
        df = self._apply(df, "vp", ta.vp, close, volume)

        return df

    def _apply_compatibility_aliases(self, df: pd.DataFrame) -> pd.DataFrame:
        import pandas_ta as ta

        df["ema_9"] = ta.ema(df["close"], length=9)
        df["ema_21"] = ta.ema(df["close"], length=21)
        df["sma_20"] = ta.sma(df["close"], length=20)
        df["rsi_14"] = ta.rsi(df["close"], length=14)
        macd = ta.macd(df["close"])
        df["macd"] = macd["MACD_12_26_9"] if macd is not None and "MACD_12_26_9" in macd else pd.NA
        bbands = ta.bbands(df["close"])
        if bbands is not None and not bbands.empty:
            df["bb_upper"] = bbands.iloc[:, 0]
            df["bb_middle"] = bbands.iloc[:, 1]
            df["bb_lower"] = bbands.iloc[:, 2]
        else:
            df["bb_upper"] = pd.NA
            df["bb_middle"] = pd.NA
            df["bb_lower"] = pd.NA
        df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)
        stoch = ta.stoch(df["high"], df["low"], df["close"])
        if stoch is not None and not stoch.empty:
            df["stoch_k"] = stoch.iloc[:, 0]
            df["stoch_d"] = stoch.iloc[:, 1]
        else:
            df["stoch_k"] = pd.NA
            df["stoch_d"] = pd.NA
        adx = ta.adx(df["high"], df["low"], df["close"])
        df["adx"] = adx.iloc[:, 0] if adx is not None and not adx.empty else pd.NA
        vwap = ta.vwap(df["high"], df["low"], df["close"], df["volume"])
        df["vwap"] = vwap if vwap is not None else pd.NA
        psar = ta.psar(df["high"], df["low"], df["close"], af0=0.02, af=0.02, max_af=0.2)
        df["sar"] = psar.iloc[:, 0] if psar is not None and not psar.empty else pd.NA
        return df

    def update(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        df = df.copy()
        df = self._apply_all_pandas_ta(df)
        df = self._apply_compatibility_aliases(df)
        return df.copy()
