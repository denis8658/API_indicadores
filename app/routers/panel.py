from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import httpx
from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, ORJSONResponse

from app.config.settings import settings

router = APIRouter(tags=["test-panel"])


Validator = Callable[[Any], tuple[bool, str]]


@dataclass(frozen=True)
class EndpointCheck:
    group: str
    name: str
    method: str
    url: str
    expected: str
    validator: Validator
    body: Optional[Dict[str, Any]] = None


def has_key(key: str) -> Validator:
    def validate(data: Any) -> tuple[bool, str]:
        if isinstance(data, dict) and key in data:
            return True, f"campo '{key}' encontrado"
        return False, f"campo '{key}' ausente"

    return validate


def status_key(expected: str = "ok") -> Validator:
    def validate(data: Any) -> tuple[bool, str]:
        status = data.get("status") if isinstance(data, dict) else None
        if status == expected:
            return True, f"status={status}"
        return False, f"status esperado={expected}, recebido={status}"

    return validate


def array_key(key: str, min_count: int = 0) -> Validator:
    def validate(data: Any) -> tuple[bool, str]:
        value = data.get(key) if isinstance(data, dict) else None
        if isinstance(value, list) and len(value) >= min_count:
            return True, f"{key}={len(value)} itens"
        return False, f"{key} deveria ser lista com pelo menos {min_count} itens"

    return validate


def object_key(key: str) -> Validator:
    def validate(data: Any) -> tuple[bool, str]:
        value = data.get(key) if isinstance(data, dict) else None
        if isinstance(value, dict):
            return True, f"{key}=objeto"
        return False, f"{key} deveria ser objeto"

    return validate


def direct_array(min_count: int = 0) -> Validator:
    def validate(data: Any) -> tuple[bool, str]:
        if isinstance(data, list) and len(data) >= min_count:
            return True, f"array={len(data)} itens"
        return False, f"resposta deveria ser array com pelo menos {min_count} itens"

    return validate


def tick_payload(expected_asset: str) -> Validator:
    def validate(data: Any) -> tuple[bool, str]:
        if not isinstance(data, dict):
            return False, "resposta deveria ser objeto"
        asset = data.get("asset")
        price = data.get("price")
        if asset == expected_asset and isinstance(price, (int, float)):
            return True, f"{asset} price={price}"
        return False, f"asset/preco invalido: asset={asset}, price={price}"

    return validate


def pocket_health(data: Any) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "resposta deveria ser objeto"
    connected = data.get("connected")
    authenticated = data.get("authenticated")
    websocket_connected = data.get("websocket_connected")
    if connected and authenticated and websocket_connected:
        return True, "connected/authenticated/websocket=true"
    return False, f"connected={connected}, authenticated={authenticated}, websocket={websocket_connected}"


def pocket_init(data: Any) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "resposta deveria ser objeto"
    if data.get("status") == "initialized":
        return True, "status=initialized"
    return False, f"status recebido={data.get('status')}"


def order_place(data: Any) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "resposta deveria ser objeto"
    request_id = data.get("request_id") or data.get("order_id")
    if request_id and data.get("status") in {"active", "placed", "open"}:
        return True, f"request_id={request_id}"
    return False, "ordem sem request_id/status ativo"


def order_result(data: Any) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "resposta deveria ser objeto"
    if data.get("completed") is True and data.get("timeout") is False:
        return True, f"result={data.get('result')}, profit={data.get('profit')}"
    return False, f"completed={data.get('completed')}, timeout={data.get('timeout')}, result={data.get('result')}"


def summarize(data: Any) -> str:
    if isinstance(data, list):
        return f"array com {len(data)} itens"
    if not isinstance(data, dict):
        return str(data)[:160]
    parts: List[str] = []
    for key, value in list(data.items())[:7]:
        if isinstance(value, list):
            parts.append(f"{key}=array({len(value)})")
        elif isinstance(value, dict):
            parts.append(f"{key}=object")
        else:
            text = str(value)
            parts.append(f"{key}={text[:80]}")
    return "; ".join(parts)


async def run_check(client: httpx.AsyncClient, check: EndpointCheck) -> Dict[str, Any]:
    started = time.perf_counter()
    try:
        response = await client.request(check.method, check.url, json=check.body)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        try:
            data: Any = response.json()
        except ValueError:
            data = response.text
        passed, detail = check.validator(data) if response.status_code < 400 else (False, "HTTP >= 400")
        return {
            "group": check.group,
            "name": check.name,
            "method": check.method,
            "url": check.url,
            "status_code": response.status_code,
            "elapsed_ms": elapsed_ms,
            "passed": response.status_code == 200 and passed,
            "expected": check.expected,
            "detail": detail,
            "summary": summarize(data),
        }
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "group": check.group,
            "name": check.name,
            "method": check.method,
            "url": check.url,
            "status_code": None,
            "elapsed_ms": elapsed_ms,
            "passed": False,
            "expected": check.expected,
            "detail": str(exc),
            "summary": "erro na requisicao",
        }


