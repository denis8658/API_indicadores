from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import httpx

from app.config.settings import settings


class DataCollector:
    def __init__(self) -> None:
        self.base_url = settings.api_base_url
        self.client: Optional[httpx.AsyncClient] = None
        self.connected = False
        self.session_info: Dict[str, Any] = {}
        self.ssid: Optional[str] = None

    async def connect(self) -> Dict[str, Any]:
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=10.0)
        payload = {"api_key": "demo"}
        response = await self.client.post(f"{self.base_url}/api/init", json=payload)
        response.raise_for_status()
        data = response.json()
        self.session_info = data
        self.ssid = data.get("ssid") or data.get("SSID") or data.get("session_id")
        self.connected = True
        return data

    async def disconnect(self) -> None:
        if self.client is not None:
            await self.client.aclose()
            self.client = None
        self.connected = False

    async def health(self) -> Dict[str, Any]:
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=10.0)
        response = await self.client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    async def get_assets(self) -> List[Dict[str, Any]]:
        if not self.connected:
            await self.connect()
        return [{"symbol": "EURUSD", "name": "EUR/USD"}]

    def _build_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if self.ssid:
            headers["SSID"] = self.ssid
            headers["ssid"] = self.ssid
        return headers

    async def get_candles(self, symbol: str = "EURUSD", limit: int = 500) -> List[Dict[str, Any]]:
        if not self.connected:
            await self.connect()
        payload = {"symbol": symbol, "limit": limit}
        response = await self.client.post(
            f"{self.base_url}/api/candles",
            json=payload,
            headers=self._build_headers(),
        )
        response.raise_for_status()
        return response.json().get("candles", [])

    async def get_ticks(self, symbol: str = "EURUSD") -> List[Dict[str, Any]]:
        if not self.connected:
            await self.connect()
        response = await self.client.get(
            f"{self.base_url}/api/ticks/{symbol}",
            headers=self._build_headers(),
        )
        response.raise_for_status()
        return response.json().get("ticks", [])

    async def get_orders(self) -> List[Dict[str, Any]]:
        return []

    async def get_balance(self) -> Dict[str, Any]:
        return {"balance": 0.0}

    async def get_payouts(self) -> Dict[str, Any]:
        return {"payouts": {}}

    async def reconnect(self) -> Dict[str, Any]:
        await self.disconnect()
        return await self.connect()

    async def heartbeat(self) -> Dict[str, Any]:
        return {"status": "ok"}


collector = DataCollector()
