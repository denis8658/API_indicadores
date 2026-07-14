from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

import pandas as pd

from app.config.settings import settings


class StorageService:
    def __init__(self, path: Optional[str] = None) -> None:
        self.path = Path(path or settings.database_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS candles (
                    symbol TEXT NOT NULL, timeframe INTEGER NOT NULL, timestamp INTEGER NOT NULL,
                    open REAL NOT NULL, high REAL NOT NULL, low REAL NOT NULL, close REAL NOT NULL,
                    volume REAL NOT NULL DEFAULT 0, PRIMARY KEY(symbol, timeframe, timestamp)
                );
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL, timeframe INTEGER NOT NULL,
                    candle_timestamp INTEGER NOT NULL, created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
                    action TEXT NOT NULL, entry_price REAL NOT NULL, score REAL NOT NULL, confidence REAL NOT NULL,
                    outcome TEXT, exit_price REAL, evaluated_at INTEGER, payload TEXT NOT NULL,
                    UNIQUE(symbol, timeframe, candle_timestamp, action)
                );
                CREATE INDEX IF NOT EXISTS ix_signals_lookup ON signals(symbol, timeframe, outcome);
                """
            )

    def save_candles(self, symbol: str, timeframe: int, df: pd.DataFrame) -> None:
        columns = {"timestamp", "open", "high", "low", "close"}
        if df is None or df.empty or not columns.issubset(df.columns):
            return
        rows = [(symbol, timeframe, int(row.timestamp), float(row.open), float(row.high), float(row.low), float(row.close), float(getattr(row, "volume", 0) or 0)) for row in df.tail(500).itertuples()]
        with self._lock, self._connect() as connection:
            connection.executemany("INSERT OR REPLACE INTO candles(symbol,timeframe,timestamp,open,high,low,close,volume) VALUES(?,?,?,?,?,?,?,?)", rows)

    def load_candles(self, symbol: str, timeframe: int, limit: int = 500) -> pd.DataFrame:
        with self._connect() as connection:
            rows = connection.execute("SELECT timestamp,open,high,low,close,volume FROM candles WHERE symbol=? AND timeframe=? ORDER BY timestamp DESC LIMIT ?", (symbol, timeframe, limit)).fetchall()
        return pd.DataFrame([dict(row) for row in reversed(rows)])

    def save_signal(self, signal: Dict[str, Any], timeframe: int, candle_timestamp: int) -> Optional[int]:
        if signal.get("action") not in {"CALL", "PUT"}:
            return None
        created_at = candle_timestamp
        expires_at = created_at + max(int(signal.get("expiration", timeframe)), 1)
        with self._lock, self._connect() as connection:
            connection.execute("INSERT OR IGNORE INTO signals(symbol,timeframe,candle_timestamp,created_at,expires_at,action,entry_price,score,confidence,payload) VALUES(?,?,?,?,?,?,?,?,?,?)", (signal["symbol"], timeframe, candle_timestamp, created_at, expires_at, signal["action"], float(signal["entryPrice"]), float(signal["score"]), float(signal["confidence"]), json.dumps(signal)))
            row = connection.execute("SELECT id FROM signals WHERE symbol=? AND timeframe=? AND candle_timestamp=? AND action=?", (signal["symbol"], timeframe, candle_timestamp, signal["action"])).fetchone()
            return int(row["id"]) if row else None

    def evaluate_pending(self, symbol: str, timeframe: int, df: pd.DataFrame) -> int:
        if df is None or df.empty:
            return 0
        evaluated = 0
        with self._lock, self._connect() as connection:
            pending = connection.execute("SELECT * FROM signals WHERE symbol=? AND timeframe=? AND outcome IS NULL", (symbol, timeframe)).fetchall()
            for signal in pending:
                future = df[pd.to_numeric(df["timestamp"], errors="coerce") >= signal["expires_at"]]
                if future.empty:
                    continue
                exit_row = future.iloc[0]
                exit_price = float(exit_row["close"])
                entry = float(signal["entry_price"])
                outcome = "DRAW" if exit_price == entry else "WIN" if (signal["action"] == "CALL" and exit_price > entry) or (signal["action"] == "PUT" and exit_price < entry) else "LOSS"
                connection.execute("UPDATE signals SET outcome=?,exit_price=?,evaluated_at=? WHERE id=?", (outcome, exit_price, int(exit_row["timestamp"]), signal["id"]))
                evaluated += 1
        return evaluated

    def signal_history(self, symbol: Optional[str] = None, timeframe: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        clauses, params = [], []
        if symbol:
            clauses.append("symbol=?"); params.append(symbol)
        if timeframe:
            clauses.append("timeframe=?"); params.append(timeframe)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(f"SELECT id,symbol,timeframe,candle_timestamp,action,entry_price,score,confidence,outcome,exit_price,evaluated_at FROM signals{where} ORDER BY id DESC LIMIT ?", (*params, limit)).fetchall()
        return [dict(row) for row in rows]

    def statistics(self, symbol: Optional[str] = None, timeframe: Optional[int] = None) -> Dict[str, Any]:
        history = self.signal_history(symbol, timeframe, 100000)
        wins = sum(item["outcome"] == "WIN" for item in history)
        losses = sum(item["outcome"] == "LOSS" for item in history)
        draws = sum(item["outcome"] == "DRAW" for item in history)
        pending = sum(item["outcome"] is None for item in history)
        completed = wins + losses + draws
        return {"total": len(history), "completed": completed, "pending": pending, "wins": wins, "losses": losses, "draws": draws, "accuracy": wins / completed if completed else 0.0}


storage_service = StorageService()