def build_checks(base_url: str, pocket_url: str, asset: str, ssid: str) -> List[EndpointCheck]:
    base = base_url.rstrip("/")
    pocket = pocket_url.rstrip("/")
    return [
        EndpointCheck("API Indicadores", "Root", "GET", f"{base}/", "message presente", has_key("message")),
        EndpointCheck("API Indicadores", "Health", "GET", f"{base}/health", "status ok", status_key()),
        EndpointCheck("API Indicadores", "Assets", "GET", f"{base}/market/assets", "assets com itens", array_key("assets", 1)),
        EndpointCheck("API Indicadores", "Candles", "GET", f"{base}/market/candles?symbol={asset}", "candles com itens", array_key("candles", 1)),
        EndpointCheck("API Indicadores", "Ticks", "GET", f"{base}/market/ticks?symbol={asset}", "ticks com itens", array_key("ticks", 1)),
        EndpointCheck("API Indicadores", "Indicators", "GET", f"{base}/market/indicators?symbol={asset}", "indicators lista", array_key("indicators", 0)),
        EndpointCheck("API Indicadores", "Features", "GET", f"{base}/market/features?symbol={asset}", "features presente", has_key("features")),
        EndpointCheck("API Indicadores", "Market Structure", "GET", f"{base}/market/market-structure?symbol={asset}", "marketStructure presente", has_key("marketStructure")),
        EndpointCheck("API Indicadores", "Price Action", "GET", f"{base}/market/price-action", "priceAction lista", array_key("priceAction", 0)),
        EndpointCheck("API Indicadores", "Signals", "GET", f"{base}/market/signals?symbol={asset}", "signals com item", array_key("signals", 1)),
        EndpointCheck("API Indicadores", "Statistics", "GET", f"{base}/market/statistics", "statistics objeto", object_key("statistics")),
        EndpointCheck("API Indicadores", "Activity", "GET", f"{base}/market/activity?symbol={asset}", "activity objeto", object_key("activity")),
        EndpointCheck("API Indicadores", "Dashboard", "GET", f"{base}/market/dashboard?symbol={asset}", "dashboard objeto", object_key("dashboard")),
        EndpointCheck("API Indicadores", "Cache", "GET", f"{base}/market/cache", "cache objeto", object_key("cache")),
        EndpointCheck("API Indicadores", "History", "GET", f"{base}/market/history?symbol={asset}", "history lista", array_key("history", 0)),
        EndpointCheck("API Indicadores", "Trend", "GET", f"{base}/market/trend?symbol={asset}", "trend objeto", object_key("trend")),
        EndpointCheck("API Indicadores", "Volatility", "GET", f"{base}/market/volatility?symbol={asset}", "volatility objeto", object_key("volatility")),
        EndpointCheck("API Indicadores", "Momentum", "GET", f"{base}/market/momentum?symbol={asset}", "momentum objeto", object_key("momentum")),
        EndpointCheck("API Indicadores", "Confluence", "GET", f"{base}/market/confluence?symbol={asset}", "confluence objeto", object_key("confluence")),
        EndpointCheck("API Indicadores", "Order Blocks", "GET", f"{base}/market/order-blocks", "orderBlocks lista", array_key("orderBlocks", 0)),
        EndpointCheck("API Indicadores", "Liquidity", "GET", f"{base}/market/liquidity", "liquidity lista", array_key("liquidity", 0)),
        EndpointCheck("API Indicadores", "Support Resistance", "GET", f"{base}/market/support-resistance", "supportResistance lista", array_key("supportResistance", 0)),
        EndpointCheck("API Indicadores", "Market Health", "GET", f"{base}/market/health", "market ready", has_key("market")),
        EndpointCheck("Pocket API", "Root", "GET", f"{pocket}/", "status running", has_key("status")),
        EndpointCheck("Pocket API", "Health", "GET", f"{pocket}/health", "conectado e autenticado", pocket_health),
        EndpointCheck("Pocket API", "Init", "POST", f"{pocket}/api/init", "initialized", pocket_init, {"ssid": ssid}),
        EndpointCheck("Pocket API", "Connect", "POST", f"{pocket}/api/connect", "connected", status_key("connected"), {}),
        EndpointCheck("Pocket API", "Diagnostics", "GET", f"{pocket}/api/diagnostics", "authenticated true", has_key("authenticated")),
        EndpointCheck("Pocket API", "Assets", "GET", f"{pocket}/api/assets", "count/assets presente", has_key("count")),
        EndpointCheck("Pocket API", "Payouts", "GET", f"{pocket}/api/payouts", "payouts objeto", object_key("payouts")),
        EndpointCheck("Pocket API", "Pairs Payouts", "GET", f"{pocket}/api/pairs/payouts", "pairs com itens", array_key("pairs", 1)),
        EndpointCheck("Pocket API", f"Payout {asset}", "GET", f"{pocket}/api/payouts/{asset}", "payout presente", has_key("payout")),
        EndpointCheck("Pocket API", "Ticks Geral", "GET", f"{pocket}/api/ticks", "ticks presente", has_key("ticks")),
        EndpointCheck("Pocket API", f"Tick {asset}", "GET", f"{pocket}/api/ticks/{asset}", "asset e price", tick_payload(asset)),
        EndpointCheck("Pocket API", "Market Cache", "GET", f"{pocket}/api/market/cache", "connected presente", has_key("connected")),
        EndpointCheck("Pocket API", f"Candles {asset}", "POST", f"{pocket}/api/candles", "array com candles", direct_array(1), {"asset": asset, "timeframe": 60, "count": 5}),
        EndpointCheck("Pocket API", "Balance", "GET", f"{pocket}/api/balance", "balance presente", has_key("balance")),
        EndpointCheck("Pocket API", "Connection Stats", "GET", f"{pocket}/api/connection-stats", "total_connections presente", has_key("total_connections")),
        EndpointCheck("Pocket API", "Active Orders", "GET", f"{pocket}/api/orders/active", "array de ordens", direct_array(0)),
    ]


