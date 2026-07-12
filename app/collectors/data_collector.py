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
        self.raw_ssid: Optional[str] = self._normalize_pocket_auth(settings.pocket_ssid)
        self.ssid: Optional[str] = self._normalize_pocket_session(settings.pocket_ssid)

    def _normalize_pocket_auth(self, pocket_ssid_raw: Any) -> Optional[str]:
        if pocket_ssid_raw is None:
            return None
        if isinstance(pocket_ssid_raw, str):
            s = pocket_ssid_raw.strip()
            return s or None
        return None

    def _normalize_pocket_session(self, pocket_ssid_raw: Any) -> Optional[str]:
        """
        Aceita:
          - "qrhc1u..." (session pura)
          - "qrhc1u..." (ssid)
          - JSON/array tipo: 42["auth",{"session":"qrhc1u...","isDemo":1,...}]
          - dict tipo {"auth":{"session":"..."}} ou {"session":"..."} etc.
        Retorna a string da sessão (session/ssid) para usar como SSID real.
        """
        if pocket_ssid_raw is None:
            return None

        # Se for dict, tenta extrair sessão diretamente
        if isinstance(pocket_ssid_raw, dict):
            # casos comuns
            for key in ("session", "ssid", "SSID"):
                val = pocket_ssid_raw.get(key)
                if isinstance(val, str) and val:
                    return val
            auth_payload = pocket_ssid_raw.get("auth")
            if isinstance(auth_payload, dict):
                for key in ("session", "ssid", "SSID"):
                    val = auth_payload.get(key)
                    if isinstance(val, str) and val:
                        return val
            # fallback
            return None

        # Se for lista (array/WS), tenta procurar "session"
        if isinstance(pocket_ssid_raw, list):
            for item in pocket_ssid_raw:
                val = self._normalize_pocket_session(item)
                if val:
                    return val
            return None

        # Se for string
        if isinstance(pocket_ssid_raw, str):
            s = pocket_ssid_raw.strip()
            if not s:
                return None

            # Se já parece session pura, retorna
            # (A sessão normalmente não contém colchetes/aspas de array)
            if s.startswith("qr") and ("[" not in s) and ("]" not in s) and ('"' not in s):
                return s

            # Tentativa por regex: session":"qrhc1u..."
            import re

            match = re.search(r'"session"\s*:\s*"([^"]+)"', s)
            if match:
                return match.group(1)

            # Tentativa por regex: ssid":"qrhc1u..."
            match = re.search(r'"ssid"\s*:\s*"([^"]+)"', s)
            if match:
                return match.group(1)

            # Tentativa por regex: "SSID":"qrhc1u..."
            match = re.search(r'"SSID"\s*:\s*"([^"]+)"', s)
            if match:
                return match.group(1)

            # fallback: às vezes a string já é o ssid puro mas com espaços
            # (não dá pra ter 100% certeza; então retorna o próprio quando contém pattern conhecido)
            if "qr" in s and '"' not in s and "[" not in s and "]" not in s and "," not in s:
                return s

        return None

    async def connect(self) -> Dict[str, Any]:
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=10.0)

        raw_ssid = self._normalize_pocket_auth(self.raw_ssid) or self._normalize_pocket_auth(settings.pocket_ssid)
        payload: Dict[str, Any] = {"ssid": raw_ssid or ""}

        if not payload["ssid"]:
            payload = {"api_key": "demo"}

        response = await self.client.post(f"{self.base_url}/api/init", json=payload)
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError:
            data = response.text

        connect_response = await self.client.post(f"{self.base_url}/api/connect")
        connect_response.raise_for_status()

        self.session_info = data if isinstance(data, dict) else {"raw": data}
        extracted = self._extract_ssid(data) or payload.get("ssid") or self.ssid
        self.ssid = self._normalize_pocket_session(extracted)
        self.raw_ssid = raw_ssid or self.raw_ssid
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
        response = await self.client.get(f"{self.base_url}/api/assets", headers=self._build_headers())
        response.raise_for_status()
        data = response.json()
        assets = data.get("assets", {}) if isinstance(data, dict) else {}
        if isinstance(assets, dict):
            return [{"symbol": symbol, "name": name} for symbol, name in assets.items()]
        if isinstance(assets, list):
            return assets
        return []

    def _extract_ssid(self, data: Any) -> Optional[str]:
        if isinstance(data, dict):
            for key in ("ssid", "SSID", "session_id", "session"):
                value = data.get(key)
                if isinstance(value, str) and value:
                    return value
            auth_payload = data.get("auth")
            if isinstance(auth_payload, dict):
                for key in ("session", "ssid", "SSID"):
                    value = auth_payload.get(key)
                    if isinstance(value, str) and value:
                        return value
            if isinstance(data.get("result"), dict):
                return self._extract_ssid(data["result"])
        elif isinstance(data, list):
            for item in data:
                ssid = self._extract_ssid(item)
                if ssid:
                    return ssid
        elif isinstance(data, str):
            import re

            patterns = [r'"session"\s*:\s*"([^"]+)"', r'"ssid"\s*:\s*"([^"]+)"', r'"SSID"\s*:\s*"([^"]+)"']
            for pattern in patterns:
                match = re.search(pattern, data)
                if match:
                    return match.group(1)
        return None

    def _build_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if self.ssid:
            headers["SSID"] = self.ssid
            headers["ssid"] = self.ssid
        return headers

    async def get_candles(self, symbol: str = "EURUSD", limit: int = 500) -> List[Dict[str, Any]]:
        if not self.connected:
            await self.connect()
        payload = {"asset": symbol, "timeframe": 60, "count": limit}
        response = await self.client.post(
            f"{self.base_url}/api/candles",
            json=payload,
            headers=self._build_headers(),
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("candles", [])
        return []

    async def get_ticks(self, symbol: str = "EURUSD") -> List[Dict[str, Any]]:
        if not self.connected:
            await self.connect()
        response = await self.client.get(
            f"{self.base_url}/api/ticks/{symbol}",
            headers=self._build_headers(),
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and "ticks" in data:
            ticks = data.get("ticks", {})
            if isinstance(ticks, dict):
                return list(ticks.values())
            if isinstance(ticks, list):
                return ticks
        if isinstance(data, dict):
            return [data]
        if isinstance(data, list):
            return data
        return []

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
