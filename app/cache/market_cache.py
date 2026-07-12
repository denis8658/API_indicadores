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
        self.features: Dict[str, Dict[str, float]] = {}
        self.structures: Dict[str, Dict[str, Any]] = {}
        self.signals: Dict[str, Dict[str, Any]] = {}
        self.statistics: Dict[str, Any] = {}
        self.synthetic_volume: Dict[str, Dict[str, float]] = {}

    def set_candles(self, symbol: str, df: pd.DataFrame) -> None:
        with self._lock:
            self.candles[symbol] = df.copy()

    def get_candles(self, symbol: str) -> Optional[pd.DataFrame]:
        with self._lock:
            return self.candles.get(symbol)

    def set_ticks(self, symbol: str, ticks: List[Dict[str, Any]]) -> None:
        with self._lock:
            self.ticks[symbol] = ticks

    def get_ticks(self, symbol: str) -> List[Dict[str, Any]]:
        with self._lock:
            return self.ticks.get(symbol, [])

    def set_indicators(self, symbol: str, df: pd.DataFrame) -> None:
        with self._lock:
            self.indicators[symbol] = df.copy()

    def get_indicators(self, symbol: str) -> Optional[pd.DataFrame]:
        with self._lock:
            return self.indicators.get(symbol)

    def set_structures(self, symbol: str, structures: Dict[str, Any]) -> None:
        with self._lock:
            self.structures[symbol] = structures

    def get_structures(self, symbol: str) -> Dict[str, Any]:
        with self._lock:
            return self.structures.get(symbol, {})

    def set_features(self, symbol: str, features: Dict[str, float]) -> None:
        with self._lock:
            self.features[symbol] = features

    def get_features(self, symbol: str) -> Dict[str, float]:
        with self._lock:
            return self.features.get(symbol, {})

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "candles": {k: len(v) for k, v in self.candles.items()},
                "ticks": {k: len(v) for k, v in self.ticks.items()},
                "indicators": {k: len(v) for k, v in self.indicators.items()},
            }


market_cache = MarketCache()