@router.get("/test-panel", response_class=HTMLResponse, include_in_schema=False)
async def test_panel_page() -> HTMLResponse:
    return HTMLResponse(TEST_PANEL_HTML)


@router.get("/usage-panel", response_class=HTMLResponse, include_in_schema=False)
async def usage_panel_page() -> HTMLResponse:
    return HTMLResponse(USAGE_PANEL_HTML)


@router.get("/usage-panel/data", response_class=ORJSONResponse)
async def usage_panel_data(
    request: Request,
    asset: str = Query(default="USDJPY_otc"),
):
    transport = httpx.ASGITransport(app=request.app)
    timeout = httpx.Timeout(80.0, connect=15.0)
    async with httpx.AsyncClient(transport=transport, base_url="http://internal", timeout=timeout) as client:
        endpoints = {
            "assets": "/market/assets",
            "candles": f"/market/candles?symbol={asset}",
            "ticks": f"/market/ticks?symbol={asset}",
            "indicators": f"/market/indicators?symbol={asset}",
            "features": f"/market/features?symbol={asset}",
            "marketStructure": f"/market/market-structure?symbol={asset}",
            "signals": f"/market/signals?symbol={asset}",
            "statistics": "/market/statistics",
            "activity": f"/market/activity?symbol={asset}",
            "dashboard": f"/market/dashboard?symbol={asset}",
            "history": f"/market/history?symbol={asset}",
            "trend": f"/market/trend?symbol={asset}",
            "volatility": f"/market/volatility?symbol={asset}",
            "momentum": f"/market/momentum?symbol={asset}",
            "confluence": f"/market/confluence?symbol={asset}",
            "orderBlocks": "/market/order-blocks",
            "liquidity": "/market/liquidity",
            "supportResistance": "/market/support-resistance",
            "health": "/market/health",
        }
        responses: Dict[str, Any] = {}
        errors: Dict[str, str] = {}
        for key, url in endpoints.items():
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    responses[key] = response.json()
                else:
                    errors[key] = f"HTTP {response.status_code}"
            except Exception as exc:
                errors[key] = str(exc)

    candles = responses.get("candles", {}).get("candles", [])
    ticks = responses.get("ticks", {}).get("ticks", [])
    indicators = responses.get("indicators", {}).get("indicators", [])
    signals = responses.get("signals", {}).get("signals", [])
    latest_candle = candles[-1] if candles else {}
    latest_indicator = indicators[-1] if indicators else {}
    latest_tick = ticks[-1] if ticks else {}
    signal = signals[0] if signals else {}
    dashboard = responses.get("dashboard", {}).get("dashboard", {})

    return {
        "asset": asset,
        "loadedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "errors": errors,
        "assets": responses.get("assets", {}).get("assets", []),
        "latest": {
            "price": latest_tick.get("price") or latest_candle.get("close") or dashboard.get("latest", {}).get("close"),
            "tick": latest_tick,
            "candle": latest_candle,
            "indicator": latest_indicator,
            "signal": signal,
            "activity": responses.get("activity", {}).get("activity", {}),
            "dashboard": dashboard,
        },
        "series": {
            "candles": candles,
            "history": responses.get("history", {}).get("history", []),
            "indicators": indicators,
        },
        "analysis": {
            "features": responses.get("features", {}).get("features"),
            "marketStructure": responses.get("marketStructure", {}).get("marketStructure", {}),
            "statistics": responses.get("statistics", {}).get("statistics", {}),
            "trend": responses.get("trend", {}).get("trend", {}),
            "volatility": responses.get("volatility", {}).get("volatility", {}),
            "momentum": responses.get("momentum", {}).get("momentum", {}),
            "confluence": responses.get("confluence", {}).get("confluence", {}),
            "orderBlocks": responses.get("orderBlocks", {}).get("orderBlocks", []),
            "liquidity": responses.get("liquidity", {}).get("liquidity", []),
            "supportResistance": responses.get("supportResistance", {}).get("supportResistance", []),
            "health": responses.get("health", {}),
        },
    }


