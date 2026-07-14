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
        close, high, low = df["close"], df["high"], df["low"]
        df["ema_9"] = close.ewm(span=9, adjust=False).mean()
        df["ema_21"] = close.ewm(span=21, adjust=False).mean()
        df["sma_20"] = close.rolling(20).mean()

        delta = close.diff()
        gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        relative_strength = gain / loss.replace(0, float("nan"))
        df["rsi_14"] = (100 - 100 / (1 + relative_strength)).where(loss.ne(0), 100.0)
        ema_12 = close.ewm(span=12, adjust=False).mean()
        ema_26 = close.ewm(span=26, adjust=False).mean()
        df["macd"] = ema_12 - ema_26

        middle = close.rolling(20).mean()
        deviation = close.rolling(20).std(ddof=0)
        df["bb_lower"] = middle - 2 * deviation
        df["bb_middle"] = middle
        df["bb_upper"] = middle + 2 * deviation

        previous_close = close.shift(1)
        true_range = pd.concat([(high - low).abs(), (high - previous_close).abs(), (low - previous_close).abs()], axis=1).max(axis=1)
        df["atr"] = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        lowest = low.rolling(14).min()
        highest = high.rolling(14).max()
        df["stoch_k"] = 100 * (close - lowest) / (highest - lowest).replace(0, float("nan"))
        df["stoch_d"] = df["stoch_k"].rolling(3).mean()

        up_move = high.diff()
        down_move = -low.diff()
        plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
        minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
        smooth_tr = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        plus_di = 100 * plus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / smooth_tr.replace(0, float("nan"))
        minus_di = 100 * minus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / smooth_tr.replace(0, float("nan"))
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, float("nan"))
        df["adx"] = dx.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()

        typical = (high + low + close) / 3
        volume = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
        cumulative_volume = volume.cumsum()
        df["vwap"] = (typical * volume).cumsum() / cumulative_volume.replace(0, float("nan"))
        df["sar"] = self._parabolic_sar(high, low)
        return df

    def _parabolic_sar(self, high: pd.Series, low: pd.Series) -> pd.Series:
        if high.empty:
            return pd.Series(dtype=float, index=high.index)
        values = [float(low.iloc[0])]
        bullish, extreme, acceleration = True, float(high.iloc[0]), 0.02
        for index in range(1, len(high)):
            sar = values[-1] + acceleration * (extreme - values[-1])
            if bullish:
                sar = min(sar, float(low.iloc[index - 1]), float(low.iloc[max(0, index - 2)]))
                if float(low.iloc[index]) < sar:
                    bullish, sar, extreme, acceleration = False, extreme, float(low.iloc[index]), 0.02
                elif float(high.iloc[index]) > extreme:
                    extreme, acceleration = float(high.iloc[index]), min(0.2, acceleration + 0.02)
            else:
                sar = max(sar, float(high.iloc[index - 1]), float(high.iloc[max(0, index - 2)]))
                if float(high.iloc[index]) > sar:
                    bullish, sar, extreme, acceleration = True, extreme, float(high.iloc[index]), 0.02
                elif float(low.iloc[index]) < extreme:
                    extreme, acceleration = float(low.iloc[index]), min(0.2, acceleration + 0.02)
            values.append(sar)
        return pd.Series(values, index=high.index, dtype=float)

    def update(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        df = df.copy()
        df = self._apply_compatibility_aliases(df)
        return df.copy()
