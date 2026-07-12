from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Candle(BaseModel):
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class Tick(BaseModel):
    timestamp: int
    price: float
    volume: float = 0.0


class IndicatorSummary(BaseModel):
    name: str
    value: float


class MarketSignal(BaseModel):
    symbol: str = "EURUSD"
    action: str = "NONE"
    score: float = 0.0
    confidence: float = 0.0
    reason: str = ""
    expiration: int = 0
    entryPrice: float = 0.0
    marketPhase: str = "neutral"
    trend: str = "neutral"
    historicalAccuracy: float = 0.0


class MarketHealth(BaseModel):
    status: str
    connected: bool = False
    candles: int = 0
    ticks: int = 0
    indicators: int = 0