@router.get("/test-panel/results", response_class=ORJSONResponse)
async def test_panel_results(
    request: Request,
    asset: str = Query(default="USDJPY_otc"),
    include_order: bool = Query(default=False),
):
    ssid = settings.pocket_ssid
    checks = build_checks("http://internal", settings.api_base_url, asset, ssid)
    timeout = httpx.Timeout(60.0, connect=15.0)
    transport = httpx.ASGITransport(app=request.app)
    async with (
        httpx.AsyncClient(transport=transport, base_url="http://internal", timeout=timeout) as internal_client,
        httpx.AsyncClient(timeout=timeout) as external_client,
    ):
        results = []
        for check in checks:
            if check.name == "Init" and not ssid:
                results.append({
                    "group": check.group,
                    "name": check.name,
                    "method": check.method,
                    "url": check.url,
                    "status_code": None,
                    "elapsed_ms": 0,
                    "passed": False,
                    "expected": "POCKET_OPTION_SSID configurado",
                    "detail": "SSID nao configurado no ambiente desta API",
                    "summary": "configure POCKET_OPTION_SSID para testar init",
                })
                continue
            client = internal_client if check.group == "API Indicadores" else external_client
            results.append(await run_check(client, check))

        order_result_data = None
        if include_order:
            order_result_data = await run_order_test(external_client, settings.api_base_url, asset)

    passed = sum(1 for item in results if item["passed"])
    failed = len(results) - passed
    if order_result_data:
        failed += 0 if order_result_data["passed"] else 1
        passed += 1 if order_result_data["passed"] else 0
    return {
        "asset": asset,
        "include_order": include_order,
        "summary": {"passed": passed, "failed": failed, "total": passed + failed},
        "results": results,
        "order": order_result_data,
    }


async def run_order_test(client: httpx.AsyncClient, pocket_url: str, asset: str) -> Dict[str, Any]:
    pocket = pocket_url.rstrip("/")
    order_payload = {"asset": asset, "direction": "CALL", "amount": 1, "duration_seconds": 30}
    started = time.perf_counter()
    try:
        response = await client.post(f"{pocket}/api/order/place", json=order_payload)
        place_data = response.json()
        if response.status_code != 200:
            return {
                "passed": False,
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
                "place": summarize(place_data),
                "result": None,
                "detail": f"order/place HTTP {response.status_code}",
            }
        request_id = place_data.get("request_id") or place_data.get("order_id")
        if not request_id:
            return {
                "passed": False,
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
                "place": summarize(place_data),
                "result": None,
                "detail": "ordem criada sem request_id",
            }

        await asyncio.sleep(35)
        result_response = await client.get(f"{pocket}/api/order/result/{request_id}", params={"timeout": 90})
        result_data = result_response.json()
        passed, detail = order_result(result_data)
        return {
            "passed": result_response.status_code == 200 and passed,
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
            "place": place_data,
            "result": result_data,
            "detail": detail,
        }
    except Exception as exc:
        return {
            "passed": False,
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
            "place": None,
            "result": None,
            "detail": str(exc),
        }


