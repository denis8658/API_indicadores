from __future__ import annotations

from threading import Lock
from typing import Any, Dict, List, Optional

import pandas as pd


class MarketCache:
    def __init__(self) -> None:
        self._lock = Lock()
        self.candles: Dict[str, pd.DataFrame] = {}
        self.ticks: Dict[str, List[Dict[str, Any]]] = {}
        self.indicators: Dict[str, pd.DataFrame] = {}
        self.features: Dict[str, Dict[str, Any]] = {}
        self.structures: Dict[str, Dict[str, Any]] = {}
        self.signals: Dict[str, Dict[str, Any]] = {}
        self.statistics: Dict[str, Any] = {}
        self.synthetic_volume: Dict[str, Dict[str, float]] = {}

    @staticmethod
    def key(symbol: str, timeframe: int = 60) -> str:
        """Keep the original M1 cache keys while isolating other timeframes."""
        return symbol if timeframe == 60 else f"{symbol}:{timeframe}"

    def set_candles(self, symbol: str, df: pd.DataFrame, timeframe: int = 60) -> None:
        with self._lock:
            self.candles[self.key(symbol, timeframe)] = df.copy()

    def get_candles(self, symbol: str, timeframe: int = 60) -> Optional[pd.DataFrame]:
        with self._lock:
            value = self.candles.get(self.key(symbol, timeframe))
            return value.copy() if value is not None else None

    def set_ticks(self, symbol: str, ticks: List[Dict[str, Any]], timeframe: int = 60) -> None:
        with self._lock:
            self.ticks[self.key(symbol, timeframe)] = list(ticks)

    def get_ticks(self, symbol: str, timeframe: int = 60) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self.ticks.get(self.key(symbol, timeframe), []))

    def set_indicators(self, symbol: str, df: pd.DataFrame, timeframe: int = 60) -> None:
        with self._lock:
            self.indicators[self.key(symbol, timeframe)] = df.copy()

    def get_indicators(self, symbol: str, timeframe: int = 60) -> Optional[pd.DataFrame]:
        with self._lock:
            value = self.indicators.get(self.key(symbol, timeframe))
            return value.copy() if value is not None else None

    def set_structures(self, symbol: str, structures: Dict[str, Any], timeframe: int = 60) -> None:
        with self._lock:
            self.structures[self.key(symbol, timeframe)] = structures

    def get_structures(self, symbol: str, timeframe: int = 60) -> Dict[str, Any]:
        with self._lock:
            return dict(self.structures.get(self.key(symbol, timeframe), {}))

    def set_features(self, symbol: str, features: Dict[str, Any], timeframe: int = 60) -> None:
        with self._lock:
            self.features[self.key(symbol, timeframe)] = features

    def get_features(self, symbol: str, timeframe: int = 60) -> Dict[str, Any]:
        with self._lock:
            return dict(self.features.get(self.key(symbol, timeframe), {}))

    def set_signal(self, symbol: str, signal: Dict[str, Any], timeframe: int = 60) -> None:
        with self._lock:
            self.signals[self.key(symbol, timeframe)] = signal

    def get_signal(self, symbol: str, timeframe: int = 60) -> Dict[str, Any]:
        with self._lock:
            return dict(self.signals.get(self.key(symbol, timeframe), {}))

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "candles": {k: len(v) for k, v in self.candles.items()},
                "ticks": {k: len(v) for k, v in self.ticks.items()},
                "indicators": {k: len(v) for k, v in self.indicators.items()},
            }


market_cache = MarketCache()