TEST_PANEL_HTML = """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Painel de Testes da API</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5f7fb;
      --surface: #ffffff;
      --ink: #16202a;
      --muted: #667085;
      --line: #d9e1ec;
      --ok: #0f8a5f;
      --bad: #c03744;
      --warn: #a15c00;
      --accent: #2357c5;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: var(--bg);
      color: var(--ink);
    }
    header {
      padding: 20px 24px;
      background: var(--surface);
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
    }
    h1 { font-size: 20px; margin: 0; font-weight: 700; }
    main { padding: 20px 24px 32px; }
    .controls {
      display: grid;
      grid-template-columns: minmax(180px, 260px) auto auto;
      gap: 10px;
      align-items: end;
      margin-bottom: 18px;
    }
    label { display: grid; gap: 6px; font-size: 13px; color: var(--muted); }
    input {
      height: 38px;
      border: 1px solid var(--line);
      background: var(--surface);
      border-radius: 6px;
      padding: 0 10px;
      color: var(--ink);
      font-size: 14px;
    }
    button {
      height: 38px;
      border: 1px solid var(--accent);
      background: var(--accent);
      color: white;
      border-radius: 6px;
      padding: 0 14px;
      font-weight: 700;
      cursor: pointer;
    }
    button.secondary {
      background: var(--surface);
      color: var(--accent);
    }
    button:disabled { opacity: .55; cursor: wait; }
    .summary {
      display: grid;
      grid-template-columns: repeat(4, minmax(120px, 1fr));
      gap: 10px;
      margin-bottom: 18px;
    }
    .metric {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
    }
    .metric span { display: block; color: var(--muted); font-size: 12px; margin-bottom: 6px; }
    .metric strong { font-size: 22px; }
    .toolbar {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      margin: 8px 0 10px;
      color: var(--muted);
      font-size: 13px;
      flex-wrap: wrap;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }
    th, td {
      padding: 10px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      font-size: 13px;
    }
    th {
      background: #edf2f8;
      color: #354154;
      font-size: 12px;
      text-transform: uppercase;
    }
    tr:last-child td { border-bottom: 0; }
    .pill {
      display: inline-flex;
      align-items: center;
      min-width: 74px;
      justify-content: center;
      height: 24px;
      border-radius: 999px;
      color: white;
      font-weight: 700;
      font-size: 12px;
    }
    .ok { background: var(--ok); }
    .fail { background: var(--bad); }
    .order {
      margin-top: 18px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }
    pre {
      margin: 10px 0 0;
      white-space: pre-wrap;
      word-break: break-word;
      background: #101828;
      color: #eef4ff;
      padding: 12px;
      border-radius: 6px;
      max-height: 360px;
      overflow: auto;
    }
    @media (max-width: 780px) {
      .controls { grid-template-columns: 1fr; }
      .summary { grid-template-columns: repeat(2, 1fr); }
      th:nth-child(4), td:nth-child(4), th:nth-child(6), td:nth-child(6) { display: none; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Painel de Testes da API</h1>
    <div id="status">Aguardando execução</div>
  </header>
  <main>
    <section class="controls">
      <label>
        Ativo
        <input id="asset" value="USDJPY_otc" autocomplete="off">
      </label>
      <button id="safeRun">Testar retornos</button>
      <button id="orderRun" class="secondary">Testar com ordem demo</button>
    </section>
    <section class="summary">
      <div class="metric"><span>Total</span><strong id="total">0</strong></div>
      <div class="metric"><span>Passou</span><strong id="passed">0</strong></div>
      <div class="metric"><span>Falhou</span><strong id="failed">0</strong></div>
      <div class="metric"><span>Ativo</span><strong id="assetOut">-</strong></div>
    </section>
    <div class="toolbar">
      <div id="lastRun">Nenhum teste executado</div>
      <div>Verde = retorno conforme expectativa</div>
    </div>
    <table>
      <thead>
        <tr>
          <th>Status</th>
          <th>Grupo</th>
          <th>Endpoint</th>
          <th>HTTP</th>
          <th>Expectativa</th>
          <th>Tempo</th>
          <th>Resumo</th>
        </tr>
      </thead>
      <tbody id="rows"></tbody>
    </table>
    <section id="orderBox" class="order" hidden>
      <strong>Resultado da ordem demo</strong>
      <pre id="orderJson"></pre>
    </section>
  </main>
  <script>
    const safeRun = document.getElementById('safeRun');
    const orderRun = document.getElementById('orderRun');
    const rows = document.getElementById('rows');
    const statusEl = document.getElementById('status');
    const orderBox = document.getElementById('orderBox');
    const orderJson = document.getElementById('orderJson');

    function setBusy(busy) {
      safeRun.disabled = busy;
      orderRun.disabled = busy;
      statusEl.textContent = busy ? 'Executando testes...' : 'Pronto';
    }

    function render(data) {
      document.getElementById('total').textContent = data.summary.total;
      document.getElementById('passed').textContent = data.summary.passed;
      document.getElementById('failed').textContent = data.summary.failed;
      document.getElementById('assetOut').textContent = data.asset;
      document.getElementById('lastRun').textContent = new Date().toLocaleString();
      rows.innerHTML = data.results.map(item => `
        <tr>
          <td><span class="pill ${item.passed ? 'ok' : 'fail'}">${item.passed ? 'OK' : 'FALHA'}</span></td>
          <td>${item.group}</td>
          <td>${item.method} ${item.name}</td>
          <td>${item.status_code ?? '-'}</td>
          <td>${item.expected}<br><small>${item.detail}</small></td>
          <td>${item.elapsed_ms} ms</td>
          <td>${item.summary}</td>
        </tr>
      `).join('');
      if (data.order) {
        orderBox.hidden = false;
        orderJson.textContent = JSON.stringify(data.order, null, 2);
      } else {
        orderBox.hidden = true;
        orderJson.textContent = '';
      }
    }

    async function run(includeOrder) {
      setBusy(true);
      rows.innerHTML = '';
      orderBox.hidden = true;
      try {
        const asset = encodeURIComponent(document.getElementById('asset').value || 'USDJPY_otc');
        const response = await fetch(`/test-panel/results?asset=${asset}&include_order=${includeOrder}`);
        const data = await response.json();
        render(data);
      } catch (error) {
        statusEl.textContent = `Erro: ${error.message}`;
      } finally {
        setBusy(false);
      }
    }

    safeRun.addEventListener('click', () => run(false));
    orderRun.addEventListener('click', () => run(true));
  </script>
</body>
</html>
"""


USAGE_PANEL_HTML = """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Painel de Uso da API</title>
  <style>
    :root {
      --bg: #eef3f8;
      --surface: #ffffff;
      --ink: #17202a;
      --muted: #667085;
      --line: #d7e0ea;
      --accent: #1f6feb;
      --good: #0f8a5f;
      --bad: #c2414b;
      --warn: #b36b00;
      --soft: #f7fafc;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Arial, Helvetica, sans-serif;
    }
    header {
      height: 64px;
      padding: 0 22px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      background: var(--surface);
      border-bottom: 1px solid var(--line);
    }
    h1 { margin: 0; font-size: 19px; }
    button, select, input {
      height: 36px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--surface);
      color: var(--ink);
      font-size: 14px;
    }
    button {
      border-color: var(--accent);
      background: var(--accent);
      color: #fff;
      font-weight: 700;
      padding: 0 13px;
      cursor: pointer;
    }
    button.secondary {
      background: var(--surface);
      color: var(--accent);
    }
    button:disabled { opacity: .55; cursor: wait; }
    select, input { padding: 0 10px; min-width: 180px; }
    main {
      display: grid;
      grid-template-columns: 280px minmax(0, 1fr);
      min-height: calc(100vh - 64px);
    }
    aside {
      border-right: 1px solid var(--line);
      background: var(--surface);
      padding: 14px;
      overflow: auto;
    }
    .content {
      padding: 16px;
      display: grid;
      gap: 14px;
      align-content: start;
    }
    .controls {
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
    }
    .asset-list {
      display: grid;
      gap: 6px;
      margin-top: 12px;
      max-height: calc(100vh - 150px);
      overflow: auto;
    }
    .asset-item {
      width: 100%;
      min-height: 36px;
      height: auto;
      text-align: left;
      border: 1px solid var(--line);
      background: var(--soft);
      color: var(--ink);
      font-weight: 600;
      padding: 8px 10px;
    }
    .asset-item.active {
      border-color: var(--accent);
      background: #e8f0ff;
      color: #143f91;
    }
    .grid {
      display: grid;
      gap: 12px;
    }
    .metrics {
      grid-template-columns: repeat(5, minmax(130px, 1fr));
    }
    .two {
      grid-template-columns: minmax(0, 1.35fr) minmax(320px, .65fr);
    }
    .three {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
    .card {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 13px;
      min-width: 0;
    }
    .metric span, .label {
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 6px;
    }
    .metric strong {
      display: block;
      font-size: 23px;
      line-height: 1.2;
      overflow-wrap: anywhere;
    }
    .signal {
      display: inline-flex;
      align-items: center;
      height: 28px;
      padding: 0 10px;
      border-radius: 999px;
      color: #fff;
      font-weight: 700;
      background: var(--muted);
    }
    .signal.call, .signal.buy { background: var(--good); }
    .signal.put, .signal.sell { background: var(--bad); }
    .signal.none { background: var(--muted); }
    canvas {
      width: 100%;
      height: 280px;
      display: block;
      background: #fbfdff;
      border: 1px solid var(--line);
      border-radius: 6px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
    }
    th, td {
      padding: 8px 7px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      font-size: 13px;
      vertical-align: top;
    }
    th {
      color: #344054;
      background: #edf2f7;
      font-size: 12px;
      text-transform: uppercase;
    }
    .kv {
      display: grid;
      gap: 8px;
    }
    .kv-row {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      border-bottom: 1px solid var(--line);
      padding-bottom: 7px;
      font-size: 13px;
    }
    .kv-row b { overflow-wrap: anywhere; text-align: right; }
    pre {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      max-height: 280px;
      overflow: auto;
      font-size: 12px;
      background: #101828;
      color: #eef4ff;
      border-radius: 6px;
      padding: 10px;
    }
    .status {
      color: var(--muted);
      font-size: 13px;
    }
    @media (max-width: 980px) {
      main { grid-template-columns: 1fr; }
      aside { border-right: 0; border-bottom: 1px solid var(--line); }
      .asset-list { max-height: 240px; }
      .metrics, .two, .three { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Painel de Uso da API</h1>
    <div class="controls">
      <select id="assetSelect"></select>
      <input id="assetInput" value="USDJPY_otc" autocomplete="off">
      <button id="loadBtn">Carregar</button>
      <button id="autoBtn" class="secondary">Auto</button>
    </div>
  </header>
  <main>
    <aside>
      <div class="label">Ativos retornados pela API</div>
      <div id="assetCount" class="status">Aguardando carga</div>
      <div id="assetList" class="asset-list"></div>
    </aside>
    <section class="content">
      <div id="status" class="status">Clique em Carregar para visualizar os dados.</div>
      <section class="grid metrics">
        <div class="card metric"><span>Ativo</span><strong id="mAsset">-</strong></div>
        <div class="card metric"><span>Preco</span><strong id="mPrice">-</strong></div>
        <div class="card metric"><span>Sinal</span><strong id="mSignal">-</strong></div>
        <div class="card metric"><span>Score</span><strong id="mScore">-</strong></div>
        <div class="card metric"><span>Atividade</span><strong id="mActivity">-</strong></div>
      </section>
      <section class="grid two">
        <div class="card">
          <div class="label">Candles recentes</div>
          <canvas id="chart" width="1100" height="360"></canvas>
        </div>
        <div class="card">
          <div class="label">Resumo operacional</div>
          <div id="summaryKv" class="kv"></div>
        </div>
      </section>
      <section class="grid three">
        <div class="card">
          <div class="label">Indicadores</div>
          <div id="indicatorKv" class="kv"></div>
        </div>
        <div class="card">
          <div class="label">Analises</div>
          <div id="analysisKv" class="kv"></div>
        </div>
        <div class="card">
          <div class="label">Estatisticas</div>
          <div id="statsKv" class="kv"></div>
        </div>
      </section>
      <section class="card">
        <div class="label">Historico</div>
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Open</th>
              <th>High</th>
              <th>Low</th>
              <th>Close</th>
              <th>Volume</th>
            </tr>
          </thead>
          <tbody id="historyRows"></tbody>
        </table>
      </section>
      <section class="card">
        <div class="label">Resposta agregada</div>
        <pre id="rawJson">{}</pre>
      </section>
    </section>
  </main>
  <script>
    const state = { data: null, auto: null, stream: null, streamAsset: null };
    const el = id => document.getElementById(id);
    const fields = ['ema_9','ema_21','sma_20','rsi_14','macd','bb_upper','bb_middle','bb_lower','atr','stoch_k','stoch_d','adx','vwap','sar'];

    function fmt(value, digits = 5) {
      if (value === null || value === undefined || value === '') return '-';
      const num = Number(value);
      if (Number.isFinite(num)) return num.toFixed(Math.abs(num) >= 100 ? 3 : digits);
      return String(value);
    }

    function kv(container, rows) {
      container.innerHTML = rows.map(([k, v]) => `
        <div class="kv-row"><span>${k}</span><b>${v === undefined || v === null || v === '' ? '-' : v}</b></div>
      `).join('');
    }

    function setBusy(busy) {
      el('loadBtn').disabled = busy;
      el('status').textContent = busy ? 'Carregando dados da API...' : 'Dados carregados.';
    }

    async function load(assetOverride) {
      const asset = assetOverride || el('assetInput').value || 'USDJPY_otc';
      el('assetInput').value = asset;
      setBusy(true);
      stopStream();
      try {
        const response = await fetch(`/usage-panel/data?asset=${encodeURIComponent(asset)}`);
        const data = await response.json();
        state.data = data;
        render(data);
        startStream(asset);
      } catch (error) {
        el('status').textContent = `Erro ao carregar: ${error.message}`;
      } finally {
        setBusy(false);
      }
    }

    function renderAssets(data) {
      const assets = data.assets || [];
      el('assetCount').textContent = `${assets.length} ativos`;
      const current = data.asset;
      const options = assets.slice(0, 250).map(a => {
        const symbol = a.symbol || a.asset || a.name || String(a);
        return `<option value="${symbol}" ${symbol === current ? 'selected' : ''}>${symbol}</option>`;
      }).join('');
      el('assetSelect').innerHTML = options;
      el('assetList').innerHTML = assets.slice(0, 160).map(a => {
        const symbol = a.symbol || a.asset || a.name || String(a);
        const name = a.name && a.name !== symbol ? a.name : '';
        return `<button class="asset-item ${symbol === current ? 'active' : ''}" data-asset="${symbol}">${symbol}${name ? `<br><small>${name}</small>` : ''}</button>`;
      }).join('');
      document.querySelectorAll('.asset-item').forEach(btn => {
        btn.addEventListener('click', () => load(btn.dataset.asset));
      });
    }

    function render(data) {
      const latest = data.latest || {};
      const signal = latest.signal || {};
      const activity = latest.activity || {};
      const candle = latest.candle || {};
      const tick = latest.tick || {};
      const indicator = latest.indicator || {};
      const action = String(signal.action || 'NONE').toLowerCase();

      renderAssets(data);
      el('mAsset').textContent = data.asset;
      el('mPrice').textContent = fmt(latest.price);
      el('mSignal').innerHTML = `<span class="signal ${action}">${signal.action || 'NONE'}</span>`;
      el('mScore').textContent = fmt(signal.score, 2);
      el('mActivity').textContent = fmt(activity.activityScore, 2);

      kv(el('summaryKv'), [
        ['Tick source', tick.source || '-'],
        ['Tick time', tick.time || tick.timestamp || '-'],
        ['Open', fmt(candle.open)],
        ['High', fmt(candle.high)],
        ['Low', fmt(candle.low)],
        ['Close', fmt(candle.close)],
        ['Razao do sinal', signal.reason || '-'],
        ['Confianca', fmt(signal.confidence, 2)],
        ['Expiracao', signal.expiration || '-'],
        ['Fase', signal.marketPhase || '-'],
        ['Tendencia', signal.trend || '-']
      ]);

      kv(el('indicatorKv'), fields.map(name => [name, fmt(indicator[name], 4)]));
      const analysis = data.analysis || {};
      kv(el('analysisKv'), [
        ['Trend', JSON.stringify(analysis.trend || {})],
        ['Volatility', JSON.stringify(analysis.volatility || {})],
        ['Momentum', JSON.stringify(analysis.momentum || {})],
        ['Confluence', JSON.stringify(analysis.confluence || {})],
        ['Order blocks', (analysis.orderBlocks || []).length],
        ['Liquidity', (analysis.liquidity || []).length],
        ['Support/resistance', (analysis.supportResistance || []).length],
        ['Market health', JSON.stringify(analysis.health || {})]
      ]);
      const stats = analysis.statistics || {};
      kv(el('statsKv'), Object.entries(stats).map(([k, v]) => [k, v]));
      renderHistory(data.series?.history || data.series?.candles || []);
      drawChart(data.series?.candles || []);
      el('rawJson').textContent = JSON.stringify(data, null, 2);
      const errCount = Object.keys(data.errors || {}).length;
      el('status').textContent = errCount ? `Dados carregados com ${errCount} erro(s).` : `Dados carregados em ${data.loadedAt}. Stream aguardando ticks.`;
    }

    function stopStream() {
      if (state.stream) {
        state.stream.close();
        state.stream = null;
        state.streamAsset = null;
      }
    }

    function startStream(asset) {
      if (state.streamAsset === asset && state.stream) return;
      stopStream();
      const source = new EventSource(`/market/candles/stream?symbol=${encodeURIComponent(asset)}&timeframe=60&interval=1`);
      state.stream = source;
      state.streamAsset = asset;
      source.addEventListener('ready', () => {
        el('status').textContent = `Streaming ativo para ${asset}.`;
      });
      source.addEventListener('heartbeat', () => {
        el('status').textContent = `Streaming ativo para ${asset}. Aguardando tick.`;
      });
      source.addEventListener('candle', event => {
        const payload = JSON.parse(event.data);
        applyStreamCandle(payload);
      });
      source.onerror = () => {
        el('status').textContent = `Streaming reconectando para ${asset}...`;
      };
    }

    function applyStreamCandle(payload) {
      if (!state.data || payload.symbol !== state.data.asset) return;
      const tick = payload.tick || {};
      const candle = payload.candle || {};
      state.data.latest.price = tick.price ?? candle.close ?? state.data.latest.price;
      state.data.latest.tick = tick;
      state.data.latest.candle = candle;
      if (Array.isArray(payload.candles)) {
        state.data.series.candles = payload.candles;
      }
      el('mPrice').textContent = fmt(state.data.latest.price);
      kv(el('summaryKv'), [
        ['Tick source', tick.source || '-'],
        ['Tick time', tick.time || tick.timestamp || '-'],
        ['Open', fmt(candle.open)],
        ['High', fmt(candle.high)],
        ['Low', fmt(candle.low)],
        ['Close', fmt(candle.close)],
        ['Razao do sinal', state.data.latest.signal?.reason || '-'],
        ['Confianca', fmt(state.data.latest.signal?.confidence, 2)],
        ['Expiracao', state.data.latest.signal?.expiration || '-'],
        ['Fase', state.data.latest.signal?.marketPhase || '-'],
        ['Tendencia', state.data.latest.signal?.trend || '-']
      ]);
      renderHistory(state.data.series?.candles || []);
      drawChart(state.data.series?.candles || []);
      el('status').textContent = `Streaming ${payload.symbol}: ${fmt(state.data.latest.price)} em ${new Date().toLocaleTimeString()}.`;
    }

    function renderHistory(rows) {
      el('historyRows').innerHTML = rows.slice(-12).reverse().map(row => `
        <tr>
          <td>${row.timestamp ?? '-'}</td>
          <td>${fmt(row.open)}</td>
          <td>${fmt(row.high)}</td>
          <td>${fmt(row.low)}</td>
          <td>${fmt(row.close)}</td>
          <td>${fmt(row.volume, 2)}</td>
        </tr>
      `).join('');
    }

    function drawChart(candles) {
      const canvas = el('chart');
      const ctx = canvas.getContext('2d');
      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = '#fbfdff';
      ctx.fillRect(0, 0, w, h);
      const rows = candles.filter(c => Number.isFinite(Number(c.close))).slice(-40);
      if (!rows.length) {
        ctx.fillStyle = '#667085';
        ctx.fillText('Sem candles para exibir', 20, 32);
        return;
      }
      const values = rows.flatMap(c => [Number(c.high ?? c.close), Number(c.low ?? c.close)]).filter(Number.isFinite);
      const min = Math.min(...values);
      const max = Math.max(...values);
      const pad = 24;
      const span = max - min || 1;
      const step = (w - pad * 2) / rows.length;
      ctx.strokeStyle = '#d7e0ea';
      ctx.lineWidth = 1;
      for (let i = 0; i < 5; i++) {
        const y = pad + ((h - pad * 2) / 4) * i;
        ctx.beginPath();
        ctx.moveTo(pad, y);
        ctx.lineTo(w - pad, y);
        ctx.stroke();
      }
      rows.forEach((c, i) => {
        const open = Number(c.open ?? c.close);
        const close = Number(c.close);
        const high = Number(c.high ?? close);
        const low = Number(c.low ?? close);
        const x = pad + i * step + step / 2;
        const y = v => h - pad - ((v - min) / span) * (h - pad * 2);
        const up = close >= open;
        ctx.strokeStyle = up ? '#0f8a5f' : '#c2414b';
        ctx.fillStyle = ctx.strokeStyle;
        ctx.beginPath();
        ctx.moveTo(x, y(high));
        ctx.lineTo(x, y(low));
        ctx.stroke();
        const bodyTop = y(Math.max(open, close));
        const bodyBottom = y(Math.min(open, close));
        const bodyH = Math.max(2, bodyBottom - bodyTop);
        ctx.fillRect(x - Math.max(3, step * .28), bodyTop, Math.max(6, step * .56), bodyH);
      });
      ctx.fillStyle = '#344054';
      ctx.fillText(`Min ${fmt(min)}  Max ${fmt(max)}`, pad, 16);
    }

    el('loadBtn').addEventListener('click', () => load());
    el('assetSelect').addEventListener('change', event => load(event.target.value));
    el('autoBtn').addEventListener('click', () => {
      if (state.auto) {
        clearInterval(state.auto);
        state.auto = null;
        el('autoBtn').textContent = 'Auto';
        return;
      }
      load();
      state.auto = setInterval(() => load(), 30000);
      el('autoBtn').textContent = 'Parar';
    });
    window.addEventListener('beforeunload', stopStream);
    load();
  </script>
</body>
</html>
"""
